# EU Steel Sections

European steel sections according to EN 10365:2017 and related European standards.

## Module Overview

::: steelsnakes.EU
    options:
      show_root_heading: false
      show_source: false
      heading_level: 3

## Beam Sections

### IPE Beams

::: steelsnakes.EU.beams
    options:
      show_root_heading: false
      show_source: true
      heading_level: 4
      members: ["IPE"]

### HE Beams

::: steelsnakes.EU.beams
    options:
      show_root_heading: false
      show_source: true
      heading_level: 4
      members: ["HEA", "HEB", "HEM"]

## Column Sections

::: steelsnakes.EU.columns
    options:
      show_root_heading: false
      show_source: true
      heading_level: 3

## Channel Sections

### UPE Channels

::: steelsnakes.EU.channels
    options:
      show_root_heading: false
      show_source: true
      heading_level: 4
      members: ["UPE"]

### UPN Channels

::: steelsnakes.EU.channels
    options:
      show_root_heading: false
      show_source: true
      heading_level: 4
      members: ["UPN"]

## Angle Sections

::: steelsnakes.EU.angles
    options:
      show_root_heading: false
      show_source: true
      heading_level: 3

## Flat Sections

::: steelsnakes.EU.flats
    options:
      show_root_heading: false
      show_source: true
      heading_level: 3

## Pile Sections

::: steelsnakes.EU.piles
    options:
      show_root_heading: false
      show_source: true
      heading_level: 3

## Database and Factory

### EU Database

::: steelsnakes.EU.database.EUSectionDatabase
    options:
      show_root_heading: true
      show_source: true
      heading_level: 4

### EU Factory

::: steelsnakes.EU.factory.EUSectionFactory
    options:
      show_root_heading: true
      show_source: true
      heading_level: 4