import csv
import gzip
import os
import re
import tempfile

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_CONTRACT_DIR = (
    PROJECT_ROOT / "data" / "contract_metadata" / "raw"
)

NORMALIZED_CONTRACT_DIR = (
    PROJECT_ROOT / "data" / "contract_metadata" / "normalized"
)

DEFAULT_OUTPUT_PATH = (
    NORMALIZED_CONTRACT_DIR / "nse_stock_options.csv"
)

NSE_EPOCH = datetime(1980, 1, 1, tzinfo=timezone.utc)

REQUIRED_FIELDS = {
    "FinInstrmId",
    "UndrlygFinInstrmId",
    "FinInstrmNm",
    "TckrSymb",
    "XpryDt",
    "StrkPric",
    "OptnTp",
    "PrtdToTrad",
    "MinLot",
    "NewBrdLotQty",
    "BidIntrvl",
    "DelFlg",
    "TradgStsNrmlMkt",
    "ElgbltyNrmlMkt",
}

OUTPUT_FIELDS = [
    "contract_id",
    "underlying_instrument_id",
    "instrument_type",
    "symbol",
    "expiry_date",
    "strike_price",
    "option_type",
    "exchange_option_type",
    "min_lot_quantity",
    "board_lot_quantity",
    "tick_size",
    "permitted_to_trade",
    "is_deleted",
    "normal_market_status",
    "normal_market_eligible",
    "exercise_style",
    "corporate_adjusted",
    "source_file_date",
    "imported_at_utc",
]


def _parse_positive_integer(value, field_name):
    """Parse a strictly positive integer from an NSE field."""

    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(
            f"Invalid integer value for {field_name}: {value!r}"
        )

    if parsed <= 0:
        raise ValueError(
            f"{field_name} must be positive. Received {parsed}."
        )

    return parsed


def _parse_nonnegative_integer(value, field_name):
    """Parse a nonnegative integer from an NSE field."""

    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(
            f"Invalid integer value for {field_name}: {value!r}"
        )

    if parsed < 0:
        raise ValueError(
            f"{field_name} cannot be negative."
        )

    return parsed


def _parse_paise_price(value, field_name):
    """
    Convert an NSE F&O price field from paise to rupees.

    Example:
        140000 paise -> ₹1400.00
    """

    try:
        paise = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(
            f"Invalid price value for {field_name}: {value!r}"
        )

    if not paise.is_finite() or paise <= 0:
        raise ValueError(
            f"{field_name} must be a positive finite price."
        )

    rupees = paise / Decimal("100")

    return format(rupees.quantize(Decimal("0.01")), "f")


def _parse_nse_date(value, field_name, required=False):
    """
    Convert NSE timestamp seconds since 01-Jan-1980 UTC
    into an ISO calendar date.

    A zero timestamp means the optional date is unavailable.
    """

    raw = str(value).strip()

    if raw in ("", "0"):
        if required:
            raise ValueError(
                f"{field_name} is required."
            )
        return ""

    seconds = _parse_nonnegative_integer(
        raw,
        field_name
    )

    try:
        timestamp = NSE_EPOCH + timedelta(seconds=seconds)
    except OverflowError:
        raise ValueError(
            f"{field_name} contains an invalid timestamp."
        )

    return timestamp.date().isoformat()


def _parse_binary_flag(value, field_name):
    """Convert an NSE 0/1 flag into a Boolean value."""

    raw = str(value).strip()

    if raw == "1":
        return True

    if raw == "0":
        return False

    raise ValueError(
        f"{field_name} must be '0' or '1'. Received {raw!r}."
    )


def _parse_delete_flag(value):
    """Convert NSE N/Y delete flag into a Boolean."""

    raw = str(value).strip().upper()

    if raw == "N":
        return False

    if raw == "Y":
        return True

    raise ValueError(
        f"DelFlg must be N or Y. Received {raw!r}."
    )


def _parse_optional_flag(value, field_name):
    """Parse an optional Y/N flag."""

    raw = str(value or "").strip().upper()

    if raw == "":
        return ""

    if raw not in ("Y", "N"):
        raise ValueError(
            f"{field_name} must be Y or N when supplied."
        )

    return raw


def parse_source_file_date(file_path):
    """
    Extract DDMMYYYY from:

        NSE_FO_contract_DDMMYYYY.csv.gz
    """

    filename = Path(file_path).name

    match = re.fullmatch(
        r"NSE_FO_contract_(\d{8})\.csv\.gz",
        filename,
        flags=re.IGNORECASE
    )

    if not match:
        raise ValueError(
            "Expected filename format: "
            "NSE_FO_contract_DDMMYYYY.csv.gz"
        )

    try:
        parsed = datetime.strptime(
            match.group(1),
            "%d%m%Y"
        ).date()
    except ValueError:
        raise ValueError(
            "The date in the NSE contract filename is invalid."
        )

    return parsed.isoformat()


