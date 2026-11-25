import math

from datetime import date

from flask import Blueprint, jsonify, request

from web.services.option_analytics import (
    simulate_terminal_distribution,
    calculate_option_payoff_analysis
)

from web.services.strategy_analysis import (
    analyze_option_strategy
)

from web.services.market_data_status import (
    get_market_data_status
)


stage17_bp = Blueprint("stage17", __name__)


def _error(code, message, status_code):
    return jsonify({
        "status": "error",
        "error": {
            "code": code,
            "message": message
        }
    }), status_code


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a JSON number.")

    result = float(value)

    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite.")

    return result


def _integer(value, name, default):
    if value is None:
        value = default

    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer.")

    return value


def _model_parameters(data):
    parameters = data.get("option_parameters")

    if not isinstance(parameters, dict):
        raise ValueError(
            "option_parameters must be a JSON object."
        )

    required = [
        "spot_price",
        "strike_price",
        "risk_free_rate",
        "dividend_yield",
        "volatility",
        "time_to_expiry_years",
        "option_type"
    ]

    missing = [
        key for key in required
        if key not in parameters
    ]

    if missing:
        raise ValueError(
            "Missing option parameters: "
            + ", ".join(missing)
        )

    result = {}

    for key in required:
        if key == "option_type":
            value = parameters[key]

            if not isinstance(value, str):
                raise ValueError("option_type must be a string.")

            value = value.strip().lower()

            if value not in ("call", "put"):
                raise ValueError("option_type must be call or put.")

            result[key] = value

        else:
            result[key] = _number(
                parameters[key],
                key
            )

    if result["spot_price"] <= 0:
        raise ValueError("Spot price must be positive.")

    if result["strike_price"] <= 0:
        raise ValueError("Strike price must be positive.")

    if result["volatility"] < 0:
        raise ValueError("Volatility cannot be negative.")

    if result["time_to_expiry_years"] < 0:
        raise ValueError("Time to expiry cannot be negative.")

    return result


@stage17_bp.post("/api/analytics/distribution")
def terminal_distribution():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return _error(
            "invalid_request",
            "A JSON object is required.",
            400
        )

    try:
        parameters = _model_parameters(data)

        sample_count = _integer(
            data.get("sample_count"),
            "sample_count",
            20000
        )

        bins = _integer(
            data.get("bins"),
            "bins",
            40
        )

        seed = _integer(
            data.get("seed"),
            "seed",
            42
        )

        result = simulate_terminal_distribution(
            parameters,
            sample_count=sample_count,
            bins=bins,
            seed=seed
        )

        return jsonify({
            "status": "success",
            "distribution": result
        }), 200

    except ValueError as exc:
        return _error(
            "invalid_distribution_parameters",
            str(exc),
            400
        )


@stage17_bp.post("/api/analytics/payoff")
def option_payoff():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return _error(
            "invalid_request",
            "A JSON object is required.",
            400
        )

    try:
        parameters = _model_parameters(data)

        premium = _number(
            data.get("premium_per_share"),
            "premium_per_share"
        )

        lot_size = _integer(
            data.get("lot_size"),
            "lot_size",
            None
        )

        points = _integer(
            data.get("points"),
            "points",
            101
        )

        result = calculate_option_payoff_analysis(
            parameters,
            premium_per_share=premium,
            lot_size=lot_size,
            points=points
        )

        return jsonify({
            "status": "success",
            "payoff_analysis": result
        }), 200

    except ValueError as exc:
        return _error(
            "invalid_payoff_parameters",
            str(exc),
            400
        )


