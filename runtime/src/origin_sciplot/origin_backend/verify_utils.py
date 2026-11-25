"""Verification helpers for Origin-generated artifacts."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .base_style_contract import FIXED_ORIGIN_STYLE, pt_to_origin_width_units
from .safe_errors import OriginGeometryError

# Origin stores page dimensions in internal/printer units and can round an
# adaptive size by roughly one tenth of a millimetre on readback.  A 0.3 mm
# gate accepts that quantization while remaining far below a visible layout
# change.
PAGE_SIZE_TOLERANCE_CM = 0.03
LAYER_GEOMETRY_TOLERANCE_PERCENT = 0.03


class NativePlotReference:
    """An owned plot slot that survives OriginExt GetIndex proxy invalidation."""

    def __init__(self, native_range: str, layer: Any) -> None:
        match = re.fullmatch(r"\[[\w]+\][1-9]\d*![1-9]\d*", native_range)
        if match is None:
            raise ValueError("Expected an explicit native graph-layer plot range")
        self._native_range = native_range
        self.layer = layer
        self.native_index = int(native_range.rsplit("!", 1)[1])

    def lt_range(self) -> str:
        return self._native_range

    def set_cmd(self, *commands: str) -> None:
        script = "{" + f"range rr={self._native_range};" + "".join(f"set rr {c};" for c in commands) + "}"
        if not self.layer.LT_execute(script):
            raise RuntimeError("Origin could not style the owned native plot range")


def _finite_float(value: Any, label: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise RuntimeError(f"Origin geometry readback is non-finite: {label}")
    return number


def _read_bridge_geometry(layer: Any) -> dict[str, float | None]:
    """Read the originpro bridge for diagnostics without making it canonical."""

    state: dict[str, float | None] = {}
    for output_name, property_name in (
        ("bridge_layer_unit", "unit"),
        ("bridge_left_percent", "left"),
        ("bridge_top_percent", "top"),
        ("bridge_width_percent", "width"),
        ("bridge_height_percent", "height"),
        ("bridge_factor", "factor"),
    ):
        try:
            value = float(layer.get_float(property_name))
        except Exception:
            value = math.nan
        state[output_name] = value if math.isfinite(value) else None
    return state


def read_layer_geometry_percent(origin: Any, layer: Any) -> dict[str, Any]:
    """Read percent-of-page geometry through two cross-checked LabTalk paths.

    A reported Origin 2026b SR1 environment returned a conflicting ``left``
    value through the originpro ``GetNumProp`` bridge. LabTalk's layer
    properties and the documented ``layer -x`` command provide the native
    cross-check needed to distinguish a bridge-only disagreement from a real
    layout failure. The bridge values are retained as diagnostics, but never
    override two agreeing native readbacks.

    ``layer -x`` has a non-intuitive official order: ``v1=width``,
    ``v2=height``, ``v3=left``, and ``v4=top``.
    """

    layer.activate()
    # Clear the shared v-registers first.  If a version returns success without
    # refreshing them, the finite-value gate below must fail instead of
    # accepting geometry left behind by an earlier layer.
    command_ok = layer.obj.LT_execute(
        "v1=NA();v2=NA();v3=NA();v4=NA();layer -x;"
    )
    if not command_ok:
        raise RuntimeError("Origin LabTalk layer geometry command failed: layer -x")

    # Capture v1..v4 immediately; later LabTalk expression evaluations must
    # not get a chance to replace the command result on another version.
    layer_x = {
        "width_percent": _finite_float(
            origin.lt_float("v1"), "layer -x v1 (width)"
        ),
        "height_percent": _finite_float(
            origin.lt_float("v2"), "layer -x v2 (height)"
        ),
        "left_percent": _finite_float(
            origin.lt_float("v3"), "layer -x v3 (left)"
        ),
        "top_percent": _finite_float(
            origin.lt_float("v4"), "layer -x v4 (top)"
        ),
    }
    direct = {
        "layer_unit": _finite_float(origin.lt_float("layer.unit"), "layer.unit"),
        "left_percent": _finite_float(origin.lt_float("layer.left"), "layer.left"),
        "top_percent": _finite_float(origin.lt_float("layer.top"), "layer.top"),
        "width_percent": _finite_float(origin.lt_float("layer.width"), "layer.width"),
        "height_percent": _finite_float(origin.lt_float("layer.height"), "layer.height"),
        "factor": _finite_float(origin.lt_float("layer.factor"), "layer.factor"),
    }
    if abs(direct["layer_unit"] - 1.0) > LAYER_GEOMETRY_TOLERANCE_PERCENT:
        raise RuntimeError(
            "Origin layer geometry unit verification failed: "
            f"got {direct['layer_unit']:.3f}, expected 1 (% of page)"
        )
    for key, layer_x_value in layer_x.items():
        direct_value = direct[key]
        if abs(direct_value - layer_x_value) > LAYER_GEOMETRY_TOLERANCE_PERCENT:
            raise RuntimeError(
                "Origin LabTalk layer geometry paths disagree: "
                f"{key} direct={direct_value:.3f}, layer-x={layer_x_value:.3f}"
            )

    bridge = _read_bridge_geometry(layer)
    bridge_geometry_consistent = (
        bridge["bridge_layer_unit"] is not None
        and abs(float(bridge["bridge_layer_unit"]) - direct["layer_unit"])
        <= LAYER_GEOMETRY_TOLERANCE_PERCENT
        and all(
            bridge[f"bridge_{key}"] is not None
        and abs(float(bridge[f"bridge_{key}"]) - direct[key])
        <= LAYER_GEOMETRY_TOLERANCE_PERCENT
            for key in (
                "left_percent",
                "top_percent",
                "width_percent",
                "height_percent",
                "factor",
            )
        )
    )
    return {
        **direct,
        "geometry_readback_source": "labtalk_crosscheck",
        "layer_x_left_percent": layer_x["left_percent"],
        "layer_x_top_percent": layer_x["top_percent"],
        "layer_x_width_percent": layer_x["width_percent"],
        "layer_x_height_percent": layer_x["height_percent"],
        **bridge,
        "bridge_geometry_consistent": bridge_geometry_consistent,
    }


def require_nonempty(path: str | Path) -> None:
    candidate = Path(path)
    if not candidate.is_file() or candidate.stat().st_size <= 0:
        raise RuntimeError(f"Required output was not generated: {candidate.name}")


def verify_text_sizes(
    labels: Mapping[str, Any],
    expected_points: Mapping[str, float],
    *,
    tolerance: float = 0.05,
) -> dict[str, float]:
    """Read back Origin text-object point sizes and enforce the locked contract."""
    state: dict[str, float] = {}
    for name, expected in expected_points.items():
        label = labels.get(name)
        if label is None:
            raise RuntimeError(f"Origin text verification failed: missing {name}")
        actual = float(label.get_float("fsize"))
        state[f"{name}.fsize"] = actual
        if abs(actual - float(expected)) > tolerance:
            raise RuntimeError(
                f"Origin text verification failed: {name}.fsize={actual:g}, expected {expected:g}"
            )
    return state


def verify_text_fonts(
    op: Any,
    labels: Mapping[str, Any],
    font_family: str,
    *,
    tolerance: float = 0.5,
) -> dict[str, int | str]:
    """Read back every editable Origin text object's font code.

    Origin does not reliably cascade a page font to axis titles, legends, and
    manually added labels.  Each object must therefore be styled separately
    and verified separately, especially after a dataset-backed axis label is
    rebound with ``axis -ps``.
    """
    expected = int(round(float(op.lt_float(f"font({font_family})"))))
    state: dict[str, int | str] = {
        "font_family_expected": font_family,
        "font_code_expected": expected,
    }
    for name, label in labels.items():
        if label is None:
            raise RuntimeError(f"Origin font verification failed: missing {name}")
        actual = int(round(float(label.get_float("font"))))
        state[f"{name}.font_code"] = actual
        if abs(actual - expected) > tolerance:
            raise RuntimeError(
                f"Origin font verification failed: {name}.font={actual}, expected {font_family} ({expected})"
            )
    return state


def _personal_text_size(name: str, overrides: Mapping[str, Any]) -> float | None:
    """Classify native axis titles and existing manual tick labels by role."""
    lower = name.lower()
    if lower in {"xb", "xt", "yl", "yr", "zl", "zr", "zb", "zt", "zf", "ztitle", "eventytitle",
                 "shapmeantitle", "shapgrouptitle"}:
        return overrides.get("axis_title_size_pt")
    if lower.startswith(("heatmaprow", "eventtrial", "shapfeaturename")):
        return overrides.get("tick_label_size_pt")
    if lower == "legend":
        return overrides.get("legend_size_pt", overrides.get("annotation_size_pt"))
    return overrides.get("annotation_size_pt")


def _personal_read_plot_option(origin: Any, plot: Any, flag: str) -> float:
    variable = f"__personal_{flag}"
    if not plot.layer.LT_execute(f"{variable}=NANUM;"):
        raise RuntimeError(f"Origin personal-profile readback initialization failed: {flag}")
    return _read_plot_option(origin, plot, f"-{flag}", variable)


def _personal_plot_state(origin: Any, graph: Any, *, column_options: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """Keep independent line, edge, fill and symbol codes as preservation evidence."""
    records = []
    for layer in graph:
        layer.activate()
        for plot in layer.plot_list():
            kind = int(_personal_read_plot_option(origin, plot, "pt"))
            record: dict[str, Any] = {"range": plot.lt_range(), "type": kind}
            # Native -pt values are shared with the existing categorical reader.
            # Error bars have no symbol or data-label properties; missing values
            # must not become two equal None values and fake preservation.
            flags = ["s"]
            if kind in {200, 201, 202, 231, 233, 240}:
                flags.extend(("c", "w"))
            if kind in {201, 202}:
                flags.extend(("cse", "csf", "kf", "k", "z", "kh"))
            if kind in {203, 207, 213, 215, 216}:
                flags.extend(("pfb", "pbc", "pbw"))
            for flag in flags:
                record[flag] = _personal_read_plot_option(origin, plot, flag)
            if kind in {203, 207, 213, 215, 216} and column_options:
                record["column_fill"] = read_column_fill(plot)
            records.append(record)
    return records


def _personal_remove_inline_bold(text: str) -> str:
    """Remove only bold grouping, preserving nested scientific text markup."""
    while (start := text.find(r"\b(")) >= 0:
        depth, end = 1, start + 3
        while end < len(text) and depth:
            depth += (text[end] == "(") - (text[end] == ")")
            end += 1
        if depth:
            raise RuntimeError("Personal profile text has an unbalanced inline bold group.")
        text = text[:start] + text[start + 3:end - 1] + text[end:]
    return text


def _personal_inline_bold(text: str, enabled: bool) -> str:
    """Use Origin's native text markup; ordinary labels have no bold scalar."""
    plain = _personal_remove_inline_bold(text.replace("\r\n", "\n").replace("\r", "\n"))
    if not enabled:
        return plain
    return "\n".join(r"\b(" + line + ")" if line else line for line in plain.split("\n"))


