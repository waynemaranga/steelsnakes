# Database System

Steel section data management and storage infrastructure.

## SectionDatabase

::: steelsnakes.base.database.SectionDatabase
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

## SQLiteJSONInterface

::: steelsnakes.base.database.SQLiteJSONInterface
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

## Database Builder Function

::: steelsnakes.base.database.build_regional_sqlite_db
    options:
      show_root_heading: true
      show_source: true
      heading_level: 3

## Regional Database Implementations

### UK Database

::: steelsnakes.UK.database.UKSectionDatabase
    options:
      show_root_heading: true
      show_source: true
      heading_level: 4

::: steelsnakes.UK.database.get_uk_database
    options:
      show_root_heading: true
      show_source: true
      heading_level: 4

### US Database

::: steelsnakes.US.database.USSectionDatabase
    options:
      show_root_heading: true
      show_source: true
      heading_level: 4

::: steelsnakes.US.database.get_US_database
    options:
      show_root_heading: true
      show_source: true
      heading_level: 4