import unittest

from web.services.black_scholes import (
    price_option_black_scholes
)

from web.services.sensitivity import (
    calculate_sensitivity
)


class TestSensitivityAnalysis(unittest.TestCase):

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

    def test_five_scenarios_are_generated(self):
        result = calculate_sensitivity(self.parameters)

        self.assertEqual(
            len(result["spot_price"]["data"]), 5
        )

        self.assertEqual(
            len(result["volatility"]["data"]), 5
        )

        self.assertEqual(
            len(result["time_to_expiry"]["data"]), 5
        )

    def test_base_scenario_matches_analytical_price(self):
        result = calculate_sensitivity(self.parameters)

        analytical_price = price_option_black_scholes(
            self.parameters
        )["estimated_price"]

        spot_base_price = result[
            "spot_price"
        ]["data"][2]["option_price"]

        volatility_index = result[
            "volatility"
        ]["base_scenario_index"]

        maturity_index = result[
            "time_to_expiry"
        ]["base_scenario_index"]

        volatility_base_price = result[
            "volatility"
        ]["data"][volatility_index]["option_price"]

        maturity_base_price = result[
            "time_to_expiry"
        ]["data"][maturity_index]["option_price"]

        self.assertAlmostEqual(
            spot_base_price, analytical_price, places=10
        )

        self.assertAlmostEqual(
            volatility_base_price, analytical_price, places=10
        )

        self.assertAlmostEqual(
            maturity_base_price, analytical_price, places=10
        )

    def test_call_price_increases_with_spot(self):
        result = calculate_sensitivity(self.parameters)

        prices = [
            point["option_price"]
            for point in result["spot_price"]["data"]
        ]

        self.assertEqual(
            prices, sorted(prices)
        )

    def test_put_price_decreases_with_spot(self):
        parameters = self.parameters.copy()
        parameters["option_type"] = "put"

        result = calculate_sensitivity(parameters)

        prices = [
            point["option_price"]
            for point in result["spot_price"]["data"]
        ]

        self.assertEqual(
            prices, sorted(prices, reverse=True)
        )

    def test_sensitivity_does_not_modify_input(self):
        original = self.parameters.copy()

        calculate_sensitivity(self.parameters)

        self.assertEqual(
            self.parameters, original
        )

    def test_zero_volatility_sensitivity(self):

        parameters = self.parameters.copy()

        parameters["volatility"] = 0.0

        result = calculate_sensitivity(parameters)

        volatility_data = result["volatility"]

        self.assertEqual(
            volatility_data["base_scenario_index"],
            0
        )

        self.assertEqual(
            [
                point["input_value"]
                for point in volatility_data["data"]
            ],
            [0.0, 1.0, 2.0, 3.0, 4.0]
        )

        base_price = price_option_black_scholes(
            parameters
        )["estimated_price"]

        self.assertAlmostEqual(
            volatility_data["data"][0]["option_price"],
            base_price,
            places=10
        )


    def test_zero_maturity_sensitivity(self):

        parameters = self.parameters.copy()

        parameters["time_to_expiry_years"] = 0.0

        result = calculate_sensitivity(parameters)

        maturity_data = result["time_to_expiry"]

        self.assertEqual(
            maturity_data["base_scenario_index"],
            0
        )

        self.assertEqual(
            len(maturity_data["data"]),
            5
        )

        expected_base_price = price_option_black_scholes(
            parameters
        )["estimated_price"]

        self.assertAlmostEqual(
            maturity_data["data"][0]["option_price"],
            expected_base_price,
            places=10
        )

        self.assertEqual(
            maturity_data["data"][0]["input_value"],
            0.0
        )


if __name__ == "__main__":
    unittest.main()
    