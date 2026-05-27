"""`python -m tools.publish` — publish the packed archive in dist/ as a GitHub
Release, targeting the current HEAD.

Run AFTER `tools.release` has packed the archive AND AFTER the build commit has
been pushed to main. Uses `git rev-parse HEAD` as the release `--target` so the
tag points to the commit that actually contains the build artifacts (not the
pre-build merge commit).

Reads the tag from `build/manifest.json`, the archive from
`dist/<tag>.tar.gz`, and the description from `dist/<tag>.description.md`.

Run from repo root:
    python -m tools.publish
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from tools.lib.release import build_tag


REPO_ROOT = Path.cwd()
BUILD_DIR = REPO_ROOT / "build"
MANIFEST = BUILD_DIR / "manifest.json"
DIST_DIR = REPO_ROOT / "dist"


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def main() -> int:
    if shutil.which("gh") is None:
        _eprint("gh CLI not found. Install from https://cli.github.com/ and run `gh auth login`.")
        return 2

    if not MANIFEST.exists():
        _eprint(f"manifest not found at {MANIFEST}; run `python -m tools.build_geojson` first.")
        return 2

    manifest = json.loads(MANIFEST.read_text())
    tag = build_tag(manifest["built_at"], manifest["commit"])

    archive = DIST_DIR / f"{tag}.tar.gz"
    description = DIST_DIR / f"{tag}.description.md"
    if not archive.exists():
        _eprint(f"archive not found: {archive}; run `python -m tools.release` first.")
        return 2
    if not description.exists():
        _eprint(f"description not found: {description}; run `python -m tools.release` first.")
        return 2

    try:
        target = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT),
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        _eprint("could not resolve HEAD via git; aborting.")
        return 2

    result = subprocess.run(
        [
            "gh", "release", "create", tag,
            str(archive),
            "--target", target,
            "--title", tag,
            "--notes-file", str(description),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        _eprint(f"`gh release create` failed:\n{result.stderr}")
        return 2

    url_lines = [ln for ln in result.stdout.strip().splitlines() if ln.strip()]
    url = url_lines[-1] if url_lines else ""
    _eprint(f"✓ Published {tag} → {url}")
    _eprint(f"  target: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
