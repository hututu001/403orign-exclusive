from __future__ import annotations

import ast
import importlib.util
import json
import sys
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SRC = ROOT / "runtime" / "src"
RUNNER_PATH = ROOT / "runtime" / "templates" / "xps_c1s_fit" / "runner.py"
sys.path.insert(0, str(RUNTIME_SRC))

from origin_sciplot.scientific_visual import apply_personal_profile  # noqa: E402
from origin_sciplot.xps_visual_style import apply_xps_visual_style  # noqa: E402
from origin_sciplot.xps_workflow import (  # noqa: E402
    load_xps_frame,
    prepare_xps,
    replace_xps_visual_contract,
)


def _load_runner(path: Path = RUNNER_PATH) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"{path.parent.name}_style_runner", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUNNER = _load_runner()
SOURCE = ROOT / "runtime" / "templates" / "xps_c1s_fit" / "example_standard.csv"
XPS_TEMPLATES = ("xps_c1s_fit", "xps_adaptive")
PERSONAL_PROFILE = {
    "id": "n4-f-u-v1.2",
    "overrides": {
        "page_width_cm": 28.8544, "page_height_cm": 20.14728,
        "font_family": "Arial", "axis_title_size_pt": 28,
        "tick_label_size_pt": 26, "legend_size_pt": 24,
        "annotation_size_pt": 24, "bold": True, "png_dpi": 600,
    },
}


class _LayerObject:
    def __init__(self) -> None:
        self.commands: list[str] = []

    def LT_execute(self, command: str) -> bool:  # noqa: N802
        self.commands.append(command)
        return True


class _AxisLayer:
    def __init__(self) -> None:
        self.ints: dict[str, int] = {}
        self.floats: dict[str, float] = {}
        self.obj = _LayerObject()

    def set_int(self, name: str, value: int) -> None:
        self.ints[name] = int(value)

    def set_float(self, name: str, value: float) -> None:
        self.floats[name] = float(value)


class _Legend:
    def __init__(self) -> None:
        self.values: dict[str, float | int] = {
            "show": 1,
            "showframe": 0,
            "attach": 0,
            "left": 100.0,
            "top": 80.0,
            "width": 100.0,
            "height": 240.0,
        }
        self.text = ""

    def set_int(self, name: str, value: int) -> None:
        self.values[name] = int(value)

    def set_float(self, name: str, value: float) -> None:
        self.values[name] = float(value)

    def get_int(self, name: str) -> int:
        return int(self.values[name])

    def get_float(self, name: str) -> float:
        return float(self.values[name])

    def remove(self) -> None:
        self.values["show"] = 0


class _LegendLayer:
    def __init__(self) -> None:
        self.legend = _Legend()
        self.obj = _LayerObject()

    def label(self, _name: str) -> _Legend:
        return self.legend


class _LegendOrigin:
    def __init__(self) -> None:
        self.commands: list[str] = []

    def lt_exec(self, command: str) -> bool:
        self.commands.append(command)
        return True

    def lt_float(self, expression: str) -> float:
        return {"page.width": 1000.0, "page.height": 800.0}[expression]


def test_fixed_preparation_keeps_raw_default_and_accepts_exact_series_colors() -> None:
    preparation = prepare_xps(SOURCE)
    assert preparation.visual_contract.raw_color == "#808080"

    styled = apply_xps_visual_style(
        preparation,
        {
            "series_colors": {
                "raw": "#123456",
                "component": "#ABCDEF",
                "Peak_CC": "#0A6F8F",
            },
            "line_width_pt": 3.25,
            "fill_transparency_percent": 37.5,
            "page_size_cm": {"width": 18.0, "height": 18.0},
        },
        source="explicit_user",
    ).preparation

    assert RUNNER._series_color(styled, "Raw", "raw") == "#123456"  # noqa: SLF001
    assert (
        RUNNER._series_color(styled, "Peak_CC", "component", 0)  # noqa: SLF001
        == "#0A6F8F"
    )
    assert (
        RUNNER._series_color(styled, "Peak_CO", "component", 1)  # noqa: SLF001
        == "#ABCDEF"
    )
    assert (
        RUNNER._component_fill_color(styled, "Peak_CC", 0)  # noqa: SLF001
        == "#0A6F8F"
    )
    style = styled.visual_contract.figure_style
    assert style.plot_line_width_pt == 3.25
    assert style.fill_transparency_percent == 37.5
    assert (style.page_width_cm, style.page_height_cm) == (18.0, 18.0)


