import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import streamlit_app


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class StreamlitAppTests(unittest.TestCase):
    def test_get_date_window_uses_months_back(self):
        start, end = streamlit_app.get_date_window(months_back=2, today=dt.date(2026, 3, 6))
        self.assertEqual(start, dt.date(2026, 1, 6))
        self.assertEqual(end, dt.date(2026, 3, 6))

    def test_get_date_window_rejects_invalid_months(self):
        with self.assertRaises(ValueError):
            streamlit_app.get_date_window(months_back=0, today=dt.date(2026, 3, 6))

    def test_fetch_earthquake_counts_paginates(self):
        day1_ts = int(dt.datetime(2026, 1, 1, 1, 0).timestamp() * 1000)
        day2_ts = int(dt.datetime(2026, 1, 2, 1, 0).timestamp() * 1000)
        responses = [
            FakeResponse(
                {
                    "features": [
                        {"properties": {"time": day1_ts}},
                        {"properties": {"time": day1_ts}},
                    ]
                }
            ),
            FakeResponse(
                {
                    "features": [
                        {"properties": {"time": day2_ts}},
                    ]
                }
            ),
        ]

        with patch.object(streamlit_app, "USGS_PAGE_SIZE", 2):
            with patch("streamlit_app.requests.get", side_effect=responses) as mock_get:
                df = streamlit_app.fetch_earthquake_counts(
                    start_date=dt.date(2026, 1, 1),
                    end_date=dt.date(2026, 1, 2),
                    min_magnitude=4.5,
                )

        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(df.loc[df["date"] == dt.date(2026, 1, 1), "earthquakes"].iloc[0], 2)
        self.assertEqual(df.loc[df["date"] == dt.date(2026, 1, 2), "earthquakes"].iloc[0], 1)

    def test_fetch_earthquake_counts_uses_local_fallback(self):
        day1_ts = int(dt.datetime(2026, 1, 1, 12, 0, tzinfo=dt.timezone.utc).timestamp() * 1000)
        day2_ts = int(dt.datetime(2026, 1, 2, 12, 0, tzinfo=dt.timezone.utc).timestamp() * 1000)
        payload = {
            "features": [
                {"properties": {"time": day1_ts, "mag": 4.2}},
                {"properties": {"time": day1_ts, "mag": 5.1}},
                {"properties": {"time": day2_ts, "mag": 4.7}},
            ]
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            fallback_json = Path(tmp_dir) / "usgs_earthquakes_4plus_365d.geojson"
            fallback_json.write_text(json.dumps(payload), encoding="utf-8")
            with patch.object(streamlit_app, "USGS_FALLBACK_PATH", fallback_json):
                with patch("streamlit_app.requests.get", side_effect=Exception("503")):
                    df = streamlit_app.fetch_earthquake_counts(
                        start_date=dt.date(2026, 1, 1),
                        end_date=dt.date(2026, 1, 2),
                        min_magnitude=4.5,
                    )

        self.assertEqual(df.loc[df["date"] == dt.date(2026, 1, 1), "earthquakes"].iloc[0], 1)
        self.assertEqual(df.loc[df["date"] == dt.date(2026, 1, 2), "earthquakes"].iloc[0], 1)

    def test_fetch_earthquake_counts_raises_if_local_fallback_missing(self):
        with patch.object(streamlit_app, "USGS_FALLBACK_PATH", Path("missing_usgs_snapshot.geojson")):
            with patch("streamlit_app.requests.get", side_effect=Exception("503")):
                with self.assertRaises(streamlit_app.DataFetchError):
                    streamlit_app.fetch_earthquake_counts(
                        start_date=dt.date(2026, 1, 1),
                        end_date=dt.date(2026, 1, 2),
                        min_magnitude=4.5,
                    )

    def test_fetch_bitcoin_prices_validates_payload(self):
        with patch("streamlit_app.requests.get", return_value=FakeResponse({})):
            with patch(
                "streamlit_app.load_local_coingecko_prices",
                side_effect=streamlit_app.DataFetchError("fallback failed"),
            ):
                with self.assertRaises(streamlit_app.DataFetchError):
                    streamlit_app.fetch_bitcoin_prices(days=10)

    def test_fetch_bitcoin_prices_uses_local_coingecko_fallback(self):
        now_ms = int(dt.datetime.now().timestamp() * 1000)
        prices = [
            [now_ms - 2 * 86_400_000, 90_000.0],
            [now_ms - 1 * 86_400_000, 91_000.0],
            [now_ms, 92_000.0],
        ]
        payload = {"prices": prices}

        with tempfile.TemporaryDirectory() as tmp_dir:
            fallback_json = Path(tmp_dir) / "coingecko_bitcoin_market_chart_365d.json"
            fallback_json.write_text(json.dumps(payload), encoding="utf-8")
            with patch.object(streamlit_app, "COINGECKO_FALLBACK_PATH", fallback_json):
                with patch("streamlit_app.requests.get", side_effect=Exception("429")):
                    df = streamlit_app.fetch_bitcoin_prices(days=3)

        self.assertFalse(df.empty)
        self.assertIn("date", df.columns)
        self.assertIn("price_usd", df.columns)

    def test_fetch_bitcoin_prices_raises_if_local_fallback_missing(self):
        with patch.object(
            streamlit_app,
            "COINGECKO_FALLBACK_PATH",
            Path("missing_coingecko_snapshot.json"),
        ):
            with patch("streamlit_app.requests.get", side_effect=Exception("429")):
                with self.assertRaises(streamlit_app.DataFetchError):
                    streamlit_app.fetch_bitcoin_prices(days=10)


if __name__ == "__main__":
    unittest.main()