def _personal_tick_auto_details(origin: Any, graph: Any, layer_index: int, *, apply: bool) -> dict[str, Any]:
    """Read real Auto sentinels with Origin C; missing LabTalk props aren't evidence."""
    import ctypes
    helper = Path(__file__).with_name("personal_axes.c")
    short = ctypes.create_unicode_buffer(4096)
    if not ctypes.windll.kernel32.GetShortPathNameW(str(helper), short, len(short)):
        raise RuntimeError("Origin axis helper path could not be resolved.")
    origin.lt_exec(f'__ep_axis_compile=run.LoadOC("{short.value}",16);')
    if origin.lt_float("__ep_axis_compile") != 0:
        raise RuntimeError("Origin axis detail reader did not compile.")
    origin.set_lt_str("__ep_axis_graph", graph.name)
    # Clear every output before calling native code; stale values must fail.
    origin.lt_exec("".join(f"__ep_axis_{i}_{key}=NA();" for i in range(4)
                           for key in ("minor_length", "major_width", "minor_width")))
    origin.lt_exec(f"__ep_axis_details_ok=0;__ep_axis_layer={layer_index};__ep_axis_apply={int(apply)};"
                   "run -oc editaplot_personal_tick_details;")
    if origin.lt_float("__ep_axis_details_ok") != 1:
        raise RuntimeError("Origin axis detail readback failed.")
    result = {}
    for i, side in enumerate(("bottom", "top", "left", "right")):
        result[side] = {}
        for key in ("minor_length", "major_width", "minor_width"):
            if origin.lt_float(f"__ep_axis_{i}_{key}") != 1:
                raise RuntimeError(f"Personal axis {side} {key} is not Auto.")
            result[side][key] = "auto"
    return result


