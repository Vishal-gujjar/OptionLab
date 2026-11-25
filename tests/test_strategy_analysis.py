import unittest
from unittest.mock import patch

from web.services.strategy_analysis import (
    analyze_option_strategy
)
from web.services.black_scholes import (
    price_option_black_scholes
)

class TestStrategyAnalysis(unittest.TestCase):

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

    @staticmethod
    def contract_result(symbol, expiry, strike, option_type):
        return {
            "valid": True,
            "contract_id": (
                f"{symbol}-{expiry}-{strike}-{option_type}"
            ),
            "symbol": symbol,
            "expiry_date": expiry,
            "strike_price": float(strike),
            "option_type": option_type,
            "exchange_option_type": (
                "CE" if option_type == "call" else "PE"
            ),
            "board_lot_quantity": 100,
            "permitted_to_trade": True
        }

    @patch("web.services.strategy_analysis.validate_option_contract")
    def test_long_call_strategy(self, mock_validate):
        mock_validate.side_effect = (
            lambda symbol, expiry_date, strike_price,
            option_type, reference_date: self.contract_result(
                symbol, expiry_date, strike_price, option_type
            )
        )

        result = analyze_option_strategy(
            self.parameters,
            "RELIANCE",
            "2026-12-29",
            "2026-11-20",
            "long_call",
            100.0
        )

        self.assertEqual(result["strategy"], "long_call")
        self.assertEqual(len(result["legs"]), 1)
        self.assertEqual(result["legs"][0]["position"], "long")
        self.assertEqual(
            result["maximum_profit_label"],
            "Unlimited"
        )

    @patch("web.services.strategy_analysis.validate_option_contract")
    def test_long_put_strategy(self, mock_validate):
        mock_validate.side_effect = (
            lambda symbol, expiry_date, strike_price,
            option_type, reference_date: self.contract_result(
                symbol, expiry_date, strike_price, option_type
            )
        )

        result = analyze_option_strategy(
            self.parameters,
            "RELIANCE",
            "2026-12-29",
            "2026-11-20",
            "long_put",
            100.0
        )

        self.assertEqual(result["legs"][0]["option_type"], "put")
        self.assertEqual(
            result["maximum_profit_label"],
            "Finite"
        )

    @patch("web.services.strategy_analysis.validate_option_contract")
    def test_bull_call_spread(self, mock_validate):
        mock_validate.side_effect = (
            lambda symbol, expiry_date, strike_price,
            option_type, reference_date: self.contract_result(
                symbol, expiry_date, strike_price, option_type
            )
        )

        result = analyze_option_strategy(
            self.parameters,
            "RELIANCE",
            "2026-12-29",
            "2026-11-20",
            "bull_call_spread",
            95.0,
            105.0
        )

        self.assertEqual(len(result["legs"]), 2)

        self.assertEqual(
            result["legs"][0]["position"],
            "long"
        )

        self.assertEqual(
            result["legs"][1]["position"],
            "short"
        )

        self.assertEqual(
            result["maximum_profit_label"],
            "Finite"
        )

    @patch("web.services.strategy_analysis.validate_option_contract")
    def test_bear_put_spread(self, mock_validate):
        mock_validate.side_effect = (
            lambda symbol, expiry_date, strike_price,
            option_type, reference_date: self.contract_result(
                symbol, expiry_date, strike_price, option_type
            )
        )

        result = analyze_option_strategy(
            self.parameters,
            "RELIANCE",
            "2026-12-29",
            "2026-11-20",
            "bear_put_spread",
            95.0,
            105.0
        )

        self.assertEqual(len(result["legs"]), 2)

        self.assertEqual(
            result["legs"][0]["option_type"],
            "put"
        )

        self.assertEqual(
            result["legs"][0]["position"],
            "short"
        )

        self.assertEqual(
            result["legs"][1]["position"],
            "long"
        )

    def test_unsupported_strategy_is_rejected(self):
        with self.assertRaises(ValueError):
            analyze_option_strategy(
                self.parameters,
                "RELIANCE",
                "2026-12-29",
                "2026-11-20",
                "iron_condor",
                95.0,
                105.0
            )

    @patch("web.services.strategy_analysis.validate_option_contract")
    def test_invalid_spread_strike_order_is_rejected(
        self,
        mock_validate
    ):
        with self.assertRaises(ValueError):
            analyze_option_strategy(
                self.parameters,
                "RELIANCE",
                "2026-12-29",
                "2026-11-20",
                "bull_call_spread",
                110.0,
                100.0
            )

        mock_validate.assert_not_called()

    @patch("web.services.strategy_analysis.validate_option_contract")
    def test_unlisted_strategy_leg_is_rejected(
        self,
        mock_validate
    ):
        mock_validate.side_effect = ValueError(
            "The selected option contract was not found."
        )

        with self.assertRaises(ValueError):
            analyze_option_strategy(
                self.parameters,
                "RELIANCE",
                "2026-12-29",
                "2026-11-20",
                "long_call",
                100.0
            )

    @patch("web.services.strategy_analysis.validate_option_contract")
    def test_spread_validates_both_contracts(
        self,
        mock_validate
    ):
        mock_validate.side_effect = (
            lambda symbol, expiry_date, strike_price,
            option_type, reference_date: self.contract_result(
                symbol, expiry_date, strike_price, option_type
            )
        )

        result = analyze_option_strategy(
            self.parameters,
            "RELIANCE",
            "2026-12-29",
            "2026-11-20",
            "bull_call_spread",
            95.0,
            105.0,
            lots=2
        )

        self.assertEqual(mock_validate.call_count, 2)

        self.assertEqual(
            result["legs"][0]["total_units"],
            200
        )

        self.assertEqual(
            result["legs"][1]["total_units"],
            200
        )

    @patch("web.services.strategy_analysis.validate_option_contract")
    def test_strategy_returns_break_even_and_chart_points(
        self,
        mock_validate
    ):
        mock_validate.side_effect = (
            lambda symbol, expiry_date, strike_price,
            option_type, reference_date: self.contract_result(
                symbol, expiry_date, strike_price, option_type
            )
        )

        result = analyze_option_strategy(
            self.parameters,
            "RELIANCE",
            "2026-12-29",
            "2026-11-20",
            "bull_call_spread",
            95.0,
            105.0
        )

        self.assertIsInstance(
            result["break_even_prices"],
            list
        )

        self.assertGreaterEqual(
            len(result["points"]),
            100
        )

        self.assertIn(
            "initial_net_cashflow",
            result
        )

    @patch("web.services.strategy_analysis.validate_option_contract")
    def test_zero_volatility_strategy_is_supported(
        self,
        mock_validate
    ):

        mock_validate.side_effect = (
            lambda symbol, expiry_date, strike_price,
            option_type, reference_date: self.contract_result(
                symbol, expiry_date, strike_price, option_type
            )
        )

        parameters = self.parameters.copy()

        parameters["volatility"] = 0.0

        result = analyze_option_strategy(
            parameters,
            "RELIANCE",
            "2026-12-29",
            "2026-11-20",
            "long_call",
            100.0
        )

        self.assertEqual(
            result["strategy"],
            "long_call"
        )

        expected_price = price_option_black_scholes(
            {
                **parameters,
                "strike_price": 100.0,
                "option_type": "call"
            }
        )["estimated_price"]

        self.assertAlmostEqual(
            result["legs"][0]["premium_per_share"],
            expected_price,
            places=10
        )

        self.assertGreaterEqual(
            result["legs"][0]["premium_per_share"],
            0.0
        )

    @patch("web.services.strategy_analysis.validate_option_contract")
    def test_vertical_spread_rejects_unequal_board_lot_quantities(
        self,
        mock_validate
    ):

        def unequal_lot_contract(
            symbol,
            expiry_date,
            strike_price,
            option_type,
            reference_date
        ):

            contract = self.contract_result(
                symbol,
                expiry_date,
                strike_price,
                option_type
            )

            # Simulate a different board-lot quantity
            # for the second spread leg.
            if strike_price == 105.0:
                contract["board_lot_quantity"] = 150

            return contract

        mock_validate.side_effect = unequal_lot_contract

        with self.assertRaisesRegex(
            ValueError,
            "identical NSE board-lot quantities"
        ):

            analyze_option_strategy(
                self.parameters,
                "RELIANCE",
                "2026-12-29",
                "2026-11-20",
                "bull_call_spread",
                95.0,
                105.0,
                lots=1
            )

        self.assertEqual(
            mock_validate.call_count,
            2
        )


if __name__ == "__main__":
    unittest.main()




    