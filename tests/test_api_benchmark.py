import unittest
from unittest.mock import patch

from web.app import create_app


class TestBenchmarkAPI(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    @patch("web.app.calculate_lot_values")
    @patch("web.app.validate_option_contract")
    @patch("web.app.get_market_data_status")
    @patch("web.app.price_from_market_data")
    def test_price_endpoint_returns_benchmark_fields(
        self,
        mock_workflow,
        mock_status,
        mock_validate,
        mock_lot
    ):
        mock_status.return_value = {
            "symbol": "RELIANCE",
            "exchange": "NSE",
            "status": "fresh",
            "warnings": [],
            "raw": {
                "latest_date": "2026-11-20",
                "latest_close": 1377.50
            },
            "adjusted": {
                "latest_date": "2026-11-20"
            }
        }

        mock_validate.return_value = {
            "valid": True,
            "contract_id": "TEST126",
            "symbol": "RELIANCE",
            "expiry_date": "2026-12-29",
            "strike_price": 1400.0,
            "option_type": "call",
            "exchange_option_type": "CE",
            "board_lot_quantity": 500,
            "tick_size": 0.05,
            "permitted_to_trade": True,
            "is_deleted": False,
            "normal_market_status": "2",
            "normal_market_eligible": True,
            "source_file_date": "2026-11-20"
        }

        mock_lot.return_value = {
            "theoretical_premium_per_lot": 5000.0,
            "analytical_premium_per_lot": 4900.0
        }


        
        mock_workflow.return_value = {
            "pricing_result": {
                "estimated_price": 10.50,
                "standard_error": 0.20,
                "confidence_interval_lower": 10.10,
                "confidence_interval_upper": 10.90,
                "simulations": 100000
            },
            "benchmark_result": {
                "model": "Black-Scholes-Merton",
                "estimated_price": 10.45,
                "d1": 0.35,
                "d2": 0.15
            },
            "comparison_result": {
                "signed_error": 0.05,
                "absolute_error": 0.05,
                "relative_error_percent": 0.4784689,
                "confidence_interval_contains_benchmark": True
            },
            "greeks_result": {
                "available": True,
                "delta": 0.60,
                "gamma": 0.02,
                "vega_per_1_00_volatility": 35.0,
                "vega_per_1_percentage_point": 0.35,
                "theta_per_year": -5.0,
                "theta_per_calendar_day": -5.0 / 365.0,
                "rho_per_1_00_rate": 50.0,
                "rho_per_1_percentage_point": 0.50
            },

            "numerical_greeks_result": {
                "delta": 0.60,
                "gamma": 0.02,
                "vega_per_1_00_volatility": 35.0,
                "theta_per_year": -5.0,
                "rho_per_1_00_rate": 50.0
            },

            "greeks_validation_result": {
                "delta": {
                    "analytical": 0.60,
                    "numerical": 0.60,
                    "absolute_difference": 0.0,
                    "relative_error_percent": 0.0
                },
                "gamma": {
                    "analytical": 0.02,
                    "numerical": 0.02,
                    "absolute_difference": 0.0,
                    "relative_error_percent": 0.0
                },
                "vega_per_1_00_volatility": {
                    "analytical": 35.0,
                    "numerical": 35.0,
                    "absolute_difference": 0.0,
                    "relative_error_percent": 0.0
                },
                "theta_per_year": {
                    "analytical": -5.0,
                    "numerical": -5.0,
                    "absolute_difference": 0.0,
                    "relative_error_percent": 0.0
                },
                "rho_per_1_00_rate": {
                    "analytical": 50.0,
                    "numerical": 50.0,
                    "absolute_difference": 0.0,
                    "relative_error_percent": 0.0
                }
            },

            "sensitivity_result": {
                "spot_price": {
                    "label": "Spot Price",
                    "x_axis_label": "Spot Price (₹)",
                    "data": []
                },
                "volatility": {
                    "label": "Annualized Volatility",
                    "x_axis_label": "Volatility (%)",
                    "data": []
                },
                "time_to_expiry": {
                    "label": "Time to Expiry",
                    "x_axis_label": "Time to Expiry (Years)",
                    "data": []
                }
            }
        }

        payload = {
            "symbol": "RELIANCE",
            "strike_price": 1400,
            "risk_free_rate": 0.06,
            "dividend_yield": 0.0,
            "expiry_date": "2026-12-20",
            "option_type": "call",
            "volatility_mode": "historical"
        }

        response = self.client.post(
            "/api/price",
            json=payload
        )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()

        self.assertIn("pricing_result", data)
        self.assertIn("benchmark_result", data)
        self.assertIn("comparison_result", data)

        self.assertIn("greeks_result", data)
        self.assertIn("numerical_greeks_result", data)
        self.assertIn("greeks_validation_result", data)
        self.assertIn("sensitivity_result", data)

        self.assertAlmostEqual(
            data["greeks_result"]["delta"],
            0.60
        )

        self.assertAlmostEqual(
            data["benchmark_result"]["estimated_price"],
            10.45
        )

        self.assertTrue(
            data["comparison_result"][
                "confidence_interval_contains_benchmark"
            ]
        )


if __name__ == "__main__":
    unittest.main()