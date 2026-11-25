# OptionLab — Interview Preparation Guide

## 1. 30-second project pitch

OptionLab is a local NSE stock-options pricing and quantitative-analysis platform. I built the pricing engine in C++17 using risk-neutral Geometric Brownian Motion and Monte Carlo simulation, then integrated it with a Python Flask backend and a browser dashboard. It uses TejHQ historical underlying data, validates stock-option contracts against an imported NSE contract master, and benchmarks the Monte Carlo price against the Black–Scholes–Merton analytical model. It also provides Greeks, sensitivity analysis, expiry P&L and selected multi-leg strategies. It is a theoretical research tool, not a trading or execution platform.

## 2. Two-minute explanation

The application starts with two local inputs: underlying market data and the NSE stock-option contract master. Raw OHLCV data supplies the latest spot close; corporate-action-adjusted closing prices are used to estimate historical volatility from daily log returns. Before pricing, OptionLab checks cache integrity and latest-date alignment, then validates the selected symbol, expiry, strike and option type against the imported stock-option contract master.

The Flask workflow constructs the model parameters and passes them through a Python bridge to a separate C++17 executable. The engine simulates terminal underlying prices under risk-neutral GBM, calculates discounted European Call or Put payoffs, and estimates the option value. It uses Welford's online algorithm to estimate sample variance without storing every payoff. The result contains the estimate, standard error and an approximate 95% confidence interval.

Python independently calculates the Black–Scholes–Merton analytical benchmark and compares it with the Monte Carlo estimate. Where the assumptions permit, it also calculates analytical and numerical Greeks and one-factor sensitivities. The browser receives JSON and renders metrics, tables and charts with Chart.js. Stage 17 adds terminal-price distribution, single-option expiry payoff and theoretical analysis for Long Call, Long Put, Bull Call Spread and Bear Put Spread.

## 3. Architecture explanation

- **C++ engine:** numerical simulation loop and statistical estimator.
- **Python bridge:** validates inputs, starts the executable safely, applies a timeout, parses JSON and validates returned fields.
- **Flask:** API validation, market-data checks, contract validation and orchestration.
- **Market-data layer:** TejHQ client, CSV cache, raw/adjusted integrity checks and historical-volatility calculation.
- **Contract layer:** NSE master normalization and exact listed-contract lookup.
- **Analytics:** BSM benchmark, Greeks, sensitivity, payoff and strategies.
- **Frontend:** form handling, asynchronous API requests, tables and Chart.js visualizations.

## 4. Technical questions and answer outlines

### Why use Monte Carlo when a BSM formula exists?

BSM provides a fast analytical benchmark for European options under its assumptions. Monte Carlo provides a simulation-based estimator and a framework that can later be extended to payoffs for which a simple closed-form solution is unavailable. In this project, the BSM result is used to validate the Monte Carlo implementation; Monte Carlo is not claimed to be more accurate than BSM for a standard European vanilla option under identical assumptions.

### Why is the drift `r - q` under risk-neutral pricing?

Under the risk-neutral measure, the expected total return of the underlying, adjusted for continuous dividend yield, is the risk-free rate. Therefore the risk-neutral GBM process has drift `r - q`; the `-0.5 sigma^2` term appears in the exponent solution for the lognormal process.

### Why use adjusted closing prices for historical volatility?

Corporate actions such as splits and dividends can create discontinuities in raw historical prices. Adjusted close provides a more consistent historical price series for estimating returns. The raw close remains the selected spot input in this project, while adjusted close is used for volatility estimation.

### Is manual volatility implied volatility?

No. It is a user-supplied annualized volatility assumption. Implied volatility would require an observed option-market price and an inversion of an option-pricing model; OptionLab does not ingest live option-chain premiums or perform that inversion.

### What does the standard error mean?

It measures Monte Carlo sampling uncertainty in the estimated mean discounted payoff. It decreases approximately with the inverse square root of the number of independent simulations. It does not measure model error, stale-data error or the difference between a theoretical value and a traded quote.

### Why use Welford's algorithm?

Welford's online method updates the running mean and sum of squared deviations for each sample. It avoids storing every discounted payoff and is numerically more stable than computing variance from the difference between two large sums.

### What does the 95% confidence interval mean?

OptionLab uses an approximate normal interval around the Monte Carlo estimator: estimate plus or minus 1.96 standard errors. It describes sampling uncertainty under the simulation assumptions. It is not a guaranteed range for the option's market price.

### What is the difference between Vega and Theta conventions here?

The service exposes Vega per 1.00 volatility change and per one-percentage-point change. Theta is exposed per year and per calendar day. Interview answers should state which scaling is being quoted.

### Why does OptionLab use both raw and adjusted data?

Raw close is the chosen spot-price input, while adjusted close is used to calculate historical volatility. Both datasets are validated, and their latest dates must match before the pricing workflow uses them. Their full historical lengths need not be identical.

### How are NSE contract strikes and expiries normalized?

The importer filters `OPTSTK` rows, maps `CE` and `PE` to Call and Put, converts the strike from paise to rupees, and converts the exchange's timestamp from the NSE epoch (1 January 1980 UTC) to an ISO date. It preserves board-lot, min-lot, tick and trading/deletion flags.

### Why validate lot sizes for spreads?

One lot of one contract need not represent the same number of shares as one lot of another contract. A vertical spread's legs must represent matched underlying quantities; otherwise its displayed payoff would be an unbalanced position rather than the intended spread.

### What are the main limitations?

European exercise only; GBM with constant volatility; no live option-chain quotes or implied volatility; no order execution; and no brokerage, taxes, slippage, liquidity or margin model. Strategy premiums are theoretical BSM values, not executable market prices.

## 5. Honest project ownership statement

Be prepared to walk through one complete request in the code: browser payload -> Flask validation -> market-data status -> contract lookup -> maturity and volatility -> C++ bridge -> Monte Carlo JSON -> BSM comparison -> frontend charts. Explain the formulas and limitations in your own words. Do not claim live option pricing, implied volatility, production deployment or trading execution because those are outside the implementation scope.
