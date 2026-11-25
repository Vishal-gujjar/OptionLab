import json
import math
import os
import subprocess

from pathlib import Path
from collections.abc import Mapping
from typing import Any


# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# C++ executable location
EXECUTABLE_PATH = (
    PROJECT_ROOT
    / "build"
    / (
        "optionlab_engine.exe"
        if os.name == "nt"
        else "optionlab_engine"
    )
)


def price_option(
    parameters: Mapping[str, Any],
    executable_path: Path | None = None
) -> dict:

    """
    Execute the C++ Monte Carlo pricing engine.

    Parameters are supplied by Python and passed to C++.
    Returns the pricing results as a Python dictionary.
    """

    # Required financial parameters
    required = {
        "spot_price",
        "strike_price",
        "risk_free_rate",
        "dividend_yield",
        "volatility",
        "time_to_expiry_years",
        "option_type",
    }

    missing = required - parameters.keys()

    if missing:
        raise ValueError(
            f"Missing parameters: {sorted(missing)}"
        )

    # Convert and validate numerical inputs
    numeric_fields = {
        "spot_price": "--spot",
        "strike_price": "--strike",
        "risk_free_rate": "--rate",
        "dividend_yield": "--dividend",
        "volatility": "--volatility",
        "time_to_expiry_years": "--maturity",
    }

    values = {}

    for name, argument in numeric_fields.items():

        raw_value = parameters[name]

        if isinstance(raw_value, bool):
            raise ValueError(f"{name} must be numeric.")

        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            raise ValueError(
                f"Invalid numerical input: {name}"
            ) from None

        if not math.isfinite(value):
            raise ValueError(
                f"{name} must be finite."
            )

        values[argument] = value

    if values["--spot"] <= 0:
        raise ValueError("Spot price must be positive.")

    if values["--strike"] <= 0:
        raise ValueError("Strike price must be positive.")

    if values["--volatility"] < 0:
        raise ValueError("Volatility cannot be negative.")

    if values["--maturity"] < 0:
        raise ValueError("Maturity cannot be negative.")

    # Validate option type
    option_type = str(parameters["option_type"]).lower()

    if option_type not in ("call", "put"):
        raise ValueError("Option type must be call or put.")

    # Simulation configuration
    simulations = parameters.get("simulations", 100000)
    seed = parameters.get("seed", 42)

    if (
        isinstance(simulations, bool)
        or not isinstance(simulations, int)
        or simulations < 2
    ):
        raise ValueError(
            "Simulations must be an integer greater than or equal to 2."
        )

    if (
        isinstance(seed, bool)
        or not isinstance(seed, int)
        or not 0 <= seed <= 2**64 - 1
    ):
        raise ValueError("Invalid random seed.")

    # Locate C++ executable
    executable = Path(
        executable_path or EXECUTABLE_PATH
    ).resolve()

    if not executable.is_file():
        raise FileNotFoundError(
            f"C++ executable not found: {executable}. "
            "Build the project using CMake first."
        )

    # Construct command
    command = [str(executable)]

    for argument, value in values.items():
        command.extend([argument, str(value)])

    command.extend([
        "--type", option_type,
        "--simulations", str(simulations),
        "--seed", str(seed),
    ])

    # Execute C++ program safely
    try:

        process = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False
        )

    except subprocess.TimeoutExpired:
        raise TimeoutError(
            "C++ pricing engine exceeded 60 seconds."
        ) from None

    # Handle C++ errors
    if process.returncode != 0:

        error_message = process.stderr.strip()

        raise RuntimeError(
            error_message or "C++ pricing engine failed."
        )

    # Parse JSON response
    try:
        result = json.loads(process.stdout)

    except json.JSONDecodeError:
        raise RuntimeError(
            "C++ engine returned invalid JSON."
        ) from None

    # Validate returned structure
    expected_fields = {
        "estimated_price",
        "standard_error",
        "confidence_interval_lower",
        "confidence_interval_upper",
        "simulations",
    }

    if not isinstance(result, dict):
        raise RuntimeError("Invalid result structure.")

    if not expected_fields.issubset(result):
        raise RuntimeError("Missing result fields.")

    for key in expected_fields - {"simulations"}:

        if (
            isinstance(result[key], bool)
            or not isinstance(result[key], (int, float))
            or not math.isfinite(result[key])
        ):
            raise RuntimeError(
                f"Invalid result value: {key}"
            )

    if result["simulations"] != simulations:
        raise RuntimeError(
            "Simulation count mismatch."
        )

    if (
        result["standard_error"] < 0
        or result["confidence_interval_lower"]
        > result["estimated_price"]
        or result["confidence_interval_upper"]
        < result["estimated_price"]
    ):
        raise RuntimeError(
            "Invalid statistical results."
        )

    return result


