# """
# stress.py  -  2-D stress distribution plotting for steel sections.

# Provides stress-field plotting on section geometry for:
# - Matplotlib (static 2-D)
# - Plotly (interactive 2-D)

# Geometry is sourced from steelsnakes.base.graphing.get_geometry, so the same
# section builders are reused (including UB/UC root-radius geometry when present).
# """

# from __future__ import annotations

# from dataclasses import dataclass
# from typing import Any

# import numpy as np
# from matplotlib.figure import Figure
# from matplotlib.path import Path

# from steelsnakes.base.graphing import LengthUnit, _bbox, _cvt_arr, get_geometry, get_graphing_output_dir

# __all__ = [
#     "StressLoadCase",
#     "StressPlotConfig",
#     "compute_stress_grid",
#     "plot_stress_2d_matplotlib",
#     "plot_stress_2d_plotly",
#     "plot_stress_dashboard_2d_plotly",
# ]


# _TO_MM: dict[LengthUnit, float] = {
#     LengthUnit.MM: 1.0,
#     LengthUnit.CM: 10.0,
#     LengthUnit.M: 1_000.0,
# }


# @dataclass
# class StressLoadCase:
#     """Linear stress load case for a prismatic member section.

#     Units
#     -----
#     - axial_force_n: N
#     - shear_force_n: N (transverse shear, used for approximate tau map)
#     - moment_y_nu: N * display_unit (about y-axis)
#     - moment_z_nu: N * display_unit (about z-axis)

#     Resulting stress is returned as N / display_unit^2.
#     For display_unit = mm, this is MPa.
#     """

#     axial_force_n: float = 0.0
#     shear_force_n: float = 0.0
#     moment_y_nu: float = 0.0
#     moment_z_nu: float = 0.0


# @dataclass
# class StressPlotConfig:
#     """Rendering and discretization settings for 2-D stress plots."""

#     input_unit: LengthUnit = LengthUnit.MM
#     display_unit: LengthUnit = LengthUnit.MM
#     grid_nz: int = 260
#     grid_ny: int = 320
#     cmap: str = "coolwarm"
#     alpha: float = 0.82
#     show_outline: bool = True
#     show_axes: bool = True
#     show_centroid: bool = True
#     show_colorbar: bool = True
#     figure_size: tuple[float, float] = (9.0, 9.0)
#     dpi: int = 220
#     stress_label: str = "Stress [N/mm^2]"


# def _area_cm2_to_unit2(area_cm2: float, unit: LengthUnit) -> float:
#     # 1 cm^2 = 100 mm^2
#     area_mm2 = area_cm2 * 100.0
#     return area_mm2 / (_TO_MM[unit] ** 2)


# def _inertia_cm4_to_unit4(inertia_cm4: float, unit: LengthUnit) -> float:
#     # 1 cm^4 = 10,000 mm^4
#     inertia_mm4 = inertia_cm4 * 10_000.0
#     return inertia_mm4 / (_TO_MM[unit] ** 4)


# def _cvt_scalar(v: float, from_unit: LengthUnit, to_unit: LengthUnit) -> float:
#     return v * (_TO_MM[from_unit] / _TO_MM[to_unit])


# def _normalise_section_type(section_type: object) -> str:
#     if isinstance(section_type, str):
#         return section_type
#     value = getattr(section_type, "value", None)
#     return str(value) if value is not None else str(section_type)


# def _plotly_colorscale_name(cmap: str) -> str:
#     """Map common matplotlib colormap names to Plotly-compatible names."""
#     c = cmap.strip()
#     lut = {
#         "coolwarm": "RdBu_r",
#         "coolwarm_r": "RdBu",
#         "viridis": "Viridis",
#         "plasma": "Plasma",
#         "inferno": "Inferno",
#         "magma": "Magma",
#         "cividis": "Cividis",
#         "seismic": "RdBu",
#         "seismic_r": "RdBu_r",
#     }
#     return lut.get(c, c)


