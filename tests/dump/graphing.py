# """
# graphing.py  —  Steel section visualisation
# ============================================

# Produces to-scale 2-D cross-section plots and 3-D member renders from
# section property dictionaries loaded from the Blue Book / library JSON files.

# Typical usage
# -------------
# >>> import json
# >>> from graphing import plot_section_2d, plot_section_3d, PlotConfig, LengthUnit
# >>>
# >>> with open("UB.json") as f:
# ...     ub_db = json.load(f)
# >>>
# >>> cfg = PlotConfig(display_unit=LengthUnit.MM, show_properties=True)
# >>> fig2 = plot_section_2d("UB", ub_db["533x210x82"], cfg)
# >>> fig2.savefig("ub_2d.png", dpi=200, bbox_inches="tight")
# >>>
# >>> fig3 = plot_section_3d("UB", ub_db["533x210x82"], length=6000, config=cfg)
# >>> fig3.savefig("ub_3d.png", dpi=200, bbox_inches="tight")

# Coordinate convention
# ---------------------
# Cross-section axes follow the standard structural convention:

#     y  ↑            (Y-Y = major axis, vertical in plot)
#        │
#        └──→  z      (Z-Z = minor axis, horizontal in plot)

# Polygon arrays are (N, 2): column 0 → z, column 1 → y.

# For 3-D plots the beam longitudinal axis maps to matplotlib's Z-axis;
# the section y-z occupy matplotlib's Y-X axes respectively.

# Supported section types (geometry builders)
# -------------------------------------------
#     UB, UC, UBP    — doubly-symmetric I-sections
#     L_EQUAL_B2B    — back-to-back equal angles

# New types can be registered at runtime via :func:`register_geometry_builder`.

# Roadmap / TODOs
# ---------------
# - Geometry builders: L_EQUAL, L_UNEQUAL, L_UNEQUAL_B2B, PFC, HFCHS, HFSHS, HFRHS
# - Stress-distribution overlay (future)
# - Plotly/interactive backend (future)
# """

# from __future__ import annotations

# from dataclasses import dataclass
# from enum import Enum
# from typing import Any, Callable, Optional

# import matplotlib.pyplot as plt
# import numpy as np
# from matplotlib.figure import Figure
# from matplotlib.patches import Polygon as MplPolygon
# from mpl_toolkits.mplot3d import Axes3D          # noqa: F401  — registers 3-D projection
# from mpl_toolkits.mplot3d.art3d import Poly3DCollection

# __all__ = [
#     "LengthUnit",
#     "PlotConfig",
#     "DEFAULT_CONFIG",
#     "get_graphing_output_dir",
#     "get_geometry",
#     "register_geometry_builder",
#     "plot_section_2d",
#     "plot_section_3d",
# ]


# # ─────────────────────────────────────────────────────────────────────────────
# # 1.  Unit handling
# # ─────────────────────────────────────────────────────────────────────────────

# class LengthUnit(Enum):
#     """Linear unit identifiers for section dimension data."""
#     MM = "mm"
#     CM = "cm"
#     M  = "m"
#     # TODO: add imperial units (in, ft) 


# _TO_MM: dict[LengthUnit, float] = {
#     LengthUnit.MM: 1.0,
#     LengthUnit.CM: 10.0,
#     LengthUnit.M:  1_000.0,
# }


# def _cvt(value: float, from_unit: LengthUnit, to_unit: LengthUnit) -> float:
#     """Convert a scalar length value between units."""
#     return value * _TO_MM[from_unit] / _TO_MM[to_unit]


# def _cvt_arr(arr: np.ndarray, from_unit: LengthUnit, to_unit: LengthUnit) -> np.ndarray:
#     """Convert a NumPy array of length values between units (returns new array)."""
#     return arr * (_TO_MM[from_unit] / _TO_MM[to_unit])


# # ─────────────────────────────────────────────────────────────────────────────
# # 2.  Plot configuration
# # ─────────────────────────────────────────────────────────────────────────────

# @dataclass
# class PlotConfig:
#     """Centralised settings for all section plots.

