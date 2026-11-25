from __future__ import annotations

import re
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime/src"))

from origin_sciplot.origin_backend import scientific_renderer as renderer  # noqa: E402
from origin_sciplot.origin_backend.safe_errors import OriginDrawError  # noqa: E402
from origin_sciplot.origin_backend.verify_utils import NativePlotReference  # noqa: E402
from origin_sciplot.scientific_visual import resolve_adaptive_style  # noqa: E402


class NativeLineError:
    def __init__(self, failure=None):
        self.failure = failure
        self.count = 2  # A preceding value/error series already owns slots 1 and 2.
        self.plot_id = 202
        self.commands = []
        self.values = {}
        self.layer = SimpleNamespace(
            obj=SimpleNamespace(LT_execute=self.execute), activate=lambda: None,
            lt_range=lambda: "[Graph1]1",
            plot_list=lambda: [None] * self.count,
            add_plot=lambda *args, **kwargs: pytest.fail("AddPlotFromString route must not be used"),
        )
        names = {"Time (h)": 1, "Treatment mean (a.u.)": 4, "Treatment SD": 5}
        self.sheet = SimpleNamespace(
            lt_col_index=lambda name: 0 if failure == "missing_column" else names[name],
            lt_range=lambda _flag: "[Book1]1",
        )
        self.op = SimpleNamespace(
            lt_exec=self.plotxy, lt_float=self.values.__getitem__,
            get_lt_str=self.values.__getitem__, ocolor=lambda color: 12345,
        )

    def plotxy(self, command):
        self.commands.append(command)
        self.plot_id = int(re.search(r"plot:=([0-9]+)", command).group(1))
        if self.failure == "command":
            return False
        self.count += 1 if self.failure == "plot_count" or "!(1,4) " in command else 2
        error_name = "Book1_wrong_SD" if self.failure == "error_binding" else "Book1_5"
        self.layer.obj.DataPlots = [None, None, SimpleNamespace(GetDatasetName=lambda: "Book1_4")]
        if self.count == 4:
            self.layer.obj.DataPlots.append(SimpleNamespace(GetDatasetName=lambda: error_name))
        return True

    def execute(self, command):
        self.commands.append(command)
        if "get __xy_plot -pt" in command:
            slot = int(re.search(r"!([0-9]+);", command).group(1))
            self.values["__xy_type"] = self.plot_id if slot == 3 else 231
            if self.failure == "plot_type":
                self.values["__xy_type"] = 202
        if "range __xy_expected=" in command:
            column = int(re.search(r"!col\(([0-9]+)\)", command).group(1))
            self.values["__xy_actual_name"] = f"Book1_{column}"
            self.values["__xy_expected_name"] = f"Book1_{column}"
            self.values["__xy_actual_count"] = 6
            self.values["__xy_expected_count"] = 6
            if self.failure == "xy_count" and column == 4:
                self.values["__xy_actual_count"] = 5
            if self.failure == "xy_binding" and column == 4:
                self.values["__xy_actual_name"] = "Book1_wrong_Y"
            if self.failure == "error_empty" and column == 5:
                self.values["__xy_expected_count"] = 0
            if self.failure == "error_nonfinite" and column == 5:
                self.values["__xy_expected_count"] = float("nan")
        return True


def _series():
    return renderer.OriginSeriesPlan(
        source_column="Treatment mean (a.u.)", plot_column="Treatment mean (a.u.)",
        x_column="Time (h)", error_column="Treatment SD", label="Treatment",
        axis="left", plot_type="y", color="#247B8B", bar_gap_percent=None,
        marker_size_pt=4.0,
    )


