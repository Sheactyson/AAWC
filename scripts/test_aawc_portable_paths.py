"""Focused clone-safe path-resolution checks for retained AAWC tools."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import aawc_paths


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
PORTABLE_FILES = (
    SCRIPTS / "aawc_paths.py",
    SCRIPTS / "aawc_controlled_install.py",
    SCRIPTS / "install_agot_alternate_world_compatch.py",
    SCRIPTS / "install_aawc_dependencies_modpack.py",
    SCRIPTS / "build_aawc_release.py",
    SCRIPTS / "build_aawc_dependencies_modpack.py",
    SCRIPTS / "stage_aawc_reforging_stage1_runtime.py",
    SCRIPTS / "generate_aawc_stage2_conditions.py",
    SCRIPTS / "package_ck3_logs.py",
    SCRIPTS / "run_aawc_ck3_background_test.ps1",
    ROOT / "mod" / "AGOT_Alternate_World_Compatch.mod",
    ROOT / "dependencies" / "AAWC_Dependencies_Modpack.mod",
)


class PortablePaths(unittest.TestCase):
    def test_git_first_repository_layout(self) -> None:
        self.assertEqual(aawc_paths.MOD_SOURCE_ROOT, ROOT / "mod")
        self.assertEqual(aawc_paths.DEPENDENCIES_SOURCE_ROOT, ROOT / "dependencies")
        self.assertEqual(aawc_paths.RELEASE_ROOT, ROOT / "release")
        self.assertFalse((ROOT / "versions").exists())

    def test_repository_root_is_derived_after_clone(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            clone = Path(temporary) / "another-machine-checkout"
            clone_scripts = clone / "scripts"
            clone_scripts.mkdir(parents=True)
            shutil.copy2(SCRIPTS / "aawc_paths.py", clone_scripts / "aawc_paths.py")
            probe = clone / "probe.py"
            probe.write_text(
                "import sys\nfrom pathlib import Path\nsys.path.insert(0, str(Path(__file__).parent / 'scripts'))\n"
                "import aawc_paths\nprint(aawc_paths.ROOT)\n",
                encoding="utf-8",
            )
            output = subprocess.check_output([sys.executable, "-B", str(probe)], text=True).strip()
            self.assertEqual(Path(output), clone)

    def test_external_locations_are_configurable(self) -> None:
        prior_userdir = os.environ.get(aawc_paths.CK3_USER_DIR_ENV)
        prior_executable = os.environ.get(aawc_paths.CK3_EXECUTABLE_ENV)
        try:
            os.environ[aawc_paths.CK3_USER_DIR_ENV] = r"D:\Games\CK3 Profile"
            os.environ[aawc_paths.CK3_EXECUTABLE_ENV] = r"D:\Steam\CK3\binaries\ck3.exe"
            self.assertEqual(aawc_paths.default_ck3_user_dir(), Path(r"D:\Games\CK3 Profile"))
            self.assertEqual(aawc_paths.default_mod_dir(), Path(r"D:\Games\CK3 Profile") / "mod")
            self.assertEqual(aawc_paths.configured_ck3_executable(), Path(r"D:\Steam\CK3\binaries\ck3.exe"))
        finally:
            if prior_userdir is None:
                os.environ.pop(aawc_paths.CK3_USER_DIR_ENV, None)
            else:
                os.environ[aawc_paths.CK3_USER_DIR_ENV] = prior_userdir
            if prior_executable is None:
                os.environ.pop(aawc_paths.CK3_EXECUTABLE_ENV, None)
            else:
                os.environ[aawc_paths.CK3_EXECUTABLE_ENV] = prior_executable

    def test_retained_entrypoints_contain_no_current_machine_absolute_path(self) -> None:
        forbidden = ("C:\\Users\\sheac", "E:\\SteamLibrary")
        for path in PORTABLE_FILES:
            text = path.read_text(encoding="utf-8-sig")
            self.assertFalse(any(token in text for token in forbidden), path)

    def test_stage_requires_explicit_ck3_configuration_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "new-stage"
        environment = os.environ.copy()
        environment.pop(aawc_paths.CK3_EXECUTABLE_ENV, None)
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPTS / "stage_aawc_reforging_stage1_runtime.py"),
             "--destination", str(destination)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            env=environment,
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("AAWC_CK3_EXECUTABLE", result.stderr)
        self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
