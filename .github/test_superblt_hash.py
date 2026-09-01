import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


sys.dont_write_bytecode = True


SCRIPT_PATH = Path(__file__).with_name("superblt_hash.py")


def load_hasher_module():
    spec = importlib.util.spec_from_file_location("kyohud_superblt_hash", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SuperBLTHashTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "A.txt").write_bytes(b"alpha\n")
        (self.root / "sub").mkdir()
        (self.root / "sub" / "b.bin").write_bytes(bytes([0, 1, 2, 255]))
        (self.root / "z.txt").write_bytes(b"")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_file_hashes_match_the_previous_release_tool(self):
        hasher = load_hasher_module()
        expected = {
            "A.txt": "61902235d6019f5ecfcce8eaab1d387c7503412c9c85433f1764a05bdcaf0c00",
            "sub/b.bin": "2208be8e31016d4a02ded2a21776233cae0f4aa3f438528cc03f6eb50c0a446c",
            "z.txt": "cd372fb85148700fa88095e3492d3f9f5beb43e555e5ff26d95f5a6adc36f8e6",
        }
        for relative_path, expected_hash in expected.items():
            with self.subTest(relative_path=relative_path):
                self.assertEqual(hasher.hash_file(self.root / relative_path), expected_hash)

    def test_directory_hash_matches_the_previous_release_tool(self):
        hasher = load_hasher_module()
        self.assertEqual(
            hasher.hash_directory(self.root),
            "62fb07452f9dcfdbae5a3f29b6e27ea28ba1e38aa82e1219918a9342a5a79912",
        )

    def test_cli_prints_only_the_hash_for_workflow_consumption(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), str(self.root)],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.stdout.strip(),
            "62fb07452f9dcfdbae5a3f29b6e27ea28ba1e38aa82e1219918a9342a5a79912",
        )

    def test_cli_rejects_a_missing_path(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), str(self.root / "missing")],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not exist", result.stderr)


if __name__ == "__main__":
    unittest.main()
