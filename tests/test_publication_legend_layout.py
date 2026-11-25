from __future__ import annotations

import sys
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime/src"))

from origin_sciplot.origin_backend.safe_errors import OriginDrawError  # noqa: E402
from origin_sciplot.origin_backend.scientific_renderer import (  # noqa: E402
    _position_publication_legend,
    _position_rotated_category_title,
)
from origin_sciplot.scientific_visual import resolve_adaptive_style  # noqa: E402


@pytest.mark.parametrize(
    "kind", ["line", "stacked_line", "line_error", "scatter", "diagnostic_curve", "decision_curve"]
)
def test_comparison_legends_have_a_reserved_physical_column(kind):
    style = resolve_adaptive_style(
        template_id="test", plot_kind=kind, row_count=100, series_count=3, max_label_length=20
    )
    right_cm = style.page_width_cm * (100 - style.layer_left_percent - style.layer_width_percent) / 100
    assert right_cm >= 6.4
    assert style.profile_name.endswith("-external-legend")
    assert style.legend_size_pt >= 17
    assert style.x_title_upshift_page_percent == 0


def test_legend_reservation_adapts_to_long_labels_without_shrinking_text():
    short = resolve_adaptive_style(
        template_id="trend", plot_kind="line", row_count=10, series_count=2, max_label_length=8
    )
    long = resolve_adaptive_style(
        template_id="trend", plot_kind="line", row_count=10, series_count=2, max_label_length=40
    )
    assert long.page_width_cm > short.page_width_cm
    assert long.legend_size_pt == short.legend_size_pt
    right_cm = long.page_width_cm * (
        100 - long.layer_left_percent - long.layer_width_percent
    ) / 100
    # Full scientific series labels include units, not only short method names.
    assert right_cm >= 12.0


def test_one_curve_does_not_get_an_unused_legend_column():
    style = resolve_adaptive_style(template_id="trend", plot_kind="line", row_count=100, series_count=1)
    assert not style.profile_name.endswith("-external-legend")


def test_existing_composite_shap_profile_is_not_changed_by_generic_legend_rule():
    style = resolve_adaptive_style(
        template_id="shap_summary", plot_kind="shap_summary", row_count=8, series_count=8
    )
    assert not style.profile_name.endswith("-external-legend")


@pytest.mark.parametrize("legend_width,valid", [(140, True), (1000, False)])
def test_single_series_legend_has_explicit_page_attachment_and_bounds(legend_width, valid):
    style = resolve_adaptive_style(template_id="trend", plot_kind="line", row_count=10, series_count=1)
    values = {"width": legend_width, "height": 100, "showframe": 0, "top": -50, "left": 1200}
    label = SimpleNamespace(
        set_int=values.__setitem__, set_float=values.__setitem__,
        get_int=values.__getitem__, get_float=values.__getitem__,
    )
    op = SimpleNamespace(lt_float=lambda key: 1000 if key == "page.width" else 700)
    layer = SimpleNamespace(obj=SimpleNamespace(LT_execute=lambda command: True))
    if not valid:
        with pytest.raises(OriginDrawError, match="page"):
            _position_publication_legend(op, layer, label, style)
    else:
        result = _position_publication_legend(op, layer, label, style)
        assert result["legend.attach"] == 1
        assert result["legend.outside_data_field"] is False
        assert 0 <= result["legend.left"] < 1000
        assert result["legend.top"] >= 0


@pytest.mark.parametrize("legend_width,valid", [(140, True), (500, False)])
def test_native_legend_bounds_are_checked_without_shrinking(legend_width, valid):
    style = resolve_adaptive_style(template_id="trend", plot_kind="line", row_count=10, series_count=3)
    values = {"width": legend_width, "height": 100, "showframe": 0}
    label = SimpleNamespace(
        set_int=values.__setitem__,
        set_float=values.__setitem__,
        get_int=values.__getitem__,
        get_float=values.__getitem__,
    )
    op = SimpleNamespace(lt_float=lambda key: 1000 if key == "page.width" else 700)
    layer = SimpleNamespace(obj=SimpleNamespace(LT_execute=lambda command: True))
    if not valid:
        with pytest.raises(OriginDrawError, match="reserved column"):
            _position_publication_legend(op, layer, label, style)
    else:
        readback = _position_publication_legend(op, layer, label, style)
        assert readback["legend.outside_data_field"]
        assert readback["legend.attach"] == 1
        assert readback["legend.width"] == legend_width


