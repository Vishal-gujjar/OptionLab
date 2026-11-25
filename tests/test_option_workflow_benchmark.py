import unittest
from unittest.mock import patch

from web.services.option_workflow import price_from_market_data


class TestOptionWorkflowBenchmark(unittest.TestCase):

    @patch("web.services.option_workflow.price_option")
    @patch("web.services.option_workflow.load_market_inputs")
    def test_workflow_returns_analytical_comparison(
        self,
        mock_market_inputs,
        mock_price_option
    ):
        mock_market_inputs.return_value = {
            "symbol": "TEST",
            "exchange": "nse",
            "spot_price": 100.0,
            "spot_date": "2026-11-20",
            "volatility": 0.20,
            "volatility_percent": 20.0,
            "volatility_start_date": "2025-11-20",
            "volatility_end_date": "2026-11-20",
            "price_observations": 248,
            "volatility_method": "Historical volatility",
            "annualization_days": 252
        }

        mock_price_option.return_value = {
            "estimated_price": 10.50,
            "standard_error": 0.20,
            "confidence_interval_lower": 0.0,
            "confidence_interval_upper": 20.0,
            "simulations": 100000
        }

        result = price_from_market_data(
            symbol="TEST",
            strike_price=100.0,
            risk_free_rate=0.05,
            dividend_yield=0.0,
            time_to_expiry_years=None,
            option_type="call",
            simulations=100000,
            seed=42,
            exchange="nse",
            expiry_date="2026-12-20",
            volatility_mode="historical",
            manual_volatility=None
        )

        self.assertIn("pricing_result", result)
        self.assertIn("benchmark_result", result)
        self.assertIn("comparison_result", result)

        self.assertEqual(
            result["benchmark_result"]["model"],
            "Black-Scholes-Merton"
        )

        self.assertGreater(
            result["benchmark_result"]["estimated_price"],
            0
        )

        self.assertGreaterEqual(
            result["comparison_result"]["absolute_error"],
            0
        )

        # Verify analytical Greeks.
        self.assertTrue(
            result["greeks_result"]["available"]
        )

        self.assertIn(
            "delta",
            result["greeks_result"]
        )

        self.assertIn(
            "gamma",
            result["greeks_result"]
        )

        self.assertIn(
            "vega_per_1_percentage_point",
            result["greeks_result"]
        )

        self.assertIn(
            "theta_per_calendar_day",
            result["greeks_result"]
        )

        self.assertIn(
            "rho_per_1_percentage_point",
            result["greeks_result"]
        )

        # Verify numerical Greek validation.
        self.assertIn(
            "delta",
            result["greeks_validation_result"]
        )

        self.assertIn(
            "gamma",
            result["greeks_validation_result"]
        )

        # Verify sensitivity scenarios.
        self.assertEqual(
            len(result["sensitivity_result"]["spot_price"]["data"]),
            5
        )

        self.assertEqual(
            len(result["sensitivity_result"]["volatility"]["data"]),
            5
        )

        self.assertEqual(
            len(result["sensitivity_result"]["time_to_expiry"]["data"]),
            5
        )


if __name__ == "__main__":
    unittest.main()