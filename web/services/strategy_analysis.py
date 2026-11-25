import math

from web.services.black_scholes import (
    price_option_black_scholes
)

from web.services.contract_lookup import (
    validate_option_contract
)


SUPPORTED_STRATEGIES = {
    "long_call",
    "long_put",
    "bull_call_spread",
    "bear_put_spread"
}


def _number(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric.")

    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be numeric.")

    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite.")

    return value


def _positive_integer(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be a positive integer.")

    if value <= 0:
        raise ValueError(f"{name} must be a positive integer.")

    return value


def _build_legs(strategy, lower_strike, upper_strike):
    """
    Map strategy names to their option legs.

    position:
        +1 means long
        -1 means short
    """

    if strategy == "long_call":
        return [
            {
                "position": "long",
                "position_sign": 1,
                "option_type": "call",
                "strike_price": lower_strike
            }
        ]

    if strategy == "long_put":
        return [
            {
                "position": "long",
                "position_sign": 1,
                "option_type": "put",
                "strike_price": lower_strike
            }
        ]

    if strategy == "bull_call_spread":
        if upper_strike is None or lower_strike >= upper_strike:
            raise ValueError(
                "Bull Call Spread requires lower_strike "
                "to be below upper_strike."
            )

        return [
            {
                "position": "long",
                "position_sign": 1,
                "option_type": "call",
                "strike_price": lower_strike
            },
            {
                "position": "short",
                "position_sign": -1,
                "option_type": "call",
                "strike_price": upper_strike
            }
        ]

    if strategy == "bear_put_spread":
        if upper_strike is None or lower_strike >= upper_strike:
            raise ValueError(
                "Bear Put Spread requires lower_strike "
                "to be below upper_strike."
            )

        return [
            {
                "position": "short",
                "position_sign": -1,
                "option_type": "put",
                "strike_price": lower_strike
            },
            {
                "position": "long",
                "position_sign": 1,
                "option_type": "put",
                "strike_price": upper_strike
            }
        ]

    raise ValueError(
        f"Unsupported strategy: {strategy}"
    )


def _payoff_for_leg(terminal_spot, leg):
    if leg["option_type"] == "call":
        return max(
            terminal_spot - leg["strike_price"],
            0.0
        )

    return max(
        leg["strike_price"] - terminal_spot,
        0.0
    )


def analyze_option_strategy(
    parameters,
    symbol,
    expiry_date,
    reference_date,
    strategy,
    lower_strike,
    upper_strike=None,
    lots=1
):
    """
    Analyze a single-leg option or two-leg vertical spread.

    Every leg is checked against the imported NSE
    stock-option contract master.

    The theoretical leg premiums are calculated using BSM.
    """

    if not isinstance(parameters, dict):
        raise ValueError("Option parameters must be a dictionary.")

    symbol = str(symbol).strip().upper()

    strategy = str(strategy).strip().lower()

    if strategy not in SUPPORTED_STRATEGIES:
        raise ValueError("Unsupported option strategy.")

    lower_strike = _number(
        lower_strike,
        "lower_strike"
    )

    if lower_strike <= 0:
        raise ValueError("Lower strike must be positive.")

    if upper_strike is not None:
        upper_strike = _number(
            upper_strike,
            "upper_strike"
        )

        if upper_strike <= 0:
            raise ValueError("Upper strike must be positive.")

    lots = _positive_integer(lots, "lots")

    if lots > 50:
        raise ValueError("Maximum strategy quantity is 50 lots.")

    spot = _number(
        parameters.get("spot_price"),
        "spot_price"
    )

    rate = _number(
        parameters.get("risk_free_rate"),
        "risk_free_rate"
    )

    dividend = _number(
        parameters.get("dividend_yield"),
        "dividend_yield"
    )

    volatility = _number(
        parameters.get("volatility"),
        "volatility"
    )

    maturity = _number(
        parameters.get("time_to_expiry_years"),
        "time_to_expiry_years"
    )

    if spot <= 0:
        raise ValueError("Spot price must be positive.")

    if volatility < 0:
        raise ValueError(
            "Volatility cannot be negative."
        )

    if maturity <= 0:
        raise ValueError(
            "Time to expiry must be positive."
        )

    leg_specs = _build_legs(
        strategy,
        lower_strike,
        upper_strike
    )

    legs = []

    for spec in leg_specs:

        # Verify that this exact NSE-listed contract exists.
        contract = validate_option_contract(
            symbol=symbol,
            expiry_date=expiry_date,
            strike_price=spec["strike_price"],
            option_type=spec["option_type"],
            reference_date=reference_date
        )

        # Use the actual contract's lot quantity.
        lot_size = int(
            contract["board_lot_quantity"]
        )

        if lot_size <= 0:
            raise ValueError(
                "NSE contract board-lot quantity must be positive."
            )

        # A vertical spread must have equal underlying
        # quantities in both legs.
        #
        # Equal numbers of lots do not necessarily mean
        # equal underlying quantities if contract lot sizes differ.
        if (
            strategy in (
                "bull_call_spread",
                "bear_put_spread"
            )
            and legs
        ):

            first_leg_lot_size = (
                legs[0]["board_lot_quantity"]
            )

            if lot_size != first_leg_lot_size:

                raise ValueError(
                    "Vertical spread legs must have identical "
                    "NSE board-lot quantities. "
                    f"First leg: {first_leg_lot_size}; "
                    f"second leg: {lot_size}."
                )

        total_units = lot_size * lots

        # Price each leg with the same market assumptions,
        # changing only strike and Call/Put type.
        leg_parameters = parameters.copy()

        leg_parameters["strike_price"] = spec["strike_price"]
        leg_parameters["option_type"] = spec["option_type"]

        analytical_result = price_option_black_scholes(
            leg_parameters
        )

        premium = _number(
            analytical_result["estimated_price"],
            "analytical premium"
        )

        leg = {
            "contract_id": contract["contract_id"],
            "symbol": symbol,
            "expiry_date": expiry_date,
            "option_type": spec["option_type"],
            "position": spec["position"],
            "position_sign": spec["position_sign"],
            "strike_price": float(spec["strike_price"]),
            "premium_per_share": premium,
            "board_lot_quantity": lot_size,
            "lots": lots,
            "total_units": total_units,
            "premium_cashflow": (
                -spec["position_sign"] * premium * total_units
            ),
            "permitted_to_trade": contract["permitted_to_trade"]
        }

        legs.append(leg)

    def strategy_pnl(terminal_spot):
        total = 0.0

        for leg in legs:

            payoff = _payoff_for_leg(
                terminal_spot,
                leg
            )

            total += (
                leg["position_sign"]
                * (payoff - leg["premium_per_share"])
                * leg["total_units"]
            )

        return total

    # Break-even values occur at a zero or a sign change
    # of the piecewise-linear P&L curve.
    strike_points = sorted({
        0.0,
        *[leg["strike_price"] for leg in legs]
    })

    pnl_at_breakpoints = [
        (value, strategy_pnl(value))
        for value in strike_points
    ]

    break_even_values = []

    tolerance = 1e-8

    for value, pnl in pnl_at_breakpoints:
        if abs(pnl) < tolerance:
            break_even_values.append(value)

    for index in range(len(pnl_at_breakpoints) - 1):

        x1, y1 = pnl_at_breakpoints[index]
        x2, y2 = pnl_at_breakpoints[index + 1]

        if y1 * y2 < 0:
            root = x1 + (
                -y1 * (x2 - x1) / (y2 - y1)
            )

            break_even_values.append(root)

    # Above the highest strike, only Call legs contribute
    # a non-zero slope.
    tail_start = max(
        strike_points
    )

    tail_value = strategy_pnl(tail_start)

    tail_slope = sum(
        leg["position_sign"] * leg["total_units"]
        for leg in legs
        if leg["option_type"] == "call"
    )

    if abs(tail_slope) > tolerance:

        tail_root = (
            tail_start - tail_value / tail_slope
        )

        if tail_root >= tail_start:
            if abs(strategy_pnl(tail_root)) < 1e-6:
                break_even_values.append(tail_root)

    break_even_values = sorted({
        round(value, 6)
        for value in break_even_values
        if value >= 0
    })

    finite_pnls = [
        pnl for _, pnl in pnl_at_breakpoints
    ]

    finite_maximum = max(finite_pnls)
    finite_minimum = min(finite_pnls)

    if tail_slope > tolerance:
        maximum_profit = None
        maximum_profit_label = "Unlimited"
    else:
        maximum_profit = max(finite_maximum, 0.0)
        maximum_profit_label = "Finite"

    if tail_slope < -tolerance:
        maximum_loss = None
        maximum_loss_label = "Unlimited"
    else:
        maximum_loss = max(-finite_minimum, 0.0)
        maximum_loss_label = "Finite"

    # Create a visualization grid.
    maximum_strike = max(
        leg["strike_price"] for leg in legs
    )

    upper_grid = max(spot, maximum_strike) * 2.0

    grid = [
        upper_grid * index / 120
        for index in range(121)
    ]

    grid.extend(strike_points)
    grid.extend(break_even_values)

    grid = sorted(set(grid))

    strategy_points = [
        {
            "terminal_stock_price": value,
            "strategy_pnl": strategy_pnl(value)
        }
        for value in grid
    ]

    initial_net_cashflow = sum(
        leg["premium_cashflow"]
        for leg in legs
    )

    warnings = []

    for leg in legs:
        if not leg["permitted_to_trade"]:
            warnings.append(
                f"{leg['option_type'].upper()} at "
                f"₹{leg['strike_price']:.2f} is not marked "
                "as permitted to trade in the imported NSE master."
            )

    return {
        "strategy": strategy,
        "symbol": symbol,
        "expiry_date": expiry_date,
        "lots_per_leg": lots,

        "legs": legs,

        "initial_net_cashflow": initial_net_cashflow,

        "initial_cashflow_label": (
            "Net credit" if initial_net_cashflow >= 0
            else "Net debit"
        ),

        "maximum_profit": maximum_profit,
        "maximum_profit_label": maximum_profit_label,

        "maximum_loss": maximum_loss,
        "maximum_loss_label": maximum_loss_label,

        "break_even_prices": break_even_values,

        "tail_pnl_slope": tail_slope,

        "points": strategy_points,

        "warnings": warnings,

        "pricing_method": (
            "Black-Scholes-Merton theoretical premium for each leg."
        ),

        "limitations": (
            "Excludes brokerage, taxes, slippage, margin, "
            "early exercise and transaction costs. "
            "The chart is an expiry scenario analysis."
        )
    }