# def _build_mask(polys: list[np.ndarray], zz: np.ndarray, yy: np.ndarray) -> np.ndarray:
#     pts = np.column_stack([zz.ravel(), yy.ravel()])
#     mask = np.zeros(pts.shape[0], dtype=bool)
#     for poly in polys:
#         path = Path(poly)
#         mask |= path.contains_points(pts)
#     return mask.reshape(yy.shape)


# def _get_section_props(section_type_key: str, section_data: dict[str, Any]) -> tuple[float, float, float]:
#     if section_type_key in ("UB", "UC", "UBP"):
#         area_cm2 = float(section_data["A"])
#         iyy_cm4 = float(section_data["I_yy"])
#         izz_cm4 = float(section_data["I_zz"])
#         return area_cm2, iyy_cm4, izz_cm4

#     # Fallback for angle families where naming may differ
#     area_cm2 = float(section_data.get("A", section_data.get("total_area")))
#     iyy_cm4 = float(section_data.get("I_yy"))
#     izz_cm4 = float(section_data.get("I_zz", section_data.get("I_yy")))
#     return area_cm2, iyy_cm4, izz_cm4


# def _compute_components(
#     section_type: object,
#     section_data: dict[str, Any],
#     load_case: StressLoadCase,
#     config: StressPlotConfig,
# ) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[np.ndarray], np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
#     """Return stress components on the clipped section grid."""
#     key = _normalise_section_type(section_type)

#     polys = [_cvt_arr(p, config.input_unit, config.display_unit) for p in get_geometry(key, section_data)]
#     zmin, ymin, zmax, ymax = _bbox(polys)

#     z_vals = np.linspace(zmin, zmax, max(40, config.grid_nz))
#     y_vals = np.linspace(ymin, ymax, max(40, config.grid_ny))
#     zz, yy = np.meshgrid(z_vals, y_vals)
#     inside = _build_mask(polys, zz, yy)

#     area_cm2, iyy_cm4, izz_cm4 = _get_section_props(key, section_data)
#     area_u2 = _area_cm2_to_unit2(area_cm2, config.display_unit)
#     iyy_u4 = _inertia_cm4_to_unit4(iyy_cm4, config.display_unit)
#     izz_u4 = _inertia_cm4_to_unit4(izz_cm4, config.display_unit)

#     sigma_axial = load_case.axial_force_n / max(area_u2, 1e-12)
#     sigma_bending = (
#         - load_case.moment_y_nu * zz / max(iyy_u4, 1e-12)
#         - load_case.moment_z_nu * yy / max(izz_u4, 1e-12)
#     )
#     sigma_total = sigma_axial + sigma_bending

#     # Approximate transverse shear distribution.
#     if key in ("UB", "UC", "UBP") and all(k in section_data for k in ("h", "tf", "tw")):
#         h = _cvt_scalar(float(section_data["h"]), config.input_unit, config.display_unit)
#         tf = _cvt_scalar(float(section_data["tf"]), config.input_unit, config.display_unit)
#         tw = _cvt_scalar(float(section_data["tw"]), config.input_unit, config.display_unit)
#         y_web = max(h / 2.0 - tf, 1e-9)
#         aw = max(tw * 2.0 * y_web, 1e-12)
#         tau_max = 1.5 * load_case.shear_force_n / aw
#         tau = np.zeros_like(zz)
#         web_band = (np.abs(zz) <= tw / 2.0 + 1e-9) & (np.abs(yy) <= y_web + 1e-9)
#         tau_web = tau_max * (1.0 - (yy / y_web) ** 2)
#         tau = np.where(web_band, tau_web, 0.0)
#     else:
#         tau = np.full_like(zz, load_case.shear_force_n / max(area_u2, 1e-12))

#     sigma_axial_grid = np.where(inside, sigma_axial, np.nan)
#     sigma_bending_grid = np.where(inside, sigma_bending, np.nan)
#     sigma_total_grid = np.where(inside, sigma_total, np.nan)
#     tau_grid = np.where(inside, tau, np.nan)

