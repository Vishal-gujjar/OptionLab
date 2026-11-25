import math

from web.services.black_scholes import (
    price_option_black_scholes
)

from web.services.pricing_bridge import price_option


MAX_SIMULATIONS = 5_000_000
MAX_UINT64 = (2**64) - 1


def _finite_number(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric.")

    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be numeric.")

    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite.")

    return value


def compare_pricing_results(
    monte_carlo_result,
    analytical_result
):
    """
    Compare Monte Carlo pricing with the
    Black-Scholes analytical benchmark.
    """

    if not isinstance(monte_carlo_result, dict):
        raise ValueError("Invalid Monte Carlo result.")

    if not isinstance(analytical_result, dict):
        raise ValueError("Invalid analytical result.")

    monte_carlo_price = _finite_number(
        monte_carlo_result.get("estimated_price"),
        "Monte Carlo price"
    )

    analytical_price = _finite_number(
        analytical_result.get("estimated_price"),
        "Analytical price"
    )

    lower = _finite_number(
        monte_carlo_result.get("confidence_interval_lower"),
        "Confidence interval lower bound"
    )

    upper = _finite_number(
        monte_carlo_result.get("confidence_interval_upper"),
        "Confidence interval upper bound"
    )

    if lower > upper:
        raise ValueError("Invalid confidence interval.")

    absolute_error = abs(
        monte_carlo_price - analytical_price
    )

    if analytical_price != 0:
        relative_error_percent = (
            absolute_error / abs(analytical_price)
        ) * 100.0
    else:
        relative_error_percent = None

    confidence_interval_contains_benchmark = (
        lower <= analytical_price <= upper
    )

    return {
        "signed_error": (
            monte_carlo_price - analytical_price
        ),
        "absolute_error": absolute_error,
        "relative_error_percent": relative_error_percent,
        "confidence_interval_contains_benchmark":
            confidence_interval_contains_benchmark
    }


def run_convergence_analysis(
    option_parameters,
    simulation_counts,
    seed=42
):
    """
    Run Monte Carlo pricing at different simulation counts
    and compare every estimate with the analytical benchmark.
    """

    if not isinstance(option_parameters, dict):
        raise ValueError("Option parameters must be a dictionary.")

    if not isinstance(simulation_counts, (list, tuple)):
        raise ValueError(
            "Simulation counts must be a list or tuple."
        )

    if not simulation_counts:
        raise ValueError("At least one simulation count is required.")

    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("Seed must be an integer.")

    if seed < 0 or seed > MAX_UINT64:
        raise ValueError("Seed is outside the supported range.")

    validated_counts = []

    for count in simulation_counts:
        if isinstance(count, bool) or not isinstance(count, int):
            raise ValueError(
                "Each simulation count must be an integer."
            )

        if count < 2 or count > MAX_SIMULATIONS:
            raise ValueError(
                f"Simulation count must be between 2 and "
                f"{MAX_SIMULATIONS}."
            )

        validated_counts.append(count)

    if any(
        validated_counts[i] >= validated_counts[i + 1]
        for i in range(len(validated_counts) - 1)
    ):
        raise ValueError(
            "Simulation counts must be strictly increasing."
        )

    analytical_result = price_option_black_scholes(
        option_parameters
    )

    rows = []

    for count in validated_counts:
        parameters = option_parameters.copy()
        parameters["simulations"] = count
        parameters["seed"] = seed

        monte_carlo_result = price_option(parameters)

        comparison = compare_pricing_results(
            monte_carlo_result,
            analytical_result
        )

        rows.append({
            "simulations": count,
            "monte_carlo_price":
                monte_carlo_result["estimated_price"],
            "analytical_price":
                analytical_result["estimated_price"],
            "standard_error":
                monte_carlo_result["standard_error"],
            "confidence_interval_lower":
                monte_carlo_result["confidence_interval_lower"],
            "confidence_interval_upper":
                monte_carlo_result["confidence_interval_upper"],
            "absolute_error":
                comparison["absolute_error"],
            "relative_error_percent":
                comparison["relative_error_percent"],
            "confidence_interval_contains_benchmark":
                comparison[
                    "confidence_interval_contains_benchmark"
                ]
        })

    return rows