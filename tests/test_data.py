import unittest

import pandas as pd

from data import _freshness_error, compute_metrics, compute_predictive_power


class MomentumContractTest(unittest.TestCase):
    def test_one_year_uses_calendar_time_for_daily_data(self):
        index = pd.date_range("2024-07-01", "2025-07-01", freq="D")
        series = pd.Series(range(1, len(index) + 1), index=index, dtype=float)

        metrics = compute_metrics(series, momentum_mode="relative")

        expected = (series.iloc[-1] - series.loc["2024-07-01"]) / series.loc["2024-07-01"] * 100
        self.assertAlmostEqual(metrics["mom_1y"], expected)

    def test_rate_momentum_is_a_point_change(self):
        index = pd.date_range("2022-01-01", periods=14, freq="QS")
        series = pd.Series(range(14), index=index, dtype=float)

        metrics = compute_metrics(series, momentum_mode="delta", unit="%")

        self.assertEqual(metrics["mom_1y"], 4.0)
        self.assertEqual(metrics["mom_unit"], "pp")


class FreshnessContractTest(unittest.TestCase):
    def test_stale_monthly_series_is_rejected(self):
        series = pd.Series(
            range(12), index=pd.date_range("2024-01-01", periods=12, freq="MS"), dtype=float,
        )
        error = _freshness_error(series, {"freq": "M"}, as_of="2026-08-03")
        self.assertIn("périmée", error)
        self.assertIn("2024-12-01", error)

    def test_current_quarterly_series_is_accepted(self):
        series = pd.Series(
            range(12), index=pd.date_range("2023-07-01", periods=12, freq="QS"), dtype=float,
        )
        self.assertIsNone(_freshness_error(series, {"freq": "Q"}, as_of="2026-08-03"))

    def test_event_series_can_declare_a_longer_validity(self):
        series = pd.Series(
            range(12), index=pd.date_range("2025-07-01", periods=12, freq="MS"), dtype=float,
        )
        meta = {"freq": "B", "max_age_days": 550}
        self.assertIsNone(_freshness_error(series, meta, as_of="2026-08-03"))


class BacktestFrequencyContractTest(unittest.TestCase):
    def test_daily_and_monthly_inputs_share_a_monthly_backtest_grid(self):
        index = pd.date_range("2015-01-01", "2025-12-31", freq="D")
        daily = pd.Series(index.to_period("M").astype(int), index=index, dtype=float)
        monthly = daily.resample("MS").last()

        daily_power = compute_predictive_power({"CISS": daily})["CISS"]
        monthly_power = compute_predictive_power({"CISS": monthly})["CISS"]

        self.assertAlmostEqual(daily_power, monthly_power)


if __name__ == "__main__":
    unittest.main()
