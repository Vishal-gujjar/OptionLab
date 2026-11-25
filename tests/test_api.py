
import unittest
from unittest.mock import patch

from web.app import create_app


class FlaskAPITests(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        # Stage 16 dependencies are mocked in this API test class
        # so existing pricing-validation tests remain isolated
        # from real NSE files and TejHQ cache contents.

        self.stage16_patches = [
            patch(
                "web.app.validate_option_contract",
                return_value={
                    "valid": True,
                    "contract_id": "TEST126",
                    "symbol": "RELIANCE",
                    "expiry_date": "2026-11-24",
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
            ),

            patch(
                "web.app.get_market_data_status",
                return_value={
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
            ),

            patch(
                "web.app.calculate_lot_values",
                return_value={
                    "theoretical_premium_per_lot": 7500.0,
                    "analytical_premium_per_lot": 7450.0
                }
            )
        ]

        for patcher in self.stage16_patches:
            patcher.start()
            self.addCleanup(patcher.stop)


    def valid_payload(self):
        return {
            "symbol": "RELIANCE",
            "strike_price": 1400,
            "risk_free_rate": 0.06,
            "dividend_yield": 0.0,
            "expiry_date": "2026-11-24",
            "option_type": "call",
            "volatility_mode": "historical",
            "simulations": 100000,
            "seed": 42
        }

    def test_health_endpoint(self):

        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_homepage_loads_dashboard(self):

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "text/html")
        self.assertIn(b"OptionLab", response.data)
        self.assertIn(b"Pricing Parameters", response.data)

    @patch("web.app.price_from_market_data")
    def test_successful_pricing_request(self, mock_pricing):

        mock_pricing.return_value = {
            "market_data": {
                "symbol": "RELIANCE",
                "spot_price": 1377.5
            },
            "maturity_info": {
                "valuation_date": "2026-11-20",
                "expiry_date": "2026-11-24",
                "calendar_days_to_expiry": 4,
                "day_count_convention": "ACT/365F",
                "time_to_expiry_years": 4 / 365
            },
            "volatility_info": {
                "mode": "historical",
                "method": "Historical volatility",
                "annualized_volatility": 0.24517,
                "annualized_volatility_percent": 24.517
            },
            "financial_assumptions": {
                "risk_free_rate": 0.06,
                "risk_free_rate_percent": 6.0,
                "risk_free_rate_convention":
                    "Annualized continuously compounded rate",
                "dividend_yield": 0.0,
                "dividend_yield_percent": 0.0,
                "dividend_yield_convention":
                    "Annualized continuous dividend yield"
            },
            "option_parameters": {
                "strike_price": 1400.0,
                "option_type": "call",
                "time_to_expiry_years": 4 / 365
            },
            "pricing_result": {
                "estimated_price": 15.0,
                "standard_error": 0.2,
                "confidence_interval_lower": 14.608,
                "confidence_interval_upper": 15.392,
                "simulations": 100000
            },
            "benchmark_result": {
                "model": "Black-Scholes-Merton",
                "estimated_price": 14.9,
                "d1": 0.1,
                "d2": 0.08
            },
            "comparison_result": {
                "signed_error": 0.1,
                "absolute_error": 0.1,
                "relative_error_percent": 0.6711409396,
                "confidence_interval_contains_benchmark": True
            }
        }

        response = self.client.post(
            "/api/price",
            json=self.valid_payload()
        )

        self.assertEqual(response.status_code, 200)

        result = response.get_json()

        # Verify the API response structure.
        self.assertIn("pricing_result", result)
        self.assertIn("benchmark_result", result)
        self.assertIn("comparison_result", result)

        # Verify maturity calculation.
        self.assertEqual(
            result["maturity_info"]["calendar_days_to_expiry"],
            4
        )

        # Verify analytical benchmark.
        self.assertAlmostEqual(
            result["benchmark_result"]["estimated_price"],
            14.9
        )

        # Verify model comparison.
        self.assertAlmostEqual(
            result["comparison_result"]["absolute_error"],
            0.1
        )

        mock_pricing.assert_called_once_with(
            symbol="RELIANCE",
            strike_price=1400.0,
            risk_free_rate=0.06,
            dividend_yield=0.0,
            time_to_expiry_years=None,
            expiry_date="2026-11-24",
            option_type="call",
            simulations=100000,
            seed=42,
            exchange="nse",
            volatility_mode="historical",
            manual_volatility=None
        )

    @patch("web.app.price_from_market_data")
    def test_manual_volatility_request(self, mock_pricing):

        mock_pricing.return_value = {
            "market_data": {"symbol": "RELIANCE"},
            "maturity_info": {},
            "volatility_info": {
                "mode": "manual",
                "annualized_volatility": 0.30
            },
            "financial_assumptions": {},
            "option_parameters": {},
            "pricing_result": {}
        }

        mock_pricing.return_value.update({
            "benchmark_result": {
                "model": "Black-Scholes-Merton",
                "estimated_price": 10.0,
                "d1": 0.2,
                "d2": 0.1
            },

            "comparison_result": {
                "signed_error": 0.05,
                "absolute_error": 0.05,
                "relative_error_percent": 0.5,
                "confidence_interval_contains_benchmark": True
            }
        })

        payload = self.valid_payload()
        payload["volatility_mode"] = "manual"
        payload["manual_volatility"] = 0.30

        response = self.client.post(
            "/api/price",
            json=payload
        )

        self.assertEqual(response.status_code, 200)

        mock_pricing.assert_called_once_with(
            symbol="RELIANCE",
            strike_price=1400.0,
            risk_free_rate=0.06,
            dividend_yield=0.0,
            time_to_expiry_years=None,
            expiry_date="2026-11-24",
            option_type="call",
            simulations=100000,
            seed=42,
            exchange="nse",
            volatility_mode="manual",
            manual_volatility=0.30
        )

    def test_missing_required_field(self):

        payload = self.valid_payload()
        del payload["expiry_date"]

        response = self.client.post(
            "/api/price",
            json=payload
        )

        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            response.get_json()["error"]["code"],
            "missing_parameters"
        )

    def test_invalid_strike_price(self):

        payload = self.valid_payload()
        payload["strike_price"] = "1400"

        response = self.client.post(
            "/api/price",
            json=payload
        )

        self.assertEqual(response.status_code, 400)

    def test_unsupported_exchange(self):

        payload = self.valid_payload()
        payload["exchange"] = "bse"

        response = self.client.post(
            "/api/price",
            json=payload
        )

        self.assertEqual(response.status_code, 400)

    def test_missing_market_data(self):

        with patch(
            "web.app.price_from_market_data",
            side_effect=FileNotFoundError
        ):

            response = self.client.post(
                "/api/price",
                json=self.valid_payload()
            )

        self.assertEqual(response.status_code, 404)

        self.assertEqual(
            response.get_json()["error"]["code"],
            "required_data_not_found"
        )

    def test_simulation_limit(self):

        payload = self.valid_payload()
        payload["simulations"] = 10_000_000

        response = self.client.post(
            "/api/price",
            json=payload
        )

        self.assertEqual(response.status_code, 400)

    def test_invalid_expiry_format(self):

        payload = self.valid_payload()
        payload["expiry_date"] = "24-11-2026"

        response = self.client.post(
            "/api/price",
            json=payload
        )

        self.assertEqual(response.status_code, 400)

    @patch("web.app.price_from_market_data")
    def test_expiry_not_after_valuation_date(self, mock_pricing):

        mock_pricing.side_effect = ValueError(
            "Expiry date must be later than valuation date."
        )

        response = self.client.post(
            "/api/price",
            json=self.valid_payload()
        )

        self.assertEqual(response.status_code, 422)

    def test_manual_volatility_required(self):

        payload = self.valid_payload()
        payload["volatility_mode"] = "manual"

        response = self.client.post(
            "/api/price",
            json=payload
        )

        self.assertEqual(response.status_code, 400)

    def test_zero_manual_volatility_rejected(self):

        payload = self.valid_payload()
        payload["volatility_mode"] = "manual"
        payload["manual_volatility"] = 0

        response = self.client.post(
            "/api/price",
            json=payload
        )

        self.assertEqual(response.status_code, 400)

    def test_manual_volatility_rejected_in_historical_mode(self):

        payload = self.valid_payload()
        payload["manual_volatility"] = 0.30

        response = self.client.post(
            "/api/price",
            json=payload
        )

        self.assertEqual(response.status_code, 400)

    def test_invalid_volatility_mode(self):

        payload = self.valid_payload()
        payload["volatility_mode"] = "implied"

        response = self.client.post(
            "/api/price",
            json=payload
        )

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