#     return zz, yy, inside, polys, sigma_axial_grid, sigma_bending_grid, sigma_total_grid, tau_grid


# def _compute_longitudinal_depth_stress(
#     section_type: object,
#     section_data: dict[str, Any],
#     load_case: StressLoadCase,
#     config: StressPlotConfig,
#     nx: int = 180,
#     ny: int = 220,
# ) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
#     """Compute sigma(x,y) with x as normalized span and y as section depth axis.

#     Uses a linearized moment profile Mz(x) = Mz_end * x and constant N, V.
#     The stress map is based on: sigma = N/A - Mz(x) * y / Izz.
#     """

#     key = _normalise_section_type(section_type)
#     polys = [_cvt_arr(p, config.input_unit, config.display_unit) for p in get_geometry(key, section_data)]
#     _zmin, ymin, _zmax, ymax = _bbox(polys)

#     area_cm2, _iyy_cm4, izz_cm4 = _get_section_props(key, section_data)
#     area_u2 = _area_cm2_to_unit2(area_cm2, config.display_unit)
#     izz_u4 = _inertia_cm4_to_unit4(izz_cm4, config.display_unit)

#     x_vals = np.linspace(0.0, 1.0, max(80, nx))
#     y_vals = np.linspace(ymin, ymax, max(80, ny))
#     _xx, yy = np.meshgrid(x_vals, y_vals)

#     n_vals = np.full_like(x_vals, load_case.axial_force_n)
#     m_vals = load_case.moment_z_nu * x_vals

#     sigma = (n_vals[np.newaxis, :] / max(area_u2, 1e-12)) - ((m_vals[np.newaxis, :] * yy) / max(izz_u4, 1e-12))
#     return x_vals, y_vals, sigma, ymin, ymax


# def compute_stress_grid(
#     section_type: object,
#     section_data: dict[str, Any],
#     load_case: StressLoadCase,
#     config: StressPlotConfig | None = None,
# ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[np.ndarray], str]:
#     """Compute sigma(z,y) over a regular grid clipped to the section polygon.

#     Stress model (linear elastic + axial):
#       sigma = N/A - My*z/Iyy - Mz*y/Izz
#     """

#     cfg = config or StressPlotConfig()
#     zz, yy, inside, polys, _sa, _sb, sigma_masked, _tau = _compute_components(
#         section_type, section_data, load_case, cfg
#     )

#     if cfg.display_unit == LengthUnit.MM:
#         s_label = "Stress [MPa]"
#     else:
#         s_label = f"Stress [N/{cfg.display_unit.value}^2]"

#     return zz, yy, sigma_masked, inside, polys, s_label


# def plot_stress_2d_matplotlib(
#     section_type: object,
#     section_data: dict[str, Any],
#     load_case: StressLoadCase,
#     config: StressPlotConfig | None = None,
# ) -> Figure:
#     """Render sigma(x,y) as a 2-D matplotlib contour map (x/L vs depth y)."""

#     import matplotlib.pyplot as plt

#     cfg = config or StressPlotConfig()
#     x_vals, y_vals, sigma, ymin, ymax = _compute_longitudinal_depth_stress(
#         section_type,
#         section_data,
#         load_case,
#         cfg,
#     )

#     if cfg.display_unit == LengthUnit.MM:
#         s_label = "Stress [MPa]"
#     else:
#         s_label = f"Stress [N/{cfg.display_unit.value}^2]"

#     xx, yy = np.meshgrid(x_vals, y_vals)

#     fig, ax = plt.subplots(figsize=cfg.figure_size, dpi=cfg.dpi)
#     levels = 26
#     cs = ax.contourf(xx, yy, sigma, levels=levels, cmap=cfg.cmap, alpha=cfg.alpha)

#     if cfg.show_outline:
#         ax.plot([0.0, 1.0], [ymin, ymin], color="#1C3D5C", lw=1.8, zorder=3)
#         ax.plot([0.0, 1.0], [ymax, ymax], color="#1C3D5C", lw=1.8, zorder=3)

