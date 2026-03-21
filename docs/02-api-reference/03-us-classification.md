# US Classification

This page documents the current AISC local-buckling classification API in `steelsnakes.US`.

## Cross-Code Naming Note

`StressPattern` is intentionally kept as a shared public name across regions so callers can reuse a familiar API shape.

Its meaning is not identical in every code:

- In **EU / EC3**, `StressPattern` is closer to an element stress-case selector.
- In **US / AISC B4.1**, `StressPattern` is better understood as the **classification context** that determines which compression element and which table case apply.

For US code, `StressPattern` is therefore an alias of `ClassificationContext`.

## Shared Principle

The order of reasoning differs slightly by code, but the underlying idea is the same:

- In **EU**, the implementation starts from the section elements and then applies the relevant force or stress case to each element.
- In **US**, the implementation starts from the member action or classification context and then selects which element and which Table B4.1 case are active.

In both codes, the core principle is still:

1. identify the relevant plate element in compression
2. identify the correct code-specific classification rule for that element
3. classify the element
4. let the governing element determine the section classification

## Scope Notes

Some AISC cases are intentionally available through the direct case API before they are auto-wired to a section adapter:

- cover-plate cases such as `CompressionCase.CASE_7` and `FlexureCase.CASE_18`
- built-up or singly symmetric cases that need extra metadata
- fabricated box-section cases that do not yet have their own section family in the library

## Case Enums

US users can now work with either:

- string values such as `"case1"` and `"case10"`
- enum values such as `CompressionCase.CASE_1` and `FlexureCase.CASE_10`

Each enum exposes:

- `.value` for the string form used by the functions
- `.label` as a readable alias of that string
- `.description` as a short guide to the corresponding AISC Table B4.1 case

## API Reference

::: steelsnakes.US.checks.classification.StressPattern

::: steelsnakes.US.checks.classification.ClassificationContext

::: steelsnakes.US.checks.classification.CompressionCase

::: steelsnakes.US.checks.classification.FlexureCase

::: steelsnakes.US.checks.classification.ElementInput

::: steelsnakes.US.checks.classification.ElementClassification

::: steelsnakes.US.checks.classification.ClassificationResult

::: steelsnakes.US.checks.classification.classify_compression

::: steelsnakes.US.checks.classification.classify_flexure

::: steelsnakes.US.checks.classification.classify_element

::: steelsnakes.US.checks.classification.classify_elements

::: steelsnakes.US.checks.classification.classify_section

::: steelsnakes.US.checks.classification.classify_section_from_dict