#     Parameters
#     ----------
#     input_unit
#         Unit of the incoming section data values.
#         Default: ``LengthUnit.MM`` (UK Blue Book JSON stores dimensions in mm).
#     display_unit
#         Unit used on axis labels and dimension callouts.
#     figure_size_2d
#         (width, height) in inches for 2-D section plots.
#     figure_size_3d
#         (width, height) in inches for 3-D member renders.
#     dpi
#         Figure resolution (dots per inch).
#     section_color
#         Face fill colour of the steel cross-section.
#     section_edge_color
#         Outline / border colour.
#     section_alpha
#         Fill opacity (0–1).
#     hatch
#         Matplotlib hatch pattern string applied to the fill.
#         ``""`` = solid fill;  ``"///"`` = diagonal hatching.
#     cap_color
#         Colour of the 3-D end-cap faces.
#     cap_alpha
#         Opacity of the 3-D end-cap faces (0–1).
#     axis_color
#         Colour of the centroidal Y-Y / Z-Z axis lines.
#     dim_color
#         Colour of dimension callout lines and text.
#     centroid_color
#         Colour of the centroid cross-hair marker.
#     show_axes
#         Draw centroidal axis lines.
#     show_centroid
#         Draw a cross marker at the centroid (origin).
#     show_dimensions
#         Draw dimension callout arrows.
#     show_properties
#         Show a compact section property table in the figure corner.
#     show_stress_overlay
#         Reserved switch for future stress distribution overlays.
#     stress_cmap
#         Colormap name reserved for future stress distribution overlays.
#     stress_alpha
#         Overlay opacity reserved for future stress distribution overlays.
#     stress_label
#         Legend/annotation label reserved for stress overlays.
#     true_scale_3d
#         If ``True`` the 3-D render uses true proportions (cross-section may
#         become tiny relative to a long member).  If ``False`` (default) the
#         member length is normalised to ``5 × max(section dimension)`` so the
#         cross-section profile remains clearly visible; the actual length is
#         still shown in the title.
#     """
#     input_unit: LengthUnit        = LengthUnit.MM
#     display_unit: LengthUnit      = LengthUnit.MM
#     figure_size_2d: tuple         = (8, 8)
#     figure_size_3d: tuple         = (11, 7)
#     dpi: int                      = 150

#     # Section appearance
#     section_color: str            = "#3A6EA5"    # steel blue
#     section_edge_color: str       = "#1C3D5C"    # dark navy
#     section_alpha: float          = 0.80
#     hatch: str                    = ""           # "" = solid fill

#     # 3-D end-cap appearance
#     cap_color: str                = "#264E7A"
#     cap_alpha: float              = 0.92

#     # Annotation colours
#     axis_color: str               = "#C0392B"    # structural-red
#     dim_color: str                = "#4A4A4A"    # charcoal
#     centroid_color: str           = "#E74C3C"    # bright red

#     # Feature toggles
#     show_axes: bool               = True
#     show_centroid: bool           = True
#     show_dimensions: bool         = True
#     show_properties: bool         = True

#     # Future stress overlay controls (not yet rendered)
#     show_stress_overlay: bool     = False
#     stress_cmap: str              = "coolwarm"
#     stress_alpha: float           = 0.60
#     stress_label: str             = "sigma"

#     # 3-D display
#     true_scale_3d: bool           = False


# #: Module-level default configuration instance.
# DEFAULT_CONFIG: PlotConfig = PlotConfig()


# def get_graphing_output_dir() -> "pathlib.Path":
#     """Return/create a neat output folder for graphing demos and exports."""
#     import pathlib

#     out = pathlib.Path(__file__).parent / "outputs" / "graphing"
#     out.mkdir(parents=True, exist_ok=True)
#     return out


# # ─────────────────────────────────────────────────────────────────────────────
# # 3.  Geometry builders
# # ─────────────────────────────────────────────────────────────────────────────
# # Convention
# # ----------
# # Each builder receives the **raw** section data dict (values in input_unit)
# # and returns a **list of closed (N, 2) float64 polygon arrays**, also in
# # input_unit, **centred so the section centroid is at the origin (0, 0)**.
# #
# # Column layout: col 0 → z (horizontal), col 1 → y (vertical).
# # Winding direction: clockwise (matplotlib Polygon accepts either).

# GeometryBuilderFn = Callable[[dict[str, Any]], list[np.ndarray]]


# def _arc_points(
#     cx: float,
#     cy: float,
#     r: float,
#     start_deg: float,
#     end_deg: float,
#     n: int,
# ) -> list[tuple[float, float]]:
#     """Return arc points including endpoints from start->end angle (degrees)."""
#     if n < 2:
#         n = 2
#     th = np.linspace(np.deg2rad(start_deg), np.deg2rad(end_deg), n)
#     return [(cx + r * float(np.cos(t)), cy + r * float(np.sin(t))) for t in th]


# def _build_ub_geometry(data: dict[str, Any]) -> list[np.ndarray]:
#     """Doubly-symmetric I-section (UB / UC / UBP) as a single closed polygon.

#     If ``r`` (root radius) is present in the data and positive, the flange-web
#     re-entrant corners are rounded using circular fillets. Otherwise sharp
#     corners are used. The centroid of a doubly-symmetric I-section lies at
#     mid-height and mid-width → (0, 0).
#     """
#     h  = float(data["h"])    # total depth
#     b  = float(data["b"])    # flange width
#     tw = float(data["tw"])   # web thickness
#     tf = float(data["tf"])   # flange thickness

