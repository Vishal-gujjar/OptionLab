import unittest
from unittest.mock import patch

from web.services.option_workflow import price_from_market_data


class OptionWorkflowTests(unittest.TestCase):

    def setUp(self):

        self.market_data = {
            "symbol": "RELIANCE",
            "exchange": "NSE",
            "spot_price": 1377.5,
            "spot_date": "2026-11-20",
            "volatility": 0.245170095,
            "volatility_percent": 24.517,
            "volatility_start_date": "2025-11-24",
            "volatility_end_date": "2026-11-20",
            "price_observations": 247,
            "volatility_method": "Historical volatility",
            "annualization_days": 252
        }

        self.pricing_result = {
            "estimated_price": 104.97,
            "standard_error": 0.51,
            "confidence_interval_lower": 103.97,
            "confidence_interval_upper": 105.98,
            "simulations": 100000
        }

    @patch("web.services.option_workflow.price_option")
    @patch("web.services.option_workflow.load_market_inputs")
    def test_complete_pricing_workflow(
        self,
        mock_load_market,
        mock_price
    ):

        mock_load_market.return_value = self.market_data
        mock_price.return_value = self.pricing_result

        result = price_from_market_data(
            symbol="RELIANCE",
            strike_price=1400,
            risk_free_rate=0.06,
            dividend_yield=0,
            time_to_expiry_years=0.5,
            option_type="call"
        )

        self.assertEqual(
            result["market_data"]["spot_price"],
            1377.5
        )

        self.assertEqual(
            result["option_parameters"]["volatility"],
            self.market_data["volatility"]
        )

        self.assertEqual(
            result["pricing_result"]["estimated_price"],
            104.97
        )

        mock_price.assert_called_once()

    @patch("web.services.option_workflow.price_option")
    @patch("web.services.option_workflow.load_market_inputs")
    def test_expiry_date_calculates_maturity(
        self,
        mock_load_market,
        mock_price
    ):

        mock_load_market.return_value = self.market_data
        mock_price.return_value = self.pricing_result

        result = price_from_market_data(
            symbol="RELIANCE",
            strike_price=1400,
            risk_free_rate=0.06,
            dividend_yield=0,
            time_to_expiry_years=None,
            expiry_date="2026-11-24",
            option_type="call"
        )

        maturity = result["option_parameters"][
            "time_to_expiry_years"
        ]

        self.assertAlmostEqual(
            maturity,
            4 / 365
        )

        self.assertEqual(
            result["maturity_info"]["calendar_days_to_expiry"],
            4
        )

        self.assertEqual(
            result["maturity_info"]["expiry_date"],
            "2026-11-24"
        )

        mock_price.assert_called_once()

    @patch("web.services.option_workflow.price_option")
    @patch("web.services.option_workflow.load_market_inputs")
    def test_put_option_is_passed_correctly(
        self,
        mock_load_market,
        mock_price
    ):

        mock_load_market.return_value = self.market_data
        mock_price.return_value = self.pricing_result

        result = price_from_market_data(
            symbol="RELIANCE",
            strike_price=1400,
            risk_free_rate=0.06,
            dividend_yield=0,
            time_to_expiry_years=0.5,
            option_type="put"
        )

        self.assertEqual(
            result["option_parameters"]["option_type"],
            "put"
        )

        mock_price.assert_called_once()

    @patch("web.services.option_workflow.price_option")
    @patch("web.services.option_workflow.load_market_inputs")
    def test_expiry_before_valuation_date_is_rejected(
        self,
        mock_load_market,
        mock_price
    ):

        mock_load_market.return_value = self.market_data

        with self.assertRaises(ValueError):

            price_from_market_data(
                symbol="RELIANCE",
                strike_price=1400,
                risk_free_rate=0.06,
                dividend_yield=0,
                time_to_expiry_years=None,
                expiry_date="2026-11-19",
                option_type="call"
            )

        mock_price.assert_not_called()


    
    @patch("web.services.option_workflow.price_option")
    @patch("web.services.option_workflow.load_market_inputs")
    def test_manual_volatility_mode(
        self,
        mock_load_market,
        mock_price
    ):

        mock_load_market.return_value = self.market_data
        mock_price.return_value = self.pricing_result

        result = price_from_market_data(
            symbol="RELIANCE",
            strike_price=1400,
            risk_free_rate=0.06,
            dividend_yield=0,
            time_to_expiry_years=0.5,
            option_type="call",
            volatility_mode="manual",
            manual_volatility=0.30
        )

        self.assertAlmostEqual(
            result["option_parameters"]["volatility"],
            0.30
        )

        self.assertEqual(
            result["volatility_info"]["mode"],
            "manual"
        )

        self.assertEqual(
            result["volatility_info"]["method"],
            "Manual volatility assumption"
        )

        mock_price.assert_called_once()


    @patch("web.services.option_workflow.price_option")
    @patch("web.services.option_workflow.load_market_inputs")
    def test_manual_volatility_requires_value(
        self,
        mock_load_market,
        mock_price
    ):

        mock_load_market.return_value = self.market_data

        with self.assertRaises(ValueError):

            price_from_market_data(
                symbol="RELIANCE",
                strike_price=1400,
                risk_free_rate=0.06,
                dividend_yield=0,
                time_to_expiry_years=0.5,
                option_type="call",
                volatility_mode="manual"
            )

        mock_price.assert_not_called()


    @patch("web.services.option_workflow.price_option")
    @patch("web.services.option_workflow.load_market_inputs")
    def test_historical_volatility_remains_default(
        self,
        mock_load_market,
        mock_price
    ):

        mock_load_market.return_value = self.market_data
        mock_price.return_value = self.pricing_result

        result = price_from_market_data(
            symbol="RELIANCE",
            strike_price=1400,
            risk_free_rate=0.06,
            dividend_yield=0,
            time_to_expiry_years=0.5,
            option_type="call"
        )

        self.assertEqual(
            result["volatility_info"]["mode"],
            "historical"
        )

        self.assertAlmostEqual(
            result["option_parameters"]["volatility"],
            self.market_data["volatility"]
        )

        mock_price.assert_called_once()

    @patch("web.services.option_workflow.price_option")
    @patch("web.services.option_workflow.load_market_inputs")
    def test_financial_assumptions_are_described(
        self,
        mock_load_market,
        mock_price
    ):

        mock_load_market.return_value = self.market_data
        mock_price.return_value = self.pricing_result

        result = price_from_market_data(
            symbol="RELIANCE",
            strike_price=1400,
            risk_free_rate=0.06,
            dividend_yield=0.01,
            time_to_expiry_years=0.5,
            option_type="call"
        )

        assumptions = result["financial_assumptions"]

        self.assertAlmostEqual(
            assumptions["risk_free_rate_percent"],
            6.0
        )

        self.assertAlmostEqual(
            assumptions["dividend_yield_percent"],
            1.0
        )

        self.assertEqual(
            assumptions["risk_free_rate_convention"],
            "Annualized continuously compounded rate"
        )

        self.assertEqual(
            assumptions["dividend_yield_convention"],
            "Annualized continuous dividend yield"
        )

        mock_price.assert_called_once()

    @patch("web.services.option_workflow.price_option")
    @patch("web.services.option_workflow.load_market_inputs")
    def test_zero_historical_volatility_completes_without_greeks(
        self,
        mock_load_market,
        mock_price
    ):

        market_data = self.market_data.copy()

        market_data["volatility"] = 0.0

        market_data["volatility_percent"] = 0.0

        mock_load_market.return_value = market_data

        mock_price.return_value = self.pricing_result

        result = price_from_market_data(
            symbol="RELIANCE",
            strike_price=1400,
            risk_free_rate=0.06,
            dividend_yield=0.0,
            time_to_expiry_years=0.5,
            option_type="call"
        )

        # Pricing must still complete.
        mock_price.assert_called_once()

        self.assertEqual(
            result["option_parameters"]["volatility"],
            0.0
        )

        # Analytical Greeks must be marked unavailable.
        self.assertFalse(
            result["greeks_result"]["available"]
        )

        # Numerical Greeks must also be unavailable.
        self.assertFalse(
            result["numerical_greeks_result"]["available"]
        )

        # Greek comparison must be unavailable.
        self.assertFalse(
            result["greeks_validation_result"]["available"]
        )

        self.assertIn(
            "zero volatility",
            result["greeks_result"]["reason"].lower()
        )

        # Sensitivity analysis must still complete.
        self.assertEqual(
            len(
                result["sensitivity_result"][
                    "volatility"
                ]["data"]
            ),
            5
        )


    @patch("web.services.option_workflow.price_option")
    @patch("web.services.option_workflow.load_market_inputs")
    def test_zero_maturity_completes_without_greeks(
        self,
        mock_load_market,
        mock_price
    ):

        mock_load_market.return_value = self.market_data

        mock_price.return_value = self.pricing_result

        result = price_from_market_data(
            symbol="RELIANCE",
            strike_price=1400,
            risk_free_rate=0.06,
            dividend_yield=0.0,
            time_to_expiry_years=0.0,
            option_type="call"
        )

        mock_price.assert_called_once()

        self.assertEqual(
            result["option_parameters"]["time_to_expiry_years"],
            0.0
        )

        self.assertFalse(
            result["greeks_result"]["available"]
        )

        self.assertIn(
            "at expiry",
            result["greeks_result"]["reason"].lower()
        )

        # Sensitivity analysis should still work at expiry.
        maturity_data = result["sensitivity_result"][
            "time_to_expiry"
        ]["data"]

        self.assertEqual(
            len(maturity_data),
            5
        )

        self.assertEqual(
            result["sensitivity_result"][
                "time_to_expiry"
            ]["base_scenario_index"],
            0
        )


if __name__ == "__main__":
    unittest.main()




    