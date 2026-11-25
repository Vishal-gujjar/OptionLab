import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


from web.services.option_workflow import price_from_market_data

from web.services.model_validation import (
    run_convergence_analysis
)


def main():
    parser = argparse.ArgumentParser(
        description="OptionLab Monte Carlo Convergence Analysis"
    )

    parser.add_argument(
        "--symbol",
        required=True
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
        "--expiry",
        required=True
    )

    parser.add_argument(
        "--type",
        choices=["call", "put"],
        required=True
    )

    parser.add_argument(
        "--volatility-mode",
        choices=["historical", "manual"],
        default="historical"
    )

    parser.add_argument(
        "--manual-volatility",
        type=float
    )

    parser.add_argument(
        "--simulation-counts",
        nargs="+",
        type=int,
        default=[1000, 5000, 10000, 50000, 100000]
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42
    )

    args = parser.parse_args()

    if args.volatility_mode == "manual":
        if args.manual_volatility is None:
            parser.error(
                "--manual-volatility is required in manual mode."
            )

    elif args.manual_volatility is not None:
        parser.error(
            "--manual-volatility should only be supplied "
            "when using manual mode."
        )

    # Load the market inputs and build the option parameters.
    # Two simulations are sufficient here because the actual
    # convergence calculations are run separately below.
    base_result = price_from_market_data(
        symbol=args.symbol,
        strike_price=args.strike,
        risk_free_rate=args.rate,
        dividend_yield=args.dividend,
        time_to_expiry_years=None,
        option_type=args.type,
        simulations=2,
        seed=args.seed,
        exchange="nse",
        expiry_date=args.expiry,
        volatility_mode=args.volatility_mode,
        manual_volatility=args.manual_volatility
    )

    option_parameters = base_result["option_parameters"]

    results = run_convergence_analysis(
        option_parameters=option_parameters,
        simulation_counts=args.simulation_counts,
        seed=args.seed
    )

    print("\nOPTIONLAB — MONTE CARLO CONVERGENCE")
    print("----------------------------------")

    print(f"Symbol: {args.symbol.upper()}")
    print(f"Spot price: {option_parameters['spot_price']:.4f}")
    print(f"Strike: {args.strike:.4f}")
    print(f"Option type: {args.type.upper()}")
    print(f"Volatility: {option_parameters['volatility'] * 100:.4f}%")
    print(f"Analytical benchmark: {results[0]['analytical_price']:.6f}")

    print("\nRESULTS")
    print(
        f"{'Simulations':>12} "
        f"{'MC Price':>12} "
        f"{'Std Error':>12} "
        f"{'Abs Error':>12} "
        f"{'Rel Error %':>12} "
        f"{'CI Contains':>12}"
    )

    for row in results:
        relative_error = row["relative_error_percent"]

        relative_text = (
            f"{relative_error:.6f}"
            if relative_error is not None
            else "N/A"
        )

        ci_text = (
            "YES"
            if row["confidence_interval_contains_benchmark"]
            else "NO"
        )

        print(
            f"{row['simulations']:>12} "
            f"{row['monte_carlo_price']:>12.6f} "
            f"{row['standard_error']:>12.6f} "
            f"{row['absolute_error']:>12.6f} "
            f"{relative_text:>12} "
            f"{ci_text:>12}"
        )


if __name__ == "__main__":
    main()