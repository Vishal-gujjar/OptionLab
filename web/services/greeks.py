import math

from web.services.black_scholes import (
    price_option_black_scholes
)


def _get_number(parameters, key):
    if key not in parameters:
        raise ValueError(f"Missing required parameter: {key}")

    value = parameters[key]

    if isinstance(value, bool):
        raise ValueError(f"{key} must be numeric.")

    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be numeric.")

    if not math.isfinite(value):
        raise ValueError(f"{key} must be finite.")

    return value


def _normal_cdf(x):
    return 0.5 * (
        1.0 + math.erf(x / math.sqrt(2.0))
    )


def _normal_pdf(x):
    return (
        math.exp(-0.5 * x * x)
        / math.sqrt(2.0 * math.pi)
    )


def calculate_greeks(parameters):
    """
    Calculate analytical European option Greeks
    using the Black-Scholes-Merton model.

    Greeks:
        Delta
        Gamma
        Vega
        Theta
        Rho

    Conventions:
        Vega: sensitivity per 1.00 volatility change.
        Theta: sensitivity per year of calendar time passing.
        Rho: sensitivity per 1.00 interest-rate change.
    """

    spot = _get_number(parameters, "spot_price")
    strike = _get_number(parameters, "strike_price")
    rate = _get_number(parameters, "risk_free_rate")
    dividend = _get_number(parameters, "dividend_yield")
    volatility = _get_number(parameters, "volatility")
    maturity = _get_number(
        parameters, "time_to_expiry_years"
    )

    option_type = str(
        parameters.get("option_type", "")
    ).strip().lower()

    if spot <= 0:
        raise ValueError("Spot price must be positive.")

    if strike <= 0:
        raise ValueError("Strike price must be positive.")

    if volatility <= 0:
        raise ValueError(
            "Greeks require positive volatility."
        )

    if maturity <= 0:
        raise ValueError(
            "Greeks require positive time to expiry."
        )

    if option_type not in ("call", "put"):
        raise ValueError(
            "Option type must be 'call' or 'put'."
        )

    sqrt_maturity = math.sqrt(maturity)

    d1 = (
        math.log(spot / strike)
        + (
            rate
            - dividend
            + 0.5 * volatility**2
        ) * maturity
    ) / (volatility * sqrt_maturity)

    d2 = d1 - volatility * sqrt_maturity

    discount_rate = math.exp(-rate * maturity)
    discount_dividend = math.exp(-dividend * maturity)

    n_d1 = _normal_cdf(d1)
    n_d2 = _normal_cdf(d2)

    n_minus_d1 = _normal_cdf(-d1)
    n_minus_d2 = _normal_cdf(-d2)

    phi_d1 = _normal_pdf(d1)

    # Gamma is identical for European Calls and Puts.
    gamma = (
        discount_dividend * phi_d1
        / (spot * volatility * sqrt_maturity)
    )

    # Vega is identical for European Calls and Puts.
    vega = (
        spot
        * discount_dividend
        * phi_d1
        * sqrt_maturity
    )

    # Common diffusion component of Theta.
    theta_common = (
        -spot
        * discount_dividend
        * phi_d1
        * volatility
        / (2.0 * sqrt_maturity)
    )

    if option_type == "call":

        delta = discount_dividend * n_d1

        theta = (
            theta_common
            - rate * strike * discount_rate * n_d2
            + dividend * spot * discount_dividend * n_d1
        )

        rho = (
            strike
            * maturity
            * discount_rate
            * n_d2
        )

    else:

        delta = discount_dividend * (n_d1 - 1.0)

        theta = (
            theta_common
            + rate * strike * discount_rate * n_minus_d2
            - dividend * spot * discount_dividend * n_minus_d1
        )

        rho = (
            -strike
            * maturity
            * discount_rate
            * n_minus_d2
        )

    return {
        "available": True,
        "model": "Black-Scholes-Merton",

        "delta": delta,

        "gamma": gamma,

        "vega_per_1_00_volatility": vega,

        "vega_per_1_percentage_point": vega / 100.0,

        "theta_per_year": theta,

        "theta_per_calendar_day": theta / 365.0,

        "rho_per_1_00_rate": rho,

        "rho_per_1_percentage_point": rho / 100.0
    }


