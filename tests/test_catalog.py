import unittest

from catalog import SERIES_CATALOG, visible_series_count


class CatalogContractTest(unittest.TestCase):
    def test_eurostat_fixed_composition_series_use_ea21(self):
        evolving = {"HICP", "HICP_CORE"}
        for family in SERIES_CATALOG.values():
            for code, meta in family.items():
                if meta.get("source") != "eurostat" or code in evolving:
                    continue
                self.assertEqual(meta["filters"].get("geo"), "EA21", code)

    def test_current_ciss_keys_are_used(self):
        stress = SERIES_CATALOG["stress_systemique"]
        self.assertEqual(stress["CISS"]["key"], "CISS.D.U2.Z0Z.4F.EC.SS_CIN.IDX")
        self.assertEqual(stress["CISS_SOV"]["key"], "CISS.D.U2.Z0Z.4F.EC.SOV_EWN.IDX")
        self.assertEqual(stress["CISS_BM"]["key"], "CISS.D.U2.Z0Z.4F.EC.SS_BMN.CON")

    def test_visible_catalog_has_expected_size(self):
        self.assertGreaterEqual(visible_series_count(), 30)


if __name__ == "__main__":
    unittest.main()
