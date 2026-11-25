"""Adaptive visual profiles for general-purpose scientific figures.

The fixed XPS contract remains available in :mod:`base_style_contract`.  This
module is deliberately separate: general statistical/scientific charts need a
page that responds to label length, series count and data density instead of a
single physical size inherited from one teaching task.
"""

from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, replace
from typing import Any

from .circular_network_layout import NETWORK_NODE_GROUP_COLORS
from .palette_catalog import list_palettes

PALETTES: dict[str, tuple[str, ...]] = {
    # Independent comparisons: neutral baseline, restrained teal, coral signal.
    # All eight remain visible on white; composition ramps stay separate.
    "publication_comparison": (
        "#59666F", "#247B8B", "#C66454", "#7E669C",
        "#A58C4B", "#61937D", "#487CB0", "#B6688D",
    ),
    # A neutral comparator and restrained signal accents stay visible on white.
    "publication_signal": (
        "#59666F", "#247B8B", "#C66454", "#7E669C",
        "#A58C4B", "#61937D", "#487CB0", "#B6688D",
    ),
    # Verified direct ``set -c`` colors for 1–6 editable 3D trajectories.
    "trajectory3d_family": (
        "#17304C",
        "#1F6F78",
        "#D5A44C",
        "#9B5C76",
        "#557A46",
        "#76548D",
    ),
    # Related method families: cool baselines, restrained rose hero variants.
    "comparison_family": (
        "#484878",
        "#7884B4",
        "#B4C0E4",
        "#E4E4F0",
        "#E4CCD8",
        "#F0C0CC",
    ),
    # Same-hue sequences for ablation and long-label horizontal bars.
    "ablation_blue": (
        "#234F7D",
        "#4777A5",
        "#7099BF",
        "#9AB9D2",
        "#C7D9E8",
        "#E1EBF3",
    ),
    # Signed effects: cool negative values, warm positive values, with a
    # neutral centre.  Row-level assignment is magnitude aware in the
    # categorical renderer; this palette is never used as a rainbow ramp.
    "diverging_effect": (
        "#3F67A8",
        "#86A5D2",
        "#D9E0E8",
        "#E9C2BE",
        "#C6534E",
    ),
    "stacked_blue": (
        "#DCE8F2",
        "#BCD2E5",
        "#91B6D4",
        "#6395BE",
        "#3B74A5",
        "#214F7D",
    ),
    "composition_teal": (
        "#DCEFED",
        "#B8DDD8",
        "#8FC8C1",
        "#61AFA6",
        "#3B9188",
        "#236F69",
    ),
    # Single-family lilac sequence for normalized compositions.  It preserves
    # ordering without turning one composition into a rainbow.
    "composition_lilac": (
        "#ECEBF5",
        "#D2D0E8",
        "#B4B0D8",
        "#928BC2",
        "#6E65A8",
        "#494277",
    ),
    "trend_family": (
        "#245B9A",
        "#76A0CC",
        "#D98782",
        "#E7B7B3",
        "#3C9D94",
        "#8CCDC5",
    ),
    "flow_family": (
        "#355F8A",
        "#5E8FB7",
        "#89B7C9",
        "#7DBFB5",
        "#A89BCD",
        "#D2A3AE",
        "#D6B66F",
    ),
    # Soft categorical node fills for circular directed networks.  Edge signs
    # retain their own semantic teal/coral/neutral colours in the renderer.
    "network_nodes": NETWORK_NODE_GROUP_COLORS,
    "distribution_family": (
        "#285D7A",
        "#4F829B",
        "#79A8B9",
        "#A7CDD3",
        "#D5E8E7",
        "#8A719B",
    ),
    "evidence_family": (
        "#2C5F85",
        "#5D88A5",
        "#91B1C4",
        "#C5D9E2",
        "#8A6F9D",
        "#B39DBD",
    ),
    "medical_ai": (
        "#244A73",
        "#3F7197",
        "#67A0B3",
        "#9BC8C8",
        "#C8DEE0",
        "#B65C67",
    ),
    "paired_neutral": (
        "#385A73",
        "#4C6C84",
        "#607E94",
        "#7490A4",
        "#88A2B4",
        "#9CB4C4",
    ),
    "grouped_box_medical": (
        "#6C78D6",
        "#E3848A",
        "#5FA6A0",
        "#C59A62",
    ),
    "spectroscopy_jewel": (
        "#245B9A",
        "#B24B5A",
        "#1E7A67",
        "#6E5AA8",
        "#3E7C91",
        "#A06D3F",
    ),
    # Ordered condition ramp for PL/FTIR temperature or concentration series.
    # The sequence is intentionally continuous and supports up to ten curves
    # without cycling back to an unrelated colour.
    "spectroscopy_temperature": (
        "#155E75",
        "#1F7899",
        "#3A91B4",
        "#68A9C1",
        "#9ABFD0",
        "#C5C8DD",
        "#D8B4CF",
        "#D98FAE",
        "#CE6F87",
        "#B84D62",
    ),
    # Restrained material comparison colours for unrelated samples.  This is
    # distinct from an ordered temperature ramp and remains readable in print.
    "materials_comparison": (
        "#263746",
        "#3B6F8F",
        "#B85864",
        "#3E8878",
        "#7A6699",
        "#A77A43",
        "#6F8796",
        "#C28791",
    ),
    "thermal_analysis": (
        "#263746",
        "#3B6F8F",
        "#B85864",
        "#B9C7B2",
        "#D5A36A",
        "#5F8E84",
    ),
}

