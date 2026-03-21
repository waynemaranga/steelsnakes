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

    print("US examples\n")
    w_shape = W_beam("W36X350")
    _print_us_result("6. W-shape in axial compression", us_classify_section(section=w_shape, Fy_ksi=50.0))
    _print_us_result(
        "7. W-shape in major-axis flexure",
        us_classify_section(
            section=w_shape,
            Fy_ksi=50.0,
            classification_context=USClassificationContext.FLEXURE_MAJOR_AXIS,
        ),
    )
    _print_us_result(
        "8. W-shape in minor-axis flexure",
        us_classify_section(
            section=w_shape,
            Fy_ksi=50.0,
            classification_context=USClassificationContext.FLEXURE_MINOR_AXIS,
        ),
    )

    hss = HSS_RCT("HSS10X6X1/2")
    _print_us_result(
        "9. Rectangular HSS in major-axis flexure",
        us_classify_section(
            section=hss,
            Fy_ksi=46.0,
            classification_context=USClassificationContext.FLEXURE_MAJOR_AXIS,
        ),
    )

    tee = WT("WT22X184")
    _print_us_result(
        "10. WT in major-axis flexure",
        us_classify_section(
            section=tee,
            Fy_ksi=50.0,
            classification_context=USClassificationContext.FLEXURE_MAJOR_AXIS,
        ),
    )

    print("11. Direct case-level US checks")
    print(f"  - {CompressionCase.CASE_1.value}: {classify_compression(CompressionCase.CASE_1, E=29000.0, Fy=50.0, b=6.0, t=0.75).section_class}")
    print(f"  - {FlexureCase.CASE_10.value}: {classify_flexure(FlexureCase.CASE_10, E=29000.0, Fy=50.0, b=6.0, t=0.75).section_class}")
    print()


if __name__ == "__main__":
    main()
