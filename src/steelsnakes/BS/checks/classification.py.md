```python
from __future__ import annotations

import math
from pydantic import BaseModel

from steelsnakes.base.renders import CheckBlock, Row, _frac, _m, _sqrt
from steelsnakes.base.sections import BaseSection


# ---------------------------------------------------------------------------
# 0.  Design strength  (Table 6)
# ---------------------------------------------------------------------------

_PY_TABLE: dict[str, list[tuple[float, float]]] = {
    "S275": [(16, 275), (40, 265), (63, 255), (80, 245), (100, 235), (150, 225)],
    "S355": [(16, 355), (40, 345), (63, 335), (80, 325), (100, 315), (150, 295)],
    "S460": [(16, 460), (40, 445), (63, 430), (80, 415), (100, 400)],
}


def design_strength(grade: str, t: float) -> float:
    """Return py (N/mm2) for a given grade and governing thickness t (mm) per Table 6."""
    g = grade.upper().replace(" ", "")
    if g not in _PY_TABLE:
        raise ValueError(f"Unknown grade {grade!r}. Options: {list(_PY_TABLE)}")
    for t_lim, py in _PY_TABLE[g]:
        if t <= t_lim:
            return float(py)
    return float(_PY_TABLE[g][-1][1])


# ---------------------------------------------------------------------------
# 1.  Classification  (Cl. 3.5 / Table 7)
# ---------------------------------------------------------------------------

_FL_LIMITS: dict[str, float] = {"Plastic": 8.5, "Compact": 9.5, "Semi-compact": 15.0}
_WEB_LIMITS: dict[str, float] = {"Plastic": 79.0, "Compact": 98.0, "Semi-compact": 120.0}
_CLASS_RANK: dict[str, int] = {"Plastic": 1, "Compact": 2, "Semi-compact": 3, "Slender": 4}
_CLASS_CSS: dict[str, str] = {"Plastic": "pass", "Compact": "pass", "Semi-compact": "note", "Slender": "fail"}
_FL_SYM: dict[str, str] = {"Plastic": "8.5", "Compact": "9.5", "Semi-compact": "15", "Slender": "15"}
_WEB_SYM: dict[str, str] = {"Plastic": "79", "Compact": "98", "Semi-compact": "120", "Slender": "120"}


def _element_class(ratio: float, limits: dict[str, float]) -> str:
    if ratio <= limits["Plastic"]:
        return "Plastic"
    if ratio <= limits["Compact"]:
        return "Compact"
    if ratio <= limits["Semi-compact"]:
        return "Semi-compact"
    return "Slender"


def _divider(label: str) -> Row:
    return Row(
        expr=f'<span style="font-size:9pt; color:#555;">{label}</span>',
        clause="",
    )


class ClassificationResult(BaseModel):
    epsilon: float
    b_2T: float
    fl_limits: dict[str, float]
    flange_class: str
    d_t: float
    web_limits: dict[str, float]
    web_class: str
    section_class: str
    governing: str


class ClassificationWebResult(BaseModel):
    epsilon: float
    d_t: float
    axial_force: float
    moment: float
    fc: float
    sigma_comp: float
    sigma_tens: float
    R: float
    r1: float
    alpha: float
    gamma_c: float
    lim_plastic: float
    lim_compact: float
    lim_semicomp: float
    web_class: str
    case_label: str
    sc_note: str


def classification_result(section: BaseSection, py: float) -> ClassificationResult:
    eps = math.sqrt(275.0 / py)

    fl_lims = {k: v * eps for k, v in _FL_LIMITS.items()}
    web_lims = {k: v * eps for k, v in _WEB_LIMITS.items()}

    fl_cls = _element_class(section.b_2t, fl_lims)
    web_cls = _element_class(section.d_t, web_lims)
    gov_cls = fl_cls if _CLASS_RANK[fl_cls] >= _CLASS_RANK[web_cls] else web_cls
    gov_el = "flange" if _CLASS_RANK[fl_cls] >= _CLASS_RANK[web_cls] else "web"

    return ClassificationResult(
        epsilon=eps,
        b_2T=section.b_2t,
        fl_limits=fl_lims,
        flange_class=fl_cls,
        d_t=section.d_t,
        web_limits=web_lims,
        web_class=web_cls,
        section_class=gov_cls,
        governing=gov_el,
    )


def render_classification_block(result: ClassificationResult, section: BaseSection, py: float) -> CheckBlock:
    rows: list[Row] = []

    rows.append(Row(
        expr=(
            _m(r"\varepsilon") + " = "
            + _m(_sqrt(r"\frac{275}{p_y}"))
            + " = " + _m(_sqrt(f"\\frac{{275}}{{{py:.0f}}}"))
            + " = " + _m(f"{result.epsilon:.4f}")
        ),
        value=f"{result.epsilon:.4f}",
        clause="Cl. 3.5.2",
    ))

    rows.append(_divider("Flange outstand"))
    rows.append(Row(
        expr=(
            _m(_frac("B", "2T"))
            + " = " + _m(_frac(f"{section.B:.1f}", f"2 \\times {section.T:.1f}"))
            + " = " + _m(f"{result.b_2T:.2f}")
        ),
        value=f"{result.b_2T:.2f}",
        clause="Table 7",
    ))

    fl_limit = result.fl_limits[result.flange_class] if result.flange_class != "Slender" else result.fl_limits["Semi-compact"]
    fl_rel = "&le;" if result.flange_class != "Slender" else "&gt;"
    rows.append(Row(
        expr=(
            "Since " + _m(f"{result.b_2T:.2f}") + f" {fl_rel} "
            + _m(f"{_FL_SYM[result.flange_class]}\\varepsilon = {fl_limit:.2f}")
            + " &ensp;&rarr;&ensp; "
            + "P " + _m(f"{result.fl_limits['Plastic']:.2f}")
            + " &ensp;C " + _m(f"{result.fl_limits['Compact']:.2f}")
            + " &ensp;SC " + _m(f"{result.fl_limits['Semi-compact']:.2f}")
        ),
        status=_CLASS_CSS[result.flange_class],
        badge=result.flange_class,
        clause="Table 7",
    ))

    rows.append(_divider("Web &mdash; N-A at mid-depth (pure bending)"))
    rows.append(Row(
        expr=(
            _m(_frac("d", "t"))
            + " = " + _m(_frac(f"{section.d:.1f}", f"{section.t:.1f}"))
            + " = " + _m(f"{result.d_t:.2f}")
        ),
        value=f"{result.d_t:.2f}",
        clause="Table 7",
    ))

    web_limit = result.web_limits[result.web_class] if result.web_class != "Slender" else result.web_limits["Semi-compact"]
    web_rel = "&le;" if result.web_class != "Slender" else "&gt;"
    rows.append(Row(
        expr=(
            "Since " + _m(f"{result.d_t:.2f}") + f" {web_rel} "
            + _m(f"{_WEB_SYM[result.web_class]}\\varepsilon = {web_limit:.2f}")
            + " &ensp;&rarr;&ensp; "
            + "P " + _m(f"{result.web_limits['Plastic']:.2f}")
            + " &ensp;C " + _m(f"{result.web_limits['Compact']:.2f}")
            + " &ensp;SC " + _m(f"{result.web_limits['Semi-compact']:.2f}")
        ),
        status=_CLASS_CSS[result.web_class],
        badge=result.web_class,
        clause="Table 7",
    ))

    rows.append(_divider("Governing"))
    rows.append(Row(
        expr=f"Governed by {result.governing} &rarr; Class {_CLASS_RANK[result.section_class]}",
        status=_CLASS_CSS[result.section_class],
        badge=f"Class {_CLASS_RANK[result.section_class]} — {result.section_class}",
        clause="Cl. 3.5",
    ))

    return CheckBlock(
        title="Section Classification",
        subtitle="Cl. 3.5 / Table 7",
        rows=rows,
        result=result,
        passed=result.section_class != "Slender",
    )


def classify(section: BaseSection, py: float) -> CheckBlock:
    return render_classification_block(classification_result(section, py), section, py)


# ---------------------------------------------------------------------------
# 2.  Web classification — general (Cl. 3.5.3 / Table 7)
# ---------------------------------------------------------------------------

def classification_web_result(
    section: BaseSection,
    py: float,
    P: float = 0.0,
    M: float = 0.0,
) -> ClassificationWebResult:
    eps = math.sqrt(275.0 / py)
    d_t = section.d / section.t

    P_N = P * 1_000.0
    M_Nmm = M * 1_000_000.0
    A_mm2 = section.A * 100.0
    I_mm4 = section.Ixx * 10_000.0

    fc = P_N / A_mm2 if A_mm2 > 0 else 0.0
    fb_edge = M_Nmm * (section.d / 2) / I_mm4 if I_mm4 > 0 else 0.0
    sigma_c = fc + fb_edge
    sigma_t = fc - fb_edge
    R = fc / py

    r1 = P_N / (section.d * section.t * py) if P > 0 else 0.0
    alpha = min(1.0 + r1, 1.5)
    gamma_c = alpha * section.d / 2.0

    if P == 0:
        case_label = "(1) N-A at mid-depth — use pure bending classification"
    elif sigma_t >= 0:
        case_label = "(3) Compression throughout &rarr; " + _m("\\alpha = 1.5")
    else:
        case_label = "(2) Combined N + M &rarr; N-A in web"

    lim_plastic = 79.0 * eps / (0.4 + 0.6 * alpha)
    lim_compact = 98.0 * eps / alpha
    lim_semicomp = 120.0 * eps / (1.0 + 2.0 * R) if R > 0.5 else 120.0 * eps
    sc_note = (
        f"R = {R:.3f} &gt; 0.5 &rarr; 120&epsilon;/(1+2R)"
        if R > 0.5 else
        f"R = {R:.3f} &le; 0.5 &rarr; 120&epsilon;"
    )

    if d_t <= lim_plastic:
        web_cls = "Plastic"
    elif d_t <= lim_compact:
        web_cls = "Compact"
    elif d_t <= lim_semicomp:
        web_cls = "Semi-compact"
    else:
        web_cls = "Slender"

    return ClassificationWebResult(
        epsilon=eps,
        d_t=d_t,
        axial_force=P,
        moment=M,
        fc=fc,
        sigma_comp=sigma_c,
        sigma_tens=sigma_t,
        R=R,
        r1=r1,
        alpha=alpha,
        gamma_c=gamma_c,
        lim_plastic=lim_plastic,
        lim_compact=lim_compact,
        lim_semicomp=lim_semicomp,
        web_class=web_cls,
        case_label=case_label,
        sc_note=sc_note,
    )


def render_classification_web_block(result: ClassificationWebResult, section: BaseSection, py: float) -> CheckBlock:
    rows: list[Row] = []

    rows.append(Row(
        expr=(
            _m(r"\varepsilon") + " = " + _m(f"\\sqrt{{275/{py:.0f}}} = {result.epsilon:.4f}")
            + " &ensp; " + result.case_label
        ),
        value=f"{result.epsilon:.4f}",
        clause="Cl. 3.5.2",
    ))

    rows.append(_divider("Web stresses"))
    rows.append(Row(
        expr=(
            _m("f_c") + " = " + _m(_frac("P", "A"))
            + " = " + _m(f"{result.axial_force * 1000.0:.0f} / {section.A * 100.0:.0f}")
            + " = " + _m(f"{result.fc:.2f}") + " N/mm²"
        ),
        value=f"{result.fc:.2f}", unit="N/mm²",
        clause="Cl. 3.5.4",
    ))

    rows.append(Row(
        expr=(
            "Web edges: compression " + _m(f"\\sigma = {result.sigma_comp:.1f}") + " N/mm²"
            + " &ensp; tension " + _m(f"\\sigma = {result.sigma_tens:.1f}") + " N/mm²"
        ),
        clause="Cl. 3.5.4",
    ))

    rows.append(Row(
        expr=(
            "Mean stress ratio " + _m("R") + " = "
            + _m(_frac("f_c", "p_y"))
            + " = " + _m(f"{result.fc:.2f}/{py:.0f}")
            + " = " + _m(f"{result.R:.4f}")
            + " &ensp; " + result.sc_note
        ),
        value=f"{result.R:.4f}",
        clause="Cl. 3.5.4",
    ))

    rows.append(_divider("N-A position"))
    rows.append(Row(
        expr=(
            _m("r_1") + " = " + _m(_frac("F_c", "d_c \\cdot t \\cdot p_y"))
            + " = " + _m(f"{result.axial_force * 1000.0:.0f}/({section.d:.1f}\\times{section.t:.1f}\\times{py:.0f})")
            + " = " + _m(f"{result.r1:.4f}")
        ),
        value=f"{result.r1:.4f}",
        clause="Table 7",
    ))

    rows.append(Row(
        expr=(
            _m(r"\alpha") + " = " + _m(r"\min(1 + r_1,\; 1.5)")
            + " = " + _m(f"\\min({1 + result.r1:.3f},\\; 1.5)")
            + " = " + _m(f"{result.alpha:.3f}")
            + " &ensp; "
            + _m(r"\gamma_c") + " = " + _m(r"\alpha \cdot d_c / 2")
            + " = " + _m(f"{result.gamma_c:.1f}") + " mm"
        ),
        value=f"{result.alpha:.3f}",
        clause="Table 7",
    ))

    rows.append(_divider("Web slenderness"))
    rows.append(Row(
        expr=(
            _m(_frac("d", "t"))
            + " = " + _m(f"{section.d:.1f}/{section.t:.1f}")
            + " = " + _m(f"{result.d_t:.2f}")
        ),
        value=f"{result.d_t:.2f}",
        clause="Table 7",
    ))

    web_limit = (
        result.lim_plastic if result.web_class == "Plastic" else
        result.lim_compact if result.web_class == "Compact" else
        result.lim_semicomp
    )
    web_rel = "&le;" if result.web_class != "Slender" else "&gt;"
    rows.append(Row(
        expr=(
            "Since " + _m(f"{result.d_t:.2f}") + f" {web_rel} limit"
            + " &ensp;&rarr;&ensp; "
            + "P " + _m(f"{result.lim_plastic:.2f}")
            + " &ensp;C " + _m(f"{result.lim_compact:.2f}")
            + " &ensp;SC " + _m(f"{result.lim_semicomp:.2f}")
        ),
        status=_CLASS_CSS[result.web_class],
        badge=result.web_class,
        clause="Table 7",
    ))

    rows.append(_divider("Result"))
    rows.append(Row(
        expr=f"Web (general) &rarr; Class {_CLASS_RANK[result.web_class]}",
        status=_CLASS_CSS[result.web_class],
        badge=f"Class {_CLASS_RANK[result.web_class]} — {result.web_class}",
        clause="Cl. 3.5.3",
    ))

    return CheckBlock(
        title="Web Classification (General)",
        subtitle="Cl. 3.5.3 / Table 7",
        rows=rows,
        result=result,
        passed=result.web_class != "Slender",
    )


def classify_web(section: BaseSection, py: float, P: float = 0.0, M: float = 0.0) -> CheckBlock:
    return render_classification_web_block(classification_web_result(section, py, P=P, M=M), section, py)


if __name__ == "__main__":
    # from szf.sections import SectionType, load_registry

    # registry = load_registry()
    # section = registry[SectionType.JIS_H]["190x190x45"]
    # block = classify(section, py=275)
    # print(f"\n{block.title}  |  {block.subtitle}")
    # for row in block.rows:
    #     print(f"  [{row.clause:<12}]  {row.expr[:70]:<70}  {row.value}  {row.badge}")

    assert 1

```