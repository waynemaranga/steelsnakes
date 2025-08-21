import json
from JSONs import CFCHS_JSON, CFRHS_JSON, CFSHS_JSON, HFCHS_JSON, HFEHS_JSON, HFRHS_JSON, HFSHS_JSON, L_EQUAL_JSON, L_UNEQUAL_JSON, L_EQUAL_B2B_JSON, L_UNEQUAL_B2B_JSON, PFC_JSON, UB_JSON, UBP_JSON, UC_JSON
from JSONs import BOLTS_PRE_88_JSON, BOLTS_PRE_109_JSON
# from JSONs import BOLTS_NONPRE_46_JSON, BOLTS_NONPRE_88_JSON, BOLTS_NONPRE_109_JSON
from JSONs import WELDS_JSON

# --- Cold-formed Circular Hollow Sections
with open(file=CFCHS_JSON, mode="r") as file_:
    global CFCHS_SECTION_LIST
    CFCHS_JSON_OBJECT = json.load(fp=file_)
    CFCHS_SECTION_LIST: list[str] = [section for section in CFCHS_JSON_OBJECT.keys()]
    #// CFCHS_SECTION_LIST: set[str] = {section for section in CFCHS_JSON_OBJECT.keys()}
    # CFCHS_SECTION_SET: OrderedSet[str] = OrderedSet(section for section in CFCHS_JSON_OBJECT.keys())
    # CFCHS_SECTION_TUPLE: tuple[str] = tuple([section for section in CFCHS_JSON_OBJECT.keys()])

# --- Cold-formed Rectangular Hollow Sections
with open(file=CFRHS_JSON, mode="r") as file_:
    global CFRHS_SECTION_LIST
    CFRHS_JSON_OBJECT = json.load(fp=file_)
    CFRHS_SECTION_LIST: list[str] = [section for section in CFRHS_JSON_OBJECT.keys()]
    #// CFRHS_SECTION_LIST: set[str] = {section for section in CFRHS_JSON_OBJECT.keys()}
    # CFRHS_SECTION_SET: OrderedSet[str] = OrderedSet(section for section in CFRHS_JSON_OBJECT.keys())
    # CFRHS_SECTION_TUPLE: tuple[str] = tuple([section for section in CFRHS_JSON_OBJECT.keys()])

# --- Cold-formed Square Hollow Sections
with open(file=CFSHS_JSON, mode="r") as file_:
    global CFSHS_SECTION_LIST
    CFSHS_JSON_OBJECT = json.load(fp=file_)
    CFSHS_SECTION_LIST: list[str] = [section for section in CFSHS_JSON_OBJECT.keys()]
    #// CFSHS_SECTION_LIST: set[str] = {section for section in CFSHS_JSON_OBJECT.keys()}
    # CFSHS_SECTION_SET: OrderedSet[str] = OrderedSet(section for section in CFSHS_JSON_OBJECT.keys())
    # CFSHS_SECTION_TUPLE: tuple[str] = tuple([section for section in CFSHS_JSON_OBJECT.keys()])

# --- Hot-formed Circular Hollow Sections
with open(file=HFCHS_JSON, mode="r") as file_:
    global HFCHS_SECTION_LIST
    HFCHS_JSON_OBJECT = json.load(fp=file_)
    HFCHS_SECTION_LIST: list[str] = [section for section in HFCHS_JSON_OBJECT.keys()]
    #// HFCHS_SECTION_LIST: set[str] = {section for section in HFCHS_JSON_OBJECT.keys()}
    # HFCHS_SECTION_SET: OrderedSet[str] = OrderedSet(section for section in HFCHS_JSON_OBJECT.keys())
    # HFCHS_SECTION_TUPLE: tuple[str] = tuple([section for section in HFCHS_JSON_OBJECT.keys()])

# --- Hot-formed Elliptical Hollow Sections
with open(file=HFEHS_JSON, mode="r") as file_:
    global HFEHS_SECTION_LIST
    HFEHS_JSON_OBJECT = json.load(fp=file_)
    HFEHS_SECTION_LIST: list[str] = [section for section in HFEHS_JSON_OBJECT.keys()]
    #// HFEHS_SECTION_LIST: set[str] = {section for section in HFEHS_JSON_OBJECT.keys()}
    # HFEHS_SECTION_SET: OrderedSet[str] = OrderedSet(section for section in HFEHS_JSON_OBJECT.keys())
    # HFEHS_SECTION_TUPLE: tuple[str] = tuple([section for section in HFEHS_JSON_OBJECT.keys()])

