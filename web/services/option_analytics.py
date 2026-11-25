import math
import random
import statistics


def _finite_number(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric.")

    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be numeric.")

    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite.")

    return number


def _positive_integer(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be a positive integer.")

    if value <= 0:
        raise ValueError(f"{name} must be a positive integer.")

    return value


def _validate_distribution_parameters(parameters):
    if not isinstance(parameters, dict):
        raise ValueError("Option parameters must be a dictionary.")

    spot = _finite_number(
        parameters.get("spot_price"),
        "spot_price"
    )

    rate = _finite_number(
        parameters.get("risk_free_rate"),
        "risk_free_rate"
    )

    dividend = _finite_number(
        parameters.get("dividend_yield"),
        "dividend_yield"
    )

    volatility = _finite_number(
        parameters.get("volatility"),
        "volatility"
    )

    maturity = _finite_number(
        parameters.get("time_to_expiry_years"),
        "time_to_expiry_years"
    )

    if spot <= 0:
        raise ValueError("Spot price must be positive.")

    if volatility < 0:
        raise ValueError("Volatility cannot be negative.")

    if maturity < 0:
        raise ValueError("Time to expiry cannot be negative.")

    return spot, rate, dividend, volatility, maturity


def _quantile(sorted_values, probability):
    """Calculate a linearly interpolated sample quantile."""

    position = (len(sorted_values) - 1) * probability

    lower_index = int(math.floor(position))
    upper_index = int(math.ceil(position))

    if lower_index == upper_index:
        return sorted_values[lower_index]

    weight = position - lower_index

    return (
        sorted_values[lower_index] * (1.0 - weight)
        + sorted_values[upper_index] * weight
    )


def simulate_terminal_distribution(
    parameters,
    sample_count=20000,
    bins=40,
    seed=42
):
    """
    Simulate terminal stock prices under risk-neutral GBM.

    Returns histogram data and summary statistics.
    The generated values are analytical scenario samples,
    not predictions of actual future market prices.
    """

    spot, rate, dividend, volatility, maturity = (
        _validate_distribution_parameters(parameters)
    )

    sample_count = _positive_integer(
        sample_count,
        "sample_count"
    )

    bins = _positive_integer(bins, "bins")

    if not 1000 <= sample_count <= 50000:
        raise ValueError(
            "sample_count must be between 1,000 and 50,000."
        )

    if not 10 <= bins <= 100:
        raise ValueError(
            "bins must be between 10 and 100."
        )

    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("Seed must be an integer.")

    if seed < 0 or seed > (2**64 - 1):
        raise ValueError("Seed must be between 0 and 2^64 - 1.")

    generator = random.Random(seed)

    drift = (
        rate
        - dividend
        - 0.5 * volatility**2
    ) * maturity

    diffusion = volatility * math.sqrt(maturity)

    samples = []

    for _ in range(sample_count):

        z = generator.gauss(0.0, 1.0)

        terminal_price = spot * math.exp(
            drift + diffusion * z
        )

        if not math.isfinite(terminal_price):
            raise ValueError(
                "A non-finite terminal price was generated."
            )

        samples.append(terminal_price)

    samples.sort()

    sample_min = samples[0]
    sample_max = samples[-1]

    # Avoid zero-width histogram bins in deterministic cases.
    if math.isclose(sample_min, sample_max, rel_tol=1e-12):
        half_width = max(sample_min * 0.005, 0.50)
        histogram_min = max(0.0, sample_min - half_width)
        histogram_max = sample_max + half_width
    else:
        histogram_min = sample_min
        histogram_max = sample_max

    bin_width = (
        histogram_max - histogram_min
    ) / bins

    histogram = [
        {
            "lower": histogram_min + i * bin_width,
            "upper": histogram_min + (i + 1) * bin_width,
            "midpoint": (
                histogram_min + (i + 0.5) * bin_width
            ),
            "count": 0
        }
        for i in range(bins)
    ]

    for value in samples:

        index = int(
            (value - histogram_min) / bin_width
        )

        index = min(max(index, 0), bins - 1)

        histogram[index]["count"] += 1

    theoretical_mean = spot * math.exp(
        (rate - dividend) * maturity
    )

    theoretical_median = spot * math.exp(
        (
            rate
            - dividend
            - 0.5 * volatility**2
        ) * maturity
    )

    result = {
        "model": "Risk-neutral Geometric Brownian Motion",
        "sample_count": sample_count,
        "seed": seed,

        "histogram": histogram,

        "summary": {
            "sample_mean": statistics.mean(samples),
            "sample_standard_deviation": (
                statistics.stdev(samples)
                if sample_count > 1 else 0.0
            ),
            "sample_minimum": sample_min,
            "sample_maximum": sample_max,
            "sample_median": _quantile(samples, 0.50),
            "sample_5th_percentile": _quantile(samples, 0.05),
            "sample_95th_percentile": _quantile(samples, 0.95),
            "theoretical_expected_terminal_price": theoretical_mean,
            "theoretical_median_terminal_price": theoretical_median
        },

        "interpretation": (
            "Risk-neutral model distribution for scenario analysis. "
            "It is not a real-world price forecast."
        )
    }

    if "strike_price" in parameters:
        strike = _finite_number(
            parameters["strike_price"],
            "strike_price"
        )

        if strike <= 0:
            raise ValueError("Strike price must be positive.")

        result["summary"]["sample_fraction_above_strike"] = (
            sum(value > strike for value in samples)
            / sample_count
        )

    return result


def calculate_option_payoff_analysis(
    parameters,
    premium_per_share,
    lot_size,
    points=101
):
    """
    Calculate European Call/Put expiry payoff and
    buyer/seller P&L using the supplied theoretical premium.
    """

    spot, _, _, _, _ = _validate_distribution_parameters(
        parameters
    )

    strike = _finite_number(
        parameters.get("strike_price"),
        "strike_price"
    )

    premium = _finite_number(
        premium_per_share,
        "premium_per_share"
    )

    option_type = str(
        parameters.get("option_type", "")
    ).strip().lower()

    lot_size = _positive_integer(
        lot_size,
        "lot_size"
    )

    points = _positive_integer(points, "points")

    if points < 21 or points > 501:
        raise ValueError(
            "points must be between 21 and 501."
        )

    if strike <= 0:
        raise ValueError("Strike price must be positive.")

    if premium < 0:
        raise ValueError("Premium cannot be negative.")

    if option_type not in ("call", "put"):
        raise ValueError("Option type must be call or put.")

    lower_spot = 0.0
    upper_spot = max(spot, strike) * 2.0

    terminal_prices = [
        lower_spot
        + i * (upper_spot - lower_spot) / (points - 1)
        for i in range(points)
    ]

    # Include strike and break-even exactly in the grid.
    terminal_prices.append(strike)

    if option_type == "call":

        break_even = strike + premium

        # Long Call:
        # Maximum profit is unlimited.
        maximum_profit = None
        maximum_profit_label = "Unlimited"

        # Long Call:
        # Maximum loss is the premium paid.
        maximum_loss = premium * lot_size

        # Short Call:
        # Maximum loss is unlimited.
        short_maximum_loss = None
        short_maximum_loss_label = "Unlimited"

    else:

        candidate = strike - premium

        break_even = (
            candidate if candidate >= 0 else None
        )

        # Long Put:
        # Maximum profit occurs when terminal stock price is zero.
        maximum_profit = max(candidate, 0.0) * lot_size
        maximum_profit_label = "Finite"

        # Long Put:
        # Maximum loss is the premium paid.
        maximum_loss = premium * lot_size

        # Short Put:
        # Maximum loss occurs when terminal stock price is zero.
        short_maximum_loss = max(
            strike - premium,
            0.0
        ) * lot_size

        short_maximum_loss_label = "Finite"

    if break_even is not None:
        terminal_prices.append(break_even)

    terminal_prices = sorted(set(terminal_prices))

    points_data = []

    for terminal_spot in terminal_prices:

        if option_type == "call":
            payoff = max(terminal_spot - strike, 0.0)
        else:
            payoff = max(strike - terminal_spot, 0.0)

        long_pnl = (payoff - premium) * lot_size
        short_pnl = -long_pnl

        points_data.append({
            "terminal_stock_price": terminal_spot,
            "payoff_per_share": payoff,
            "payoff_per_lot": payoff * lot_size,
            "long_pnl_per_lot": long_pnl,
            "short_pnl_per_lot": short_pnl
        })

    return {
        "option_type": option_type,
        "strike_price": strike,
        "premium_per_share": premium,
        "lot_size": lot_size,
        "premium_per_lot": premium * lot_size,

        "break_even_stock_price": break_even,

        "long_position": {
            "maximum_profit": maximum_profit,
            "maximum_profit_label": maximum_profit_label,
            "maximum_loss": maximum_loss
        },

        "short_position": {
            "maximum_profit": premium * lot_size,

            "maximum_loss": short_maximum_loss,

            "maximum_loss_label": short_maximum_loss_label
        },

        "points": points_data,

        "pricing_basis": (
            "Theoretical premium supplied by OptionLab, "
            "without brokerage, taxes, slippage, or other costs."
        )
    }