#     bh = b  / 2              # half flange width
#     wh = tw / 2              # half web thickness
#     yt =  h / 2              # extreme top fibre
#     yb = -h / 2              # extreme bottom fibre
#     yi =  h / 2 - tf         # inner face of top flange
#     yo = -h / 2 + tf         # inner face of bottom flange

#     r_raw = float(data.get("r", 0.0) or 0.0)
#     r_lim = max(0.0, min((b - tw) / 2.0, (h - 2.0 * tf) / 2.0))
#     r = min(r_raw, r_lim)

#     if r <= 0.0:
#         # Outline traversed clockwise starting at bottom-left.
#         pts = np.array([
#             (-bh,  yb),   # 0  bottom-left of bottom flange
#             ( bh,  yb),   # 1  bottom-right
#             ( bh,  yo),   # 2  inner-right of bottom flange
#             ( wh,  yo),   # 3  web bottom-right
#             ( wh,  yi),   # 4  web top-right
#             ( bh,  yi),   # 5  inner-right of top flange
#             ( bh,  yt),   # 6  top-right
#             (-bh,  yt),   # 7  top-left
#             (-bh,  yi),   # 8  inner-left of top flange
#             (-wh,  yi),   # 9  web top-left
#             (-wh,  yo),   # 10 web bottom-left
#             (-bh,  yo),   # 11 inner-left of bottom flange
#             (-bh,  yb),   # 12 close
#         ], dtype=float)
#         return [pts]

#     # Slightly adaptive sampling gives smoother fillets in interactive plots.
#     n_arc = max(9, min(31, int(10 + 0.8 * r)))
#     br = _arc_points(wh + r, yo + r, r, -90.0, -180.0, n_arc)
#     tr = _arc_points(wh + r, yi - r, r, 180.0, 90.0, n_arc)
#     tl = _arc_points(-wh - r, yi - r, r, 90.0, 0.0, n_arc)
#     bl = _arc_points(-wh - r, yo + r, r, 0.0, -90.0, n_arc)

#     coords: list[tuple[float, float]] = [
#         (-bh, yb),
#         (bh, yb),
#         (bh, yo),
#         (wh + r, yo),
#     ]
#     coords.extend(br[1:])
#     coords.append((wh, yi - r))
#     coords.extend(tr[1:])
#     coords.append((bh, yi))
#     coords.append((bh, yt))
#     coords.append((-bh, yt))
#     coords.append((-bh, yi))
#     coords.append((-wh - r, yi))
#     coords.extend(tl[1:])
#     coords.append((-wh, yo + r))
#     coords.extend(bl[1:])
#     coords.append((-bh, yo))
#     coords.append((-bh, yb))

#     pts = np.array(coords, dtype=float)
#     return [pts]


# def _build_l_equal_b2b_geometry(data: dict[str, Any]) -> list[np.ndarray]:
#     """Back-to-back equal angle pair — two mirrored L-polygons.

#     The backs of the two angles are coincident at z = 0.
#     The section centroid is placed at (0, 0):
#       z = 0  by double symmetry;
#       y = 0  because the y-origin is offset by n_y from the bottom of each leg.
#     """
#     leg = float(data["hxh"].split("x")[0])   # leg length (both legs equal)
#     t   = float(data["t"])                    # leg thickness
#     n_y = float(data["n_y"])                  # single-angle centroid from back

#     yo = -n_y   # bottom edge of horizontal leg in centroidal coordinates

#     # Right-hand angle: back at z = 0, legs extend toward +z and +y.
#     right = np.array([
#         ( 0,    yo),
#         (leg,   yo),
#         (leg,   yo + t),
#         (  t,   yo + t),
#         (  t,   yo + leg),
#         ( 0,    yo + leg),
#         ( 0,    yo),          # close
#     ], dtype=float)

#     # Left-hand angle: mirror the right angle in the z-axis (negate col 0).
#     left = right.copy()
#     left[:, 0] = -left[:, 0]

#     return [right, left]


# # ── Public geometry registry ──────────────────────────────────────────────────

# _GEOMETRY_BUILDERS: dict[str, GeometryBuilderFn] = {
#     "UB":          _build_ub_geometry,
#     "UC":          _build_ub_geometry,
#     "UBP":         _build_ub_geometry,
#     "L_EQUAL_B2B": _build_l_equal_b2b_geometry,
#     # TODO: L_EQUAL, L_UNEQUAL, L_UNEQUAL_B2B, PFC, HFCHS, HFSHS, HFRHS, …
# }


# def register_geometry_builder(
#     section_type_key: str,
#     builder: GeometryBuilderFn,
# ) -> None:
#     """Register (or replace) a geometry builder for *section_type_key*.