@stage17_bp.post("/api/strategies/analyze")
def strategy_analysis():

    data = request.get_json(silent=True)

    # --------------------------------------------------
    # 1. Validate request body
    # --------------------------------------------------

    if not isinstance(data, dict):

        return _error(
            "invalid_request",
            "A JSON object is required.",
            400
        )

    required_fields = [
        "option_parameters",
        "symbol",
        "expiry_date",
        "strategy",
        "lower_strike"
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in data
    ]

    if missing_fields:

        return _error(
            "missing_parameters",
            "Missing required fields: "
            + ", ".join(missing_fields),
            400
        )

    option_parameters = data.get("option_parameters")

    if not isinstance(option_parameters, dict):

        return _error(
            "invalid_request",
            "option_parameters must be a JSON object.",
            400
        )

    required_option_parameters = [
        "spot_price",
        "strike_price",
        "risk_free_rate",
        "dividend_yield",
        "volatility",
        "time_to_expiry_years",
        "option_type"
    ]

    missing_option_parameters = [
        field
        for field in required_option_parameters
        if field not in option_parameters
    ]

    if missing_option_parameters:

        return _error(
            "missing_parameters",
            "Missing option parameters: "
            + ", ".join(missing_option_parameters),
            400
        )

    try:

        # --------------------------------------------------
        # 2. Validate model parameters
        # --------------------------------------------------

        parameters = _model_parameters(data)

        symbol = data.get("symbol")

        expiry_date = data.get("expiry_date")

        strategy = data.get("strategy")

        if not isinstance(symbol, str) or not symbol.strip():

            raise ValueError(
                "A stock symbol is required."
            )

        symbol = symbol.strip().upper()

        if not isinstance(expiry_date, str) or not expiry_date.strip():

            raise ValueError(
                "An expiry date is required."
            )

        if not isinstance(strategy, str):

            raise ValueError(
                "A strategy name is required."
            )

        lower_strike = _number(
            data.get("lower_strike"),
            "lower_strike"
        )

        upper_strike = data.get("upper_strike")

        if upper_strike is not None:

            upper_strike = _number(
                upper_strike,
                "upper_strike"
            )

        lots = _integer(
            data.get("lots"),
            "lots",
            1
        )

        # --------------------------------------------------
        # 3. Obtain authoritative server-side market status
        # --------------------------------------------------

        market_status = get_market_data_status(
            symbol=symbol,
            exchange="nse"
        )

        status = market_status["status"]

        if status == "missing":

            return _error(
                "market_data_not_found",
                "Required raw and adjusted market data "
                "is missing for this stock.",
                404
            )

        if status in ("invalid", "date_mismatch"):

            details = " ".join(
                market_status.get("warnings", [])
            )

            return _error(
                "market_data_invalid",
                "Strategy analysis cannot use invalid "
                "or inconsistent market data. "
                + details,
                422
            )

        # Aging and stale datasets are allowed,
        # consistent with the main pricing workflow.

        raw_data = market_status.get("raw", {})

        latest_raw_date = raw_data.get("latest_date")

        if not isinstance(latest_raw_date, str):

            raise ValueError(
                "A valid latest raw market date is required."
            )

        try:

            market_date = date.fromisoformat(
                latest_raw_date
            )

        except ValueError:

            raise ValueError(
                "The latest raw market date is invalid."
            ) from None

        # The contract reference date is determined
        # entirely on the server.
        reference_date = max(
            date.today(),
            market_date
        ).isoformat()

        # --------------------------------------------------
        # 4. Perform strategy analysis
        # --------------------------------------------------

        result = analyze_option_strategy(
            parameters=parameters,
            symbol=symbol,
            expiry_date=expiry_date,
            reference_date=reference_date,
            strategy=strategy,
            lower_strike=lower_strike,
            upper_strike=upper_strike,
            lots=lots
        )

        # --------------------------------------------------
        # 5. Return result
        # --------------------------------------------------

        return jsonify({
            "status": "success",
            "strategy_analysis": result
        }), 200

    except FileNotFoundError:

        return _error(
            "contract_metadata_not_found",
            "The normalized NSE contract master was not found.",
            404
        )

    except ValueError as exc:

        return _error(
            "strategy_validation_failed",
            str(exc),
            422
        )

    except Exception:

        return _error(
            "strategy_analysis_failed",
            "An unexpected strategy-analysis error occurred.",
            500
        )

    