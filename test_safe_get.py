import unittest
from fda_approvals import safe_get

class TestSafeGet(unittest.TestCase):
    def test_safe_get_valid(self):
        """Test safe_get returns the correct value for valid nested keys."""
        data = {"a": {"b": {"c": 42}}}
        self.assertEqual(safe_get(data, ["a", "b", "c"]), 42)

    def test_safe_get_missing_key(self):
        """Test safe_get returns default value when a key is missing."""
        data = {"a": {"b": {"c": 42}}}
        self.assertEqual(safe_get(data, ["a", "x", "c"], default=0), 0)

    def test_safe_get_empty_dict(self):
        """Test safe_get returns default value for an empty dictionary."""
        data = {}
        self.assertEqual(safe_get(data, ["a", "b", "c"], default=0), 0)

    def test_safe_get_not_dict_intermediate(self):
        """Test safe_get returns default value when an intermediate value is not a dict."""
        data = {"a": {"b": "not_a_dict"}}
        self.assertEqual(safe_get(data, ["a", "b", "c"], default=0), 0)

    def test_safe_get_none_value(self):
        """Test safe_get handles None values properly."""
        data = {"a": {"b": {"c": None}}}
        self.assertEqual(safe_get(data, ["a", "b", "c"], default=0), 0)
        self.assertEqual(safe_get(data, ["a", "b", "c"]), None)

        data2 = {"a": {"b": None}}
        self.assertEqual(safe_get(data2, ["a", "b", "c"], default=0), 0)

    def test_safe_get_default_none(self):
        """Test safe_get returns None by default when a key is missing."""
        data = {"a": {"b": {"c": 42}}}
        self.assertIsNone(safe_get(data, ["a", "x", "c"]))

if __name__ == '__main__':
    unittest.main()
