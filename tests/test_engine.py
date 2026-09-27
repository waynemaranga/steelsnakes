from __future__ import annotations

from functools import lru_cache
from typing import Any, Callable

import pytest
from sectionproperties.pre.library import rectangular_section

from steelsnakes.base.sections import BaseSection, SectionType
from steelsnakes.BS.checks.uls import check_bending as bs_check_bending
from steelsnakes.engine import LENGTH_UNITS, SECTION_TABLE_UNITS, SectionAnalysis, analyse_section, get_unit, section_geometry
from steelsnakes.engine.units import CM, CM4, DM6, IN4, INCH, MM4_E6, MM6_E9
from steelsnakes.EU import IPE, UPN
from steelsnakes.EU.checks.uls import check_bending
from steelsnakes.UK import CFSHS, HFCHS, HFEHS, HFRHS, L_EQUAL, L_EQUAL_B2B, L_UNEQUAL, PFC, UB
from steelsnakes.US.sections import HSS_RCT, HSS_RND, WT, S_beam, W_beam
from steelsnakes.US.sections import L_UNEQUAL as US_L_UNEQUAL
from steelsnakes.US_Metric.sections.beams import W as W_METRIC

GEOMETRIC_TOLERANCE = 0.015 # A, I, W, i: the drawn polygon against the tables, which round to 3 significant figures
WARPING_TOLERANCE = 0.04 # I_t and I_w: the tables use closed-form approximations, e.g EN 10210-2 for I_t of EHS


@lru_cache(maxsize=None)
def _analysis(make: Callable[[str], BaseSection], designation: str) -> tuple[BaseSection, SectionAnalysis]:
    section: BaseSection = make(designation)
    return section, analyse_section(section)


def _assert_matches_table(properties: dict[str, float], table: dict[str, Any], keys: dict[str, str], rel: float) -> None:
    for key, table_key in keys.items():
        assert properties[key] == pytest.approx(table[table_key], rel=rel), f"{key} against the table's {table_key}"


# --- Units ---
def test_units_aliases_and_conversions() -> None:
    assert get_unit("cm4") is CM4
    assert get_unit("cm^4") is CM4
    assert get_unit("cm**4") is CM4
    assert get_unit("in") is INCH
    assert CM4.to_mm(8356.0) == pytest.approx(8.356e7) # IPE 300 I_y
    assert DM6.from_mm(1.26e11) == pytest.approx(0.126) # IPE 300 I_w, as the EU tables give it
    assert IN4.to_mm(1.0) == pytest.approx(25.4**4)
    assert MM4_E6.to_mm(416.0) == pytest.approx(4.16e8) # W360X134 Ix
    assert MM6_E9.to_mm(4300.0) == pytest.approx(4.3e12) # W360X134 Cw
    with pytest.raises(ValueError):
        get_unit("furlong")


def test_section_table_units_align_with_the_modules() -> None:
    assert set(LENGTH_UNITS) == {"UK", "EU", "US", "US_METRIC"}
    assert set(SECTION_TABLE_UNITS) == {"UK", "EU", "BS", "US", "US_METRIC"}
    assert SECTION_TABLE_UNITS["EU"] is SECTION_TABLE_UNITS["UK"]
    assert SECTION_TABLE_UNITS["UK"]["I_w"] == ("I_w", DM6) # EU/UK I_w in dm⁶, as EU.checks.uls reads it
    assert SECTION_TABLE_UNITS["UK"]["i_y"] == ("i_yy", CM)
    assert SECTION_TABLE_UNITS["BS"]["W_pl_y"][0] == "Sx" # BS 5950: S plastic, Z elastic
    assert SECTION_TABLE_UNITS["BS"]["I_w"][0] == "H" # BS 5950: H is the warping constant
    assert SECTION_TABLE_UNITS["US"]["H"][0] == "H" # AISC: H is the flexural constant of E4
    assert SECTION_TABLE_UNITS["US"]["I_u"][0] == "Iw" # AISC angles: w-w is the major principal axis