#     if cfg.show_axes:
#         ax.axhline(0.0, color="#C0392B", lw=1.0, ls="--", zorder=2)
#         ax.axvline(0.0, color="#C0392B", lw=1.0, ls="--", zorder=2)

#     if cfg.show_centroid:
#         ax.plot([0.0], [0.0], marker="+", ms=14, mew=2.2, color="#E74C3C", zorder=4)

#     span = max(ymax - ymin, 1e-9)
#     pad = 0.22 * span
#     unit = cfg.display_unit.value
#     ax.set_xlim(0.0, 1.0)
#     ax.set_ylim(ymin - pad, ymax + pad)
#     ax.set_xlabel("Normalized Span x/L")
#     ax.set_ylabel(f"y [{unit}]")
#     ax.set_title(
#         f"Longitudinal Stress Distribution  ·  {_normalise_section_type(section_type)}  ·  {section_data.get('designation', '')}"
#     )
#     ax.grid(True, ls=":", lw=0.45, alpha=0.45)

#     if cfg.show_colorbar:
#         cbar = fig.colorbar(cs, ax=ax, fraction=0.046, pad=0.04)
#         cbar.set_label(s_label)

#     fig.tight_layout()
#     return fig


# def plot_stress_2d_plotly(
#     section_type: object,
#     section_data: dict[str, Any],
#     load_case: StressLoadCase,
#     config: StressPlotConfig | None = None,
# ) -> Any:
#     """Render sigma(x,y) as an interactive 2-D Plotly heatmap (x/L vs depth y)."""

#     import plotly.graph_objects as go

#     cfg = config or StressPlotConfig()
#     x_vals, y_vals, sigma, ymin, ymax = _compute_longitudinal_depth_stress(
#         section_type,
#         section_data,
#         load_case,
#         cfg,
#     )

#     if cfg.display_unit == LengthUnit.MM:
#         s_label = "Stress [MPa]"
#     else:
#         s_label = f"Stress [N/{cfg.display_unit.value}^2]"

#     fig = go.Figure()
#     fig.add_trace(
#         go.Heatmap(
#             x=x_vals,
#             y=y_vals,
#             z=sigma,
#             colorscale=_plotly_colorscale_name(cfg.cmap),
#             colorbar={"title": s_label},
#             hovertemplate="x/L=%{x:.3f}<br>y=%{y:.2f}<br>sigma=%{z:.3f}<extra></extra>",
#             zsmooth=False,
#             showscale=cfg.show_colorbar,
#         )
#     )

#     if cfg.show_outline:
#         fig.add_trace(
#             go.Scatter(
#                 x=[0.0, 1.0],
#                 y=[ymin, ymin],
#                 mode="lines",
#                 line={"color": "#1C3D5C", "width": 2},
#                 hoverinfo="skip",
#                 showlegend=False,
#             )
#         )
#         fig.add_trace(
#             go.Scatter(
#                 x=[0.0, 1.0],
#                 y=[ymax, ymax],
#                 mode="lines",
#                 line={"color": "#1C3D5C", "width": 2},
#                 hoverinfo="skip",
#                 showlegend=False,
#             )
#         )

#     if cfg.show_axes:
#         fig.add_shape(type="line", x0=0.0, y0=0.0, x1=1.0, y1=0.0, line={"color": "#C0392B", "width": 1, "dash": "dash"})
#         fig.add_shape(type="line", x0=0.0, y0=ymin, x1=0.0, y1=ymax, line={"color": "#C0392B", "width": 1, "dash": "dash"})

#     if cfg.show_centroid:
#         fig.add_trace(
#             go.Scatter(
#                 x=[0.0],
#                 y=[0.0],
#                 mode="markers",
#                 marker={"symbol": "cross", "size": 11, "color": "#E74C3C"},
#                 hoverinfo="skip",
#                 showlegend=False,
#             )
#         )

#     span = max(ymax - ymin, 1e-9)
#     pad = 0.22 * span
#     unit = cfg.display_unit.value

