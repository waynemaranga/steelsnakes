# """
# graphing_plotly.py  —  Interactive steel section visualisation (Plotly)
# =======================================================================

# Companion to ``graphing.py`` (matplotlib).  Uses Plotly for fully
# interactive 2-D cross-section plots and 3-D member renders with pan /
# zoom / rotate / hover built-in.

# Dependencies
# ------------
#     pip install plotly numpy

# Optional (needed for static image export only):
#     pip install kaleido

# Typical usage
# -------------
# >>> import json
# >>> from graphing_plotly import plot_section_2d, plot_section_3d, PlotlyConfig, LengthUnit
# >>>
# >>> with open("UB.json") as f:
# ...     ub_db = json.load(f)
# >>>
# >>> cfg = PlotlyConfig(display_unit=LengthUnit.MM, show_properties=True)
# >>>
# >>> fig2 = plot_section_2d("UB", ub_db["533x210x82"], cfg)
# >>> fig2.show()                          # interactive browser window
# >>> fig2.write_html("ub_section.html")  # shareable HTML
# >>>
# >>> fig3 = plot_section_3d("UB", ub_db["533x210x82"], length=6000, config=cfg)
# >>> fig3.show()
# >>> fig3.write_html("ub_member.html")

# Coordinate convention
# ---------------------
# Cross-section axes follow the structural standard:

#     y  ↑           (Y-Y = major axis, vertical)
#        │
#        └──→  z     (Z-Z = minor axis, horizontal)

# Plotly axis mapping
#     Plotly X  ≡  section z  (minor, horizontal)
#     Plotly Y  ≡  section y  (major, vertical)
#     Plotly Z  ≡  longitudinal member axis

# Architecture
# ------------
# Geometry is delegated to ``graphing.py`` via :func:`get_geometry` and
# :func:`register_geometry_builder`.  This module adds:
#   - :class:`PlotlyConfig`  — appearance/behaviour settings
#   - :func:`_triangulate_polygon`  — ear-clip for Mesh3d end-caps
#   - :func:`_build_member_mesh`  — Mesh3d vertex/face lists per polygon
#   - :func:`plot_section_2d`  — ``go.Figure`` with scatter fill, axes, dims
#   - :func:`plot_section_3d`  — ``go.Figure`` with Mesh3d + edge outlines

# Registering new section types
# ------------------------------
# New geometry builders are registered once (only needs doing in graphing.py):
# >>> from graphing import register_geometry_builder
# >>> register_geometry_builder("PFC", my_pfc_fn)
# The plotly module picks them up automatically through get_geometry().
# """

# from __future__ import annotations

# from dataclasses import dataclass, field
# from typing import Any, Optional

# import numpy as np
# import plotly.graph_objects as go

# # ── Re-export unit helpers & geometry registry from the matplotlib companion ─
# from steelsnakes.base.graphing import (
#     LengthUnit,
#     PlotConfig,          # not used directly but convenient for users to import together
#     get_geometry,
#     register_geometry_builder,
#     _cvt,
#     _cvt_arr,
#     _bbox,
# )

# __all__ = [
#     "LengthUnit",
#     "PlotlyConfig",
#     "DEFAULT_CONFIG",
#     "plot_section_2d",
#     "plot_section_3d",
#     "get_geometry",
#     "register_geometry_builder",
# ]


# # ─────────────────────────────────────────────────────────────────────────────
# # 1.  Configuration
# # ─────────────────────────────────────────────────────────────────────────────

# @dataclass
# class PlotlyConfig:
#     """Settings controlling appearance and behaviour of Plotly section figures.

#     Parameters
#     ----------
#     input_unit
#         Unit of the raw section data (Blue Book JSON → ``LengthUnit.MM``).
#     display_unit
#         Unit shown on axis labels and dimension callouts.
#     section_color
#         Hex fill colour for the steel section.
#     section_opacity
#         Opacity of the section fill (0–1).
#     edge_color
#         Colour of the section outline and 3-D edge loops.
#     edge_width
#         Line width of the section outline in px.
#     axis_color
#         Colour of the centroidal Y-Y / Z-Z axis lines.
#     dim_color
#         Colour of dimension annotation arrows and text.
#     centroid_color
#         Colour of the centroid cross-hair marker.
#     show_axes
#         Draw centroidal axis lines.
#     show_centroid
#         Draw a ``+`` marker at the centroid (2-D only).
#     show_dimensions
#         Draw dimension callout arrows and labels.
#     show_properties
#         Show a compact section-property annotation in the figure.
#     show_grid
#         Show background grid in the 2-D figure.
#     true_scale_3d
#         If ``True`` the 3-D render is truly to scale.
#         If ``False`` (default) the member length is normalised to
#         ``6 × max(section dimension)`` so the cross-section profile
#         is clearly visible; the real length still appears in the title.
#     camera_eye
#         Dict with ``x, y, z`` for the initial 3-D camera position.
#         Defaults to an isometric-style view.
#     mesh_lighting
#         Dict of Plotly Mesh3d ``lighting`` kwargs for shading.
#     mesh_lightposition
#         Dict of Plotly Mesh3d ``lightposition`` kwargs.
#     fig_width, fig_height
#         Figure pixel dimensions.
#     """
#     input_unit:       LengthUnit = LengthUnit.MM
#     display_unit:     LengthUnit = LengthUnit.MM

