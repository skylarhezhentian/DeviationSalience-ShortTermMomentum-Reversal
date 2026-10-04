"""Regression checks for the provenance of reused test results."""
from pathlib import Path
import tempfile
import unittest

from scripts.validate_outputs import unittest_cache_identity


class ValidationCacheTests(unittest.TestCase):
    def test_script_and_dependency_changes_invalidate_signature(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            script = root / "scripts" / "helper.py"
            requirements = root / "requirements-tested.txt"
            script.write_text("answer = 1\n")
            requirements.write_text("numpy==1.26.0\n")
            first, environment = unittest_cache_identity(root)
            script.write_text("answer = 2\n")
            second, _ = unittest_cache_identity(root)
            self.assertNotEqual(first["scripts/helper.py"], second["scripts/helper.py"])
            requirements.write_text("numpy==2.4.0\n")
            third, _ = unittest_cache_identity(root)
            self.assertNotEqual(second["requirements-tested.txt"], third["requirements-tested.txt"])
            self.assertIn("executable", environment)
            self.assertIn("version", environment)
            self.assertIn("numpy", environment["packages"])

    def test_bundled_sample_changes_invalidate_signature(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sample = root / "data" / "sample"
            sample.mkdir(parents=True)
            fixture = sample / "fixture.parquet"
            fixture.write_bytes(b"first fixture")
            first, _ = unittest_cache_identity(root)
            fixture.write_bytes(b"different fixture")
            second, _ = unittest_cache_identity(root)
            self.assertNotEqual(first["data/sample/fixture.parquet"], second["data/sample/fixture.parquet"])


if __name__ == "__main__":
    unittest.main()
