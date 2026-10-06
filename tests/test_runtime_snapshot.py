import json
import os
import unittest

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
SNAPSHOT_PATH = os.path.join(REPO_ROOT, "snapshots", "sit-runtime-snapshot.json")

REQUIRED_OBSERVED_FIELDS = (
    "environment",
    "gateway_base_url",
    "gateway_timeout_ms",
    "gateway_retry_count",
    "feature_flags",
)


class RuntimeSnapshotStructureTests(unittest.TestCase):
    """Validates the shape and provenance of the committed snapshot fixture.

    This is not a live-environment equality gate: `scripts/check_runtime_snapshot.py`
    is the operational tool for comparing a snapshot against repository config.
    """

    def setUp(self):
        with open(SNAPSHOT_PATH, "r", encoding="utf-8") as fh:
            self.snapshot = json.load(fh)

    def test_snapshot_declares_synthetic_provenance(self):
        provenance = self.snapshot["_provenance"]
        self.assertEqual(provenance["type"], "synthetic capture")
        self.assertIn("environment", provenance)

    def test_snapshot_has_required_observed_fields(self):
        observed = self.snapshot["observed"]
        for field_name in REQUIRED_OBSERVED_FIELDS:
            self.assertIn(field_name, observed)
        self.assertIn("express_service_enabled", observed["feature_flags"])

    def test_snapshot_observed_field_types(self):
        observed = self.snapshot["observed"]
        self.assertIsInstance(observed["gateway_base_url"], str)
        self.assertIsInstance(observed["gateway_timeout_ms"], int)
        self.assertIsInstance(observed["gateway_retry_count"], int)
        self.assertIsInstance(observed["feature_flags"]["express_service_enabled"], bool)

    def test_snapshot_contains_no_secret_references(self):
        serialized = json.dumps(self.snapshot)
        self.assertNotIn("secret://", serialized)


if __name__ == "__main__":
    unittest.main()