#     Parameters
#     ----------
#     section_type_key
#         String matching the ``SectionType`` enum ``.value``, e.g. ``"PFC"``.
#     builder
#         Callable ``(data: dict) -> list[np.ndarray]`` that follows the module
#         convention: centroid at (0, 0), values in input unit, col 0 = z, col 1 = y.

#     Example
#     -------
#     >>> from graphing import register_geometry_builder
#     >>> def my_pfc(data):
#     ...     # build and return polygon list ...
#     ...     return [pts]
#     >>> register_geometry_builder("PFC", my_pfc)
#     """
#     _GEOMETRY_BUILDERS[section_type_key] = builder


# def get_geometry(
#     section_type: "str | SectionType",
#     section_data: dict[str, Any],
# ) -> list[np.ndarray]:
#     """Return closed polygon arrays for *section_type*, centred at (0, 0).

#     Parameters
#     ----------
#     section_type
#         A ``SectionType`` enum value **or** its string ``.value`` (e.g. ``"UB"``).
#     section_data
#         Raw property dict as loaded from the JSON database for a single section.

#     Returns
#     -------
#     list of ``(N, 2)`` float64 arrays in the *input* unit.
#     """
#     key = section_type.value if hasattr(section_type, "value") else str(section_type)
#     builder = _GEOMETRY_BUILDERS.get(key)
#     if builder is None:
#         raise NotImplementedError(
#             f"No geometry builder registered for section type '{key}'.\n"
#             f"Available: {sorted(_GEOMETRY_BUILDERS)}.\n"
#             f"Add one with graphing.register_geometry_builder()."
#         )
#     return builder(section_data)


# # ─────────────────────────────────────────────────────────────────────────────
# # 4.  Internal drawing helpers
# # ─────────────────────────────────────────────────────────────────────────────

# def _bbox(polygons: list[np.ndarray]) -> tuple[float, float, float, float]:
#     """Return (zmin, ymin, zmax, ymax) over all polygon arrays."""
#     pts = np.concatenate(polygons, axis=0)
#     return float(pts[:, 0].min()), float(pts[:, 1].min()), \
#            float(pts[:, 0].max()), float(pts[:, 1].max())


# def _draw_patches(ax: plt.Axes, polygons: list[np.ndarray], cfg: PlotConfig) -> None:
#     for poly in polygons:
#         patch = MplPolygon(
#             poly,
#             closed=True,
#             facecolor=cfg.section_color,
#             edgecolor=cfg.section_edge_color,
#             linewidth=1.5,
#             alpha=cfg.section_alpha,
#             hatch=cfg.hatch,
#             zorder=2,
#         )
#         ax.add_patch(patch)


# def _draw_centroidal_axes(
#     ax: plt.Axes,
#     zmin: float, zmax: float, ymin: float, ymax: float,
#     cfg: PlotConfig,
# ) -> None:
#     """Draw Y-Y (horizontal) and Z-Z (vertical) centroidal axis lines."""
#     pad_z = (zmax - zmin) * 0.28
#     pad_y = (ymax - ymin) * 0.28
#     dy = (ymax - ymin) * 0.06
#     dx = (zmax - zmin) * 0.03

#     ax.plot([zmin - pad_z, zmax + pad_z], [0, 0],
#             color=cfg.axis_color, lw=1.0, ls="--", zorder=1)
#     ax.text(zmax + pad_z * 0.40, -dy, "Y–Y",
#             ha="left", va="center", fontsize=8,
#             color=cfg.axis_color, fontweight="bold")

#     ax.plot([0, 0], [ymin - pad_y, ymax + pad_y],
#             color=cfg.axis_color, lw=1.0, ls="--", zorder=1)
#     ax.text(dx, ymax + pad_y * 0.62, "Z–Z",
#             ha="center", va="bottom", fontsize=8,
#             color=cfg.axis_color, fontweight="bold")


# # ── Dimension arrow primitives ─────────────────────────────────────────────

# def _dim_h(
#     ax: plt.Axes,
#     y_arrow: float, z0: float, z1: float,
#     z_label: float, y_label: float, va_label: str,
#     label: str, cfg: PlotConfig,
# ) -> None:
#     """Horizontal dimension arrow at height *y_arrow* with label at (z_label, y_label)."""
#     ak = dict(arrowstyle="<->", color=cfg.dim_color, lw=0.8, mutation_scale=8)
#     ax.annotate("", xy=(z1, y_arrow), xytext=(z0, y_arrow), arrowprops=ak)
#     ax.text(z_label, y_label, label,
#             ha="center", va=va_label, fontsize=7, color=cfg.dim_color)


