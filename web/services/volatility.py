import csv
import math

from pathlib import Path
from statistics import mean, stdev


def calculate_historical_volatility(
    csv_path: Path,
    annualization_days: int = 252
) -> dict:

    """
    Calculate historical volatility using adjusted closes.

    Returns annualized and daily volatility as decimals.
    """

    if (
        isinstance(annualization_days, bool)
        or not isinstance(annualization_days, int)
        or annualization_days <= 0
    ):
        raise ValueError("Invalid annualization factor.")

    csv_path = Path(csv_path)

    if not csv_path.is_file():
        raise FileNotFoundError(csv_path)

    prices = []
    dates = []

    with csv_path.open(
        "r",
        newline="",
        encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)

        if not reader.fieldnames or "adj_close" not in reader.fieldnames:
            raise ValueError(
                "CSV must contain adj_close."
            )

        for row in reader:

            price = float(row["adj_close"])

            if not math.isfinite(price) or price <= 0:
                raise ValueError("Invalid adjusted closing price.")

            dates.append(row["date"])
            prices.append(price)

    if len(prices) < 3:
        raise ValueError(
            "At least three closing prices are required."
        )

    if dates != sorted(dates):
        raise ValueError(
            "Price observations must be chronological."
        )

    if len(set(dates)) != len(dates):
        raise ValueError("Duplicate price dates found.")

    # Calculate daily logarithmic returns.
    log_returns = []

    for i in range(1, len(prices)):

        daily_return = math.log(
            prices[i] / prices[i - 1]
        )

        log_returns.append(daily_return)

    # Sample standard deviation of daily returns.
    daily_volatility = stdev(log_returns)

    # Annualize volatility.
    annualized_volatility = (
        daily_volatility *
        math.sqrt(annualization_days)
    )

    average_daily_return = mean(log_returns)

    return {
        "observations": len(prices),
        "return_observations": len(log_returns),
        "first_date": dates[0],
        "last_date": dates[-1],
        "daily_volatility": daily_volatility,
        "annualized_volatility": annualized_volatility,
        "annualized_volatility_percent": (
            annualized_volatility * 100
        ),
        "average_daily_log_return": average_daily_return,
        "annualization_days": annualization_days,
    }