#     # Section aesthetics
#     section_color:    str   = "#3A6EA5"    # steel blue
#     section_opacity:  float = 0.88
#     edge_color:       str   = "#1C3D5C"    # dark navy
#     edge_width:       float = 2.0

#     # Annotation colours
#     axis_color:       str   = "#C0392B"    # structural red
#     dim_color:        str   = "#555555"    # charcoal
#     centroid_color:   str   = "#E74C3C"    # bright red

#     # Feature toggles
#     show_axes:        bool  = True
#     show_centroid:    bool  = True
#     show_dimensions:  bool  = True
#     show_properties:  bool  = True
#     show_grid:        bool  = True

#     # 3-D options
#     true_scale_3d:    bool  = False
#     camera_eye:       dict  = field(default_factory=lambda: dict(x=1.6, y=0.9, z=1.2))
#     mesh_lighting:    dict  = field(default_factory=lambda: dict(
#                                   ambient=0.40, diffuse=0.90,
#                                   specular=0.50, roughness=0.35, fresnel=0.10))
#     mesh_lightposition: dict = field(default_factory=lambda: dict(x=500, y=800, z=2000))

#     # Figure size
#     fig_width:  int = 700
#     fig_height: int = 700

#     # 3-D figure (wider to give room for the perspective)
#     fig_width_3d:  int = 950
#     fig_height_3d: int = 680


# #: Module-level default configuration.
# DEFAULT_CONFIG: PlotlyConfig = PlotlyConfig()


# # ─────────────────────────────────────────────────────────────────────────────
# # 2.  Polygon triangulation  (ear-clip, O(n²))
# # ─────────────────────────────────────────────────────────────────────────────

# def _signed_area(pts: np.ndarray) -> float:
#     """Return signed area of a polygon (positive = CCW winding)."""
#     x, y = pts[:, 0], pts[:, 1]
#     return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


# def _pt_in_tri(p: np.ndarray, a: np.ndarray, b: np.ndarray, c: np.ndarray) -> bool:
#     """Return True if point *p* is strictly inside triangle (a, b, c)."""
#     def _side(p1, p2, p3):
#         return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
#     d1, d2, d3 = _side(p, a, b), _side(p, b, c), _side(p, c, a)
#     has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
#     has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
#     return not (has_neg and has_pos)


# def _triangulate_polygon(pts2d: np.ndarray) -> list[tuple[int, int, int]]:
#     """Ear-clip triangulation of a simple 2-D polygon.

#     Handles both convex and non-convex (concave) polygons, including
#     I-sections.  Works on uniquely-listed vertices (do **not** repeat the
#     first vertex at the end).

#     Parameters
#     ----------
#     pts2d
#         ``(n, 2)`` float array of polygon vertices (no closing repeat).

#     Returns
#     -------
#     list of ``(i, j, k)`` index triples referencing *pts2d* rows.
#     """
#     pts  = pts2d.copy()
#     n    = len(pts)
#     if n < 3:
#         return []
#     if n == 3:
#         return [(0, 1, 2)]

#     # Ensure CCW winding so the "left turn" ear test is consistent.
#     if _signed_area(pts) < 0:
#         pts = pts[::-1].copy()
#         original_indices = list(range(n - 1, -1, -1))
#     else:
#         original_indices = list(range(n))

#     remaining = list(range(n))   # indices into *pts* (CCW-remapped)
#     triangles_local: list[tuple[int, int, int]] = []
#     safety = n * n

#     while len(remaining) > 3 and safety > 0:
#         safety -= 1
#         ear_found = False
#         m = len(remaining)
#         for idx in range(m):
#             i_prev = remaining[(idx - 1) % m]
#             i_curr = remaining[idx]
#             i_next = remaining[(idx + 1) % m]
#             a, b, c = pts[i_prev], pts[i_curr], pts[i_next]
#             # Must form a left (CCW) turn
#             cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
#             if cross <= 1e-10:
#                 continue
#             # No other polygon vertex inside the candidate ear triangle
#             is_ear = True
#             for j_idx in range(m):
#                 j = remaining[j_idx]
#                 if j in (i_prev, i_curr, i_next):
#                     continue
#                 if _pt_in_tri(pts[j], a, b, c):
#                     is_ear = False
#                     break
#             if is_ear:
#                 triangles_local.append((i_prev, i_curr, i_next))
#                 remaining.pop(idx)
#                 ear_found = True
#                 break
#         if not ear_found:
#             break   # degenerate polygon guard

