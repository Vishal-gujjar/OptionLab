import math
import re

from datetime import date, datetime

from flask import Flask, jsonify, request, render_template

from web.services.option_workflow import (
    price_from_market_data
)

from web.services.contract_lookup import (
    get_available_symbols,
    get_available_expiries,
    get_available_strikes,
    validate_option_contract
)

from web.services.lot_calculations import (
    calculate_lot_values
)

from web.services.market_data_status import (
    get_market_data_status
)

from web.services.market_refresh import (
    refresh_market_data
)

from web.stage17_routes import stage17_bp

MAX_SIMULATIONS = 5_000_000
MAX_UINT64 = (2**64) - 1

SYMBOL_PATTERN = re.compile(r"^[A-Z0-9&.-]{1,25}$")


def create_app():
    app = Flask(__name__)
    app.register_blueprint(stage17_bp)

    def validate_symbol(value):
        if not isinstance(value, str):
            raise ValueError("Symbol must be a string.")

        symbol = value.strip().upper()

        if not SYMBOL_PATTERN.fullmatch(symbol):
            raise ValueError("Invalid NSE stock symbol.")

        return symbol


    def get_market_reference_date(symbol):
        """
        Use the latest raw spot-price date for contract-expiry
        comparison. If raw market data is unavailable, use today.
        """

        status = get_market_data_status(
            symbol,
            exchange="nse"
        )

        latest_date = status["raw"]["latest_date"]

        return latest_date or date.today().isoformat()


    def get_contract_reference_date(symbol):
        market_date = date.fromisoformat(
            get_market_reference_date(symbol)
        )

        # Exclude contracts that have already expired today.
        reference_date = max(date.today(), market_date)

        return reference_date.isoformat()

    def error_response(code, message, status_code):
        return jsonify({
            "status": "error",
            "error": {
                "code": code,
                "message": message
            }
        }), status_code

    def get_number(data, field, default=None):
        value = data.get(field, default)

        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(
                f"'{field}' must be a valid JSON number."
            )

        value = float(value)

        if not math.isfinite(value):
            raise ValueError(
                f"'{field}' must be finite."
            )

        return value

    def get_integer(data, field, default):
        value = data.get(field, default)

        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(
                f"'{field}' must be an integer."
            )

        return value

    @app.get("/")
    def home():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return jsonify({
            "status": "ok",
            "service": "OptionLab API"
        })

    @app.get("/api/contracts/symbols")
    def contract_symbols():

        try:
            symbols = get_available_symbols()

            return jsonify({
                "status": "success",
                "count": len(symbols),
                "symbols": symbols
            }), 200

        except FileNotFoundError:
            return error_response(
                "contract_metadata_not_found",
                "Import the NSE stock-option contract master first.",
                404
            )

        except Exception:
            app.logger.exception(
                "Could not load NSE contract symbols."
            )

            return error_response(
                "contract_lookup_failed",
                "Could not load available stock symbols.",
                500
            )

    @app.get("/api/contracts/expiries")
    def contract_expiries():

        try:
            symbol = validate_symbol(
                request.args.get("symbol")
            )

            reference_date = get_contract_reference_date(
                symbol
            )

            expiries = get_available_expiries(
                symbol=symbol,
                reference_date=reference_date
            )

            return jsonify({
                "status": "success",
                "symbol": symbol,
                "reference_date": reference_date,
                "count": len(expiries),
                "expiries": expiries
            }), 200

        except ValueError as exc:
            return error_response(
                "invalid_contract_query",
                str(exc),
                400
            )

        except FileNotFoundError:
            return error_response(
                "contract_metadata_not_found",
                "NSE contract metadata is not available.",
                404
            )

        except Exception:
            app.logger.exception(
                "Could not load contract expiries."
            )

            return error_response(
                "contract_lookup_failed",
                "Could not load contract expiries.",
                500
            )

    @app.get("/api/contracts/strikes")
    def contract_strikes():

        try:
            symbol = validate_symbol(
                request.args.get("symbol")
            )

            expiry_date = request.args.get("expiry_date")

            option_type = request.args.get("option_type")

            if not expiry_date:
                raise ValueError("Expiry date is required.")

            if option_type not in ("call", "put"):
                raise ValueError(
                    "Option type must be call or put."
                )

            reference_date = get_contract_reference_date(
                symbol
            )

            strikes = get_available_strikes(
                symbol=symbol,
                expiry_date=expiry_date,
                option_type=option_type,
                reference_date=reference_date
            )

            return jsonify({
                "status": "success",
                "symbol": symbol,
                "expiry_date": expiry_date,
                "option_type": option_type,
                "strikes": [float(value) for value in strikes],
                "count": len(strikes)
            }), 200

        except ValueError as exc:
            return error_response(
                "invalid_contract_query",
                str(exc),
                400
            )

        except FileNotFoundError:
            return error_response(
                "contract_metadata_not_found",
                "NSE contract metadata is not available.",
                404
            )

        except Exception:
            app.logger.exception(
                "Could not load contract strikes."
            )

            return error_response(
                "contract_lookup_failed",
                "Could not load contract strikes.",
                500
            )

    @app.post("/api/contracts/validate")
    def contract_validate():

        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return error_response(
                "invalid_request",
                "A JSON object is required.",
                400
            )

        try:
            symbol = validate_symbol(
                data.get("symbol")
            )

            expiry_date = data.get("expiry_date")

            option_type = data.get("option_type")

            if option_type not in ("call", "put"):
                raise ValueError(
                    "Option type must be call or put."
                )

            strike_price = get_number(
                data,
                "strike_price"
            )

            reference_date = get_contract_reference_date(
                symbol
            )

            contract = validate_option_contract(
                symbol=symbol,
                expiry_date=expiry_date,
                strike_price=strike_price,
                option_type=option_type,
                reference_date=reference_date
            )

            return jsonify({
                "status": "success",
                "contract": contract
            }), 200

        except ValueError as exc:
            return error_response(
                "invalid_contract",
                str(exc),
                422
            )

        except FileNotFoundError:
            return error_response(
                "contract_metadata_not_found",
                "Import the NSE stock-option contract master first.",
                404
            )

        except Exception:
            app.logger.exception(
                "Contract validation failed unexpectedly."
            )

            return error_response(
                "contract_validation_failed",
                "Contract validation could not be completed.",
                500
            )

    @app.get("/api/market-data/status")
    def market_data_status():

        try:
            symbol = validate_symbol(
                request.args.get("symbol")
            )

            result = get_market_data_status(
                symbol=symbol,
                exchange="nse"
            )

            return jsonify({
                "status": "success",
                "market_data": result
            }), 200

        except ValueError as exc:
            return error_response(
                "invalid_symbol",
                str(exc),
                400
            )

        except Exception:
            app.logger.exception(
                "Could not inspect market-data status."
            )

            return error_response(
                "market_status_failed",
                "Could not inspect market-data cache.",
                500
            )

    @app.post("/api/market-data/refresh")
    def market_data_refresh():

        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return error_response(
                "invalid_request",
                "A JSON object is required.",
                400
            )

        try:
            symbol = validate_symbol(
                data.get("symbol")
            )

            # Restrict refreshes to stocks present in the
            # imported NSE stock-option universe.
            available_symbols = get_available_symbols()

            if symbol not in available_symbols:
                raise ValueError(
                    "The selected stock is not present in "
                    "the NSE stock-option contract master."
                )

            lookback_days = get_integer(
                data,
                "lookback_days",
                default=365
            )

            if not 1 <= lookback_days <= 3650:
                raise ValueError(
                    "lookback_days must be between 1 and 3650."
                )

            result = refresh_market_data(
                symbol=symbol,
                exchange="nse",
                lookback_days=lookback_days
            )

            return jsonify({
                "status": "success",
                "refresh": result
            }), 200

        except ValueError as exc:
            return error_response(
                "invalid_refresh_request",
                str(exc),
                400
            )

        except FileNotFoundError:
            return error_response(
                "contract_metadata_not_found",
                "Import the NSE contract master before refreshing.",
                404
            )

        except Exception as exc:
            app.logger.exception(
                "Market-data refresh failed."
            )

            return error_response(
                "market_refresh_failed",
                str(exc),
                502
            )   

    @app.post("/api/price")
    def price():

        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return error_response(
                "invalid_request",
                "Request body must contain a valid JSON object.",
                400
            )

        # Required parameters
        required_fields = [
            "symbol",
            "strike_price",
            "risk_free_rate",
            "expiry_date",
            "option_type"
        ]

        missing_fields = [
            field for field in required_fields
            if field not in data
        ]

        if missing_fields:
            return error_response(
                "missing_parameters",
                f"Missing required fields: {', '.join(missing_fields)}",
                400
            )

        # Validate request parameters
        try:

            # Symbol
            symbol = data["symbol"]

            if not isinstance(symbol, str):
                raise ValueError("'symbol' must be a string.")

            symbol = symbol.strip().upper()

            if not SYMBOL_PATTERN.fullmatch(symbol):
                raise ValueError("Invalid NSE stock symbol.")

            # Exchange
            exchange = data.get("exchange", "nse")

            if not isinstance(exchange, str):
                raise ValueError("'exchange' must be a string.")

            exchange = exchange.strip().lower()

            if exchange != "nse":
                raise ValueError(
                    "Only NSE data is supported currently."
                )

            # Option type
            option_type = data["option_type"]

            if not isinstance(option_type, str):
                raise ValueError(
                    "'option_type' must be a string."
                )

            option_type = option_type.strip().lower()

            if option_type not in ("call", "put"):
                raise ValueError(
                    "'option_type' must be either 'call' or 'put'."
                )

            # Expiry date
            expiry_date = data["expiry_date"]

            if not isinstance(expiry_date, str):
                raise ValueError(
                    "'expiry_date' must be a date string."
                )

            try:
                parsed_expiry = datetime.strptime(
                    expiry_date,
                    "%Y-%m-%d"
                )

                if parsed_expiry.strftime("%Y-%m-%d") != expiry_date:
                    raise ValueError

            except ValueError as exc:
                raise ValueError(
                    "'expiry_date' must use YYYY-MM-DD format."
                ) from exc

            # Financial inputs
            strike_price = get_number(
                data,
                "strike_price"
            )

            risk_free_rate = get_number(
                data,
                "risk_free_rate"
            )

            dividend_yield = get_number(
                data,
                "dividend_yield",
                default=0.0
            )

            if strike_price <= 0:
                raise ValueError(
                    "Strike price must be positive."
                )

            # Volatility selection
            volatility_mode = data.get(
                "volatility_mode",
                "historical"
            )

            if not isinstance(volatility_mode, str):
                raise ValueError(
                    "'volatility_mode' must be a string."
                )

            volatility_mode = volatility_mode.strip().lower()

            if volatility_mode not in ("historical", "manual"):
                raise ValueError(
                    "'volatility_mode' must be "
                    "'historical' or 'manual'."
                )

            manual_volatility = None

            if volatility_mode == "manual":

                if "manual_volatility" not in data:
                    raise ValueError(
                        "Manual volatility is required "
                        "in manual mode."
                    )

                manual_volatility = get_number(
                    data,
                    "manual_volatility"
                )

                if manual_volatility <= 0:
                    raise ValueError(
                        "Manual volatility must be positive."
                    )

            else:

                if data.get("manual_volatility") is not None:
                    raise ValueError(
                        "Do not supply manual_volatility "
                        "in historical mode."
                    )

            # Simulation settings
            simulations = get_integer(
                data,
                "simulations",
                default=100000
            )

            seed = get_integer(
                data,
                "seed",
                default=42
            )

            if simulations < 2:
                raise ValueError(
                    "At least 2 simulations are required."
                )

            if simulations > MAX_SIMULATIONS:
                raise ValueError(
                    f"Maximum allowed simulations are {MAX_SIMULATIONS}."
                )

            if seed < 0 or seed > MAX_UINT64:
                raise ValueError(
                    "Seed must be between 0 and 2^64 - 1."
                )

        except ValueError as exc:
            return error_response(
                "invalid_parameters",
                str(exc),
                400
            )

        # Run contract validation and pricing workflow.
        try:

            # Step 1: Inspect current market-data cache.
            data_status = get_market_data_status(
                symbol=symbol,
                exchange=exchange
            )

            # Reject missing market data before contract validation.
            if data_status["status"] == "missing":

                raise FileNotFoundError(
                    "Required raw or adjusted market data is missing."
                )

            # Invalid or mismatched data must not be priced.
            if data_status["status"] in (
                "invalid",
                "date_mismatch"
            ):

                details = " ".join(
                    data_status.get("warnings", [])
                )

                raise ValueError(
                    "Market data is invalid or inconsistent. "
                    + details
                )

            # Aging and stale data remain usable with warnings.
            spot_date_text = data_status["raw"]["latest_date"]

            spot_reference_date = (
                date.fromisoformat(spot_date_text)
                if spot_date_text
                else date.today()
            )

            reference_date = max(
                date.today(),
                spot_reference_date
            ).isoformat()

            # Step 2: Validate the exact listed contract.
            contract_metadata = validate_option_contract(
                symbol=symbol,
                expiry_date=expiry_date,
                strike_price=strike_price,
                option_type=option_type,
                reference_date=reference_date
            )

            # Step 3: Calculate the theoretical option price.
            result = price_from_market_data(
                symbol=symbol,
                strike_price=strike_price,
                risk_free_rate=risk_free_rate,
                dividend_yield=dividend_yield,
                time_to_expiry_years=None,
                expiry_date=expiry_date,
                option_type=option_type,
                simulations=simulations,
                seed=seed,
                exchange=exchange,
                volatility_mode=volatility_mode,
                manual_volatility=manual_volatility
            )

            # Step 4: Convert per-share estimates to lot values.
            lot_valuation = calculate_lot_values(
                pricing_result=result["pricing_result"],
                benchmark_result=result["benchmark_result"],
                contract_metadata=contract_metadata,
                comparison_result=result["comparison_result"]
            )

            # Step 5: Build transparent warnings.
            warnings = list(data_status["warnings"])

            if not contract_metadata["permitted_to_trade"]:
                warnings.append(
                    "The contract is present in the NSE master "
                    "but is not marked as permitted to trade. "
                    "The result is a theoretical valuation only."
                )

            if not contract_metadata["normal_market_eligible"]:
                warnings.append(
                    "The contract is not marked eligible for "
                    "the normal market in the NSE master."
                )

            # Check age of the imported contract-master snapshot.
            source_date = date.fromisoformat(
                contract_metadata["source_file_date"]
            )

            contract_age_days = (
                date.today() - source_date
            ).days

            if contract_age_days < 0:
                contract_status = "future_dated"
                warnings.append(
                    "The contract-master source date is later "
                    "than the local calendar date."
                )

            elif contract_age_days > 7:
                contract_status = "stale"
                warnings.append(
                    "The NSE contract-master snapshot is more "
                    "than seven calendar days old."
                )

            elif contract_age_days > 4:
                contract_status = "aging"
                warnings.append(
                    "The NSE contract-master snapshot is aging."
                )

            else:
                contract_status = "fresh"

            # Step 6: Attach Stage 16 information.
            result["contract_metadata"] = contract_metadata

            result["contract_master_status"] = {
                "source_file_date":
                    contract_metadata["source_file_date"],
                "age_calendar_days": contract_age_days,
                "status": contract_status
            }

            result["market_data_status"] = data_status

            result["lot_valuation"] = lot_valuation

            result["warnings"] = warnings

            return jsonify(result), 200

        except FileNotFoundError as exc:

            app.logger.warning(
                "Required OptionLab data is missing: %s",
                exc
            )

            return error_response(
                "required_data_not_found",
                "Required market-data or NSE contract metadata "
                "was not found. Check the local cache and "
                "contract-master import.",
                404
            )

        except ValueError as exc:

            app.logger.warning(
                "Pricing could not be completed: %s",
                exc
            )

            return error_response(
                "pricing_error",
                str(exc),
                422
            )

        except Exception:

            app.logger.exception(
                "Unexpected OptionLab API error."
            )

            return error_response(
                "internal_error",
                "An unexpected server error occurred.",
                500
            )

    return app
