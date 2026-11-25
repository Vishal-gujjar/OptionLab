import unittest

from web.services.option_analytics import (
    simulate_terminal_distribution,
    calculate_option_payoff_analysis
)


class TestOptionAnalytics(unittest.TestCase):

    def setUp(self):
        self.parameters = {
            "spot_price": 100.0,
            "strike_price": 100.0,
            "risk_free_rate": 0.05,
            "dividend_yield": 0.0,
            "volatility": 0.20,
            "time_to_expiry_years": 1.0,
            "option_type": "call"
        }

    def test_distribution_histogram_counts(self):
        result = simulate_terminal_distribution(
            self.parameters,
            sample_count=2000,
            bins=20,
            seed=42
        )

        total = sum(
            item["count"]
            for item in result["histogram"]
        )

        self.assertEqual(total, 2000)
        self.assertEqual(len(result["histogram"]), 20)

    def test_distribution_is_repeatable(self):
        first = simulate_terminal_distribution(
            self.parameters,
            sample_count=2000,
            bins=20,
            seed=42
        )

        second = simulate_terminal_distribution(
            self.parameters,
            sample_count=2000,
            bins=20,
            seed=42
        )

        self.assertEqual(
            first["histogram"],
            second["histogram"]
        )

    def test_distribution_has_theoretical_mean(self):
        result = simulate_terminal_distribution(
            self.parameters,
            sample_count=30000,
            bins=30,
            seed=42
        )

        self.assertAlmostEqual(
            result["summary"][
                "theoretical_expected_terminal_price"
            ],
            100.0 * 2.718281828459045**0.05,
            places=6
        )

    def test_zero_volatility_distribution_is_deterministic(self):
        parameters = self.parameters.copy()
        parameters["volatility"] = 0.0

        result = simulate_terminal_distribution(
            parameters,
            sample_count=1000,
            bins=10,
            seed=42
        )

        self.assertAlmostEqual(
            result["summary"]["sample_minimum"],
            result["summary"]["sample_maximum"],
            places=8
        )

    def test_invalid_sample_count_is_rejected(self):
        with self.assertRaises(ValueError):
            simulate_terminal_distribution(
                self.parameters,
                sample_count=100
            )

    def test_invalid_bins_are_rejected(self):
        with self.assertRaises(ValueError):
            simulate_terminal_distribution(
                self.parameters,
                bins=5
            )

    def test_call_payoff_and_break_even(self):
        result = calculate_option_payoff_analysis(
            self.parameters,
            premium_per_share=10.0,
            lot_size=100
        )

        self.assertEqual(
            result["break_even_stock_price"],
            110.0
        )

        self.assertEqual(
            result["long_position"]["maximum_loss"],
            1000.0
        )

        self.assertEqual(
            result["long_position"]["maximum_profit_label"],
            "Unlimited"
        )

        self.assertEqual(
            result["short_position"]["maximum_profit"],
            1000.0
        )

        self.assertIsNone(
            result["short_position"]["maximum_loss"]
        )

        self.assertEqual(
            result["short_position"]["maximum_loss_label"],
            "Unlimited"
        )

    def test_put_payoff_and_break_even(self):
        parameters = self.parameters.copy()
        parameters["option_type"] = "put"

        result = calculate_option_payoff_analysis(
            parameters,
            premium_per_share=5.0,
            lot_size=100
        )

        self.assertEqual(
            result["break_even_stock_price"],
            95.0
        )

        self.assertEqual(
            result["long_position"]["maximum_profit"],
            9500.0
        )

        self.assertEqual(
            result["long_position"]["maximum_loss"],
            500.0
        )

        self.assertEqual(
            result["short_position"]["maximum_profit"],
            500.0
        )

        self.assertEqual(
            result["short_position"]["maximum_loss"],
            9500.0
        )

        self.assertEqual(
            result["short_position"]["maximum_loss_label"],
            "Finite"
        )

        # The short Put's worst case is a zero stock price.
        zero_price_point = next(
            point for point in result["points"]
            if point["terminal_stock_price"] == 0.0
        )

        self.assertEqual(
            zero_price_point["short_pnl_per_lot"],
            -9500.0
        )



    def test_payoff_per_lot_scales_with_lot_size(self):
        result = calculate_option_payoff_analysis(
            self.parameters,
            premium_per_share=10.0,
            lot_size=500
        )

        self.assertEqual(
            result["premium_per_lot"],
            5000.0
        )

    def test_invalid_option_type_is_rejected(self):
        parameters = self.parameters.copy()
        parameters["option_type"] = "asian"

        with self.assertRaises(ValueError):
            calculate_option_payoff_analysis(
                parameters,
                premium_per_share=10.0,
                lot_size=100
            )


if __name__ == "__main__":
    unittest.main()



    