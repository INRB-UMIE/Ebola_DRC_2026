# Admin / contributor flow separation + automated releases

## Background

Today the project has one undifferentiated "Contributor flow" (README steps 0–8) that quietly mixes contributor and admin/maintainer responsibilities. The current process has two concrete pain points:

1. **No role enforcement.** Contributors are nominally expected to stop short of merging to `main` and cutting releases, but the docs present everything as one numbered list and nothing prevents a contributor from running `tools.release`.
2. **Merge-conflict friction.** Contributors run `tools.build_geojson` locally and commit the resulting `build/`, `qa/qa_log.csv`, `qa/matrix_log.csv`, `qa/reports/`, and an updated `README.md` "last build" line as part of their PR. When two contributors work in parallel, these timestamped artifacts collide on `git merge origin/main`, forcing rebuilds and replays before a PR can land.

The current `tools.release` script also assumes the "contributor commits a freshly-built `build/`" pattern: it archives whatever is in `build/` as a new GitHub Release, then rebuilds *again* to leave a fresh (still-unreleased) build on `main` for the next call. That asymmetry — `build/` on `main` is always one step ahead of the latest published release — is hard to reason about and incompatible with the cleaner contributor flow proposed below.

## Goals

- Make the contributor / admin split explicit in both docs and tooling.
- Eliminate the timestamped-artifact merge-conflict pain by removing built artifacts from PRs entirely.
- Automate releases so that each merge to `main` that touches data publishes a new GitHub release without admin manual steps.
- Preserve a manual escape hatch (admin can suppress a release or force one) for edge cases.

## Non-goals

- Changing the data contract, QA logic, or build logic (`tools.qa`, `tools.build_geojson` stay as-is).
- Reworking how the dataset folders are structured.
- Adding a separate "staging" or "preview" environment.

## Design

### 1. Role split

**Contributor** owns: adding/updating `data/<dataset>/**`, `data/aliases.csv`, and `tests/`; running `pytest` and `tools.qa` locally; optionally running `tools.build_geojson` locally to sanity-check; opening a PR with a populated `## What's new` section in the PR body.

**Admin** owns: reviewing PRs and merging to `main`. That is the entire admin contribution in the common case. Releases happen automatically via CI after merge.

A contributor's PR diff must touch only:

- `data/**`
- `tests/**` (when relevant)
- Documentation/config files unrelated to releases (e.g. `docs/`, `LICENSE.md`)

A contributor's PR **must not** touch:

- `build/**`
- `qa/qa_log.csv`, `qa/matrix_log.csv`, `qa/reports/**`
- `README.md` "last build" line, "current build" date, "what's new" block, or past-releases table
- `dist/**`

These constraints are documented in the README and reinforced by a PR template checklist; CI is not asked to enforce them mechanically (a noisy false-positive class), but the release workflow only commits these paths itself so contributor-introduced drift will surface during review.

### 2. Repository layout additions

| Path | Purpose |
|---|---|
| `.github/pull_request_template.md` | PR template with a required `## What's new` section + contributor checklist (no `build/`, no `qa/`, no `README.md` touches) |
| `.github/workflows/release.yml` | New release workflow (described below) |
| `.github/workflows/ci.yml` | Existing PR-validation workflow (pytest + `tools.qa`); confirmed not to fire on `build/`, `qa/`, `README.md`, `dist/` self-commits |

### 3. PR template

`.github/pull_request_template.md` contains, at minimum:

```markdown
## What's new

<!-- This section becomes the GitHub Release description and the README "what's new" block. -->
<!-- Write 1–3 sentences describing what changed in this PR from a data/consumer perspective. -->

## Contributor checklist

- [ ] My PR touches only `data/**`, `tests/**`, and unrelated docs.
- [ ] I did NOT commit changes under `build/`, `qa/`, `dist/`, or to the `README.md` "current build" / "past releases" sections.
- [ ] `pytest` and `python -m tools.qa` pass locally.
```

### 4. Release workflow (`.github/workflows/release.yml`)

**Trigger:**

```yaml
on:
  push:
    branches: [main]
    paths:
      - 'data/**'
  workflow_dispatch:
```

`paths: ['data/**']` prevents the workflow from firing on documentation-only commits, README typo fixes, etc. `workflow_dispatch` provides a manual override (e.g. when `tools/**` changes alter build output and an admin wants to publish a new build without a data change).

**Skip marker:** the workflow's first step inspects the HEAD commit message. If it contains the substring `[skip release]`, the workflow exits with success and no release is cut. This handles cases like a typo fix in `data/*/metadata.yaml` that does not warrant a release.

**Job steps (sequential):**

1. Checkout with full history; configure Git LFS; set up Python; install `tools/requirements.txt`.
2. Install GitHub CLI (`gh`) and authenticate using `GITHUB_TOKEN`.
3. Obtain the release description:
   - For `push` triggers: resolve the PR associated with the HEAD commit via `gh api repos/${{ github.repository }}/commits/${{ github.sha }}/pulls` (this API returns PRs containing a given commit, and handles squash-merge cases reliably). Read its `body` field. Extract the section between `## What's new` and the next `## ` header (or end of body). Trim.
   - For `workflow_dispatch` triggers: read from a required workflow input named `description` (one-line for simple cases) or `description_file` (path within the repo for multi-line). At least one must be provided.
   - Write the extracted/provided text to a temporary file.
   - Fail the job if the section is missing/empty or, for push triggers, if no PR can be found for the commit.