#     if len(remaining) == 3:
#         triangles_local.append((remaining[0], remaining[1], remaining[2]))

#     # Map back to original (pre-CCW-reorder) indices
#     return [
#         (original_indices[a], original_indices[b], original_indices[c])
#         for (a, b, c) in triangles_local
#     ]


# # ─────────────────────────────────────────────────────────────────────────────
# # 3.  3-D mesh construction
# # ─────────────────────────────────────────────────────────────────────────────

# def _build_member_mesh(
#     poly2d: np.ndarray,
#     length: float,
# ) -> dict:
#     """Build Mesh3d vertex and face arrays for one extruded polygon.

#     The polygon is extruded along the Plotly Z-axis from 0 to *length*.
#     Plotly X ≡ section-z, Plotly Y ≡ section-y.

#     Parameters
#     ----------
#     poly2d
#         ``(n, 2)`` array — unique vertices, col 0 = section-z, col 1 = section-y.
#         **Must not** repeat the first vertex at the end.
#     length
#         Extrusion distance (in display_unit).

#     Returns
#     -------
#     dict with keys ``x, y, z, i, j, k`` ready for ``go.Mesh3d(**mesh)``.
#     """
#     n  = len(poly2d)

#     # ── Vertices ─────────────────────────────────────────────────────────────
#     # Near face (Plotly-Z = 0): indices 0..n-1
#     # Far  face (Plotly-Z = L): indices n..2n-1
#     xs = np.concatenate([poly2d[:, 0], poly2d[:, 0]])
#     ys = np.concatenate([poly2d[:, 1], poly2d[:, 1]])
#     zs = np.concatenate([np.zeros(n), np.full(n, length)])

#     # ── Faces ────────────────────────────────────────────────────────────────
#     fi, fj, fk = [], [], []

#     # Side walls: each polygon edge → one quad → two triangles
#     for e in range(n):
#         e1 = (e + 1) % n
#         # quad: near[e], near[e1], far[e1], far[e]
#         fi += [e,       e,           n + e]
#         fj += [e1,      n + e1,      n + e1]
#         fk += [n + e1,  n + e,       e1]

#     # End caps: ear-clip triangulation
#     cap_tris = _triangulate_polygon(poly2d)
#     for (a, b, c) in cap_tris:
#         # Near cap (outward normal → −Z): reverse winding
#         fi.append(a);      fj.append(c);      fk.append(b)
#         # Far  cap (outward normal → +Z): keep winding
#         fi.append(n + a);  fj.append(n + b);  fk.append(n + c)

#     return dict(
#         x=xs.tolist(), y=ys.tolist(), z=zs.tolist(),
#         i=fi, j=fj, k=fk,
#     )


# def _polygon_outline_3d(
#     poly2d: np.ndarray,
#     length: float,
#     n_longi_lines: int = 4,
# ) -> tuple[list[float], list[float], list[float]]:
#     """Return (x, y, z) lists for edge-loop outlines suitable for go.Scatter3d.

#     Draws three loops:
#     * near-face perimeter  (Plotly-Z = 0)
#     * far-face perimeter   (Plotly-Z = *length*)
#     * *n_longi_lines* longitudinal edge lines along the extrusion

#     ``None`` values are used to break line segments without a separate trace.
#     """
#     n   = len(poly2d)
#     x, y, z = [], [], []

#     def _ring(lz: float) -> None:
#         for pt in poly2d:
#             x.append(pt[0]); y.append(pt[1]); z.append(lz)
#         x.append(poly2d[0, 0]); y.append(poly2d[0, 1]); z.append(lz)
#         x.append(None);         y.append(None);         z.append(None)

#     _ring(0.0)
#     _ring(length)

#     # Longitudinal edge lines at evenly spaced vertices
#     step = max(1, n // n_longi_lines)
#     for i in range(0, n, step):
#         x += [poly2d[i, 0], poly2d[i, 0], None]
#         y += [poly2d[i, 1], poly2d[i, 1], None]
#         z += [0.0,          length,        None]

#     return x, y, z


# # ─────────────────────────────────────────────────────────────────────────────
# # 4.  2-D annotation helpers
# # ─────────────────────────────────────────────────────────────────────────────

# def _make_dim_h(
#     z0: float, z1: float, y_arrow: float,
#     label: str, cfg: PlotlyConfig,
#     y_offset_frac: float = 0.04,
#     total_height: float = 1.0,
# ) -> tuple[list[dict], list[go.Scatter]]:
#     """Horizontal dimension: double-headed arrow at *y_arrow*, label above."""
#     mid_z = (z0 + z1) / 2.0
#     y_txt = y_arrow + total_height * y_offset_frac
#     c = cfg.dim_color

