import csv
import math
import os
import tempfile

from datetime import date, datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CSV_COLUMNS = [
    "symbol",
    "exchange",
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "source",
    "price_basis",
    "retrieved_at_utc",
]


def save_ohlcv_csv(
    symbol: str,
    exchange: str,
    rows: list[dict],
    cache_dir: Path | None = None
) -> Path:

    """
    Save historical OHLCV observations into a CSV file.

    Existing dates are updated.
    Older observations are preserved.
    Duplicate dates are eliminated.
    """

    symbol = symbol.strip().upper()
    exchange = exchange.strip().upper()

    if not symbol or not exchange:
        raise ValueError("Symbol and exchange are required.")

    if not rows:
        raise ValueError("Cannot save empty market data.")

    output_dir = Path(
        cache_dir or PROJECT_ROOT / "data" / "cache"
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{exchange.lower()}_{symbol}.csv"

    # Store observations using date as the unique key.
    observations = {}

    # Read previously stored observations.
    if output_file.exists():

        with output_file.open(
            "r",
            newline="",
            encoding="utf-8"
        ) as file:

            reader = csv.DictReader(file)

            if reader.fieldnames != CSV_COLUMNS:
                raise ValueError(
                    "Existing CSV has an unexpected schema."
                )

            for row in reader:

                if (
                    row["symbol"] != symbol
                    or row["exchange"] != exchange
                ):
                    raise ValueError(
                        "Existing CSV contains another instrument."
                    )

                observations[row["date"]] = row

    retrieved_at = (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )

    # Validate and merge incoming observations.
    for row in rows:

        if not isinstance(row, dict):
            raise ValueError(
                "Every market-data observation must be a dictionary."
            )

        try:
            observation_date = date.fromisoformat(
                row.get("date", "")
            )

        except (TypeError, ValueError):
            raise ValueError(
                "Invalid observation date."
            ) from None

        prices = {
            field: _finite_number(
                row.get(field),
                field
            )
            for field in ("open", "high", "low", "close")
        }

        volume = _finite_number(
            row.get("volume"),
            "volume"
        )

        if any(value <= 0 for value in prices.values()):
            raise ValueError(
                "Stock prices must be positive."
            )

        if volume < 0 or not volume.is_integer():
            raise ValueError(
                "Volume must be a non-negative integer."
            )

        if prices["high"] < max(
            prices["open"],
            prices["close"],
            prices["low"]
        ):
            raise ValueError(
                "Invalid daily high."
            )

        if prices["low"] > min(
            prices["open"],
            prices["close"],
            prices["high"]
        ):
            raise ValueError(
                "Invalid daily low."
            )

        observations[observation_date.isoformat()] = {
            "symbol": symbol,
            "exchange": exchange,
            "date": observation_date.isoformat(),
            "open": str(row["open"]),
            "high": str(row["high"]),
            "low": str(row["low"]),
            "close": str(row["close"]),
            "volume": str(int(volume)),
            "source": "TejHQ",
            "price_basis": "raw_ohlcv",
            "retrieved_at_utc": retrieved_at,
        }

    # Sort all observations chronologically.
    sorted_rows = sorted(
        observations.values(),
        key=lambda item: item["date"]
    )

    # Write to a temporary file first.
    temporary_path = None

    try:

        with tempfile.NamedTemporaryFile(
            mode="w",
            newline="",
            encoding="utf-8",
            dir=output_dir,
            suffix=".tmp",
            delete=False
        ) as file:

            temporary_path = Path(file.name)

            writer = csv.DictWriter(
                file,
                fieldnames=CSV_COLUMNS
            )

            writer.writeheader()
            writer.writerows(sorted_rows)

        # Replace destination only after successful writing.
        os.replace(temporary_path, output_file)

    finally:

        if (
            temporary_path is not None
            and temporary_path.exists()
        ):
            temporary_path.unlink()

    return output_file




ADJUSTED_CSV_COLUMNS = CSV_COLUMNS + [
    "adj_factor_cumulative",
    "adj_close",
]


def _finite_number(value, field_name):

    """
    Convert a value to float and reject NaN or Infinity.
    """

    if isinstance(value, bool):
        raise ValueError(
            f"{field_name} must be a finite number."
        )

    try:
        number = float(value)

    except (TypeError, ValueError, OverflowError):
        raise ValueError(
            f"{field_name} must be a finite number."
        ) from None

    if not math.isfinite(number):
        raise ValueError(
            f"{field_name} must be a finite number."
        )

    return number


def save_adjusted_csv(
    symbol: str,
    exchange: str,
    rows: list[dict],
    cache_dir: Path | None = None
) -> Path:

    symbol = symbol.strip().upper()
    exchange = exchange.strip().upper()

    if not symbol or exchange not in ("NSE", "BSE"):
        raise ValueError("Invalid instrument.")

    if not rows:
        raise ValueError("Cannot save empty adjusted data.")

    output_dir = Path(
        cache_dir or PROJECT_ROOT / "data" / "cache"
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = (
        output_dir /
        f"{exchange.lower()}_{symbol}_adjusted.csv"
    )

    observations = {}

    # Preserve previously downloaded adjusted observations.
    if output_file.exists():

        with output_file.open(
            "r", newline="", encoding="utf-8"
        ) as file:

            reader = csv.DictReader(file)

            if reader.fieldnames != ADJUSTED_CSV_COLUMNS:
                raise ValueError(
                    "Unexpected adjusted CSV schema."
                )

            for row in reader:
                if (
                    row["symbol"] != symbol
                    or row["exchange"] != exchange
                ):
                    raise ValueError("Instrument mismatch.")

                observations[row["date"]] = row

    retrieved_at = (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )

    for row in rows:

        if not isinstance(row, dict):
            raise ValueError(
                "Every adjusted observation must be a dictionary."
            )

        try:
            observation_date = date.fromisoformat(
                row.get("date", "")
            )

        except (TypeError, ValueError):
            raise ValueError(
                "Invalid adjusted observation date."
            ) from None

        open_price = _finite_number(
            row.get("open"), "open"
        )

        high_price = _finite_number(
            row.get("high"), "high"
        )

        low_price = _finite_number(
            row.get("low"), "low"
        )

        close_price = _finite_number(
            row.get("close"), "close"
        )

        adjusted_close = _finite_number(
            row.get("adj_close"), "adj_close"
        )

        factor = _finite_number(
            row.get("adj_factor_cumulative"),
            "adj_factor_cumulative"
        )

        volume = _finite_number(
            row.get("volume"), "volume"
        )

        if min(
            open_price,
            high_price,
            low_price,
            close_price,
            adjusted_close,
            factor
        ) <= 0:
            raise ValueError(
                "Adjusted prices and adjustment factor must be positive."
            )

        if volume < 0 or not volume.is_integer():
            raise ValueError(
                "Volume must be a non-negative integer."
            )

        if (
            high_price < max(
                open_price,
                close_price,
                low_price
            )
            or low_price > min(
                open_price,
                close_price,
                high_price
            )
        ):
            raise ValueError(
                "Inconsistent adjusted OHLC values."
            )

        observations[observation_date.isoformat()] = {
            "symbol": symbol,
            "exchange": exchange,
            "date": observation_date.isoformat(),
            "open": str(open_price),
            "high": str(high_price),
            "low": str(low_price),
            "close": str(close_price),
            "volume": str(int(volume)),
            "source": "TejHQ",
            "price_basis": "adjusted_close",
            "retrieved_at_utc": retrieved_at,
            "adj_factor_cumulative": str(factor),
            "adj_close": str(adjusted_close),
        }

    sorted_rows = sorted(
        observations.values(),
        key=lambda item: item["date"]
    )

    temporary_path = None

    try:

        with tempfile.NamedTemporaryFile(
            mode="w",
            newline="",
            encoding="utf-8",
            dir=output_dir,
            suffix=".tmp",
            delete=False
        ) as file:

            temporary_path = Path(file.name)

            writer = csv.DictWriter(
                file,
                fieldnames=ADJUSTED_CSV_COLUMNS
            )

            writer.writeheader()
            writer.writerows(sorted_rows)

        os.replace(temporary_path, output_file)

    finally:

        if temporary_path and temporary_path.exists():
            temporary_path.unlink()

    return output_file


    