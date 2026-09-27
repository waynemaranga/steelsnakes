"""IS 800:2025 (draft) 10.8 classification; limits from Table 2 (codes/IS 800-2025 (Draft for comments).pdf), which
restates EN 1993-1-1 Table 5.2 with ε = (250/fy)^0.5. Sections are IS 808 profiles built from their dimensions, as the
IN module ships no data yet: ISMB 300 (D 300, B 140, t 7.5, T 12.4, R1 14 mm, A 56.26 cm²) and ISMC 200."""

import math

import pytest

from steelsnakes.base.checks import SectionClass
from steelsnakes.base.renders import CheckBlock
from steelsnakes.base.sections import SectionType
from steelsnakes.IN.checks import (
    ElementInput,
    ElementKind,
    ElementStressDistribution,
    StressPattern,
    classify_element,
    classify_section,
    classify_section_from_dict,
    compound_flange_elements,
    effective_width,
    element_limits,
    epsilon,
    render_classification,
    stress_ratios,
    ultimate_stress,
    yield_stress,
)
from steelsnakes.IN.sections import (
    EqualAngle,
    HeavyWeightBeam,
    MediumWeightBeam,
    MediumWeightChannel,
    ParallelFlangeBearingPile,
    StandardColumn,
    UnequalAngle,
)

C = ElementStressDistribution.COMPRESSION
B = ElementStressDistribution.BENDING
M = ElementStressDistribution.COMBINED
EPS_350 = math.sqrt(250.0 / 350.0)

ISMB_300 = MediumWeightBeam(designation="ISMB 300", D=300.0, B=140.0, t=7.5, T=12.4, R1=14.0, area=56.26)
ISMC_200 = MediumWeightChannel(designation="ISMC 200", D=200.0, B=75.0, t=6.1, T=11.4, R1=11.0, area=28.21)


# --- Table 1 and Table 2 note 2 ---
def test_yield_stress_follows_the_is_2062_thickness_bands() -> None:
    assert yield_stress(12.4, "E250") == 250.0 # t < 20 mm
    assert yield_stress(20.0, "E250") == 240.0 # 20 mm to 40 mm
    assert yield_stress(40.0, "E250") == 240.0
    assert yield_stress(40.1, "E250") == 230.0 # > 40 mm
    assert [yield_stress(t, "E350") for t in (10.0, 30.0, 50.0)] == [350.0, 330.0, 320.0]
    assert yield_stress(10.0, "e 450 br") == 450.0 # qualities and spaces are ignored
    assert ultimate_stress("E250") == 410.0
    assert ultimate_stress("E410 C") == 540.0
    with pytest.raises(ValueError, match="Unknown steel_grade"):
        yield_stress(10.0, "S275")
    with pytest.raises(ValueError, match="positive"):
        yield_stress(0.0, "E250")


def test_epsilon_is_referred_to_250_mpa() -> None:
    assert epsilon(250.0) == 1.0
    assert epsilon(350.0) == pytest.approx(0.845, abs=1e-3)
    with pytest.raises(ValueError):
        epsilon(0.0)


# --- Table 2 ---
def test_table_2_restates_ec3_table_5_2_with_epsilon_at_250_mpa() -> None:
    # 9ε, 10ε, 14ε (ε at 235 MPa) become 8.7ε, 9.7ε, 13.6ε; 72ε/83ε/124ε become 70ε/80ε/120ε; 396ε/456ε 384ε/442ε
    to_250: float = math.sqrt(235.0 / 250.0)
    for ec3, is800 in ((9.0, 8.7), (10.0, 9.7), (14.0, 13.6), (33.0, 32.0), (38.0, 36.8), (42.0, 40.7), (15.0, 14.5), (23.0, 22.3)):
        assert ec3 * to_250 == pytest.approx(is800, abs=0.06)
    for ec3, is800 in ((72.0, 70.0), (83.0, 80.0), (124.0, 120.0), (396.0, 384.0), (456.0, 442.0), (36.0, 35.0), (41.5, 40.2)):
        assert ec3 * to_250 == pytest.approx(is800, rel=0.01)