def apply_personal_axes(origin: Any, graph: Any, style: Any, *, apply: bool = True) -> list[dict[str, Any]]:
    """Customize only ordinary Cartesian axes; preserve scales and label roles."""
    from ..scientific_visual import personal_axis_style
    values = personal_axis_style(style)
    if not values:
        return []
    records = []
    for index, layer in enumerate(graph):
        layer.activate()
        pair_labels = {a: int(_finite_float(origin.lt_float(f"layer.{a}.showLabels"), f"{a}.showLabels"))
                       for a in ("x", "y")}
        pair_axes = {a: int(_finite_float(origin.lt_float(f"layer.{a}.showAxes"), f"{a}.showAxes"))
                     for a in ("x", "y")}
        if not any(pair_axes.values()):
            records.append({"layer": index + 1, "applicable": False, "reason": "axis_free_layer"})
            continue
        before_scale = {f"{a}.{p}": _finite_float(origin.lt_float(f"layer.{a}.{p}"), f"{a}.{p}")
                        for a in ("x", "y") for p in ("from", "to", "inc", "type")}
        expected = {}
        for a in ("x2", "y2", "x", "y"):
            enabled = bool(pair_labels[a[0]] & (2 if a.endswith("2") else 1))
            if "frame_line_width_pt" in values:
                expected[f"{a}.thickness"] = values["frame_line_width_pt"]
            if "axis_color" in values:
                expected[f"{a}.color"] = 1  # documented LabTalk black
            if "major_tick_length_pt" in values:
                expected[f"{a}.ticklength"] = values["major_tick_length_pt"]
            if "tick_direction" in values:
                expected[f"{a}.ticks"] = (10 if values["tick_direction"] == "out" else 5) if enabled else 0
            if a in ("x", "y"):
                if "axis_frame" in values:
                    expected[f"{a}.showAxes"] = 3
                    expected[f"{a}.showGrids"] = 0
                # Category/text axes and logarithmic subdivisions inherit their
                # scientific meaning. Only linear numeric visible axes change.
                if "numeric_minor_ticks" in values and enabled:
                    label_type = int(origin.lt_float(f"layer.{a}.label.type"))
                    scale_type = int(before_scale[f"{a}.type"])
                    if label_type == 1 and scale_type in (0, 1):
                        expected[f"{a}.minorTicks"] = values["numeric_minor_ticks"]
        if apply:
            for key, value in expected.items():
                if not layer.obj.LT_execute(f"layer.{key}={value:g};"):
                    raise RuntimeError(f"Origin personal axis write failed: {key}")
        details = (_personal_tick_auto_details(origin, graph, index, apply=apply)
                   if values.get("tick_details") == "auto" else {})
        layer.activate()
        actual = {key: _finite_float(origin.lt_float(f"layer.{key}"), key) for key in expected}
        for key, value in expected.items():
            if abs(actual[key] - value) > 0.05:
                raise RuntimeError(f"Personal axis readback mismatch: {key}={actual[key]}, expected {value}.")
        if any(origin.lt_float(f"layer.{key}") != value for key, value in before_scale.items()):
            raise RuntimeError("Personal axis styling changed a source scale.")
        if any(int(origin.lt_float(f"layer.{a}.showLabels")) != value for a, value in pair_labels.items()):
            raise RuntimeError("Personal axis styling changed axis label visibility.")
        records.append({"layer": index + 1, "applicable": True, "properties": actual,
                        "tick_details": details, "scales_preserved": True,
                        "label_visibility_preserved": True})
    return records


