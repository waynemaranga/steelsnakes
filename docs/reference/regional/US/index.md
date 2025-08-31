# US Steel Sections

US steel sections conforming to AISC standards. This module provides access to American steel section data and specifications.

::: steelsnakes.US.beams
    options:
        show_root_heading: true
        show_source: true
        heading_level: 3
        members_order: source
        show_bases: true

<!-- ::: steelsnakes.US.channels
    options:
        show_root_heading: true
        show_source: true
        heading_level: 3
        members_order: source
        show_bases: true -->

!!! info "Development Status"
    US steel sections are currently under development. More comprehensive documentation will be available in future releases.


## Table of Contents

- [US Steel Sections](#us-steel-sections)
  - [Table of Contents](#table-of-contents)
  - [Section Types](#section-types)
    - [Beams - `W`, `S`, `M`, `HP`](#beams---w-s-m-hp)
    - [Channels - `C`, `MC`](#channels---c-mc)
    - [Double Channels - `C2C`, `MC2MC`](#double-channels---c2c-mc2mc)
    - [Angles - `L`](#angles---l)
    - [Double Angles - `L2L`](#double-angles---l2l)
    - [Structural Tees - `WT`, `ST`, `MT`](#structural-tees---wt-st-mt)
    - [Hollow Structural Sections - `HSS`](#hollow-structural-sections---hss)
    - [Pipes - `PIPE`](#pipes---pipe)
  - [Dimensions and Properties](#dimensions-and-properties)

## Section Types
###  Beams - `W`, `S`, `M`, `HP`

- `W` - Wide-Flange Beams, with parallel inner and outer flanges
- `S` - Standard Beams, with sloped inner flanges
- `M` - Miscellaneous Beams, not classified as W, S or HP; may have sloped inside flange faces; don't meet criteria for W, S, or HP shapes
- `HP` - Bearing Piles, like W shapes but webs and flanges are of equal thickness and depth and flange width are equal for given designation <!-- TODO: check this out -->

### Channels - `C`, `MC`

- `C` - Standard Channels, with sloped inner flange surfaces
- `MC` - Miscellaneous Channels, not classified as C shapes; have slopes other than 16 2/3% on inner flange surfaces;

### Double Channels - `C2C`, `MC2MC`

- Double channels (also known as 2C- and 2MC-shapes) are made with two channels that are interconnected through their back-to-back webs along the length of the member, either in contact for the fulllength or separated by spacers at the points of interconnection.

### Angles - `L`

- `L` - Equal and Unequal Leg Angles; legs of equal thickness and either equal or unequal leg sizes

### Double Angles - `L2L`

- `L2L` - Double angles (also known as 2L-shapes) are made with two angles that are interconnected through their back-to-back legs along the length of the member, either in contact for the full length or separated by spacers at the points of interconnection.

### Structural Tees - `WT`, `ST`, `MT`

- `WT` - cut from `W` shapes
- `ST` - cut from `S` shapes
- `MT` - cut from `M` shapes

### Hollow Structural Sections - `HSS`

- `HSS`, with:
  - Rectangular which have an essentially rectangular cross-section, except for rounded corners, and uniform wall thickness, except at the weld seam(s).
  - Square, which have an essentially square cross-section, except for rounded corners, and uniform wall thickness, except at the weld seam(s)
  - Round which have an essentially round cross-section and uniform wall thickness, except at the weld seam(s).

### Pipes - `PIPE`

- `PIPE` - Pipes have an essentially round cross-section and uniform thickness, except at the weld seam(s) for welded pipe.

## Dimensions and Properties

| N | M |
| -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `W` | Nominal weight, lb/ft (kg/m) |
| `A` | Cross-sectional area, in.2 (mm2) |
| `d` | Overall depth of member, or width of shorter leg for angles, or width of the outstanding legs of long legs back-to-back double angles, or the width of the back-to-back legs of short legs back-to-back double angles, in. (mm) |
| `ddet` | Detailing value of member depth, in. (mm) |
| `Ht` | Overall depth of square HSS or longer wall of rectangular HSS, in. (mm) |
| `h` | Depth of the flat wall of square HSS or longer flat wall of rectangular HSS, in. (mm) |
| `OD` | Outside diameter of round HSS or pipe, in. (mm) |
| `bf` | Width of flange, in. (mm) |
| `bfdet` | Detailing value of flange width, in. (mm) |
| `B` | Overall width of square HSS or shorter wall of rectangular HSS, in. (mm) |
| `b` | Width of the flat wall of square HSS or the shorter flat wall of rectangular HSS, or width of the longer leg for angles, or width of the back-to-back legs of long legs back-to-back double angles, or width of the outstanding legs of short legs back-to-back double angles, in. (mm) |
| `ID` | Inside diameter of pipe, in. (mm) |
| `tw` | Thickness of web, in. (mm) |
| `tw_det` | Detailing value of web thickness, in. (mm) |
| `tw_det_2` | Detailing value of tw/2, in. (mm) |
| `tf` | Thickness of flange, in. (mm) |
| `tf_det` | Detailing value of flange thickness, in. (mm) |
| `t` | Thickness of angle leg, in. (mm) |
| `t_nom` | Nominal thickness of HSS and pipe wall, in. (mm) |
| `t_des` | Design thickness of HSS and pipe wall, in. (mm) |
| `k_des` | Distance from outer face of flange to web toe of fillet used for design, in. (mm) |
| `k_det` | Distance from outer face of flange to web toe of fillet used for detailing, in. (mm) |
| `k1` | Distance from web center line to flange toe of fillet used for detailing, in. (mm) |
| `x` | Horizontal distance from designated edge of member, as defined in the AISC Steel Construction Manual Part 1, to center of gravity of member, in. (mm) |
| `y` | Vertical distance from designated edge of member, as defined in the AISC Steel Construction Manual Part 1, to center of gravity of member, in. (mm) |
| `eo` | Horizontal distance from designated edge of member, as defined in the AISC Steel Construction Manual Part 1, to shear center of member, in. (mm) |
| `xp` | Horizontal distance from designated edge of member, as defined in the AISC Steel Construction Manual Part 1, to plastic neutral axis of member, in. (mm) |
| `yp` | Vertical distance from designated edge of member, as defined in the AISC Steel Construction Manual Part 1, to plastic neutral axis of member, in. (mm) |
| `bf_2tf` | Slenderness ratio for W, M, S, HP, WT, and ST flange |
| `b` | /t Slenderness ratio for angles and channel flange |
| `b` | /tdes Slenderness ratio for square HSS or shorter wall of rectangular HSS |
| `h` | /tw Slenderness ratio for W, M, S, HP, or channel web |
| `h` | /tdes Slenderness ratio for square HSS or longer wall of rectangular HSS |
| `D` | /t Slenderness ratio for round HSS and pipe (D = ID), or tee shapes (D = d) |
| `Ix` | Moment of inertia about the x-axis, in.4 (´106 mm4) |
| `Zx` | Plastic section modulus about the x-axis, in.3 (´103 mm3) |
| `Sx` | Elastic section modulus about the x-axis, in.3 (´103 mm3) |
| `rx` | Radius of gyration about the x-axis, in. (mm) |
| `Iy` | Moment of inertia about the y-axis, in.4 (´106 mm4) |
| `Zy` | Plastic section modulus about the y-axis, in.3 (´103 mm3) |
| `Sy` | Elastic section modulus about the y-axis, in.3 (´103 mm3) |
| `ry` | Radius of gyration about the y-axis (with no separation for double angles back-to-back), in. (mm) |
| `Iz` | Moment of inertia about the z-axis, in.4 (´106 mm4) |
| `rz` | Radius of gyration about the z-axis, in. (mm) |
| `Sz` | Elastic section modulus about the z-axis, in.3 (´103 mm3). For single angles, see SzA, SzB, and SzC. |
| `J` | Torsional constant, in.4 (´103 mm4) |
| `Cw` | Warping constant, in.6 (´109 mm6) |
| `C` | HSS torsional constant, in.3 (´103 mm3) |
| `Wno` | Normalized warping function, as used in Design Guide 9, in.2 (mm2) |
| `Sw1` | Warping statical moment at point 1 on cross section, as used in AISC Design Guide 9 and shown in Figures 1 and 2, in.4 (´106 mm4) |
| `Sw2` | Warping statical moment at point 2 on cross section, as used in AISC Design Guide 9 and shown in Figure 2, in.4 (´106 mm4) |
| `Sw3` | Warping statical moment at point 3 on cross section, as used in AISC Design Guide 9 and shown in Figure 2, in.4 (´106 mm4) |
| `Qf` | Statical moment for a point in the flange directly above the vertical edge of the web, as used in AISC Design Guide 9, in.3 (´103 mm3) |
| `Qw` | Statical moment for a point at mid-depth of the cross section, as used in AISC Design Guide 9, in.3 (´103 mm3) |
| `ro` | Polar radius of gyration about the shear center, in. (mm) |
| `H` | Flexural constant |
| `tan_alpha`| Tangent of the angle between the y-y and z-z axes for single angles, where a is shown in Figure 3 |
| `Iw` | Moment of inertia about the w-axis for single angles, in.4 (´106 mm4) |
| `zA` | Distance from point A to center of gravity along z-axis, as shown in Figure 3, in. (mm) |
| `zB` | Distance from point B to center of gravity along z-axis, as shown in Figure 3, in. (mm) |
| `zC` | Distance from point C to center of gravity along z-axis, as shown in Figure 3, in. (mm) |
| `wA` | Distance from point A to center of gravity along w-axis, as shown in Figure 3, in. (mm) |
| `wB` | Distance from point B to center of gravity along w-axis, as shown in Figure 3, in. (mm) |
| `wC` | Distance from point C to center of gravity along w-axis, as shown in Figure 3, in. (mm) |
| `SwA` | Elastic section modulus about the w-axis at point A on cross section, as shown in Figure 3, in.3 (´103 mm3) |
| `SwB` | Elastic section modulus about the w-axis at point B on cross section, as shown in Figure 3, in.3 (´103 mm3) |
| `SwC` | Elastic section modulus about the w-axis at point C on cross section, as shown in Figure 3, in.3 (´103 mm3) |
| `SzA` | Elastic section modulus about the z-axis at point A on cross section, as shown in Figure 3, in.3 (´103 mm3) |
| `SzB` | Elastic section modulus about the z-axis at point B on cross section, as shown in Figure 3, in.3 (´103 mm3) |
| `SzC` | Elastic section modulus about the z-axis at point C on cross section, as shown in Figure 3, in.3 (´103 mm3) |
| `rts` | Effective radius of gyration, in. (mm) |
| `ho` | Distance between the flange centroids, in. (mm) |
| `PA` | Shape perimeter minus one flange surface (or short leg surface for a single angle), as used in Design Guide 19, in. (mm) |
| `PA2` | Single angle shape perimeter minus long leg surface, as used in AISC Design Guide 19, in. (mm) |
| `PB` | Shape perimeter, as used in AISC Design Guide 19, in. (mm) |
| `PC` | Box perimeter minus one flange surface, as used in Design Guide 19, in. (mm) |
| `PD` | Box perimeter, as used in AISC Design Guide 19, in. (mm) |
| `T` | Distance between web toes of fillets at top and bottom of web, in. (mm) |
| `WGi` | The workable gage for the inner fastener holes in the flange that provides for entering and tightening clearances and edge distance and spacing requirements. The actual size, combination, and orientation of fastener components should be compared with the geometry of the cross section to ensure compatibility. See AISC Manual Part 1 for additional information, in. (mm) |
| `WGo` | The bolt spacing between inner and outer fastener holes when the workable gage is compatible with four holes across the flange. See AISC Manual Part 1 for additional information, in. (mm | ) |
