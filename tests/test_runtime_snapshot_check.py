import json
import os
import tempfile
import unittest

from scripts.check_runtime_snapshot import check_snapshot_against_config, main


def _write_json(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh)


SYNTHETIC_SNAPSHOT = {
    "_provenance": {"type": "synthetic capture", "environment": "SIT"},
    "observed": {
        "environment": "SIT",
        "gateway_base_url": "http://carrier-gateway.sit.internal.invalid",
        "gateway_timeout_ms": 2000,
        "gateway_retry_count": 2,
        "feature_flags": {"express_service_enabled": False},
    },
}

SYNTHETIC_CONFIG = {
    "environment": "SIT",
    "api": {"base_url": "http://parcelflow.sit.internal.invalid", "port": 8102},
    "gateway": {
        "base_url": "http://carrier-gateway.sit.internal.invalid",
        "timeout_ms": 2000,
        "retry_count": 2,
        "fallback_enabled": True,
        "simulation_enabled": True,
    },
    "feature_flags": {"express_service_enabled": False},
    "roles": {
        "quote_allowed_roles": ["customer", "ops", "admin"],
        "booking_allowed_roles": ["customer", "ops", "admin"],
        "dispatch_allowed_roles": ["ops", "admin"],
    },
    "secrets": {"gateway_api_key_ref": "secret://parcelflow/sit/gateway-api-key"},
}


class RuntimeSnapshotCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.snapshot_path = os.path.join(self.tmpdir.name, "snapshot.json")
        self.config_path = os.path.join(self.tmpdir.name, "config.json")

    def test_matching_snapshot_and_config_report_no_differences(self):
        _write_json(self.snapshot_path, SYNTHETIC_SNAPSHOT)
        _write_json(self.config_path, SYNTHETIC_CONFIG)

        report = check_snapshot_against_config(self.snapshot_path, self.config_path)

        self.assertEqual(report["differences"], [])
        self.assertTrue(report["match"])

    def test_mismatched_field_is_reported_with_both_values(self):
        snapshot = json.loads(json.dumps(SYNTHETIC_SNAPSHOT))
        snapshot["observed"]["gateway_retry_count"] = 5
        _write_json(self.snapshot_path, snapshot)
        _write_json(self.config_path, SYNTHETIC_CONFIG)

        report = check_snapshot_against_config(self.snapshot_path, self.config_path)

        self.assertFalse(report["match"])
        self.assertEqual(len(report["differences"]), 1)
        diff = report["differences"][0]
        self.assertEqual(diff["field"], "gateway_retry_count")
        self.assertEqual(diff["snapshot_value"], 5)
        self.assertEqual(diff["config_value"], 2)

    def test_report_never_contains_secret_references(self):
        _write_json(self.snapshot_path, SYNTHETIC_SNAPSHOT)
        _write_json(self.config_path, SYNTHETIC_CONFIG)

        report = check_snapshot_against_config(self.snapshot_path, self.config_path)

        serialized = json.dumps(report)
        self.assertNotIn("secret://", serialized)
        self.assertNotIn("gateway_api_key_ref", serialized)

    def test_main_exits_zero_on_match(self):
        _write_json(self.snapshot_path, SYNTHETIC_SNAPSHOT)
        _write_json(self.config_path, SYNTHETIC_CONFIG)

        exit_code = main([self.snapshot_path, self.config_path])

        self.assertEqual(exit_code, 0)

    def test_main_exits_one_on_mismatch(self):
        snapshot = json.loads(json.dumps(SYNTHETIC_SNAPSHOT))
        snapshot["observed"]["gateway_timeout_ms"] = 9999
        _write_json(self.snapshot_path, snapshot)
        _write_json(self.config_path, SYNTHETIC_CONFIG)

        exit_code = main([self.snapshot_path, self.config_path])

        self.assertEqual(exit_code, 1)

    def test_main_exits_two_on_invalid_input(self):
        with open(self.snapshot_path, "w", encoding="utf-8") as fh:
            fh.write("{not valid json")
        _write_json(self.config_path, SYNTHETIC_CONFIG)

        exit_code = main([self.snapshot_path, self.config_path])

        self.assertEqual(exit_code, 2)

    def test_main_exits_two_on_missing_file(self):
        _write_json(self.config_path, SYNTHETIC_CONFIG)

        exit_code = main([os.path.join(self.tmpdir.name, "missing.json"), self.config_path])

        self.assertEqual(exit_code, 2)


if __name__ == "__main__":
    unittest.main()
