import sys

from datetime import date, timedelta
from pathlib import Path


# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PROJECT_ROOT))

from web.services.tejhq_client import fetch_ohlcv


def main():

    symbol = "RELIANCE"

    end_date = date.today()
    start_date = end_date - timedelta(days=365)

    print("\n================================")
    print("     OPTIONLAB MARKET DATA")
    print("================================")

    print("Provider: TejHQ")
    print("Exchange: NSE")
    print("Company:", symbol)
    print("Period:", start_date, "to", end_date)

    print("\nFetching historical data...")

    try:

        response = fetch_ohlcv(
            symbol=symbol,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            exchange="nse"
        )

        rows = response["data"]

        if not rows:
            raise RuntimeError(
                "No historical data returned."
            )

        first = rows[0]
        latest = rows[-1]

        print("\nData successfully retrieved!")

        print("\nCompany:", symbol)
        print("Exchange:", response["meta"].get("exchange"))
        print("Number of records:", len(rows))

        print("\nFirst available record:")
        print("Date:", first["date"])
        print("Open:", first["open"])
        print("High:", first["high"])
        print("Low:", first["low"])
        print("Close:", first["close"])
        print("Volume:", first["volume"])

        print("\nLatest available record:")
        print("Date:", latest["date"])
        print("Open:", latest["open"])
        print("High:", latest["high"])
        print("Low:", latest["low"])
        print("Close:", latest["close"])
        print("Volume:", latest["volume"])

        print("\n================================")
        print("TEJHQ CONNECTION SUCCESSFUL")
        print("================================")

    except Exception as error:

        print("\nERROR:", error)

        sys.exit(1)


if __name__ == "__main__":
    main()



    