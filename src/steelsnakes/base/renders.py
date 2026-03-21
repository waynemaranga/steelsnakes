"""
Checks with pre-rendered LaTeX rows.

Design: every check returns a CheckBlock with a list of Row objects.
LaTeX is substituted in Python; the Jinja template just emits {{ row.expr | safe }}.

Template loop:
    {% for block in blocks %}
      <div class="sec-head">{{ block.title }} <span>{{ block.subtitle }}</span></div>
      {% for row in block.rows %}
      <div class="calc-block">
        <div class="ref">{{ row.clause }}</div>
        <div class="calc">{{ row.expr | safe }}</div>
        <div class="out">
          {% if row.value %}{{ row.value }}{% if row.unit %} {{ row.unit }}{% endif %}{% endif %}
          {% if row.badge %}<span class="{{ row.status }}">{{ row.badge }}</span>{% endif %}
        </div>
      </div>
      {% endfor %}
    {% endfor %}

//TODO: Units: forces kN, moments kN.m, lengths mm, stresses N/mm2, moduli cm3, I cm4.
"""

import math
from dataclasses import dataclass
from typing import Any, Optional

from steelsnakes.base.sections import BaseSection

# --- Constants ---
E_STEEL = 205_000.0   # Young's Modulus N/mm2
G_STEEL = 80_000.0    # Shear Modulus N/mm2

# --- Rendering primitives ---
@dataclass
class Row:
    """One line in the calculation sheet."""
    expr:   str        # HTML + inline LaTeX, values already substituted
    value:  str = ""   # formatted result for the out column
    unit:   str = ""   # unit label
    clause: str = ""   # clause reference for the ref column
    status: str = ""   # "pass" | "fail" | "note" | ""
    badge:  str = ""   # plain text label e.g. "PASS", "Plastic"

@dataclass
class CheckBlock:
    """A titled group of rows — one per clause / sub-check."""
    title:    str
    subtitle: str
    rows:     list[Row] # A CheckBlock has a list of rows, 
    result:   Any  = None
    passed:   Optional[bool] = None

# LaTeX helpers — all inline ($...$)
def _m(expr: str) -> str:
    """Wrap in inline math."""
    return f"${expr}$"

def _frac(n: str, d: str) -> str:
    """Wrap fraction; n (numerator) and d (denominator)"""
    return rf"\frac{{{n}}}{{{d}}}"

def _sqrt(arg: str) -> str:
    return rf"\sqrt{{{arg}}}"

def _status(passed: bool) -> tuple[str, str]:
    return ("pass", "PASS") if passed else ("fail", "FAIL")


if __name__ == "__main__":
    assert 1