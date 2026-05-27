"""Integration tests for `tools.publish` — the GitHub Release step that runs
after the build commit has been pushed to main.
"""

import json
import os
import stat
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _make_stub(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _seed_packed(tmp: Path, *, tag: str = "build-2026-05-22-newsha1", with_archive: bool = True, with_description: bool = True) -> None:
    (tmp / "build").mkdir()
    (tmp / "build" / "manifest.json").write_text(json.dumps({
        "shapefile": "data/shapefiles/DRC_Health_zones.shp",
        "built_at": "2026-05-22T10:00:00+00:00",
        "commit": "newsha1",
        "datasets": [],
    }))
    (tmp / "dist").mkdir()
    if with_archive:
        (tmp / "dist" / f"{tag}.tar.gz").write_bytes(b"fake-archive")
    if with_description:
        (tmp / "dist" / f"{tag}.description.md").write_text("Release notes.\n")


def _init_git(tmp: Path, head_sha: str = "deadbeef") -> str:
    subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@e", "-c", "user.name=t", "commit", "-qm", "init"],
        cwd=tmp,
        check=True,
    )
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp, text=True).strip()
    return sha


def _install_gh_stub(tmp: Path, *, returncode: int = 0) -> tuple[Path, Path]:
    bin_dir = tmp / "bin"
    bin_dir.mkdir()
    gh_log = tmp / "gh.log"
    body = (
        f"""#!/usr/bin/env bash
echo "$@" >> {gh_log}
if [ "$1" = "release" ] && [ "$2" = "create" ]; then
  echo "https://github.com/INRB-UMIE/Ebola_DRC_2026/releases/tag/$3"
fi
exit {returncode}
"""
    )
    _make_stub(bin_dir / "gh", body)
    return bin_dir, gh_log


def _env(tmp: Path, bin_dir: Path) -> dict:
    return {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
        "PYTHONPATH": str(REPO_ROOT),
    }


def _run(tmp: Path, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "tools.publish"],
        cwd=tmp,
        capture_output=True,
        text=True,
        env=env,
    )


def test_publishes_with_head_as_target(tmp_path):
    _seed_packed(tmp_path)
    sha = _init_git(tmp_path)
    bin_dir, gh_log = _install_gh_stub(tmp_path)
    result = _run(tmp_path, _env(tmp_path, bin_dir))
    assert result.returncode == 0, result.stderr

    invocations = gh_log.read_text()
    assert "release create build-2026-05-22-newsha1" in invocations
    assert f"--target {sha}" in invocations
    assert "dist/build-2026-05-22-newsha1.tar.gz" in invocations
    assert "dist/build-2026-05-22-newsha1.description.md" in invocations


def test_fails_when_archive_missing(tmp_path):
    _seed_packed(tmp_path, with_archive=False)
    _init_git(tmp_path)
    bin_dir, _ = _install_gh_stub(tmp_path)
    result = _run(tmp_path, _env(tmp_path, bin_dir))
    assert result.returncode != 0
    assert "archive" in result.stderr.lower()


def test_fails_when_description_missing(tmp_path):
    _seed_packed(tmp_path, with_description=False)
    _init_git(tmp_path)
    bin_dir, _ = _install_gh_stub(tmp_path)
    result = _run(tmp_path, _env(tmp_path, bin_dir))
    assert result.returncode != 0
    assert "description" in result.stderr.lower()


def test_fails_when_gh_missing(tmp_path):
    _seed_packed(tmp_path)
    _init_git(tmp_path)
    result = subprocess.run(
        [sys.executable, "-m", "tools.publish"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={"PATH": "/nonexistent-bin", "PYTHONPATH": str(REPO_ROOT), "HOME": str(tmp_path)},
    )
    assert result.returncode != 0
    assert "gh" in result.stderr.lower()


def test_propagates_gh_failure(tmp_path):
    _seed_packed(tmp_path)
    _init_git(tmp_path)
    bin_dir, _ = _install_gh_stub(tmp_path, returncode=1)
    result = _run(tmp_path, _env(tmp_path, bin_dir))
    assert result.returncode != 0
    assert "gh release create" in result.stderr.lower() or "failed" in result.stderr.lower()
