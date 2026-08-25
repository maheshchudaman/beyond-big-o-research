import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DatasetManifestTests(unittest.TestCase):
    def test_generated_files_match_manifest(self):
        manifest_path = ROOT / "data/generated/manifest.json"
        if not manifest_path.exists():
            self.skipTest("Generate datasets before validating their manifest")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertTrue(manifest)
        for entry in manifest:
            path = ROOT / "data/generated" / entry["file"]
            self.assertTrue(path.exists())
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), entry["sha256"])


if __name__ == "__main__":
    unittest.main()
