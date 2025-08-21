import pathlib # https://www.freecodecamp.org/news/how-to-use-pathlib-module-in-python/
from pathlib import Path # https://realpython.com/python-pathlib/
# https://stackoverflow.com/a/8820636/13807486

DB_DIR: Path = Path.cwd() / "steelsnakesengine/db/"
OBJECTS_PY: Path = DB_DIR / "OBJECTS.py"
JSONS_PY: Path = DB_DIR / "JSONs.py"

# --- SECTIONS ---
SECTION_TYPES: list[str] = [
    "CFCHS", "CFRHS", "CFSHS", # Cold-formed Sections
    "HFCHS", "HFEHS", "HFRHS", "HFSHS", # Hot-finished Sections
    "L_EQUAL", "L_EQUAL_B2B", "L_UNEQUAL", "L_UNEQUAL_B2B", # Angles
    "PFC", # Channels
    "UB", "UBP", "UC", # Universal Sections
    ]

CFCHS_JSON: Path = DB_DIR / "CFCHS.json" # Cold-formed Circular Hollow Sections
CFRHS_JSON: Path = DB_DIR / "CFRHS.json" # Cold-formed Rectangular Hollow Sections
CFSHS_JSON: Path = DB_DIR / "CFSHS.json" # Cold-formed Square Hollow Sections
HFCHS_JSON: Path = DB_DIR / "HFCHS.json" # Hot-finished Circular Hollow Sections
HFEHS_JSON: Path = DB_DIR / "HFEHS.json" # Hot-finished Ellipitical Hollow Sections
HFRHS_JSON: Path = DB_DIR / "HFRHS.json" # Hot-finished Rectangular Hollow Sections
HFSHS_JSON: Path = DB_DIR / "HFSHS.json" # Hot-finished Square Hollow Sections
L_EQUAL_JSON: Path = DB_DIR / "L_EQUAL.json" # Equal Angles
L_EQUAL_B2B_JSON: Path = DB_DIR / "L_EQUAL_B2B.json" # Back-to-Back Equal Angles
L_UNEQUAL_JSON: Path = DB_DIR / "L_UNEQUAL.json" # Unequal Angles
L_UNEQUAL_B2B_JSON: Path = DB_DIR / "L_UNEQUAL_B2B.json" # Back-to-Back Unequal Angles
PFC_JSON: Path = DB_DIR / "PFC.json" # Parallel Flange Channels
UB_JSON: Path = DB_DIR / "UB.json" # Universal Beams
UBP_JSON: Path = DB_DIR / "UBP.json" # Universal Bearing Piles
UC_JSON: Path = DB_DIR / "UC.json" # Universal Columns


# --- BOLTS AND WELDS ---
BOLTS_PRE_88_JSON: Path = DB_DIR / "BOLT_PRE_88.json" # Preloaded Bolts: Grade 8.8
BOLTS_PRE_109_JSON: Path = DB_DIR / "BOLT_PRE_109.json" # Preloaded Bolts: Grade 10.9
# BOLTS_NONPRE_46_JSON: Path = DB_DIR / "BOLT_NONPRE_46.json" # Non-Preloaded Bolts: Grade 4.6
# BOLTS_NONPRE_88_JSON: Path = DB_DIR / "BOLT_NONPRE_88.json" # Non-Preloaded Bolts: Grade 8.8
# BOLTS_NONPRE_109_JSON: Path = DB_DIR / "BOLT_NONPRE_109.json" # Non-Preloaded Bolts: Grade 10.9
WELDS_JSON: Path = DB_DIR / "WELDS.json" # Welds

JSON_DICT: dict[str, Path] = {
    "CFCHS": CFCHS_JSON,
    "CFRHS": CFRHS_JSON,
    "CFSHS": CFSHS_JSON,
    "HFCHS": HFCHS_JSON,
    "HFEHS": HFEHS_JSON,
    "HFRHS": HFRHS_JSON,
    "HFSHS": HFSHS_JSON,
    "L_EQUAL": L_EQUAL_JSON,
    "L_EQUAL_B2B": L_EQUAL_B2B_JSON,
    "L_UNEQUAL": L_UNEQUAL_JSON,
    "L_UNEQUAL_B2B": L_UNEQUAL_B2B_JSON,
    "PFC": PFC_JSON,
    "UB": UB_JSON,
    "UBP": UBP_JSON,
    "UC": UC_JSON,
    "BOLTS_PRE_108": BOLTS_PRE_88_JSON,
    "BOLTS_PRE_109": BOLTS_PRE_109_JSON,
    # "BOLTS_NONPRE_46": BOLTS_NONPRE_46_JSON,
    # "BOLTS_NONPRE_88": BOLTS_NONPRE_88_JSON,
    # "BOLTS_NONPRE_109": BOLTS_NONPRE_109_JSON,
    "WELDS": WELDS_JSON,

}

JSON_LIST: list[Path] = [
    CFCHS_JSON, CFRHS_JSON, CFSHS_JSON, #
    HFCHS_JSON, HFEHS_JSON, HFRHS_JSON, HFSHS_JSON, #
    L_EQUAL_JSON, L_EQUAL_B2B_JSON, L_UNEQUAL_JSON, L_UNEQUAL_B2B_JSON, #
    PFC_JSON, # 
    UB_JSON, UBP_JSON, UC_JSON, # 
    BOLTS_PRE_88_JSON, BOLTS_PRE_109_JSON, #
    # BOLTS_NONPRE_46_JSON, BOLTS_NONPRE_88_JSON, BOLTS_NONPRE_109_JSON, #
    WELDS_JSON # 
    
]

class JSON_OBJECT:
    def __init__(self, section_type: str) -> None:
        self.section_type: str | None = section_type if section_type in SECTION_TYPES else None

if __name__ == "__main__":
    assert DB_DIR.exists() 
    assert DB_DIR.is_dir()
    # assert 0 
    # print([file.name for file in DB_DIR.iterdir()])

    # assert []
    assert [file.exists() for file in JSON_LIST]
    assert [value.exists() for key, value in JSON_DICT.items()]

    print("\n😁", end="\n")