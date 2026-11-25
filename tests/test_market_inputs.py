import csv
import tempfile
import unittest

from pathlib import Path

from web.services.csv_store import (
    save_ohlcv_csv,
    save_adjusted_csv
)

from web.services.market_inputs import load_market_inputs


class MarketInputsTests(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self.temp_dir.name)

        raw_rows = [
            {
                "date": "2026-11-18",
                "open": 100,
                "high": 103,
                "low": 99,
                "close": 101,
                "volume": 10000
            },
            {
                "date": "2026-11-19",
                "open": 101,
                "high": 105,
                "low": 100,
                "close": 104,
                "volume": 12000
            },
            {
                "date": "2026-11-20",
                "open": 104,
                "high": 108,
                "low": 103,
                "close": 107,
                "volume": 15000
            }
        ]

        adjusted_rows = [
            {
                "date": "2026-11-18",
                "open": 100,
                "high": 103,
                "low": 99,
                "close": 101,
                "volume": 10000,
                "adj_factor_cumulative": 1.0,
                "adj_close": 100.0
            },
            {
                "date": "2026-11-19",
                "open": 101,
                "high": 105,
                "low": 100,
                "close": 104,
                "volume": 12000,
                "adj_factor_cumulative": 1.0,
                "adj_close": 103.0
            },
            {
                "date": "2026-11-20",
                "open": 104,
                "high": 108,
                "low": 103,
                "close": 107,
                "volume": 15000,
                "adj_factor_cumulative": 1.0,
                "adj_close": 106.0
            }
        ]

        save_ohlcv_csv(
            "RELIANCE", "NSE",
            raw_rows, self.cache_dir
        )

        save_adjusted_csv(
            "RELIANCE", "NSE",
            adjusted_rows, self.cache_dir
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_market_inputs(self):

        result = load_market_inputs(
            "RELIANCE",
            "nse",
            self.cache_dir
        )

        self.assertEqual(result["spot_price"], 107.0)

        self.assertEqual(
            result["spot_date"],
            "2026-11-20"
        )

        self.assertGreater(
            result["volatility"],
            0
        )

    def test_missing_company_data(self):

        with self.assertRaises(FileNotFoundError):

            load_market_inputs(
                "TCS",
                "nse",
                self.cache_dir
            )

    def test_mismatched_latest_dates_are_rejected(self):

        adjusted_file = (
            self.cache_dir /
            "nse_RELIANCE_adjusted.csv"
        )

        # Read current adjusted observations.
        with adjusted_file.open(
            "r",
            newline="",
            encoding="utf-8"
        ) as file:

            reader = csv.DictReader(file)
            fieldnames = reader.fieldnames
            rows = list(reader)

        # Remove the latest adjusted observation.
        rows = [
            row for row in rows
            if row["date"] != "2026-11-20"
        ]

        with adjusted_file.open(
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

        # Raw data now ends on November 20, but
        # adjusted data ends on November 19.
        with self.assertRaisesRegex(
            ValueError,
            "Market data cannot be used for pricing"
        ):

            load_market_inputs(
                "RELIANCE",
                "nse",
                self.cache_dir
            )


    def test_non_finite_raw_price_is_rejected(self):

        raw_file = (
            self.cache_dir /
            "nse_RELIANCE.csv"
        )

        with raw_file.open(
            "r",
            newline="",
            encoding="utf-8"
        ) as file:

            reader = csv.DictReader(file)
            fieldnames = reader.fieldnames
            rows = list(reader)

        rows[-1]["close"] = "nan"

        with raw_file.open(
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

        with self.assertRaisesRegex(
            ValueError,
            "Market data cannot be used for pricing"
        ):

            load_market_inputs(
                "RELIANCE",
                "nse",
                self.cache_dir
            )


if __name__ == "__main__":
    unittest.main()