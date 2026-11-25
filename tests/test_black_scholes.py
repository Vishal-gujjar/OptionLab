import unittest

from web.services.black_scholes import price_option_black_scholes


class TestBlackScholes(unittest.TestCase):

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

    def test_european_call_price(self):
        result = price_option_black_scholes(self.parameters)

        self.assertAlmostEqual(
            result["estimated_price"],
            10.4505835722,
            places=6
        )

    def test_european_put_price(self):
        parameters = self.parameters.copy()
        parameters["option_type"] = "put"

        result = price_option_black_scholes(parameters)

        self.assertAlmostEqual(
            result["estimated_price"],
            5.5735260223,
            places=6
        )

    def test_put_call_parity_with_dividend(self):
        call_parameters = self.parameters.copy()
        call_parameters["dividend_yield"] = 0.02

        put_parameters = call_parameters.copy()
        put_parameters["option_type"] = "put"

        call_price = price_option_black_scholes(
            call_parameters
        )["estimated_price"]

        put_price = price_option_black_scholes(
            put_parameters
        )["estimated_price"]

        spot = call_parameters["spot_price"]
        strike = call_parameters["strike_price"]
        rate = call_parameters["risk_free_rate"]
        dividend = call_parameters["dividend_yield"]
        maturity = call_parameters["time_to_expiry_years"]

        expected_difference = (
            spot * __import__("math").exp(-dividend * maturity)
            - strike * __import__("math").exp(-rate * maturity)
        )

        self.assertAlmostEqual(
            call_price - put_price,
            expected_difference,
            places=8
        )

    def test_zero_maturity_call(self):
        parameters = self.parameters.copy()
        parameters["time_to_expiry_years"] = 0.0
        parameters["spot_price"] = 110.0
        parameters["strike_price"] = 100.0

        result = price_option_black_scholes(parameters)

        self.assertAlmostEqual(
            result["estimated_price"], 10.0
        )
        self.assertIsNone(result["d1"])
        self.assertIsNone(result["d2"])

    def test_zero_maturity_put(self):
        parameters = self.parameters.copy()
        parameters["time_to_expiry_years"] = 0.0
        parameters["spot_price"] = 90.0
        parameters["strike_price"] = 100.0
        parameters["option_type"] = "put"

        result = price_option_black_scholes(parameters)

        self.assertAlmostEqual(
            result["estimated_price"], 10.0
        )

    def test_zero_volatility_call(self):
        parameters = self.parameters.copy()
        parameters["volatility"] = 0.0
        parameters["strike_price"] = 95.0

        result = price_option_black_scholes(parameters)

        self.assertGreater(result["estimated_price"], 0.0)

    def test_zero_volatility_put(self):
        parameters = self.parameters.copy()
        parameters["volatility"] = 0.0
        parameters["strike_price"] = 110.0
        parameters["option_type"] = "put"

        result = price_option_black_scholes(parameters)

        self.assertGreater(result["estimated_price"], 0.0)

    def test_invalid_spot_price(self):
        parameters = self.parameters.copy()
        parameters["spot_price"] = 0.0

        with self.assertRaises(ValueError):
            price_option_black_scholes(parameters)

    def test_negative_volatility(self):
        parameters = self.parameters.copy()
        parameters["volatility"] = -0.1

        with self.assertRaises(ValueError):
            price_option_black_scholes(parameters)

    def test_invalid_option_type(self):
        parameters = self.parameters.copy()
        parameters["option_type"] = "asian"

        with self.assertRaises(ValueError):
            price_option_black_scholes(parameters)

    def test_non_finite_input(self):
        parameters = self.parameters.copy()
        parameters["risk_free_rate"] = float("nan")

        with self.assertRaises(ValueError):
            price_option_black_scholes(parameters)


if __name__ == "__main__":
    unittest.main()