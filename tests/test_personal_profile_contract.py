from __future__ import annotations

import copy
import hashlib
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime/src"))

from origin_sciplot.origin_backend.event_raster_renderer import _validate_event_layout  # noqa: E402
from origin_sciplot.origin_backend.signal_stack_renderer import _resolve_signal_stack_layout  # noqa: E402
from origin_sciplot.scientific_visual import (  # noqa: E402
    PERSONAL_AXIS_STYLE_KEYS,
    PERSONAL_STYLE_KEYS,
    PersonalProfileError,
    apply_personal_profile,
    normalize_personal_profile,
    personal_profile_hash,
    resolve_adaptive_style,
)
from origin_sciplot.scientific_workflow import prepare_scientific  # noqa: E402
from origin_sciplot.xps_workflow import prepare_xps  # noqa: E402

PROFILE = {
    "id": "n4-f-u-v1.2",
    "overrides": {
        "page_width_cm": 28.8544, "page_height_cm": 20.14728,
        "font_family": "Arial", "axis_title_size_pt": 28, "tick_label_size_pt": 26,
        "legend_size_pt": 24, "annotation_size_pt": 24, "bold": True, "png_dpi": 600,
    },
}
SCIENTIFIC_CASES = ("trend", "line_error", "bar", "event_raster", "signal_stack", "heatmap")
XPS_CASES = ("xps_adaptive", "xps_c1s_fit")


def _prepare(template_id):
    source = ROOT / "runtime/templates" / template_id / "example_standard.csv"
    return prepare_xps(source) if template_id in XPS_CASES else prepare_scientific(source, template_id)


def _style(preparation):
    if hasattr(preparation, "visual_contract"):
        return preparation.visual_contract.figure_style
    return preparation.plot_spec.display_plan.figure_style


def _without_absent_profile(value):
    """Project the new optional field out of the pre-profile schema."""
    if isinstance(value, dict):
        return {key: _without_absent_profile(item) for key, item in value.items()
                if not (key == "personal_profile" and item is None)}
    if isinstance(value, (tuple, list)):
        return [_without_absent_profile(item) for item in value]
    return value