4. Run `python -m tools.qa`. Fail-fast if any row in `qa/qa_log.csv` has `status=fail`.
5. Run `python -m tools.build_geojson`.
6. Run `python -m tools.release --description-file <tmp> --non-interactive`.
7. Commit `build/`, `qa/qa_log.csv`, `qa/matrix_log.csv`, `qa/reports/`, `README.md` with a commit message containing both `[skip release]` and `[skip ci]` to prevent recursive triggering.
8. Push to `main` using `GITHUB_TOKEN`.

**Permissions:** the workflow needs `contents: write` on the default `GITHUB_TOKEN` to push the build commit back to `main`.

**Concurrency:** set `concurrency: { group: release-main, cancel-in-progress: false }` so two rapid merges queue rather than racing; each merge gets its own release.

### 5. `tools.release` rework

Current behavior to remove:

- The `_archive_previous_build` step. In the new flow, `build/` on `main` between releases is exactly equal to the last published release, so attempting to re-archive it would fail the existing `gh release view <tag>` precheck. This step is no longer meaningful and is deleted.
- The trailing rebuild (`from tools import build_geojson as _bg; _bg.main()`). In the new flow the workflow runs `tools.build_geojson` explicitly *before* `tools.release`, so the build is already current when `tools.release` runs.

Current behavior to keep:

- Preflight: working-tree-clean allowlist check; `gh` installed check; QA log free of `status=fail`.
- README rewrite: last-build line, current-build date, "what's new" block, prepend a row to the past-releases table.

New CLI flags:

- `--description-file <path>`: read the description from a file instead of prompting via `$EDITOR`. Required when `--non-interactive` is set.
- `--non-interactive`: do not prompt for anything; fail if any prompt would be needed. Used by CI.

New responsibilities:

- Pack the current `build/` (which the workflow rebuilt in the prior step) as a `dist/<tag>.tar.gz` archive, where `<tag> = build-YYYY-MM-DD-<short-sha>` and `<short-sha>` is the HEAD commit short SHA on `main`.
- `gh release create <tag> <archive> --title <tag> --notes-file <description-file>`.
- Update README (last-build line, current-build date, what's-new block, prepend row to past-releases table). The "what's new" block sources directly from the description file passed in; `build/DESCRIPTION.md` is no longer written — it was needed in the old flow to persist the description between the two-step archive/rebuild cycle, which no longer exists.

The interactive `$EDITOR` path is retained for emergency local use by an admin (e.g. when CI is down). When `--description-file` is supplied, `$EDITOR` is skipped entirely.

### 6. README rewrite

Replace the existing "Contributor flow" section with two top-level sections:

**`# Contributor flow`**

Steps:

1. One-time setup (LFS, venv, install).
2. Create `data/<your_dataset>/` with `raw/`, `metadata.yaml`, `process.{py,R}`, `processed/`.
3. Conform to the filename contract; update `data/aliases.csv` if needed.
4. Sync with `main` (`git merge origin/main`) — no longer a source of QA-timestamp conflicts because contributors no longer commit `qa/` outputs.
5. Run `pytest` and `python -m tools.qa` locally.
6. (Optional) Run `python -m tools.build_geojson --skip-readme` locally to sanity-check the merged GeoJSON. **Do not commit the resulting `build/` or `qa/` outputs.**
7. Open a PR. Fill in the `## What's new` section in the PR body — this becomes the release description.

Explicitly call out: PR diffs must not include `build/`, `qa/`, `dist/`, or `README.md` updates.

**`# Admin flow`**

Steps:

1. Review the PR (data diff, CI green, `## What's new` section populated and accurate).
2. Merge to `main`. The release workflow takes over from here.
3. Escape hatches:
   - Include `[skip release]` in the merge commit message to suppress the release for trivial data fixes.
   - Use `workflow_dispatch` from the Actions tab to force a release without a data change (e.g. after a `tools/**` fix).

**`# Release internals`** (new short section)

Document what the release workflow does, where the description comes from, and what files it commits back. This gives consumers/auditors a clear picture without requiring them to read CI YAML.

### 7. Branch protection (configuration, not code)

Recommended GitHub repo settings (documented in the spec, not enforced by this change):

- `main` requires PR before merge.
- `main` requires at least one approving review from an admin/maintainer.
- `main` requires status checks (PR CI) to pass.
- Direct pushes to `main` allowed only for the release workflow's service identity (or via admin override).

## Migration & rollout

1. Land the spec and plan.
2. Implement `tools.release` rework with new CLI flags (keeps backward compat for interactive use).
3. Add the PR template.
4. Add the release workflow.
5. Update README.
6. Configure branch protection on GitHub (manual step by repo admin).
7. Communicate the change to existing contributors.

The first CI-driven release after rollout will publish whatever data is currently on `main` — verify that the resulting tag and README state are correct before declaring the migration complete.

## Open questions

None at design time. Implementation may surface details (e.g. exact `gh pr list` query for finding the PR from a merge commit) that the plan can address.

## Out of scope

- Multi-PR batched releases.
- Pre-release / staging tags.
- Automatic changelog generation from commit history (we use the human-written PR `## What's new` section instead).
- Mechanically enforcing the contributor PR-scope constraint via CI (relies on review + template + the release workflow's own commits as the only source of `build/qa/README` changes).
