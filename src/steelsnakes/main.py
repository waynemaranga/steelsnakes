from steelsnakes.EU import (
    ElementInput,
    ElementStressCase,
    StressPattern,
    classify_section,
    classify_section_from_dict,
    IPE,
    UC,
)
from steelsnakes.base.sections import SectionType


def _print_result(title: str, result) -> None:
    print(title)
    print(f"  Section class: {result.section_class}")
    print(f"  Governing elements: {', '.join(result.governing_elements)}")
    for element in result.elements:
        print(
            f"  - {element.name}: stress={element.stress}, "
            f"c/t={element.c_over_t:.2f}, class={element.section_class}"
        )
    print()


def main() -> None:
    print("steelsnakes EU classification examples\n")

    beam = IPE("IPE-750x220")
    beam_compression = classify_section(section=beam, fy_mpa=355.0)
    _print_result("1. IPE section in compression", beam_compression)

    beam_bending = classify_section(
        section=beam,
        fy_mpa=355.0,
        stress_pattern="bending-major-axis",
    )
    _print_result("2. IPE section in major-axis bending", beam_bending)

    column = UC("356x406x1299")
    column_compression = classify_section(section=column, fy_mpa=355.0)
    _print_result("3. UC section in compression", column_compression)

    combined_result = classify_section(
        fy_mpa=275.0,
        custom_elements=[
            ElementInput(
                name="web",
                kind="internal",
                c_mm=360.4,
                t_mm=7.7,
                stress=ElementStressCase.COMBINED,
                alpha=0.70,
            ),
            ElementInput(
                name="flange",
                kind="outstand",
                c_mm=74.8,
                t_mm=10.9,
                stress=ElementStressCase.COMPRESSION,
            ),
        ],
    )
    _print_result("4. Explicit combined bending and compression", combined_result)

    dict_result = classify_section_from_dict(
        section_type=SectionType.IPE,
        data={"d": 300.0, "tw": 8.0, "b": 200.0, "tf": 12.0},
        fy_mpa=355.0,
        stress_pattern=StressPattern.MAJOR_AXIS_BENDING,
    )
    _print_result("5. Dictionary-based I-section classification", dict_result)


if __name__ == "__main__":
    main()
