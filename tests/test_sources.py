import copy
import unittest
from unittest.mock import patch

import pandas as pd
import requests

from data import (
    _fetch_ecb, _fetch_eurostat, _fetch_eurostat_sdmx, _freshness_error, _normalize_periods,
    _observation_series, _parse_jsonstat, _request,
)


def response(status=200, text="ok", headers=None):
    result = requests.Response()
    result.status_code = status
    result._content = text.encode()
    result._content_consumed = True
    result.headers.update(headers or {})
    return result


class RequestTest(unittest.TestCase):
    @patch("data.time.sleep")
    @patch("data.requests.get")
    def test_timeout_and_503_are_retried_then_recover(self, get, sleep):
        success = response()
        get.side_effect = [requests.ReadTimeout(), response(503), success]
        self.assertIs(_request("https://example.test/data", headers={}), success)
        self.assertEqual(get.call_count, 3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [2, 4])
        self.assertEqual(get.call_args.kwargs["timeout"], (10, 45))

    @patch("data.time.sleep")
    @patch("data.requests.get", side_effect=requests.ReadTimeout())
    def test_persistent_failure_stops_after_three_attempts(self, get, sleep):
        with self.assertRaises(requests.ReadTimeout):
            _request("https://example.test/data", headers={})
        self.assertEqual(get.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    @patch("data.time.sleep")
    @patch("data.requests.get")
    def test_permanent_http_and_tls_errors_are_not_retried(self, get, sleep):
        for failure in (response(400), response(404), requests.exceptions.SSLError()):
            with self.subTest(failure=failure):
                get.reset_mock()
                get.side_effect = [failure]
                with self.assertRaises(requests.RequestException):
                    _request("https://example.test/data", headers={})
                self.assertEqual(get.call_count, 1)
        sleep.assert_not_called()

    @patch("data.time.sleep")
    @patch("data.requests.get")
    def test_retry_after_is_respected(self, get, sleep):
        get.side_effect = [response(429, headers={"Retry-After": "8"}), response()]
        _request("https://example.test/data", headers={})
        sleep.assert_called_once_with(8)

    @patch("data.time.sleep")
    @patch("data.requests.get")
    def test_long_or_unparsed_retry_after_does_not_retry_early(self, get, sleep):
        for value in ("120", "Wed, 21 Oct 2037 07:28:00 GMT"):
            with self.subTest(value=value):
                get.reset_mock()
                get.side_effect = [response(429, headers={"Retry-After": value})]
                with self.assertRaises(requests.HTTPError):
                    _request("https://example.test/data", headers={})
                self.assertEqual(get.call_count, 1)
        sleep.assert_not_called()


def cube():
    # Synthetic parser fixture, never used by the runtime collector.
    return {
        "id": ["geo", "time", "indic"], "size": [1, 2, 2],
        "dimension": {
            "geo": {"category": {"index": {"EA21": 0}}},
            "time": {"category": {"index": {"2026-08": 0, "2026-09": 1}}},
            "indic": {"category": {"index": {"OTHER": 0, "EEI": 1}}},
        },
        "value": {"0": -6, "1": 98, "2": -5, "3": 97},
    }


class JsonstatTest(unittest.TestCase):
    def test_exact_cell_uses_real_dimension_strides(self):
        result = _parse_jsonstat(cube(), {"geo": "EA21", "indic": "EEI"})
        self.assertEqual(result.tolist(), [98, 97])
        self.assertEqual(result.index[-1], pd.Timestamp("2026-09-01"))

    def test_missing_indicator_cannot_be_replaced_by_first_series(self):
        with self.assertRaisesRegex(ValueError, "code demandé absent"):
            _parse_jsonstat(cube(), {"geo": "EA21", "indic": "BS-EEI-I"})

    def test_wrong_singleton_country_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "geo=EA20"):
            _parse_jsonstat(cube(), {"geo": "EA20", "indic": "EEI"})

    def test_unselected_multivalued_dimension_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "non sélectionnée"):
            _parse_jsonstat(cube(), {"geo": "EA21"})

    def test_missing_requested_dimension_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "dimension demandée absente"):
            _parse_jsonstat(cube(), {"indic": "EEI", "unit": "IDX"})

    def test_ecfin_time_dimension_is_supported(self):
        payload = copy.deepcopy(cube())
        payload["id"][1] = "TIME_PERIOD"
        payload["dimension"]["TIME_PERIOD"] = payload["dimension"].pop("time")
        payload["value"] = [-6, 98, -5, 97]
        self.assertEqual(_parse_jsonstat(payload, {"INDIC": "EEI"}).tolist(), [98, 97])

    def test_zero_sized_requested_category_is_rejected(self):
        payload = cube()
        payload["size"][2] = 0
        payload["dimension"]["indic"]["category"]["index"] = {}
        payload["value"] = {}
        with self.assertRaisesRegex(ValueError, "code demandé absent"):
            _parse_jsonstat(payload, {"indic": "EEI"})

    @patch("data._request")
    def test_bad_filter_is_not_followed_by_unfiltered_request(self, request):
        request.return_value.json.return_value = cube()
        with self.assertRaisesRegex(ValueError, "code demandé absent"):
            _fetch_eurostat("dataset", {"indic": "MISSING"})
        request.assert_called_once()