# def _dim_v(
#     ax: plt.Axes,
#     z_arrow: float, y0: float, y1: float,
#     z_label: float, y_label: float, ha_label: str,
#     label: str, cfg: PlotConfig,
# ) -> None:
#     """Vertical dimension arrow at position *z_arrow* with label at (z_label, y_label)."""
#     ak = dict(arrowstyle="<->", color=cfg.dim_color, lw=0.8, mutation_scale=8)
#     ax.annotate("", xy=(z_arrow, y1), xytext=(z_arrow, y0), arrowprops=ak)
#     ax.text(z_label, y_label, label,
#             ha=ha_label, va="center", fontsize=7, color=cfg.dim_color)


# def _extension_lines_h(
#     ax: plt.Axes, z_section: float, z_arrow: float, y: float, cfg: PlotConfig
# ) -> None:
#     """Dashed horizontal leader line from section edge to a vertical arrow."""
#     ax.plot([z_section, z_arrow], [y, y],
#             color=cfg.dim_color, lw=0.5, ls=":", zorder=1)


# # ── Section-specific dimension drawers ────────────────────────────────────────

# def _dims_ub(
#     ax: plt.Axes,
#     data: dict[str, Any],
#     polys_d: list[np.ndarray],
#     cfg: PlotConfig,
# ) -> None:
#     """Dimension callouts for I-sections (all coords already in display_unit)."""
#     def c(v: Any) -> float:
#         return _cvt(float(v), cfg.input_unit, cfg.display_unit)

#     h_d  = c(data["h"])
#     b_d  = c(data["b"])
#     tw_d = c(data["tw"])
#     tf_d = c(data["tf"])
#     u    = cfg.display_unit.value

#     zmin, ymin, zmax, ymax = _bbox(polys_d)
#     gz = (zmax - zmin) * 0.07    # horizontal gap unit
#     gy = (ymax - ymin) * 0.07    # vertical gap unit

#     # b  — flange width, above section
#     _dim_h(ax,
#            y_arrow=ymax + 1.4 * gy,
#            z0=-b_d / 2, z1=b_d / 2,
#            z_label=0.0, y_label=ymax + 1.4 * gy + 0.35 * gy, va_label="bottom",
#            label=f"b = {b_d:.1f} {u}", cfg=cfg)

#     # h  — total depth, to the right
#     _dim_v(ax,
#            z_arrow=zmax + 1.5 * gz,
#            y0=-h_d / 2, y1=h_d / 2,
#            z_label=zmax + 1.5 * gz + 0.35 * gz, y_label=0.0, ha_label="left",
#            label=f"h = {h_d:.1f} {u}", cfg=cfg)

#     # tw — web thickness, below section
#     _dim_h(ax,
#            y_arrow=ymin - 1.4 * gy,
#            z0=-tw_d / 2, z1=tw_d / 2,
#            z_label=0.0, y_label=ymin - 1.4 * gy - 0.35 * gy, va_label="top",
#            label=f"tw = {tw_d:.1f} {u}", cfg=cfg)

#     # tf — top flange thickness, further right with extension leaders
#     z_tf_arrow = zmax + 4.2 * gz
#     _dim_v(ax,
#            z_arrow=z_tf_arrow,
#            y0=h_d / 2 - tf_d, y1=h_d / 2,
#            z_label=z_tf_arrow + 0.35 * gz, y_label=h_d / 2 - tf_d / 2, ha_label="left",
#            label=f"tf = {tf_d:.1f} {u}", cfg=cfg)
#     _extension_lines_h(ax, zmax, z_tf_arrow, h_d / 2, cfg)
#     _extension_lines_h(ax, zmax, z_tf_arrow, h_d / 2 - tf_d, cfg)


# def _dims_l_equal_b2b(
#     ax: plt.Axes,
#     data: dict[str, Any],
#     polys_d: list[np.ndarray],
#     cfg: PlotConfig,
# ) -> None:
#     """Dimension callouts for back-to-back equal angles."""
#     def c(v: Any) -> float:
#         return _cvt(float(v), cfg.input_unit, cfg.display_unit)

#     leg_d = c(data["hxh"].split("x")[0])
#     t_d   = c(data["t"])
#     n_y_d = c(data["n_y"])
#     u     = cfg.display_unit.value

#     zmin, ymin, zmax, ymax = _bbox(polys_d)
#     gz = (zmax - zmin) * 0.07
#     gy = (ymax - ymin) * 0.07

#     yo = -n_y_d   # bottom edge (centroidal coords)

#     # Total width (2 × leg), below section
#     _dim_h(ax,
#            y_arrow=ymin - 1.4 * gy,
#            z0=-leg_d, z1=leg_d,
#            z_label=0.0, y_label=ymin - 1.4 * gy - 0.35 * gy, va_label="top",
#            label=f"2h = {2*leg_d:.1f} {u}", cfg=cfg)

#     # Leg length (vertical), to the right
#     _dim_v(ax,
#            z_arrow=zmax + 1.5 * gz,
#            y0=yo, y1=yo + leg_d,
#            z_label=zmax + 1.5 * gz + 0.35 * gz, y_label=yo + leg_d / 2, ha_label="left",
#            label=f"h = {leg_d:.1f} {u}", cfg=cfg)

