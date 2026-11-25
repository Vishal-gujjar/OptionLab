import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

from web.services.csv_store import (
    save_ohlcv_csv,
    save_adjusted_csv
)

from web.services.market_refresh import (
    refresh_market_data
)


class TestMarketRefresh(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self.temp_dir.name)

        self.raw_rows = [{
            "date": "2026-11-20",
            "open": 100.0,
            "high": 105.0,
            "low": 99.0,
            "close": 103.0,
            "volume": 10000
        }]

        self.adjusted_rows = [{
            "date": "2026-11-20",
            "open": 100.0,
            "high": 105.0,
            "low": 99.0,
            "close": 103.0,
            "volume": 10000,
            "adj_factor_cumulative": 1.0,
            "adj_close": 103.0
        }]

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_existing_cache(self):
        save_ohlcv_csv(
            "RELIANCE",
            "nse",
            self.raw_rows,
            self.cache_dir
        )

        save_adjusted_csv(
            "RELIANCE",
            "nse",
            self.adjusted_rows,
            self.cache_dir
        )

    @patch("web.services.market_refresh.fetch_adjusted")
    @patch("web.services.market_refresh.fetch_ohlcv")
    def test_initial_refresh_creates_both_caches(
        self,
        mock_raw,
        mock_adjusted
    ):
        mock_raw.return_value = {"data": self.raw_rows}
        mock_adjusted.return_value = {
            "data": self.adjusted_rows
        }

        result = refresh_market_data(
            "RELIANCE",
            end_date="2026-11-20",
            lookback_days=365,
            cache_dir=self.cache_dir
        )

        self.assertTrue(
            (self.cache_dir / "nse_RELIANCE.csv").exists()
        )

        self.assertTrue(
            (
                self.cache_dir /
                "nse_RELIANCE_adjusted.csv"
            ).exists()
        )

        self.assertTrue(result["raw_updated"])
        self.assertTrue(result["adjusted_updated"])

    @patch("web.services.market_refresh.fetch_adjusted")
    @patch("web.services.market_refresh.fetch_ohlcv")
    def test_incremental_refresh_uses_overlap(
        self,
        mock_raw,
        mock_adjusted
    ):
        old_raw = [{
            "date": "2026-11-19",
            "open": 100.0,
            "high": 105.0,
            "low": 99.0,
            "close": 103.0,
            "volume": 10000
        }]

        old_adjusted = [{
            "date": "2026-11-20",
            "open": 100.0,
            "high": 105.0,
            "low": 99.0,
            "close": 103.0,
            "volume": 10000,
            "adj_factor_cumulative": 1.0,
            "adj_close": 103.0
        }]

        save_ohlcv_csv(
            "RELIANCE", "nse", old_raw, self.cache_dir
        )

        save_adjusted_csv(
            "RELIANCE", "nse", old_adjusted, self.cache_dir
        )

        mock_raw.return_value = {"data": self.raw_rows}
        mock_adjusted.return_value = {
            "data": self.adjusted_rows
        }

        result = refresh_market_data(
            "RELIANCE",
            end_date="2026-11-23",
            overlap_days=5,
            cache_dir=self.cache_dir
        )

        self.assertEqual(
            result["requested_start_date"],
            "2026-11-14"
        )

        mock_raw.assert_called_once()

        mock_adjusted.assert_called_once()

    @patch("web.services.market_refresh.fetch_adjusted")
    @patch("web.services.market_refresh.fetch_ohlcv")
    def test_network_failure_preserves_existing_cache(
        self,
        mock_raw,
        mock_adjusted
    ):
        self.create_existing_cache()

        raw_path = self.cache_dir / "nse_RELIANCE.csv"
        adjusted_path = (
            self.cache_dir / "nse_RELIANCE_adjusted.csv"
        )

        raw_before = raw_path.read_bytes()
        adjusted_before = adjusted_path.read_bytes()

        mock_raw.return_value = {"data": self.raw_rows}

        mock_adjusted.side_effect = ConnectionError(
            "Simulated TejHQ outage"
        )

        with self.assertRaises(ConnectionError):
            refresh_market_data(
                "RELIANCE",
                end_date="2026-11-23",
                cache_dir=self.cache_dir
            )

        self.assertEqual(
            raw_path.read_bytes(),
            raw_before
        )

        self.assertEqual(
            adjusted_path.read_bytes(),
            adjusted_before
        )

    @patch("web.services.market_refresh.fetch_adjusted")
    @patch("web.services.market_refresh.fetch_ohlcv")
    def test_empty_responses_preserve_existing_cache(
        self,
        mock_raw,
        mock_adjusted
    ):
        self.create_existing_cache()

        mock_raw.return_value = {"data": []}
        mock_adjusted.return_value = {"data": []}

        result = refresh_market_data(
            "RELIANCE",
            end_date="2026-11-23",
            cache_dir=self.cache_dir
        )

        self.assertFalse(result["raw_updated"])
        self.assertFalse(result["adjusted_updated"])

    @patch("web.services.market_refresh.save_adjusted_csv")
    @patch("web.services.market_refresh.fetch_adjusted")
    @patch("web.services.market_refresh.fetch_ohlcv")
    def test_save_failure_rolls_back_both_files(
        self,
        mock_raw,
        mock_adjusted,
        mock_save_adjusted
    ):
        self.create_existing_cache()

        raw_path = self.cache_dir / "nse_RELIANCE.csv"
        adjusted_path = (
            self.cache_dir / "nse_RELIANCE_adjusted.csv"
        )

        raw_before = raw_path.read_bytes()
        adjusted_before = adjusted_path.read_bytes()

        new_raw = [{
            "date": "2026-11-21",
            "open": 101.0,
            "high": 106.0,
            "low": 100.0,
            "close": 104.0,
            "volume": 11000
        }]

        new_adjusted = [{
            "date": "2026-11-21",
            "open": 101.0,
            "high": 106.0,
            "low": 100.0,
            "close": 104.0,
            "volume": 11000,
            "adj_factor_cumulative": 1.0,
            "adj_close": 104.0
        }]

        mock_raw.return_value = {"data": new_raw}
        mock_adjusted.return_value = {
            "data": new_adjusted
        }

        mock_save_adjusted.side_effect = RuntimeError(
            "Simulated adjusted CSV write failure"
        )

        with self.assertRaises(RuntimeError):
            refresh_market_data(
                "RELIANCE",
                end_date="2026-11-23",
                cache_dir=self.cache_dir
            )

        self.assertEqual(raw_path.read_bytes(), raw_before)
        self.assertEqual(
            adjusted_path.read_bytes(),
            adjusted_before
        )

    @patch("web.services.market_refresh.fetch_adjusted")
    @patch("web.services.market_refresh.fetch_ohlcv")
    def test_empty_initial_response_is_rejected(
        self,
        mock_raw,
        mock_adjusted
    ):
        mock_raw.return_value = {"data": []}
        mock_adjusted.return_value = {"data": []}

        with self.assertRaises(RuntimeError):
            refresh_market_data(
                "RELIANCE",
                end_date="2026-11-20",
                cache_dir=self.cache_dir
            )


if __name__ == "__main__":
    unittest.main()