#     fig.update_xaxes(title="Normalized Span x/L", range=[0.0, 1.0], showgrid=True)
#     fig.update_yaxes(title=f"y [{unit}]", range=[ymin - pad, ymax + pad], showgrid=True)

#     fig.update_layout(
#         template="plotly_white",
#         width=940,
#         height=840,
#         title={
#             "text": f"Longitudinal Stress Distribution  ·  {_normalise_section_type(section_type)}  ·  {section_data.get('designation', '')}",
#             "x": 0.5,
#         },
#         margin={"l": 60, "r": 30, "t": 70, "b": 60},
#     )
#     return fig


# def plot_stress_dashboard_2d_plotly(
#     section_type: object,
#     section_data: dict[str, Any],
#     config: StressPlotConfig | None = None,
#     cases: dict[str, StressLoadCase] | None = None,
# ) -> Any:
#     """Interactive stress dashboard with case-switch buttons and N-V-M diagrams.

#     Center panel: longitudinal-depth stress map sigma(x,y).
#     Right panels: engineering-style diagrams along normalized span:
#     - Axial force diagram N(x)
#     - Shear force diagram V(x)
#     - Bending moment diagram Mz(x)
#     """

#     import plotly.graph_objects as go
#     from plotly.subplots import make_subplots

#     cfg = config or StressPlotConfig()
#     if cases is None:
#         cases = {
#             "Pure Bending": StressLoadCase(axial_force_n=0.0, shear_force_n=0.0, moment_z_nu=220e6),
#             "Bending + Axial": StressLoadCase(axial_force_n=700e3, shear_force_n=220e3, moment_z_nu=180e6),
#             "Pure Axial": StressLoadCase(axial_force_n=1200e3, shear_force_n=0.0, moment_z_nu=0.0),
#         }

#     case_names = list(cases.keys())
#     case_data: dict[str, dict[str, Any]] = {}

#     global_abs = 1.0
#     for name, lc in cases.items():
#         zz, yy, _inside, polys, s_ax, s_b, s_t, tau = _compute_components(section_type, section_data, lc, cfg)
#         global_abs = max(global_abs, float(np.nanmax(np.abs(s_t))), float(np.nanmax(np.abs(tau))))
#         case_data[name] = {
#             "load_case": lc,
#             "zz": zz,
#             "yy": yy,
#             "polys": polys,
#             "sigma_ax": s_ax,
#             "sigma_b": s_b,
#             "sigma_t": s_t,
#             "tau": tau,
#         }

#     first = case_data[case_names[0]]
#     _zmin, ymin, _zmax, ymax = _bbox(first["polys"])
#     span_y = max(ymax - ymin, 1e-9)
#     pad_y = 0.20 * span_y

#     key = _normalise_section_type(section_type)
#     area_cm2, _iyy_cm4, izz_cm4 = _get_section_props(key, section_data)
#     area_u2 = _area_cm2_to_unit2(area_cm2, cfg.display_unit)
#     izz_u4 = _inertia_cm4_to_unit4(izz_cm4, cfg.display_unit)
#     unit = cfg.display_unit.value

#     fig = make_subplots(
#         rows=3,
#         cols=2,
#         specs=[
#             [{"type": "heatmap", "rowspan": 3}, {"type": "xy"}],
#             [None, {"type": "xy"}],
#             [None, {"type": "xy"}],
#         ],
#         column_widths=[0.70, 0.30],
#         row_heights=[0.34, 0.33, 0.33],
#         horizontal_spacing=0.08,
#         vertical_spacing=0.10,
#         subplot_titles=(
#             "Total Stress Field",
#             "Axial Force Diagram  N(x)",
#             "Shear Force Diagram  V(x)",
#             "Bending Moment Diagram  Mz(x)",
#         ),
#     )

#     for idx, name in enumerate(case_names):
#         d = case_data[name]
#         lc = d["load_case"]

#         x_span = np.linspace(0.0, 1.0, 180)
#         y_vals = np.linspace(ymin, ymax, 200)
#         xx, yy_map = np.meshgrid(x_span, y_vals)

