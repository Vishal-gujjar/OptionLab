import unittest

from web.services.greeks import (
    calculate_greeks,
    calculate_numerical_greeks,
    compare_greeks
)


class TestOptionGreeks(unittest.TestCase):

    def setUp(self):
        self.call_parameters = {
            "spot_price": 100.0,
            "strike_price": 100.0,
            "risk_free_rate": 0.05,
            "dividend_yield": 0.0,
            "volatility": 0.20,
            "time_to_expiry_years": 1.0,
            "option_type": "call"
        }

    def test_known_call_greeks(self):
        result = calculate_greeks(self.call_parameters)

        self.assertAlmostEqual(
            result["delta"],
            0.636830651,
            places=7
        )

        self.assertAlmostEqual(
            result["gamma"],
            0.018762017,
            places=7
        )

        self.assertAlmostEqual(
            result["vega_per_1_00_volatility"],
            37.52403469,
            places=6
        )

        self.assertAlmostEqual(
            result["theta_per_year"],
            -6.41402755,
            places=6
        )

        self.assertAlmostEqual(
            result["rho_per_1_00_rate"],
            53.23248155,
            places=6
        )

    def test_known_put_greeks(self):
        parameters = self.call_parameters.copy()
        parameters["option_type"] = "put"

        result = calculate_greeks(parameters)

        self.assertAlmostEqual(
            result["delta"],
            -0.363169349,
            places=7
        )

        self.assertAlmostEqual(
            result["gamma"],
            0.018762017,
            places=7
        )

        self.assertAlmostEqual(
            result["vega_per_1_00_volatility"],
            37.52403469,
            places=6
        )

        self.assertAlmostEqual(
            result["theta_per_year"],
            -1.65788042,
            places=6
        )

        self.assertAlmostEqual(
            result["rho_per_1_00_rate"],
            -41.89046090,
            places=6
        )

    def test_put_call_delta_relationship(self):
        call = calculate_greeks(self.call_parameters)

        put_parameters = self.call_parameters.copy()
        put_parameters["option_type"] = "put"

        put = calculate_greeks(put_parameters)

        # With q = 0, Call Delta - Put Delta = 1.
        self.assertAlmostEqual(
            call["delta"] - put["delta"],
            1.0,
            places=8
        )

    def test_call_and_put_have_same_gamma_and_vega(self):
        call = calculate_greeks(self.call_parameters)

        put_parameters = self.call_parameters.copy()
        put_parameters["option_type"] = "put"

        put = calculate_greeks(put_parameters)

        self.assertAlmostEqual(
            call["gamma"], put["gamma"], places=10
        )

        self.assertAlmostEqual(
            call["vega_per_1_00_volatility"],
            put["vega_per_1_00_volatility"],
            places=10
        )

    def test_vega_and_rho_scaling(self):
        result = calculate_greeks(self.call_parameters)

        self.assertAlmostEqual(
            result["vega_per_1_percentage_point"],
            result["vega_per_1_00_volatility"] / 100.0
        )

        self.assertAlmostEqual(
            result["rho_per_1_percentage_point"],
            result["rho_per_1_00_rate"] / 100.0
        )

    def test_theta_daily_scaling(self):
        result = calculate_greeks(self.call_parameters)

        self.assertAlmostEqual(
            result["theta_per_calendar_day"],
            result["theta_per_year"] / 365.0
        )

    def test_numerical_greeks_match_analytical_greeks(self):
        analytical = calculate_greeks(self.call_parameters)

        numerical = calculate_numerical_greeks(
            self.call_parameters
        )

        self.assertAlmostEqual(
            numerical["delta"],
            analytical["delta"],
            places=5
        )

        self.assertAlmostEqual(
            numerical["gamma"],
            analytical["gamma"],
            places=5
        )

        self.assertAlmostEqual(
            numerical["vega_per_1_00_volatility"],
            analytical["vega_per_1_00_volatility"],
            places=5
        )

        self.assertAlmostEqual(
            numerical["theta_per_year"],
            analytical["theta_per_year"],
            places=5
        )

        self.assertAlmostEqual(
            numerical["rho_per_1_00_rate"],
            analytical["rho_per_1_00_rate"],
            places=5
        )

    def test_greek_comparison_reports_errors(self):
        analytical = calculate_greeks(self.call_parameters)

        numerical = calculate_numerical_greeks(
            self.call_parameters
        )

        comparison = compare_greeks(
            analytical, numerical
        )

        self.assertIn("delta", comparison)
        self.assertIn("gamma", comparison)
        self.assertIn("vega_per_1_00_volatility", comparison)
        self.assertIn("theta_per_year", comparison)
        self.assertIn("rho_per_1_00_rate", comparison)

        self.assertGreaterEqual(
            comparison["delta"]["absolute_difference"],
            0.0
        )

    def test_zero_maturity_is_rejected(self):
        parameters = self.call_parameters.copy()
        parameters["time_to_expiry_years"] = 0.0

        with self.assertRaises(ValueError):
            calculate_greeks(parameters)

    def test_zero_volatility_is_rejected(self):
        parameters = self.call_parameters.copy()
        parameters["volatility"] = 0.0

        with self.assertRaises(ValueError):
            calculate_greeks(parameters)


if __name__ == "__main__":
    unittest.main()



    