class ObservationTest(unittest.TestCase):
    def test_invalid_duplicate_and_nonfinite_observations_are_rejected(self):
        cases = [
            (["2026-08", "2026-08"], [1, 2]),
            (["invalid"], [1]), (["2026-08"], [float("inf")]),
            (["2026-08"], ["invalid"]),
        ]
        for periods, values in cases:
            with self.subTest(periods=periods, values=values), self.assertRaises(ValueError):
                _observation_series(periods, values)

    def test_missing_observations_are_omitted_not_fabricated(self):
        result = _observation_series(["2026-07", "2026-08", "2026-09"], [1, None, ":"])
        self.assertEqual(result.tolist(), [1])
        self.assertEqual(result.index[-1], pd.Timestamp("2026-07-01"))

    @patch("data._request", return_value=response(text="unexpected,columns\n2026-08,42\n"))
    def test_ecb_schema_drift_is_rejected(self, request):
        with self.assertRaisesRegex(ValueError, "colonnes CSV BCE"):
            _fetch_ecb("FLOW.KEY")

    @patch("data._request")
    def test_sdmx_does_not_multiply_retries_after_server_failure(self, request):
        request.side_effect = requests.HTTPError(response=response(503))
        with self.assertRaises(requests.HTTPError):
            _fetch_eurostat_sdmx("dataset", "KEY")
        request.assert_called_once()

    @patch("data._request")
    def test_sdmx_changes_format_only_when_format_is_rejected(self, request):
        request.side_effect = [requests.HTTPError(response=response(406)),
                               response(text="TIME_PERIOD,OBS_VALUE\n2026-08,42\n")]
        self.assertEqual(_fetch_eurostat_sdmx("dataset", "KEY").tolist(), [42])
        self.assertEqual(request.call_count, 2)

    def test_weekly_dates_use_iso_weeks(self):
        self.assertEqual(_normalize_periods(["2024-W05", "2025-W01"]),
                         ["2024-01-29", "2024-12-30"])

    def test_future_dates_and_nonfinite_computed_values_are_rejected(self):
        future = pd.Series([1.0], index=pd.to_datetime(["2026-10-04"]))
        self.assertIn("future", _freshness_error(future, {"freq": "D"}, "2026-10-03"))
        invalid = pd.Series([float("inf")], index=pd.to_datetime(["2026-10-03"]))
        self.assertIn("non finie", _freshness_error(invalid, {"freq": "D"}, "2026-10-03"))


if __name__ == "__main__":
    unittest.main()
