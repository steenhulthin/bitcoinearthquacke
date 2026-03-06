import datetime as dt
import unittest
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

    def test_fetch_bitcoin_prices_validates_payload(self):
        with patch("streamlit_app.requests.get", return_value=FakeResponse({})):
            with self.assertRaises(streamlit_app.DataFetchError):
                streamlit_app.fetch_bitcoin_prices(days=10)


if __name__ == "__main__":
    unittest.main()