def test_outstand_limits_uniform_and_non_uniform() -> None:
    uniform = element_limits(ElementInput(name="f", kind=ElementKind.OUTSTAND, b_mm=70.0, t_mm=10.0), 350.0)
    assert (uniform.class_1_limit, uniform.class_2_limit, uniform.class_3_limit) == pytest.approx((8.7 * EPS_350, 9.7 * EPS_350, 13.6 * EPS_350))
    tip_c = element_limits(ElementInput(name="f", kind=ElementKind.OUTSTAND, stress=ElementStressDistribution.TIP_COMPRESSION, b_mm=70.0, t_mm=10.0, r1=0.5), 250.0)
    assert (tip_c.class_1_limit, tip_c.class_2_limit) == pytest.approx((17.4, 19.4)) # 8.7ε/r1, 9.7ε/r1
    assert tip_c.class_3_limit == pytest.approx(13.6) # blank in Table 2: the uniform limit, conservative
    tip_t = element_limits(ElementInput(name="f", kind=ElementKind.OUTSTAND, stress=ElementStressDistribution.TIP_TENSION, b_mm=70.0, t_mm=10.0, r1=0.5), 250.0)
    assert tip_t.class_1_limit == pytest.approx(8.7 / (0.5 * math.sqrt(0.5))) # 8.7ε/(r1√r1)
    in_tension = element_limits(ElementInput(name="f", kind=ElementKind.OUTSTAND, stress=ElementStressDistribution.TIP_TENSION, b_mm=70.0, t_mm=10.0, r1=0.0), 250.0)
    assert in_tension.class_3_limit == math.inf
    with pytest.raises(ValueError, match="need r1"):
        element_limits(ElementInput(name="f", kind=ElementKind.OUTSTAND, stress=ElementStressDistribution.TIP_COMPRESSION, b_mm=70.0, t_mm=10.0), 250.0)


def test_internal_element_limits() -> None:
    web = ElementInput(name="web", kind=ElementKind.INTERNAL, stress=C, b_mm=200.0, t_mm=8.0)
    assert element_limits(web, 250.0).model_dump(exclude={"note"}) == pytest.approx({"class_1_limit": 32.0, "class_2_limit": 36.8, "class_3_limit": 40.7})
    web_bending = web.model_copy(update={"stress": B})
    assert (element_limits(web_bending, 250.0).class_1_limit, element_limits(web_bending, 250.0).class_3_limit) == (70.0, 120.0)

    def combined(r1: float, r2: float) -> tuple[float, float, float]:
        limits = element_limits(web.model_copy(update={"stress": M, "r1": r1, "r2": r2}), 250.0)
        return limits.class_1_limit, limits.class_2_limit, limits.class_3_limit # type: ignore[return-value]

    # the r1 branches meet at r1 = 0.5 (≈ 70ε, 80ε) and reach the axial compression row at r1 = 1
    assert combined(0.5, -1.0)[:2] == pytest.approx((70.0, 80.4))
    assert combined(0.5 + 1e-9, -1.0)[:2] == pytest.approx((69.8, 80.4), abs=0.1)
    assert combined(1.0, 1.0) == pytest.approx((32.0, 36.83, 40.7), abs=0.01)
    # the r2 branches meet at r2 = -1 (120ε)
    assert combined(0.5, -1.0)[2] == pytest.approx(120.0)
    assert combined(0.5, -1.0 + 1e-9)[2] == pytest.approx(40.7 / 0.34, abs=0.01)
    assert combined(0.3, -2.0)[2] == pytest.approx(60.0 * 3.0 * math.sqrt(2.0)) # 60ε(1 - r2)(-r2)^0.5
    assert combined(0.0, -3.0)[0] == math.inf # web in tension
    with pytest.raises(ValueError, match="need r2"):
        element_limits(web.model_copy(update={"stress": M, "r1": 0.6}), 250.0)


