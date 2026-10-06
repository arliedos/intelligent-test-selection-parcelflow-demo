import json
import os
import tempfile
import unittest

from parcelflow import config


class ConfigLoadingTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(lambda: None)

    def _write(self, name, payload):
        path = os.path.join(self.tmpdir, f"{name}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        return path

    def _valid_payload(self, environment="ST"):
        return {
            "environment": environment,
            "api": {"base_url": "http://parcelflow.st.internal.invalid", "port": 8101},
            "gateway": {
                "base_url": "http://carrier-gateway.st.internal.invalid",
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
            "secrets": {"gateway_api_key_ref": "secret://parcelflow/st/gateway-api-key"},
        }

    def test_loads_valid_config_for_known_environment(self):
        path = self._write("st", self._valid_payload("ST"))
        cfg = config.load_config_file(path)
        self.assertEqual(cfg.environment, "ST")
        self.assertEqual(cfg.gateway_retry_count, 2)
        self.assertFalse(cfg.express_service_enabled)

    def test_rejects_unknown_environment_name(self):
        path = self._write("bogus", self._valid_payload("PRODBOGUS"))
        with self.assertRaises(config.ConfigValidationError):
            config.load_config_file(path)

    def test_rejects_missing_required_key(self):
        payload = self._valid_payload("ST")
        del payload["gateway"]
        path = self._write("broken", payload)
        with self.assertRaises(config.ConfigValidationError):
            config.load_config_file(path)

    def test_rejects_non_integer_retry_count(self):
        payload = self._valid_payload("ST")
        payload["gateway"]["retry_count"] = "two"
        path = self._write("broken2", payload)
        with self.assertRaises(config.ConfigValidationError):
            config.load_config_file(path)

    def test_rejects_unknown_role_in_allowed_roles(self):
        payload = self._valid_payload("ST")
        payload["roles"]["quote_allowed_roles"] = ["customer", "superuser"]
        path = self._write("broken3", payload)
        with self.assertRaises(config.ConfigValidationError):
            config.load_config_file(path)

    def test_error_message_never_includes_secret_reference_value(self):
        payload = self._valid_payload("ST")
        payload["gateway"]["retry_count"] = "two"
        secret_value = "secret://parcelflow/st/gateway-api-key"
        payload["secrets"]["gateway_api_key_ref"] = secret_value
        path = self._write("broken4", payload)
        try:
            config.load_config_file(path)
            self.fail("expected ConfigValidationError")
        except config.ConfigValidationError as exc:
            self.assertNotIn(secret_value, str(exc))

    def test_load_environment_resolves_known_environment_from_directory(self):
        env_dir = tempfile.mkdtemp()
        self._write_into(env_dir, "sit", self._valid_payload("SIT"))
        cfg = config.load_environment("SIT", config_dir=env_dir)
        self.assertEqual(cfg.environment, "SIT")

    def test_load_environment_rejects_unknown_environment(self):
        env_dir = tempfile.mkdtemp()
        with self.assertRaises(config.ConfigValidationError):
            config.load_environment("NOPE", config_dir=env_dir)

    def _write_into(self, directory, name, payload):
        path = os.path.join(directory, f"{name}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        return path


if __name__ == "__main__":
    unittest.main()
