import csv
import math

from pathlib import Path

from web.services.volatility import calculate_historical_volatility

from web.services.market_data_status import (
    get_market_data_status
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_market_inputs(
    symbol: str,
    exchange: str = "nse",
    cache_dir: Path | None = None
) -> dict:

    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError(
            "A valid stock symbol is required."
        )

    symbol = symbol.strip().upper()

    if not isinstance(exchange, str):
        raise ValueError(
            "Exchange must be a string."
        )

    exchange = exchange.strip().lower()

    if exchange not in ("nse", "bse"):
        raise ValueError(
            "Exchange must be NSE or BSE."
        )

    data_dir = Path(
        cache_dir or PROJECT_ROOT / "data" / "cache"
    )

    raw_file = data_dir / f"{exchange}_{symbol}.csv"

    adjusted_file = (
        data_dir / f"{exchange}_{symbol}_adjusted.csv"
    )

    # Preserve the existing missing-file behaviour.
    if not raw_file.is_file():
        raise FileNotFoundError(raw_file)

    if not adjusted_file.is_file():
        raise FileNotFoundError(adjusted_file)

    # Inspect both datasets before using them.
    data_status = get_market_data_status(
        symbol=symbol,
        exchange=exchange,
        cache_dir=data_dir
    )

    # Missing datasets must never reach pricing.
    if data_status["status"] == "missing":
        raise FileNotFoundError(
            "Required raw or adjusted market data is missing."
        )

    # Invalid or mismatched datasets must never reach pricing.
    if data_status["status"] in (
        "invalid",
        "date_mismatch"
    ):

        details = " ".join(
            data_status.get("warnings", [])
        )

        raise ValueError(
            "Market data cannot be used for pricing. "
            + details
        )

    # Aging and stale data remain usable.
    # Their warning information is available in the status response.

    # Read the latest raw market closing price.
    with raw_file.open(
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        required_columns = {
            "symbol",
            "exchange",
            "date",
            "close",
            "price_basis"
        }

        if not reader.fieldnames or not required_columns.issubset(
            reader.fieldnames
        ):
            raise ValueError(
                "Invalid raw market CSV schema."
            )

        raw_rows = list(reader)

    if not raw_rows:
        raise ValueError(
            "Raw market CSV is empty."
        )

    # Confirm that every row belongs to the selected instrument.
    for row in raw_rows:

        if (
            row["symbol"] != symbol
            or row["exchange"] != exchange.upper()
            or row["price_basis"] != "raw_ohlcv"
        ):
            raise ValueError(
                "Raw market data mismatch."
            )

    raw_rows.sort(
        key=lambda row: row["date"]
    )

    latest_raw = raw_rows[-1]

    spot_price = float(
        latest_raw["close"]
    )

    if not math.isfinite(spot_price) or spot_price <= 0:
        raise ValueError(
            "Invalid latest market price."
        )

    # Calculate volatility from adjusted closing prices.
    volatility_result = calculate_historical_volatility(
        adjusted_file,
        annualization_days=252
    )

    return {
        "symbol": symbol,
        "exchange": exchange.upper(),

        "spot_price": spot_price,
        "spot_date": latest_raw["date"],

        "volatility": volatility_result[
            "annualized_volatility"
        ],

        "volatility_percent": volatility_result[
            "annualized_volatility_percent"
        ],

        "volatility_start_date": volatility_result[
            "first_date"
        ],

        "volatility_end_date": volatility_result[
            "last_date"
        ],

        "price_observations": volatility_result[
            "observations"
        ],

        "volatility_method": "Historical volatility",
        "annualization_days": 252
    }