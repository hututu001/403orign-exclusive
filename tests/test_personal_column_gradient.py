"""Bar overrides preserve palette/data and do not restyle other figure families."""
from __future__ import annotations

import sys
from dataclasses import asdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime/src"))

from origin_sciplot.scientific_visual import (  # noqa: E402
    PersonalProfileError,
    apply_personal_profile,
    column_highlight_color,
    normalize_personal_profile,
    personal_bar_style,
)
from origin_sciplot.scientific_workflow import prepare_scientific  # noqa: E402

PROFILE = {"id": "n4-f-u-v1.2", "overrides": {
    "bar_border": "none", "bar_fill": "two_color_center",
    "bar_fill_transparency_percent": 10,
}}


@pytest.mark.parametrize("template", ["bar", "horizontal_bar", "stacked_bar", "percent_stacked_bar"])
def test_column_profile_keeps_data_and_template_palette(template):
    source = ROOT / "runtime/templates" / template / "example_standard.csv"
    before = prepare_scientific(source, template)
    after, report = apply_personal_profile(before, PROFILE)
    old, new = before.plot_spec.display_plan.figure_style, after.plot_spec.display_plan.figure_style
    assert new.palette_name == old.palette_name
    assert new.fill_transparency_percent == 10
    assert after.source_sha256 == before.source_sha256
    assert after.plot_spec.series == before.plot_spec.series
    assert after.plot_spec.axis_plan == before.plot_spec.axis_plan
    assert set(report["applied_fields"]) == set(PROFILE["overrides"])
    assert personal_bar_style(new) == PROFILE["overrides"]


@pytest.mark.parametrize("template", ["trend", "scatter", "heatmap"])
def test_column_options_do_not_change_other_template_styles(template):
    before = prepare_scientific(ROOT / "runtime/templates" / template / "example_standard.csv", template)
    after, report = apply_personal_profile(before, PROFILE)
    a, b = (
        asdict(before.plot_spec.display_plan.figure_style),
        asdict(after.plot_spec.display_plan.figure_style),
    )
    a.pop("personal_profile")
    b.pop("personal_profile")
    assert a == b
    assert report["applied_fields"] == []
    assert set(report["not_applicable_fields"]) == set(PROFILE["overrides"])
    assert personal_bar_style(after.plot_spec.display_plan.figure_style) == {}


@pytest.mark.parametrize("key,value", [
    ("bar_border", "black"), ("bar_fill", "rainbow"),
    ("bar_fill_transparency_percent", -1), ("bar_fill_transparency_percent", 101),
    ("bar_fill_transparency_percent", True),
])
def test_invalid_column_profile_is_rejected(key, value):
    with pytest.raises(PersonalProfileError):
        normalize_personal_profile({"id": "bad", "overrides": {key: value}})


def test_highlight_uses_template_color_with_seventy_percent_white():
    assert column_highlight_color("#484878") == "#C8C8D6"
    assert column_highlight_color("#FB8315") == "#FEDAB9"


@pytest.mark.parametrize("template", ["bar", "horizontal_bar", "stacked_bar", "percent_stacked_bar"])
def test_preview_has_dark_edges_bright_center_and_keeps_bar_heights(template):
    import numpy as np
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from origin_sciplot.scientific_preview import _build_scientific_preview_figure

    baseline = prepare_scientific(ROOT / "runtime/templates" / template / "example_standard.csv", template)
    updated, _ = apply_personal_profile(baseline, PROFILE)
    original, figure = _build_scientific_preview_figure(baseline), _build_scientific_preview_figure(updated)
    try:
        FigureCanvasAgg(figure).draw()
        before, after = original.axes[0], figure.axes[0]
        assert [(p.get_x(), p.get_y(), p.get_width(), p.get_height()) for p in before.patches] == [
            (p.get_x(), p.get_y(), p.get_width(), p.get_height()) for p in after.patches
        ]
        assert after.images
        for image in after.images:
            rgba = np.asarray(image.get_array())
            np.testing.assert_allclose(rgba[0, 0], rgba[0, -1])
            assert np.all(rgba[0, rgba.shape[1] // 2, :3] > rgba[0, 0, :3])
            np.testing.assert_allclose(rgba[..., 3], 0.9)
        assert all(p.get_edgecolor()[3] == 0 for p in after.patches)
    finally:
        original.clear()
        figure.clear()


@pytest.mark.parametrize("changed", [
    None, "primary_color", "secondary_color", "shading_mode", "direction", "pattern",
    "border_color", "transparency_percent", "secondary_transparency_auto", "secondary_transparency_percent",
])
def test_native_gradient_verifier_rejects_each_independent_mismatch(monkeypatch, changed):
    from origin_sciplot.origin_backend import verify_utils as verify
    from test_column_style_readback import NativeColumn

    preparation = prepare_scientific(ROOT / "runtime/templates/bar/example_standard.csv", "bar")
    updated, _ = apply_personal_profile(preparation, PROFILE)
    style = updated.plot_spec.display_plan.figure_style
    plot = NativeColumn()
    color = "#484878"
    code, highlight = plot.ocolor(color), plot.ocolor(column_highlight_color(color))
    plot.options.update({"-pfb": code, "-pbc": -4})
    actual = {
        "primary_color": code, "secondary_color": highlight, "shading_mode": 2,
        "direction": 9, "pattern": 0, "border_color": -4,
        "transparency_percent": 10, "secondary_transparency_auto": 1,
        "secondary_transparency_percent": 10,
    }
    if changed:
        actual[changed] -= 1
    monkeypatch.setattr(verify, "read_column_fill", lambda _plot: actual)
    if changed:
        with pytest.raises(RuntimeError, match="gradient verification failed"):
            verify.verify_column_colors(plot, plot, color, variable_name="__gradient", style=style)
    else:
        result = verify.verify_column_colors(plot, plot, color, variable_name="__gradient", style=style)
        assert result["gradient"] == actual
        verify.verify_column_border_widths(plot, {"Series": plot}, 1.4, style=style)
        assert plot.commands == []  # A read-only no-border check does not recalibrate hidden widths.
