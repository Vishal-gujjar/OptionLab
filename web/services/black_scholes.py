import math


def _get_finite_number(parameters, key):
    """Read and validate a finite numeric parameter."""
    if key not in parameters:
        raise ValueError(f"Missing required parameter: {key}")

    value = parameters[key]

    if isinstance(value, bool):
        raise ValueError(f"{key} must be a numeric value.")

    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be a numeric value.")

    if not math.isfinite(value):
        raise ValueError(f"{key} must be finite.")

    return value


def _normal_cdf(x):
    """Standard normal cumulative distribution function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def price_option_black_scholes(parameters):
    """
    Calculate a European option price using the
    Black-Scholes-Merton analytical model.

    Required parameters:
        spot_price
        strike_price
        risk_free_rate
        dividend_yield
        volatility
        time_to_expiry_years
        option_type
    """

    spot = _get_finite_number(parameters, "spot_price")
    strike = _get_finite_number(parameters, "strike_price")
    rate = _get_finite_number(parameters, "risk_free_rate")
    dividend = _get_finite_number(parameters, "dividend_yield")
    volatility = _get_finite_number(parameters, "volatility")
    maturity = _get_finite_number(
        parameters, "time_to_expiry_years"
    )

    option_type = str(
        parameters.get("option_type", "")
    ).strip().lower()

    # Input validation
    if spot <= 0:
        raise ValueError("Spot price must be positive.")

    if strike <= 0:
        raise ValueError("Strike price must be positive.")

    if volatility < 0:
        raise ValueError("Volatility cannot be negative.")

    if maturity < 0:
        raise ValueError("Time to expiry cannot be negative.")

    if option_type not in ("call", "put"):
        raise ValueError("Option type must be 'call' or 'put'.")

    # Case 1: Option has reached expiry.
    if maturity == 0:
        if option_type == "call":
            price = max(spot - strike, 0.0)
        else:
            price = max(strike - spot, 0.0)

        return {
            "model": "Black-Scholes-Merton",
            "estimated_price": price,
            "d1": None,
            "d2": None
        }

    # Case 2: Zero volatility.
    # The risk-neutral terminal stock price is deterministic.
    if volatility == 0:
        terminal_spot = spot * math.exp(
            (rate - dividend) * maturity
        )

        if option_type == "call":
            payoff = max(terminal_spot - strike, 0.0)
        else:
            payoff = max(strike - terminal_spot, 0.0)

        price = math.exp(-rate * maturity) * payoff

        return {
            "model": "Black-Scholes-Merton",
            "estimated_price": price,
            "d1": None,
            "d2": None
        }

    # Standard Black-Scholes-Merton calculation.
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

    if option_type == "call":
        price = (
            spot * math.exp(-dividend * maturity)
            * _normal_cdf(d1)
            - strike * math.exp(-rate * maturity)
            * _normal_cdf(d2)
        )

    else:
        price = (
            strike * math.exp(-rate * maturity)
            * _normal_cdf(-d2)
            - spot * math.exp(-dividend * maturity)
            * _normal_cdf(-d1)
        )

    return {
        "model": "Black-Scholes-Merton",
        "estimated_price": price,
        "d1": d1,
        "d2": d2
    }