def test_helper_columns_are_workbook_only_and_plot_x_remains_negated() -> None:
    preparation = prepare_xps(SOURCE)
    frame = pd.read_csv(SOURCE)
    original = frame.copy(deep=True)

    prepared = RUNNER._prepare_frame(frame, preparation)  # noqa: SLF001

    pd.testing.assert_frame_equal(frame, original)
    assert prepared["PlotX"].tolist() == pytest.approx(
        (-prepared["BindingEnergy"]).tolist()
    )
    for component in preparation.roles.components:
        assert f"{component}{RUNNER.FILL_TOP_SUFFIX}" in prepared.columns
        assert f"{component}{RUNNER.FILL_BASE_SUFFIX}" in prepared.columns
        assert prepared[f"{component}{RUNNER.FILL_TOP_SUFFIX}"].tolist() == pytest.approx(
            (prepared["Background"] + prepared[component]).tolist()
        )


def test_fixed_axis_contract_keeps_verified_negated_binding_energy_route() -> None:
    layer = _AxisLayer()

    RUNNER._apply_x_axis_contract(layer, -292.0)  # noqa: SLF001
    RUNNER._apply_y_axis_contract(layer)  # noqa: SLF001

    assert layer.floats["x.label.divideBy"] == -1.0
    assert layer.floats["x.firstTick"] == -292.0
    assert layer.ints["x.reverse"] == 0
    assert layer.ints["x.label.align"] == 1
    assert layer.ints["y.ticks"] == 0
    assert layer.ints["y.minorTicks"] == 0
    assert layer.ints["y.showLabels"] == 0
    assert layer.ints["x2.ticks"] == 0
    assert layer.ints["y2.ticks"] == 0
    assert "x2.showLabels" not in layer.ints
    assert "y2.showLabels" not in layer.ints


def test_hidden_legend_does_not_require_a_text_object_for_verification() -> None:
    preparation = prepare_xps(SOURCE)
    visual = replace(
        preparation.visual_contract,
        legend_visible=False,
        legend_position="none",
    )
    preparation = replace_xps_visual_contract(preparation, visual)
    layer = _LegendLayer()

    legend, state = RUNNER._style_legend(  # noqa: SLF001
        _LegendOrigin(),
        layer,
        [("raw", "#808080", "Raw")],
        preparation,
    )

    assert legend is None
    assert state == {
        "visible": False,
        "visible_readback": False,
        "position": "none",
        "showframe": None,
    }
    assert layer.legend.get_int("show") == 0


def test_outside_legend_position_frame_and_dynamic_width_are_read_back() -> None:
    preparation = apply_xps_visual_style(
        prepare_xps(SOURCE),
        {
            "legend_position": "outside_right",
            "legend_frame": True,
            "line_width_pt": 2.75,
        },
        source="explicit_user",
    ).preparation
    layer = _LegendLayer()

    legend, state = RUNNER._style_legend(  # noqa: SLF001
        _LegendOrigin(),
        layer,
        [("raw", "#123456", "Raw"), ("envelope", "#654321", "Envelope")],
        preparation,
    )

    assert legend is layer.legend
    assert state["visible_readback"] is True
    assert state["position"] == "outside_right"
    assert state["showframe"] == 1
    assert state["inside_page"] is True
    style = preparation.visual_contract.figure_style
    layer_right = 1000.0 * (
        style.layer_left_percent + style.layer_width_percent
    ) / 100.0
    assert state["left"] >= layer_right
    assert state["attach"] == 1
    assert "LineWidth:2.75" in layer.legend.text
    assert "EdgeColor:#123456" in layer.legend.text


def test_runner_keeps_independent_pfm3_fill_and_full_style_readback() -> None:
    text = RUNNER_PATH.read_text(encoding="utf-8")

    assert "style = visual.figure_style" in text
    assert "fill_plot.transparency = style.fill_transparency_percent" in text
    assert "fill_plot.set_fill_area(" in text
    assert 'fill_plot.set_cmd("-pfm 3")' in text
    assert "four-colour" in text
    assert "visible_series_colors" in text
    assert "fill_transparency_percent_expected" in text
    assert '"legend": legend_state' in text
    assert '"xps_visual_contract": visual.to_dict()' in text
    assert "labels = {\"x_title\": x_title, \"y_title\": y_title}" in text