# --- Tabulated sections against their own tables ---
UK_I_KEYS: dict[str, str] = {"A": "A", "I_yy": "I_yy", "I_zz": "I_zz", "W_el_yy": "W_el_yy", "W_el_zz": "W_el_zz", "W_pl_yy": "W_pl_yy", "W_pl_zz": "W_pl_zz"}
UK_WARPING_KEYS: dict[str, str] = {"I_t": "I_t", "I_w": "I_w"}
UK_ANGLE_KEYS: dict[str, str] = {"A": "A", "I_yy": "I_yy", "I_zz": "I_zz", "I_uu": "I_uu", "I_vv": "I_vv", "W_el_yy": "W_el_yy"}
UK_RHS_KEYS: dict[str, str] = {"A": "A", "I_yy": "I_yy", "I_zz": "I_zz", "W_el_yy": "W_el_yy", "W_pl_yy": "W_pl_yy", "W_pl_zz": "W_pl_zz"}
UK_SHS_KEYS: dict[str, str] = {"A": "A", "I_yy": "I", "I_zz": "I", "W_el_yy": "W_el", "W_pl_yy": "W_pl"} # SHS/CHS tables are unsuffixed
US_I_KEYS: dict[str, str] = {"A": "A", "Ix": "Ix", "Iy": "Iy", "Sx": "Sx", "Sy": "Sy", "Zx": "Zx", "Zy": "Zy"}
US_WARPING_KEYS: dict[str, str] = {"J": "J", "Cw": "Cw"}

TABLE_CASES: list[tuple[str, Callable[[str], BaseSection], str, str, dict[str, str], dict[str, str]]] = [
    ("EU IPE 300", IPE, "IPE-300", "EU", UK_I_KEYS, UK_WARPING_KEYS),
    ("UK UB 457x191x67", UB, "457x191x67", "UK", UK_I_KEYS, UK_WARPING_KEYS),
    ("UK PFC 200x90x30", PFC, "200x90x30", "UK", UK_I_KEYS, UK_WARPING_KEYS),
    ("UK L 100x100x10", L_EQUAL, "100x100x10.0", "UK", UK_ANGLE_KEYS, {"I_t": "I_t"}),
    ("UK L 200x150x18", L_UNEQUAL, "200x150x18", "UK", UK_ANGLE_KEYS, {"I_t": "I_t"}),
    ("UK HFRHS 200x100x8.0", HFRHS, "200x100x8.0", "UK", UK_RHS_KEYS, {"I_t": "I_t"}),
    ("UK CFSHS 100x100x5.0", CFSHS, "100x100x5.0", "UK", UK_SHS_KEYS, {"I_t": "I_t"}),
    ("UK HFCHS 168.3x10.0", HFCHS, "168.3x10.0", "UK", UK_SHS_KEYS, {"I_t": "I_t"}),
    ("UK HFEHS 300x150x8.0", HFEHS, "300x150x8.0", "UK", UK_RHS_KEYS, {"I_t": "I_t"}),
    ("US W14X90", W_beam, "W14X90", "US", US_I_KEYS, US_WARPING_KEYS),
    ("US WT7X45", WT, "WT7X45", "US", {**US_I_KEYS, "ro": "ro", "H": "H"}, US_WARPING_KEYS),
    ("US L8X4X1/2", US_L_UNEQUAL, "L8X4X1/2", "US", {"A": "A", "Ix": "Ix", "Iy": "Iy", "Iw": "Iw", "Iz": "Iz", "rz": "rz", "Sx": "Sx", "Zx": "Zx"}, {"J": "J", "Cw": "Cw", "ro": "ro"}),
    ("US HSS8X4X1/2", HSS_RCT, "HSS8X4X1/2", "US", US_I_KEYS, {"J": "J"}),
    ("US HSS6.625X0.500", HSS_RND, "HSS6.625X0.500", "US", US_I_KEYS, {"J": "J"}),
    ("US_Metric W360X134", W_METRIC, "W360X134", "US_METRIC", US_I_KEYS, US_WARPING_KEYS),
]


@pytest.mark.parametrize(("name", "make", "designation", "region", "keys", "warping_keys"), TABLE_CASES, ids=[case[0] for case in TABLE_CASES])
def test_tabulated_sections_match_their_tables(
    name: str,
    make: Callable[[str], BaseSection],
    designation: str,
    region: str,
    keys: dict[str, str],
    warping_keys: dict[str, str],
) -> None:
    section, analysis = _analysis(make, designation)
    properties: dict[str, float] = analysis.to_properties(region)
    table: dict[str, Any] = section.get_properties()
    _assert_matches_table(properties, table, keys, GEOMETRIC_TOLERANCE)
    _assert_matches_table(properties, table, warping_keys, WARPING_TOLERANCE)
    assert analysis.designation == section.designation
    assert analysis.section_type == section.get_section_type()


