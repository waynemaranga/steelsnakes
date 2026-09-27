# """
# graphing_plotly.py  -  Interactive steel section visualisation with Plotly.

# This module mirrors the intent of `steelsnakes.base.graphing` but returns
# Plotly figures for interactive pan/zoom/rotate workflows.

# Supported section geometry is inherited from `steelsnakes.base.graphing`
# through `get_geometry(...)`, so any runtime geometry registrations are reused.
# """

# from __future__ import annotations

# import importlib
# from dataclasses import dataclass
# from enum import Enum
# from typing import Any, Optional

# import numpy as np

# from steelsnakes.base.graphing import get_geometry

# __all__ = [
#     "LengthUnit",
#     "PlotlyConfig",
#     "DEFAULT_PLOTLY_CONFIG",
#     "plot_section_2d_plotly",
#     "plot_section_3d_plotly",
# ]


# class LengthUnit(Enum):
#     """Linear unit identifiers for section dimension data."""

#     MM = "mm"
#     CM = "cm"
#     M = "m"


# _TO_MM: dict[LengthUnit, float] = {
#     LengthUnit.MM: 1.0,
#     LengthUnit.CM: 10.0,
#     LengthUnit.M: 1_000.0,
# }


# @dataclass
# class PlotlyConfig:
#     """Centralized settings for Plotly section plotting."""

#     input_unit: LengthUnit = LengthUnit.MM
#     display_unit: LengthUnit = LengthUnit.MM

#     # 2D layout size
#     width_2d: int = 900
#     height_2d: int = 760

#     # 3D layout size
#     width_3d: int = 1100
#     height_3d: int = 760

#     # Style
#     section_color: str = "#3A6EA5"
#     section_edge_color: str = "#1C3D5C"
#     section_alpha: float = 0.82
#     cap_color: str = "#264E7A"
#     cap_alpha: float = 0.95
#     axis_color: str = "#C0392B"
#     dim_color: str = "#4A4A4A"
#     centroid_color: str = "#E74C3C"

#     # Feature toggles
#     show_axes: bool = True
#     show_centroid: bool = True
#     show_dimensions: bool = True
#     show_properties: bool = True

#     # Future stress overlay controls (not yet rendered)
#     show_stress_overlay: bool = False
#     stress_cmap: str = "RdBu_r"
#     stress_alpha: float = 0.60
#     stress_label: str = "sigma"

#     # 3D display behavior
#     true_scale_3d: bool = False
#     camera_eye_x: float = -1.9
#     camera_eye_y: float = -1.45
#     camera_eye_z: float = 1.35


# DEFAULT_PLOTLY_CONFIG = PlotlyConfig()


# def _go():
#     try:
#         go_module = importlib.import_module("plotly" + "." + "graph_objects")
#     except ImportError as exc:  # pragma: no cover - exercised when plotly is missing
#         raise ImportError(
#             "Plotly is required for steelsnakes.base.graphing_plotly. "
#             "Install it with: pip install plotly"
#         ) from exc
#     return go_module


# def _normalise_section_type(section_type: object) -> str:
#     if isinstance(section_type, str):
#         return section_type
#     value = getattr(section_type, "value", None)
#     return str(value) if value is not None else str(section_type)


# def _cvt(value: float, from_unit: LengthUnit, to_unit: LengthUnit) -> float:
#     return value * _TO_MM[from_unit] / _TO_MM[to_unit]


# def _cvt_arr(arr: np.ndarray, from_unit: LengthUnit, to_unit: LengthUnit) -> np.ndarray:
#     return arr * (_TO_MM[from_unit] / _TO_MM[to_unit])


# def _bbox(polygons: list[np.ndarray]) -> tuple[float, float, float, float]:
#     pts = np.concatenate(polygons, axis=0)
#     return float(pts[:, 0].min()), float(pts[:, 1].min()), float(pts[:, 0].max()), float(pts[:, 1].max())


# def _hex_to_rgba(hex_color: str, alpha: float) -> str:
#     c = hex_color.lstrip("#")
#     if len(c) != 6:
#         return hex_color
#     r = int(c[0:2], 16)
#     g = int(c[2:4], 16)
#     b = int(c[4:6], 16)
#     return f"rgba({r},{g},{b},{alpha:.3f})"