def test_angle_and_chs_rows() -> None:
    legs = element_limits(ElementInput(name="leg", kind=ElementKind.ANGLE_LEG, b_mm=100.0, t_mm=10.0), 250.0)
    assert (legs.class_1_limit, legs.class_2_limit, legs.class_3_limit) == (8.7, 9.7, 14.5)
    back_to_back = element_limits(ElementInput(name="leg", kind=ElementKind.ANGLE_OUTSTAND_LEG, b_mm=100.0, t_mm=10.0), 250.0)
    assert back_to_back.class_3_limit == 14.5
    chs_moment = element_limits(ElementInput(name="wall", kind=ElementKind.CHS, stress=B, b_mm=200.0, t_mm=5.0), 350.0)
    eps2: float = 250.0 / 350.0
    assert (chs_moment.class_1_limit, chs_moment.class_2_limit, chs_moment.class_3_limit) == pytest.approx((47.0 * eps2, 66.0 * eps2, 85.0 * eps2))
    chs_axial = element_limits(ElementInput(name="wall", kind=ElementKind.CHS, stress=C, b_mm=200.0, t_mm=5.0), 250.0)
    assert (chs_axial.class_1_limit, chs_axial.class_3_limit) == (None, 86.0)


def test_single_angle_in_axial_compression_takes_all_three_criteria() -> None:
    # ISA 100x100x10: b/t = d/t = 10 <= 14.5, (b + d)/t = 20 <= 22.3 -> semi-compact
    stocky = classify_element(ElementInput(name="angle", kind=ElementKind.ANGLE, b_mm=100.0, t_mm=10.0, leg_mm=100.0), 250.0)
    assert stocky.section_class == SectionClass.CLASS_3
    # ISA 100x100x8: b/t = 12.5 <= 14.5 but (b + d)/t = 25 > 22.3 -> slender
    thin = classify_element(ElementInput(name="angle", kind=ElementKind.ANGLE, b_mm=100.0, t_mm=8.0, leg_mm=100.0), 250.0)
    assert thin.section_class == SectionClass.CLASS_4
    assert thin.metadata["governing_check"] == "(b+d)/t"
    with pytest.raises(ValueError, match="leg_mm"):
        classify_element(ElementInput(name="angle", kind=ElementKind.ANGLE, b_mm=100.0, t_mm=8.0), 250.0)


def test_stress_ratios() -> None:
    # ISMB 300 web d = 300 - 2(12.4 + 14) = 247.2 mm; P = 300 kN
    ratios = stress_ratios(300.0, 247.2, 7.5, 250.0, 56.26)
    assert ratios.r1 == pytest.approx(0.5 * (1.0 + 300e3 / (247.2 * 7.5 * 250.0)))
    assert ratios.r2 == pytest.approx(2.0 * 300e3 / (5626.0 * 250.0) - 1.0)
    assert stress_ratios(0.0, 247.2, 7.5, 250.0, 56.26).model_dump() == pytest.approx({"r1": 0.5, "r2": -1.0})
    assert stress_ratios(5000.0, 247.2, 7.5, 250.0, 56.26).model_dump() == pytest.approx({"r1": 1.0, "r2": 1.0}) # capped
    assert stress_ratios(300.0, 185.0, 5.0, 250.0, 28.0, webs=2).r1 == pytest.approx(0.5 * (1.0 + 300e3 / (2 * 185.0 * 5.0 * 250.0)))
    with pytest.raises(ValueError):
        stress_ratios(300.0, 0.0, 7.5, 250.0, 56.26)


# --- Sections (Fig. 2A) ---
def test_ismb_300_in_each_stress_pattern() -> None:
    compression = classify_section(ISMB_300, steel_grade="E250", stress_pattern="compression")
    elements = {element.name: element for element in compression.elements}
    assert elements["flange"].ratio == pytest.approx(70.0 / 12.4) # b = B/2
    assert elements["web"].ratio == pytest.approx(247.2 / 7.5) # d clear of the root fillets: 32.96 > 32ε
    assert compression.section_class == SectionClass.CLASS_2
    assert compression.governing_elements == ["web"]
    assert classify_section(ISMB_300, stress_pattern=StressPattern.MAJOR_AXIS_BENDING).section_class == SectionClass.CLASS_1
    minor = classify_section(ISMB_300, stress_pattern="bending-minor-axis")
    assert [element.name for element in minor.elements] == ["flange"] # the web lies on the neutral axis
    assert minor.elements[0].stress == ElementStressDistribution.TIP_COMPRESSION
    combined = classify_section(ISMB_300, stress_pattern="combined", P_kN=300.0)
    assert combined.r1 == pytest.approx(0.8237, abs=1e-4)
    assert combined.section_class == SectionClass.CLASS_1 # 32.96 <= 384/(13 x 0.8237 - 1) = 39.6
    # E350: ε = 0.845, the web in compression is semi-compact (31.1 < 32.96 <= 34.4)
    assert classify_section(ISMB_300, steel_grade="E350").section_class == SectionClass.CLASS_3