@pytest.mark.parametrize("template_id", XPS_TEMPLATES)
@pytest.mark.parametrize("frame", (False, True))
@pytest.mark.parametrize("profile_enabled", (False, True))
def test_inside_legend_reuses_profile_page_placement_and_preserves_frame(
    template_id: str, frame: bool, profile_enabled: bool, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from origin_sciplot.origin_backend import scientific_renderer

    template = ROOT / "runtime" / "templates" / template_id
    runner = _load_runner(template / "runner.py")
    preparation = apply_xps_visual_style(
        prepare_xps(template / "example_standard.csv"),
        {"legend_position": "inside", "legend_frame": frame},
        source="explicit_user",
    ).preparation
    if profile_enabled:
        preparation, _ = apply_personal_profile(preparation, PERSONAL_PROFILE)
    layer, op = _LegendLayer(), _LegendOrigin()
    if profile_enabled:
        # Simulate the stale template coordinates from the live failure.
        layer.legend.values.update(left=1200.0, top=-50.0)
    old_position = (layer.legend.get_float("left"), layer.legend.get_float("top"))
    calls = []
    position = scientific_renderer._position_publication_legend

    def track_position(*args, **kwargs):
        calls.append(kwargs)
        return position(*args, **kwargs)

    monkeypatch.setattr(scientific_renderer, "_position_publication_legend", track_position)
    result = runner._style_legend(op, layer, [("raw", "#123456", "Raw")], preparation)
    state = result[1] if isinstance(result, tuple) else result
    assert calls == ([{"expected_frame": int(frame)}] if profile_enabled else [])
    assert state["showframe"] == int(frame)
    assert layer.legend.get_int("showframe") == int(frame)
    assert state["inside_page"] is True
    if profile_enabled:
        assert state["attach"] == 1
        assert (state["left"], state["top"]) != old_position
        assert layer.legend.get_float("fsize") == 24
    else:
        assert state["attach"] == 0
        assert (state["left"], state["top"]) == old_position


@pytest.mark.parametrize("template_id", XPS_TEMPLATES)
@pytest.mark.parametrize("position", ("none", "outside_right"))
def test_personal_profile_retains_hidden_and_outside_legend_routes(
    template_id: str, position: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from origin_sciplot.origin_backend import scientific_renderer

    template = ROOT / "runtime" / "templates" / template_id
    runner = _load_runner(template / "runner.py")
    preparation = apply_xps_visual_style(
        prepare_xps(template / "example_standard.csv"),
        {"legend_position": position, "legend_frame": True},
        source="explicit_user",
    ).preparation
    preparation, _ = apply_personal_profile(preparation, PERSONAL_PROFILE)
    monkeypatch.setattr(
        scientific_renderer, "_position_publication_legend",
        lambda *_args, **_kwargs: pytest.fail("Only an inside personal legend needs shared placement"),
    )
    layer, op = _LegendLayer(), _LegendOrigin()
    result = runner._style_legend(op, layer, [("raw", "#123456", "Raw")], preparation)
    state = result[1] if isinstance(result, tuple) else result
    assert state["position"] == position
    if position == "none":
        assert state["visible_readback"] is False
    else:
        style = preparation.visual_contract.figure_style
        layer_right = 1000 * (style.layer_left_percent + style.layer_width_percent) / 100
        assert state["left"] >= layer_right
        assert state["inside_page"] is True
        assert state["showframe"] == 1


@pytest.mark.parametrize("template_id", XPS_TEMPLATES)
def test_personal_typography_runs_after_axis_formatter_before_text_verification(template_id: str) -> None:
    path = ROOT / "runtime" / "templates" / template_id / "runner.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    build = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_build_origin_graph"
    )
    calls = [node for node in ast.walk(build) if isinstance(node, ast.Call)]

    def lines(name: str) -> list[int]:
        return sorted(node.lineno for node in calls if (
            isinstance(node.func, ast.Name) and node.func.id == name
        ) or (isinstance(node.func, ast.Attribute) and node.func.attr == name))

    typography = lines("apply_personal_typography")
    assert len(typography) == 1  # Apply before verification; do not mutate again after it.
    assert max(lines("_apply_clean_x_axis_format")) < typography[0]
    assert typography[0] < min(lines("_position_axis_titles"))
    assert typography[0] < min(lines("verify_text_sizes") + lines("verify_text_fonts"))
    assert max(lines("verify_text_fonts")) < min(lines("save"))
    gated = [node for node in ast.walk(build) if isinstance(node, ast.IfExp)
             and isinstance(node.body, ast.Call)
             and isinstance(node.body.func, ast.Name)
             and node.body.func.id == "apply_personal_typography"]
    assert len(gated) == 1
    assert ast.unparse(gated[0].test) == "getattr(style, 'personal_profile', None)"
    assert isinstance(gated[0].orelse, ast.Constant) and gated[0].orelse.value is None


@pytest.mark.parametrize("template_id", XPS_TEMPLATES)
@pytest.mark.parametrize("profile_enabled", (False, True))
def test_run_exports_real_xps_preparation_style_and_persists_png_readback(
    template_id: str, profile_enabled: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from origin_sciplot.logging_utils import RunLogger
    from origin_sciplot.output_manager import create_run_output
    from origin_sciplot.template_registry import TemplateRegistry

    manifest = TemplateRegistry(ROOT / "runtime" / "templates").get(template_id)
    runner = _load_runner(manifest.runner_path)
    preparation = prepare_xps(manifest.example_path)
    if profile_enabled:
        preparation, _ = apply_personal_profile(preparation, PERSONAL_PROFILE)
    # Keep the actual contract shape: visual_contract belongs to XpsPreparation,
    # not its plot_spec. A nested fake would hide the post-save export failure.
    assert not hasattr(preparation.plot_spec, "visual_contract")
    style = preparation.visual_contract.figure_style
    frame = load_xps_frame(manifest.example_path, preparation)
    output = create_run_output(manifest.example_path, manifest, tmp_path / "run")
    op, graph = object(), object()
    events = []
    png_readback = {"passed": True, "dpi": 600, "width": 6816, "height": 4759}
    graph_report = {"native_graph_built": True}
    if profile_enabled:
        graph_report["personal_profile"] = {"passed": True}

    @contextmanager
    def session(*, keep_open):
        assert keep_open is False
        yield SimpleNamespace(
            op=op,
            environment=SimpleNamespace(
                origin_version="test-only", to_dict=lambda: {"origin_version": "test-only"}
            ),
        )

    def build(actual_op, actual_frame, actual_output, actual_preparation):
        assert actual_op is op
        assert actual_frame is frame
        assert actual_output is output
        assert actual_preparation is preparation
        events.append("build")
        return graph, graph_report

    def export(actual_op, actual_graph, png, pdf, tif, **kwargs):
        assert actual_op is op and actual_graph is graph
        assert (png, pdf, tif) == (output.result_png, output.result_pdf, output.result_tif)
        assert kwargs == ({"style": style} if profile_enabled else {})
        if profile_enabled:
            assert kwargs["style"] is style
        events.append("export")
        return {"png": str(png), "pdf": str(pdf), "tif": str(tif)}

    def verify_png(png, actual_style):
        assert profile_enabled
        assert events == ["build", "export"]
        assert png == output.result_png and actual_style is style
        events.append("png_readback")
        return png_readback

    monkeypatch.setattr(runner, "OriginSession", session)
    monkeypatch.setattr(runner, "_build_origin_graph", build)
    monkeypatch.setattr(runner, "export_graph", export)
    monkeypatch.setattr(runner, "verify_png_export", verify_png)
    result = runner.run(
        manifest, frame, output, RunLogger(output.run_log),
        keep_origin_open=False, preparation=preparation,
    )
    # The real preparation resolution and JSON writers remain in the run path.
    saved = json.loads(output.origin_verify_report.read_text(encoding="utf-8"))
    assert saved == result["verify"]
    assert saved["native_graph_built"] is True
    assert saved["exports"]["png"] == result["png"] == str(output.result_png)
    assert json.loads(output.environment_report.read_text(encoding="utf-8"))["template_id"] == template_id
    if profile_enabled:
        assert events == ["build", "export", "png_readback"]
        assert saved["personal_profile"] == {"passed": True, "png": png_readback}
    else:
        assert events == ["build", "export"]
        assert "personal_profile" not in saved
