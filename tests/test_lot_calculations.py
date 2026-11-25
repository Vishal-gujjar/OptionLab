import unittest

from web.services.lot_calculations import (
    calculate_lot_values
)


class TestLotCalculations(unittest.TestCase):

    def setUp(self):

        self.pricing_result = {
            "estimated_price": 10.0,
            "standard_error": 0.20,
            "confidence_interval_lower": 9.608,
            "confidence_interval_upper": 10.392,
            "simulations": 100000
        }

        self.benchmark_result = {
            "model": "Black-Scholes-Merton",
            "estimated_price": 9.80
        }

        self.contract_metadata = {
            "contract_id": "126008",
            "symbol": "RELIANCE",
            "expiry_date": "2026-11-23",
            "strike_price": 1400.0,
            "option_type": "call",
            "board_lot_quantity": 500
        }

        self.comparison_result = {
            "confidence_interval_contains_benchmark": True
        }

    def calculate(self):
        return calculate_lot_values(
            self.pricing_result,
            self.benchmark_result,
            self.contract_metadata,
            self.comparison_result
        )

    def test_monte_carlo_premium_per_lot(self):
        result = self.calculate()

        self.assertAlmostEqual(
            result["theoretical_premium_per_lot"],
            5000.0
        )

    def test_analytical_premium_per_lot(self):
        result = self.calculate()

        self.assertAlmostEqual(
            result["analytical_premium_per_lot"],
            4900.0
        )

    def test_standard_error_per_lot(self):
        result = self.calculate()

        self.assertAlmostEqual(
            result["standard_error_per_lot"],
            100.0
        )

    def test_confidence_interval_per_lot(self):
        result = self.calculate()

        self.assertAlmostEqual(
            result["confidence_interval_per_lot"]["lower"],
            9.608 * 500
        )

        self.assertAlmostEqual(
            result["confidence_interval_per_lot"]["upper"],
            10.392 * 500
        )

    def test_absolute_error_per_lot(self):
        result = self.calculate()

        self.assertAlmostEqual(
            result["absolute_error_per_lot"],
            100.0
        )

    def test_relative_error_is_unchanged(self):
        result = self.calculate()

        expected = (0.20 / 9.80) * 100

        self.assertAlmostEqual(
            result["relative_error_percent"],
            expected
        )

    def test_tcs_contract_lot_size(self):
        metadata = self.contract_metadata.copy()
        metadata["symbol"] = "TCS"
        metadata["board_lot_quantity"] = 225

        result = calculate_lot_values(
            self.pricing_result,
            self.benchmark_result,
            metadata
        )

        self.assertEqual(
            result["theoretical_premium_per_lot"],
            2250.0
        )

    def test_invalid_lot_size_is_rejected(self):
        metadata = self.contract_metadata.copy()
        metadata["board_lot_quantity"] = 0

        with self.assertRaises(ValueError):
            calculate_lot_values(
                self.pricing_result,
                self.benchmark_result,
                metadata
            )

    def test_invalid_confidence_interval_is_rejected(self):
        pricing = self.pricing_result.copy()

        pricing["confidence_interval_lower"] = 11.0
        pricing["confidence_interval_upper"] = 10.0

        with self.assertRaises(ValueError):
            calculate_lot_values(
                pricing,
                self.benchmark_result,
                self.contract_metadata
            )


if __name__ == "__main__":
    unittest.main()