#     annots = [
#         # left-pointing arrow
#         dict(x=z0, y=y_arrow, ax=mid_z, ay=y_arrow,
#              xref="x", yref="y", axref="x", ayref="y",
#              arrowhead=2, arrowsize=1, arrowwidth=1.2, arrowcolor=c,
#              showarrow=True, text=""),
#         # right-pointing arrow
#         dict(x=z1, y=y_arrow, ax=mid_z, ay=y_arrow,
#              xref="x", yref="y", axref="x", ayref="y",
#              arrowhead=2, arrowsize=1, arrowwidth=1.2, arrowcolor=c,
#              showarrow=True, text=""),
#         # label text
#         dict(x=mid_z, y=y_txt, xref="x", yref="y",
#              text=label, showarrow=False,
#              font=dict(size=9, color=c)),
#     ]
#     # connector line between the two arrowheads
#     line = go.Scatter(x=[z0, z1], y=[y_arrow, y_arrow],
#                       mode="lines",
#                       line=dict(color=c, width=0.8),
#                       showlegend=False, hoverinfo="skip")
#     return annots, [line]


# def _make_dim_v(
#     y0: float, y1: float, z_arrow: float,
#     label: str, cfg: PlotlyConfig,
#     z_offset_frac: float = 0.04,
#     total_width: float = 1.0,
# ) -> tuple[list[dict], list[go.Scatter]]:
#     """Vertical dimension: double-headed arrow at *z_arrow*, label to the right."""
#     mid_y = (y0 + y1) / 2.0
#     z_txt = z_arrow + total_width * z_offset_frac
#     c = cfg.dim_color

#     annots = [
#         dict(x=z_arrow, y=y0, ax=z_arrow, ay=mid_y,
#              xref="x", yref="y", axref="x", ayref="y",
#              arrowhead=2, arrowsize=1, arrowwidth=1.2, arrowcolor=c,
#              showarrow=True, text=""),
#         dict(x=z_arrow, y=y1, ax=z_arrow, ay=mid_y,
#              xref="x", yref="y", axref="x", ayref="y",
#              arrowhead=2, arrowsize=1, arrowwidth=1.2, arrowcolor=c,
#              showarrow=True, text=""),
#         dict(x=z_txt, y=mid_y, xref="x", yref="y",
#              text=label, showarrow=False,
#              font=dict(size=9, color=c),
#              xanchor="left"),
#     ]
#     line = go.Scatter(x=[z_arrow, z_arrow], y=[y0, y1],
#                       mode="lines",
#                       line=dict(color=c, width=0.8),
#                       showlegend=False, hoverinfo="skip")
#     return annots, [line]


# def _extension_line(z0, y0, z1, y1, cfg):
#     """Dashed leader line trace."""
#     return go.Scatter(
#         x=[z0, z1], y=[y0, y1],
#         mode="lines",
#         line=dict(color=cfg.dim_color, width=0.6, dash="dot"),
#         showlegend=False, hoverinfo="skip",
#     )


# # ── Section-specific dimension sets ──────────────────────────────────────────

# def _dims_ub_plotly(
#     ax_traces: list, annots: list,
#     data: dict[str, Any],
#     polys_d: list[np.ndarray],
#     cfg: PlotlyConfig,
# ) -> None:
#     """Add UB/UC/UBP dimension callouts in-place to *ax_traces* and *annots*."""
#     def c(v):
#         return _cvt(float(v), cfg.input_unit, cfg.display_unit)

#     h  = c(data["h"])
#     b  = c(data["b"])
#     tw = c(data["tw"])
#     tf = c(data["tf"])
#     u  = cfg.display_unit.value

#     zmin, ymin, zmax, ymax = _bbox(polys_d)
#     gz = (zmax - zmin) * 0.07
#     gy = (ymax - ymin) * 0.07
#     W  = zmax - zmin
#     H  = ymax - ymin

#     # b — flange width, above section
#     a, t = _make_dim_h(-b/2, b/2, ymax + 1.4*gy,
#                         f"b = {b:.1f} {u}", cfg,
#                         y_offset_frac=0.04, total_height=H)
#     annots += a; ax_traces += t

#     # h — total depth, to the right
#     a, t = _make_dim_v(-h/2, h/2, zmax + 1.5*gz,
#                         f"h = {h:.1f} {u}", cfg,
#                         z_offset_frac=0.04, total_width=W)
#     annots += a; ax_traces += t

#     # tw — web thickness, below section
#     a, t = _make_dim_h(-tw/2, tw/2, ymin - 1.4*gy,
#                         f"tw = {tw:.1f} {u}", cfg,
#                         y_offset_frac=-0.04, total_height=H)
#     annots += a; ax_traces += t

