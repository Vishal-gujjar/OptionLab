import unittest
from unittest.mock import patch

from web.app import create_app


class TestStage16API(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

        self.sample_status = {
            "symbol": "RELIANCE",
            "exchange": "NSE",
            "reference_date": "2026-11-20",
            "status": "fresh",
            "dates_match": True,
            "raw_age_calendar_days": 0,
            "adjusted_age_calendar_days": 0,
            "raw": {
                "available": True,
                "valid": True,
                "start_date": "2025-11-20",
                "latest_date": "2026-11-20",
                "observations": 248,
                "last_retrieved_at_utc": "2026-11-23T09:00:00+00:00",
                "latest_close": 1377.50,
                "error": None
            },
            "adjusted": {
                "available": True,
                "valid": True,
                "start_date": "2025-11-24",
                "latest_date": "2026-11-20",
                "observations": 247,
                "last_retrieved_at_utc": "2026-11-23T09:00:00+00:00",
                "latest_close": 1377.50,
                "error": None
            },
            "warnings": [],
            "freshness_policy": {
                "fresh_through_calendar_days": 4,
                "stale_after_calendar_days": 7
            }
        }

    @patch("web.app.get_available_symbols")
    def test_contract_symbols_endpoint(self, mock_symbols):
        mock_symbols.return_value = [
            "RELIANCE",
            "TCS"
        ]

        response = self.client.get(
            "/api/contracts/symbols"
        )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()

        self.assertEqual(data["count"], 2)
        self.assertEqual(
            data["symbols"],
            ["RELIANCE", "TCS"]
        )

    @patch("web.app.get_available_expiries")
    @patch("web.app.get_market_data_status")
    def test_contract_expiries_endpoint(
        self,
        mock_status,
        mock_expiries
    ):
        mock_status.return_value = self.sample_status

        mock_expiries.return_value = [
            "2026-11-23",
            "2026-12-29"
        ]

        response = self.client.get(
            "/api/contracts/expiries?symbol=RELIANCE"
        )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()

        self.assertEqual(
            data["expiries"],
            ["2026-11-23", "2026-12-29"]
        )

    @patch("web.app.get_available_strikes")
    @patch("web.app.get_market_data_status")
    def test_contract_strikes_endpoint(
        self,
        mock_status,
        mock_strikes
    ):
        mock_status.return_value = self.sample_status

        mock_strikes.return_value = [
            1370,
            1380,
            1390,
            1400
        ]

        response = self.client.get(
            "/api/contracts/strikes"
            "?symbol=RELIANCE"
            "&expiry_date=2026-11-23"
            "&option_type=call"
        )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()

        self.assertEqual(
            data["strikes"],
            [1370, 1380, 1390, 1400]
        )

    @patch("web.app.validate_option_contract")
    @patch("web.app.get_market_data_status")
    def test_contract_validation_endpoint(
        self,
        mock_status,
        mock_validate
    ):
        mock_status.return_value = self.sample_status

        mock_validate.return_value = {
            "valid": True,
            "contract_id": "126008",
            "symbol": "RELIANCE",
            "expiry_date": "2026-11-23",
            "strike_price": 1400.0,
            "option_type": "call",
            "exchange_option_type": "CE",
            "board_lot_quantity": 500,
            "tick_size": 0.05,
            "permitted_to_trade": True,
            "source_file_date": "2026-11-20"
        }

        response = self.client.post(
            "/api/contracts/validate",
            json={
                "symbol": "RELIANCE",
                "expiry_date": "2026-11-23",
                "strike_price": 1400,
                "option_type": "call"
            }
        )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()

        self.assertTrue(data["contract"]["valid"])
        self.assertEqual(
            data["contract"]["contract_id"],
            "126008"
        )

    @patch("web.app.get_market_data_status")
    def test_market_status_endpoint(self, mock_status):
        mock_status.return_value = self.sample_status

        response = self.client.get(
            "/api/market-data/status?symbol=RELIANCE"
        )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()

        self.assertEqual(
            data["market_data"]["status"],
            "fresh"
        )

    @patch("web.app.refresh_market_data")
    @patch("web.app.get_available_symbols")
    def test_market_refresh_endpoint(
        self,
        mock_symbols,
        mock_refresh
    ):
        mock_symbols.return_value = [
            "RELIANCE",
            "TCS"
        ]

        mock_refresh.return_value = {
            "symbol": "RELIANCE",
            "exchange": "NSE",
            "raw_rows_received": 4,
            "adjusted_rows_received": 4,
            "raw_updated": True,
            "adjusted_updated": True
        }

        response = self.client.post(
            "/api/market-data/refresh",
            json={
                "symbol": "RELIANCE",
                "exchange": "nse",
                "lookback_days": 365
            }
        )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()

        self.assertEqual(
            data["refresh"]["symbol"],
            "RELIANCE"
        )

        mock_refresh.assert_called_once()

    @patch("web.app.get_available_symbols")
    def test_refresh_rejects_unknown_symbol(self, mock_symbols):
        mock_symbols.return_value = [
            "RELIANCE",
            "TCS"
        ]

        response = self.client.post(
            "/api/market-data/refresh",
            json={
                "symbol": "UNKNOWN",
                "lookback_days": 365
            }
        )

        self.assertEqual(response.status_code, 400)

    @patch("web.app.calculate_lot_values")
    @patch("web.app.price_from_market_data")
    @patch("web.app.validate_option_contract")
    @patch("web.app.get_market_data_status")
    def test_pricing_returns_contract_and_lot_values(
        self,
        mock_status,
        mock_contract,
        mock_workflow,
        mock_lot
    ):
        mock_status.return_value = self.sample_status

        mock_contract.return_value = {
            "valid": True,
            "contract_id": "126008",
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

        mock_workflow.return_value = {
            "market_data": {
                "symbol": "RELIANCE",
                "exchange": "NSE",
                "spot_price": 1377.50,
                "spot_date": "2026-11-20"
            },
            "maturity_info": {},
            "volatility_info": {},
            "financial_assumptions": {},
            "option_parameters": {},
            "pricing_result": {
                "estimated_price": 10.0,
                "standard_error": 0.2,
                "confidence_interval_lower": 9.608,
                "confidence_interval_upper": 10.392,
                "simulations": 100000
            },
            "benchmark_result": {
                "model": "Black-Scholes-Merton",
                "estimated_price": 9.8
            },
            "comparison_result": {
                "absolute_error": 0.2,
                "confidence_interval_contains_benchmark": True
            },
            "greeks_result": {},
            "numerical_greeks_result": {},
            "greeks_validation_result": {},
            "sensitivity_result": {}
        }

        mock_lot.return_value = {
            "contract": {
                "board_lot_quantity": 500
            },
            "theoretical_premium_per_lot": 5000.0,
            "analytical_premium_per_lot": 4900.0
        }

        response = self.client.post(
            "/api/price",
            json={
                "symbol": "RELIANCE",
                "strike_price": 1400,
                "risk_free_rate": 0.06,
                "dividend_yield": 0.0,
                "expiry_date": "2026-12-29",
                "option_type": "call",
                "volatility_mode": "historical",
                "simulations": 100000,
                "seed": 42
            }
        )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()

        self.assertIn("contract_metadata", data)
        self.assertIn("contract_master_status", data)
        self.assertIn("market_data_status", data)
        self.assertIn("lot_valuation", data)
        self.assertIn("warnings", data)

        self.assertEqual(
            data["lot_valuation"]["theoretical_premium_per_lot"],
            5000.0
        )

    @patch("web.app.validate_option_contract")
    @patch("web.app.get_market_data_status")
    def test_pricing_rejects_unlisted_contract(
        self,
        mock_status,
        mock_contract
    ):
        mock_status.return_value = self.sample_status

        mock_contract.side_effect = ValueError(
            "The selected option contract was not found."
        )

        response = self.client.post(
            "/api/price",
            json={
                "symbol": "RELIANCE",
                "strike_price": 1425,
                "risk_free_rate": 0.06,
                "dividend_yield": 0.0,
                "expiry_date": "2026-12-29",
                "option_type": "call",
                "volatility_mode": "historical"
            }
        )

        self.assertEqual(response.status_code, 422)

        data = response.get_json()

        self.assertEqual(
            data["status"],
            "error"
        )

    @patch("web.app.get_market_data_status")
    def test_pricing_rejects_date_mismatch(self, mock_status):

        status = self.sample_status.copy()

        status["status"] = "date_mismatch"

        status["warnings"] = [
            "Raw and adjusted datasets have different latest dates."
        ]

        mock_status.return_value = status

        response = self.client.post(
            "/api/price",
            json={
                "symbol": "RELIANCE",
                "strike_price": 1400,
                "risk_free_rate": 0.06,
                "dividend_yield": 0.0,
                "expiry_date": "2026-12-29",
                "option_type": "call",
                "volatility_mode": "historical"
            }
        )

        self.assertEqual(
            response.status_code,
            422
        )

        data = response.get_json()

        self.assertEqual(
            data["error"]["code"],
            "pricing_error"
        )


    @patch("web.app.get_market_data_status")
    def test_pricing_rejects_invalid_market_data(self, mock_status):

        status = self.sample_status.copy()

        status["status"] = "invalid"

        status["warnings"] = [
            "Market data contains NaN or Infinity."
        ]

        mock_status.return_value = status

        response = self.client.post(
            "/api/price",
            json={
                "symbol": "RELIANCE",
                "strike_price": 1400,
                "risk_free_rate": 0.06,
                "dividend_yield": 0.0,
                "expiry_date": "2026-12-29",
                "option_type": "call",
                "volatility_mode": "historical"
            }
        )

        self.assertEqual(
            response.status_code,
            422
        )

        data = response.get_json()

        self.assertEqual(
            data["error"]["code"],
            "pricing_error"
        )


if __name__ == "__main__":
    unittest.main()