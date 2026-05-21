"""Smoke test for the manifest fields written by tools.build_geojson."""

import json
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_manifest_has_built_at_and_commit():
    """After running build_geojson, manifest.json must carry built_at + commit."""
    result = subprocess.run(
        [sys.executable, "-m", "tools.build_geojson"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    manifest = json.loads((REPO_ROOT / "build" / "manifest.json").read_text())
    assert "built_at" in manifest, "manifest must record build timestamp"
    assert "commit" in manifest, "manifest must record commit at build time"
    assert re.match(r"^\d{4}-\d{2}-\d{2}T", manifest["built_at"]), manifest["built_at"]
    assert re.match(r"^[0-9a-f]{7,}$", manifest["commit"]), manifest["commit"]
