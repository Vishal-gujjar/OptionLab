import math

from web.services.black_scholes import (
    price_option_black_scholes
)


SCENARIO_MULTIPLIERS = [
    0.90,
    0.95,
    1.00,
    1.05,
    1.10
]

# When the base volatility is zero, relative percentage
# changes cannot create different volatility scenarios.
#
# Therefore, use absolute one-percentage-point increments:
# 0%, 1%, 2%, 3%, 4%.
ZERO_VOLATILITY_SCENARIOS = [
    0.00,
    0.01,
    0.02,
    0.03,
    0.04
]


def calculate_sensitivity(parameters):
    """
    Calculate Black-Scholes option-price sensitivity
    to spot price, volatility and time to expiry.

    Each variable is changed independently.

    Boundary behaviour:
        Zero volatility:
            Use absolute volatility scenarios from 0% to 4%.

        Zero maturity:
            Use 0 to 4 calendar days as maturity scenarios.
    """

    if not isinstance(parameters, dict):
        raise ValueError(
            "Option parameters must be a dictionary."
        )

    try:

        base_spot = float(parameters["spot_price"])

        base_volatility = float(
            parameters["volatility"]
        )

        base_maturity = float(
            parameters["time_to_expiry_years"]
        )

    except (KeyError, TypeError, ValueError, OverflowError):

        raise ValueError(
            "Invalid sensitivity-analysis parameters."
        ) from None

    if not all(
        math.isfinite(value)
        for value in (
            base_spot,
            base_volatility,
            base_maturity
        )
    ):
        raise ValueError(
            "Sensitivity parameters must be finite."
        )

    if base_spot <= 0:
        raise ValueError(
            "Spot price must be positive."
        )

    if base_volatility < 0:
        raise ValueError(
            "Volatility cannot be negative."
        )

    if base_maturity < 0:
        raise ValueError(
            "Time to expiry cannot be negative."
        )

    # --------------------------------------------------
    # 1. Spot-price sensitivity
    # --------------------------------------------------

    spot_scenarios = []

    for multiplier in SCENARIO_MULTIPLIERS:

        scenario = parameters.copy()

        scenario_spot = base_spot * multiplier

        scenario["spot_price"] = scenario_spot

        price = price_option_black_scholes(
            scenario
        )["estimated_price"]

        spot_scenarios.append({
            "input_value": scenario_spot,
            "option_price": price
        })

    # The base spot scenario remains the middle point.
    spot_base_index = 2

    # --------------------------------------------------
    # 2. Volatility sensitivity
    # --------------------------------------------------

    volatility_scenarios = []

    if base_volatility == 0:

        # A percentage multiplier of zero is always zero.
        # Use absolute one-percentage-point increments instead.
        volatility_values = ZERO_VOLATILITY_SCENARIOS

        volatility_base_index = 0

        volatility_method = (
            "Absolute one-percentage-point increments "
            "from zero volatility."
        )

    else:

        volatility_values = [
            base_volatility * multiplier
            for multiplier in SCENARIO_MULTIPLIERS
        ]

        volatility_base_index = 2

        volatility_method = (
            "Relative volatility multipliers around "
            "the base volatility."
        )

    for scenario_volatility in volatility_values:

        scenario = parameters.copy()

        scenario["volatility"] = scenario_volatility

        price = price_option_black_scholes(
            scenario
        )["estimated_price"]

        volatility_scenarios.append({
            "input_value": scenario_volatility * 100.0,
            "option_price": price
        })

    # --------------------------------------------------
    # 3. Time-to-expiry sensitivity
    # --------------------------------------------------

    maturity_scenarios = []

    if base_maturity == 0:

        # When maturity is zero, relative multipliers
        # cannot create different maturity scenarios.
        # Explore the first four calendar days instead.
        maturity_values = [
            day / 365.0
            for day in range(5)
        ]

        maturity_base_index = 0

        maturity_method = (
            "One-calendar-day increments from expiry."
        )

    else:

        maturity_values = [
            base_maturity * multiplier
            for multiplier in SCENARIO_MULTIPLIERS
        ]

        maturity_base_index = 2

        maturity_method = (
            "Relative maturity multipliers around "
            "the base time to expiry."
        )

    for scenario_maturity in maturity_values:

        scenario = parameters.copy()

        scenario["time_to_expiry_years"] = (
            scenario_maturity
        )

        price = price_option_black_scholes(
            scenario
        )["estimated_price"]

        maturity_scenarios.append({
            "input_value": scenario_maturity,
            "option_price": price
        })

    # --------------------------------------------------
    # 4. Return sensitivity data
    # --------------------------------------------------

    return {
        "spot_price": {
            "label": "Spot Price",

            "x_axis_label": "Spot Price (₹)",

            "base_scenario_index": spot_base_index,

            "data": spot_scenarios
        },

        "volatility": {
            "label": "Annualized Volatility",

            "x_axis_label": "Volatility (%)",

            "base_scenario_index": volatility_base_index,

            "scenario_method": volatility_method,

            "data": volatility_scenarios
        },

        "time_to_expiry": {
            "label": "Time to Expiry",

            "x_axis_label": "Time to Expiry (Years)",

            "base_scenario_index": maturity_base_index,

            "scenario_method": maturity_method,

            "data": maturity_scenarios
        }
    }




