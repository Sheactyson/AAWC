# AAWC

Development repository for AGOT Alternate World Compatch. The checkout is Git-first: it contains one current AAWC source tree and one current dependency source tree, not a local archive of old releases.

## Current layout

- `mod/` — current AAWC source and transport descriptor (`1.11.3.7`).
- `dependencies/` — current Dependencies source and descriptor (`1.1.2`). Large binary art is tracked with Git LFS.
- `docs/` — authoritative master documentation.
- `evidence/stage2/` — the small retained Stage 2 validation and rendered-continuation records.
- `evidence/stage1-authority/` — the two inputs still required by the retained Stage 1 authority validator.
- `catalogue/stage3/` - authoritative Stage 3 candidate source, schema guide and inert generated artifacts.
- `evidence/stage3/` - hash-verified historical catalogue inputs and focused compiler/package receipts.
- `scripts/` — current packaging, installation, staging, and Stage 1/2 validation tools and the Stage 3 catalogue compiler.
- `release/` — only the current AAWC package and manifest. Large dependency archives belong on GitHub Releases and are ignored locally after publication.
- `archive/pre-cleanup-2026-11-11/` — recovery metadata and restore tooling for the one-time pre-Git snapshot.

The former `versions/`, historical `playtest/`, duplicated extraction, older-stage evidence, and obsolete test/tool trees are not part of the current layout.

## Setup on another PC

Install Git LFS before cloning, then run `git lfs install` and clone normally. Python tools derive repository-owned paths from their own checkout. The default CK3 profile is `%USERPROFILE%\Documents\Paradox Interactive\Crusader Kings III`; set `AAWC_CK3_USER_DIR` when yours differs. Set `AAWC_CK3_EXECUTABLE` for tools that stage or launch CK3.

Focused clone/layout verification:

```powershell
python -X utf8 -B scripts/test_aawc_portable_paths.py
```

## Branches, package, and release

`main` contains only the latest verified packaged build. Development for each B-level version (the first two version components) happens on a matching branch such as `1.11`. The branch is created from the current verified `main` release and tracks `origin/1.11`; do not develop directly on `main`.

To promote a B-level branch: complete the focused validation, update the descriptors and master documentation, package the next `a.b.c.d` release, commit the package/manifest/evidence/docs on that B-level branch, push it and its version tag, then fast-forward or merge that verified release commit into `main` and push `main`. A future B-level line starts only from the then-current verified `main` commit (for example, create `1.12` from the released `main`, configure `origin/1.12`, and develop there). This preserves `main` as the working release while each active B-level line has an isolated development branch.

1. Update both AAWC descriptors and the master documentation for the new version.
2. Run `python -X utf8 -B scripts/build_aawc_release.py`. The builder replaces the prior AAWC artifacts in `release/` so the checkout never accumulates local versions.
3. Run the focused Stage 1/2 checks and exact source/archive/manifest parity verification documented in the master.
4. Commit source, the current package/manifest, evidence, and documentation together on the active B-level branch.
5. Create the release tag, push the branch commit and tag, promote that verified commit to `main`, and push `main`. Attach any intentionally retained large dependency archive to the GitHub Release rather than Git history.

## Historical recovery

The one-time snapshot is commit `46b0dafcb401a5c228bd30649cde43a3723cc960`, branch `archive/pre-cleanup-2026-11-11`, annotated tag `pre-cleanup-2026-11-11`, and the matching GitHub Release. It retains the complete `1.10.x.x` verified baseline, active pre-cleanup work, documentation, tooling, and non-save evidence. Pre-1.10 release folders and machine-local `.ck3` saves were deliberately excluded by user direction. See `archive/pre-cleanup-2026-11-11/README.md` for restoration.

Stage 3 target construction is active for 131 chains / 771 levels. See `catalogue/stage3/CONSTRUCTION_POLICY.md` for derivations, source validation and the separate rendered-verification boundary.