def test_ipe_300_in_mm_units() -> None:
    _, analysis = _analysis(IPE, "IPE-300")
    assert analysis.A == pytest.approx(5381.0, rel=1e-3) # 2btf + (h - 2tf)tw + (4 - π)r² = 5381.2 mm²
    assert analysis.W_pl_y == pytest.approx(628_355.0, rel=1e-3) # twh²/4 + (b - tw)(h - tf)tf + (4 - π)r²(h - 2tf)/2 + (3π - 10)r³/3
    assert analysis.I_w == pytest.approx(analysis.I_z * (300.0 - 10.7) ** 2 / 4.0, rel=0.02) # I_z(h - tf)²/4
    assert analysis.y_s == pytest.approx(0.0, abs=1e-3) # doubly symmetric: shear centre at the centroid
    assert analysis.z_s == pytest.approx(0.0, abs=1e-3)
    assert analysis.I_yz == pytest.approx(0.0, abs=1e-3 * analysis.I_y)
    assert analysis.mesh_elements > 200
    assert "I_uu" not in analysis.to_properties("EU") # principal axes only for sections with I_yz


def test_angle_principal_axes() -> None:
    _, analysis = _analysis(L_EQUAL, "100x100x10.0")
    assert analysis.alpha % 90.0 == pytest.approx(45.0, abs=0.01) # equal angle: principal axes at 45° to the legs
    assert analysis.I_u + analysis.I_v == pytest.approx(analysis.I_y + analysis.I_z, rel=1e-9)
    properties: dict[str, float] = analysis.to_properties("UK")
    assert {"I_uu", "I_vv", "i_uu", "i_vv"} <= set(properties)


def test_channel_shear_centre_behind_the_web() -> None:
    section, analysis = _analysis(PFC, "200x90x30")
    assert analysis.z_s == pytest.approx(0.0, abs=1e-3)
    # e0 of the tables is from the centreline of the web, by the thin-walled 3b'²tf/(6b'tf + h'tw) = 36.7 mm; the
    # ... fillets draw the shear centre towards the web
    tw: float = section.get_properties()["tw"]
    e_0: float = -(analysis.y_c + analysis.y_s) + tw / 2.0 # the back of the web is at the origin
    assert e_0 / 10.0 == pytest.approx(section.get_properties()["e0"], rel=0.05) # cm


def test_us_and_us_metric_twins_agree() -> None:
    _, imperial = _analysis(W_beam, "W14X90")
    _, metric = _analysis(W_METRIC, "W360X134")
    assert metric.A == pytest.approx(imperial.A, rel=0.01) # both in mm², from inches and mm respectively
    assert metric.I_y == pytest.approx(imperial.I_y, rel=0.01)
    assert metric.I_w == pytest.approx(imperial.I_w, rel=0.02)


# --- Built-up and custom sections ---
def test_welded_i_section_from_plain_dimensions() -> None:
    # 300 x 20 flanges on a 1000 x 10 web, no fillets; exact for the polygon
    analysis: SectionAnalysis = analyse_section(
        section_type=SectionType.UB,
        properties={"designation": "welded", "h": 1040.0, "b": 300.0, "tw": 10.0, "tf": 20.0, "r": 0.0},
        region="UK",
    )
    assert analysis.designation == "welded"
    assert analysis.A == pytest.approx(2 * 300.0 * 20.0 + 1000.0 * 10.0, rel=1e-9)
    assert analysis.I_y == pytest.approx((300.0 * 1040.0**3 - 290.0 * 1000.0**3) / 12.0, rel=1e-9)
    assert analysis.W_pl_y == pytest.approx(2 * 300.0 * 20.0 * 510.0 + 10.0 * 1000.0**2 / 4.0, rel=1e-9)
    assert analysis.I_z == pytest.approx(2 * 20.0 * 300.0**3 / 12.0 + 1000.0 * 10.0**3 / 12.0, rel=1e-9)


