import math


def _finite_number(value, field_name):
    """Validate and convert a finite numeric value."""

    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be numeric."
        )

    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(
            f"{field_name} must be numeric."
        )

    if not math.isfinite(number):
        raise ValueError(
            f"{field_name} must be finite."
        )

    return number


def _positive_integer(value, field_name):
    """Validate a positive integer quantity."""

    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be a positive integer."
        )

    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(
            f"{field_name} must be a positive integer."
        )

    if str(value).strip() not in (
        str(number),
        f"{number}.0"
    ) or number <= 0:
        raise ValueError(
            f"{field_name} must be a positive integer."
        )

    return number


def calculate_lot_values(
    pricing_result,
    benchmark_result,
    contract_metadata,
    comparison_result=None
):
    """
    Convert per-share theoretical pricing results
    into per-lot theoretical values.

    Uses the contract's board_lot_quantity.

    The Monte Carlo and Black-Scholes prices are
    theoretical model estimates, not market quotes.
    """

    if not isinstance(pricing_result, dict):
        raise ValueError(
            "Pricing result must be a dictionary."
        )

    if not isinstance(benchmark_result, dict):
        raise ValueError(
            "Benchmark result must be a dictionary."
        )

    if not isinstance(contract_metadata, dict):
        raise ValueError(
            "Contract metadata must be a dictionary."
        )

    lot_size = _positive_integer(
        contract_metadata.get("board_lot_quantity"),
        "board_lot_quantity"
    )

    monte_carlo_price = _finite_number(
        pricing_result.get("estimated_price"),
        "Monte Carlo estimated price"
    )

    standard_error = _finite_number(
        pricing_result.get("standard_error"),
        "Monte Carlo standard error"
    )

    ci_lower = _finite_number(
        pricing_result.get("confidence_interval_lower"),
        "Confidence interval lower bound"
    )

    ci_upper = _finite_number(
        pricing_result.get("confidence_interval_upper"),
        "Confidence interval upper bound"
    )

    analytical_price = _finite_number(
        benchmark_result.get("estimated_price"),
        "Analytical estimated price"
    )

    if monte_carlo_price < 0:
        raise ValueError(
            "Monte Carlo option price cannot be negative."
        )

    if analytical_price < 0:
        raise ValueError(
            "Analytical option price cannot be negative."
        )

    if standard_error < 0:
        raise ValueError(
            "Standard error cannot be negative."
        )

    if ci_lower > ci_upper:
        raise ValueError(
            "Confidence interval lower bound "
            "cannot exceed its upper bound."
        )

    absolute_error = abs(
        monte_carlo_price - analytical_price
    )

    if analytical_price > 0:
        relative_error_percent = (
            absolute_error / analytical_price
        ) * 100.0
    else:
        relative_error_percent = None

    result = {
        "contract": {
            "contract_id": str(
                contract_metadata.get("contract_id", "")
            ),
            "symbol": str(
                contract_metadata.get("symbol", "")
            ),
            "expiry_date": str(
                contract_metadata.get("expiry_date", "")
            ),
            "strike_price": float(
                contract_metadata.get("strike_price", 0)
            ),
            "option_type": str(
                contract_metadata.get("option_type", "")
            ),
            "board_lot_quantity": lot_size
        },

        "theoretical_premium_per_share":
            monte_carlo_price,

        "theoretical_premium_per_lot":
            monte_carlo_price * lot_size,

        "analytical_price_per_share":
            analytical_price,

        "analytical_premium_per_lot":
            analytical_price * lot_size,

        "standard_error_per_share":
            standard_error,

        "standard_error_per_lot":
            standard_error * lot_size,

        "confidence_interval_per_share": {
            "lower": ci_lower,
            "upper": ci_upper
        },

        "confidence_interval_per_lot": {
            "lower": ci_lower * lot_size,
            "upper": ci_upper * lot_size
        },

        "absolute_error_per_share":
            absolute_error,

        "absolute_error_per_lot":
            absolute_error * lot_size,

        "relative_error_percent":
            relative_error_percent,

        "pricing_basis": (
            "Theoretical model estimate multiplied "
            "by NSE board lot quantity."
        )
    }

    if comparison_result is not None:
        if not isinstance(comparison_result, dict):
            raise ValueError(
                "Comparison result must be a dictionary."
            )

        result["confidence_interval_contains_benchmark"] = (
            comparison_result.get(
                "confidence_interval_contains_benchmark"
            )
        )

    return result