"""Keep template regression tests independent of workstation customizations."""

from __future__ import annotations

import sys

import pytest


@pytest.fixture(autouse=True)
def isolated_personal_profile_config(tmp_path, monkeypatch):
    core = sys.modules.get("editaplot_core")
    if core is not None:
        monkeypatch.setattr(core, "PERSONAL_PROFILE_CONFIG_PATH", tmp_path / ".editaplot-local.json")
        # Upstream template tests intentionally exercise uncustomized behavior.
        # The personal-edition integration tests explicitly enable the shipped file.
        monkeypatch.setattr(core, "PROJECT_PROFILE_FILENAME", ".no-test-project-profile.json")
