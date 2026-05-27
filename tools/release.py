"""`python -m tools.release` — pack the current build/ as a release archive and
update README.

In the new flow:
- The release workflow runs `tools.build_geojson` immediately before invoking
  this script, so `build/` already reflects the data on `main`.
- This script does NOT rebuild and does NOT publish a GitHub Release. It only
  packs `dist/<tag>.tar.gz`, writes the description to `dist/<tag>.description.md`,
  and updates README with the (deterministic) release URL.
- After this script runs, the caller commits + pushes the build/qa/README
  changes, then publishes the release via `python -m tools.publish` (or `gh
  release create ... --target <sha>` directly). Splitting the publish from the
  pack lets the release tag point to the commit that contains the build
  artifacts, not the pre-build merge commit.
- Use `--description-file <path>` to provide the release notes non-interactively
  (CI mode). Otherwise the script opens $EDITOR.

Pure helpers live in tools.lib.release.

Run from repo root:
    python -m tools.release                                            # interactive ($EDITOR)
    python -m tools.release --description-file desc.md --non-interactive
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from tools.lib.release import (
    DEFAULT_GITHUB_REPO,
    build_tag,
    format_last_build_line,
    pack_archive,
    render_editor_template,
    rewrite_readme,
    strip_editor_comments,
)


REPO_ROOT = Path.cwd()
QA_LOG = REPO_ROOT / "qa" / "qa_log.csv"
MATRIX_LOG = REPO_ROOT / "qa" / "matrix_log.csv"
BUILD_DIR = REPO_ROOT / "build"
MANIFEST = BUILD_DIR / "manifest.json"
README = REPO_ROOT / "README.md"
DIST_DIR = REPO_ROOT / "dist"

ALLOWLIST_PREFIXES = (
    "build/",
    "qa/qa_log.csv",
    "qa/matrix_log.csv",
    "qa/reports/",
    "README.md",
    "dist/",
)


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def _preflight(description_file: str | None = None) -> int:
    if not QA_LOG.exists():
        _eprint(f"qa log not found at {QA_LOG}; run `python -m tools.qa` first.")
        return 2
    with QA_LOG.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("status") == "fail":
                _eprint(
                    "qa log contains failures — resolve them and re-run "
                    "`python -m tools.qa` before releasing."
                )
                return 2
    dirty = _git_dirty_paths()
    allowlist = ALLOWLIST_PREFIXES
    if description_file:
        try:
            rel = str(Path(description_file).resolve().relative_to(REPO_ROOT.resolve()))
            allowlist = ALLOWLIST_PREFIXES + (rel,)
        except ValueError:
            pass
    unrelated = [p for p in dirty if not any(p.startswith(pre) for pre in allowlist)]
    if unrelated:
        _eprint(
            "working tree has unrelated uncommitted changes; commit or stash them first:\n"
            + "\n".join(f"  {p}" for p in unrelated)
        )
        return 2
    return 0


def _git_dirty_paths() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    paths: list[str] = []
    for line in result.stdout.splitlines():
        path = line[3:].split(" -> ", 1)[-1].strip()
        if path:
            paths.append(path)
    return paths


def _resolve_description(args: argparse.Namespace) -> str:
    if args.description_file:
        body = Path(args.description_file).read_text(encoding="utf-8").strip()
        if not body:
            _eprint(
                f"description file {args.description_file} is empty after trimming; aborting."
            )
            sys.exit(2)
        return body
    if args.non_interactive:
        _eprint("--non-interactive requires --description-file; aborting.")
        sys.exit(2)
    editor = os.environ.get("EDITOR", "vi")
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as f:
            f.write(render_editor_template())
            tmp_path = Path(f.name)
        subprocess.run([editor, str(tmp_path)], check=True)
        raw = tmp_path.read_text()
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
    body = strip_editor_comments(raw)
    if not body:
        _eprint("description is required (empty after stripping comments); aborting.")
        sys.exit(2)
    return body


def release_url(tag: str, github_repo: str = DEFAULT_GITHUB_REPO) -> str:
    return f"https://github.com/{github_repo}/releases/tag/{tag}"


def _pack_archive(description: str) -> tuple[str, str]:
    """Pack build/ to dist/<tag>.tar.gz and persist the description alongside it.

    Returns (tag, url). The URL is the deterministic GitHub Release URL — the
    release itself is published later by `tools.publish` once the build commit
    has been pushed.
    """
    manifest = json.loads(MANIFEST.read_text())
    tag = build_tag(manifest["built_at"], manifest["commit"])

    out_path = DIST_DIR / f"{tag}.tar.gz"
    members: list[tuple[Path, str]] = [
        (BUILD_DIR / "drc_health_zones.geojson", "build/drc_health_zones.geojson"),
        (BUILD_DIR / "long", "build/long"),
        (BUILD_DIR / "manifest.json", "build/manifest.json"),
        (QA_LOG, "qa/qa_log.csv"),
        (MATRIX_LOG, "qa/matrix_log.csv"),
    ]
    pack_archive(members, out_path)

    description_path = DIST_DIR / f"{tag}.description.md"
    description_path.write_text(description, encoding="utf-8")

    url = release_url(tag)
    _eprint(f"✓ Packed {out_path}")
    _eprint(f"✓ Wrote {description_path}")
    return tag, url


def _update_readme(tag: str, url: str, description: str) -> None:
    manifest = json.loads(MANIFEST.read_text())
    built_at = manifest["built_at"]
    short_sha = manifest["commit"]
    current_date = built_at.split("T", 1)[0]

    try:
        head_full = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT),
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        head_full = ""

    last_build_line = format_last_build_line(
        built_at=built_at,
        commit_short=short_sha,
        head_full_sha=head_full,
    )
    release_date = tag.split("-", 1)[1].rsplit("-", 1)[0]
    summary_line = description.strip().splitlines()[0]
    past_release_row = (
        f"| [`{tag}`]({url}) | {release_date} | {summary_line} | [release]({url}) |"
    )

    readme = README.read_text()
    readme = rewrite_readme(
        readme,
        last_build_line=last_build_line,
        current_build_date=current_date,
        whats_new=description,
        past_release_row=past_release_row,
    )
    README.write_text(readme, encoding="utf-8")
    _eprint("✓ Updated README.md")


def main() -> int:
    parser = argparse.ArgumentParser(prog="tools.release")
    parser.add_argument(
        "--description-file",
        type=str,
        default=None,
        help="Path to a file containing the release description (skips $EDITOR).",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Fail instead of prompting. Requires --description-file.",
    )
    args = parser.parse_args()

    rc = _preflight(description_file=args.description_file)
    if rc != 0:
        return rc

    description = _resolve_description(args)
    tag, url = _pack_archive(description)
    _update_readme(tag, url, description)

    _eprint("")
    _eprint("Next: review the changes, then")
    _eprint("  git add build/ qa/qa_log.csv qa/matrix_log.csv qa/reports/ README.md")
    _eprint("  git commit -m \"New build YYYY-MM-DD\"")
    _eprint("  git push")
    _eprint("  python -m tools.publish   # creates the GitHub Release pointing at the build commit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
