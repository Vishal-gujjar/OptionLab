import argparse
import sys

from datetime import date, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PROJECT_ROOT))

from web.services.tejhq_client import fetch_adjusted
from web.services.csv_store import save_adjusted_csv
from web.services.volatility import calculate_historical_volatility


def main():

    parser = argparse.ArgumentParser(
        description="Download adjusted stock prices and calculate volatility."
    )

    parser.add_argument(
        "--symbol",
        default="RELIANCE"
    )

    parser.add_argument(
        "--exchange",
        choices=["nse", "bse"],
        default="nse"
    )

    parser.add_argument(
        "--years",
        type=int,
        choices=[1, 2],
        default=1
    )

    args = parser.parse_args()

    end_date = date.today()
    start_date = end_date - timedelta(days=365 * args.years)

    symbol = args.symbol.upper()

    print("\n================================")
    print("  OPTIONLAB ADJUSTED DATA")
    print("================================")

    print("Company:", symbol)
    print("Exchange:", args.exchange.upper())
    print("Period:", start_date, "to", end_date)

    try:

        print("\nFetching adjusted prices...")

        response = fetch_adjusted(
            symbol=symbol,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            exchange=args.exchange
        )

        rows = response["data"]

        if not rows:
            raise RuntimeError("No adjusted data received.")

        output_file = save_adjusted_csv(
            symbol=symbol,
            exchange=args.exchange,
            rows=rows
        )

        print("\nAdjusted data successfully saved.")

        print("Records downloaded:", len(rows))
        print("CSV file:", output_file)

        print(
            "Latest adjusted close:",
            rows[-1]["adj_close"]
        )

        print("\nCalculating historical volatility...")

        result = calculate_historical_volatility(
            output_file
        )

        print("\n================================")
        print("    VOLATILITY RESULTS")
        print("================================")

        print("Company:", symbol)

        print(
            "Price observations:",
            result["observations"]
        )

        print(
            "Return observations:",
            result["return_observations"]
        )

        print(
            "First date:",
            result["first_date"]
        )

        print(
            "Last date:",
            result["last_date"]
        )

        print(
            "Daily volatility:",
            f"{result['daily_volatility'] * 100:.4f}%"
        )

        print(
            "Annualized volatility:",
            f"{result['annualized_volatility_percent']:.4f}%"
        )

        print("\n================================")
        print("    STAGE 8 COMPLETED")
        print("================================")

    except Exception as error:

        print("\nERROR:", error)
        sys.exit(1)


if __name__ == "__main__":
    main()



    