#         n_vals = np.full_like(x_span, lc.axial_force_n)
#         v_vals = np.full_like(x_span, lc.shear_force_n)
#         # Linearized moment diagram ending at moment_z_nu.
#         m_vals = lc.moment_z_nu * x_span

#         sigma_x_y = (n_vals[np.newaxis, :] / max(area_u2, 1e-12)) - (
#             (m_vals[np.newaxis, :] * yy_map) / max(izz_u4, 1e-12)
#         )

#         fig.add_trace(
#             go.Heatmap(
#                 x=x_span,
#                 y=y_vals,
#                 z=sigma_x_y,
#                 colorscale=_plotly_colorscale_name(cfg.cmap),
#                 zmin=-global_abs,
#                 zmax=global_abs,
#                 colorbar={"title": "Stress [MPa]" if cfg.display_unit == LengthUnit.MM else f"Stress [N/{unit}^2]"},
#                 showscale=(idx == 0),
#                 hovertemplate="x/L=%{x:.3f}<br>y=%{y:.2f}<br>sigma=%{z:.3f}<extra></extra>",
#             ),
#             row=1,
#             col=1,
#         )

#         fig.add_trace(
#             go.Scatter(
#                 x=x_span,
#                 y=n_vals,
#                 mode="lines",
#                 line={"color": "#1f77b4", "width": 2.3},
#                 fill="tozeroy",
#                 fillcolor="rgba(31,119,180,0.20)",
#                 name="N(x)",
#                 showlegend=(idx == 0),
#                 hovertemplate="x=%{x:.2f}<br>N=%{y:.3e} N<extra></extra>",
#             ),
#             row=1,
#             col=2,
#         )
#         fig.add_trace(
#             go.Scatter(
#                 x=x_span,
#                 y=v_vals,
#                 mode="lines",
#                 line={"color": "#2ca02c", "width": 2.3},
#                 fill="tozeroy",
#                 fillcolor="rgba(44,160,44,0.20)",
#                 name="V(x)",
#                 showlegend=(idx == 0),
#                 hovertemplate="x=%{x:.2f}<br>V=%{y:.3e} N<extra></extra>",
#             ),
#             row=2,
#             col=2,
#         )
#         fig.add_trace(
#             go.Scatter(
#                 x=x_span,
#                 y=m_vals,
#                 mode="lines",
#                 line={"color": "#d62728", "width": 2.3},
#                 fill="tozeroy",
#                 fillcolor="rgba(214,39,40,0.20)",
#                 name="Mz(x)",
#                 showlegend=(idx == 0),
#                 hovertemplate="x=%{x:.2f}<br>Mz=%{y:.3e} N·u<extra></extra>",
#             ),
#             row=3,
#             col=2,
#         )

#         # outlines and guides on heatmap panel
#         fig.add_trace(
#             go.Scatter(x=[0.0, 1.0], y=[0.0, 0.0], mode="lines", line={"color": "#C0392B", "dash": "dash", "width": 1}, showlegend=False, hoverinfo="skip"),
#             row=1,
#             col=1,
#         )
#         fig.add_trace(
#             go.Scatter(x=[0.0, 1.0], y=[ymin, ymin], mode="lines", line={"color": "#1C3D5C", "width": 1.5}, showlegend=False, hoverinfo="skip"),
#             row=1,
#             col=1,
#         )
#         fig.add_trace(
#             go.Scatter(x=[0.0, 1.0], y=[ymax, ymax], mode="lines", line={"color": "#1C3D5C", "width": 1.5}, showlegend=False, hoverinfo="skip"),
#             row=1,
#             col=1,
#         )

#     # Toggle visibility by case
#     total_traces = len(fig.data)
#     traces_per_case = total_traces // max(len(case_names), 1)
#     buttons = []
#     for i, name in enumerate(case_names):
#         vis = [False] * total_traces
#         start = i * traces_per_case
#         end = (i + 1) * traces_per_case
#         for j in range(start, end):
#             vis[j] = True
#         buttons.append(
#             dict(
#                 label=name,
#                 method="update",
#                 args=[
#                     {"visible": vis},
#                     {"title": f"Stress Dashboard  ·  {_normalise_section_type(section_type)}  ·  {section_data.get('designation', '')}  ·  {name}"},
#                 ],
#             )
#         )