def test_channel_and_angle_sections() -> None:
    channel = classify_section(ISMC_200, stress_pattern="bending-major-axis")
    assert {element.name: round(element.ratio, 2) for element in channel.elements} == {"flange": round(75.0 / 11.4, 2), "web": round(155.2 / 6.1, 2)}
    minor = classify_section(ISMC_200, stress_pattern="bending-minor-axis")
    assert [element.stress for element in minor.elements] == [C, C] # conservatively in compression
    angle = UnequalAngle(designation="ISA 100x75x8", a=100.0, b=75.0, t=8.0, area=13.36)
    compression = classify_section(angle, stress_pattern="compression")
    assert compression.elements[0].b_mm == 100.0 and compression.elements[0].metadata["d/t"] == pytest.approx(75.0 / 8.0)
    assert compression.section_class == SectionClass.CLASS_3 # (100 + 75)/8 = 21.9 <= 22.3
    bending = classify_section(angle, stress_pattern="bending")
    assert [element.name for element in bending.elements] == ["leg_b", "leg_d"]
    assert bending.section_class == SectionClass.CLASS_3 # 100/8 = 12.5 <= 14.5ε; 75/8 = 9.4 <= 9.7ε is compact
    assert classify_section(EqualAngle(designation="ISA 100x100x8", t=8.0, area=15.39), stress_pattern="compression").section_class == SectionClass.CLASS_4


def test_hollow_sections_from_plain_properties() -> None:
    # RHS 200x100x5: b = 100 - 3t = 85, d = 200 - 3t = 185; in compression d/t = 37 > 36.8 -> semi-compact
    rhs = classify_section_from_dict(SectionType.HFRHS, {"hxb": "200x100", "t": 5.0, "A": 28.4}, fy_mpa=250.0)
    assert {element.name: element.ratio for element in rhs.elements} == pytest.approx({"flange_wall": 17.0, "web_wall": 37.0})
    assert rhs.section_class == SectionClass.CLASS_3
    minor = classify_section_from_dict(SectionType.HFRHS, {"D": 200.0, "B": 100.0, "t": 5.0, "A": 28.4}, fy_mpa=250.0, stress_pattern="bending-minor-axis")
    assert {element.name: element.ratio for element in minor.elements} == pytest.approx({"flange_wall": 37.0, "web_wall": 17.0})
    combined = classify_section_from_dict(SectionType.CFRHS, {"D": 200.0, "B": 100.0, "t": 5.0, "A": 28.4}, fy_mpa=250.0, stress_pattern="combined", P_kN=200.0)
    assert combined.r1 == pytest.approx(0.5 * (1.0 + 200e3 / (2 * 185.0 * 5.0 * 250.0)))
    # CHS 219.1x5: D/t = 43.8 <= 47ε² in bending; <= 86ε² in axial compression
    chs = {"D": 219.1, "t": 5.0, "A": 33.6}
    assert classify_section_from_dict(SectionType.HFCHS, chs, fy_mpa=250.0, stress_pattern="bending").section_class == SectionClass.CLASS_1
    assert classify_section_from_dict(SectionType.HFCHS, chs, fy_mpa=250.0).section_class == SectionClass.CLASS_3
    moment_row = classify_section_from_dict(SectionType.CFCHS, {"D_t": 80.0, "t": 4.0, "A": 30.0}, fy_mpa=250.0, stress_pattern="combined", P_kN=100.0)
    assert moment_row.section_class == SectionClass.CLASS_3 and any("moment row" in note for note in moment_row.notes)


