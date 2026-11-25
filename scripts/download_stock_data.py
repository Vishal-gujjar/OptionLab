import argparse
import csv
import sys

from datetime import date, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PROJECT_ROOT))

from web.services.tejhq_client import fetch_ohlcv
from web.services.csv_store import save_ohlcv_csv


def main():

    parser = argparse.ArgumentParser(
        description="Download historical NSE/BSE stock prices."
    )

    parser.add_argument(
        "--symbol",
        default="RELIANCE",
        help="Stock trading symbol."
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
        default=1,
        help="Historical period: 1 or 2 years."
    )

    parser.add_argument(
        "--start-date",
        help="Optional start date (YYYY-MM-DD)."
    )

    parser.add_argument(
        "--end-date",
        help="Optional end date (YYYY-MM-DD)."
    )

    args = parser.parse_args()

    if bool(args.start_date) != bool(args.end_date):
        parser.error(
            "Provide both --start-date and --end-date."
        )

    if args.start_date and args.end_date:

        try:
            start_date = date.fromisoformat(args.start_date)
            end_date = date.fromisoformat(args.end_date)

        except ValueError:
            parser.error("Dates must use YYYY-MM-DD.")

        if start_date > end_date:
            parser.error("Start date cannot exceed end date.")

    else:

        end_date = date.today()
        start_date = end_date - timedelta(
            days=365 * args.years
        )

    symbol = args.symbol.upper()

    print("\n================================")
    print("     OPTIONLAB CSV DOWNLOADER")
    print("================================")

    print("Company:", symbol)
    print("Exchange:", args.exchange.upper())
    print("From:", start_date)
    print("To:", end_date)

    print("\nFetching data from TejHQ...")

    try:

        response = fetch_ohlcv(
            symbol=symbol,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            exchange=args.exchange
        )

        rows = response["data"]

        if not rows:
            raise RuntimeError(
                "No historical observations returned."
            )

        output_file = save_ohlcv_csv(
            symbol=symbol,
            exchange=args.exchange,
            rows=rows
        )

        with output_file.open(
            "r",
            newline="",
            encoding="utf-8"
        ) as file:

            saved_rows = list(csv.DictReader(file))

        print("\nDownload successful!")
        print("New API records:", len(rows))
        print("Total stored records:", len(saved_rows))

        print("First stored date:", saved_rows[0]["date"])
        print("Latest stored date:", saved_rows[-1]["date"])

        print("\nLatest closing price:",
              saved_rows[-1]["close"])

        print("\nCSV location:")
        print(output_file)

        print("\n================================")
        print("     CSV STORAGE COMPLETED")
        print("================================")

    except Exception as error:

        print("\nERROR:", error)
        sys.exit(1)


if __name__ == "__main__":
    main()


    