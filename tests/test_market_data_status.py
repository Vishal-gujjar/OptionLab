import csv
import tempfile
import unittest

from datetime import date, datetime, timezone
from pathlib import Path

from web.services.csv_store import (
    save_ohlcv_csv,
    save_adjusted_csv
)

from web.services.market_data_status import (
    get_market_data_status
)


class TestMarketDataStatus(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_raw(self, dates):
        rows = []

        for index, item in enumerate(dates):
            rows.append({
                "date": item,
                "open": 100 + index,
                "high": 105 + index,
                "low": 99 + index,
                "close": 103 + index,
                "volume": 10000
            })

        return save_ohlcv_csv(
            "RELIANCE",
            "nse",
            rows,
            self.cache_dir
        )

    def create_adjusted(self, dates):
        rows = []

        for index, item in enumerate(dates):
            rows.append({
                "date": item,
                "open": 100 + index,
                "high": 105 + index,
                "low": 99 + index,
                "close": 103 + index,
                "volume": 10000,
                "adj_factor_cumulative": 1.0,
                "adj_close": 103 + index
            })

        return save_adjusted_csv(
            "RELIANCE",
            "nse",
            rows,
            self.cache_dir
        )

    def overwrite_csv_field(
        self,
        path,
        row_index,
        field,
        value
    ):

        with path.open(
            "r",
            newline="",
            encoding="utf-8"
        ) as file:

            reader = csv.DictReader(file)
            fieldnames = reader.fieldnames
            rows = list(reader)

        rows[row_index][field] = str(value)

        with path.open(
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames
            )

            writer.writeheader()
            writer.writerows(rows)

    def test_fresh_matching_data(self):
        dates = ["2026-11-19", "2026-11-20"]

        self.create_raw(dates)
        self.create_adjusted(dates)

        result = get_market_data_status(
            "RELIANCE",
            cache_dir=self.cache_dir,
            as_of_date="2026-11-23"
        )

        self.assertEqual(result["status"], "fresh")
        self.assertTrue(result["dates_match"])
        self.assertEqual(
            result["raw"]["latest_date"],
            "2026-11-20"
        )

    def test_missing_raw_file(self):
        self.create_adjusted(["2026-11-20"])

        result = get_market_data_status(
            "RELIANCE",
            cache_dir=self.cache_dir,
            as_of_date="2026-11-20"
        )

        self.assertEqual(result["status"], "missing")
        self.assertFalse(result["raw"]["available"])

    def test_missing_adjusted_file(self):
        self.create_raw(["2026-11-20"])

        result = get_market_data_status(
            "RELIANCE",
            cache_dir=self.cache_dir,
            as_of_date="2026-11-20"
        )

        self.assertEqual(result["status"], "missing")
        self.assertFalse(result["adjusted"]["available"])

    def test_raw_adjusted_date_mismatch(self):
        self.create_raw(["2026-11-20"])
        self.create_adjusted(["2026-11-19"])

        result = get_market_data_status(
            "RELIANCE",
            cache_dir=self.cache_dir,
            as_of_date="2026-11-20"
        )

        self.assertEqual(result["status"], "date_mismatch")
        self.assertFalse(result["dates_match"])

    def test_aging_data(self):
        self.create_raw(["2026-11-15"])
        self.create_adjusted(["2026-11-15"])

        result = get_market_data_status(
            "RELIANCE",
            cache_dir=self.cache_dir,
            as_of_date="2026-11-20"
        )

        self.assertEqual(result["status"], "aging")

    def test_stale_data(self):
        self.create_raw(["2026-11-10"])
        self.create_adjusted(["2026-11-10"])

        result = get_market_data_status(
            "RELIANCE",
            cache_dir=self.cache_dir,
            as_of_date="2026-11-20"
        )

        self.assertEqual(result["status"], "stale")

    def test_future_market_date_is_invalid(self):
        self.create_raw(["2026-11-21"])
        self.create_adjusted(["2026-11-21"])

        result = get_market_data_status(
            "RELIANCE",
            cache_dir=self.cache_dir,
            as_of_date="2026-11-20"
        )

        self.assertEqual(result["status"], "invalid")

    def test_non_finite_raw_price_is_invalid(self):

        self.create_raw(["2026-11-20"])
        self.create_adjusted(["2026-11-20"])

        raw_file = (
            self.cache_dir / "nse_RELIANCE.csv"
        )

        self.overwrite_csv_field(
            raw_file,
            0,
            "high",
            "nan"
        )

        result = get_market_data_status(
            "RELIANCE",
            cache_dir=self.cache_dir,
            as_of_date="2026-11-20"
        )

        self.assertEqual(
            result["status"],
            "invalid"
        )

        self.assertFalse(
            result["raw"]["valid"]
        )


    def test_non_finite_adjustment_factor_is_invalid(self):

        self.create_raw(["2026-11-20"])
        self.create_adjusted(["2026-11-20"])

        adjusted_file = (
            self.cache_dir /
            "nse_RELIANCE_adjusted.csv"
        )

        self.overwrite_csv_field(
            adjusted_file,
            0,
            "adj_factor_cumulative",
            "inf"
        )

        result = get_market_data_status(
            "RELIANCE",
            cache_dir=self.cache_dir,
            as_of_date="2026-11-20"
        )

        self.assertEqual(
            result["status"],
            "invalid"
        )

        self.assertFalse(
            result["adjusted"]["valid"]
        )


    def test_duplicate_raw_dates_are_invalid(self):

        dates = [
            "2026-11-19",
            "2026-11-20"
        ]

        self.create_raw(dates)
        self.create_adjusted(dates)

        raw_file = (
            self.cache_dir / "nse_RELIANCE.csv"
        )

        self.overwrite_csv_field(
            raw_file,
            1,
            "date",
            "2026-11-19"
        )

        result = get_market_data_status(
            "RELIANCE",
            cache_dir=self.cache_dir,
            as_of_date="2026-11-20"
        )

        self.assertEqual(
            result["status"],
            "invalid"
        )


    def test_out_of_order_raw_dates_are_invalid(self):

        dates = [
            "2026-11-19",
            "2026-11-20"
        ]

        self.create_raw(dates)
        self.create_adjusted(dates)

        raw_file = (
            self.cache_dir / "nse_RELIANCE.csv"
        )

        self.overwrite_csv_field(
            raw_file,
            0,
            "date",
            "2026-11-21"
        )

        result = get_market_data_status(
            "RELIANCE",
            cache_dir=self.cache_dir,
            as_of_date="2026-11-21"
        )

        self.assertEqual(
            result["status"],
            "invalid"
        )


    def test_different_history_lengths_are_allowed(self):

        # Raw data contains two observations.
        self.create_raw([
            "2026-11-19",
            "2026-11-20"
        ])

        # Adjusted data contains only one observation.
        self.create_adjusted([
            "2026-11-20"
        ])

        result = get_market_data_status(
            "RELIANCE",
            cache_dir=self.cache_dir,
            as_of_date="2026-11-20"
        )

        self.assertEqual(
            result["status"],
            "fresh"
        )

        self.assertTrue(
            result["dates_match"]
        )

        self.assertEqual(
            result["raw"]["observations"],
            2
        )

        self.assertEqual(
            result["adjusted"]["observations"],
            1
        )


if __name__ == "__main__":
    unittest.main()