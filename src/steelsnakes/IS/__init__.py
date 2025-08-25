# STAAD Pro - https://docs.bentley.com/LiveContent/web/STAAD.Pro%20Help-v18/ja/GUID-65D44A75-31B7-48EB-9375-0530F08CDA48.html
# TODO: Check against IS 808:2021 clause 5.1 & 5.2, and 6
# TODO: Have sections according to code without data :)

# --- Beams --- IS 808:2021 clause 5.1.1
# ISJB - Junior beam
# ISLB - Light beam
# ISMB - Medium weight beam
# ISWB - Wide flange beam
# ISNPB - Narrow parallel flange beam
# ISWBP - Wide parallel flange beam

# --- Columns/Heavy Beams --- IS 808:2021 clause 5.1.2
# ISSC - Column sections
# ISHB - Heavy weight beam

# --- Channels ---
# ISJC - Junior channel
# ISLC - Light channel
# ISMC - Medium weight channel
# ISMPC - Medium weight parallel flange channel

# --- Angles ---
# ISEA - Equal angle # TODO: cross-reference with Indian standards, check equal v unequal angles
# ISUA - Unequal angle
# However, IS 808:2021 only denotes ISA for both; so, # TODO: differentiate between database implementation and naming conventions

# --- Pile sections ---
# ISPBP - Bearing pile

# THE FOLLOWING NOT in IS 808:2021 i.e 
# HOT ROLLED STEEL BEAM, COLUMN,CHANNEL AND ANGLE SECTIONS DIMENSIONS AND PROPERTIES 

# --- T-sections ---
# ISJT - Junior tees/tee-bars
# ISLT - Light tees
# ISMT - Medium weight tees
# ISNT - Normal tees
# ISHT - Wide flange tees
# ISST - Long-legged tees
# ISDT - Deep-legged tees

# --- Rolled steel bars ---
# ISSQ - Square bars
# ISSR - Round bars

# --- Rolled steel tubular sections ---
# 

# --- Rolled steel plates ---
# ISPL - Steel plates

# --- Rolled steel strips ---
# ISST - Steel strips

# --- Rolled steel flats ---
# ISFI - Steel flats

__all__ = [
    # Will be populated when Indian sections are implemented
]
