# TODO: Units, Units, Unts
# --- SI ---
# Create a system of units (pun-intended), have aliases, representations descriptions etc
# Use pint or forallpeople and strict validation
# Use the same units intereface to bridge sections accross regions

m: dict[str, str | list[str]] = {"symbol":"m", "variable": "m","aliases": ["m", "metre", "metres"], }
kg = {"symbol":"kg", "variable": "kg","aliases": ["kg", "kgs", "kilogram", "kilograms", "kilogramme", "kilogrammes"]}
mm = ["millimetre", "mm"]
inch = ["inch", "in"] # because `in` is a python keyword
mm2 = ["square millimetre", "mm2"]