#     # Leg thickness, further right with extension leaders
#     z_t_arrow = zmax + 4.2 * gz
#     _dim_v(ax,
#            z_arrow=z_t_arrow,
#            y0=yo, y1=yo + t_d,
#            z_label=z_t_arrow + 0.35 * gz, y_label=yo + t_d / 2, ha_label="left",
#            label=f"t = {t_d:.1f} {u}", cfg=cfg)
#     _extension_lines_h(ax, zmax, z_t_arrow, yo, cfg)
#     _extension_lines_h(ax, zmax, z_t_arrow, yo + t_d, cfg)


# _DIM_DRAWERS: dict[str, Callable] = {
#     "UB":          _dims_ub,
#     "UC":          _dims_ub,
#     "UBP":         _dims_ub,
#     "L_EQUAL_B2B": _dims_l_equal_b2b,
# }


# # ── Properties table ──────────────────────────────────────────────────────────

# def _draw_props_table(
#     ax: plt.Axes,
#     key: str,
#     data: dict[str, Any],
#     cfg: PlotConfig,
# ) -> None:
#     """Render a compact monospaced properties table in the bottom-left corner.

#     Property values are shown in the units used by the database
#     (Blue Book: A in cm², I in cm⁴, W in cm³).
#     """
#     rows: list[tuple[str, str]] = [
#         ("Designation", str(data.get("designation", "—"))),
#     ]

#     def _f(k: str, fmt: str = ",.0f") -> str:
#         v = data.get(k)
#         return format(v, fmt) if v is not None else "—"

#     if key in ("UB", "UC", "UBP"):
#         rows += [
#             ("mass [kg/m]",   _f("mass_per_metre", ".1f")),
#             ("A  [cm²]",      _f("A")),
#             ("Iyy  [cm⁴]",   _f("I_yy")),
#             ("Izz  [cm⁴]",   _f("I_zz")),
#             ("Wpl,yy [cm³]", _f("W_pl_yy")),
#             ("It  [cm⁴]",    _f("I_t")),
#         ]
#     elif key == "L_EQUAL_B2B":
#         rows += [
#             ("mass [kg/m]",    _f("total_mass_per_metre", ".1f")),
#             ("A  [cm²]",       _f("total_area", ".1f")),
#             ("Iyy  [cm⁴]",    _f("I_yy", ".1f")),
#             ("Wel,yy [cm³]",  _f("W_el_yy", ".1f")),
#         ]

#     text = "\n".join(f"{k:<17} {v}" for k, v in rows)
#     ax.text(
#         0.02, 0.02, text,
#         transform=ax.transAxes,
#         fontsize=7,
#         va="bottom",
#         fontfamily="monospace",
#         bbox=dict(boxstyle="round,pad=0.45", fc="white", ec="#BBBBBB", alpha=0.90),
#         zorder=5,
#     )


# # ─────────────────────────────────────────────────────────────────────────────
# # 5.  3-D extrusion helper
# # ─────────────────────────────────────────────────────────────────────────────

# def _extrude_faces(
#     poly2d: np.ndarray,
#     length: float,
# ) -> tuple[list, list, list]:
#     """Convert a closed 2-D polygon into Poly3DCollection face lists.

#     The polygon lies in the XY-plane (col 0 → X, col 1 → Y).
#     Extrusion runs along the Z-axis from Z = 0 to Z = *length*.

#     Returns
#     -------
#     near_cap : list  — single face list for the near end-cap (Z = 0)
#     far_cap  : list  — single face list for the far  end-cap (Z = length)
#     sides    : list  — face lists for all side panels
#     """
#     n    = len(poly2d) - 1     # unique vertices (polygon closed: last == first)
#     z0   = [(poly2d[i, 0], poly2d[i, 1], 0.0)    for i in range(n)]
#     zL   = [(poly2d[i, 0], poly2d[i, 1], length)  for i in range(n)]

#     sides = [
#         [z0[i], z0[(i + 1) % n], zL[(i + 1) % n], zL[i]]
#         for i in range(n)
#     ]
#     return z0, zL, sides


# # ─────────────────────────────────────────────────────────────────────────────
# # 6.  Public API
# # ─────────────────────────────────────────────────────────────────────────────

# def plot_section_2d(
#     section_type: "str | SectionType",
#     section_data: dict[str, Any],
#     config: Optional[PlotConfig] = None,
#     ax: Optional[plt.Axes] = None,
# ) -> Figure:
#     """Plot a 2-D cross-section to scale.

