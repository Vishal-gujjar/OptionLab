import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


from web.services.contract_metadata import (
    import_nse_contract_file
)


def main():
    parser = argparse.ArgumentParser(
        description="Import NSE stock-option contract metadata."
    )

    parser.add_argument(
        "--file",
        help="Path to an NSE_FO_contract_DDMMYYYY.csv.gz file."
    )

    parser.add_argument(
        "--output",
        help="Optional output CSV path."
    )

    args = parser.parse_args()

    result = import_nse_contract_file(
        file_path=args.file,
        output_path=args.output
    )

    print("\nOPTIONLAB — NSE CONTRACT IMPORT")
    print("--------------------------------")

    print("Source file:", result["source_file"])

    print("Source file date:", result["source_file_date"])

    print(
        "Stock-option contracts:",
        result["total_stock_option_contracts"]
    )

    print(
        "Unique underlying symbols:",
        result["unique_symbols"]
    )

    print("Output file:", result["output_file"])

    print("\nFIRST 20 UNDERLYING SYMBOLS:")

    for symbol in result["symbols"][:20]:
        print(" -", symbol)

    print("\nNSE contract import completed successfully.")


if __name__ == "__main__":
    main()