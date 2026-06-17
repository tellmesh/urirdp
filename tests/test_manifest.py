from __future__ import annotations

import yaml
from importlib.resources import files


def test_manifest_loads():
    raw = files("urirdp").joinpath("manifest.yaml").read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    assert data["scheme"] == "rdp"
    assert len(data["uri_patterns"]) == 5