#     Parameters
#     ----------
#     section_type
#         Section type identifier — string (e.g. ``"UB"``) or ``SectionType`` enum.
#     section_data
#         Raw property dict for a single section (e.g. ``ub_db["533x210x82"]``).
#     config
#         :class:`PlotConfig` instance.  Defaults to :data:`DEFAULT_CONFIG`.
#     ax
#         Optional existing ``Axes`` to draw into.  If ``None`` a new figure is
#         created and returned.

#     Returns
#     -------
#     ``matplotlib.figure.Figure``

#     Features rendered
#     -----------------
#     - Section outline filled to scale
#     - Centroidal Y-Y and Z-Z axis lines  (toggleable)
#     - Centroid cross-hair marker          (toggleable)
#     - Key dimension callout arrows        (toggleable)
#     - Section property table             (toggleable)
#     """
#     cfg = config or DEFAULT_CONFIG
#     key = section_type.value if hasattr(section_type, "value") else str(section_type)

#     # Build polygons in display_unit, centred at (0, 0)
#     polys = [
#         _cvt_arr(p, cfg.input_unit, cfg.display_unit)
#         for p in get_geometry(key, section_data)
#     ]

#     if ax is None:
#         fig, ax = plt.subplots(figsize=cfg.figure_size_2d, dpi=cfg.dpi)
#     else:
#         fig = ax.get_figure()

#     # ── Section fill ─────────────────────────────────────────────────────────
#     _draw_patches(ax, polys, cfg)

#     zmin, ymin, zmax, ymax = _bbox(polys)
#     width   = zmax - zmin
#     height  = ymax - ymin

#     # ── Annotations ──────────────────────────────────────────────────────────
#     if cfg.show_axes:
#         _draw_centroidal_axes(ax, zmin, zmax, ymin, ymax, cfg)

#     if cfg.show_centroid:
#         ax.plot(0, 0, "+", color=cfg.centroid_color, ms=14, mew=2.0, zorder=4,
#                 label="Centroid")

#     if cfg.show_dimensions:
#         dim_fn = _DIM_DRAWERS.get(key)
#         if dim_fn is not None:
#             dim_fn(ax, section_data, polys, cfg)

#     if cfg.show_properties:
#         _draw_props_table(ax, key, section_data, cfg)

#     # ── Axes formatting ───────────────────────────────────────────────────────
#     pad_z = width  * 0.50
#     pad_y = height * 0.50
#     ax.set_aspect("equal")
#     ax.set_xlim(zmin - pad_z, zmax + pad_z)
#     ax.set_ylim(ymin - pad_y, ymax + pad_y)

#     u = cfg.display_unit.value
#     ax.set_xlabel(f"z  [{u}]", fontsize=9)
#     ax.set_ylabel(f"y  [{u}]", fontsize=9)
#     ax.set_title(
#         f"{key}  ·  {section_data.get('designation', '')}",
#         fontsize=11, fontweight="bold", pad=10,
#     )
#     ax.tick_params(labelsize=8)
#     ax.grid(True, ls=":", lw=0.4, alpha=0.5)
#     ax.set_axisbelow(True)
#     fig.tight_layout()
#     return fig


# def plot_section_3d(
#     section_type: "str | SectionType",
#     section_data: dict[str, Any],
#     length: float,
#     config: Optional[PlotConfig] = None,
#     elev: float = 22.0,
#     azim: float = -52.0,
# ) -> Figure:
#     """Render a 3-D member by extruding the cross-section along the beam axis.

#     Parameters
#     ----------
#     section_type
#         Section type identifier — string or ``SectionType`` enum.
#     section_data
#         Raw property dict for a single section.
#     length
#         Member length **in** ``config.input_unit`` (same unit as the database).
#     config
#         :class:`PlotConfig` instance.  Defaults to :data:`DEFAULT_CONFIG`.
#     elev
#         View elevation angle in degrees.
#     azim
#         View azimuth angle in degrees.

#     Returns
#     -------
#     ``matplotlib.figure.Figure``

#     Notes
#     -----
#     The cross-section is in the matplotlib X-Y plane; the beam axis runs along
#     matplotlib Z.  When ``config.true_scale_3d`` is ``False`` the displayed
#     length is normalised to ``5 × max(section dimension)`` so the profile
#     remains visible at a glance; the actual length is shown in the title.
#     """
#     cfg    = config or DEFAULT_CONFIG
#     key    = section_type.value if hasattr(section_type, "value") else str(section_type)

#     polys  = [
#         _cvt_arr(p, cfg.input_unit, cfg.display_unit)
#         for p in get_geometry(key, section_data)
#     ]
#     length_d = _cvt(length, cfg.input_unit, cfg.display_unit)

#     zmin, ymin, zmax, ymax = _bbox(polys)
#     max_dim = max(zmax - zmin, ymax - ymin)

#     if cfg.true_scale_3d:
#         display_len = length_d
#         len_note    = f"{length_d:.2f} {cfg.display_unit.value}"
#     else:
#         display_len = max_dim * 5.0
#         len_note    = f"{length_d:.2f} {cfg.display_unit.value}  (section scaled for clarity)"

