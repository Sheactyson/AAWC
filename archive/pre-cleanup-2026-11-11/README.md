# AAWC pre-cleanup snapshot

This directory is the recovery index for the complete AAWC workspace immediately before the Git-backed cleanup. The Git commit and tag preserve the manifest and recovery tooling; the associated GitHub Release stores the segmented `tar.gz` payload.

The snapshot deliberately excludes Git's own `.git` database, the tool-created empty root `lfs` directory, this recovery-index directory (which is stored directly in the tagged commit), pre-1.10 release directories (`versions/1.9*`), and machine-local CK3 saves (`*.ck3`). The latter two exclusions follow the user's explicit archival-policy update. Every retained pre-cleanup file—including the complete 1.10.x.x line, active 1.11.x.x work, master documentation, source, scripts, and non-save evidence—is listed by path, byte length, modification time, and SHA-256 in `snapshot-manifest.json`.

This is a one-time safety net. The post-snapshot repository is intended to contain only the current mod work, not a growing `versions/` directory; Git history and release tags/assets replace local version-directory accumulation.

Snapshot identity:

- Tag: `pre-cleanup-2026-11-11`
- Snapshot commit: `46b0dafcb401a5c228bd30649cde43a3723cc960`
- Archival branch: `archive/pre-cleanup-2026-11-11`
- Published release: `https://github.com/Sheactyson/AAWC/releases/tag/pre-cleanup-2026-11-11` (ID `442051750`)
- Retained files: 27,340 across 7,900 directories
- Retained logical size: 61.111 GiB
- Unique payload files: 8,284
- Unique payload size before compression: 35.368 GiB
- Release payload: 10 ordered parts totaling 18.074 GiB
- `snapshot-manifest.json` SHA-256: `86255f7dddcc33149fa8cc661687377f7bd2527d0abb8625e159b9cef824a1bd`
- `release-assets.json` SHA-256: `d6e4aec4ad4a9716e45b799d3233898a8b734328929c35cf01f95e011d536636`
- Payload path-list SHA-256: `7a31735ac3c23b0919491fe017d832d2a1009da12302d8d21caefac4de480a76`

All 10 published assets were re-inventoried through the GitHub API in `uploaded` state. Their remote byte lengths and GitHub-computed SHA-256 digests exactly match `release-assets.json`. Remote `main`, the archival branch, and the annotated tag were created without force from an empty repository.

## Restore

1. Check out the tagged recovery index: `git checkout pre-cleanup-2026-11-11`.
2. Download all 10 `aawc-pre-cleanup-2026-11-11.tar.gz.part-*` assets from the associated Release into one directory.
3. Compare every downloaded part with `release-assets.json`.
4. Run `./archive/pre-cleanup-2026-11-11/Restore-AAWCPreCleanupSnapshot.ps1 -AssetDirectory <download-directory> -Destination <empty-destination> -Verify`.

The restore script concatenates the ordered parts, extracts the representative payload files, reconstructs duplicate paths from the content map, restores recorded modification times, and—when `-Verify` is supplied—checks every restored file's length and SHA-256.
