from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
