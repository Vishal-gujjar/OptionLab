
import math
from web.services.market_inputs import load_market_inputs
from web.services.pricing_bridge import price_option
from web.services.time_to_expiry import calculate_time_to_expiry

from web.services.black_scholes import (
    price_option_black_scholes
)

from web.services.model_validation import (
    compare_pricing_results
)

from web.services.greeks import (
    calculate_greeks,
    calculate_numerical_greeks,
    compare_greeks
)

from web.services.sensitivity import (
    calculate_sensitivity
)

def price_from_market_data(
    symbol,
    strike_price,
    risk_free_rate,
    dividend_yield,
    time_to_expiry_years,
    option_type,
    simulations=100000,
    seed=42,
    exchange="nse",
    expiry_date=None,
    volatility_mode="historical",
    manual_volatility=None
):
    """
    Load market data and price an option.

    Volatility modes:
        historical: Use calculated historical volatility.
        manual: Use user-provided annualized volatility.

    Manual volatility is an assumption. It is not automatically
    an implied volatility derived from market option prices.
    """

    # Step 1: Load market information
    market_data = load_market_inputs(
        symbol=symbol,
        exchange=exchange
    )

    # Step 2: Calculate maturity
    if expiry_date is not None:

        maturity_info = calculate_time_to_expiry(
            valuation_date=market_data["spot_date"],
            expiry_date=expiry_date
        )

        maturity = maturity_info["time_to_expiry_years"]

    else:

        if time_to_expiry_years is None:
            raise ValueError(
                "Either expiry_date or time_to_expiry_years "
                "must be supplied."
            )

        if isinstance(time_to_expiry_years, bool):
            raise ValueError(
                "Time to expiry must be a valid number."
            )

        maturity = float(time_to_expiry_years)

        if not math.isfinite(maturity) or maturity < 0:
            raise ValueError(
                "Time to expiry must be finite and non-negative."
            )

        maturity_info = {
            "valuation_date": market_data["spot_date"],
            "expiry_date": None,
            "calendar_days_to_expiry": None,
            "day_count_convention": "Manual year fraction",
            "time_to_expiry_years": maturity
        }

    # Step 3: Select volatility
    volatility_mode = str(volatility_mode).strip().lower()

    if volatility_mode == "historical":

        if manual_volatility is not None:
            raise ValueError(
                "Do not supply manual_volatility in historical mode."
            )

        selected_volatility = market_data["volatility"]

        volatility_info = {
            "mode": "historical",
            "method": "Historical volatility",
            "annualized_volatility": selected_volatility,
            "annualized_volatility_percent": (
                selected_volatility * 100
            )
        }

    elif volatility_mode == "manual":

        if manual_volatility is None:
            raise ValueError(
                "Manual volatility is required in manual mode."
            )

        if isinstance(manual_volatility, bool):
            raise ValueError(
                "Manual volatility must be a valid number."
            )

        try:
            selected_volatility = float(manual_volatility)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "Manual volatility must be numeric."
            ) from exc

        if (
            not math.isfinite(selected_volatility)
            or selected_volatility <= 0
        ):
            raise ValueError(
                "Manual volatility must be finite and positive."
            )

        volatility_info = {
            "mode": "manual",
            "method": "Manual volatility assumption",
            "annualized_volatility": selected_volatility,
            "annualized_volatility_percent": (
                selected_volatility * 100
            )
        }

    else:
        raise ValueError(
            "volatility_mode must be 'historical' or 'manual'."
        )

    # Step 4: Construct pricing parameters
    parameters = {
        "spot_price": market_data["spot_price"],
        "strike_price": strike_price,
        "risk_free_rate": risk_free_rate,
        "dividend_yield": dividend_yield,
        "volatility": selected_volatility,
        "time_to_expiry_years": maturity,
        "option_type": option_type,
        "simulations": simulations,
        "seed": seed
    }

    # Step 5: Call C++ Monte Carlo engine
    pricing_result = price_option(parameters)

    benchmark_result = price_option_black_scholes(
        parameters
    )

    comparison_result = compare_pricing_results(
        pricing_result,
        benchmark_result
    )

    # --------------------------------------------------
    # Step 6: Calculate Greeks when mathematically valid
    # --------------------------------------------------

    greeks_available = (
        selected_volatility > 0
        and maturity > 0
    )

    if greeks_available:

        # Analytical Greeks.
        greeks_result = calculate_greeks(
            parameters
        )

        # Numerical Greeks using finite differences.
        numerical_greeks_result = calculate_numerical_greeks(
            parameters
        )

        # Compare analytical and numerical Greeks.
        greeks_validation_result = compare_greeks(
            greeks_result,
            numerical_greeks_result
        )

    else:

        unavailable_reasons = []

        if selected_volatility <= 0:

            unavailable_reasons.append(
                "Standard Black-Scholes-Merton Greeks "
                "are unavailable at zero volatility."
            )

        if maturity <= 0:

            unavailable_reasons.append(
                "Standard option Greeks are unavailable "
                "at expiry because the payoff is not "
                "differentiable at the strike."
            )

        unavailable_reason = " ".join(
            unavailable_reasons
        )

        # Return an explicit unavailable status rather
        # than failing the complete pricing workflow.
        greeks_result = {
            "available": False,
            "model": "Black-Scholes-Merton",
            "reason": unavailable_reason
        }

        numerical_greeks_result = {
            "available": False,
            "reason": unavailable_reason
        }

        greeks_validation_result = {
            "available": False,
            "reason": unavailable_reason
        }

    # --------------------------------------------------
    # Step 7: Sensitivity analysis
    # --------------------------------------------------

    sensitivity_result = calculate_sensitivity(
        parameters
    )

    # Step 6: Return all information
    return {
        "market_data": market_data,

        "maturity_info": maturity_info,

        "volatility_info": volatility_info,

        "financial_assumptions": {
            "risk_free_rate": float(risk_free_rate),
            "risk_free_rate_percent":
                float(risk_free_rate) * 100,
            "risk_free_rate_convention":
                "Annualized continuously compounded rate",

            "dividend_yield": float(dividend_yield),
            "dividend_yield_percent":
                float(dividend_yield) * 100,
            "dividend_yield_convention":
                "Annualized continuous dividend yield"
        },

        "option_parameters": parameters,

        "pricing_result": pricing_result,

        "benchmark_result": benchmark_result,

        "comparison_result": comparison_result,

        "greeks_result": greeks_result,

        "numerical_greeks_result": numerical_greeks_result,

        "greeks_validation_result": greeks_validation_result,

        "sensitivity_result": sensitivity_result
    }
