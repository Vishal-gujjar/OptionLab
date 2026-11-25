import csv
import sys
import tempfile
import unittest

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from web.services.csv_store import (
    save_ohlcv_csv,
    save_adjusted_csv
)

class CSVStorageTests(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self.temp_dir.name)

        self.rows = [
            {
                "date": "2026-11-20",
                "open": 1369,
                "high": 1383,
                "low": 1356.1,
                "close": 1377.5,
                "volume": 13167730
            },
            {
                "date": "2026-11-19",
                "open": 1370,
                "high": 1380,
                "low": 1360,
                "close": 1372,
                "volume": 12000000
            }
        ]

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_csv_creation(self):

        path = save_ohlcv_csv(
            "RELIANCE",
            "NSE",
            self.rows,
            self.cache_dir
        )

        self.assertTrue(path.exists())

        with path.open(encoding="utf-8") as file:
            rows = list(csv.DictReader(file))

        self.assertEqual(len(rows), 2)

        self.assertEqual(
            rows[0]["date"],
            "2026-11-19"
        )

        self.assertEqual(
            rows[1]["date"],
            "2026-11-20"
        )

    def test_duplicate_dates_are_updated(self):

        path = save_ohlcv_csv(
            "RELIANCE",
            "NSE",
            self.rows,
            self.cache_dir
        )

        updated_rows = [
            {
                "date": "2026-11-20",
                "open": 1369,
                "high": 1390,
                "low": 1356.1,
                "close": 1385,
                "volume": 14000000
            }
        ]

        save_ohlcv_csv(
            "RELIANCE",
            "NSE",
            updated_rows,
            self.cache_dir
        )

        with path.open(encoding="utf-8") as file:
            rows = list(csv.DictReader(file))

        self.assertEqual(len(rows), 2)

        self.assertEqual(
            rows[-1]["close"],
            "1385"
        )

    def test_empty_data_is_rejected(self):

        with self.assertRaises(ValueError):

            save_ohlcv_csv(
                "RELIANCE",
                "NSE",
                [],
                self.cache_dir
            )

    def test_invalid_prices_are_rejected(self):

        invalid_rows = [
            {
                "date": "2026-11-20",
                "open": 1400,
                "high": 1350,
                "low": 1360,
                "close": 1377,
                "volume": 1000
            }
        ]

        with self.assertRaises(ValueError):

            save_ohlcv_csv(
                "RELIANCE",
                "NSE",
                invalid_rows,
                self.cache_dir
            )
    def test_nan_raw_close_is_rejected(self):

        invalid_rows = [
            self.rows[0].copy()
        ]

        invalid_rows[0]["close"] = float("nan")

        with self.assertRaises(ValueError):

            save_ohlcv_csv(
                "RELIANCE",
                "NSE",
                invalid_rows,
                self.cache_dir
            )


    def test_infinite_raw_volume_is_rejected(self):

        invalid_rows = [
            self.rows[0].copy()
        ]

        invalid_rows[0]["volume"] = float("inf")

        with self.assertRaises(ValueError):

            save_ohlcv_csv(
                "RELIANCE",
                "NSE",
                invalid_rows,
                self.cache_dir
            )


    def test_nan_adjusted_close_is_rejected(self):

        invalid_rows = [
            {
                **self.rows[0],
                "adj_factor_cumulative": 1.0,
                "adj_close": float("nan")
            }
        ]

        with self.assertRaises(ValueError):

            save_adjusted_csv(
                "RELIANCE",
                "NSE",
                invalid_rows,
                self.cache_dir
            )



if __name__ == "__main__":
    unittest.main()








    