def apply_personal_typography(origin: Any, graph: Any, style: Any, *, apply: bool = True) -> dict[str, Any]:
    """Apply/read only the frozen typography; retain template marks and visibility.

    Reuses native graph objects, font lookup, page readback and plot-option reads.
    ``apply=False`` is the independent saved-OPJU verification path.
    """
    from ..scientific_visual import normalize_personal_profile, personal_profile_hash, personal_bar_style

    if not getattr(style, "personal_profile", None):
        return {}
    profile = normalize_personal_profile(style.personal_profile)
    values = profile["overrides"]
    font = (int(round(origin.lt_float(f"font({values['font_family']})")))
            if "font_family" in values else None)
    if font is not None and font <= 0:
        raise RuntimeError("The personal profile font is not available in Origin.")
    column_options = personal_bar_style(style)
    original_marks = _personal_plot_state(origin, graph, column_options=column_options)
    axis_styles = apply_personal_axes(origin, graph, style, apply=apply)
    page = read_page_geometry_cm(origin, graph)
    for prop, key in (("width_cm", "page_width_cm"), ("height_cm", "page_height_cm")):
        if key in values and abs(page[prop] - values[key]) > PAGE_SIZE_TOLERANCE_CM:
            raise RuntimeError(f"Personal profile native page {prop} readback failed.")
    axes, texts, plot_labels, color_scales = [], [], [], []
    visibility_checks: list[tuple[Any, float]] = []
    for layer_index, layer in enumerate(graph, 1):
        layer.activate()
        pair_visibility = {axis: _finite_float(origin.lt_float(f"layer.{axis}.showLabels"), f"{axis}.showLabels")
                           for axis in ("x", "y")}
        for axis in ("x", "y", "x2", "y2", "z"):
            # showLabels is a shared pair bitmask (1 bottom/left, 2 top/right).
            if axis == "z":
                visible = float(origin.lt_float("layer.z.showLabels"))
                if not math.isfinite(visible):  # No Z axis on ordinary 2D graphs.
                    continue
            else:
                visible = int(pair_visibility[axis[0]]) & (2 if axis.endswith("2") else 1)
            if visible <= 0:
                continue
            expected = {}
            if font is not None:
                expected["font"] = font
            if "tick_label_size_pt" in values:
                expected["pt"] = values["tick_label_size_pt"]
            if "bold" in values:
                expected["bold"] = int(values["bold"])
            if apply:
                for prop, value in expected.items():
                    layer.set_float(f"{axis}.label.{prop}", value)
            actual = {prop: float(layer.get_float(f"{axis}.label.{prop}")) for prop in expected}
            if any(not math.isfinite(actual[k]) or abs(actual[k] - v) > 0.05 for k, v in expected.items()):
                raise RuntimeError(f"Personal profile {axis} tick typography readback failed.")
            axes.append({"layer": layer_index, "axis": axis, **actual})
        for native in layer.obj.GraphObjects:
            if native.GetObjectType() not in (2, 3):  # Origin native text and legend.
                continue
            visible = _finite_float(native.GetShow(), "GraphObject.Show")
            visibility_checks.append((native, visible))
            if not visible or not native.GetText():
                continue
            name = native.GetName()
            label = layer.label(name)
            original_text = str(label.text)
            size = _personal_text_size(name, values)
            expected = {}
            if size is not None:
                expected["fsize"] = float(size)
            if font is not None:
                expected["font"] = font
            if apply:
                # Normalize only presentation overrides; preserve chemical
                # subscripts/superscripts, plot legend samples and substitutions.
                text = re.sub(r"\\p[0-9]+(?:\.[0-9]+)?\(", r"\\p100(", original_text) if size is not None else original_text
                if font is not None:
                    text = re.sub(r"\\f:[^()]+\(", lambda _: f"\\f:{values['font_family']}(", text)
                if "bold" in values:
                    text = _personal_inline_bold(text, values["bold"])
                if text != original_text:
                    label.text = text
                for prop, value in expected.items():
                    label.set_float(prop, value)
            actual = {prop: float(label.get_float(prop)) for prop in expected}
            if any(not math.isfinite(actual[k]) or abs(actual[k] - v) > 0.05 for k, v in expected.items()):
                raise RuntimeError(f"Personal profile text {name} typography readback failed: actual={actual}, expected={expected}.")
            text = str(label.text)
            if size is not None and any(float(p) != 100 for p in re.findall(r"\\p([0-9]+(?:\.[0-9]+)?)\(", text)):
                raise RuntimeError(f"Personal profile text {name} retains a conflicting inline size.")
            if "bold" in values:
                normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
                canonical_text = _personal_inline_bold(normalized_text, values["bold"])
                if normalized_text != canonical_text:
                    raise RuntimeError(
                        f"Personal profile text {name} has conflicting inline bold: "
                        f"actual={normalized_text[:240]!r}, canonical={canonical_text[:240]!r}."
                    )
                actual["bold"] = int(values["bold"])
                actual["bold_source"] = "inline_markup"
            if font is not None and any(f != values["font_family"] for f in re.findall(r"\\f:([^()]+)\(", text)):
                raise RuntimeError(f"Personal profile text {name} retains a conflicting inline font.")
            texts.append({"layer": layer_index, "name": name, "text": text, **actual})
        for plot_index, plot in enumerate(layer.plot_list(), 1):
            # Changing label typography does not turn hidden labels on.
            kind = int(_personal_read_plot_option(origin, plot, "pt"))
            if kind in (231, 233):
                plot_labels.append({"layer": layer_index, "plot": plot_index, "type": kind,
                                    "applicable": False, "reason": "error_bar"})
                continue
            expected = {}
            if "annotation_size_pt" in values:
                expected["qs"] = values["annotation_size_pt"]
            if font is not None:
                expected["qf"] = font
            if "bold" in values:
                expected["qb"] = int(values["bold"])
            actual = {}
            for flag, value in expected.items():
                if apply:
                    plot.set_cmd(f"-{flag} {value:g}")
                measured = _personal_read_plot_option(origin, plot, flag)
                if abs(measured - value) > 0.05:
                    raise RuntimeError(f"Personal profile plot-label {flag} readback failed.")
                actual[flag] = measured
            plot_labels.append({"layer": layer_index, "plot": plot_index, **actual})
        for native in layer.obj.GraphObjects:
            name = native.GetName()
            if not name.lower().startswith("spectrum"):
                continue
            visible = _finite_float(native.GetShow(), "GraphObject.Show")
            visibility_checks.append((native, visible))
            if not visible:
                continue
            expected = {}
            if "annotation_size_pt" in values:
                expected["fsize"] = values["annotation_size_pt"]
            if font is not None:
                expected["font"] = font
            if "bold" in values:
                expected["bold"] = int(values["bold"])
            if apply:
                origin.lt_exec("".join(f"{name}.labels.{k}={v:g};" for k, v in expected.items()))
            actual = {k: float(origin.lt_float(f"{name}.labels.{k}")) for k in expected}
            if any(not math.isfinite(actual[k]) or abs(actual[k] - v) > 0.05 for k, v in expected.items()):
                raise RuntimeError("Personal profile color-scale typography readback failed.")
            color_scales.append({"layer": layer_index, "name": name, **actual})
    origin.lt_exec("doc -uw;")
    if any(_finite_float(native.GetShow(), "GraphObject.Show") != visible for native, visible in visibility_checks):
        raise RuntimeError("Personal typography changed text-object visibility.")
    if original_marks != _personal_plot_state(origin, graph, column_options=column_options):
        raise RuntimeError("Personal typography changed a template line, symbol, edge or fill style.")
    return {
        "id": profile["id"], "profile_hash": personal_profile_hash(profile), "overrides": values,
        "page": page, "axes": axes, "axis_styles": axis_styles, "texts": texts, "plot_labels": plot_labels,
        "color_scales": color_scales, "plot_styles": original_marks,
        "plot_styles_preserved": True, "passed": True,
    }


