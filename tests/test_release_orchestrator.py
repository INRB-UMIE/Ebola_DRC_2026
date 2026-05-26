"""Integration tests for the tools.release orchestrator (new flow).

Stubs `gh` (PATH manipulation) and `$EDITOR` (env var). The orchestrator no
longer rebuilds — the workflow does that before calling tools.release — so
tests do not fake tools.build_geojson.
"""

import json
import os
import stat
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


README_TEMPLATE = (
    "# Header\n\n"
    "Last successful build: **OLD** (commit `oldsha`).\n\n"
    "# Current build (2026-01-01)\n\n"
    "prose\n\n"
    "<!-- whats-new:start -->\n"
    "old description\n"
    "<!-- whats-new:end -->\n\n"
    "## Past releases\n\n"
    "<!-- past-releases:start -->\n"
    "| Tag | Date | Summary | Download |\n"
    "|-----|------|---------|----------|\n"
    "<!-- past-releases:end -->\n\n"
    "# Repository layout\n"
)


def _make_stub(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _seed_repo(tmp: Path) -> None:
    (tmp / "build").mkdir()
    (tmp / "build" / "long").mkdir()
    (tmp / "build" / "drc_health_zones.geojson").write_text(
        '{"type":"FeatureCollection","features":[]}'
    )
    (tmp / "build" / "manifest.json").write_text(json.dumps({
        "shapefile": "data/shapefiles/DRC_Health_zones.shp",
        "n_features": 0,
        "built_at": "2026-05-22T10:00:00+00:00",
        "commit": "newsha1",
        "datasets": [],
    }))
    (tmp / "qa").mkdir()
    (tmp / "qa" / "qa_log.csv").write_text("dataset,type,file,status\nfoo,vector,foo.csv,pass\n")
    (tmp / "qa" / "matrix_log.csv").write_text("dataset,file\n")
    (tmp / "README.md").write_text(README_TEMPLATE)
    (tmp / ".gitignore").write_text("bin/\ngh.log\ndist/\n")


def _init_git(tmp: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@e", "-c", "user.name=t", "commit", "-qm", "init"],
        cwd=tmp,
        check=True,
    )


def _install_stubs(tmp: Path, *, editor_body: str = "", gh_body: str | None = None) -> tuple[Path, Path]:
    bin_dir = tmp / "bin"
    bin_dir.mkdir()
    gh_log = tmp / "gh.log"
    default_gh = (
        f"""#!/usr/bin/env bash
echo "$@" >> {gh_log}
if [ "$1" = "release" ] && [ "$2" = "create" ]; then
  echo "https://github.com/example/repo/releases/tag/$3"
fi
exit 0
"""
    )
    _make_stub(bin_dir / "gh", gh_body or default_gh)
    if editor_body:
        _make_stub(bin_dir / "fake-editor", editor_body)
    return bin_dir, gh_log


def _env(tmp: Path, bin_dir: Path, *, editor: Path | None = None) -> dict:
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ.get('PATH', '')}",
        "PYTHONPATH": str(REPO_ROOT),
    }
    if editor is not None:
        env["EDITOR"] = str(editor)
    return env


def _run(tmp: Path, env: dict, *extra_args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "tools.release", *extra_args],
        cwd=tmp,
        capture_output=True,
        text=True,
        env=env,
    )


# ---------- preflight ----------

def test_preflight_fails_when_qa_log_missing(tmp_path):
    _seed_repo(tmp_path)
    (tmp_path / "qa" / "qa_log.csv").unlink()
    bin_dir, _ = _install_stubs(tmp_path)
    result = _run(tmp_path, _env(tmp_path, bin_dir))
    assert result.returncode != 0
    assert "qa" in result.stderr.lower()


def test_preflight_fails_when_qa_log_has_failures(tmp_path):
    _seed_repo(tmp_path)
    (tmp_path / "qa" / "qa_log.csv").write_text(
        "dataset,type,file,status\nfoo,vector,foo.csv,fail\n"
    )
    bin_dir, _ = _install_stubs(tmp_path)
    result = _run(tmp_path, _env(tmp_path, bin_dir))
    assert result.returncode != 0
    assert "fail" in result.stderr.lower()