def test_monosymmetric_plate_girder_geometry() -> None:
    top = rectangular_section(d=20.0, b=300.0).shift_section(x_offset=-150.0, y_offset=500.0)
    web = rectangular_section(d=1000.0, b=10.0).shift_section(x_offset=-5.0, y_offset=-500.0)
    bottom = rectangular_section(d=25.0, b=400.0).shift_section(x_offset=-200.0, y_offset=-525.0)
    analysis: SectionAnalysis = analyse_section(geometry=top + web + bottom)
    assert analysis.A == pytest.approx(6000.0 + 10_000.0 + 10_000.0, rel=1e-9)
    assert analysis.designation is None and analysis.section_type is None
    # Thin-walled I_w = h_s² I_f1 I_f2/(I_f1 + I_f2), h_s between the flange centroids; the shear centre is nearer the
    # ... stiffer (bottom) flange
    I_f1: float = 20.0 * 300.0**3 / 12.0
    I_f2: float = 25.0 * 400.0**3 / 12.0
    h_s: float = 510.0 + 512.5
    assert analysis.I_w == pytest.approx(h_s**2 * I_f1 * I_f2 / (I_f1 + I_f2), rel=0.01)
    assert analysis.y_s == pytest.approx(0.0, abs=0.01)
    assert analysis.z_s is not None and analysis.z_s < 0.0
    assert analysis.I_t == pytest.approx((300.0 * 20.0**3 + 1000.0 * 10.0**3 + 400.0 * 25.0**3) / 3.0, rel=0.05) # Σbt³/3


def test_universal_beam_with_a_cover_plate() -> None:
    ub = UB("457x191x67")
    geometry = section_geometry(ub)
    plate = rectangular_section(d=15.0, b=250.0).align_center(geometry).align_to(geometry, on="top")
    analysis: SectionAnalysis = analyse_section(geometry=geometry + plate, warping=False)
    _, bare = _analysis(UB, "457x191x67")
    assert analysis.A == pytest.approx(bare.A + 15.0 * 250.0, rel=1e-9)
    assert analysis.z_c > bare.z_c # the plate lifts the centroid
    assert analysis.I_y > bare.I_y


def test_skipping_the_warping_analysis() -> None:
    analysis: SectionAnalysis = analyse_section(HFRHS("200x100x8.0"), warping=False)
    assert analysis.I_t is None and analysis.I_w is None and analysis.i_0 is None
    assert "I_t" not in analysis.to_properties("UK")
    assert "ro" not in analysis.to_properties("US") and "H" not in analysis.to_properties("US")
    assert analysis.model is not None # the sectionproperties Section, kept for stress analysis
    assert "model" not in analysis.model_dump()


# --- Engine properties in the regional checks ---
def test_engine_properties_in_the_EU_bending_check() -> None:
    ub, analysis = _analysis(UB, "457x191x67")
    dimensions: dict[str, Any] = {key: ub.get_properties()[key] for key in ("h", "b", "tw", "tf", "r", "d")}
    from_engine = check_bending(section_type=SectionType.UB, properties={**dimensions, **analysis.to_properties("UK")}, fy=355.0)
    from_table = check_bending(ub, fy=355.0)
    assert from_engine.section_class == from_table.section_class
    assert from_engine.M_c_Rd == pytest.approx(from_table.M_c_Rd, rel=0.005)


def test_engine_properties_in_the_BS_bending_check() -> None:
    ub, analysis = _analysis(UB, "457x191x67")
    dimensions: dict[str, Any] = {key: ub.get_properties()[key] for key in ("h", "b", "tw", "tf", "r", "d")}
    from_engine = bs_check_bending(section_type=SectionType.UB, properties={**dimensions, **analysis.to_properties("BS")}, steel_grade="S355")
    from_table = bs_check_bending(ub, steel_grade="S355")
    assert from_engine.Mc == pytest.approx(from_table.Mc, rel=0.005)


# --- Errors ---
def test_plain_properties_need_a_region() -> None:
    with pytest.raises(ValueError):
        analyse_section(section_type=SectionType.UB, properties={"h": 1040.0, "b": 300.0, "tw": 10.0, "tf": 20.0})
    with pytest.raises(ValueError):
        section_geometry(section_type=SectionType.UB, properties={"h": 1040.0}, region="UK") # no b, tw, tf
    with pytest.raises(ValueError):
        section_geometry(properties={"h": 1040.0}, region="UK") # no section type


def test_unknown_region_in_to_properties() -> None:
    _, analysis = _analysis(IPE, "IPE-300")
    with pytest.raises(ValueError):
        analysis.to_properties("MARS")


@pytest.mark.parametrize(("make", "designation"), [(UPN, "UPN-200"), (S_beam, "S12X50"), (L_EQUAL_B2B, "200x200x24")], ids=["UPN", "S", "L_EQUAL_B2B"])
def test_sections_without_geometry(make: Callable[[str], BaseSection], designation: str) -> None:
    with pytest.raises(NotImplementedError):
        section_geometry(make(designation))
