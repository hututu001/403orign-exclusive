from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
sys.path.insert(0, str(ROOT / "skill" / "editaplot" / "scripts"))
sys.path.insert(0, str(RUNTIME / "src"))

import editaplot as cli  # noqa: E402
import editaplot_core as core  # noqa: E402
from origin_sciplot.scientific_workflow import prepare_scientific  # noqa: E402
from origin_sciplot.workers.run_template_worker import (  # noqa: E402
    _apply_personal_profile_request,
    _parse_personal_profile_request,
    _record_personal_profile,
)

PROFILE = {
    "id": "n4-f-u-v1.2",
    "overrides": {
        "page_width_cm": 28.8544, "page_height_cm": 20.14728,
        "font_family": "Arial", "axis_title_size_pt": 28,
        "tick_label_size_pt": 26, "legend_size_pt": 24,
        "annotation_size_pt": 24, "bold": True, "png_dpi": 600,
        "legend_position": "inside",
    },
}
SOURCE = RUNTIME / "templates" / "trend" / "example_standard.csv"


def _hash(payload):
    return hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


@pytest.fixture
def local_config(tmp_path, monkeypatch):
    path = tmp_path / ".editaplot-local.json"
    monkeypatch.setattr(core, "PERSONAL_PROFILE_CONFIG_PATH", path)
    return path


def _write_config(path, *, engine=RUNTIME, profile=PROFILE):
    path.write_text(json.dumps({"engine_home": str(engine), "personal_profile": profile}), encoding="utf-8")


def _plan(**kwargs):
    confirmation = core.understand_data(SOURCE, template_id="trend", engine_home=RUNTIME)[
        "confirmation_gate"
    ]["confirmation_payload_template"]
    return core.build_plan(
        SOURCE, template_id="trend", claim="Compare the supplied series.",
        evidence_role="comparison", semantic_confirmation=confirmation,
        engine_home=RUNTIME, **kwargs,
    )


def test_default_profile_is_engine_scoped_and_can_be_disabled(local_config, tmp_path):
    baseline = _plan()
    _write_config(local_config, engine=tmp_path / "another-runtime")
    assert _plan() == baseline
    _write_config(local_config)
    plan = _plan()
    contract = plan["figure_contract"]["personal_profile"]
    assert contract["id"] == PROFILE["id"]
    assert contract["overrides"]["png_dpi"] == 600
    assert contract["overrides"]["legend_position"] == "inside"
    assert len(contract["overrides"]) == 10
    assert contract["report"]["input_plan_digest"] == baseline["template"]["plan_digest"]
    assert contract["report"]["output_plan_digest"] == plan["template"]["plan_digest"]
    assert _plan(personal_profile="none") == baseline
    core.validate_plan(plan)


def test_worker_uses_frozen_profile_when_local_default_changes(local_config):
    _write_config(local_config)
    plan = _plan()
    changed = copy.deepcopy(PROFILE)
    changed["overrides"]["png_dpi"] = 300
    _write_config(local_config, profile=changed)
    command, _, _ = core.build_worker_command(plan, engine_home=RUNTIME)
    raw = command[command.index("--personal-profile-json") + 1]
    request = _parse_personal_profile_request(raw)
    prepared = prepare_scientific(SOURCE, "trend")
    updated, report = _apply_personal_profile_request(prepared, request)
    assert updated.plan_digest == plan["template"]["plan_digest"]
    assert report == plan["figure_contract"]["personal_profile"]["report"]
    style = updated.plot_spec.display_plan.figure_style
    original = prepared.plot_spec.display_plan.figure_style
    assert style.personal_profile["overrides"]["png_dpi"] == 600
    assert style.personal_profile["overrides"]["page_width_cm"] == 28.8544
    assert style.personal_profile["overrides"]["page_height_cm"] == 20.14728
    assert style.page_width_cm == 28.8544
    assert style.page_height_cm == 20.14728
    assert style.personal_profile["overrides"]["legend_position"] == "inside"
    for field in ("plot_line_width_pt", "frame_line_width_pt", "palette_name"):
        assert getattr(style, field) == getattr(original, field)
    assert updated.plot_spec.series == prepared.plot_spec.series