#     # tf — top flange thickness, further right with extension leaders
#     z_tf = zmax + 4.2*gz
#     a, t = _make_dim_v(h/2 - tf, h/2, z_tf,
#                         f"tf = {tf:.1f} {u}", cfg,
#                         z_offset_frac=0.04, total_width=W)
#     annots += a; ax_traces += t
#     ax_traces.append(_extension_line(zmax, h/2,       z_tf, h/2,       cfg))
#     ax_traces.append(_extension_line(zmax, h/2 - tf,  z_tf, h/2 - tf,  cfg))


# def _dims_l_equal_b2b_plotly(
#     ax_traces: list, annots: list,
#     data: dict[str, Any],
#     polys_d: list[np.ndarray],
#     cfg: PlotlyConfig,
# ) -> None:
#     """Add L_EQUAL_B2B dimension callouts in-place."""
#     def c(v):
#         return _cvt(float(v), cfg.input_unit, cfg.display_unit)

#     leg = c(data["hxh"].split("x")[0])
#     t   = c(data["t"])
#     n_y = c(data["n_y"])
#     u   = cfg.display_unit.value
#     yo  = -n_y

#     zmin, ymin, zmax, ymax = _bbox(polys_d)
#     gz = (zmax - zmin) * 0.07
#     gy = (ymax - ymin) * 0.07
#     W  = zmax - zmin
#     H  = ymax - ymin

#     # 2h — total width, below section
#     a, t_traces = _make_dim_h(-leg, leg, ymin - 1.4*gy,
#                                f"2h = {2*leg:.1f} {u}", cfg,
#                                y_offset_frac=-0.04, total_height=H)
#     annots += a; ax_traces += t_traces

#     # h — leg length, to the right
#     a, t_traces = _make_dim_v(yo, yo + leg, zmax + 1.5*gz,
#                                f"h = {leg:.1f} {u}", cfg,
#                                z_offset_frac=0.04, total_width=W)
#     annots += a; ax_traces += t_traces

#     # t — leg thickness, further right
#     z_t = zmax + 4.2*gz
#     a, t_traces = _make_dim_v(yo, yo + t, z_t,
#                                f"t = {t:.1f} {u}", cfg,
#                                z_offset_frac=0.04, total_width=W)
#     annots += a; ax_traces += t_traces
#     ax_traces.append(_extension_line(zmax, yo,     z_t, yo,     cfg))
#     ax_traces.append(_extension_line(zmax, yo + t, z_t, yo + t, cfg))


# _DIM_DRAWERS_PLOTLY = {
#     "UB":          _dims_ub_plotly,
#     "UC":          _dims_ub_plotly,
#     "UBP":         _dims_ub_plotly,
#     "L_EQUAL_B2B": _dims_l_equal_b2b_plotly,
# }


# def _normalise_section_type(section_type: object) -> str:
#     """Return canonical section type string from enum-like or plain string input."""
#     if isinstance(section_type, str):
#         return section_type
#     value = getattr(section_type, "value", None)
#     return str(value) if value is not None else str(section_type)


# # ── Properties annotation ─────────────────────────────────────────────────────

# def _props_annotation(key: str, data: dict[str, Any]) -> dict:
#     """Return a Plotly annotation dict containing a property table."""
#     rows = [f"<b>{data.get('designation', '—')}</b>"]

#     def _f(k, fmt=".0f"):
#         v = data.get(k)
#         return format(v, fmt) if v is not None else "—"

#     if key in ("UB", "UC", "UBP"):
#         rows += [
#             f"mass = {_f('mass_per_metre', '.1f')} kg/m",
#             f"A  = {_f('A')} cm²",
#             f"Iyy = {_f('I_yy')} cm⁴",
#             f"Izz = {_f('I_zz')} cm⁴",
#             f"Wpl,yy = {_f('W_pl_yy')} cm³",
#             f"It = {_f('I_t')} cm⁴",
#         ]
#     elif key == "L_EQUAL_B2B":
#         rows += [
#             f"mass = {_f('total_mass_per_metre', '.1f')} kg/m",
#             f"A  = {_f('total_area', '.1f')} cm²",
#             f"Iyy = {_f('I_yy', '.1f')} cm⁴",
#             f"Wel,yy = {_f('W_el_yy', '.1f')} cm³",
#         ]

#     return dict(
#         xref="paper", yref="paper",
#         x=0.01, y=0.01,
#         xanchor="left", yanchor="bottom",
#         text="<br>".join(rows),
#         showarrow=False,
#         font=dict(size=10, family="Courier New, monospace"),
#         bgcolor="rgba(255,255,255,0.88)",
#         bordercolor="#BBBBBB",
#         borderwidth=1,
#         borderpad=6,
#     )


# # ─────────────────────────────────────────────────────────────────────────────
# # 5.  Public API
# # ─────────────────────────────────────────────────────────────────────────────