#     # default to first case
#     vis0 = [False] * total_traces
#     for j in range(0, traces_per_case):
#         vis0[j] = True
#     for j in range(total_traces):
#         fig.data[j].visible = vis0[j]

#     fig.update_xaxes(title="Normalized Span x/L", range=[0.0, 1.0], row=1, col=1)
#     fig.update_yaxes(title=f"Depth y [{unit}]", range=[ymin - pad_y, ymax + pad_y], row=1, col=1)

#     fig.update_xaxes(title="Normalized Span x/L", range=[0.0, 1.0], row=1, col=2)
#     fig.update_yaxes(title="N [N]", row=1, col=2)
#     fig.update_xaxes(title="Normalized Span x/L", range=[0.0, 1.0], row=2, col=2)
#     fig.update_yaxes(title="V [N]", row=2, col=2)
#     fig.update_xaxes(title="Normalized Span x/L", range=[0.0, 1.0], row=3, col=2)
#     fig.update_yaxes(title=f"Mz [N·{unit}]", row=3, col=2)

#     fig.update_layout(
#         template="plotly_white",
#         width=1280,
#         height=980,
#         title=f"Stress Dashboard  ·  {_normalise_section_type(section_type)}  ·  {section_data.get('designation', '')}  ·  {case_names[0]}",
#         margin={"l": 50, "r": 40, "t": 90, "b": 50},
#         updatemenus=[
#             {
#                 "type": "dropdown",
#                 "x": 0.01,
#                 "y": 1.12,
#                 "xanchor": "left",
#                 "yanchor": "top",
#                 "buttons": buttons,
#                 "showactive": True,
#             }
#         ],
#         annotations=[
#             {
#                 "xref": "paper",
#                 "yref": "paper",
#                 "x": 0.01,
#                 "y": 1.17,
#                 "text": "Load Case",
#                 "showarrow": False,
#                 "font": {"size": 12},
#             }
#         ],
#         legend={"orientation": "h", "x": 0.66, "y": 1.12},
#     )

#     return fig


# if __name__ == "__main__":
#     import json
#     import pathlib

#     db_path = pathlib.Path(__file__).parent.parent / "UK" / "data" / "UB.json"
#     if not db_path.exists():
#         raise SystemExit("UB.json not found")

#     db = json.loads(db_path.read_text(encoding="utf-8"))
#     key = "533x210x82"
#     sec = db[key]

#     # Example: major-axis-type bending using Mz term in this coordinate setup.
#     loads = StressLoadCase(axial_force_n=0.0, moment_y_nu=0.0, moment_z_nu=220e6)
#     cfg = StressPlotConfig(display_unit=LengthUnit.MM)

#     out = get_graphing_output_dir()

#     fig_mpl = plot_stress_2d_matplotlib("UB", sec, loads, cfg)
#     p_mpl = out / "UB_Stress_2D_matplotlib.png"
#     fig_mpl.savefig(p_mpl, dpi=cfg.dpi, bbox_inches="tight")

#     fig_pl = plot_stress_2d_plotly("UB", sec, loads, cfg)
#     p_pl = out / "UB_Stress_2D_plotly.html"
#     fig_pl.write_html(str(p_pl), include_plotlyjs="cdn", config={"responsive": True, "scrollZoom": True})

#     fig_dash = plot_stress_dashboard_2d_plotly("UB", sec, cfg)
#     p_dash = out / "UB_Stress_Dashboard_plotly.html"
#     fig_dash.write_html(str(p_dash), include_plotlyjs="cdn", config={"responsive": True, "scrollZoom": True})

#     print(f"Saved {p_mpl}")
#     print(f"Saved {p_pl}")
#     print(f"Saved {p_dash}")