def test_preflight_fails_when_gh_missing(tmp_path):
    _seed_repo(tmp_path)
    result = subprocess.run(
        [sys.executable, "-m", "tools.release"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={"PATH": "/nonexistent-bin", "PYTHONPATH": str(REPO_ROOT), "HOME": str(tmp_path)},
    )
    assert result.returncode != 0
    assert "gh" in result.stderr.lower()


def test_preflight_fails_on_unrelated_dirty_paths(tmp_path):
    _seed_repo(tmp_path)
    _init_git(tmp_path)
    bin_dir, _ = _install_stubs(tmp_path)
    (tmp_path / "unrelated.txt").write_text("dirty")
    result = _run(tmp_path, _env(tmp_path, bin_dir))
    assert result.returncode != 0
    assert "unrelated" in result.stderr.lower() or "dirty" in result.stderr.lower()


# ---------- happy paths ----------

def test_interactive_editor_release(tmp_path):
    """$EDITOR mode (no flags): full pass publishes current build."""
    _seed_repo(tmp_path)
    _init_git(tmp_path)
    editor_body = (
        "#!/usr/bin/env bash\n"
        "cat > \"$1\" <<EOF\n"
        "# stripped comment\n"
        "Updated cross-border POE counts.\n"
        "EOF\n"
    )
    bin_dir, gh_log = _install_stubs(tmp_path, editor_body=editor_body)
    result = _run(tmp_path, _env(tmp_path, bin_dir, editor=bin_dir / "fake-editor"))
    assert result.returncode == 0, result.stderr

    expected_tag = "build-2026-05-22-newsha1"
    archive = tmp_path / "dist" / f"{expected_tag}.tar.gz"
    assert archive.exists()
    with tarfile.open(archive) as tf:
        names = tf.getnames()
    assert "build/drc_health_zones.geojson" in names
    assert "build/manifest.json" in names
    assert "qa/qa_log.csv" in names

    gh_invocations = gh_log.read_text()
    assert f"release create {expected_tag}" in gh_invocations

    readme = (tmp_path / "README.md").read_text()
    assert expected_tag in readme
    assert "Updated cross-border POE counts." in readme

    assert not (tmp_path / "build" / "DESCRIPTION.md").exists()


def test_description_file_release(tmp_path):
    """--description-file path: read description from a file, do not open $EDITOR."""
    _seed_repo(tmp_path)
    _init_git(tmp_path)
    bin_dir, gh_log = _install_stubs(tmp_path)
    desc = tmp_path / "desc.md"
    desc.write_text("Refreshed Flowminder month.\n")
    result = _run(
        tmp_path,
        _env(tmp_path, bin_dir),
        "--description-file", str(desc), "--non-interactive",
    )
    assert result.returncode == 0, result.stderr
    readme = (tmp_path / "README.md").read_text()
    assert "Refreshed Flowminder month." in readme
    assert "build-2026-05-22-newsha1" in readme


def test_non_interactive_without_description_file_fails(tmp_path):
    _seed_repo(tmp_path)
    _init_git(tmp_path)
    bin_dir, _ = _install_stubs(tmp_path)
    result = _run(tmp_path, _env(tmp_path, bin_dir), "--non-interactive")
    assert result.returncode != 0
    assert "description-file" in result.stderr.lower() or "non-interactive" in result.stderr.lower()


def test_description_file_empty_fails(tmp_path):
    _seed_repo(tmp_path)
    _init_git(tmp_path)
    bin_dir, _ = _install_stubs(tmp_path)
    desc = tmp_path / "desc.md"
    desc.write_text("   \n\n")
    result = _run(
        tmp_path,
        _env(tmp_path, bin_dir),
        "--description-file", str(desc), "--non-interactive",
    )
    assert result.returncode != 0
    assert "empty" in result.stderr.lower() or "description" in result.stderr.lower()
