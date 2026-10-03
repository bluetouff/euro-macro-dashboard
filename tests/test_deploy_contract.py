from pathlib import Path
import configparser
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeploymentContractTest(unittest.TestCase):
    def test_refresh_refuses_an_unattested_revision_before_building(self):
        refresh = (ROOT / "deploy" / "refresh.sh").read_text(encoding="utf-8")

        self.assertIn("L0G_ATTESTED_SHA", refresh)
        self.assertIn("révision Euro non attestée", refresh)
        self.assertLess(
            refresh.index('EUROMACRO_SOURCE_SHA" != "$L0G_ATTESTED_SHA'),
            refresh.index('"$APP_DIR/.venv/bin/python" "$APP_DIR/build_snapshot.py"'),
        )

    def test_service_has_bounded_recovery(self):
        unit = configparser.ConfigParser(interpolation=None)
        unit.read(ROOT / "deploy" / "euromacro-snapshot.service")
        self.assertEqual(unit["Unit"]["StartLimitIntervalSec"], "4h")
        self.assertEqual(unit["Unit"]["StartLimitBurst"], "3")
        self.assertEqual(unit["Service"]["Restart"], "on-failure")
        self.assertEqual(unit["Service"]["RestartSec"], "5min")
        self.assertEqual(unit["Service"]["TimeoutStartSec"], "15min")
        self.assertEqual(unit["Service"]["NoNewPrivileges"], "true")
        self.assertEqual(unit["Service"]["ProtectSystem"], "strict")

    def test_refresh_locks_before_build_or_publication(self):
        refresh = (ROOT / "deploy" / "refresh.sh").read_text(encoding="utf-8")
        self.assertLess(refresh.index("flock -n 9"), refresh.index("build_snapshot.py"))


if __name__ == "__main__":
    unittest.main()