def test_slender_web_note_and_effective_width() -> None:
    # A thin rolled web: d = 600 - 2(12 + 10) = 556, d/t = 92.7 > 67ε (Table 2 note 3) and > 40.7ε in compression
    data = {"D": 600.0, "B": 210.0, "t": 6.0, "T": 12.0, "R1": 10.0, "area": 83.0}
    result = classify_section_from_dict(SectionType.MWB, data, fy_mpa=250.0)
    assert result.is_slender and result.section_class == SectionClass.CLASS_4
    assert any("note 3" in note for note in result.notes) and any("10.8.2 d)" in note for note in result.notes)
    assert effective_width(556.0, 6.0, 40.7) == pytest.approx(244.2)
    assert effective_width(200.0, 6.0, 40.7) == 200.0
    with pytest.raises(ValueError):
        effective_width(0.0, 6.0, 40.7)


def test_compound_flange_elements() -> None:
    elements = compound_flange_elements(be_mm=120.0, te_mm=20.0, bi_mm=180.0, tp_mm=12.0, bo_mm=30.0)
    assert [(element.name, element.kind) for element in elements] == [
        ("compound_outstand", ElementKind.OUTSTAND),
        ("plate_internal", ElementKind.INTERNAL),
        ("plate_outstand", ElementKind.OUTSTAND),
    ]
    result = classify_section(custom_elements=elements, fy_mpa=250.0)
    assert result.section_class == SectionClass.CLASS_1 # 120/20 = 6, 180/12 = 15 and 30/12 = 2.5 are all plastic
    assert result.governing_elements == ["compound_outstand", "plate_internal", "plate_outstand"]
    thin_plate = compound_flange_elements(be_mm=120.0, te_mm=20.0, bi_mm=500.0, tp_mm=12.0)
    assert classify_section(custom_elements=thin_plate, fy_mpa=250.0).governing_elements == ["plate_internal"] # 41.7 > 40.7
    with pytest.raises(ValueError, match="tp_mm"):
        compound_flange_elements(be_mm=120.0, te_mm=20.0, bi_mm=180.0)


def test_render_classification() -> None:
    block = render_classification(classify_section(ISMB_300, stress_pattern="combined", P_kN=300.0))
    assert isinstance(block, CheckBlock)
    assert block.subtitle == "IS 800:2025 10.8" and block.passed
    assert "Class 1" in block.rows[-1].badge # type: ignore[operator]


def test_classification_errors() -> None:
    with pytest.raises(ValueError, match="fy_mpa is required"):
        classify_section(custom_elements=[ElementInput(name="x", kind=ElementKind.OUTSTAND, b_mm=10.0, t_mm=1.0)])
    with pytest.raises(ValueError, match="Provide either"):
        classify_section()
    with pytest.raises(ValueError, match="Did you mean"):
        classify_section(ISMB_300, stress_pattern="compresion")
    with pytest.raises(ValueError, match="needs P_kN"):
        classify_section(ISMB_300, stress_pattern="combined")
    with pytest.raises(NotImplementedError):
        classify_section_from_dict(SectionType.UB, {"D": 300.0}, fy_mpa=250.0)
    with pytest.raises(ValueError, match="Missing flange width"):
        classify_section_from_dict(SectionType.MWB, {"D": 300.0, "T": 12.0, "t": 7.0}, fy_mpa=250.0)
    with pytest.raises(ValueError, match="At least one"):
        classify_section(custom_elements=[], fy_mpa=250.0)


def test_every_in_section_class_can_be_built() -> None:
    # SC, HWB and PBP had no section type, and columns, channels and piles no get_properties()
    for cls, section_type in ((StandardColumn, SectionType.SC), (HeavyWeightBeam, SectionType.HWB), (ParallelFlangeBearingPile, SectionType.PBP), (MediumWeightChannel, SectionType.MWC)):
        section = cls(designation="x", D=200.0, B=200.0, t=8.0, T=12.0, R1=12.0, area=50.0)
        assert section.get_section_type() == section_type
        assert section.get_properties()["D"] == 200.0
    column = StandardColumn(designation="ISSC 200", D=200.0, B=200.0, t=9.0, T=15.0, R1=12.0, area=65.0)
    assert classify_section(column).section_class == SectionClass.CLASS_1 # (200 - 54)/9 = 16.2 <= 32ε; 100/15 = 6.7
