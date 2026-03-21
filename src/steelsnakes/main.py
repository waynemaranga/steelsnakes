from steelsnakes.EU import (
    ElementInput as EUElementInput,
    ElementStressCase,
    IPE,
    StressPattern as EUStressPattern,
    UC,
    classify_section as eu_classify_section,
    classify_section_from_dict as eu_classify_section_from_dict,
)
from steelsnakes.US import (
    ClassificationContext as USClassificationContext,
    CompressionCase,
    FlexureCase,
    classify_compression,
    classify_flexure,
    classify_section as us_classify_section,
)
from steelsnakes.UK import (
    HFCHS,
    HFRHS,
    HFSHS,
    StressPattern as UKStressPattern,
    UB,
    classify_section as uk_classify_section,
    classify_section_from_dict as uk_classify_section_from_dict,
)
from steelsnakes.US.sections.beams import W_beam
from steelsnakes.US.sections.hollow import HSS_RCT
from steelsnakes.US.sections.tees import WT
from steelsnakes.base.sections import SectionType


def _print_eu_result(title: str, result) -> None:
    print(title)
    print(f"  Section class: {result.section_class}")
    print(f"  Governing elements: {', '.join(result.governing_elements)}")
    for element in result.elements:
        print(
            f"  - {element.name}: stress={element.stress}, "
            f"c/t={element.c_over_t:.2f}, class={element.section_class}"
        )
    print()


def _print_us_result(title: str, result) -> None:
    print(title)
    print(f"  Section class: {result.section_class}")
    print(f"  Governing elements: {', '.join(result.governing_elements)}")
    for element in result.elements:
        print(
            f"  - {element.name}: case={element.case.value}, "
            f"lambda={element.wttr:.2f}, class={element.section_class}"
        )
    print()


def main() -> None:
    print("steelsnakes classification examples\n")

    print("EU examples\n")
    beam = IPE("IPE-750x220")
    _print_eu_result("1. IPE section in compression", eu_classify_section(section=beam, fy_mpa=355.0))
    _print_eu_result(
        "2. IPE section in major-axis bending",
        eu_classify_section(section=beam, fy_mpa=355.0, stress_pattern=EUStressPattern.MAJOR_AXIS_BENDING),
    )

    column = UC("356x406x1299")
    _print_eu_result("3. UC section in compression", eu_classify_section(section=column, fy_mpa=355.0))

    combined_result = eu_classify_section(
        fy_mpa=275.0,
        custom_elements=[
            EUElementInput(
                name="web",
                kind="internal",
                c_mm=360.4,
                t_mm=7.7,
                stress=ElementStressCase.COMBINED,
                alpha=0.70,
            ),
            EUElementInput(
                name="flange",
                kind="outstand",
                c_mm=74.8,
                t_mm=10.9,
                stress=ElementStressCase.COMPRESSION,
            ),
        ],
    )
    _print_eu_result("4. Explicit EU combined bending and compression", combined_result)

    dict_result = eu_classify_section_from_dict(
        section_type=SectionType.IPE,
        data={"d": 300.0, "tw": 8.0, "b": 200.0, "tf": 12.0},
        fy_mpa=355.0,
        stress_pattern=EUStressPattern.MAJOR_AXIS_BENDING,
    )
    _print_eu_result("5. Dictionary-based EU I-section classification", dict_result)

    print("UK examples\n")
    uk_beam = UB("457x191x67")
    _print_eu_result("6. UK UB section in compression", uk_classify_section(section=uk_beam, fy_mpa=355.0))
    _print_eu_result("6. UK UB section in major-axis bending", uk_classify_section(section=uk_beam, fy_mpa=355.0, stress_pattern=UKStressPattern.MAJOR_AXIS_BENDING))


    uk_rhs = HFRHS("50x30x3.2")
    _print_eu_result("7. UK HFRHS in compression", uk_classify_section(section=uk_rhs, fy_mpa=355.0))
    _print_eu_result(
        "8. UK HFRHS in major-axis bending",
        uk_classify_section(section=uk_rhs, fy_mpa=355.0, stress_pattern=UKStressPattern.MAJOR_AXIS_BENDING),
    )
    _print_eu_result(
        "9. UK HFRHS in minor-axis bending",
        uk_classify_section(section=uk_rhs, fy_mpa=355.0, stress_pattern=UKStressPattern.MINOR_AXIS_BENDING),
    )

    uk_shs = HFSHS("40x40x3.2")
    _print_eu_result("10. UK HFSHS in compression", uk_classify_section(section=uk_shs, fy_mpa=355.0))

    uk_chs = HFCHS("42.4x3.2")
    _print_eu_result("11. UK HFCHS in compression", uk_classify_section(section=uk_chs, fy_mpa=355.0))

    uk_hollow_dict_result = uk_classify_section_from_dict(
        section_type=SectionType.HFRHS,
        data={"cw_t": 12.6, "cf_t": 6.38, "t": 3.2},
        fy_mpa=355.0,
        stress_pattern=UKStressPattern.MAJOR_AXIS_BENDING,
    )
    _print_eu_result("12. Dictionary-based UK RHS classification", uk_hollow_dict_result)

    print("US examples\n")
    w_shape = W_beam("W36X350")
    _print_us_result("13. W-shape in axial compression", us_classify_section(section=w_shape, Fy_ksi=50.0))
    _print_us_result(
        "14. W-shape in major-axis flexure",
        us_classify_section(
            section=w_shape,
            Fy_ksi=50.0,
            classification_context=USClassificationContext.FLEXURE_MAJOR_AXIS,
        ),
    )
    _print_us_result(
        "15. W-shape in minor-axis flexure",
        us_classify_section(
            section=w_shape,
            Fy_ksi=50.0,
            classification_context=USClassificationContext.FLEXURE_MINOR_AXIS,
        ),
    )

    hss = HSS_RCT("HSS10X6X1/2")
    _print_us_result(
        "16. Rectangular HSS in major-axis flexure",
        us_classify_section(
            section=hss,
            Fy_ksi=46.0,
            classification_context=USClassificationContext.FLEXURE_MAJOR_AXIS,
        ),
    )

    tee = WT("WT22X184")
    _print_us_result(
        "17. WT in major-axis flexure",
        us_classify_section(
            section=tee,
            Fy_ksi=50.0,
            classification_context=USClassificationContext.FLEXURE_MAJOR_AXIS,
        ),
    )

    print("18. Direct case-level US checks")
    print(f"  - {CompressionCase.CASE_1.value}: {classify_compression(CompressionCase.CASE_1, E=29000.0, Fy=50.0, b=6.0, t=0.75).section_class}")
    print(f"  - {FlexureCase.CASE_10.value}: {classify_flexure(FlexureCase.CASE_10, E=29000.0, Fy=50.0, b=6.0, t=0.75).section_class}")
    print()


if __name__ == "__main__":
    # main()
    beam = UB("457x191x67")
    print(beam.get_properties())
    beam_class = uk_classify_section(section=beam, fy_mpa=355.0, stress_pattern=UKStressPattern.COMBINED)
    print(f"Section class: {beam_class.model_dump_json()}")