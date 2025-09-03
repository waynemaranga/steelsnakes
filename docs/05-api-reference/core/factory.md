# Factory Pattern

Unified section creation interface across all regions.

## SectionFactory

::: steelsnakes.base.factory.SectionFactory
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

## Regional Factory Implementations

### UK Factory

::: steelsnakes.UK.factory.UKSectionFactory
    options:
      show_root_heading: true
      show_source: true
      heading_level: 4

::: steelsnakes.UK.factory.get_UK_factory
    options:
      show_root_heading: true
      show_source: true
      heading_level: 4

### US Factory

::: steelsnakes.US.factory.USSectionFactory
    options:
      show_root_heading: true
      show_source: true
      heading_level: 4

::: steelsnakes.US.factory.get_US_factory
    options:
      show_root_heading: true
      show_source: true
      heading_level: 4

## Exception Handling

::: steelsnakes.base.exceptions.SectionFactoryError
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

::: steelsnakes.base.exceptions.SectionNotFoundError
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

::: steelsnakes.base.exceptions.SectionTypeNotRegisteredError
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3