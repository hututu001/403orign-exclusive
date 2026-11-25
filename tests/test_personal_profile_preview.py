from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.text import Text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime/src"))

from origin_sciplot.scientific_preview import _build_scientific_preview_figure  # noqa: E402
from origin_sciplot.scientific_visual import apply_personal_profile  # noqa: E402
from origin_sciplot.scientific_workflow import prepare_scientific  # noqa: E402
from origin_sciplot.xps_preview import _build_xps_preview_figure  # noqa: E402
from origin_sciplot.xps_workflow import prepare_xps  # noqa: E402


def _prepare_and_build(template_id):
    source = ROOT / "runtime/templates" / template_id / "example_standard.csv"
    if template_id.startswith("xps_"):
        return prepare_xps(source), _build_xps_preview_figure
    return prepare_scientific(source, template_id), _build_scientific_preview_figure


@pytest.mark.parametrize("template_id", (
    "trend", "event_raster", "signal_stack", "heatmap", "xps_adaptive", "xps_c1s_fit",
))
@pytest.mark.parametrize("overrides", (
    {"font_family": "Times New Roman"}, {"bold": False}, {"bold": True}, {"png_dpi": 600},
), ids=("family-only", "bold-false", "bold-true", "dpi-only"))
def test_preview_profile_fonts_preserve_other_text_and_plot_properties(template_id, overrides):
    preparation, build = _prepare_and_build(template_id)
    updated, _ = apply_personal_profile(preparation, {"id": "preview", "overrides": overrides})
    baseline, figure = build(preparation), build(updated)
    try:
        # Inspect after rendering as well, so lazily created ticks are covered.
        FigureCanvasAgg(baseline).draw()
        FigureCanvasAgg(figure).draw()
        old_texts, texts = baseline.findobj(match=Text), figure.findobj(match=Text)
        assert texts
        assert len(texts) == len(old_texts)
        for old, text in zip(old_texts, texts, strict=True):
            assert text.get_text() == old.get_text()
            assert text.get_fontsize() == old.get_fontsize()
            assert text.get_color() == old.get_color()
            assert text.get_visible() == old.get_visible()
            assert text.get_fontfamily() == (
                [overrides["font_family"]] if "font_family" in overrides else old.get_fontfamily()
            )
            assert text.get_fontweight() == (
                ("bold" if overrides["bold"] else "normal") if "bold" in overrides
                else old.get_fontweight()
            )
        np.testing.assert_array_equal(figure.get_size_inches(), baseline.get_size_inches())
        assert len(figure.axes) == len(baseline.axes)
        for old_axis, axis in zip(baseline.axes, figure.axes, strict=True):
            assert axis.get_xlim() == old_axis.get_xlim()
            assert axis.get_ylim() == old_axis.get_ylim()
            assert len(axis.lines) == len(old_axis.lines)
            for old, line in zip(old_axis.lines, axis.lines, strict=True):
                np.testing.assert_array_equal(line.get_xdata(), old.get_xdata())
                np.testing.assert_array_equal(line.get_ydata(), old.get_ydata())
                for field in ("color", "linewidth", "linestyle", "marker", "markersize",
                              "markeredgecolor", "markerfacecolor", "markeredgewidth"):
                    assert getattr(line, f"get_{field}")() == getattr(old, f"get_{field}")()
            assert len(axis.collections) == len(old_axis.collections)
            for old, collection in zip(old_axis.collections, axis.collections, strict=True):
                np.testing.assert_array_equal(collection.get_offsets(), old.get_offsets())
                np.testing.assert_array_equal(collection.get_facecolors(), old.get_facecolors())
                np.testing.assert_array_equal(collection.get_edgecolors(), old.get_edgecolors())
    finally:
        baseline.clear()
        figure.clear()


def test_bar_profile_preview_uses_native_page_size_and_keeps_all_categories():
    preparation, build = _prepare_and_build("bar")
    updated, _ = apply_personal_profile(preparation, {"id": "large-bar", "overrides": {
        "page_width_cm": 28.8544, "page_height_cm": 20.14728,
        "tick_label_size_pt": 26, "axis_title_size_pt": 28,
        "legend_size_pt": 24, "font_family": "Arial", "bold": True,
    }})
    figure = build(updated)
    try:
        FigureCanvasAgg(figure).draw()
        axis = figure.axes[0]
        ticks = axis.get_xticklabels()
        assert [tick.get_text() for tick in ticks] == [f"Group {index}" for index in range(1, 6)]
        assert all(tick.get_rotation() == 0 for tick in ticks)
        assert all(tick.get_fontweight() == "bold" for tick in ticks)
        native = updated.plot_spec.display_plan.figure_style
        original = preparation.plot_spec.display_plan.figure_style
        assert native.layer_height_percent == original.layer_height_percent
        assert native.layer_width_percent == original.layer_width_percent
        assert all(
            tick.get_fontsize() == pytest.approx(26 * 7.2 / (native.page_width_cm / 2.54)) for tick in ticks
        )
        assert axis.get_position().height == pytest.approx(native.layer_height_percent / 100)
        assert figure.get_size_inches()[1] == pytest.approx(
            7.2 * native.page_height_cm / native.page_width_cm
        )
    finally:
        figure.clear()


@pytest.mark.parametrize("template_id", ("bar", "line_error"))
def test_inside_profile_preview_removes_only_external_column(template_id):
    preparation, build = _prepare_and_build(template_id)
    updated, _ = apply_personal_profile(
        preparation, {"id": "inside", "overrides": {"legend_position": "inside"}}
    )
    figure = build(updated)
    try:
        FigureCanvasAgg(figure).draw()
        axis = figure.axes[0]
        legend = axis.get_legend()
        assert legend is not None
        bounds = legend.get_window_extent().transformed(axis.transAxes.inverted())
        assert bounds.x0 >= 0 and bounds.x1 <= 1
        assert bounds.y0 >= 0 and bounds.y1 <= 1
        assert axis.get_position().width == pytest.approx(
            updated.plot_spec.display_plan.figure_style.layer_width_percent / 100
        )
        assert not updated.plot_spec.display_plan.figure_style.profile_name.endswith("-external-legend")
    finally:
        figure.clear()