def _head_scientific_digest(preparation):
    # Snapshot of HEAD d93cd31's payload and serialization, checked with git show
    # during development. No call to the modified digest helper or git in this test.
    spec = _without_absent_profile(asdict(preparation.plot_spec))
    for key in ("shap_dashboard", "phasor_plan", "time_frequency_plan", "signal_stack_plan",
                "signal_stack_layout", "event_raster_plan", "event_raster_layout", "heatmap_layout"):
        if spec[key] is None:
            spec.pop(key)
    if not spec["color_scale_hex"]:
        spec.pop("color_scale_hex")
    payload = {
        "template_id": preparation.template_id, "source_sha256": preparation.source_sha256,
        "source_columns": preparation.source_columns, "assignments": preparation.assignments,
        "plot_spec": spec, "mapping_confirmed": preparation.mapping_confirmed,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _head_xps_digest(preparation):
    # HEAD d93cd31 prepare_xps's exact digest envelope and compact serialization.
    payload = {
        "source_sha256": preparation.source_sha256, "source_format": preparation.source_format,
        "source_sheet": preparation.source_sheet, "source_delimiter": preparation.source_delimiter,
        "source_columns": list(preparation.source_columns), "row_count": preparation.row_count,
        "ignored_empty_rows": preparation.ignored_empty_rows, "detection": preparation.detection.to_dict(),
        "roles": preparation.roles.to_dict(), "component_basis": preparation.component_basis,
        "plot_spec": preparation.plot_spec.to_dict(),
        "visual_contract": _without_absent_profile(preparation.visual_contract.to_dict()),
        "warnings": list(preparation.warnings), "confidence": preparation.confidence,
        "mapping_confirmed": preparation.mapping_confirmed,
        "requires_confirmation": preparation.requires_confirmation,
        "confirmation_reasons": list(preparation.confirmation_reasons),
    }
    return hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()


def _assert_unrequested_fields_unchanged(before, after, overrides):
    old_style, new_style = asdict(_style(before)), asdict(_style(after))
    for key, value in old_style.items():
        if key != "personal_profile" and key not in overrides:
            assert new_style[key] == value, key
    old, new = asdict(before), asdict(after)
    old.pop("plan_digest")
    new.pop("plan_digest")
    if hasattr(before, "visual_contract"):
        old["visual_contract"].pop("figure_style")
        new["visual_contract"].pop("figure_style")
    else:
        old["plot_spec"]["display_plan"].pop("figure_style")
        new["plot_spec"]["display_plan"].pop("figure_style")
        for key in ("event_raster_layout", "signal_stack_layout", "heatmap_layout"):
            old["plot_spec"].pop(key)
            new["plot_spec"].pop(key)
    assert new == old  # Source identity, scientific roles, mappings, marks and colors.


@pytest.mark.parametrize("template_id", SCIENTIFIC_CASES + XPS_CASES)
def test_nine_overrides_preserve_unrequested_scientific_and_visual_contract(template_id):
    baseline = _prepare(template_id)
    before = copy.deepcopy(asdict(baseline))
    source = Path(baseline.source_path)
    source_before = source.read_bytes()
    updated, report = apply_personal_profile(baseline, PROFILE)
    style = _style(updated)
    assert set(PROFILE["overrides"]) == PERSONAL_STYLE_KEYS - PERSONAL_AXIS_STYLE_KEYS - {
        "legend_position", "bar_border", "bar_fill", "bar_fill_transparency_percent",
    }
    assert style.personal_profile == normalize_personal_profile(PROFILE)
    for key in ("page_width_cm", "page_height_cm", "font_family", "axis_title_size_pt",
                "tick_label_size_pt", "legend_size_pt"):
        assert getattr(style, key) == PROFILE["overrides"][key]
    for key in ("annotation_size_pt", "bold", "png_dpi"):
        assert style.personal_profile["overrides"][key] == PROFILE["overrides"][key]
    assert style.page_width_cm / 2.54 == pytest.approx(11.36)
    assert style.page_height_cm / 2.54 == pytest.approx(7.932)
    _assert_unrequested_fields_unchanged(baseline, updated, PROFILE["overrides"])
    assert asdict(baseline) == before
    assert source.read_bytes() == source_before
    assert updated.plan_digest != baseline.plan_digest
    assert report["input_plan_digest"] == baseline.plan_digest
    assert report["output_plan_digest"] == updated.plan_digest
    assert report["applied_fields"] == sorted(PROFILE["overrides"])
    assert report["report_hash"] == personal_profile_hash({
        key: value for key, value in report.items() if key != "report_hash"
    })
    repeated, repeated_report = apply_personal_profile(baseline, PROFILE)
    assert repeated == updated
    assert repeated_report == report


@pytest.mark.parametrize("template_id", ("trend", "heatmap", "xps_adaptive"))
@pytest.mark.parametrize("overrides", (
    {"font_family": "Times New Roman"}, {"png_dpi": 300},
    {"bold": False}, {"annotation_size_pt": 24},
))
def test_partial_profile_inherits_every_unspecified_template_setting(template_id, overrides):
    baseline = _prepare(template_id)
    updated, _ = apply_personal_profile(baseline, {"id": "partial", "overrides": overrides})
    assert _style(updated).personal_profile["overrides"] == overrides
    _assert_unrequested_fields_unchanged(baseline, updated, overrides)
    if template_id == "heatmap":
        assert updated.plot_spec.heatmap_layout == baseline.plot_spec.heatmap_layout


def test_event_layout_retains_source_positions_marks_and_colors_with_shared_style():
    baseline = _prepare("event_raster")
    updated, _ = apply_personal_profile(baseline, PROFILE)
    old, new = asdict(baseline.plot_spec.event_raster_layout), asdict(updated.plot_spec.event_raster_layout)
    old.pop("style")
    new.pop("style")
    assert new == old
    assert updated.plot_spec.event_raster_layout.style == _style(updated)
    _validate_event_layout(updated)  # Pure contract check; no Origin activation.


def test_signal_layout_preserves_ruler_amplitudes_and_offsets():
    baseline = _prepare("signal_stack")
    updated, _ = apply_personal_profile(baseline, PROFILE)
    spec = updated.plot_spec
    assert spec.signal_stack_plan == baseline.plot_spec.signal_stack_plan
    old_layout, new_layout = baseline.plot_spec.signal_stack_layout, spec.signal_stack_layout
    for key in ("x_range", "y_range", "reference_y_from", "reference_y_to",
                "reference_text", "reference_text_y_percent", "y_title_y_percent"):
        assert getattr(new_layout, key) == getattr(old_layout, key)
    assert [(label, y) for label, _, y in new_layout.channel_labels] == [
        (label, y) for label, _, y in old_layout.channel_labels
    ]
    assert spec.signal_stack_layout.x_range == spec.signal_stack_plan.time_range
    assert (
        spec.signal_stack_layout.reference_y_to - spec.signal_stack_layout.reference_y_from
        == pytest.approx(spec.signal_stack_plan.amplitude_scale_length)
    )
    expected_height = (
        spec.signal_stack_plan.amplitude_scale_length / (spec.axis_plan.y_to - spec.axis_plan.y_from)
        * _style(updated).page_height_cm * _style(updated).layer_height_percent / 100
    )
    assert spec.signal_stack_layout.reference_height_cm == pytest.approx(expected_height)
    _resolve_signal_stack_layout(updated, spec.signal_stack_plan)


def test_heatmap_layout_updates_type_sizes_without_reordering_values_or_labels():
    baseline = _prepare("heatmap")
    updated, _ = apply_personal_profile(baseline, PROFILE)
    spec, style = updated.plot_spec, _style(updated)
    layout = spec.heatmap_layout
    assert layout.cell_label_size_pt == round(style.tick_label_size_pt * 0.76)
    assert layout.colorbar_label_size_pt == max(15, round(style.tick_label_size_pt * 0.88))
    for key in ("rows", "columns", "show_cell_labels", "x_visible_indices", "y_visible_indices",
                "x_display_labels", "y_display_labels", "x_rotation_deg"):
        assert getattr(layout, key) == getattr(baseline.plot_spec.heatmap_layout, key)


def test_sparse_heatmap_labels_keep_hidden_row_inventory_after_profile(tmp_path):
    source = tmp_path / "dense_heatmap.csv"
    source.write_text(
        "Dataset,A,B,C\n" + "".join(
            f"Dataset with long name {index:02d},{index},{index + 1},{index + 2}\n"
            for index in range(30)
        ), encoding="utf-8",
    )
    baseline = prepare_scientific(source, "heatmap")
    updated, _ = apply_personal_profile(baseline, PROFILE)
    before, after = asdict(baseline.plot_spec.heatmap_layout), asdict(updated.plot_spec.heatmap_layout)
    assert before["rows"] == 30
    assert "" in before["y_display_labels"]  # A hidden label is still a real source row.
    for field in ("cell_label_size_pt", "colorbar_label_size_pt"):
        before.pop(field)
        after.pop(field)
    assert after == before
    _assert_unrequested_fields_unchanged(baseline, updated, PROFILE["overrides"])


@pytest.mark.parametrize("template_id", SCIENTIFIC_CASES)
def test_no_profile_scientific_digest_matches_pre_profile_head_schema(template_id):
    prepared = _prepare(template_id)
    assert _style(prepared).personal_profile is None
    assert "personal_profile" not in _style(prepared).to_dict()
    assert prepared.plan_digest == _head_scientific_digest(prepared)


@pytest.mark.parametrize("template_id", XPS_CASES)
def test_no_profile_xps_digest_matches_pre_profile_head_schema(template_id):
    prepared = _prepare(template_id)
    assert _style(prepared).personal_profile is None
    assert "personal_profile" not in prepared.visual_contract.to_dict()["figure_style"]
    assert prepared.plan_digest == _head_xps_digest(prepared)


@pytest.mark.parametrize("template_id", SCIENTIFIC_CASES + XPS_CASES)
def test_page_profile_changes_native_page_only_and_preserves_layer_percentages(template_id):
    baseline = _prepare(template_id)
    overrides = {"page_width_cm": 28.8544, "page_height_cm": 20.14728, "png_dpi": 600}
    updated, _ = apply_personal_profile(baseline, {"id": "canvas", "overrides": overrides})
    assert _style(updated).page_width_cm == 28.8544
    assert _style(updated).page_height_cm == 20.14728
    _assert_unrequested_fields_unchanged(baseline, updated, overrides)
    if not hasattr(baseline, "visual_contract"):
        assert (updated.plot_spec.display_plan.category_label_rotation_deg
                == baseline.plot_spec.display_plan.category_label_rotation_deg)


@pytest.mark.parametrize("key", ("export_width_in", "export_height_in"))
def test_export_canvas_overrides_are_rejected_in_native_page_profile(key):
    with pytest.raises(PersonalProfileError, match="unsupported"):
        normalize_personal_profile({"id": "old", "overrides": {key: 11.36}})


def test_bar_profile_keeps_original_rotation_and_full_native_layer():
    baseline = _prepare("bar")
    updated, _ = apply_personal_profile(baseline, PROFILE)
    assert updated.plot_spec.display_plan.category_label_rotation_deg == 0
    assert _style(updated).layer_height_percent == _style(baseline).layer_height_percent == 80
    assert _style(updated).layer_width_percent == _style(baseline).layer_width_percent
    assert _style(updated).tick_label_size_pt == 26
    assert _style(updated).axis_title_size_pt == 28
    assert baseline.plan_digest == _head_scientific_digest(baseline)


@pytest.mark.parametrize(
    "template_id", ("trend", "line_error", "bar", "scatter", "diagnostic_curve", "decision_curve")
)
def test_explicit_inside_legend_uses_pre_reservation_layout_and_preserves_science(template_id):
    baseline = _prepare(template_id)
    old_style = _style(baseline)
    assert old_style.profile_name.endswith("-external-legend")
    updated, _ = apply_personal_profile(
        baseline, {"id": "inside", "overrides": {"legend_position": "inside"}}
    )
    style = _style(updated)
    assert not style.profile_name.endswith("-external-legend")
    assert style.page_width_cm < old_style.page_width_cm
    old_data_width = old_style.page_width_cm * old_style.layer_width_percent / 100
    new_data_width = style.page_width_cm * style.layer_width_percent / 100
    assert new_data_width == pytest.approx(old_data_width, abs=0.01)
    for field, value in asdict(old_style).items():
        if field not in {
            "profile_name",
            "page_width_cm",
            "layer_left_percent",
            "layer_width_percent",
            "personal_profile",
        }:
            assert getattr(style, field) == value, field
    old_spec, new_spec = asdict(baseline.plot_spec), asdict(updated.plot_spec)
    old_spec["display_plan"].pop("figure_style")
    new_spec["display_plan"].pop("figure_style")
    assert new_spec == old_spec
    assert updated.source_sha256 == baseline.source_sha256


def test_inside_bar_restores_original_sixteen_eighty_plot_field():
    baseline = _prepare("bar")
    updated, _ = apply_personal_profile(
        baseline, {"id": "inside", "overrides": {"legend_position": "inside"}}
    )
    style = _style(updated)
    assert style.page_width_cm == 24.45
    assert style.layer_left_percent == 16
    assert style.layer_width_percent == 80
    assert style.page_height_cm == 16.5


@pytest.mark.parametrize("template_id", ("trend", "line_error", "bar", "scatter"))
def test_native_page_overrides_apply_after_inside_template_layer_resolution(template_id):
    baseline = _prepare(template_id)
    inside, _ = apply_personal_profile(baseline, {"id": "inside", "overrides": {"legend_position": "inside"}})
    profile = copy.deepcopy(PROFILE)
    profile["overrides"]["legend_position"] = "inside"
    updated, _ = apply_personal_profile(baseline, profile)
    style, inside_style = _style(updated), _style(inside)
    assert style.page_width_cm == 28.8544
    assert style.page_height_cm == 20.14728
    for field in (
        "profile_name",
        "layer_left_percent",
        "layer_top_percent",
        "layer_width_percent",
        "layer_height_percent",
    ):
        assert getattr(style, field) == getattr(inside_style, field)
    assert (
        updated.plot_spec.display_plan.category_label_rotation_deg
        == baseline.plot_spec.display_plan.category_label_rotation_deg
    )
    assert updated.plot_spec.series == baseline.plot_spec.series
    assert updated.plot_spec.axis_plan == baseline.plot_spec.axis_plan


@pytest.mark.parametrize(
    "template_id", ("trend", "line_error", "bar", "heatmap", "event_raster", "signal_stack")
)
def test_template_legend_override_preserves_upstream_layout(template_id):
    baseline = _prepare(template_id)
    updated, _ = apply_personal_profile(
        baseline, {"id": "template", "overrides": {"legend_position": "template"}}
    )
    _assert_unrequested_fields_unchanged(baseline, updated, {"legend_position": "template"})


@pytest.mark.parametrize("template_id", ("heatmap", "event_raster", "signal_stack"))
def test_inside_legend_does_not_rebuild_specialized_layout(template_id):
    baseline = _prepare(template_id)
    updated, _ = apply_personal_profile(
        baseline, {"id": "inside", "overrides": {"legend_position": "inside"}}
    )
    _assert_unrequested_fields_unchanged(baseline, updated, {"legend_position": "inside"})


def test_xps_inside_position_retains_explicit_hidden_legend():
    baseline = _prepare("xps_adaptive")
    baseline = replace(baseline, visual_contract=replace(baseline.visual_contract,
                                                       legend_position="outside_right", legend_visible=False))
    updated, _ = apply_personal_profile(
        baseline, {"id": "inside", "overrides": {"legend_position": "inside"}}
    )
    assert updated.visual_contract.legend_position == "inside"
    assert updated.visual_contract.legend_visible is False
    assert _style(updated).page_width_cm == _style(baseline).page_width_cm


def test_inside_resolver_keeps_publication_palette_and_widths():
    args = dict(template_id="trend", plot_kind="line", row_count=10, series_count=2)
    normal, inside = resolve_adaptive_style(**args), resolve_adaptive_style(**args, legend_position="inside")
    assert normal.palette_name == inside.palette_name == "publication_signal"
    assert normal.plot_line_width_pt == inside.plot_line_width_pt == 2.2
    assert normal.frame_line_width_pt == inside.frame_line_width_pt == 1.3