# def plot_section_2d(
#     section_type: object,
#     section_data: dict[str, Any],
#     config: Optional[PlotlyConfig] = None,
# ) -> go.Figure:
#     """Return an interactive Plotly 2-D cross-section figure.

#     Parameters
#     ----------
#     section_type
#         Section type key (string or ``SectionType`` enum).
#     section_data
#         Property dict for a single section from the JSON database.
#     config
#         :class:`PlotlyConfig` instance — defaults to :data:`DEFAULT_CONFIG`.

#     Returns
#     -------
#     ``plotly.graph_objects.Figure``
#         Call ``.show()`` to open in the browser, or ``.write_html()`` /
#         ``.write_image()`` to export.

#     Features
#     --------
#     - Filled, to-scale cross-section with hover coordinates
#     - Centroidal Y–Y and Z–Z axis lines
#     - ``+`` centroid marker
#     - Dimension callout arrows and leader lines
#     - Section property annotation box
#     - Equal aspect ratio enforced via ``scaleanchor``
#     - Hover info shows z, y coordinates
#     """
#     cfg  = config or DEFAULT_CONFIG
#     key = _normalise_section_type(section_type)

#     polys = [
#         _cvt_arr(p, cfg.input_unit, cfg.display_unit)
#         for p in get_geometry(key, section_data)
#     ]

#     zmin, ymin, zmax, ymax = _bbox(polys)
#     width  = zmax - zmin
#     height = ymax - ymin
#     u      = cfg.display_unit.value

#     traces: list[Any] = []
#     annots: list[dict]              = []

#     # ── Section fill ──────────────────────────────────────────────────────────
#     for poly in polys:
#         closed = np.vstack([poly, poly[0]])   # close the loop for Scatter fill
#         traces.append(go.Scatter(
#             x=closed[:, 0], y=closed[:, 1],
#             mode="lines",
#             fill="toself",
#             fillcolor=cfg.section_color,
#             opacity=cfg.section_opacity,
#             line=dict(color=cfg.edge_color, width=cfg.edge_width),
#             name=key,
#             hovertemplate=f"z = %{{x:.2f}} {u}<br>y = %{{y:.2f}} {u}<extra></extra>",
#         ))

#     # ── Centroidal axes ────────────────────────────────────────────────────────
#     if cfg.show_axes:
#         pad_z = width  * 0.28
#         pad_y = height * 0.28

#         traces.append(go.Scatter(
#             x=[zmin - pad_z, zmax + pad_z], y=[0, 0],
#             mode="lines+text",
#             line=dict(color=cfg.axis_color, width=1.0, dash="dash"),
#             text=["", "Y–Y"], textposition="middle right",
#             textfont=dict(size=10, color=cfg.axis_color),
#             showlegend=False, hoverinfo="skip",
#         ))
#         traces.append(go.Scatter(
#             x=[0, 0], y=[ymin - pad_y, ymax + pad_y],
#             mode="lines+text",
#             line=dict(color=cfg.axis_color, width=1.0, dash="dash"),
#             text=["", "Z–Z"], textposition="top center",
#             textfont=dict(size=10, color=cfg.axis_color),
#             showlegend=False, hoverinfo="skip",
#         ))

#     # ── Centroid marker ────────────────────────────────────────────────────────
#     if cfg.show_centroid:
#         traces.append(go.Scatter(
#             x=[0], y=[0],
#             mode="markers",
#             marker=dict(symbol="cross", size=14, color=cfg.centroid_color, line_width=2),
#             name="Centroid",
#             hovertemplate="Centroid (0, 0)<extra></extra>",
#         ))

#     # ── Dimension callouts ─────────────────────────────────────────────────────
#     if cfg.show_dimensions:
#         dim_fn = _DIM_DRAWERS_PLOTLY.get(key)
#         if dim_fn is not None:
#             dim_fn(traces, annots, section_data, polys, cfg)

#     # ── Properties annotation ──────────────────────────────────────────────────
#     if cfg.show_properties:
#         annots.append(_props_annotation(key, section_data))

#     # ── Layout ────────────────────────────────────────────────────────────────
#     pad_z = width  * 0.55
#     pad_y = height * 0.55

#     layout = go.Layout(
#         title=dict(
#             text=f"<b>{key}</b>  ·  {section_data.get('designation', '')}",
#             font=dict(size=15),
#             x=0.5,
#         ),
#         xaxis=dict(
#             title=f"z  [{u}]",
#             range=[zmin - pad_z, zmax + pad_z],
#             scaleanchor="y",        # enforce equal aspect ratio
#             scaleratio=1,
#             showgrid=cfg.show_grid,
#             gridcolor="#EEEEEE",
#             zeroline=False,
#         ),
#         yaxis=dict(
#             title=f"y  [{u}]",
#             range=[ymin - pad_y, ymax + pad_y],
#             showgrid=cfg.show_grid,
#             gridcolor="#EEEEEE",
#             zeroline=False,
#         ),
#         annotations=annots,
#         showlegend=False,
#         plot_bgcolor="white",
#         paper_bgcolor="white",
#         width=cfg.fig_width,
#         height=cfg.fig_height,
#         margin=dict(l=60, r=60, t=60, b=60),
#     )