def test_native_line_error_uses_numeric_xy_error_range_and_preserves_original_style():
    native = NativeLineError()
    style = resolve_adaptive_style(
        template_id="line_error", plot_kind="line_error", row_count=6, series_count=2
    )
    main, errors = renderer._add_plot(
        native.op, native.layer, native.sheet, _series(), "Time (h)", style,
        native_xy_series=True,
    )
    assert native.commands[0] == "plotxy iy:=[Book1]1!(1,4,5) plot:=202 ogl:=[Graph1]1!;"
    assert isinstance(main, NativePlotReference)
    assert main.lt_range() == "[Graph1]1!3"
    assert [plot.lt_range() for plot in errors] == ["[Graph1]1!4"]
    commands = "\n".join(native.commands)
    assert "range -wx __xy_actual=[Graph1]1!3" in commands
    assert "range -wy __xy_actual=[Graph1]1!4" not in commands
    assert "range __xy_expected=[Book1]1!col(5);" in commands
    assert "set rr -kf 1;" in commands
    assert "set rr -k 2;" in commands
    assert "set rr -z 4;" in commands
    assert "set rr -kh 50;" in commands
    assert f"set rr -w {renderer.pt_to_origin_width_units(style.error_bar_width_pt)};" in commands
    assert "set rr -c 12345;" in commands
    assert not any("Treatment" in command for command in native.commands)


@pytest.mark.parametrize("plot_type", ("y", "c"))
@pytest.mark.parametrize("failure", (
    "missing_column", "command", "plot_count", "plot_type", "error_binding", "error_empty",
    "error_nonfinite", "xy_count", "xy_binding",
))
def test_native_line_error_rejects_missing_or_misbound_error_plot(failure, plot_type):
    native = NativeLineError(failure)
    with pytest.raises(OriginDrawError):
        renderer._add_native_xy_series(native.op, native.layer, native.sheet,
                                       replace(_series(), plot_type=plot_type), "Time (h)")


def test_series_without_an_error_column_keeps_no_error_inside_line_error_template():
    native = NativeLineError()
    series = replace(_series(), error_column=None)
    main, errors = renderer._add_native_xy_series(native.op, native.layer, native.sheet, series, "Time (h)")
    assert main.lt_range() == "[Graph1]1!3"
    assert errors == []
    assert native.commands[0] == "plotxy iy:=[Book1]1!(1,4) plot:=202 ogl:=[Graph1]1!;"


@pytest.mark.parametrize("has_error", (False, True))
def test_native_column_keeps_fill_border_gap_and_optional_error_binding(has_error):
    native = NativeLineError()
    style = resolve_adaptive_style(template_id="bar", plot_kind="bar_error", row_count=6, series_count=2)
    series = replace(_series(), plot_type="c", bar_gap_percent=64,
                     error_column="Treatment SD" if has_error else None)
    main, errors = renderer._add_plot(
        native.op, native.layer, native.sheet, series, "Time (h)", style, native_xy_series=True,
    )
    columns = "1,4,5" if has_error else "1,4"
    assert native.commands[0] == f"plotxy iy:=[Book1]1!({columns}) plot:=203 ogl:=[Graph1]1!;"
    assert main.native_index == 3
    assert len(errors) == int(has_error)
    commands = "\n".join(native.commands)
    assert "range -wx __xy_actual=[Graph1]1!3" in commands
    assert "range -wy __xy_actual=[Graph1]1!3" in commands
    assert "range -wy __xy_actual=[Graph1]1!4" not in commands
    assert ("range __xy_expected=[Book1]1!col(5);" in commands) is has_error
    for command in ("-pfb 12345", "-pbc 12345", f"-vw {style.bar_border_width_pt:g}", "-vg 64"):
        assert f"set rr {command};" in commands
    assert "set rr -kf" not in commands
    assert "set rr -z" not in commands


def test_native_column_transparency_uses_owned_slot_without_cached_proxy_index():
    native = NativeLineError()
    style = resolve_adaptive_style(template_id="bar", plot_kind="bar_error", row_count=6, series_count=2)
    native.layer.plot_list = lambda: pytest.fail("No cached plot index should be read")
    values = {}
    native.layer.set_float, native.layer.get_float = values.__setitem__, values.__getitem__
    series = replace(_series(), plot_type="c")
    main = NativePlotReference("[Graph1]1!3", native.layer.obj)
    result = renderer._set_bar_transparency(
        native.layer, SimpleNamespace(series=(series,)), {series.label: main}, style,
    )
    assert values == {"plot3.transparency": style.fill_transparency_percent}
    assert result == {series.label: style.fill_transparency_percent}