def _read_plot_option(op: Any, plot: Any, option: str, variable_name: str) -> float:
    command = f"{{range rr={plot.lt_range()};get rr {option} {variable_name};}}"
    result = plot.layer.LT_execute(command)
    if not result:
        raise RuntimeError(f"Origin plot verification command failed: {option}")
    value = float(op.lt_float(variable_name))
    if not math.isfinite(value):
        raise RuntimeError(f"Origin plot verification returned a non-finite value: {option}")
    return value


def verify_plot_line_widths(
    op: Any,
    plots: Mapping[str, Any],
    expected_points: float,
    *,
    tolerance_units: float = 1.0,
) -> dict[str, dict[str, float]]:
    """Read back visible DataPlot widths; LabTalk ``get -w`` returns pt x 500."""
    expected_units = float(pt_to_origin_width_units(expected_points))
    state: dict[str, dict[str, float]] = {}
    for index, (name, plot) in enumerate(plots.items()):
        actual_units = _read_plot_option(op, plot, "-w", f"__osc_width_{index}")
        state[name] = {
            "set_w_units": actual_units,
            "line_width_pt": actual_units / 500.0,
        }
        if abs(actual_units - expected_units) > tolerance_units:
            raise RuntimeError(
                f"Origin plot width verification failed: {name}={actual_units / 500.0:g} pt, "
                f"expected {expected_points:g} pt"
            )
    return state