# --- Hot-formed Rectangular Hollow Sections
with open(file=HFRHS_JSON, mode="r") as file_:
    global HFRHS_SECTION_LIST
    HFRHS_JSON_OBJECT = json.load(fp=file_)
    HFRHS_SECTION_LIST: list[str] = [section for section in HFRHS_JSON_OBJECT.keys()]
    #// HFRHS_SECTION_LIST: set[str] = {section for section in HFRHS_JSON_OBJECT.keys()}
    # HFRHS_SECTION_SET: OrderedSet[str] = OrderedSet(section for section in HFRHS_JSON_OBJECT.keys())
    # HFRHS_SECTION_TUPLE: tuple[str] = tuple([section for section in HFRHS_JSON_OBJECT.keys()])

# --- Hot-formed Square Hollow Sections
with open(file=HFSHS_JSON, mode="r") as file_:
    global HFSHS_SECTION_LIST
    HFSHS_JSON_OBJECT = json.load(fp=file_)
    HFSHS_SECTION_LIST: list[str] = [section for section in HFSHS_JSON_OBJECT.keys()]
    #// HFSHS_SECTION_LIST: set[str] = {section for section in HFSHS_JSON_OBJECT.keys()}
    # HFSHS_SECTION_SET: OrderedSet[str] = OrderedSet(section for section in HFSHS_JSON_OBJECT.keys())
    # HFSHS_SECTION_TUPLE: tuple[str] = tuple([section for section in HFSHS_JSON_OBJECT.keys()])

# --- Equal Angles
with open(file=L_EQUAL_JSON, mode="r") as file_:
    global L_EQUAL_SECTION_LIST
    L_EQUAL_JSON_OBJECT = json.load(fp=file_)
    L_EQUAL_SECTION_LIST: list[str] = [section for section in L_EQUAL_JSON_OBJECT.keys()]
    #// L_EQUAL_SECTION_LIST: set[str] = {section for section in L_EQUAL_JSON_OBJECT.keys()}
    # L_EQUAL_SECTION_SET: OrderedSet[str] = OrderedSet(section for section in L_EQUAL_JSON_OBJECT.keys())
    # L_EQUAL_SECTION_TUPLE: tuple[str] = tuple([section for section in L_EQUAL_JSON_OBJECT.keys()])

# --- Unequal Angles
with open(file=L_UNEQUAL_JSON, mode="r") as file_:
    global L_UNEQUAL_SECTION_LIST
    L_UNEQUAL_JSON_OBJECT = json.load(fp=file_)
    L_UNEQUAL_SECTION_LIST: list[str] = [section for section in L_UNEQUAL_JSON_OBJECT.keys()]
    #// L_UNEQUAL_SECTION_LIST: set[str] = {section for section in L_UNEQUAL_JSON_OBJECT.keys()}
    # L_UNEQUAL_SECTION_SET: OrderedSet[str] = OrderedSet(section for section in L_UNEQUAL_JSON_OBJECT.keys())
    # L_UNEQUAL_SECTION_TUPLE: tuple[str] = tuple([section for section in L_UNEQUAL_JSON_OBJECT.keys()])

# --- Back-to-Back Equal Angles
with open(file=L_UNEQUAL_B2B_JSON, mode="r") as file_:
    global L_UNEQUAL_B2B_SECTION_LIST
    L_UNEQUAL_B2B_JSON_OBJECT = json.load(fp=file_)
    L_UNEQUAL_B2B_SECTION_LIST: list[str] = [section for section in L_UNEQUAL_B2B_JSON_OBJECT.keys()]
    #// L_UNEQUAL_B2B_SECTION_LIST: set[str] = {section for section in L_UNEQUAL_B2B_JSON_OBJECT.keys()}
    # L_UNEQUAL_B2B_SECTION_SET: OrderedSet[str] = OrderedSet(section for section in L_UNEQUAL_B2B_JSON_OBJECT.keys())
    # L_UNEQUAL_B2B_SECTION_TUPLE: tuple[str] = tuple([section for section in L_UNEQUAL_B2B_JSON_OBJECT.keys()])

# --- Back-to-Back Unequal Angles
with open(file=L_EQUAL_B2B_JSON, mode="r") as file_:
    global L_EQUAL_B2B_SECTION_LIST
    L_EQUAL_B2B_JSON_OBJECT = json.load(fp=file_)
    L_EQUAL_B2B_SECTION_LIST: list[str] = [section for section in L_EQUAL_B2B_JSON_OBJECT.keys()]
    #// L_EQUAL_B2B_SECTION_LIST: set[str] = {section for section in L_EQUAL_B2B_JSON_OBJECT.keys()}
    # L_EQUAL_B2B_SECTION_SET: OrderedSet[str] = OrderedSet(section for section in L_EQUAL_B2B_JSON_OBJECT.keys())
    # L_EQUAL_B2B_SECTION_TUPLE: tuple[str] = tuple([section for section in L_EQUAL_B2B_JSON_OBJECT.keys()])

