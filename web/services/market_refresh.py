import csv

from datetime import date, timedelta
from pathlib import Path

from web.services.tejhq_client import (
    fetch_ohlcv,
    fetch_adjusted
)

from web.services.csv_store import (
    save_ohlcv_csv,
    save_adjusted_csv
)

from web.services.market_data_status import (
    get_market_data_status
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _latest_date(path):
    if not path.is_file():
        return None

    with path.open(
        "r",
        encoding="utf-8",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        if not reader.fieldnames or "date" not in reader.fieldnames:
            raise ValueError(
                f"Invalid cache schema: {path}"
            )

        dates = [
            date.fromisoformat(row["date"])
            for row in reader
        ]

    return max(dates) if dates else None


def _restore_file(path, backup):
    """
    Restore the original cache contents after a failed
    two-file refresh operation.
    """

    if backup is None:
        path.unlink(missing_ok=True)
        return

    temporary = path.with_suffix(path.suffix + ".rollback")

    try:
        temporary.write_bytes(backup)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def refresh_market_data(
    symbol,
    exchange="nse",
    lookback_days=365,
    overlap_days=5,
    end_date=None,
    cache_dir=None
):
    """
    Refresh raw OHLCV and adjusted market data.

    Existing records are preserved by csv_store.
    Both network requests complete before any cache update.
    If a cache write fails, previous files are restored.

    When caches exist, request from the earlier of their
    latest dates minus an overlap window. This helps fill
    missing dates and capture revised observations.
    """

    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("A stock symbol is required.")

    symbol = symbol.strip().upper()
    exchange = str(exchange).strip().lower()

    if exchange != "nse":
        raise ValueError(
            "Only NSE market-data refresh is supported."
        )

    if (
        isinstance(lookback_days, bool)
        or not isinstance(lookback_days, int)
        or not 1 <= lookback_days <= 3650
    ):
        raise ValueError(
            "lookback_days must be between 1 and 3650."
        )

    if (
        isinstance(overlap_days, bool)
        or not isinstance(overlap_days, int)
        or not 0 <= overlap_days <= 30
    ):
        raise ValueError(
            "overlap_days must be between 0 and 30."
        )

    end = (
        date.fromisoformat(end_date)
        if isinstance(end_date, str)
        else end_date
        if isinstance(end_date, date)
        else date.today()
    )

    data_dir = Path(
        cache_dir or PROJECT_ROOT / "data" / "cache"
    )

    raw_path = data_dir / f"nse_{symbol}.csv"
    adjusted_path = data_dir / f"nse_{symbol}_adjusted.csv"

    raw_latest = _latest_date(raw_path)
    adjusted_latest = _latest_date(adjusted_path)

    existing_dates = [
        value for value in (raw_latest, adjusted_latest)
        if value is not None
    ]

    if len(existing_dates) == 2:
        anchor = min(existing_dates)
        start = anchor - timedelta(days=overlap_days)
    else:
        start = end - timedelta(days=lookback_days)

    if start > end:
        raise ValueError(
            "Refresh start date is later than end date."
        )

    start_text = start.isoformat()
    end_text = end.isoformat()

    # Fetch both datasets before modifying local files.
    raw_payload = fetch_ohlcv(
        symbol=symbol,
        start_date=start_text,
        end_date=end_text,
        exchange=exchange
    )

    adjusted_payload = fetch_adjusted(
        symbol=symbol,
        start_date=start_text,
        end_date=end_text,
        exchange=exchange
    )

    raw_rows = raw_payload.get("data")
    adjusted_rows = adjusted_payload.get("data")

    if not isinstance(raw_rows, list):
        raise RuntimeError(
            "TejHQ returned an invalid raw-data response."
        )

    if not isinstance(adjusted_rows, list):
        raise RuntimeError(
            "TejHQ returned an invalid adjusted-data response."
        )

    # If a cache does not yet exist, an empty response
    # cannot produce a usable market-data dataset.
    if not raw_rows and not raw_path.is_file():
        raise RuntimeError(
            "No raw data was returned and no raw cache exists."
        )

    if not adjusted_rows and not adjusted_path.is_file():
        raise RuntimeError(
            "No adjusted data was returned and no adjusted cache exists."
        )

    data_dir.mkdir(parents=True, exist_ok=True)

    # Back up both cache files to provide rollback if
    # either save operation fails.
    raw_backup = (
        raw_path.read_bytes()
        if raw_path.is_file() else None
    )

    adjusted_backup = (
        adjusted_path.read_bytes()
        if adjusted_path.is_file() else None
    )

    try:
        raw_output = raw_path
        adjusted_output = adjusted_path

        if raw_rows:
            raw_output = save_ohlcv_csv(
                symbol=symbol,
                exchange=exchange,
                rows=raw_rows,
                cache_dir=data_dir
            )

        if adjusted_rows:
            adjusted_output = save_adjusted_csv(
                symbol=symbol,
                exchange=exchange,
                rows=adjusted_rows,
                cache_dir=data_dir
            )

    except Exception:
        _restore_file(raw_path, raw_backup)
        _restore_file(adjusted_path, adjusted_backup)
        raise

    status = get_market_data_status(
        symbol=symbol,
        exchange=exchange,
        cache_dir=data_dir,
        as_of_date=end
    )

    return {
        "symbol": symbol,
        "exchange": exchange.upper(),

        "requested_start_date": start_text,
        "requested_end_date": end_text,

        "raw_rows_received": len(raw_rows),
        "adjusted_rows_received": len(adjusted_rows),

        "raw_updated": bool(raw_rows),
        "adjusted_updated": bool(adjusted_rows),

        "raw_file": str(raw_output),
        "adjusted_file": str(adjusted_output),

        "market_data_status": status
    }