def verify_plot_color(
    op: Any,
    plot: Any,
    expected_html: str,
    *,
    variable_name: str,
) -> dict[str, float | str]:
    """Read back the effective line/symbol edge color after a ``set -c`` call."""
    actual = _read_plot_option(op, plot, "-c", variable_name)
    expected = float(op.ocolor(expected_html))
    if int(actual) != int(expected):
        raise RuntimeError(
            f"Origin plot color verification failed: {actual:g}, expected {expected:g} for {expected_html}"
        )
    return {
        "html": expected_html,
        "origin_color_code": actual,
    }


def _column_object(plot: Any) -> Any:
    if isinstance(plot, NativePlotReference):
        return list(plot.layer.DataPlots)[plot.native_index - 1]
    return plot.obj


def read_column_fill(plot: Any) -> dict[str, float]:
    """Read named scalar theme fields; never deserialize native color-list blobs."""
    native = _column_object(plot)
    theme = native.GetTheme()
    pattern = theme.Pattern
    fill = pattern.Fill
    fields = {
        "primary_color": fill.FillColor,
        "shading_mode": fill.ShadingMode,
        "pattern": fill.Pattern.Style,
        "border_color": pattern.Border.Color,
        "transparency_percent": pattern.Transparency,
    }
    mode = int(fill.ShadingMode.GetIntValue())
    if mode == 2:  # Native theme is zero-based; LabTalk -pfm is one-based.
        fields.update({
            "secondary_color": fill.GradColor,
            "direction": fill.GradDirection,
            "secondary_transparency_auto": fill.Auto,
            "secondary_transparency_percent": fill.PtnBkColor2Trans,
        })
    return {key: _finite_float(node.GetDoubleValue(), key) for key, node in fields.items()}


def apply_column_style(op: Any, plot: Any, color: str, *, border_width_pt: float, style: Any = None) -> None:
    """Set the documented column fill, border and point-sized border width."""
    if not math.isfinite(border_width_pt) or border_width_pt <= 0:
        raise ValueError("Column border width must be a positive point value")
    code = int(op.ocolor(color))
    from ..scientific_visual import column_highlight_color, personal_bar_style

    options = personal_bar_style(style) if style is not None else {}
    plot.set_cmd(f"-pfb {code}")
    plot.set_cmd(f"-pbc {-4 if options.get('bar_border') == 'none' else code}")
    plot.set_cmd(f"-vw {border_width_pt:g}")
    if options.get("bar_fill") == "two_color_center":
        plot.set_cmd("-pfm 3")
        plot.set_cmd("-pfp 0")
        plot.set_cmd(f"-pff {int(op.ocolor(column_highlight_color(color)))}")
        native = _column_object(plot)
        theme = native.GetTheme()
        theme.Pattern.Fill.GradDirection.SetIntValue(9)
        theme.Pattern.Fill.Auto.SetIntValue(1)
        theme.Pattern.Fill.PtnBkColor2Trans.SetDoubleValue(style.fill_transparency_percent)
        native.PutTheme(theme)


def verify_column_colors(
    op: Any, plot: Any, expected_html: str, *, variable_name: str, style: Any = None,
) -> dict[str, Any]:
    """Read the column fill and border independently; -c is a line property."""
    expected = int(op.ocolor(expected_html))
    from ..scientific_visual import column_highlight_color, personal_bar_style

    options = personal_bar_style(style) if style is not None else {}
    expected_border = -4 if options.get("bar_border") == "none" else expected
    fill = _read_plot_option(op, plot, "-pfb", f"{variable_name}_fill")
    border = _read_plot_option(op, plot, "-pbc", f"{variable_name}_border")
    if int(fill) != expected or int(border) != expected_border:
        raise RuntimeError(
            f"Origin column color verification failed: fill={fill:g}, border={border:g}, "
            f"expected {expected} for {expected_html}"
        )
    result = {"html": expected_html, "fill_origin_color_code": fill, "border_origin_color_code": border}
    if options.get("bar_fill") == "two_color_center":
        actual = read_column_fill(plot)
        highlight = column_highlight_color(expected_html)
        expected_fields = {
            "primary_color": expected, "secondary_color": int(op.ocolor(highlight)),
            "shading_mode": 2, "direction": 9, "pattern": 0,
            "border_color": expected_border, "transparency_percent": style.fill_transparency_percent,
            "secondary_transparency_auto": 1,
            "secondary_transparency_percent": style.fill_transparency_percent,
        }
        if any(abs(actual.get(key, math.inf) - value) > 0.05 for key, value in expected_fields.items()):
            raise RuntimeError(f"Origin column gradient verification failed: {actual}, expected {expected_fields}")
        result.update({"secondary_html": highlight, "gradient": actual})
    return result