# User-selectable palettes are registered by stable ID.  Internal semantic
# palettes above remain available for signed effects, heatmaps, and other
# routes where colour meaning must not be replaced by a cosmetic override.
PALETTES.update({palette.palette_id: palette.colors for palette in list_palettes()})


@dataclass(frozen=True)
class AdaptiveOriginStyle:
    """Resolved physical/style contract carried by a frozen plot plan."""

    profile_name: str
    page_width_cm: float
    page_height_cm: float
    layer_left_percent: float
    layer_top_percent: float
    layer_width_percent: float
    layer_height_percent: float
    layer_fixed: int = 1
    layer_factor: float = 1.0
    font_family: str = "Arial"
    axis_title_size_pt: float = 20.0
    tick_label_size_pt: float = 17.0
    legend_size_pt: float = 17.0
    plot_line_width_pt: float = 2.6
    frame_line_width_pt: float = 1.8
    major_tick_length_pt: float = 5.5
    minor_tick_length_pt: float = 3.0
    x_major_step: float = 2.0
    x_minor_ticks_between_majors: int = 1
    x_title_upshift_page_percent: float = 1.5
    error_bar_width_pt: float = 1.8
    bar_border_width_pt: float = 1.4
    fill_transparency_percent: float = 12.0
    palette_name: str = "comparison_family"
    heatmap_palette: str = "Viridis.PAL"
    inset_axis_title_size_pt: float = 15.0
    inset_tick_label_size_pt: float = 13.0
    inset_frame_line_width_pt: float = 1.3
    personal_profile: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        if self.personal_profile is None:
            result.pop("personal_profile")
        return result


PERSONAL_BAR_STYLE_KEYS = frozenset({
    "bar_border", "bar_fill", "bar_fill_transparency_percent",
})
PERSONAL_BAR_TEMPLATES = frozenset({"bar", "horizontal_bar", "stacked_bar", "percent_stacked_bar"})
PERSONAL_AXIS_STYLE_KEYS = frozenset({
    "frame_line_width_pt", "major_tick_length_pt", "axis_color", "tick_direction",
    "numeric_minor_ticks", "tick_details", "axis_frame",
})
# Ordinary Cartesian plots share this axis contract. Specialized axes retain
# their own scientific layout (e.g. raster lanes, polar plots, heatmap cells).
PERSONAL_AXIS_TEMPLATES = PERSONAL_BAR_TEMPLATES | frozenset({
    "trend", "line_error", "scatter", "xrd", "xas", "pl", "ftir", "uv_vis", "dsc",
    "nmr", "cv", "lsv", "eis", "calibration_curve", "diagnostic_curve", "decision_curve",
    "paired_trajectory", "raw_summary", "violin", "raincloud", "histogram", "grouped_box", "bubble",
})
PERSONAL_STYLE_KEYS = frozenset({
    "page_width_cm", "page_height_cm", "font_family", "axis_title_size_pt",
    "tick_label_size_pt", "legend_size_pt", "annotation_size_pt", "bold", "png_dpi", "legend_position",
}) | PERSONAL_BAR_STYLE_KEYS | PERSONAL_AXIS_STYLE_KEYS


class PersonalProfileError(ValueError):
    code = "personal_profile_invalid"


