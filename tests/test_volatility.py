import csv
import math
import sys
import tempfile
import unittest

from pathlib import Path
from statistics import stdev


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from web.services.volatility import calculate_historical_volatility


class VolatilityTests(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()

        self.csv_path = (
            Path(self.temp_dir.name) / "test_adjusted.csv"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_prices(self, prices):

        with self.csv_path.open(
            "w", newline="", encoding="utf-8"
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                "date",
                "adj_close"
            ])

            for i, price in enumerate(prices):

                writer.writerow([
                    f"2026-01-{i + 1:02d}",
                    price
                ])

    def test_volatility_calculation(self):

        prices = [100, 102, 101, 105, 103]

        self.write_prices(prices)

        result = calculate_historical_volatility(
            self.csv_path
        )

        returns = [
            math.log(prices[i] / prices[i - 1])
            for i in range(1, len(prices))
        ]

        expected_daily_volatility = stdev(returns)

        expected_annualized = (
            expected_daily_volatility * math.sqrt(252)
        )

        self.assertAlmostEqual(
            result["daily_volatility"],
            expected_daily_volatility
        )

        self.assertAlmostEqual(
            result["annualized_volatility"],
            expected_annualized
        )

    def test_observation_count(self):

        self.write_prices([100, 101, 102])

        result = calculate_historical_volatility(
            self.csv_path
        )

        self.assertEqual(result["observations"], 3)

        self.assertEqual(
            result["return_observations"], 2
        )

    def test_zero_price_is_rejected(self):

        self.write_prices([100, 0, 105])

        with self.assertRaises(ValueError):

            calculate_historical_volatility(
                self.csv_path
            )

    def test_insufficient_data(self):

        self.write_prices([100, 102])

        with self.assertRaises(ValueError):

            calculate_historical_volatility(
                self.csv_path
            )

    def test_missing_file(self):

        with self.assertRaises(FileNotFoundError):

            calculate_historical_volatility(
                self.csv_path
            )


if __name__ == "__main__":
    unittest.main()




    