# def _add_dim_h(
#     fig: Any,
#     y_arrow: float,
#     z0: float,
#     z1: float,
#     z_label: float,
#     y_label: float,
#     label: str,
#     cfg: PlotlyConfig,
# ) -> None:
#     fig.add_annotation(
#         x=z1,
#         y=y_arrow,
#         ax=z0,
#         ay=y_arrow,
#         xref="x",
#         yref="y",
#         axref="x",
#         ayref="y",
#         showarrow=True,
#         arrowside="end+start",
#         arrowhead=3,
#         arrowwidth=1,
#         arrowcolor=cfg.dim_color,
#     )
#     fig.add_annotation(
#         x=z_label,
#         y=y_label,
#         text=label,
#         showarrow=False,
#         xref="x",
#         yref="y",
#         font={"size": 11, "color": cfg.dim_color},
#     )


# def _add_dim_v(
#     fig: Any,
#     z_arrow: float,
#     y0: float,
#     y1: float,
#     z_label: float,
#     y_label: float,
#     label: str,
#     cfg: PlotlyConfig,
# ) -> None:
#     fig.add_annotation(
#         x=z_arrow,
#         y=y1,
#         ax=z_arrow,
#         ay=y0,
#         xref="x",
#         yref="y",
#         axref="x",
#         ayref="y",
#         showarrow=True,
#         arrowside="end+start",
#         arrowhead=3,
#         arrowwidth=1,
#         arrowcolor=cfg.dim_color,
#     )
#     fig.add_annotation(
#         x=z_label,
#         y=y_label,
#         text=label,
#         showarrow=False,
#         xref="x",
#         yref="y",
#         font={"size": 11, "color": cfg.dim_color},
#         xanchor="left",
#     )


# def _add_extension_line_h(fig: Any, z0: float, z1: float, y: float, cfg: PlotlyConfig) -> None:
#     fig.add_shape(
#         type="line",
#         x0=z0,
#         x1=z1,
#         y0=y,
#         y1=y,
#         line={"color": cfg.dim_color, "width": 1, "dash": "dot"},
#     )


# def _add_dims_ub(fig: Any, data: dict[str, Any], polys_d: list[np.ndarray], cfg: PlotlyConfig) -> None:
#     h_d = _cvt(float(data["h"]), cfg.input_unit, cfg.display_unit)
#     b_d = _cvt(float(data["b"]), cfg.input_unit, cfg.display_unit)
#     tw_d = _cvt(float(data["tw"]), cfg.input_unit, cfg.display_unit)
#     tf_d = _cvt(float(data["tf"]), cfg.input_unit, cfg.display_unit)
#     unit = cfg.display_unit.value

#     zmin, ymin, zmax, ymax = _bbox(polys_d)
#     gz = (zmax - zmin) * 0.07
#     gy = (ymax - ymin) * 0.07

#     _add_dim_h(
#         fig,
#         y_arrow=ymax + 1.4 * gy,
#         z0=-b_d / 2,
#         z1=b_d / 2,
#         z_label=0.0,
#         y_label=ymax + 1.78 * gy,
#         label=f"b = {b_d:.1f} {unit}",
#         cfg=cfg,
#     )

#     _add_dim_v(
#         fig,
#         z_arrow=zmax + 1.5 * gz,
#         y0=-h_d / 2,
#         y1=h_d / 2,
#         z_label=zmax + 1.86 * gz,
#         y_label=0.0,
#         label=f"h = {h_d:.1f} {unit}",
#         cfg=cfg,
#     )

#     _add_dim_h(
#         fig,
#         y_arrow=ymin - 1.4 * gy,
#         z0=-tw_d / 2,
#         z1=tw_d / 2,
#         z_label=0.0,
#         y_label=ymin - 1.78 * gy,
#         label=f"tw = {tw_d:.1f} {unit}",
#         cfg=cfg,
#     )

