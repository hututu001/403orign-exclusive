from __future__ import annotations

import sys
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime/src"))

from origin_sciplot.origin_backend.scientific_renderer import _position_x_title  # noqa: E402
from origin_sciplot.scientific_visual import resolve_adaptive_style  # noqa: E402


@pytest.mark.parametrize("title_height", (268.0, 310.0))
def test_profile_title_keeps_template_position_without_moving_native_plot_or_center(title_height):
    style = replace(resolve_adaptive_style(
        template_id="bar", plot_kind="bar_error", row_count=5, series_count=2,
    ), personal_profile={"id": "canvas-v1.2", "overrides": {"axis_title_size_pt": 28}})
    original_style = asdict(style)
    values = {"left": 2200.0, "top": 3480.0, "width": 900.0, "height": title_height,
              "attach": 1, "fsize": 28.0}
    before = values.copy()
    writes = []

    def set_property(name, value):
        writes.append(name)
        values[name] = value

    label = SimpleNamespace(set_int=set_property, set_float=set_property, get_float=values.__getitem__)
    op = SimpleNamespace(lt_float=lambda key: 3897.0 if key == "page.height" else pytest.fail(key))
    _position_x_title(op, label, style)
    assert values["top"] == pytest.approx(before["top"] - 3897.0 * style.x_title_upshift_page_percent / 100)
    assert {key: value for key, value in values.items() if key != "top"} == {
        key: value for key, value in before.items() if key != "top"
    }
    assert writes == ["attach", "top"]
    assert asdict(style) == original_style


@pytest.mark.parametrize("profile_enabled", [False, True])
def test_line_title_keeps_existing_upshift_with_or_without_personal_profile(profile_enabled):
    style = resolve_adaptive_style(template_id="trend", plot_kind="line", row_count=5, series_count=1)
    if profile_enabled:
        style = replace(
            style, personal_profile={"id": "canvas-v1.2", "overrides": {"axis_title_size_pt": 28}}
        )
    values = {"top": 900.0}
    label = SimpleNamespace(set_int=values.__setitem__, set_float=values.__setitem__,
                            get_float=values.__getitem__)
    _position_x_title(SimpleNamespace(lt_float=lambda key: 1000), label, style)
    assert values["top"] == 900.0 - 1000 * style.x_title_upshift_page_percent / 100


def test_outward_personal_axis_title_uses_lower_margin_without_changing_layer():
    style = replace(
        resolve_adaptive_style(template_id="bar", plot_kind="bar_error", row_count=5, series_count=3),
        personal_profile={"id": "axes", "overrides": {"tick_direction": "out"}},
    )
    before = asdict(style)
    values={"top":4280.,"height":268.}
    label=SimpleNamespace(set_int=values.__setitem__,set_float=values.__setitem__,get_float=values.__getitem__)
    _position_x_title(SimpleNamespace(lt_float=lambda key:4759.),label,style)
    assert values['top']==pytest.approx(4443.41)
    assert values['top']+values['height']<4759
    assert asdict(style)==before