#     fig = plt.figure(figsize=cfg.figure_size_3d, dpi=cfg.dpi)
#     ax  = fig.add_subplot(111, projection="3d")

#     for poly in polys:
#         near, far, sides = _extrude_faces(poly, display_len)

#         # Side walls
#         ax.add_collection3d(Poly3DCollection(
#             sides,
#             facecolor=cfg.section_color,
#             edgecolor=cfg.section_edge_color,
#             alpha=cfg.section_alpha,
#             linewidth=0.4,
#         ))
#         # End caps
#         for cap in (near, far):
#             ax.add_collection3d(Poly3DCollection(
#                 [cap],
#                 facecolor=cfg.cap_color,
#                 edgecolor=cfg.section_edge_color,
#                 alpha=cfg.cap_alpha,
#                 linewidth=0.8,
#             ))

#     # ── Axis bounds (with padding to avoid clipped/too-close startup view) ──
#     x_span = max(zmax - zmin, 1e-9)
#     y_span = max(ymax - ymin, 1e-9)
#     z_span = max(display_len, 1e-9)
#     pad_xy = max(0.10 * max(x_span, y_span), 1e-6)
#     pad_z0 = 0.04 * z_span
#     pad_z1 = 0.06 * z_span

#     ax.set_xlim(zmin - pad_xy, zmax + pad_xy)
#     ax.set_ylim(ymin - pad_xy, ymax + pad_xy)
#     ax.set_zlim(-pad_z0, display_len + pad_z1)

#     # Equal-box aspect ratio so the cross-section isn't distorted.
#     try:
#         ax.set_box_aspect([x_span, y_span, z_span])
#     except AttributeError:
#         pass   # set_box_aspect available from matplotlib 3.3

#     try:
#         ax.set_proj_type("persp", focal_length=0.9)
#     except TypeError:
#         pass

#     u = cfg.display_unit.value
#     ax.set_xlabel(f"z  [{u}]", fontsize=8, labelpad=6)
#     ax.set_ylabel(f"y  [{u}]", fontsize=8, labelpad=6)
#     ax.set_zlabel(f"Member axis  [{u}]", fontsize=8, labelpad=10)
#     ax.set_title(
#         f"{key}  ·  {section_data.get('designation', '')}   L = {len_note}",
#         fontsize=10, fontweight="bold", pad=12,
#     )
#     ax.view_init(elev=elev, azim=azim)
#     ax.tick_params(labelsize=7)
#     fig.tight_layout()
#     return fig


# # ─────────────────────────────────────────────────────────────────────────────
# # 7.  Quick demo  (python graphing.py)
# # ─────────────────────────────────────────────────────────────────────────────

# if __name__ == "__main__":
#     import json
#     import pathlib
#     import sys

#     from steelsnakes.base.graphing_plotly import LengthUnit as PlotlyLengthUnit
#     from steelsnakes.base.graphing_plotly import PlotlyConfig, plot_section_3d_plotly

#     def _load(path: str) -> dict:
#         with open(path) as fh:
#             return json.load(fh)

#     # Single reference section: 2-D with matplotlib + 3-D with plotly
#     ub_path = pathlib.Path(__file__).parent.parent / "UK" / "data" / "UB.json"
#     if not ub_path.exists():
#         print("[warn] UB.json not found — skipping graphing demo", file=sys.stderr)
#         raise SystemExit(0)

#     ub_db = _load(str(ub_path))
#     ub_key = "533x210x82"
#     ub_data = ub_db.get(ub_key)
#     if not ub_data:
#         print(f"[warn] '{ub_key}' not found in UB.json", file=sys.stderr)
#         raise SystemExit(0)

#     out_dir = get_graphing_output_dir()

#     cfg_2d = PlotConfig(
#         display_unit=LengthUnit.MM,
#         figure_size_2d=(9, 9),
#         dpi=220,
#         show_dimensions=True,
#         show_properties=True,
#         show_stress_overlay=False,
#     )
#     fig2 = plot_section_2d("UB", ub_data, cfg_2d)
#     out_2d = out_dir / "UB_2D_matplotlib.png"
#     fig2.savefig(out_2d, dpi=220, bbox_inches="tight")
#     print(f"Saved {out_2d}")

#     cfg_3d = PlotlyConfig(display_unit=PlotlyLengthUnit.MM)
#     fig3 = plot_section_3d_plotly("UB", ub_data, length=6000, config=cfg_3d)
#     out_3d = out_dir / "UB_3D_plotly.html"
#     fig3.write_html(
#         str(out_3d),
#         include_plotlyjs="cdn",
#         config={"responsive": True, "scrollZoom": True},
#     )
#     print(f"Saved {out_3d}")