#     z_tf_arrow = zmax + 4.2 * gz
#     _add_dim_v(
#         fig,
#         z_arrow=z_tf_arrow,
#         y0=h_d / 2 - tf_d,
#         y1=h_d / 2,
#         z_label=z_tf_arrow + 0.35 * gz,
#         y_label=h_d / 2 - tf_d / 2,
#         label=f"tf = {tf_d:.1f} {unit}",
#         cfg=cfg,
#     )
#     _add_extension_line_h(fig, zmax, z_tf_arrow, h_d / 2, cfg)
#     _add_extension_line_h(fig, zmax, z_tf_arrow, h_d / 2 - tf_d, cfg)


# def _add_dims_l_equal_b2b(
#     fig: Any,
#     data: dict[str, Any],
#     polys_d: list[np.ndarray],
#     cfg: PlotlyConfig,
# ) -> None:
#     leg_d = _cvt(float(data["hxh"].split("x")[0]), cfg.input_unit, cfg.display_unit)
#     t_d = _cvt(float(data["t"]), cfg.input_unit, cfg.display_unit)
#     n_y_d = _cvt(float(data["n_y"]), cfg.input_unit, cfg.display_unit)
#     unit = cfg.display_unit.value

#     zmin, ymin, zmax, ymax = _bbox(polys_d)
#     gz = (zmax - zmin) * 0.07
#     gy = (ymax - ymin) * 0.07

#     yo = -n_y_d

#     _add_dim_h(
#         fig,
#         y_arrow=ymin - 1.4 * gy,
#         z0=-leg_d,
#         z1=leg_d,
#         z_label=0.0,
#         y_label=ymin - 1.78 * gy,
#         label=f"2h = {2 * leg_d:.1f} {unit}",
#         cfg=cfg,
#     )

#     _add_dim_v(
#         fig,
#         z_arrow=zmax + 1.5 * gz,
#         y0=yo,
#         y1=yo + leg_d,
#         z_label=zmax + 1.86 * gz,
#         y_label=yo + leg_d / 2,
#         label=f"h = {leg_d:.1f} {unit}",
#         cfg=cfg,
#     )

#     z_t_arrow = zmax + 4.2 * gz
#     _add_dim_v(
#         fig,
#         z_arrow=z_t_arrow,
#         y0=yo,
#         y1=yo + t_d,
#         z_label=z_t_arrow + 0.35 * gz,
#         y_label=yo + t_d / 2,
#         label=f"t = {t_d:.1f} {unit}",
#         cfg=cfg,
#     )
#     _add_extension_line_h(fig, zmax, z_t_arrow, yo, cfg)
#     _add_extension_line_h(fig, zmax, z_t_arrow, yo + t_d, cfg)


# def _add_props_table(fig: Any, key: str, data: dict[str, Any]) -> None:
#     rows: list[tuple[str, str]] = [
#         ("Designation", str(data.get("designation", "-"))),
#     ]

#     def _f(k: str, fmt: str = ",.0f") -> str:
#         v = data.get(k)
#         return format(v, fmt) if v is not None else "-"

#     if key in ("UB", "UC", "UBP"):
#         rows += [
#             ("mass [kg/m]", _f("mass_per_metre", ".1f")),
#             ("A [cm2]", _f("A")),
#             ("Iyy [cm4]", _f("I_yy")),
#             ("Izz [cm4]", _f("I_zz")),
#             ("Wpl,yy [cm3]", _f("W_pl_yy")),
#             ("It [cm4]", _f("I_t")),
#         ]
#     elif key == "L_EQUAL_B2B":
#         rows += [
#             ("mass [kg/m]", _f("total_mass_per_metre", ".1f")),
#             ("A [cm2]", _f("total_area", ".1f")),
#             ("Iyy [cm4]", _f("I_yy", ".1f")),
#             ("Wel,yy [cm3]", _f("W_el_yy", ".1f")),
#         ]

#     text = "<br>".join(f"{k}: {v}" for k, v in rows)
#     fig.add_annotation(
#         x=0.02,
#         y=0.02,
#         xref="paper",
#         yref="paper",
#         text=text,
#         showarrow=False,
#         align="left",
#         bgcolor="rgba(255,255,255,0.90)",
#         bordercolor="#BBBBBB",
#         borderwidth=1,
#         font={"size": 11, "family": "Courier New"},
#     )


# def plot_section_2d_plotly(
#     section_type: "str | Any",
#     section_data: dict[str, Any],
#     config: Optional[PlotlyConfig] = None,
# ) -> Any:
#     """Create an interactive 2-D to-scale section plot with Plotly."""

