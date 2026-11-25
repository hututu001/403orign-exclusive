"""Exercise the personal edition exactly as a fresh checkout without local state."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
sys.path.insert(0, str(ROOT / "skill" / "editaplot" / "scripts"))
sys.path.insert(0, str(RUNTIME / "src"))

import editaplot_core as core  # noqa: E402
from origin_sciplot.scientific_visual import normalize_personal_profile  # noqa: E402


@pytest.fixture
def portable_defaults(monkeypatch):
    monkeypatch.setattr(core, "PROJECT_PROFILE_FILENAME", "personal-profile.json")
    return normalize_personal_profile(
        json.loads((RUNTIME / "personal-profile.json").read_text(encoding="utf-8"))
    )


def _plan(template_id, source, **kwargs):
    confirmation = core.understand_data(source, template_id=template_id, engine_home=RUNTIME)[
        "confirmation_gate"
    ]["confirmation_payload_template"]
    return core.build_plan(
        source, template_id=template_id, claim="Compare the supplied series.",
        evidence_role="comparison", semantic_confirmation=confirmation, engine_home=RUNTIME, **kwargs,
    )


@pytest.mark.parametrize("template_id,source", [
    ("trend", RUNTIME / "templates" / "trend" / "example_standard.csv"),
    ("bar", ROOT / "examples" / "gallery" / "bar_grouped_error.csv"),
])
def test_fresh_checkout_auto_applies_twenty_defaults(portable_defaults, template_id, source):
    assert not core.PERSONAL_PROFILE_CONFIG_PATH.exists()
    plan = _plan(template_id, source)
    profile = plan["figure_contract"]["personal_profile"]
    assert profile["id"] == portable_defaults["id"]
    assert profile["overrides"] == portable_defaults["overrides"]
    assert len(profile["overrides"]) == 20
    core.validate_plan(plan)
    baseline = _plan(template_id, source, personal_profile="none")
    assert "personal_profile" not in baseline["figure_contract"]
    assert baseline["source"] == plan["source"]
    assert (
        plan["figure_contract"]["personal_profile"]["report"]["input_plan_digest"]
        == baseline["template"]["plan_digest"]
    )


def test_portable_defaults_follow_selected_engine(portable_defaults, tmp_path):
    assert core._resolve_personal_profile(tmp_path, "auto") is None
    (tmp_path / "personal-profile.json").write_text(json.dumps(portable_defaults), encoding="utf-8")
    assert core._resolve_personal_profile(tmp_path, "auto") == portable_defaults


def test_local_partial_override_preserves_other_project_fields(portable_defaults):
    core.PERSONAL_PROFILE_CONFIG_PATH.write_text(json.dumps({
        "engine_home": str(RUNTIME),
        "personal_profile": {"id": "local", "overrides": {"png_dpi": 300}},
    }), encoding="utf-8")
    actual = core._resolve_personal_profile(RUNTIME, "auto")
    assert actual["overrides"] == {**portable_defaults["overrides"], "png_dpi": 300}


def test_unrelated_engine_config_does_not_hide_defaults(portable_defaults, tmp_path):
    core.PERSONAL_PROFILE_CONFIG_PATH.write_text(json.dumps({
        "engine_home": str(tmp_path), "personal_profile": None,
    }), encoding="utf-8")
    assert core._resolve_personal_profile(RUNTIME, "auto") == portable_defaults


def test_local_explicit_opt_out_remains_supported(portable_defaults):
    core.PERSONAL_PROFILE_CONFIG_PATH.write_text(json.dumps({
        "engine_home": str(RUNTIME), "personal_profile": None,
    }), encoding="utf-8")
    assert core._resolve_personal_profile(RUNTIME, "auto") is None


def test_bad_project_defaults_are_not_silently_ignored(portable_defaults, tmp_path):
    (tmp_path / "personal-profile.json").write_text(
        '{"id":"bad","overrides":{"unknown":1}}', encoding="utf-8"
    )
    with pytest.raises(core.EditaPlotError, match="project personal profile"):
        core._resolve_personal_profile(tmp_path, "auto")


def test_frozen_plan_does_not_reread_project_defaults(portable_defaults, monkeypatch):
    plan = _plan("trend", RUNTIME / "templates" / "trend" / "example_standard.csv")
    monkeypatch.setattr(core, "PROJECT_PROFILE_FILENAME", "missing-after-plan.json")
    command, _, _ = core.build_worker_command(plan, engine_home=RUNTIME)
    frozen = json.loads(command[command.index("--personal-profile-json") + 1])
    assert frozen["overrides"] == portable_defaults["overrides"]