#     return go.Figure(data=traces, layout=layout)


# def plot_section_3d(
#     section_type: object,
#     section_data: dict[str, Any],
#     length: float,
#     config: Optional[PlotlyConfig] = None,
#     show_edge_loops: bool = True,
# ) -> go.Figure:
#     """Return an interactive Plotly 3-D member figure.

#     The cross-section is extruded along the member axis (Plotly Z) using
#     ``go.Mesh3d`` with explicit triangulation, producing a solid, shaded,
#     fully rotatable member.

#     Parameters
#     ----------
#     section_type
#         Section type key (string or ``SectionType`` enum).
#     section_data
#         Property dict for a single section from the JSON database.
#     length
#         Member length in ``config.input_unit``.
#     config
#         :class:`PlotlyConfig` instance.
#     show_edge_loops
#         If ``True`` (default) draw near/far perimeter loops and longitudinal
#         edge lines as a ``go.Scatter3d`` overlay — sharpens the look and
#         makes zooming at end faces cleaner.

#     Returns
#     -------
#     ``plotly.graph_objects.Figure``

#     3-D interaction
#     ---------------
#     - **Rotate** — left-click drag
#     - **Pan** — right-click drag (or Shift + left-click)
#     - **Zoom** — scroll wheel, or use the toolbar
#     - **Orbit** — use the ``Orbital`` rotation type button in the Plotly toolbar
#     - **Hover** — shows x, y, z coordinates at the cursor

#     Notes
#     -----
#     When ``config.true_scale_3d`` is ``False`` the displayed length is
#     normalised to ``6 × max(section dimension)`` so the section profile
#     remains clearly visible.  The real length still appears in the title.
#     """
#     cfg        = config or DEFAULT_CONFIG
#     key = _normalise_section_type(section_type)

#     polys      = [
#         _cvt_arr(p, cfg.input_unit, cfg.display_unit)
#         for p in get_geometry(key, section_data)
#     ]
#     length_d   = _cvt(length, cfg.input_unit, cfg.display_unit)

#     zmin, ymin, zmax, ymax = _bbox(polys)
#     max_dim    = max(zmax - zmin, ymax - ymin)
#     u          = cfg.display_unit.value

#     if cfg.true_scale_3d:
#         disp_len  = length_d
#         len_note  = f"{length_d:.2f} {u}"
#     else:
#         disp_len  = max_dim * 6.0
#         len_note  = f"{length_d:.2f} {u}  (section scaled for clarity)"

#     traces: list[Any] = []

#     # ── One Mesh3d per polygon ────────────────────────────────────────────────
#     for idx, poly in enumerate(polys):
#         # Remove closing vertex if present (last == first)
#         if np.allclose(poly[0], poly[-1]):
#             poly = poly[:-1]

#         mesh = _build_member_mesh(poly, disp_len)

#         traces.append(go.Mesh3d(
#             **mesh,
#             color=cfg.section_color,
#             opacity=cfg.section_opacity,
#             lighting=cfg.mesh_lighting,
#             lightposition=cfg.mesh_lightposition,
#             flatshading=False,
#             hovertemplate=(
#                 f"z (section) = %{{x:.2f}} {u}<br>"
#                 f"y (section) = %{{y:.2f}} {u}<br>"
#                 f"L = %{{z:.2f}} {u}<extra>{key}</extra>"
#             ),
#             name=f"{key} – part {idx + 1}" if len(polys) > 1 else key,
#             showlegend=False,
#         ))

#         # ── Edge loop overlay ──────────────────────────────────────────────────
#         if show_edge_loops:
#             ex, ey, ez = _polygon_outline_3d(poly, disp_len)
#             traces.append(go.Scatter3d(
#                 x=ex, y=ey, z=ez,
#                 mode="lines",
#                 line=dict(color=cfg.edge_color, width=2.0),
#                 showlegend=False,
#                 hoverinfo="skip",
#             ))

#     # ── Centroidal axis lines through the member ───────────────────────────────
#     if cfg.show_axes:
#         for zval, label in [(0.0, "Z–Z"), (None, None)]:
#             traces.append(go.Scatter3d(
#                 x=[0, 0], y=[0, 0], z=[0, disp_len],
#                 mode="lines+text",
#                 line=dict(color=cfg.axis_color, width=1.5, dash="dash"),
#                 text=["", "  member axis"],
#                 textfont=dict(size=9, color=cfg.axis_color),
#                 showlegend=False,
#                 hoverinfo="skip",
#             ))
#             break   # one member-axis line is enough