#     cfg = config or DEFAULT_PLOTLY_CONFIG
#     key = _normalise_section_type(section_type)

#     polys = [_cvt_arr(p, cfg.input_unit, cfg.display_unit) for p in get_geometry(key, section_data)]
#     zmin, ymin, zmax, ymax = _bbox(polys)
#     width = zmax - zmin
#     height = ymax - ymin

#     go = _go()
#     fig = go.Figure()

#     fill_color = _hex_to_rgba(cfg.section_color, cfg.section_alpha)
#     for idx, poly in enumerate(polys):
#         fig.add_trace(
#             go.Scatter(
#                 x=poly[:, 0],
#                 y=poly[:, 1],
#                 mode="lines",
#                 fill="toself",
#                 line={"color": cfg.section_edge_color, "width": 2},
#                 fillcolor=fill_color,
#                 hoverinfo="skip",
#                 name="Section" if idx == 0 else "Section part",
#                 showlegend=idx == 0,
#             )
#         )

#     if cfg.show_axes:
#         pad_z = width * 0.28
#         pad_y = height * 0.28
#         fig.add_shape(
#             type="line",
#             x0=zmin - pad_z,
#             x1=zmax + pad_z,
#             y0=0,
#             y1=0,
#             line={"color": cfg.axis_color, "width": 1, "dash": "dash"},
#         )
#         fig.add_shape(
#             type="line",
#             x0=0,
#             x1=0,
#             y0=ymin - pad_y,
#             y1=ymax + pad_y,
#             line={"color": cfg.axis_color, "width": 1, "dash": "dash"},
#         )
#         fig.add_annotation(
#             x=zmax + 0.17 * width,
#             y=0,
#             text="Y-Y",
#             font={"size": 11, "color": cfg.axis_color},
#             showarrow=False,
#         )
#         fig.add_annotation(
#             x=0,
#             y=ymax + 0.17 * height,
#             text="Z-Z",
#             font={"size": 11, "color": cfg.axis_color},
#             showarrow=False,
#         )

#     if cfg.show_centroid:
#         fig.add_trace(
#             go.Scatter(
#                 x=[0],
#                 y=[0],
#                 mode="markers",
#                 marker={"symbol": "cross", "size": 12, "color": cfg.centroid_color},
#                 name="Centroid",
#             )
#         )

#     if cfg.show_dimensions:
#         if key in ("UB", "UC", "UBP"):
#             _add_dims_ub(fig, section_data, polys, cfg)
#         elif key == "L_EQUAL_B2B":
#             _add_dims_l_equal_b2b(fig, section_data, polys, cfg)

#     if cfg.show_properties:
#         _add_props_table(fig, key, section_data)

#     pad_z = width * 0.50
#     pad_y = height * 0.50
#     unit = cfg.display_unit.value
#     fig.update_xaxes(
#         title=f"z [{unit}]",
#         range=[zmin - pad_z, zmax + pad_z],
#         showgrid=True,
#         gridcolor="rgba(0,0,0,0.12)",
#         zeroline=False,
#     )
#     fig.update_yaxes(
#         title=f"y [{unit}]",
#         range=[ymin - pad_y, ymax + pad_y],
#         scaleanchor="x",
#         scaleratio=1,
#         showgrid=True,
#         gridcolor="rgba(0,0,0,0.12)",
#         zeroline=False,
#     )

#     fig.update_layout(
#         template="plotly_white",
#         width=cfg.width_2d,
#         height=cfg.height_2d,
#         title={"text": f"{key}  ·  {section_data.get('designation', '')}", "x": 0.5},
#         margin={"l": 50, "r": 40, "t": 70, "b": 60},
#         legend={"orientation": "h", "yanchor": "bottom", "y": 1.01, "x": 0.0},
#     )

#     return fig


# def _signed_area(pts: np.ndarray) -> float:
#     x, y = pts[:, 0], pts[:, 1]
#     return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


# def _pt_in_tri(p: np.ndarray, a: np.ndarray, b: np.ndarray, c: np.ndarray) -> bool:
#     def _side(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
#         return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

