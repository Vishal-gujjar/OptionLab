# OptionLab

## NSE stock-option pricing and quantitative analysis platform

OptionLab is a local, personal-use application for theoretical pricing and analysis of European-style NSE stock options. It combines a C++17 Monte Carlo pricing engine with a Python/Flask backend and a browser dashboard built with HTML, CSS, Bootstrap, JavaScript and Chart.js.

The application uses historical underlying-stock data for its spot-price and volatility inputs, validates selected option contracts against an imported NSE stock-option contract master, and compares Monte Carlo estimates with a Black–Scholes–Merton (BSM) analytical benchmark.

> **Scope:** OptionLab is a model-based research and learning tool. It is not a trading system, investment recommendation, execution platform or source of live option quotes.

---

## Contents

- [Capabilities](#capabilities)
- [Architecture](#architecture)
- [Technology stack](#technology-stack)
- [Model and conventions](#model-and-conventions)
- [Requirements](#requirements)
- [Setup on Windows with MinGW](#setup-on-windows-with-mingw)
- [Market-data setup](#market-data-setup)
- [Import the NSE stock-option contract master](#import-the-nse-stock-option-contract-master)
- [Run the dashboard](#run-the-dashboard)
- [Command-line pricing](#command-line-pricing)
- [API overview](#api-overview)
- [Tests](#tests)
- [Limitations](#limitations)
- [Security and data handling](#security-and-data-handling)
- [Documentation](#documentation)
- [License](#license)

## Capabilities

### Pricing and model validation

- European Call and Put pricing using risk-neutral Monte Carlo simulation.
- C++17 engine using `std::mt19937_64` and a standard-normal distribution.
- Reproducible runs using a configurable random seed.
- Online sample variance using Welford's algorithm.
- Standard error and approximate 95% confidence interval.
- Black–Scholes–Merton analytical benchmark and Monte Carlo comparison.
- Absolute/relative error and confidence-interval coverage checks.
- Simulation convergence analysis.

### Underlying market data

- Raw OHLCV and corporate-action-adjusted historical price retrieval through TejHQ.
- Local CSV cache and incremental refresh with overlap.
- Spot price from the latest valid raw close.
- Historical volatility from adjusted closing prices.
- Cache validation, latest-date matching, finite-value checks and freshness status.

### NSE contract handling

- Import of NSE F&O contract-master snapshots.
- Stock-option (`OPTSTK`) filtering.
- Listed symbol, expiry, strike and Call/Put validation.
- Contract ID, tick size, trading permission, deletion state and lot-size metadata.
- Per-lot theoretical premium and statistical values.

### Risk and expiry analytics

- Analytical BSM Delta, Gamma, Vega, Theta and Rho.
- Numerical finite-difference Greek comparison where the standard formulas are defined.
- Spot, volatility and time-to-expiry sensitivity scenarios.
- Risk-neutral terminal-stock-price distribution for scenario analysis.
- Single-option expiry payoff, long/short P&L, break-even and maximum gain/loss.
- Long Call, Long Put, Bull Call Spread and Bear Put Spread analysis.

## Architecture

```text
Browser dashboard
  HTML / CSS / Bootstrap / JavaScript / Chart.js
                 |
                 v
        Flask application
    validation, routing, JSON APIs
          /             \
         v               v
Market-data services   NSE contract services
TejHQ -> CSV cache     contract master -> lookup
         \               /
          \             /
           v           v
             Pricing workflow
      spot + volatility + maturity
                 |
        +--------+---------+
        |                  |
        v                  v
  C++ Monte Carlo      Python analytics
  subprocess/JSON      BSM, Greeks, validation,
                       sensitivity and payoffs
        |                  |
        +--------+---------+
                 v
        JSON response to dashboard
                 |
                 v
        Chart.js results and tables
```

The detailed module map, data flow and endpoint inventory are in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Mathematical derivations and implementation notes are in the [technical documentation PDF](docs/OptionLab_Technical_Documentation.pdf).

## Technology stack

| Layer | Technology |
| --- | --- |
| Pricing engine | C++17 |
| Build | CMake |
| Backend | Python 3.13, Flask |
| Python environment | `venv`, `requirements.txt` |
| Market data | TejHQ API |
| Contract metadata | NSE F&O contract master |
| Frontend | HTML, CSS, Bootstrap, vanilla JavaScript |
| Charts | Chart.js 4.6.2 |
| Automated tests | Python `unittest`, CTest |

## Model and conventions

### Risk-neutral stock-price model

The terminal stock price follows risk-neutral Geometric Brownian Motion:

\[
S_T = S_0\exp\left[(r-q-\tfrac12\sigma^2)T+\sigma\sqrt{T}Z\right],\quad Z\sim N(0,1).
\]

The Monte Carlo estimate is the average discounted terminal payoff. The BSM analytical value acts as an independent benchmark under the same assumptions.

### Volatility modes

- **Historical:** annualized sample standard deviation of daily log returns from adjusted closes, using 252 trading days.
- **Manual:** user-supplied annualized volatility assumption. It is **not** inferred implied volatility and is not derived from option-chain premiums.

### Time to expiry

When an NSE expiry is selected, time to maturity uses ACT/365 Fixed: calendar days from the latest underlying spot-data date to the selected contract expiry, divided by 365.

### Statistical interval

The reported interval is the normal-approximation interval `estimate +/- 1.96 * standard_error`. It is an estimate of Monte Carlo sampling uncertainty, not a guarantee of market-price accuracy.

## Requirements

- Python 3.13 (the tested development environment).
- C++17 compiler (the reported Windows build uses MinGW/GCC 15.2.0).
- CMake 3.16 or newer.
- Git.
- TejHQ API credentials for retrieving market data.
- An NSE F&O contract-master snapshot for NSE stock-option selection.

## Setup on Windows with MinGW

Open PowerShell in the project directory.

### 1. Clone the repository

```powershell
git clone https://github.com/Vishal-gujjar/OptionLab.git
cd OptionLab
```

Replace the placeholder with your own repository URL after creating the remote repository.

### 2. Create and activate a virtual environment

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use the Python executable directly as `\.venv\Scripts\python.exe` or adjust the PowerShell execution policy for your user according to your machine's policy.

### 3. Install Python dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip check
```

The repository dependency pins are:

```text
Flask==3.1.3
python-dotenv==1.2.4
```

### 4. Configure TejHQ credentials

```powershell
Copy-Item .env.example .env
```

Edit `.env` locally:

```text
TEJHQ_API_KEY=your_actual_tejhq_api_key
```

Never commit `.env`, paste its contents into an issue, or include it in a shared ZIP.

### 5. Build the C++ engine

```powershell
cmake -S . -B build -G "MinGW Makefiles"
cmake --build build
```

The Python bridge expects the Windows executable at:

```text
build/optionlab_engine.exe
```

Run C++ tests:

```powershell
ctest --test-dir build --output-on-failure
```

## Market-data setup

Download raw OHLCV data (the script accepts `--years 1` or `--years 2`; it also supports an explicit start/end date pair):

```powershell
python scripts/download_stock_data.py --symbol RELIANCE --exchange nse --years 1
```

Download adjusted historical prices:

```powershell
python scripts/download_adjusted_data.py --symbol RELIANCE --exchange nse --years 1
```

The local cache paths follow this pattern:

```text
data/cache/nse_RELIANCE.csv
 data/cache/nse_RELIANCE_adjusted.csv
```

Raw close is the spot-price input. Adjusted close is used for historical-volatility estimation. The application checks that the latest dates match before pricing. Historical row counts and start dates do not have to be identical.

Refreshes use an overlapping date window to reduce the chance of missing recent corrections. Data is cached locally; the cache is excluded from Git.

## Import the NSE stock-option contract master

Place an appropriate NSE F&O contract-master snapshot in the local raw metadata directory, then run:

```powershell
python scripts/import_nse_contracts.py --file "data/contract_metadata/raw/NSE_FO_contract_DDMMYYYY.csv.gz"
```

The importer filters `OPTSTK` records and creates normalized metadata. Key transformations include:

- `CE` -> Call; `PE` -> Put.
- NSE price fields stored in paise -> rupees by dividing by 100.
- NSE date timestamps interpreted relative to 1 January 1980 UTC.
- `NewBrdLotQty` retained as board-lot quantity; `MinLot` is also preserved.
- Trading permission and deletion/market-eligibility flags retained.

The contract master is a dated snapshot. Refresh it when a newer suitable file is available. Contract metadata is not a live option quote feed.

## Run the dashboard

```powershell
python run.py
```

Open:

```text
http://127.0.0.1:5000/
```

The supplied `run.py` binds to `127.0.0.1` on port `5000` with Flask debug mode enabled. This is a local development configuration, not a production deployment configuration.

## Command-line pricing

The command-line script accepts a manual year fraction for maturity:

```powershell
python scripts/price_option.py `
  --symbol RELIANCE `
  --exchange nse `
  --strike 1400 `
  --rate 0.06 `
  --dividend 0.00 `
  --maturity 0.25 `
  --type call `
  --simulations 100000 `
  --seed 42
```

Rates, dividend yield and volatility are decimal fractions: `0.06` means 6%. The command-line example uses the default historical-volatility mode in the workflow. The browser UI additionally supports selecting a listed expiry and choosing historical or manual volatility.

## API overview

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/` | Dashboard |
| GET | `/health` | Health check |
| GET | `/api/contracts/symbols` | Available stock-option symbols |
| GET | `/api/contracts/expiries` | Available expiries for a symbol |
| GET | `/api/contracts/strikes` | Listed strikes for symbol/expiry/type |
| POST | `/api/contracts/validate` | Validate an exact option contract |
| GET | `/api/market-data/status` | Inspect cache validity and freshness |
| POST | `/api/market-data/refresh` | Refresh underlying market data |
| POST | `/api/price` | Run the main pricing workflow |
| POST | `/api/analytics/distribution` | Risk-neutral terminal-price distribution |
| POST | `/api/analytics/payoff` | Single-option expiry payoff and P&L |
| POST | `/api/strategies/analyze` | Single-leg or vertical-spread analysis |

API request/response responsibilities and validation notes are documented in `docs/ARCHITECTURE.md`.

## Tests

Run the full Python test suite:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

Build and run C++ tests:

```powershell
cmake --build build
ctest --test-dir build --output-on-failure
```

The project includes tests for C++ Monte Carlo pricing, BSM, pricing bridge, historical volatility, CSV storage, market-data validation/refresh, NSE contract parsing/lookup, lot calculations, Greeks, sensitivity, payoff, strategy analysis and Flask APIs.

**Latest verification supplied by the project owner (25 November 2026):** 181 Python tests passed in a fresh Python 3.13 virtual environment; `pip check` reported no broken requirements; the C++ engine rebuilt from a clean CMake build directory and the registered CTest target passed. These are owner-supplied test results, not a claim that this repository was independently executed as part of document generation.

## Limitations

- The pricing product is limited to European-style Call and Put options.
- The core underlying model is risk-neutral GBM with constant volatility, continuously compounded risk-free rate and dividend yield.
- Historical volatility is a realized-volatility estimate; it is not implied volatility.
- There is no live option-chain premium ingestion, implied-volatility inversion, order placement or trade execution.
- Strategy-leg premiums are theoretical BSM premiums, not observed bid/ask prices.
- Brokerage, exchange charges, taxes, slippage, liquidity, margin, funding and early-exercise effects are not included in the strategy payoff model.
- Terminal-price distributions are risk-neutral model scenarios, not real-world price forecasts.
- Data freshness is a calendar-day heuristic, not a full NSE trading-calendar service.
- The application depends on the availability, correctness and permitted use of the TejHQ data and imported NSE contract snapshot.

## Security and data handling

- Keep API credentials in `.env`; `.env` is ignored by Git.
- `.env.example` contains only a placeholder and may be committed.
- Local `data/cache/`, raw/normalized contract metadata, `build/`, virtual environments, generated executables and Python caches are ignored.
- Respect TejHQ and NSE data terms. Do not redistribute provider data unless the applicable terms permit it.
- Before the first commit, review `git status --short` and `git diff --cached --name-only` to verify that no credential or local dataset is staged.

## Documentation

- `docs/OptionLab_Technical_Documentation.pdf` — mathematical theory, system design, data pipeline, implementation, testing and limitations.
- `docs/ARCHITECTURE.md` — module map, end-to-end workflows and API inventory.
- `docs/INTERVIEW_GUIDE.md` — project pitch and technical interview preparation.
- `docs/RELEASE_CHECKLIST.md` — pre-commit and release checklist.

## License

OptionLab source code and associated documentation are
licensed under the MIT License.

See the [LICENSE](LICENSE) file for complete terms.

Market data obtained from TejHQ and NSE/BSE is not covered
by the software licence. Applicable provider and exchange
data-use and redistribution restrictions continue to apply.
See [DATA_NOTICE.md](DATA_NOTICE.md).
