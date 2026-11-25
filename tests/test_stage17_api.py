import unittest

from datetime import date

from unittest.mock import patch

from web.app import create_app


class TestStage17API(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        self.parameters = {
            "spot_price": 100.0,
            "strike_price": 100.0,
            "risk_free_rate": 0.05,
            "dividend_yield": 0.0,
            "volatility": 0.20,
            "time_to_expiry_years": 1.0,
            "option_type": "call"
        }

    @patch("web.stage17_routes.simulate_terminal_distribution")
    def test_distribution_endpoint(self, mock_distribution):

        mock_distribution.return_value = {
            "model": "Risk-neutral Geometric Brownian Motion",
            "sample_count": 20000,
            "histogram": [],
            "summary": {
                "sample_mean": 105.0
            }
        }

        response = self.client.post(
            "/api/analytics/distribution",
            json={
                "option_parameters": self.parameters,
                "sample_count": 20000,
                "bins": 40,
                "seed": 42
            }
        )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()

        self.assertIn("distribution", data)
        self.assertEqual(
            data["distribution"]["sample_count"],
            20000
        )

    def test_distribution_rejects_invalid_sample_count(self):

        response = self.client.post(
            "/api/analytics/distribution",
            json={
                "option_parameters": self.parameters,
                "sample_count": 100
            }
        )

        self.assertEqual(response.status_code, 400)

    @patch("web.stage17_routes.calculate_option_payoff_analysis")
    def test_payoff_endpoint(self, mock_payoff):

        mock_payoff.return_value = {
            "option_type": "call",
            "break_even_stock_price": 110.0,
            "points": []
        }

        response = self.client.post(
            "/api/analytics/payoff",
            json={
                "option_parameters": self.parameters,
                "premium_per_share": 10.0,
                "lot_size": 500
            }
        )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()

        self.assertIn("payoff_analysis", data)

        self.assertEqual(
            data["payoff_analysis"]["break_even_stock_price"],
            110.0
        )

    @patch("web.stage17_routes.get_market_data_status")
    @patch("web.stage17_routes.analyze_option_strategy")
    def test_strategy_endpoint(
        self,
        mock_strategy,
        mock_market_status
    ):
        mock_market_status.return_value = {
            "status": "fresh",

            "raw": {
                "latest_date": "2026-11-20"
            },

            "warnings": []
        }

        mock_strategy.return_value = {
            "strategy": "bull_call_spread",
            "legs": [],
            "maximum_profit": 500.0,
            "maximum_profit_label": "Finite",
            "maximum_loss": 500.0,
            "maximum_loss_label": "Finite",
            "break_even_prices": [102.5],
            "points": []
        }

        response = self.client.post(
            "/api/strategies/analyze",
            json={
                "option_parameters": self.parameters,
                "symbol": "RELIANCE",
                "expiry_date": "2026-12-29",
                "reference_date": "2026-11-20",
                "strategy": "bull_call_spread",
                "lower_strike": 95.0,
                "upper_strike": 105.0,
                "lots": 1
            }
        )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()

        self.assertIn("strategy_analysis", data)

        self.assertEqual(
            data["strategy_analysis"]["strategy"],
            "bull_call_spread"
        )

    def test_strategy_endpoint_rejects_missing_parameters(self):

        response = self.client.post(
            "/api/strategies/analyze",
            json={
                "strategy": "long_call"
            }
        )

        self.assertEqual(response.status_code, 400)

    def test_strategy_endpoint_rejects_json_null(self):

        response = self.client.post(
            "/api/strategies/analyze",
            data="null",
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)

        data = response.get_json()

        self.assertEqual(
            data["error"]["code"],
            "invalid_request"
        )


    def test_strategy_endpoint_rejects_json_array(self):

        response = self.client.post(
            "/api/strategies/analyze",
            data="[]",
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)

        data = response.get_json()

        self.assertEqual(
            data["error"]["code"],
            "invalid_request"
        )

    def test_payoff_endpoint_rejects_missing_option_parameters(self):

        response = self.client.post(
            "/api/analytics/payoff",
            json={
                "premium_per_share": 10.0,
                "lot_size": 500
            }
        )

        self.assertEqual(response.status_code, 400)

    @patch("web.stage17_routes.get_market_data_status")
    @patch("web.stage17_routes.analyze_option_strategy")
    def test_strategy_endpoint_uses_server_reference_date(
        self,
        mock_strategy,
        mock_market_status
    ):

        mock_market_status.return_value = {
            "status": "fresh",

            "raw": {
                "latest_date": "2026-11-20"
            },

            "warnings": []
        }

        mock_strategy.return_value = {
            "strategy": "long_call",
            "legs": [],
            "maximum_profit": None,
            "maximum_profit_label": "Unlimited",
            "maximum_loss": 500.0,
            "maximum_loss_label": "Finite",
            "break_even_prices": [],
            "points": []
        }

        response = self.client.post(
            "/api/strategies/analyze",
            json={
                "option_parameters": self.parameters,
                "symbol": "RELIANCE",
                "expiry_date": "2026-12-29",

                # Deliberately supply an old date.
                # The server must ignore it.
                "reference_date": "2000-01-01",

                "strategy": "long_call",
                "lower_strike": 100.0,
                "lots": 1
            }
        )

        self.assertEqual(
            response.status_code,
            200
        )

        expected_reference_date = max(
            date.today(),
            date.fromisoformat("2026-11-20")
        ).isoformat()

        actual_reference_date = (
            mock_strategy.call_args.kwargs["reference_date"]
        )

        self.assertEqual(
            actual_reference_date,
            expected_reference_date
        )


    @patch("web.stage17_routes.get_market_data_status")
    @patch("web.stage17_routes.analyze_option_strategy")
    def test_strategy_endpoint_rejects_mismatched_market_data(
        self,
        mock_strategy,
        mock_market_status
    ):

        mock_market_status.return_value = {
            "status": "date_mismatch",

            "raw": {
                "latest_date": "2026-11-20"
            },

            "warnings": [
                "Raw and adjusted datasets have different latest dates."
            ]
        }

        response = self.client.post(
            "/api/strategies/analyze",
            json={
                "option_parameters": self.parameters,
                "symbol": "RELIANCE",
                "expiry_date": "2026-12-29",
                "strategy": "long_call",
                "lower_strike": 100.0,
                "lots": 1
            }
        )

        self.assertEqual(
            response.status_code,
            422
        )

        data = response.get_json()

        self.assertEqual(
            data["error"]["code"],
            "market_data_invalid"
        )

        mock_strategy.assert_not_called()



if __name__ == "__main__":
    unittest.main()



    