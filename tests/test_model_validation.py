import unittest
from unittest.mock import patch

from web.services.model_validation import (
    compare_pricing_results,
    run_convergence_analysis
)


class TestModelValidation(unittest.TestCase):

    def setUp(self):
        self.monte_carlo_result = {
            "estimated_price": 10.50,
            "standard_error": 0.20,
            "confidence_interval_lower": 10.10,
            "confidence_interval_upper": 10.90,
            "simulations": 100000
        }

        self.analytical_result = {
            "model": "Black-Scholes-Merton",
            "estimated_price": 10.45
        }

        self.option_parameters = {
            "spot_price": 100.0,
            "strike_price": 100.0,
            "risk_free_rate": 0.05,
            "dividend_yield": 0.0,
            "volatility": 0.20,
            "time_to_expiry_years": 1.0,
            "option_type": "call"
        }

    def test_comparison_metrics(self):
        result = compare_pricing_results(
            self.monte_carlo_result,
            self.analytical_result
        )

        self.assertAlmostEqual(
            result["absolute_error"], 0.05
        )

        self.assertAlmostEqual(
            result["relative_error_percent"],
            (0.05 / 10.45) * 100
        )

        self.assertTrue(
            result["confidence_interval_contains_benchmark"]
        )

    def test_benchmark_outside_confidence_interval(self):
        monte_carlo = self.monte_carlo_result.copy()
        monte_carlo["confidence_interval_lower"] = 11.0
        monte_carlo["confidence_interval_upper"] = 12.0

        result = compare_pricing_results(
            monte_carlo,
            self.analytical_result
        )

        self.assertFalse(
            result["confidence_interval_contains_benchmark"]
        )

    def test_zero_analytical_price(self):
        analytical = {
            "estimated_price": 0.0
        }

        result = compare_pricing_results(
            self.monte_carlo_result,
            analytical
        )

        self.assertIsNone(
            result["relative_error_percent"]
        )

    @patch("web.services.model_validation.price_option")
    def test_convergence_analysis(self, mock_price_option):
        mock_price_option.side_effect = [
            {
                "estimated_price": 10.40,
                "standard_error": 0.30,
                "confidence_interval_lower": 9.81,
                "confidence_interval_upper": 10.99,
                "simulations": 1000
            },
            {
                "estimated_price": 10.44,
                "standard_error": 0.13,
                "confidence_interval_lower": 10.18,
                "confidence_interval_upper": 10.70,
                "simulations": 5000
            }
        ]

        results = run_convergence_analysis(
            self.option_parameters,
            [1000, 5000],
            seed=42
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["simulations"], 1000)
        self.assertEqual(results[1]["simulations"], 5000)

        self.assertEqual(
            mock_price_option.call_count, 2
        )

    def test_invalid_simulation_count_order(self):
        with self.assertRaises(ValueError):
            run_convergence_analysis(
                self.option_parameters,
                [5000, 1000]
            )


if __name__ == "__main__":
    unittest.main()