def test_page_override_changes_native_page_and_preserves_template_layer_percentages(local_config):
    profile = {"id": "page-only", "overrides": {
        "page_width_cm": 28.8544, "page_height_cm": 20.14728, "png_dpi": 600,
    }}
    _write_config(local_config, profile=profile)
    plan = _plan()
    command, _, _ = core.build_worker_command(plan, engine_home=RUNTIME)
    request = _parse_personal_profile_request(command[command.index("--personal-profile-json") + 1])
    prepared = prepare_scientific(SOURCE, "trend")
    updated, _ = _apply_personal_profile_request(prepared, request)
    before, after = prepared.plot_spec.display_plan.figure_style, updated.plot_spec.display_plan.figure_style
    assert after.page_width_cm == 28.8544
    assert after.page_height_cm == 20.14728
    for field in ("layer_left_percent", "layer_top_percent",
                  "layer_width_percent", "layer_height_percent"):
        assert getattr(after, field) == getattr(before, field)


@pytest.mark.parametrize("field", ["overrides", "profile_hash", "report_hash", "output_plan_digest"])
def test_profile_tampering_is_rejected_before_origin(local_config, field):
    _write_config(local_config)
    plan = _plan()
    contract = plan["figure_contract"]["personal_profile"]
    if field == "overrides":
        contract["overrides"]["png_dpi"] = 300
    elif field == "profile_hash":
        contract[field] = "0" * 64
    else:
        contract["report"][field] = "0" * 64
    plan["plan_hash"] = _hash({key: value for key, value in plan.items() if key != "plan_hash"})
    with pytest.raises(core.EditaPlotError, match="personal profile"):
        core.build_worker_command(plan, engine_home=RUNTIME)


def test_old_plan_does_not_pick_up_new_local_profile(local_config):
    old = _plan()
    _write_config(local_config)
    core.validate_plan(old)
    command, _, _ = core.build_worker_command(old, engine_home=RUNTIME)
    assert "--personal-profile-json" not in command
    preparation = prepare_scientific(SOURCE, "trend")
    unchanged, report = _apply_personal_profile_request(preparation, None)
    assert unchanged is preparation and report is None


def test_cli_personal_profile_none(local_config, tmp_path):
    _write_config(local_config)
    confirmation = core.understand_data(SOURCE, template_id="trend", engine_home=RUNTIME)[
        "confirmation_gate"
    ]["confirmation_payload_template"]
    confirmed = tmp_path / "confirmed.json"
    confirmed.write_text(json.dumps(confirmation), encoding="utf-8")
    output = tmp_path / "plan.json"
    assert cli.main([
        "plan", str(SOURCE), "--template-id", "trend", "--claim", "Compare series.",
        "--personal-profile", "none", "--semantic-confirmation-json", str(confirmed),
        "--output", str(output), "--engine-home", str(RUNTIME),
    ]) == 0
    assert "personal_profile" not in json.loads(output.read_text(encoding="utf-8"))["figure_contract"]


@pytest.fixture
def profiled_output(local_config, tmp_path):
    _write_config(local_config)
    plan = _plan()
    contract = plan["figure_contract"]["personal_profile"]
    output = tmp_path / "output"
    output.mkdir()
    for name in ("result.opju", "result.pdf", "result.tif", "validation_report.json"):
        (output / name).write_bytes(b"existing artifact")
    Image.new("1", (6816, 4759), 1).save(output / "result.png", dpi=(600, 600))
    report = {
        "origin_axis_state": {"x": {"font": 1}},
        "origin_text_state": {"title": {"font": 1, "font_code_expected": 1}},
        "exports": {"png": True, "pdf": True, "tif": True},
        "source_data_modified": False,
        "personal_profile_application": contract["report"],
        "personal_profile": {
            "id": contract["id"], "overrides": contract["overrides"],
            "profile_hash": contract["profile_hash"], "passed": True,
            "plot_styles_preserved": True,
            "page": {"width_cm": 28.8544, "height_cm": 20.14728},
            "axes": [{"axis": "x", "tick_label_size_pt": 26}],
            "texts": [{"name": "Legend", "size_pt": 24}],
            "png": {"verified": True},
        },
    }
    core.write_json(output / "render-plan.json", plan)
    core.write_json(output / "origin_verify_report.json", report)
    return output, report


