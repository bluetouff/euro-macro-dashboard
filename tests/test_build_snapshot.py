import re
import unittest
import io
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from build_snapshot import _generated_at, _source_url, build
from catalog import SERIES_CATALOG
from snapshot_contract import SnapshotValidationError


class GeneratedAtContractTest(unittest.TestCase):
    def test_generated_at_is_an_explicit_utc_timestamp(self):
        value = _generated_at()

        self.assertRegex(value, re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"))
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        self.assertEqual(parsed.utcoffset(), timedelta(0))
        self.assertLess(abs(datetime.now(timezone.utc) - parsed), timedelta(seconds=2))

    def test_eei_provenance_points_to_exact_commission_series(self):
        url = _source_url(SERIES_CATALOG["avances"]["EEI"])
        self.assertTrue(url.startswith("https://webgate.ec.europa.eu/ecfin/redisstat/"))
        self.assertIn("INDICATOR=EEI", url)
        self.assertIn("REF_AREA=EA", url)

    @patch("build_snapshot._atomic_write")
    @patch("build_snapshot._source_revision", return_value="worktree")
    @patch("build_snapshot.fetch_all_series", return_value=({}, {"CISS": "timeout"}))
    def test_failed_collection_logs_cause_and_preserves_snapshot(self, fetch, revision, write):
        diagnostic = io.StringIO()
        with redirect_stderr(diagnostic), redirect_stdout(io.StringIO()):
            with self.assertRaises(SnapshotValidationError):
                build()
        self.assertIn("SOURCE_ERROR CISS: timeout", diagnostic.getvalue())
        write.assert_not_called()


if __name__ == "__main__":
    unittest.main()