#     # ── Layout ────────────────────────────────────────────────────────────────
#     # Aspect ratio: true scale vs display scale
#     if cfg.true_scale_3d:
#         aspect = dict(x=zmax - zmin, y=ymax - ymin, z=disp_len)
#     else:
#         aspect = dict(x=zmax - zmin, y=ymax - ymin, z=disp_len)
#     # Normalise so the longest axis = 1 (Plotly "manual" aspectratio)
#     mx = max(abs(v) for v in aspect.values()) or 1.0
#     aspect = {k: v / mx for k, v in aspect.items()}

#     pad = max_dim * 0.15
#     scene = dict(
#         xaxis=dict(
#             title=f"z (section)  [{u}]",
#             range=[zmin - pad, zmax + pad],
#             backgroundcolor="rgba(245,245,250,0.6)",
#             showgrid=True, gridcolor="#DDDDDD",
#         ),
#         yaxis=dict(
#             title=f"y (section)  [{u}]",
#             range=[ymin - pad, ymax + pad],
#             backgroundcolor="rgba(245,250,245,0.6)",
#             showgrid=True, gridcolor="#DDDDDD",
#         ),
#         zaxis=dict(
#             title=f"Member axis  [{u}]",
#             range=[0, disp_len],
#             backgroundcolor="rgba(250,245,245,0.6)",
#             showgrid=True, gridcolor="#DDDDDD",
#         ),
#         aspectmode="manual",
#         aspectratio=aspect,
#         camera=dict(
#             eye=cfg.camera_eye,
#             up=dict(x=0, y=1, z=0),
#         ),
#         bgcolor="white",
#     )

#     layout = go.Layout(
#         title=dict(
#             text=(
#                 f"<b>{key}</b>  ·  {section_data.get('designation', '')} "
#                 f"  L = {len_note}"
#             ),
#             font=dict(size=13),
#             x=0.5,
#         ),
#         scene=scene,
#         paper_bgcolor="white",
#         width=cfg.fig_width_3d,
#         height=cfg.fig_height_3d,
#         margin=dict(l=0, r=0, t=50, b=0),
#     )

#     return go.Figure(data=traces, layout=layout)


# # ─────────────────────────────────────────────────────────────────────────────
# # 6.  Quick demo  (python graphing_plotly.py)
# # ─────────────────────────────────────────────────────────────────────────────

# if __name__ == "__main__":
#     import json, pathlib, sys

#     def _load(path: str) -> dict:
#         with open(path) as fh:
#             return json.load(fh)

#     cfg = PlotlyConfig(display_unit=LengthUnit.MM, show_properties=True)

#     # ── UB ────────────────────────────────────────────────────────────────────
#     ub_path = pathlib.Path(__file__).parent.parent / "UK" / "data" / "UB.json"
#     if ub_path.exists():
#         ub_db   = _load(str(ub_path))
#         ub_key  = "533x210x82"
#         ub_data = ub_db.get(ub_key)
#         if ub_data:
#             fig2 = plot_section_2d("UB", ub_data, cfg)
#             fig2.write_html("demo_UB_2d.html")
#             print(f"Saved demo_UB_2d.html  ({ub_key})")

#             fig3 = plot_section_3d("UB", ub_data, length=6000, config=cfg)
#             fig3.write_html("demo_UB_3d.html")
#             print(f"Saved demo_UB_3d.html  ({ub_key}, L=6000 mm)")
#         else:
#             print(f"[warn] '{ub_key}' not found in UB.json", file=sys.stderr)
#     else:
#         print("[warn] UB.json not found", file=sys.stderr)

#     # ── L_EQUAL_B2B ───────────────────────────────────────────────────────────
#     # lb_path = pathlib.Path(__file__).parent.parent / "UK" / "data" / "L_EQUAL_B2B.json"
#     # if lb_path.exists():
#     #     lb_db   = _load(str(lb_path))
#     #     lb_key  = "150x150x15.0"
#     #     lb_data = lb_db.get(lb_key)
#     #     if lb_data:
#     #         fig2 = plot_section_2d("L_EQUAL_B2B", lb_data, cfg)
#     #         fig2.write_html("demo_L_EQUAL_B2B_2d.html")
#     #         print(f"Saved demo_L_EQUAL_B2B_2d.html  ({lb_key})")

#     #         fig3 = plot_section_3d("L_EQUAL_B2B", lb_data, length=3000, config=cfg)
#     #         fig3.write_html("demo_L_EQUAL_B2B_3d.html")
#     #         print(f"Saved demo_L_EQUAL_B2B_3d.html  ({lb_key}, L=3000 mm)")
#     #     else:
#     #         print(f"[warn] '{lb_key}' not found in L_EQUAL_B2B.json", file=sys.stderr)
#     # else:
#     #     print("[warn] L_EQUAL_B2B.json not found", file=sys.stderr)