"""Portable path defaults shared by AAWC development and install tools.

Repository-owned locations are always derived from this file.  CK3 locations
are deliberately external configuration: supply them with a command-line
option or the documented environment variables when the platform default is
not appropriate.
"""
from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MOD_SOURCE_ROOT = ROOT / "mod"
DEPENDENCIES_SOURCE_ROOT = ROOT / "dependencies"
RELEASE_ROOT = ROOT / "release"
EVIDENCE_ROOT = ROOT / "evidence"
PLAYTEST_ROOT = ROOT / "playtest"
CK3_USER_DIR_ENV = "AAWC_CK3_USER_DIR"
CK3_EXECUTABLE_ENV = "AAWC_CK3_EXECUTABLE"


def configured_path(variable: str) -> Path | None:
    """Return a configured external path, or ``None`` when it was not set."""
    value = os.environ.get(variable, "").strip()
    return Path(value).expanduser() if value else None


def default_ck3_user_dir() -> Path:
    """Use the portable Paradox profile convention unless explicitly overridden."""
    return configured_path(CK3_USER_DIR_ENV) or (
        Path.home() / "Documents" / "Paradox Interactive" / "Crusader Kings III"
    )


def default_mod_dir() -> Path:
    return default_ck3_user_dir() / "mod"


def configured_ck3_executable() -> Path | None:
    """CK3 install discovery is intentionally opt-in rather than machine-specific."""
    return configured_path(CK3_EXECUTABLE_ENV)
