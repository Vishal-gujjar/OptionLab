import sys
import unittest

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PROJECT_ROOT))

from web.services.pricing_bridge import price_option


class PricingBridgeTests(unittest.TestCase):

    def setUp(self):

        self.parameters = {
            "spot_price": 271.86,
            "strike_price": 280.0,
            "risk_free_rate": 0.06,
            "dividend_yield": 0.0,
            "volatility": 0.321758,
            "time_to_expiry_years": 1.0,
            "option_type": "call",
            "simulations": 100000,
            "seed": 42,
        }

    def test_european_call(self):

        result = price_option(self.parameters)

        self.assertGreater(
            result["estimated_price"], 0
        )

        self.assertEqual(
            result["simulations"], 100000
        )

        self.assertLessEqual(
            result["confidence_interval_lower"],
            result["estimated_price"]
        )

        self.assertGreaterEqual(
            result["confidence_interval_upper"],
            result["estimated_price"]
        )

    def test_european_put(self):

        parameters = self.parameters.copy()

        parameters["option_type"] = "put"
        parameters["strike_price"] = 300.0

        result = price_option(parameters)

        self.assertGreater(
            result["estimated_price"], 0
        )

    def test_repeatability(self):

        first = price_option(self.parameters)
        second = price_option(self.parameters)

        self.assertEqual(first, second)

    def test_invalid_option_type(self):

        parameters = self.parameters.copy()

        parameters["option_type"] = "wrong"

        with self.assertRaises(ValueError):
            price_option(parameters)

    def test_invalid_volatility(self):

        parameters = self.parameters.copy()

        parameters["volatility"] = -0.5

        with self.assertRaises(ValueError):
            price_option(parameters)

    def test_missing_parameter(self):

        parameters = self.parameters.copy()

        del parameters["spot_price"]

        with self.assertRaises(ValueError):
            price_option(parameters)


if __name__ == "__main__":
    unittest.main()