def normalize_contract_rows(raw_rows, source_file_date):
    """
    Filter OPTSTK rows and normalize NSE contract fields.

    Index options and futures are excluded.

    All original contract rows are retained, including
    contracts which are listed but not permitted to trade.
    Their flags are preserved explicitly.
    """

    imported_at = datetime.now(
        timezone.utc
    ).isoformat()

    normalized = []
    seen_contract_ids = set()

    for row_number, row in enumerate(raw_rows, start=2):

        if row.get("FinInstrmNm", "").strip() != "OPTSTK":
            continue

        try:
            contract_id = str(
                row["FinInstrmId"]
            ).strip()

            if not contract_id:
                raise ValueError("FinInstrmId is empty.")

            if contract_id in seen_contract_ids:
                raise ValueError(
                    f"Duplicate FinInstrmId: {contract_id}"
                )

            symbol = str(
                row["TckrSymb"]
            ).strip().upper()

            if not symbol:
                raise ValueError("TckrSymb is empty.")

            exchange_option_type = str(
                row["OptnTp"]
            ).strip().upper()

            if exchange_option_type == "CE":
                option_type = "call"

            elif exchange_option_type == "PE":
                option_type = "put"

            else:
                raise ValueError(
                    "OPTSTK option type must be CE or PE."
                )

            expiry_date = _parse_nse_date(
                row["XpryDt"],
                "XpryDt",
                required=True
            )

            strike_price = _parse_paise_price(
                row["StrkPric"],
                "StrkPric"
            )

            min_lot = _parse_positive_integer(
                row["MinLot"],
                "MinLot"
            )

            board_lot = _parse_positive_integer(
                row["NewBrdLotQty"],
                "NewBrdLotQty"
            )

            bid_interval_paise = _parse_positive_integer(
                row["BidIntrvl"],
                "BidIntrvl"
            )

            # The MII field sequence maps BidIntrvl to
            # the contract's tick-size / minimum price step.
            tick_size = format(
                (
                    Decimal(bid_interval_paise)
                    / Decimal("100")
                ).quantize(Decimal("0.01")),
                "f"
            )

            permitted_to_trade = _parse_binary_flag(
                row["PrtdToTrad"],
                "PrtdToTrad"
            )

            is_deleted = _parse_delete_flag(
                row["DelFlg"]
            )

            market_eligible = _parse_binary_flag(
                row["ElgbltyNrmlMkt"],
                "ElgbltyNrmlMkt"
            )

            market_status = str(
                row["TradgStsNrmlMkt"]
            ).strip()

            if not market_status:
                raise ValueError(
                    "TradgStsNrmlMkt is empty."
                )

            record = {
                "contract_id": contract_id,

                "underlying_instrument_id": str(
                    row["UndrlygFinInstrmId"]
                ).strip(),

                "instrument_type": "OPTSTK",

                "symbol": symbol,

                "expiry_date": expiry_date,

                "strike_price": strike_price,

                "option_type": option_type,

                "exchange_option_type":
                    exchange_option_type,

                "min_lot_quantity": min_lot,

                "board_lot_quantity": board_lot,

                "tick_size": tick_size,

                "permitted_to_trade":
                    permitted_to_trade,

                "is_deleted": is_deleted,

                "normal_market_status": market_status,

                "normal_market_eligible":
                    market_eligible,

                "exercise_style": str(
                    row.get("OptnExrcStyle", "")
                ).strip().upper(),

                "corporate_adjusted": _parse_optional_flag(
                    row.get("CorpAdjstmnt", ""),
                    "CorpAdjstmnt"
                ),

                "source_file_date": source_file_date,

                "imported_at_utc": imported_at,
            }

            normalized.append(record)
            seen_contract_ids.add(contract_id)

        except (KeyError, ValueError) as exc:
            raise ValueError(
                f"Invalid NSE contract row {row_number}: {exc}"
            ) from exc

    if not normalized:
        raise ValueError(
            "No valid OPTSTK records were found in the NSE file."
        )

    return normalized


def find_latest_contract_file(raw_dir=None):
    """Find the latest NSE contract file by its filename date."""

    search_dir = (
        Path(raw_dir)
        if raw_dir is not None
        else RAW_CONTRACT_DIR
    )

    candidates = list(
        search_dir.glob("NSE_FO_contract_*.csv.gz")
    )

    if not candidates:
        raise FileNotFoundError(
            f"No NSE contract files found in {search_dir}"
        )

    dated_files = []

    for candidate in candidates:
        source_date = parse_source_file_date(candidate)
        dated_files.append((source_date, candidate))

    return max(
        dated_files,
        key=lambda item: item[0]
    )[1]


def import_nse_contract_file(
    file_path=None,
    output_path=None
):
    """
    Import an NSE compressed MII contract file and
    atomically write normalized stock-option metadata.
    """

    source_path = (
        Path(file_path)
        if file_path is not None
        else find_latest_contract_file()
    )

    if not source_path.is_file():
        raise FileNotFoundError(
            f"NSE contract file not found: {source_path}"
        )

    source_date = parse_source_file_date(source_path)

    with gzip.open(
        source_path,
        mode="rt",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError(
                "The NSE contract file has no CSV header."
            )

        missing_fields = (
            REQUIRED_FIELDS - set(reader.fieldnames)
        )

        if missing_fields:
            raise ValueError(
                "NSE contract file is missing required fields: "
                + ", ".join(sorted(missing_fields))
            )

        normalized = normalize_contract_rows(
            reader,
            source_date
        )

    destination = (
        Path(output_path)
        if output_path is not None
        else DEFAULT_OUTPUT_PATH
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=destination.parent,
            suffix=".tmp",
            delete=False
        ) as temp_file:

            temp_path = Path(temp_file.name)

            writer = csv.DictWriter(
                temp_file,
                fieldnames=OUTPUT_FIELDS
            )

            writer.writeheader()
            writer.writerows(normalized)

        os.replace(
            temp_path,
            destination
        )

    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise

    symbols = sorted({
        row["symbol"]
        for row in normalized
    })

    return {
        "source_file": str(source_path),

        "source_file_date": source_date,

        "total_stock_option_contracts":
            len(normalized),

        "unique_symbols": len(symbols),

        "symbols": symbols,

        "output_file": str(destination),
    }

    