# --- Parallel Flange Channels
with open(file=PFC_JSON, mode="r") as file_:
    global PFC_SECTION_LIST
    PFC_JSON_OBJECT = json.load(fp=file_)
    PFC_SECTION_LIST: list[str] = [section for section in PFC_JSON_OBJECT.keys()]
    #// PFC_SECTION_LIST: set[str] = {section for section in PFC_JSON_OBJECT.keys()}
    # PFC_SECTION_SET: OrderedSet[str] = OrderedSet(section for section in PFC_JSON_OBJECT.keys())
    # PFC_SECTION_TUPLE: tuple[str] = tuple([section for section in PFC_JSON_OBJECT.keys()])

# --- Universal Beams
with open(file=UB_JSON, mode="r") as file_:
    global UB_SECTION_LIST
    UB_JSON_OBJECT = json.load(fp=file_)
    UB_SECTION_LIST: list[str] = [section for section in UB_JSON_OBJECT.keys()]
    #// UB_SECTION_LIST: set[str] = {section for section in UB_JSON_OBJECT.keys()}
    # UB_SECTION_SET: OrderedSet[str] = OrderedSet(section for section in UB_JSON_OBJECT.keys())
    # UB_SECTION_TUPLE: tuple[str] = tuple([section for section in UB_JSON_OBJECT.keys()])

# --- Universal Bearing Piles
with open(file=UBP_JSON, mode="r") as file_:
    global UBP_SECTION_LIST
    UBP_JSON_OBJECT = json.load(fp=file_)
    UBP_SECTION_LIST: list[str] = [section for section in UBP_JSON_OBJECT.keys()]
    #// UBP_SECTION_LIST: set[str] = {section for section in UBP_JSON_OBJECT.keys()}
    # UBP_SECTION_SET: OrderedSet[str] = OrderedSet(section for section in UBP_JSON_OBJECT.keys())
    # UBP_SECTION_TUPLE: tuple[str] = tuple([section for section in UBP_JSON_OBJECT.keys()])

# --- Universal Columns
with open(file=UC_JSON, mode="r") as file_:
    global UC_SECTION_LIST
    UC_JSON_OBJECT = json.load(fp=file_)
    UC_SECTION_LIST: list[str] = [section for section in UC_JSON_OBJECT.keys()]
    #// UC_SECTION_LIST: set[str] = {section for section in UC_JSON_OBJECT.keys()}
    # UC_SECTION_SET: OrderedSet[str] = OrderedSet(section for section in UC_JSON_OBJECT.keys())
    # UC_SECTION_TUPLE: tuple[str] = tuple([section for section in UC_JSON_OBJECT.keys()])

# --- Preloaded Bolts: Grade 8.8
# with open(file=BOLTS_PRE_88_JSON, mode="r") as file_:
#     global BOLTS_PRE_88_LIST
#     BOLTS_PRE_88_JSON_OBJECT = json.load(fp=file_)
#     BOLTS_PRE_88_LIST: list[str] = [bolt for bolt in BOLTS_PRE_88_JSON_OBJECT.keys()]
#     #// BOLTS_PRE_88_LIST: set[str] = {bolt for bolt in BOLTS_PRE_88_JSON_OBJECT.keys()}
#     # BOLTS_PRE_88_SET: OrderedSet[str] = OrderedSet(bolt for bolt in BOLTS_PRE_88_JSON_OBJECT.keys())
#     # BOLTS_PRE_88_TUPLE: tuple[str] = tuple([bolt for bolt in BOLTS_PRE_88_JSON_OBJECT.keys()])

# --- Preloaded Bolts: Grade 10.9
# with open(file=BOLTS_PRE_109_JSON, mode="r") as file_:
#     global BOLTS_PRE_109_LIST
#     BOLTS_PRE_109_JSON_OBJECT = json.load(fp=file_)
#     BOLTS_PRE_109_LIST: list[str] = [bolt for bolt in BOLTS_PRE_109_JSON_OBJECT.keys()]
#     #// BOLTS_PRE_109_LIST: set[str] = {bolt for bolt in BOLTS_PRE_109_JSON_OBJECT.keys()}
#     # BOLTS_PRE_109_SET: OrderedSet[str] = OrderedSet(bolt for bolt in BOLTS_PRE_109_JSON_OBJECT.keys())
#     # BOLTS_PRE_109_TUPLE: tuple[str] = tuple([bolt for bolt in BOLTS_PRE_109_JSON_OBJECT.keys()])