#     d1, d2, d3 = _side(p, a, b), _side(p, b, c), _side(p, c, a)
#     has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
#     has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
#     return not (has_neg and has_pos)


# def _triangulate_polygon(pts2d: np.ndarray) -> list[tuple[int, int, int]]:
#     pts = pts2d.copy()
#     n = len(pts)
#     if n < 3:
#         return []
#     if n == 3:
#         return [(0, 1, 2)]

#     if _signed_area(pts) < 0:
#         pts = pts[::-1].copy()
#         orig = list(range(n - 1, -1, -1))
#     else:
#         orig = list(range(n))

#     remaining = list(range(n))
#     tris_local: list[tuple[int, int, int]] = []
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

#             cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
#             if cross <= 1e-10:
#                 continue

#             is_ear = True
#             for j in remaining:
#                 if j in (i_prev, i_curr, i_next):
#                     continue
#                 if _pt_in_tri(pts[j], a, b, c):
#                     is_ear = False
#                     break
#             if is_ear:
#                 tris_local.append((i_prev, i_curr, i_next))
#                 remaining.pop(idx)
#                 ear_found = True
#                 break

#         if not ear_found:
#             break

#     if len(remaining) == 3:
#         tris_local.append((remaining[0], remaining[1], remaining[2]))

#     return [(orig[a], orig[b], orig[c]) for (a, b, c) in tris_local]


# def _build_member_mesh(poly2d: np.ndarray, length: float) -> dict[str, list[float] | list[int]]:
#     n = len(poly2d)
#     xs = np.concatenate([poly2d[:, 0], poly2d[:, 0]])
#     ys = np.concatenate([poly2d[:, 1], poly2d[:, 1]])
#     zs = np.concatenate([np.zeros(n), np.full(n, length)])

#     fi: list[int] = []
#     fj: list[int] = []
#     fk: list[int] = []

#     for e in range(n):
#         e1 = (e + 1) % n
#         fi += [e, e, n + e]
#         fj += [e1, n + e1, n + e1]
#         fk += [n + e1, n + e, e1]

#     cap_tris = _triangulate_polygon(poly2d)
#     for (a, b, c) in cap_tris:
#         fi.append(a)
#         fj.append(c)
#         fk.append(b)
#         fi.append(n + a)
#         fj.append(n + b)
#         fk.append(n + c)

#     return {
#         "x": xs.tolist(),
#         "y": ys.tolist(),
#         "z": zs.tolist(),
#         "i": fi,
#         "j": fj,
#         "k": fk,
#     }


# def _polygon_outline_3d(poly2d: np.ndarray, length: float) -> tuple[list[float], list[float], list[float]]:
#     n = len(poly2d)
#     x: list[float] = []
#     y: list[float] = []
#     z: list[float] = []

#     def _ring(z_level: float) -> None:
#         for pt in poly2d:
#             x.append(float(pt[0]))
#             y.append(float(pt[1]))
#             z.append(z_level)
#         x.append(float(poly2d[0, 0]))
#         y.append(float(poly2d[0, 1]))
#         z.append(z_level)
#         x.append(None)  # type: ignore[arg-type]
#         y.append(None)  # type: ignore[arg-type]
#         z.append(None)  # type: ignore[arg-type]

#     _ring(0.0)
#     _ring(length)

#     step = max(1, n // 5)
#     for i in range(0, n, step):
#         x += [float(poly2d[i, 0]), float(poly2d[i, 0]), None]  # type: ignore[list-item]
#         y += [float(poly2d[i, 1]), float(poly2d[i, 1]), None]  # type: ignore[list-item]
#         z += [0.0, float(length), None]  # type: ignore[list-item]

#     return x, y, z


# def plot_section_3d_plotly(
#     section_type: "str | Any",
#     section_data: dict[str, Any],
#     length: float,
#     config: Optional[PlotlyConfig] = None,
# ) -> Any:
#     """Create an interactive 3-D member render by extrusion along the member axis."""

#     cfg = config or DEFAULT_PLOTLY_CONFIG
#     key = _normalise_section_type(section_type)

#     polys = [_cvt_arr(p, cfg.input_unit, cfg.display_unit) for p in get_geometry(key, section_data)]
#     length_d = _cvt(length, cfg.input_unit, cfg.display_unit)