def test_verify_rechecks_real_png_pixels_and_dpi(profiled_output):
    output, _ = profiled_output
    result = core.verify_output(output)
    assert result["programmatic_pass"] is True
    png = result["semantic_checks"]["personal_profile"]["png"]
    assert png["width_px"] == 6816 and png["height_px"] == 4759
    assert png["expected_dpi"] == 600
    assert png["expected_width_in"] == pytest.approx(11.36)
    assert png["expected_height_in"] == pytest.approx(7.932)
    # A previously passing report cannot make a replaced 300-dpi image pass.
    Image.new("1", (6816, 4759), 1).save(output / "result.png", dpi=(300, 300))
    result = core.verify_output(output)
    assert result["programmatic_pass"] is False
    assert "DPI metadata" in result["semantic_checks"]["personal_profile"]["error"]


@pytest.mark.parametrize("field", ["missing", "profile_hash", "application", "page"])
def test_verify_requires_actual_profile_evidence_matching_frozen_plan(profiled_output, field):
    output, report = profiled_output
    if field == "missing":
        del report["personal_profile"]
    elif field == "profile_hash":
        report["personal_profile"]["profile_hash"] = "0" * 64
    elif field == "application":
        report["personal_profile_application"]["report_hash"] = "0" * 64
    else:
        report["personal_profile"]["page"]["width_cm"] = 0
    core.write_json(output / "origin_verify_report.json", report)
    assert core.verify_output(output)["semantic_checks"]["personal_profile"]["ok"] is False


@pytest.mark.parametrize("dimension", ["width", "height"])
def test_native_page_must_match_frozen_personal_dimensions(profiled_output, dimension):
    output, report = profiled_output
    report["personal_profile"]["page"][f"{dimension}_cm"] = 18
    core.write_json(output / "origin_verify_report.json", report)
    result = core.verify_output(output)
    assert result["programmatic_pass"] is False
    assert f"native page {dimension}" in result["semantic_checks"]["personal_profile"]["error"]


def test_native_page_rounding_tolerance_does_not_change_frozen_png_dimensions(profiled_output):
    output, report = profiled_output
    report["personal_profile"]["page"]["height_cm"] += 0.01
    core.write_json(output / "origin_verify_report.json", report)
    result = core.verify_output(output)
    assert result["programmatic_pass"] is True
    assert result["semantic_checks"]["personal_profile"]["png"]["expected_height_in"] == pytest.approx(7.932)


def test_worker_rejects_non_object_profile_report(local_config):
    _write_config(local_config)
    contract = _plan()["figure_contract"]["personal_profile"]
    contract["report"] = []
    with pytest.raises(ValueError, match="report must be an object"):
        _parse_personal_profile_request(json.dumps(contract))


def test_worker_preserves_actual_readback_when_recording_frozen_application(profiled_output):
    directory, report = profiled_output
    output = SimpleNamespace(
        output_dir=directory, origin_verify_report=directory / "origin_verify_report.json"
    )
    actual = copy.deepcopy(report["personal_profile"])
    application = report.pop("personal_profile_application")
    core.write_json(output.origin_verify_report, report)
    result = {"verify": report}
    _record_personal_profile(output, result, application)
    recorded = json.loads(output.origin_verify_report.read_text(encoding="utf-8"))
    assert recorded["personal_profile"] == actual
    assert recorded["personal_profile_application"] == application
    assert result["verify"]["personal_profile_application"] == application
    del report["personal_profile"]
    core.write_json(output.origin_verify_report, report)
    with pytest.raises(RuntimeError, match="readback does not match"):
        _record_personal_profile(output, {"verify": report}, application)