def personal_profile_hash(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(
        dict(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def normalize_personal_profile(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate only explicit overrides; never fill unspecified template fields."""
    if not isinstance(payload, Mapping) or set(payload) != {"id", "overrides"}:
        raise PersonalProfileError("A personal profile requires id and overrides only.")
    identifier, raw = payload["id"], payload["overrides"]
    if not isinstance(identifier, str) or not identifier.strip() or len(identifier) > 120:
        raise PersonalProfileError("A personal profile needs a non-empty id.")
    if not isinstance(raw, Mapping) or set(raw) - PERSONAL_STYLE_KEYS:
        raise PersonalProfileError("The personal profile contains unsupported override fields.")
    overrides: dict[str, Any] = {}
    for key, value in raw.items():
        if key in {"axis_color", "tick_direction", "tick_details", "axis_frame"}:
            allowed = {"axis_color": ("#000000",), "tick_direction": ("out", "in"),
                       "tick_details": ("auto",), "axis_frame": ("four_sides",)}[key]
            if value not in allowed:
                raise PersonalProfileError(f"{key} must be one of {allowed}.")
            overrides[key] = value
        elif key in {"bar_border", "bar_fill"}:
            allowed = ("none", "template") if key == "bar_border" else ("two_color_center", "template")
            if value not in allowed:
                raise PersonalProfileError(f"{key} must be one of {allowed}.")
            overrides[key] = value
        elif key == "legend_position":
            if value not in ("inside", "template"):
                raise PersonalProfileError("legend_position must be inside or template.")
            overrides[key] = value
        elif key == "font_family":
            if not isinstance(value, str) or not value.strip() or any(c in value for c in '\r\n;()"'):
                raise PersonalProfileError("font_family must be a plain installed font name.")
            overrides[key] = value.strip()
        elif key == "bold":
            if not isinstance(value, bool):
                raise PersonalProfileError("bold must be a boolean.")
            overrides[key] = value
        else:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise PersonalProfileError(f"{key} must be a finite number.")
            limits = (0.1, 100) if key.startswith("page_") else (1, 144)
            if key == "bar_fill_transparency_percent":
                limits = (0, 100)
            if key in {"frame_line_width_pt", "major_tick_length_pt"}:
                limits = (0.1, 30)
            if key == "numeric_minor_ticks":
                limits = (0, 20)
                if int(value) != value:
                    raise PersonalProfileError("numeric_minor_ticks must be an integer.")
            if key == "png_dpi":
                limits = (72, 2400)
                if int(value) != value:
                    raise PersonalProfileError("png_dpi must be an integer.")
            if not limits[0] <= value <= limits[1]:
                raise PersonalProfileError(f"{key} must be between {limits[0]} and {limits[1]}.")
            overrides[key] = int(value) if key == "png_dpi" else float(value)
    return {"id": identifier.strip(), "overrides": dict(sorted(overrides.items()))}


def personal_style(style: AdaptiveOriginStyle, profile: Mapping[str, Any]) -> AdaptiveOriginStyle:
    """Apply native page dimensions and typography, retaining layer percentages."""
    canonical = normalize_personal_profile(profile)
    changes = {k: v for k, v in canonical["overrides"].items()
               if k not in {"bold", "annotation_size_pt", "png_dpi", "legend_position"}
               and k not in PERSONAL_BAR_STYLE_KEYS and k not in PERSONAL_AXIS_STYLE_KEYS}
    if personal_axes_supported(style):
        changes.update({k: canonical["overrides"][k] for k in ("frame_line_width_pt", "major_tick_length_pt")
                        if k in canonical["overrides"]})
    return replace(style, **changes, personal_profile=canonical)


def personal_axes_supported(style: AdaptiveOriginStyle) -> bool:
    name = getattr(style, "profile_name", "")
    return name.startswith("xps_") or any(name.startswith(f"adaptive-{t}-") for t in PERSONAL_AXIS_TEMPLATES)


def personal_axis_style(style: AdaptiveOriginStyle) -> dict[str, Any]:
    profile = getattr(style, "personal_profile", None)
    if not profile or not personal_axes_supported(style):
        return {}
    return {k: v for k, v in profile["overrides"].items() if k in PERSONAL_AXIS_STYLE_KEYS}


def personal_bar_style(style: AdaptiveOriginStyle) -> dict[str, Any]:
    """Read only the bar-specific overrides; callers are column renderers."""
    profile = style.personal_profile
    if not profile or not (PERSONAL_BAR_STYLE_KEYS & profile["overrides"].keys()):
        return {}
    if not any(
        style.profile_name.startswith(f"adaptive-{template}-") for template in PERSONAL_BAR_TEMPLATES
    ):
        return {}
    return {key: value for key, value in profile["overrides"].items()
            if key in PERSONAL_BAR_STYLE_KEYS and value != "template"}


def column_highlight_color(color: str) -> str:
    """Keep the template hue, mixing 70% white for the central highlight."""
    rgb = tuple(int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    return "#" + "".join(f"{round(channel + (255 - channel) * 0.70):02X}" for channel in rgb)


def apply_personal_profile(preparation: Any, profile: Mapping[str, Any]) -> tuple[Any, dict[str, Any]]:
    """Use the existing immutable preparation and digest replacement routes."""
    canonical = normalize_personal_profile(profile)
    before = preparation.plan_digest
    if hasattr(preparation, "visual_contract"):
        from .xps_workflow import replace_xps_visual_contract

        contract = preparation.visual_contract
        if canonical["overrides"].get("legend_position") == "inside":
            contract = replace(contract, legend_position="inside")
        updated = replace_xps_visual_contract(preparation, replace(
            contract, figure_style=personal_style(contract.figure_style, canonical),
        ))
    else:
        from .scientific_workflow import _legend_label_length, _scientific_plan_digest

        spec = preparation.plot_spec
        if spec.display_plan.figure_style is None:
            raise PersonalProfileError("The selected template has no existing style to customize.")
        base_style = spec.display_plan.figure_style
        if (canonical["overrides"].get("legend_position") == "inside"
                and base_style.profile_name.endswith("-external-legend")
                and spec.plot_kind in {"bar_error", "line", "stacked_line", "line_error",
                                       "scatter", "diagnostic_curve", "decision_curve"}):
            inside = resolve_adaptive_style(
                template_id=preparation.template_id, plot_kind=spec.plot_kind,
                row_count=preparation.row_count, series_count=len(spec.series),
                max_legend_label_length=_legend_label_length(spec.series),
                category_rotation_deg=spec.display_plan.category_label_rotation_deg,
                legend_position="inside",
            )
            # Reuse the resolver's original plot field; only remove its added
            # exterior legend column. Preserve all data, marks and other styles.
            base_style = replace(base_style, **{key: getattr(inside, key) for key in (
                "profile_name", "page_width_cm", "layer_left_percent", "layer_width_percent",
            )})
        style = personal_style(base_style, canonical)
        if (preparation.template_id in PERSONAL_BAR_TEMPLATES
                and "bar_fill_transparency_percent" in canonical["overrides"]):
            style = replace(
                style, fill_transparency_percent=canonical["overrides"]["bar_fill_transparency_percent"],
            )
        updated_spec = replace(spec, display_plan=replace(spec.display_plan, figure_style=style))
        if spec.event_raster_layout is not None:
            updated_spec = replace(
                updated_spec, event_raster_layout=replace(spec.event_raster_layout, style=style)
            )
        if (spec.signal_stack_layout is not None
                and {"page_width_cm", "page_height_cm"} & canonical["overrides"].keys()):
            from .signal_stack_layout import build_signal_stack_layout

            updated_spec = replace(updated_spec, signal_stack_layout=build_signal_stack_layout(
                spec.signal_stack_plan, style,
                y_range=(spec.axis_plan.y_from, spec.axis_plan.y_to),
            ))
        if spec.heatmap_layout is not None and "tick_label_size_pt" in canonical["overrides"]:
            # Heatmap row labels are already frozen here; category_order may be
            # empty and sparse display labels must not be treated as missing rows.
            updated_spec = replace(updated_spec, heatmap_layout=replace(
                spec.heatmap_layout,
                cell_label_size_pt=float(round(style.tick_label_size_pt * 0.76)),
                colorbar_label_size_pt=float(max(15, round(style.tick_label_size_pt * 0.88))),
            ))
        updated = replace(preparation, plot_spec=updated_spec,
                          plan_digest=_scientific_plan_digest(preparation, updated_spec))
    report = {
        **canonical, "applied_fields": sorted(canonical["overrides"]),
        "input_plan_digest": before, "output_plan_digest": updated.plan_digest,
    }
    bar_fields = PERSONAL_BAR_STYLE_KEYS & canonical["overrides"].keys()
    if bar_fields and preparation.template_id not in PERSONAL_BAR_TEMPLATES:
        report["applied_fields"] = sorted(canonical["overrides"].keys() - bar_fields)
        report["not_applicable_fields"] = sorted(bar_fields)
    final_style = (
        updated.visual_contract.figure_style
        if hasattr(updated, "visual_contract")
        else updated.plot_spec.display_plan.figure_style
    )
    axis_fields = PERSONAL_AXIS_STYLE_KEYS & canonical["overrides"].keys()
    if axis_fields and not personal_axes_supported(final_style):
        report["applied_fields"] = sorted(set(report["applied_fields"]) - axis_fields)
        report["not_applicable_fields"] = sorted(set(report.get("not_applicable_fields", [])) | axis_fields)
    report["report_hash"] = personal_profile_hash(report)
    return updated, report


def palette_colors(name: str) -> tuple[str, ...]:
    try:
        return PALETTES[name]
    except KeyError as exc:
        raise ValueError(f"Unknown scientific palette: {name}") from exc


def interpolate_hex_colors(start: str, end: str, count: int) -> tuple[str, ...]:
    """Return a deterministic same-family color ramp with ``count`` entries."""
    if count < 1:
        raise ValueError("Color ramp count must be positive")

    def _rgb(value: str) -> tuple[int, int, int]:
        text = value.lstrip("#")
        if len(text) != 6:
            raise ValueError(f"Expected a six-digit hex color, got {value!r}")
        return tuple(int(text[index : index + 2], 16) for index in (0, 2, 4))

    start_rgb = _rgb(start)
    end_rgb = _rgb(end)
    if count == 1:
        return (f"#{start_rgb[0]:02X}{start_rgb[1]:02X}{start_rgb[2]:02X}",)
    colors: list[str] = []
    for index in range(count):
        fraction = index / (count - 1)
        rgb = tuple(
            round(source + (target - source) * fraction)
            for source, target in zip(start_rgb, end_rgb, strict=True)
        )
        colors.append(f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}")
    return tuple(colors)


def series_palette_colors(name: str, count: int) -> tuple[str, ...]:
    """Resolve a non-cycling palette for the visible series count."""

    if count < 1:
        raise ValueError("Series count must be positive")
    colors = palette_colors(name)
    if count <= len(colors):
        if name == "spectroscopy_temperature" and count > 1:
            indices = [round(index * (len(colors) - 1) / (count - 1)) for index in range(count)]
            return tuple(colors[index] for index in indices)
        return colors[:count]
    # Extend a family from its endpoints instead of repeating the first colour.
    return interpolate_hex_colors(colors[0], colors[-1], count)


def signed_effect_colors(values: Iterable[float]) -> tuple[str, ...]:
    """Map signed effect magnitudes to a restrained cool-neutral-warm palette."""
    numeric = [float(value) for value in values]
    finite = [value for value in numeric if math.isfinite(value)]
    negative_scale = max((abs(value) for value in finite if value < 0), default=0.0)
    positive_scale = max((value for value in finite if value > 0), default=0.0)
    deep_cool, soft_cool, neutral, soft_warm, deep_warm = palette_colors("diverging_effect")
    cool_ramp = interpolate_hex_colors(soft_cool, deep_cool, 101)
    warm_ramp = interpolate_hex_colors(soft_warm, deep_warm, 101)
    colors: list[str] = []
    for value in numeric:
        if not math.isfinite(value) or abs(value) < 1e-12:
            colors.append(neutral)
        elif value < 0:
            index = min(100, round(abs(value) / negative_scale * 100))
            colors.append(cool_ramp[index])
        else:
            index = min(100, round(value / positive_scale * 100))
            colors.append(warm_ramp[index])
    return tuple(colors)


def text_span_cm(text: str, size: float, *, bold: bool = False) -> float:
    """Measure Latin glyphs and reserve full physical ems for wide source text."""
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextToPath

    properties = FontProperties(family=["Arial", "DejaVu Sans"], size=size,
                                weight="bold" if bold else "normal")
    widths = []
    for line in text.splitlines() or [""]:
        wide = sum(unicodedata.east_asian_width(char) in {"W", "F"} for char in line)
        regular_text = "".join(char for char in line if unicodedata.east_asian_width(char) not in {"W", "F"})
        width = TextToPath().get_text_width_height_descent(regular_text, properties, ismath=False)[0]
        width += wide * 1.05 * size
        widths.append(float(width) * 2.54 / 72 * 1.12)
    return max(widths)


def resolve_time_frequency_style(x_title: str, y_title: str, value_title: str) -> AdaptiveOriginStyle:
    """Allocate physical text space without shrinking titles or changing supplied labels."""
    plot_width = max(18.0, text_span_cm(x_title, 20.0, bold=True) + 1.0)
    plot_height = max(13.0, text_span_cm(y_title, 20.0, bold=True) + 1.0,
                      text_span_cm(value_title, 17.0) + 1.0)
    width, height = plot_width + 10.0, plot_height + 5.0
    return AdaptiveOriginStyle(
        profile_name="research-time-frequency", page_width_cm=width, page_height_cm=height,
        layer_left_percent=3.5 / width * 100, layer_top_percent=1.5 / height * 100,
        layer_width_percent=plot_width / width * 100, layer_height_percent=plot_height / height * 100,
        frame_line_width_pt=1.1, x_title_upshift_page_percent=0.0,
    )


def time_frequency_scale_region(style: AdaptiveOriginStyle) -> dict[str, float]:
    """Shared physical colorbar gutter and title anchors for preview and Origin."""
    return {
        "left_percent": (
            style.layer_left_percent + style.layer_width_percent + 0.7 / style.page_width_cm * 100
        ),
        "top_percent": style.layer_top_percent,
        "width_percent": 3.36 / style.page_width_cm * 100,
        "height_percent": style.layer_height_percent,
        "bar_width_percent": 0.7 / style.page_width_cm * 100,
        "title_x_percent": (style.page_width_cm - 1.12) / style.page_width_cm * 100,
        "title_y_percent": style.layer_top_percent + style.layer_height_percent / 2,
    }


def resolve_signal_stack_style(
    channel_labels: tuple[str, ...], x_title: str, y_title: str, scale_label: str
) -> AdaptiveOriginStyle:
    """Reserve separate label/data/ruler columns at unchanged physical type sizes."""
    left = max(3.5, max(text_span_cm(label, 17.0) for label in channel_labels) + 2.8)
    right = max(5.0, text_span_cm(scale_label, 17.0) + 1.8)
    row_height = max(
        2.1, max(len(label.splitlines()) for label in channel_labels) * 17 * 2.54 / 72 * 1.4 + 0.4
    )
    plot_width = max(22.0, text_span_cm(x_title, 20.0, bold=True) + 1.0)
    plot_height = max(11.0, len(channel_labels) * row_height, text_span_cm(y_title, 20.0, bold=True) + 1.0)
    width, height = left + plot_width + right, plot_height + 4.5
    return AdaptiveOriginStyle(
        profile_name="research-signal-stack", page_width_cm=width, page_height_cm=height,
        layer_left_percent=left / width * 100, layer_top_percent=1.3 / height * 100,
        layer_width_percent=plot_width / width * 100, layer_height_percent=plot_height / height * 100,
        plot_line_width_pt=1.4, frame_line_width_pt=1.1, x_title_upshift_page_percent=0.0,
        palette_name="publication_signal",
    )


def resolve_adaptive_style(
    *,
    template_id: str,
    plot_kind: str,
    row_count: int,
    series_count: int,
    max_label_length: int = 0,
    max_legend_label_length: int | None = None,
    category_rotation_deg: float = 0.0,
    signed_values: bool = False,
    legend_position: str = "auto",
) -> AdaptiveOriginStyle:
    """Resolve a readable physical page without locking every chart to one size."""

    rows = max(1, int(row_count))
    series = max(1, int(series_count))
    label_len = max(0, int(max_label_length))
    legend_label_len = label_len if max_legend_label_length is None else max(0, int(max_legend_label_length))

    width = 23.5
    height = 16.0
    left = 17.0
    top = 5.5
    layer_height = 80.0
    axis_title = 20.0
    tick = 17.0
    legend = 17.0
    line = 2.6
    frame = 1.8
    palette = "trend_family"
    transparency = 8.0
    heatmap_palette = "RedWhiteBlue.PAL" if signed_values else "Viridis.PAL"
    layer_width_override: float | None = None
    categorical_external_legend = False

    if plot_kind == "bar_error":
        width = min(42.0, max(22.0, 15.0 + rows * 1.55 + series * 0.85))
        height = 16.5 if rows <= 6 else 18.0
        label_width_cm = width * 0.16
        data_width_cm = width * 0.80
        if legend_position == "inside":
            left, layer_width_override = 16.0, 80.0
        else:
            legend_width_cm = max(8.5, min(16.0, 2.5 + legend_label_len * 0.30))
            width = label_width_cm + data_width_cm + legend_width_cm
            left = label_width_cm / width * 100.0
            layer_width_override = data_width_cm / width * 100.0
        palette = "publication_comparison"
        transparency = 6.0
        frame = 1.3
        categorical_external_legend = legend_position != "inside"
    elif plot_kind == "horizontal_bar":
        # Allocate physical regions, not a growing percentage of a growing
        # page. The plot field and typography stay readable for long labels.
        label_width_cm = max(2.6, 1.0 + label_len * tick * 2.54 / 72.0 * 0.52)
        data_width_cm = 17.0 + max(0, series - 3) * 0.4
        legend_width_cm = max(8.5, min(16.0, 2.5 + legend_label_len * 0.30))
        width = label_width_cm + data_width_cm + legend_width_cm
        height = min(30.0, max(15.5, 10.5 + rows * 1.15))
        left = label_width_cm / width * 100.0
        layer_width_override = data_width_cm / width * 100.0
        top = 5.0
        # Reserve a real bottom gutter for tick labels and the value-axis title.
        layer_height = 77.0
        palette = "diverging_effect" if signed_values else "ablation_blue"
        transparency = 16.0
        frame = 1.3
        categorical_external_legend = True
    elif plot_kind in {"stacked_bar", "percent_stacked_bar"}:
        width = min(38.0, max(22.0, 16.0 + rows * 1.65 + series * 0.35))
        height = 16.5
        left = 17.0
        palette = "stacked_blue" if plot_kind == "stacked_bar" else "composition_lilac"
        transparency = 5.0
        if plot_kind == "percent_stacked_bar":
            # Keep a dedicated right-side legend column.  The wider page
            # preserves the physical data-field width instead of shrinking
            # typography to force the legend inside the bars.
            width = min(44.0, max(31.0, width + 7.0) + 0.01)
            left = 14.0
            layer_width_override = 62.0
            legend = 18.0
    elif plot_kind == "pie":
        width = min(34.0, max(22.0, 20.0 + rows * 0.6))
        height = min(24.0, max(16.0, 14.0 + rows * 0.4))
        palette = "composition_teal"
    elif plot_kind == "sankey":
        width = min(46.0, max(30.0, 27.0 + rows * 0.22))
        height = min(28.0, max(17.0, 15.0 + rows * 0.12))
        axis_title = 18.0
        tick = 16.0
        legend = 15.0
        palette = "flow_family"
        transparency = 18.0
    elif plot_kind == "circular_network":
        # ``series`` carries panel count for this axis-free route.  One and
        # two panels remain presentation-friendly; four panels use a 2×2 page
        # instead of shrinking type or locking every dataset to one canvas.
        if series == 1:
            width = min(34.0, max(26.0, 24.0 + label_len * 0.18))
            height = 20.5
        elif series == 2:
            width = min(48.0, max(40.0, 38.0 + label_len * 0.22))
            height = 20.5
        elif series == 3:
            width = min(50.0, max(45.0, 43.0 + label_len * 0.20))
            height = 21.0
        else:
            width = min(46.0, max(39.0, 37.0 + label_len * 0.18))
            height = 32.0
        left = 4.0
        top = 5.0
        layer_height = 77.0
        layer_width_override = 92.0
        axis_title = 20.0
        tick = 17.0
        legend = 17.0
        line = 2.2
        frame = 1.4
        palette = "network_nodes"
        transparency = 8.0
    elif plot_kind == "radar":
        width = min(36.0, max(28.0, 24.0 + rows * 0.70))
        height = min(26.0, max(18.5, 15.0 + rows * 0.70))
        label_width_cm = width * 0.20
        data_width_cm = width * 0.54
        legend_width_cm = max(8.5, min(16.0, 2.5 + legend_label_len * 0.30))
        width = label_width_cm + data_width_cm + legend_width_cm
        left = label_width_cm / width * 100.0
        top = 8.0
        layer_height = 76.0
        plot_height_cm = height * layer_height / 100
        top_cm = height * top / 100 + 0.8
        height += 0.8
        top = top_cm / height * 100
        layer_height = plot_height_cm / height * 100
        layer_width_override = data_width_cm / width * 100.0
        palette = "publication_comparison"
        line = 2.3
        frame = 1.3
        transparency = 82.0
        categorical_external_legend = True
    elif plot_kind == "heatmap":
        dense = rows > 12 or series > 10 or rows * series > 120
        if dense:
            # Keep physical type readable and make the cells denser instead of
            # inflating the page to 48 cm and shrinking labels.  The renderer
            # thins display labels while retaining the complete matrix.
            width = min(
                36.0,
                max(28.0, 22.0 + min(series, 40) * 0.30 + label_len * 0.16),
            )
            height = min(30.0, max(21.0, 15.0 + min(rows, 40) * 0.35))
            left = min(28.0, max(15.0, 14.0 + label_len * 0.45))
            layer_height = 80.0
            layer_width_override = max(52.0, 84.0 - left)
        else:
            # Preserve the spacious annotated profile for small matrices.
            width = min(48.0, max(28.0, 19.0 + series * 1.55 + label_len * 0.24))
            height = min(36.0, max(21.0, 12.0 + rows * 0.72))
            left = min(35.0, max(17.0, 15.0 + label_len * 0.55))
            layer_height = 82.0
            layer_width_override = max(52.0, 89.0 - left)
        top = 5.0
        axis_title = 18.0
        tick = 17.0
        legend = 17.0
    elif plot_kind in {"raw_summary", "violin", "raincloud"}:
        width = min(42.0, max(23.5, 17.0 + series * 3.1 + label_len * 0.20))
        if plot_kind == "raincloud":
            # Origin stores page extent on a discrete internal grid.  This
            # 0.01 cm nudge keeps the frozen physical contract within the
            # existing strict 0.01 cm readback gate for common three-group
            # Raincloud pages instead of weakening verification tolerance.
            width = min(42.0, width + 0.01)
        height = 17.0 if rows <= 60 else 18.5
        left = 17.0
        top = 5.0
        layer_height = 80.0
        palette = "distribution_family"
        transparency = 42.0 if plot_kind == "violin" else 34.0 if plot_kind == "raincloud" else 18.0
    elif plot_kind == "histogram":
        width = min(36.0, max(24.0, 22.0 + series * 1.4))
        height = 17.0
        left = 17.0
        palette = "distribution_family"
        transparency = 28.0
    elif plot_kind == "forest":
        width = min(48.0, max(28.0, 23.0 + label_len * 0.48))
        height = min(32.0, max(16.5, 10.5 + rows * 1.25))
        left = min(48.0, max(25.0, 22.0 + label_len * 0.75))
        top = 5.0
        layer_height = 82.0
        palette = "evidence_family"
        transparency = 5.0
    elif plot_kind == "bubble":
        width = 27.0
        height = 18.0
        left = 17.0
        palette = "evidence_family"
        transparency = 25.0
    elif plot_kind == "trajectory3d":
        # Verified Origin 2024b glTraject geometry and physical typography.
        width = 24.0
        height = 18.0
        left = 18.0
        top = 5.0
        layer_height = 70.0
        layer_width_override = 64.0
        axis_title = 22.0
        tick = 18.0
        legend = 17.0
        line = 2.2
        palette = "trajectory3d_family"
        transparency = 0.0
    elif plot_kind == "density_ridgeline3d":
        # Ordered condition colours identify the scientific third axis; line
        # style distinguishes the two supplied profiles within each condition.
        width = min(34.0, max(27.0, 25.0 + series * 0.85))
        height = 20.5
        left = 16.0
        top = 4.5
        layer_height = 74.0
        layer_width_override = 68.0
        axis_title = 22.0
        tick = 18.0
        legend = 18.0
        line = 2.4
        frame = 1.8
        palette = "trajectory3d_family"
        transparency = 0.0
    elif plot_kind == "diagnostic_curve":
        width = min(34.0, max(23.5, 22.5 + series * 0.85))
        height = width
        left = 17.0
        top = 5.0
        layer_height = 79.0
        palette = "medical_ai"
        line = 2.4
        transparency = 5.0
    elif plot_kind == "calibration_curve":
        width = 25.5
        height = 25.5
        left = 17.0
        top = 5.0
        layer_height = 79.0
        palette = "medical_ai"
        line = 2.2
        transparency = 68.0
    elif plot_kind == "decision_curve":
        width = min(34.0, max(27.0, 24.0 + series * 0.8))
        height = 18.0
        left = 17.0
        palette = "medical_ai"
        line = 2.2
        transparency = 5.0
    elif plot_kind == "bland_altman":
        width = 27.0
        height = 18.0
        left = 17.0
        palette = "medical_ai"
        line = 1.8
        transparency = 22.0
    elif plot_kind == "paired_trajectory":
        width = min(34.0, max(25.0, 23.0 + min(series, 20) * 0.34))
        height = 17.0
        left = 17.0
        palette = "paired_neutral"
        line = 1.25
        transparency = 34.0
    elif plot_kind == "grouped_box":
        width = min(44.0, max(27.0, 22.0 + series * 1.25 + label_len * 0.18))
        height = 18.0
        left = 17.0
        top = 5.0
        layer_height = 78.0
        palette = "grouped_box_medical"
        line = 1.8
        legend = 18.0
        transparency = 28.0
    elif plot_kind == "pl_decay":
        width = min(36.0, max(27.0, 25.0 + series * 0.85))
        height = 18.5
        left = 17.0
        palette = "spectroscopy_jewel"
        line = 2.0
        transparency = 4.0
    elif plot_kind == "pl_spectrum":
        width = min(36.0, max(26.0, 24.0 + series * 0.80))
        height = 17.5
        left = 17.0
        palette = "spectroscopy_temperature" if series > 3 else "materials_comparison"
        line = 2.2
        transparency = 4.0
    elif plot_kind == "uv_vis":
        width = min(38.0, max(29.0, 27.0 + series * 0.75))
        height = 20.0
        left = 17.0
        top = 5.0
        layer_height = 81.0
        palette = "materials_comparison"
        line = 2.2
        transparency = 4.0
    elif plot_kind == "dsc":
        width = min(38.0, max(27.0, 24.5 + series * 0.90))
        height = 18.0
        left = 18.0
        layer_height = 80.0
        palette = "thermal_analysis"
        line = 2.2
        transparency = 4.0
    elif plot_kind == "nmr":
        width = min(40.0, max(29.0, 26.0 + series * 0.90))
        height = min(24.0, 18.0 + max(0, series - 3) * 0.60)
        left = 17.0
        layer_height = 80.0
        palette = "materials_comparison"
        line = 2.0
        transparency = 3.0
    elif plot_kind == "ftir":
        width = min(40.0, max(29.0, 26.0 + series * 0.82))
        height = min(24.0, 18.0 + max(0, series - 4) * 0.45)
        left = 17.0
        layer_height = 80.0
        palette = "spectroscopy_temperature" if series > 3 else "materials_comparison"
        line = 2.0
        transparency = 3.0
    elif plot_kind == "xps_compare":
        width = min(40.0, max(29.0, 25.5 + series * 0.95))
        height = min(24.0, 18.0 + max(0, series - 4) * 0.50)
        left = 18.0
        layer_height = 80.0
        palette = "materials_comparison"
        line = 2.2
        transparency = 3.0
    elif plot_kind == "shap_summary":
        width = min(48.0, max(28.0, 23.0 + label_len * 0.52))
        width = min(48.0, width + 0.01)
        height = min(32.0, max(17.0, 10.5 + rows * 1.30))
        left = min(50.0, max(25.0, 22.0 + label_len * 0.78))
        top = 7.0
        layer_height = 78.0
        palette = "medical_ai"
        transparency = 18.0
    elif plot_kind in {"line", "line_error", "scatter", "nyquist", "stacked_line"}:
        width = min(34.0, max(23.5, 22.0 + series * 0.75))
        height = 16.5 if series <= 5 else 18.0
        palette = "trend_family"
        transparency = 8.0

    if category_rotation_deg:
        height = max(height, 18.5)
        layer_height = min(layer_height, 68.0)

    layer_width = layer_width_override or max(34.0, 96.0 - left)
    external_legend = series > 1 and plot_kind in {
        "line", "stacked_line", "line_error", "scatter", "diagnostic_curve", "decision_curve"
    }
    if external_legend:
        # Add a real page column, preserving the physical plot field rather
        # than squeezing the data or shrinking the typography. Native text
        # bounds are checked again by the renderer before accepting the plot.
        if legend_position != "inside":
            original_width = width
            width += max(6.5, min(16.0, 2.5 + legend_label_len * 0.30))
            left *= original_width / width
            layer_width *= original_width / width
        palette = "publication_signal"
        line = 2.2
        frame = 1.3
        external_legend = legend_position != "inside"
    return AdaptiveOriginStyle(
        profile_name=f"adaptive-{template_id}-{plot_kind}" + (
            "-external-legend" if external_legend or categorical_external_legend else ""
        ),
        page_width_cm=round(width, 2),
        page_height_cm=round(height, 2),
        layer_left_percent=round(left, 2),
        layer_top_percent=top,
        layer_width_percent=round(layer_width, 2),
        layer_height_percent=layer_height,
        x_title_upshift_page_percent=(
            0.0
            if external_legend or categorical_external_legend or plot_kind == "percent_stacked_bar" else 1.5
        ),
        axis_title_size_pt=axis_title,
        tick_label_size_pt=tick,
        legend_size_pt=legend,
        plot_line_width_pt=line,
        frame_line_width_pt=frame,
        major_tick_length_pt=5.5,
        minor_tick_length_pt=3.0,
        error_bar_width_pt=1.8,
        bar_border_width_pt=1.4,
        fill_transparency_percent=transparency,
        palette_name=palette,
        heatmap_palette=heatmap_palette,
    )


__all__ = [
    "AdaptiveOriginStyle",
    "PALETTES",
    "interpolate_hex_colors",
    "palette_colors",
    "series_palette_colors",
    "resolve_adaptive_style",
    "signed_effect_colors",
]