#     zmin, ymin, zmax, ymax = _bbox(polys)
#     max_dim = max(zmax - zmin, ymax - ymin)

#     if cfg.true_scale_3d:
#         display_len = length_d
#         len_note = f"{length_d:.2f} {cfg.display_unit.value}"
#     else:
#         display_len = max_dim * 5.0
#         len_note = f"{length_d:.2f} {cfg.display_unit.value} (section scaled for clarity)"

#     go = _go()
#     fig = go.Figure()

#     for poly in polys:
#         unique = poly[:-1]
#         mesh = _build_member_mesh(unique, display_len)

#         fig.add_trace(
#             go.Mesh3d(
#                 x=mesh["x"],
#                 y=mesh["y"],
#                 z=mesh["z"],
#                 i=mesh["i"],
#                 j=mesh["j"],
#                 k=mesh["k"],
#                 color=cfg.section_color,
#                 opacity=cfg.section_alpha,
#                 flatshading=True,
#                 hoverinfo="skip",
#                 showscale=False,
#             )
#         )

#         edge_x, edge_y, edge_z = _polygon_outline_3d(unique, display_len)
#         fig.add_trace(
#             go.Scatter3d(
#                 x=edge_x,
#                 y=edge_y,
#                 z=edge_z,
#                 mode="lines",
#                 line={"color": cfg.section_edge_color, "width": 2},
#                 hoverinfo="skip",
#                 showlegend=False,
#             )
#         )

#     x_span = max(zmax - zmin, 1e-9)
#     y_span = max(ymax - ymin, 1e-9)
#     z_span = max(display_len, 1e-9)
#     span_max = max(x_span, y_span, z_span)
#     aspect = {
#         "x": x_span / span_max,
#         "y": y_span / span_max,
#         "z": z_span / span_max,
#     }
#     pad_xy = max(0.08 * max(x_span, y_span), 1e-6)
#     pad_z0 = 0.04 * z_span
#     pad_z1 = 0.06 * z_span

#     unit = cfg.display_unit.value
#     fig.update_layout(
#         template="plotly_white",
#         width=cfg.width_3d,
#         height=cfg.height_3d,
#         title={"text": f"{key}  ·  {section_data.get('designation', '')}   L = {len_note}", "x": 0.5},
#         margin={"l": 10, "r": 10, "t": 60, "b": 10},
#         showlegend=False,
#         scene={
#             "xaxis": {"title": f"z [{unit}]", "range": [zmin - pad_xy, zmax + pad_xy]},
#             "yaxis": {"title": f"y [{unit}]", "range": [ymin - pad_xy, ymax + pad_xy]},
#             "zaxis": {"title": f"Member axis [{unit}]", "range": [-pad_z0, display_len + pad_z1]},
#             "aspectmode": "manual",
#             "aspectratio": aspect,
#             "camera": {
#                 "eye": {"x": cfg.camera_eye_x, "y": cfg.camera_eye_y, "z": cfg.camera_eye_z},
#             },
#         },
#         scene_dragmode="orbit",
#     )

#     return fig


# if __name__ == "__main__":
#     import json
#     import pathlib

#     base = pathlib.Path(__file__).parent.parent / "UK" / "data"
#     ub_path = base / "UB.json"

#     if ub_path.exists():
#         with open(ub_path, encoding="utf-8") as fh:
#             db = json.load(fh)
#         section = db.get("533x210x82")
#         if section:
#             cfg = PlotlyConfig(display_unit=LengthUnit.MM, show_properties=True)
#             fig2 = plot_section_2d_plotly("UB", section, cfg)
#             fig2.write_html(
#                 "demo_plotly_UB_2d.html",
#                 include_plotlyjs="cdn",
#                 config={"responsive": True, "scrollZoom": True},
#             )

#             fig3 = plot_section_3d_plotly("UB", section, length=6000, config=cfg)
#             fig3.write_html(
#                 "demo_plotly_UB_3d.html",
#                 include_plotlyjs="cdn",
#                 config={"responsive": True, "scrollZoom": True},
#             )
#             print("Saved demo_plotly_UB_2d.html and demo_plotly_UB_3d.html")