# --- Non-Preloaded Bolts: Grade 4.6
# with open(file=BOLTS_NONPRE_46_JSON, mode="r") as file_:
#     global BOLTS_NONPRE_46_LIST
#     BOLTS_NONPRE_46_JSON_OBJECT = json.load(fp=file_)
#     BOLTS_NONPRE_46_LIST: list[str] = [bolt for bolt in BOLTS_NONPRE_46_JSON_OBJECT.keys()]
#     #// BOLTS_NONPRE_46_LIST: set[str] = {bolt for bolt in BOLTS_NONPRE_46_JSON_OBJECT.keys()}
#     # BOLTS_NONPRE_46_SET: OrderedSet[str] = OrderedSet(bolt for bolt in BOLTS_NONPRE_46_JSON_OBJECT.keys())
#     # BOLTS_NONPRE_46_TUPLE: tuple[str] = tuple([bolt for bolt in BOLTS_NONPRE_46_JSON_OBJECT.keys()])

# --- Non-Preloaded Bolts: Grade 8.8
# with open(file=BOLTS_NONPRE_88_JSON, mode="r") as file_:
#     global BOLTS_NONPRE_88_LIST
#     BOLTS_NONPRE_88_JSON_OBJECT = json.load(fp=file_)
#     BOLTS_NONPRE_88_LIST: list[str] = [bolt for bolt in BOLTS_NONPRE_88_JSON_OBJECT.keys()]
#     #// BOLTS_NONPRE_88_LIST: set[str] = {bolt for bolt in BOLTS_NONPRE_88_JSON_OBJECT.keys()}
#     # BOLTS_NONPRE_88_SET: OrderedSet[str] = OrderedSet(bolt for bolt in BOLTS_NONPRE_88_JSON_OBJECT.keys())
#     # BOLTS_NONPRE_88_TUPLE: tuple[str] = tuple([bolt for bolt in BOLTS_NONPRE_88_JSON_OBJECT.keys()])

# --- Non-Preloaded Bolts: Grade 10.9
# with open(file=BOLTS_NONPRE_109_JSON, mode="r") as file_:
#     global BOLTS_NONPRE_109_LIST
#     BOLTS_NONPRE_109_JSON_OBJECT = json.load(fp=file_)
#     BOLTS_NONPRE_109_LIST: list[str] = [bolt for bolt in BOLTS_NONPRE_109_JSON_OBJECT.keys()]
#     #// BOLTS_NONPRE_109_LIST: set[str] = {bolt for bolt in BOLTS_NONPRE_109_JSON_OBJECT.keys()}
#     # BOLTS_NONPRE_109_SET: OrderedSet[str] = OrderedSet(bolt for bolt in BOLTS_NONPRE_109_JSON_OBJECT.keys())
#     # BOLTS_NONPRE_109_TUPLE: tuple[str] = tuple([bolt for bolt in BOLTS_NONPRE_109_JSON_OBJECT.keys()])

# --- Welds
with open(file=WELDS_JSON, mode="r") as file_:
    global WELDS_LIST
    WELDS_JSON_OBJECT = json.load(fp=file_)
    WELDS_LIST: list[str] = [weld for weld in WELDS_JSON_OBJECT.keys()]
    #// WELDS_LIST: set[str] = {weld for weld in WELDS_JSON_OBJECT.keys()}
    # WELDS_SET: OrderedSet[str] = OrderedSet(weld for weld in WELDS_JSON_OBJECT.keys())
    # WELDS_TUPLE: tuple[str] = tuple([weld for weld in WELDS_JSON_OBJECT.keys()])





if __name__ == "__main__":
    # print(CFCHS_SECTION_LIST)
    # print(CFSHS_SECTION_LIST)
    # print(CFRHS_SECTION_LIST)
    # print(HFCHS_SECTION_LIST)
    # print(HFEHS_SECTION_LIST)
    # print(HFRHS_SECTION_LIST)
    # print(HFSHS_SECTION_LIST)
    # print(L_EQUAL_SECTION_LIST)
    # print(L_UNEQUAL_SECTION_LIST)
    # print(L_EQUAL_B2B_SECTION_LIST)    
    # print(L_UNEQUAL_B2B_SECTION_LIST)    
    # print(PFC_SECTION_LIST)
    # print(UB_SECTION_LIST)
    # print(UBP_SECTION_LIST)
    # print(UC_SECTION_LIST)

    # print(BOLTS_PRE_88_LIST)
    # print(BOLTS_PRE_109_LIST)
    # print(BOLTS_NONPRE_46_LIST)
    # print(BOLTS_NONPRE_88_LIST)
    # print(BOLTS_NONPRE_109_LIST)
    print(WELDS_LIST)

    print("\n😁", end="\n")