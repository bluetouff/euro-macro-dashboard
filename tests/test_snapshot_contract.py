import copy
import unittest

from snapshot_contract import SnapshotValidationError, validate_snapshot


def valid_snapshot():
    required = ["CISS", "HICP", "UNEMP", "EEI", "ESI"]
    codes = required + [f"X{i}" for i in range(15)]
    indicators = [{
        "code": code,
        "as_of": "2026-07-01",
        "source_url": "https://example.test/source",
    } for code in codes]
    return {
        "generated_at": "2026-08-03T10:00:00Z",
        "source_sha": "a" * 40,
        "global_score": 42.0,
        "quality": {"active": 20, "expected": 20},
        "counts": {"total": 20},
        "families": [{"indicators": indicators}],
        "errors": {},
        "error_sources": {},
    }


class SnapshotContractTest(unittest.TestCase):
    def test_valid_snapshot_passes(self):
        snapshot = valid_snapshot()
        self.assertIs(validate_snapshot(snapshot), snapshot)

    def test_missing_critical_indicator_fails_closed(self):
        snapshot = valid_snapshot()
        snapshot["families"][0]["indicators"][0]["code"] = "OTHER"

        with self.assertRaisesRegex(SnapshotValidationError, "critiques absents"):
            validate_snapshot(snapshot)

    def test_untraceable_revision_is_rejected(self):
        snapshot = copy.deepcopy(valid_snapshot())
        snapshot["source_sha"] = "unknown"

        with self.assertRaisesRegex(SnapshotValidationError, "source_sha"):
            validate_snapshot(snapshot)


if __name__ == "__main__":
    unittest.main()
