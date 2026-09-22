"""Release-contract tests: strict SemVer version + exact tag match.

Covers the cases required by AGENTS.md:
  - v1.0.0 is accepted when mod.txt says "1.0.0".
  - r84, 1.0.0, V1.0.0, v1.0, v1.0.0-rc1, v01.0.0 are all rejected.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True

SCRIPT_PATH = Path(__file__).with_name("validate_release_version.py")


def load_validator():
    spec = importlib.util.spec_from_file_location(
        "kyohud_validate_release_version", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_mod_txt(tmp: Path, version: str) -> Path:
    path = tmp / "mod.txt"
    path.write_text(
        json.dumps(
            {
                "name": "KyoHUD - Killfeed & Combat Score",
                "version": version,
            }
        ),
        encoding="utf-8",
    )
    return path


class ModVersionValidationTests(unittest.TestCase):
    """mod.txt version must be strict SemVer."""

    def setUp(self):
        self.validator = load_validator()

    def test_accepts_canonical_v1(self):
        ok, _ = self.validator.validate_mod_version("1.0.0")
        self.assertTrue(ok)

    def test_accepts_canonical_zero_components(self):
        ok, _ = self.validator.validate_mod_version("0.0.0")
        self.assertTrue(ok)

    def test_accepts_large_components(self):
        ok, _ = self.validator.validate_mod_version("12.34.56")
        self.assertTrue(ok)

    def test_rejects_leading_zero_on_major(self):
        ok, msg = self.validator.validate_mod_version("01.0.0")
        self.assertFalse(ok)
        self.assertIn("SemVer", msg)

    def test_rejects_leading_zero_on_minor(self):
        ok, _ = self.validator.validate_mod_version("1.00.0")
        self.assertFalse(ok)

    def test_rejects_leading_zero_on_patch(self):
        ok, _ = self.validator.validate_mod_version("1.0.00")
        self.assertFalse(ok)

    def test_rejects_prerelease_suffix(self):
        ok, _ = self.validator.validate_mod_version("1.0.0-rc1")
        self.assertFalse(ok)

    def test_rejects_build_metadata(self):
        ok, _ = self.validator.validate_mod_version("1.0.0+build")
        self.assertFalse(ok)

    def test_rejects_two_components(self):
        ok, _ = self.validator.validate_mod_version("1.0")
        self.assertFalse(ok)

    def test_rejects_four_components(self):
        ok, _ = self.validator.validate_mod_version("1.0.0.0")
        self.assertFalse(ok)

    def test_rejects_empty(self):
        ok, _ = self.validator.validate_mod_version("")
        self.assertFalse(ok)

    def test_rejects_legacy_rN(self):
        ok, _ = self.validator.validate_mod_version("25")
        self.assertFalse(ok)

    def test_rejects_non_string(self):
        ok, _ = self.validator.validate_mod_version(25)  # type: ignore[arg-type]
        self.assertFalse(ok)


class TagValidationTests(unittest.TestCase):
    """Tag must equal 'v' + mod.version and itself be strict SemVer."""

    def setUp(self):
        self.validator = load_validator()

    def test_accepts_matching_v_prefix(self):
        ok, _ = self.validator.validate_tag("v1.0.0", "1.0.0")
        self.assertTrue(ok)

    def test_rejects_mismatched_version(self):
        ok, msg = self.validator.validate_tag("v1.0.1", "1.0.0")
        self.assertFalse(ok)
        self.assertIn("does not match", msg)

    def test_rejects_missing_v_prefix(self):
        # 1.0.0 without the leading 'v' — required rejection case.
        ok, _ = self.validator.validate_tag("1.0.0", "1.0.0")
        self.assertFalse(ok)

    def test_rejects_uppercase_v(self):
        # V1.0.0 — required rejection case.
        ok, _ = self.validator.validate_tag("V1.0.0", "1.0.0")
        self.assertFalse(ok)

    def test_rejects_legacy_rN_tag(self):
        # r84 — required rejection case.
        ok, _ = self.validator.validate_tag("r84", "84")
        self.assertFalse(ok)

    def test_rejects_truncated_tag(self):
        # v1.0 — required rejection case.
        ok, _ = self.validator.validate_tag("v1.0", "1.0")
        self.assertFalse(ok)

    def test_rejects_prerelease_tag(self):
        # v1.0.0-rc1 — required rejection case.
        ok, _ = self.validator.validate_tag("v1.0.0-rc1", "1.0.0-rc1")
        self.assertFalse(ok)

    def test_rejects_leading_zero_in_tag(self):
        # v01.0.0 — required rejection case.
        ok, _ = self.validator.validate_tag("v01.0.0", "01.0.0")
        self.assertFalse(ok)

    def test_rejects_empty_tag(self):
        ok, _ = self.validator.validate_tag("", "1.0.0")
        self.assertFalse(ok)


class EndToEndCLITests(unittest.TestCase):
    """CLI accepts valid pairs and rejects invalid ones."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, tag: str, version: str) -> subprocess.CompletedProcess:
        mod_path = write_mod_txt(self.tmp_path, version)
        return subprocess.run(
            [sys.executable, str(SCRIPT_PATH), tag, str(mod_path)],
            capture_output=True,
            text=True,
        )

    def test_cli_accepts_valid_pair(self):
        result = self.run_cli("v1.0.0", "1.0.0")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ok", result.stdout)

    def test_cli_rejects_r84(self):
        result = self.run_cli("r84", "84")
        self.assertNotEqual(result.returncode, 0)

    def test_cli_rejects_bare_version(self):
        result = self.run_cli("1.0.0", "1.0.0")
        self.assertNotEqual(result.returncode, 0)

    def test_cli_rejects_uppercase_v(self):
        result = self.run_cli("V1.0.0", "1.0.0")
        self.assertNotEqual(result.returncode, 0)

    def test_cli_rejects_truncated(self):
        result = self.run_cli("v1.0", "1.0")
        self.assertNotEqual(result.returncode, 0)

    def test_cli_rejects_prerelease(self):
        result = self.run_cli("v1.0.0-rc1", "1.0.0-rc1")
        self.assertNotEqual(result.returncode, 0)

    def test_cli_rejects_leading_zero(self):
        result = self.run_cli("v01.0.0", "01.0.0")
        self.assertNotEqual(result.returncode, 0)

    def test_cli_rejects_mismatch(self):
        result = self.run_cli("v1.0.1", "1.0.0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not match", result.stderr)

    def test_cli_rejects_legacy_mod_version(self):
        result = self.run_cli("r25", "25")
        self.assertNotEqual(result.returncode, 0)

    def test_cli_reports_missing_mod_file(self):
        missing = self.tmp_path / "no-such-mod.txt"
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "v1.0.0", str(missing)],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mod.txt", result.stderr.lower())


class RealModTxtTests(unittest.TestCase):
    """The actual mod.txt in the repository must be accepted as v1.0.0."""

    def test_repository_mod_txt_is_valid_semver(self):
        validator = load_validator()
        repo_root = Path(__file__).resolve().parent.parent
        mod_txt = repo_root / "mod.txt"
        if not mod_txt.exists():
            self.skipTest("mod.txt not found next to .github/")
        mod_version = validator.read_mod_version(mod_txt)
        ok, msg = validator.validate_mod_version(mod_version)
        self.assertTrue(ok, msg)

    def test_repository_mod_txt_matches_derived_tag(self):
        validator = load_validator()
        repo_root = Path(__file__).resolve().parent.parent
        mod_txt = repo_root / "mod.txt"
        if not mod_txt.exists():
            self.skipTest("mod.txt not found next to .github/")
        mod_version = validator.read_mod_version(mod_txt)
        ok, msg = validator.validate_tag("v" + mod_version, mod_version)
        self.assertTrue(ok, msg)


if __name__ == "__main__":
    unittest.main()
