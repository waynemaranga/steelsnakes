"""Where the steel materials of each design code live in `steelsnakes`."""

# NOTE: strengths and elastic constants differ by code, so each code's checks own them; nothing here is shared yet.

# -- UK --
# S355
# S460
# S275 - deprecated/obsolete # FIXME: Probably not? S235 pretty common for ZSF
# Whatever bolts/welds use that's weird.
# BS 5950-1:2000: steelsnakes.BS.checks.classification.design_strength(), Table 9 py by thickness for S275, S355, S460;
# ... E = 205 000 N/mm², G = E/2.6 (3.1.3) in steelsnakes.BS.checks.uls

# -- EU --
# Probably same as UK, but double-check
# EN 1993-1-1: steelsnakes.EU.checks.uls.steel_material() -> SteelMaterial, Table 3.1 fy and fu of the EN 10025,
# ... EN 10210 and EN 10219 grades; E = 210 000 N/mm², G = 81 000 N/mm² (3.2.6); the UK sections use these checks too

# -- US --
# AISC 360-22: Fy and Fu are arguments of each check; E = 29 000 ksi, G = 11 200 ksi in steelsnakes.US.checks.compression
# US_Metric: E = 200 000 MPa, G = 77 200 MPa, FY_A992 = 345 MPa, FU_A992 = 450 MPa in
# ... steelsnakes.US_Metric.checks.classification