def test_repositioning_preserves_an_explicitly_requested_legend_frame():
    style = resolve_adaptive_style(template_id="trend", plot_kind="line", row_count=10, series_count=1)
    values = {"width": 140, "height": 100, "showframe": 1, "top": -50, "left": 1200}
    label = SimpleNamespace(set_int=values.__setitem__, set_float=values.__setitem__,
                            get_int=values.__getitem__, get_float=values.__getitem__)
    op = SimpleNamespace(lt_float=lambda key: 1000 if key == "page.width" else 700)
    layer = SimpleNamespace(obj=SimpleNamespace(LT_execute=lambda command: True))
    result = _position_publication_legend(op, layer, label, style, expected_frame=1)
    assert result["legend.showframe"] == 1
    assert values["showframe"] == 1
    with pytest.raises(OriginDrawError):
        _position_publication_legend(op, layer, label, style)


def test_profile_rotated_title_centers_on_its_frozen_data_layer():
    style = resolve_adaptive_style(template_id="bar", plot_kind="bar_error", row_count=5, series_count=2)
    values = {"width": 120}
    label = SimpleNamespace(set_int=values.__setitem__, set_float=values.__setitem__,
                            get_float=values.__getitem__)
    op = SimpleNamespace(lt_float=lambda key: 1000 if key == "page.width" else 700,
                         lt_exec=lambda _command: True)
    _position_rotated_category_title(op, label, style)
    assert values["left"] + 60 == pytest.approx(
        1000 * (style.layer_left_percent + style.layer_width_percent / 2) / 100
    )
    assert values["top"] == 630
    _position_rotated_category_title(op, label)
    assert values["left"] + 60 == pytest.approx(610.05)


@pytest.mark.parametrize("profile,external", [(True, True), (False, True), (True, False)])
def test_native_wrap_is_only_used_for_profile_external_legends(profile, external):
    style = resolve_adaptive_style(
        template_id="trend", plot_kind="line", row_count=10, series_count=3 if external else 1,
    )
    style = replace(style, legend_size_pt=24, personal_profile=(
        {"id": "n4-f-u-v1.2", "overrides": {"legend_size_pt": 24}} if profile else None
    ))
    before = asdict(style)
    page = {"page.width": 1000, "page.height": 700}
    page_before = dict(page)
    values = {"width": 1100, "height": 100, "showframe": 0, "fsize": 24, "font": 71}
    writes = []

    def set_property(key, value):
        writes.append((key, value))
        values[key] = value
        if key == "wrapwidth":
            assert values["wrap"] == 1
            values["width"] = value
            values["height"] = 240

    def refresh(command):
        assert command == "doc -uw;"  # No page/layer geometry commands.
        return True

    label = SimpleNamespace(set_int=set_property, set_float=set_property,
                            get_int=values.__getitem__, get_float=values.__getitem__)
    op = SimpleNamespace(lt_float=page.__getitem__)
    layer = SimpleNamespace(obj=SimpleNamespace(LT_execute=refresh))
    if profile and external:
        result = _position_publication_legend(op, layer, label, style)
        assert values["wrapwidth"] == pytest.approx(990 - values["left"])
        assert result["legend.width"] == values["wrapwidth"]
        assert result["legend.height"] == 240
        assert result["legend.outside_data_field"] is True
    else:
        with pytest.raises(OriginDrawError, match="does not fit"):
            _position_publication_legend(op, layer, label, style)
        assert not any(key in {"wrap", "wrapwidth"} for key, _ in writes)
    assert values["fsize"] == 24 and values["font"] == 71
    assert not any(key in {"fsize", "font"} for key, _ in writes)
    assert asdict(style) == before
    assert page == page_before


def test_wrapping_still_rejects_a_legend_taller_than_the_native_page():
    style = replace(resolve_adaptive_style(
        template_id="trend", plot_kind="line", row_count=10, series_count=3,
    ), personal_profile={"id": "n4-f-u-v1.2", "overrides": {"legend_size_pt": 24}})
    values = {"width": 1100, "height": 100, "showframe": 0}

    def set_property(key, value):
        values[key] = value
        if key == "wrapwidth":
            values.update(width=value, height=1000)

    label = SimpleNamespace(set_int=set_property, set_float=set_property,
                            get_int=values.__getitem__, get_float=values.__getitem__)
    op = SimpleNamespace(lt_float=lambda key: 1000 if key == "page.width" else 700)
    layer = SimpleNamespace(obj=SimpleNamespace(LT_execute=lambda _: True))
    with pytest.raises(OriginDrawError, match="reserved column"):
        _position_publication_legend(op, layer, label, style)
    assert values["wrap"] == 1
