import unittest

from parcelflow import auth
from parcelflow.models import AuthorizationError


class AuthTests(unittest.TestCase):
    def test_allowed_role_passes(self):
        auth.require_role("ops", allowed_roles=("ops", "admin"))  # no raise

    def test_disallowed_role_raises(self):
        with self.assertRaises(AuthorizationError):
            auth.require_role("customer", allowed_roles=("ops", "admin"))

    def test_missing_role_header_raises(self):
        with self.assertRaises(AuthorizationError):
            auth.require_role(None, allowed_roles=("ops", "admin"))

    def test_unknown_role_name_raises(self):
        with self.assertRaises(AuthorizationError):
            auth.require_role("superuser", allowed_roles=("ops", "admin"))

    def test_is_allowed_returns_bool_without_raising(self):
        self.assertTrue(auth.is_allowed("ops", allowed_roles=("ops", "admin")))
        self.assertFalse(auth.is_allowed("customer", allowed_roles=("ops", "admin")))


if __name__ == "__main__":
    unittest.main()