def calculate_numerical_greeks(parameters):
    """
    Calculate numerical Greeks using finite differences
    of the Black-Scholes-Merton option price.

    The results are used to validate the analytical Greeks.
    """

    spot = _get_number(parameters, "spot_price")
    volatility = _get_number(parameters, "volatility")
    maturity = _get_number(
        parameters, "time_to_expiry_years"
    )

    if spot <= 0:
        raise ValueError("Spot price must be positive.")

    if volatility <= 0:
        raise ValueError("Volatility must be positive.")

    if maturity <= 0:
        raise ValueError("Time to expiry must be positive.")

    def calculate_price(updated_parameters):
        return price_option_black_scholes(
            updated_parameters
        )["estimated_price"]

    base_price = calculate_price(parameters)

    # Finite-difference step sizes.
    spot_step = max(spot * 1e-4, 1e-5)

    volatility_step = min(
        1e-4,
        volatility * 0.25
    )

    maturity_step = min(
        1e-4,
        maturity * 0.25
    )

    rate_step = 1e-4

    # Delta and Gamma: derivatives with respect to spot.
    spot_up = parameters.copy()
    spot_down = parameters.copy()

    spot_up["spot_price"] = spot + spot_step
    spot_down["spot_price"] = spot - spot_step

    price_spot_up = calculate_price(spot_up)
    price_spot_down = calculate_price(spot_down)

    delta = (
        price_spot_up - price_spot_down
    ) / (2.0 * spot_step)

    gamma = (
        price_spot_up
        - 2.0 * base_price
        + price_spot_down
    ) / (spot_step**2)

    # Vega: derivative with respect to volatility.
    volatility_up = parameters.copy()
    volatility_down = parameters.copy()

    volatility_up["volatility"] = (
        volatility + volatility_step
    )

    volatility_down["volatility"] = (
        volatility - volatility_step
    )

    vega = (
        calculate_price(volatility_up)
        - calculate_price(volatility_down)
    ) / (2.0 * volatility_step)

    # Theta: negative derivative with respect to
    # remaining time to expiry.
    maturity_up = parameters.copy()
    maturity_down = parameters.copy()

    maturity_up["time_to_expiry_years"] = (
        maturity + maturity_step
    )

    maturity_down["time_to_expiry_years"] = (
        maturity - maturity_step
    )

    theta = (
        calculate_price(maturity_down)
        - calculate_price(maturity_up)
    ) / (2.0 * maturity_step)

    # Rho: derivative with respect to risk-free rate.
    rate_up = parameters.copy()
    rate_down = parameters.copy()

    rate_up["risk_free_rate"] = (
        float(parameters["risk_free_rate"]) + rate_step
    )

    rate_down["risk_free_rate"] = (
        float(parameters["risk_free_rate"]) - rate_step
    )

    rho = (
        calculate_price(rate_up)
        - calculate_price(rate_down)
    ) / (2.0 * rate_step)

    return {
        "delta": delta,
        "gamma": gamma,
        "vega_per_1_00_volatility": vega,
        "vega_per_1_percentage_point": vega / 100.0,
        "theta_per_year": theta,
        "theta_per_calendar_day": theta / 365.0,
        "rho_per_1_00_rate": rho,
        "rho_per_1_percentage_point": rho / 100.0
    }


def compare_greeks(analytical, numerical):
    """
    Compare analytical Greeks with finite-difference Greeks.
    """

    greek_names = [
        "delta",
        "gamma",
        "vega_per_1_00_volatility",
        "theta_per_year",
        "rho_per_1_00_rate"
    ]

    comparison = {}

    for name in greek_names:

        analytical_value = analytical[name]
        numerical_value = numerical[name]

        difference = abs(
            analytical_value - numerical_value
        )

        if analytical_value != 0:
            relative_error = (
                difference / abs(analytical_value)
            ) * 100.0
        else:
            relative_error = None

        comparison[name] = {
            "analytical": analytical_value,
            "numerical": numerical_value,
            "absolute_difference": difference,
            "relative_error_percent": relative_error
        }

    return comparison