def verify_column_border_widths(
    op: Any, plots: Mapping[str, Any], expected_points: float, *, style: Any = None,
) -> dict[str, dict[str, float]]:
    """Measure native read units and restore the frozen point width.

    The documented -vw setter uses points. Old get documentation describes
    -pbw as pt*500, whereas 10.15 returns points. Calibrate on the owned plot
    instead of mistaking a 500-times-too-wide border for another unit encoding.
    """
    from ..scientific_visual import personal_bar_style

    if style is not None and personal_bar_style(style).get("bar_border") == "none":
        result = {}
        for index, (name, plot) in enumerate(plots.items()):
            color = _read_plot_option(op, plot, "-pbc", f"__column_none_{index}")
            if color != -4:
                raise RuntimeError(f"Origin column {name} retains a visible border.")
            result[name] = {"visible": False, "border_color_origin_code": color}
        return result
    if not math.isfinite(expected_points) or expected_points <= 0:
        raise ValueError("Column border width must be a positive point value")
    state: dict[str, dict[str, float]] = {}
    if not plots:
        return state
    head = next(iter(plots.values()))
    try:
        head.set_cmd("-vw 1")
        scale = _read_plot_option(op, head, "-pbw", "__osc_bar_reference_unit")
        if not any(math.isclose(scale, candidate, rel_tol=0, abs_tol=0.001) for candidate in (1, 500)):
            raise RuntimeError("Origin column border width has an unknown native unit")
    finally:
        head.set_cmd(f"-vw {expected_points:g}")
    for index, (name, plot) in enumerate(plots.items()):
        plot.set_cmd("-pbw 1")
        probe = _read_plot_option(op, plot, "-pbw", f"__osc_bar_setter_unit_{index}")
        if not any(math.isclose(probe, candidate, rel_tol=0, abs_tol=0.001) for candidate in (1, 500)):
            plot.set_cmd(f"-vw {expected_points:g}")
            raise RuntimeError("Origin column border setter has an unknown native unit")
        setter_units_per_pt = scale / probe
        plot.set_cmd(f"-pbw {expected_points * setter_units_per_pt:g}")
        actual = _read_plot_option(op, plot, "-pbw", f"__osc_bar_width_{index}")
        points = actual / scale
        if not math.isclose(points, expected_points, rel_tol=0, abs_tol=0.01):
            raise RuntimeError(
                f"Origin column border width verification failed: {name}={points:g} pt, "
                f"expected {expected_points:g} pt"
            )
        state[name] = {
            "native_value": actual, "native_units_per_pt": scale, "border_width_pt": points,
            "setter_units_per_pt": setter_units_per_pt,
        }
    return state


def verify_symbol_style(
    op: Any,
    plot: Any,
    *,
    expected_size_pt: float,
    expected_edge_percent: float,
    expected_symbol_kind: int | None = None,
    expected_symbol_interior: int | None = None,
    tolerance: float = 0.05,
) -> dict[str, float]:
    """Read back the requested scatter-symbol contract from the merged plot."""
    size = _read_plot_option(op, plot, "-z", "__osc_symbol_size")
    edge = _read_plot_option(op, plot, "-kh", "__osc_symbol_edge")
    kind = (
        _read_plot_option(op, plot, "-k", "__osc_symbol_kind")
        if expected_symbol_kind is not None
        else None
    )
    interior = (
        _read_plot_option(op, plot, "-kf", "__osc_symbol_interior")
        if expected_symbol_interior is not None
        else None
    )
    if abs(size - expected_size_pt) > tolerance:
        raise RuntimeError(
            f"Origin symbol size verification failed: {size:g} pt, expected {expected_size_pt:g} pt"
        )
    if abs(edge - expected_edge_percent) > tolerance:
        raise RuntimeError(
            "Origin symbol edge verification failed: "
            f"{edge:g}% of radius, expected {expected_edge_percent:g}%"
        )
    if kind is not None and abs(kind - float(expected_symbol_kind)) > tolerance:
        raise RuntimeError(
            f"Origin symbol kind verification failed: {kind:g}, "
            f"expected {expected_symbol_kind}"
        )
    if interior is not None and abs(interior - float(expected_symbol_interior)) > tolerance:
        raise RuntimeError(
            f"Origin symbol interior verification failed: {interior:g}, "
            f"expected {expected_symbol_interior}"
        )
    state = {
        "symbol_size_pt": size,
        "symbol_edge_percent_of_radius": edge,
    }
    if kind is not None:
        state["symbol_kind"] = kind
    if interior is not None:
        state["symbol_interior"] = interior
    return state


def read_page_geometry_cm(origin: Any, graph: Any) -> dict[str, Any]:
    """Use documented printer dots/resolution for physical page dimensions."""
    graph.activate()
    native = {
        name: _finite_float(origin.lt_float(f"page.{name}"), f"page.{name}")
        for name in ("width", "height", "resx", "resy")
    }
    for name, value in native.items():
        if value <= 0:
            raise RuntimeError(f"Origin page geometry requires positive page.{name}")
    width = _finite_float(native["width"] / native["resx"] * 2.54, "page.width_cm")
    height = _finite_float(native["height"] / native["resy"] * 2.54, "page.height_cm")
    bridge: dict[str, float | None] = {}
    for dimension, method in (("width", "GetWidth"), ("height", "GetHeight")):
        try:
            value = float(getattr(graph.obj, method)()) * 2.54
            bridge[dimension] = value if math.isfinite(value) else None
        except Exception:  # Optional COM bridge diagnostics, never the physical-size source.
            bridge[dimension] = None
    return {
        "width_cm": width, "height_cm": height,
        "page_geometry_readback_source": "labtalk_printer_dots",
        "page_width_dots": native["width"], "page_height_dots": native["height"],
        "page_resx": native["resx"], "page_resy": native["resy"],
        "page_bridge_width_cm": bridge["width"], "page_bridge_height_cm": bridge["height"],
        "page_bridge_geometry_consistent": all(
            bridge[name] is not None and abs(float(bridge[name]) - actual) <= PAGE_SIZE_TOLERANCE_CM
            for name, actual in (("width", width), ("height", height))
        ),
    }


