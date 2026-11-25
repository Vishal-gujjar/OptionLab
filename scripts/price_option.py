import argparse
import json
import sys

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PROJECT_ROOT))

from web.services.option_workflow import price_from_market_data


def main():

    parser = argparse.ArgumentParser(
        description="Calculate option price using real historical stock data."
    )

    parser.add_argument(
        "--symbol",
        required=True
    )

    parser.add_argument(
        "--exchange",
        choices=["nse", "bse"],
        default="nse"
    )

    parser.add_argument(
        "--strike",
        type=float,
        required=True
    )

    parser.add_argument(
        "--rate",
        type=float,
        required=True
    )

    parser.add_argument(
        "--dividend",
        type=float,
        default=0.0
    )

    parser.add_argument(
        "--maturity",
        type=float,
        required=True
    )

    parser.add_argument(
        "--type",
        choices=["call", "put"],
        required=True
    )

    parser.add_argument(
        "--simulations",
        type=int,
        default=100000
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42
    )

    args = parser.parse_args()

    try:

        result = price_from_market_data(
            symbol=args.symbol,
            exchange=args.exchange,
            strike_price=args.strike,
            risk_free_rate=args.rate,
            dividend_yield=args.dividend,
            time_to_expiry_years=args.maturity,
            option_type=args.type,
            simulations=args.simulations,
            seed=args.seed
        )

        print("\n================================")
        print("       OPTIONLAB PRICING")
        print("================================")

        market = result["market_data"]

        print("\nMarket Information")

        print("Company:", market["symbol"])
        print("Exchange:", market["exchange"])

        print("Spot Price:", market["spot_price"])
        print("Spot Date:", market["spot_date"])

        print(
            "Historical Volatility:",
            f"{market['volatility_percent']:.4f}%"
        )

        print(
            "Volatility Period:",
            market["volatility_start_date"],
            "to",
            market["volatility_end_date"]
        )

        pricing = result["pricing_result"]

        print("\nMonte Carlo Results")

        print(
            "Estimated Premium:",
            f"₹{pricing['estimated_price']:.6f} per share"
        )

        print(
            "Standard Error:",
            pricing["standard_error"]
        )

        print(
            "95% Confidence Interval:",
            pricing["confidence_interval_lower"],
            "to",
            pricing["confidence_interval_upper"]
        )

        print(
            "Simulations:",
            pricing["simulations"]
        )

        print("\n================================")

        # Complete machine-readable result
        print("\nJSON RESULT")

        print(json.dumps(result, indent=4))

    except Exception as error:

        print("\nPRICING ERROR:", error)

        sys.exit(1)


if __name__ == "__main__":
    main()