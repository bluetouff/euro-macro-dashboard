import re
import unittest
from datetime import datetime, timedelta, timezone

from build_snapshot import _generated_at


class GeneratedAtContractTest(unittest.TestCase):
    def test_generated_at_is_an_explicit_utc_timestamp(self):
        value = _generated_at()

        self.assertRegex(value, re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"))
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        self.assertEqual(parsed.utcoffset(), timedelta(0))
        self.assertLess(abs(datetime.now(timezone.utc) - parsed), timedelta(seconds=2))


if __name__ == "__main__":
    unittest.main()