def verify_page_and_layer(
    graph: Any,
    layer: Any,
    *,
    origin: Any,
    style: Any = FIXED_ORIGIN_STYLE,
    expected_layer: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    expected = {
        "left_percent": style.layer_left_percent,
        "top_percent": style.layer_top_percent,
        "width_percent": style.layer_width_percent,
        "height_percent": style.layer_height_percent,
        "factor": style.layer_factor,
    }
    if expected_layer is not None:
        expected.update(expected_layer)

    def read_layer() -> dict[str, Any]:
        return read_layer_geometry_percent(origin, layer)

    def read_page() -> dict[str, Any]:
        return read_page_geometry_cm(origin, graph)

    def restore_contract() -> None:
        graph.activate()
        for name in ("resx", "resy"):
            if _finite_float(origin.lt_float(f"page.{name}"), f"page.{name}") <= 0:
                raise RuntimeError(f"Origin page geometry requires positive page.{name}")
        if not graph.obj.LT_execute(
            "page.updatetoprinter=0;page.kar=0;"
            f"page.width=({style.page_width_cm:.17g}/2.54)*page.resx;"
            f"page.height=({style.page_height_cm:.17g}/2.54)*page.resy;doc -uw;"
        ):
            raise RuntimeError("Origin native page size assignment failed")
        layer.activate()
        layer.set_int("unit", 1)
        layer.set_float("left", expected["left_percent"])
        layer.set_float("top", expected["top_percent"])
        layer.set_float("width", expected["width_percent"])
        layer.set_float("height", expected["height_percent"])
        layer.set_int("fixed", style.layer_fixed)
        layer.set_float("factor", expected["factor"])
        # The property assignments are documented LabTalk and provide a
        # version-neutral write path in addition to the originpro setters.
        layer.obj.LT_execute(
            "layer.unit=1;"
            f"layer.left={expected['left_percent']:g};"
            f"layer.top={expected['top_percent']:g};"
            f"layer.width={expected['width_percent']:g};"
            f"layer.height={expected['height_percent']:g};"
            f"layer.fixed={int(style.layer_fixed)};"
            f"layer.factor={expected['factor']:g};"
            "doc -uw;"
        )

    layer_values: dict[str, Any] = {}
    for _attempt in range(3):
        try:
            page_cm = read_page()
            layer_values = read_layer()
        except RuntimeError:
            page_cm = {}
            layer_values = {}
        page_ok = bool(page_cm) and (
            abs(page_cm["width_cm"] - style.page_width_cm) <= PAGE_SIZE_TOLERANCE_CM
            and abs(page_cm["height_cm"] - style.page_height_cm) <= PAGE_SIZE_TOLERANCE_CM
        )
        layer_ok = bool(layer_values) and all(
            abs(float(layer_values[key]) - value) <= LAYER_GEOMETRY_TOLERANCE_PERCENT
            for key, value in expected.items()
        )
        if page_ok and layer_ok:
            return {**page_cm, **layer_values}
        restore_contract()

    try:
        page_cm = read_page()
    except RuntimeError as exc:
        raise RuntimeError(f"Origin page geometry verification failed: {exc}") from exc
    if abs(page_cm["width_cm"] - style.page_width_cm) > PAGE_SIZE_TOLERANCE_CM:
        raise OriginGeometryError(
            f"Origin page width verification failed: got {page_cm['width_cm']:.3f} cm, "
            f"expected {style.page_width_cm:.3f} cm",
            diagnostics={"geometry_check": "page_width_cm", "expected_value": style.page_width_cm,
                         "measured_value": page_cm["width_cm"], "tolerance_value": PAGE_SIZE_TOLERANCE_CM},
        )
    if abs(page_cm["height_cm"] - style.page_height_cm) > PAGE_SIZE_TOLERANCE_CM:
        raise OriginGeometryError(
            f"Origin page height verification failed: got {page_cm['height_cm']:.3f} cm, "
            f"expected {style.page_height_cm:.3f} cm",
            diagnostics={"geometry_check": "page_height_cm", "expected_value": style.page_height_cm,
                         "measured_value": page_cm["height_cm"], "tolerance_value": PAGE_SIZE_TOLERANCE_CM},
        )
    try:
        layer_values = read_layer()
    except RuntimeError as exc:
        raise RuntimeError(f"Origin layer geometry verification failed: {exc}") from exc
    for key, value in expected.items():
        actual = float(layer_values[key])
        if abs(actual - value) > LAYER_GEOMETRY_TOLERANCE_PERCENT:
            raise RuntimeError(
                f"Origin layer {key} verification failed: got {actual:.3f}, expected {value:.3f}"
            )
    return {**page_cm, **layer_values}
