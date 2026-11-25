
const form = document.getElementById("pricing-form");

const symbolInput = document.getElementById("symbol");
const expiryInput = document.getElementById("expiry-date");
const strikeInput = document.getElementById("strike-price");
const optionTypeInput = document.getElementById("option-type");

const refreshMarketDataButton = document.getElementById(
    "refresh-market-data"
);

const marketStatusPanel = document.getElementById(
    "market-status-panel"
);

let latestMarketStatus = null;

const calculateButton = document.getElementById("calculate-button");

const emptyState = document.getElementById("empty-state");
const loadingState = document.getElementById("loading-state");
const resultsPanel = document.getElementById("results-panel");
const errorMessage = document.getElementById("error-message");

const volatilityModeInput = document.getElementById("volatility-mode");
const manualVolatilityContainer = document.getElementById(
    "manual-volatility-container"
);
const manualVolatilityInput = document.getElementById("manual-volatility");



let confidenceChart = null;
let spotSensitivityChart = null;
let volatilitySensitivityChart = null;
let maturitySensitivityChart = null;
let terminalDistributionChart = null;
let singleOptionPayoffChart = null;
let strategyPnlChart = null;

let latestStage17PricingData = null;
// Prevent outdated asynchronous responses from updating the UI.

let pricingRequestSequence = 0;

let stage17AnalyticsSequence = 0;

let strategyAnalysisSequence = 0;

// Currency formatting
function formatCurrency(value) {

    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}


// Number formatting
function formatNumber(value, digits = 4) {

    return Number(value).toFixed(digits);
}


// Error display
function showError(message) {

    errorMessage.textContent = message;
    errorMessage.classList.remove("d-none");
}


function hideError() {

    errorMessage.textContent = "";
    errorMessage.classList.add("d-none");
}


// Loading state
function setLoading(isLoading) {

    calculateButton.disabled = isLoading;

    calculateButton.textContent = isLoading
        ? "Calculating..."
        : "Calculate Option Premium";

    loadingState.classList.toggle("d-none", !isLoading);
}


// Volatility mode selection
function updateVolatilityMode() {

    const isManual = volatilityModeInput.value === "manual";

    manualVolatilityContainer.classList.toggle(
        "d-none",
        !isManual
    );

    manualVolatilityInput.required = isManual;

    manualVolatilityInput.disabled = !isManual;
}


// Update the confidence interval chart
function updateConfidenceChart(pricing) {

    const canvas = document.getElementById("confidence-chart");

    if (confidenceChart) {
        confidenceChart.destroy();
    }

    confidenceChart = new Chart(canvas, {

        type: "bar",

        data: {
            labels: [
                "Lower 95% CI",
                "Estimated Premium",
                "Upper 95% CI"
            ],

            datasets: [{
                label: "Price per share (₹)",

                data: [
                    pricing.confidence_interval_lower,
                    pricing.estimated_price,
                    pricing.confidence_interval_upper
                ],

                backgroundColor: [
                    "#94a3b8",
                    "#315efb",
                    "#94a3b8"
                ],

                borderRadius: 6,
                maxBarThickness: 65
            }]
        },

        options: {

            responsive: true,
            maintainAspectRatio: false,

            plugins: {

                legend: {
                    display: false
                },

                tooltip: {

                    callbacks: {

                        label: function(context) {
                            return formatCurrency(context.raw);
                        }

                    }

                }

            },

            scales: {

                y: {
                    beginAtZero: true,

                    title: {
                        display: true,
                        text: "Price per share (₹)"
                    }
                },

                x: {
                    grid: {
                        display: false
                    }
                }

            }

        }

    });

}


// Add a model parameter card
function addParameter(label, value) {

    const container = document.getElementById("model-parameters");

    const column = document.createElement("div");
    column.className = "col-6 col-md-4";

    const item = document.createElement("div");
    item.className = "parameter-item";

    const labelElement = document.createElement("div");
    labelElement.className = "parameter-label";
    labelElement.textContent = label;

    const valueElement = document.createElement("div");
    valueElement.className = "parameter-value";
    valueElement.textContent = value;

    item.appendChild(labelElement);
    item.appendChild(valueElement);

    column.appendChild(item);

    container.appendChild(column);

}


// Display API result
function displayResults(data) {

    const market = data.market_data;
    const maturityInfo = data.maturity_info;
    const volatilityInfo = data.volatility_info;
    const assumptions = data.financial_assumptions;
    const parameters = data.option_parameters;
    const pricing = data.pricing_result;


    // Main metrics
    document.getElementById("premium-value").textContent =
        formatCurrency(pricing.estimated_price);

    document.getElementById("spot-value").textContent =
        formatCurrency(market.spot_price);

    document.getElementById("volatility-value").textContent =
        formatNumber(
            volatilityInfo.annualized_volatility_percent,
            2
        ) + "%";

    document.getElementById("standard-error-value").textContent =
        formatNumber(pricing.standard_error, 4);


    // Confidence interval
    document.getElementById("confidence-range").textContent =
        formatCurrency(pricing.confidence_interval_lower) +
        " – " +
        formatCurrency(pricing.confidence_interval_upper);


    // Market information
    document.getElementById("market-symbol").textContent =
        market.symbol + " (" + market.exchange + ")";

    document.getElementById("spot-date").textContent =
        market.spot_date;

    document.getElementById("volatility-period").textContent =
        market.volatility_start_date +
        " to " +
        market.volatility_end_date;

    document.getElementById("observations").textContent =
        market.price_observations;


    // Selected volatility information
    document.getElementById("volatility-source").textContent =
        volatilityInfo.method;

    document.getElementById("selected-volatility").textContent =
        formatNumber(
            volatilityInfo.annualized_volatility_percent,
            2
        ) + "%";


    // Model parameters
    const container = document.getElementById("model-parameters");

    container.replaceChildren();

    addParameter(
        "Option Type",
        parameters.option_type.toUpperCase()
    );

    addParameter(
        "Strike Price",
        formatCurrency(parameters.strike_price)
    );

    addParameter(
        "Expiry Date",
        maturityInfo.expiry_date
    );

    addParameter(
        "Valuation Date",
        maturityInfo.valuation_date
    );

    addParameter(
        "Calendar Days to Expiry",
        maturityInfo.calendar_days_to_expiry
    );

    addParameter(
        "Time to Expiry",
        formatNumber(parameters.time_to_expiry_years, 6) + " years"
    );

    addParameter(
        "Day Count Convention",
        maturityInfo.day_count_convention
    );

    addParameter(
        "Volatility Source",
        volatilityInfo.method
    );

    addParameter(
        "Annualized Volatility",
        formatNumber(
            volatilityInfo.annualized_volatility_percent,
            2
        ) + "%"
    );

    addParameter(
        "Risk-free Rate",
        formatNumber(
            assumptions.risk_free_rate_percent,
            2
        ) + "%"
    );

    addParameter(
        "Dividend Yield",
        formatNumber(
            assumptions.dividend_yield_percent,
            2
        ) + "%"
    );

    addParameter(
        "Simulations",
        Number(parameters.simulations).toLocaleString("en-IN")
    );

    addParameter(
        "Random Seed",
        parameters.seed
    );

    // Update graph
    updateConfidenceChart(pricing);

    // Show results
    emptyState.classList.add("d-none");
    resultsPanel.classList.remove("d-none");

    displayBenchmarkResults(data);

    displayGreeks(data);

    displaySensitivityCharts(data);

    displayContractAndLot(data);

    displayCalculationDataStatus(data);
    
    // Stage 17 analytics
    latestStage17PricingData = data;

    prefillStrategyControls(data);

    loadStage17Analytics(data);

    // Keep the market-data status panel synchronized with
    // the data used for this calculation.
    if (data.market_data_status) {
        setMarketStatusDisplay(data.market_data_status);
    }
}

function displayContractAndLot(data) {
    const contract = data.contract_metadata;
    const lot = data.lot_valuation;

    if (!contract || !lot) {
        console.error(
            "NSE contract or lot valuation is missing."
        );
        return;
    }

    document.getElementById("contract-id").textContent =
        contract.contract_id;

    document.getElementById("contract-symbol").textContent =
        contract.symbol;

    document.getElementById("contract-expiry").textContent =
        contract.expiry_date;

    document.getElementById("contract-strike").textContent =
        formatCurrency(contract.strike_price);

    document.getElementById("contract-type").textContent =
        contract.option_type.toUpperCase();

    document.getElementById("contract-lot-size").textContent =
        Number(contract.board_lot_quantity).toLocaleString("en-IN");

    document.getElementById("contract-tick-size").textContent =
        formatCurrency(contract.tick_size);

    document.getElementById("contract-source-date").textContent =
        contract.source_file_date;

    const permissionElement = document.getElementById(
        "contract-permission"
    );

    permissionElement.textContent =
        contract.permitted_to_trade
            ? "Permitted to trade in the contract master"
            : "Not marked as permitted to trade";

    permissionElement.className =
        contract.permitted_to_trade
            ? "detail-value text-success fw-semibold"
            : "detail-value text-warning fw-semibold";

    const warnings = data.warnings || [];

    document.getElementById(
        "contract-warning"
    ).textContent = warnings.join(" ");

    document.getElementById(
        "mc-premium-lot"
    ).textContent = formatCurrency(
        lot.theoretical_premium_per_lot
    );

    document.getElementById(
        "bs-premium-lot"
    ).textContent = formatCurrency(
        lot.analytical_premium_per_lot
    );

    document.getElementById(
        "standard-error-lot"
    ).textContent = formatCurrency(
        lot.standard_error_per_lot
    );

    document.getElementById(
        "absolute-error-lot"
    ).textContent = formatCurrency(
        lot.absolute_error_per_lot
    );

    document.getElementById(
        "confidence-interval-lot"
    ).textContent =
        formatCurrency(
            lot.confidence_interval_per_lot.lower
        ) +
        " – " +
        formatCurrency(
            lot.confidence_interval_per_lot.upper
        );
}


function displayCalculationDataStatus(data) {
    const status = data.market_data_status;

    if (!status) {
        return;
    }

    document.getElementById(
        "calculation-data-status"
    ).textContent = status.status.toUpperCase();

    document.getElementById(
        "calculation-data-warnings"
    ).textContent = (
        status.warnings || []
    ).join(" ");
}

function formatBenchmarkCurrency(value) {
    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "N/A";
    }

    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        minimumFractionDigits: 2,
        maximumFractionDigits: 4
    }).format(number);
}


function displayBenchmarkResults(data) {
    const benchmark = data.benchmark_result;
    const comparison = data.comparison_result;

    if (!benchmark || !comparison) {
        console.error(
            "Analytical benchmark results are missing."
        );
        return;
    }

    document.getElementById(
        "black-scholes-price"
    ).textContent = formatBenchmarkCurrency(
        benchmark.estimated_price
    );

    document.getElementById(
        "benchmark-absolute-error"
    ).textContent = formatBenchmarkCurrency(
        comparison.absolute_error
    );

    const relativeErrorElement = document.getElementById(
        "benchmark-relative-error"
    );

    if (comparison.relative_error_percent === null) {
        relativeErrorElement.textContent =
            "N/A (analytical price is zero)";
    } else {
        relativeErrorElement.textContent =
            `${comparison.relative_error_percent.toFixed(6)}%`;
    }

    const ciStatusElement = document.getElementById(
        "benchmark-ci-status"
    );

    const isInside =
        comparison.confidence_interval_contains_benchmark;

    if (isInside) {
        ciStatusElement.textContent =
            "Inside the 95% confidence interval";

        ciStatusElement.className =
            "detail-value text-success fw-semibold";
    } else {
        ciStatusElement.textContent =
            "Outside the 95% confidence interval";

        ciStatusElement.className =
            "detail-value text-warning fw-semibold";
    }
}

function formatGreekValue(value) {
    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "N/A";
    }

    return number.toFixed(6);
}


function displayGreeks(data) {

    const greeks = data.greeks_result;
    const validation = data.greeks_validation_result;

    const greekElements = {
        delta: document.getElementById("greek-delta"),
        gamma: document.getElementById("greek-gamma"),
        vega: document.getElementById("greek-vega"),
        theta: document.getElementById("greek-theta"),
        rho: document.getElementById("greek-rho")
    };

    const tableBody = document.getElementById(
        "greeks-validation-body"
    );

    // --------------------------------------------------
    // 1. Handle unavailable Greeks
    // --------------------------------------------------

    if (!greeks || greeks.available !== true) {

        // Clear all previous Greek values.
        // This prevents stale values from a previous
        // successful calculation from remaining visible.
        Object.values(greekElements).forEach(element => {

            element.textContent = "N/A";

        });

        // Clear the previous validation table.
        tableBody.replaceChildren();

        const row = document.createElement("tr");

        const cell = document.createElement("td");

        cell.colSpan = 4;

        cell.className = "text-muted";

        cell.textContent = (
            greeks?.reason ||
            "Greek calculations are unavailable for this scenario."
        );

        row.appendChild(cell);

        tableBody.appendChild(row);

        return;
    }

    // --------------------------------------------------
    // 2. Display analytical Greek values
    // --------------------------------------------------

    greekElements.delta.textContent =
        formatGreekValue(greeks.delta);

    greekElements.gamma.textContent =
        formatGreekValue(greeks.gamma);

    greekElements.vega.textContent =
        formatGreekValue(
            greeks.vega_per_1_percentage_point
        );

    greekElements.theta.textContent =
        formatGreekValue(
            greeks.theta_per_calendar_day
        );

    greekElements.rho.textContent =
        formatGreekValue(
            greeks.rho_per_1_percentage_point
        );

    // --------------------------------------------------
    // 3. Handle unavailable comparison results
    // --------------------------------------------------

    if (!validation || validation.available === false) {

        tableBody.replaceChildren();

        const row = document.createElement("tr");

        const cell = document.createElement("td");

        cell.colSpan = 4;

        cell.className = "text-muted";

        cell.textContent = (
            validation?.reason ||
            "Greek comparison is unavailable."
        );

        row.appendChild(cell);

        tableBody.appendChild(row);

        return;
    }

    // --------------------------------------------------
    // 4. Display analytical versus numerical Greeks
    // --------------------------------------------------

    const greekRows = [
        ["Delta", "delta"],
        ["Gamma", "gamma"],
        ["Vega", "vega_per_1_00_volatility"],
        ["Theta", "theta_per_year"],
        ["Rho", "rho_per_1_00_rate"]
    ];

    tableBody.replaceChildren();

    greekRows.forEach(([label, key]) => {

        const item = validation[key];

        const row = document.createElement("tr");

        const values = [
            label,
            formatGreekValue(item.analytical),
            formatGreekValue(item.numerical),
            formatGreekValue(item.absolute_difference)
        ];

        values.forEach(value => {

            const cell = document.createElement("td");

            cell.textContent = value;

            row.appendChild(cell);

        });

        tableBody.appendChild(row);

    });
}

function createSensitivityChart(
    existingChart,
    canvasId,
    scenario,
    datasetLabel
) {
    if (!scenario || !Array.isArray(scenario.data)) {
        return existingChart;
    }

    if (existingChart) {
        existingChart.destroy();
    }

    const canvas = document.getElementById(canvasId);

    if (!canvas) {
        return null;
    }

    const labels = scenario.data.map(point => {
        const value = Number(point.input_value);

        const precision =
            canvasId === "maturity-sensitivity-chart" ? 5 : 3;

        return value.toFixed(precision);
    });

    const prices = scenario.data.map(point =>
        Number(point.option_price)
    );

    return new Chart(canvas, {
        type: "line",

        data: {
            labels: labels,

            datasets: [{
                label: datasetLabel,
                data: prices,
                tension: 0.25,
                fill: false
            }]
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,

            plugins: {
                legend: {
                    display: false
                },

                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return "Option Price: ₹" +
                                context.parsed.y.toFixed(4);
                        }
                    }
                }
            },

            scales: {
                x: {
                    title: {
                        display: true,
                        text: scenario.x_axis_label
                    }
                },

                y: {
                    title: {
                        display: true,
                        text: "Option Price (₹)"
                    },

                    beginAtZero: true
                }
            }
        }
    });
}


function displaySensitivityCharts(data) {
    const sensitivity = data.sensitivity_result;

    if (!sensitivity) {
        console.error("Sensitivity results are missing.");
        return;
    }

    spotSensitivityChart = createSensitivityChart(
        spotSensitivityChart,
        "spot-sensitivity-chart",
        sensitivity.spot_price,
        "Option Price"
    );

    volatilitySensitivityChart = createSensitivityChart(
        volatilitySensitivityChart,
        "volatility-sensitivity-chart",
        sensitivity.volatility,
        "Option Price"
    );

    maturitySensitivityChart = createSensitivityChart(
        maturitySensitivityChart,
        "maturity-sensitivity-chart",
        sensitivity.time_to_expiry,
        "Option Price"
    );
}


async function requestApi(url, options = {}) {
    const response = await fetch(url, options);

    let result;

    try {
        result = await response.json();
    } catch {
        throw new Error("The server returned an invalid response.");
    }

    if (!response.ok) {
        throw new Error(
            result.error?.message ||
            "The requested operation could not be completed."
        );
    }

    return result;
}


function populateSelect(selectElement, values, placeholder) {
    selectElement.replaceChildren();

    const placeholderOption = new Option(
        placeholder,
        ""
    );

    placeholderOption.disabled = true;
    placeholderOption.selected = true;

    selectElement.add(placeholderOption);

    values.forEach(value => {
        selectElement.add(
            new Option(String(value), String(value))
        );
    });

    selectElement.disabled = values.length === 0;
}


function setMarketStatusDisplay(status) {
    latestMarketStatus = status;

    const heading = document.getElementById(
        "market-status-heading"
    );

    const details = document.getElementById(
        "market-status-details"
    );

    const warnings = document.getElementById(
        "market-status-warnings"
    );

    const raw = status.raw || {};
    const adjusted = status.adjusted || {};

    const statusLabels = {
        fresh: "Market data is fresh",
        aging: "Market data is aging",
        stale: "Market data is stale",
        date_mismatch: "Raw and adjusted dates do not match",
        missing: "Market data is missing",
        invalid: "Market data is invalid"
    };

    heading.textContent =
        statusLabels[status.status] || "Market-data status unknown";

    if (status.status === "fresh") {
        marketStatusPanel.className =
            "border rounded p-3 mb-3 alert alert-success";
    } else if (
        status.status === "aging" ||
        status.status === "date_mismatch"
    ) {
        marketStatusPanel.className =
            "border rounded p-3 mb-3 alert alert-warning";
    } else {
        marketStatusPanel.className =
            "border rounded p-3 mb-3 alert alert-danger";
    }

    details.textContent =
        `Raw latest date: ${raw.latest_date || "Missing"} | ` +
        `Adjusted latest date: ${adjusted.latest_date || "Missing"} | ` +
        `Last raw retrieval: ${raw.last_retrieved_at_utc || "Unknown"}`;

    warnings.textContent = (
        status.warnings || []
    ).join(" ");

    if (refreshMarketDataButton) {
        refreshMarketDataButton.disabled = false;
    }
}


async function loadMarketStatus(symbol) {
    const result = await requestApi(
        `/api/market-data/status?symbol=${encodeURIComponent(symbol)}`
    );

    setMarketStatusDisplay(result.market_data);

    return result.market_data;
}


async function loadAvailableSymbols() {
    symbolInput.disabled = true;

    populateSelect(
        symbolInput,
        [],
        "Loading NSE stock symbols..."
    );

    const result = await requestApi(
        "/api/contracts/symbols"
    );

    if (!result.symbols.length) {
        throw new Error(
            "No NSE stock-option symbols are available."
        );
    }

    symbolInput.replaceChildren();

    result.symbols.forEach(symbol => {
        symbolInput.add(
            new Option(symbol, symbol)
        );
    });

    const preferredSymbol = result.symbols.includes("RELIANCE")
        ? "RELIANCE"
        : result.symbols[0];

    symbolInput.value = preferredSymbol;
    symbolInput.disabled = false;

    await loadMarketStatus(preferredSymbol);

    await loadAvailableExpiries();
}


async function loadAvailableExpiries() {
    const symbol = symbolInput.value;

    if (!symbol) {
        populateSelect(
            expiryInput,
            [],
            "Select a stock first"
        );

        return;
    }

    expiryInput.disabled = true;

    const result = await requestApi(
        `/api/contracts/expiries?symbol=${encodeURIComponent(symbol)}`
    );

    const expiries = result.expiries || [];

    // Remember the expiry currently selected.
    const previousExpiry = expiryInput.value;

    populateSelect(
        expiryInput,
        expiries,
        expiries.length
            ? "Select expiry"
            : "No future expiries available"
    );

    if (!expiries.length) {

        populateSelect(
            strikeInput,
            [],
            "No contract strikes available"
        );

        return;
    }

    // Preserve the previous expiry if it is still listed.
    // Otherwise select the nearest available expiry.
    if (expiries.includes(previousExpiry)) {

        expiryInput.value = previousExpiry;

    } else {

        expiryInput.value = expiries[0];

    }

    await loadAvailableStrikes();
}


async function loadAvailableStrikes() {
    const symbol = symbolInput.value;
    const expiry = expiryInput.value;
    const optionType = optionTypeInput.value;

    if (!symbol || !expiry) {
        populateSelect(
            strikeInput,
            [],
            "Select stock and expiry first"
        );

        return;
    }

    strikeInput.disabled = true;

    const query = new URLSearchParams({
        symbol: symbol,
        expiry_date: expiry,
        option_type: optionType
    });

    const result = await requestApi(
        `/api/contracts/strikes?${query.toString()}`
    );

    const strikes = result.strikes || [];

    populateSelect(
        strikeInput,
        strikes,
        strikes.length
            ? "Select listed strike"
            : "No listed strikes available"
    );

    if (!strikes.length) {
        return;
    }

    const currentSpot = Number(
        latestMarketStatus?.raw?.latest_close
    );

    // Prefer a strike near the cached spot price.
    // If spot is unavailable, use the first available strike.
    if (Number.isFinite(currentSpot) && currentSpot > 0) {

        const closestStrike = strikes.reduce(
            (closest, current) =>
                Math.abs(current - currentSpot) <
                Math.abs(closest - currentSpot)
                    ? current
                    : closest
        );

        strikeInput.value = String(closestStrike);

    } else {

        strikeInput.value = String(strikes[0]);

    }
}


async function refreshSelectedStockData() {
    const symbol = symbolInput.value;

    if (!symbol) {
        throw new Error("Select a stock first.");
    }

    refreshMarketDataButton.disabled = true;

    const originalText = refreshMarketDataButton.textContent;

    refreshMarketDataButton.textContent = "Refreshing...";

    const message = document.getElementById(
        "market-refresh-message"
    );

    message.textContent = "Downloading raw and adjusted data from TejHQ...";

    try {
        const result = await requestApi(
            "/api/market-data/refresh",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    symbol: symbol,
                    exchange: "nse",
                    lookback_days: 365
                })
            }
        );

        const refresh = result.refresh;

        message.textContent =
            `Refresh completed. Raw records received: ` +
            `${refresh.raw_rows_received}; adjusted records received: ` +
            `${refresh.adjusted_rows_received}.`;

        await loadMarketStatus(symbol);

    } finally {
        refreshMarketDataButton.disabled = false;
        refreshMarketDataButton.textContent = originalText;
    }
}


async function initializeContractSelectors() {
    try {

        await loadAvailableSymbols();

    } catch (error) {

        console.error(
            "Could not initialize NSE contract selection:",
            error
        );

        showError(error.message);

        populateSelect(
            symbolInput,
            [],
            "Contract metadata unavailable"
        );
    }
}


// Stock selection changes the available expiries and cached data.
symbolInput.addEventListener(
    "change",
    async function() {
        hideError();

        try {
            await loadMarketStatus(symbolInput.value);
            await loadAvailableExpiries();
        } catch (error) {
            showError(error.message);
        }
    }
);


// Expiry selection changes available strikes.
expiryInput.addEventListener(
    "change",
    async function() {
        hideError();

        try {
            await loadAvailableStrikes();
        } catch (error) {
            showError(error.message);
        }
    }
);


// Call/Put selection changes available strike list.
optionTypeInput.addEventListener(
    "change",
    async function() {
        hideError();

        try {
            await loadAvailableStrikes();
        } catch (error) {
            showError(error.message);
        }
    }
);


// Refresh button action.
refreshMarketDataButton.addEventListener(
    "click",
    async function() {

        hideError();

        try {
            await refreshSelectedStockData();
        } catch (error) {
            showError(error.message);

            document.getElementById(
                "market-refresh-message"
            ).textContent = error.message;
        }
    }
);


// -------------------------------------------------------
// STAGE 17 — ADVANCED OPTION ANALYTICS
// -------------------------------------------------------


async function stage17Post(url, payload) {

    const response = await fetch(url, {
        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify(payload)
    });

    let result;

    try {
        result = await response.json();
    } catch {
        throw new Error(
            "Stage 17 API returned an invalid response."
        );
    }

    if (!response.ok) {
        throw new Error(
            result.error?.message ||
            "Stage 17 analysis could not be completed."
        );
    }

    return result;
}


function destroyStage17Chart(chart) {
    if (chart) {
        chart.destroy();
    }
}


function displayTerminalDistribution(distribution) {

    document.getElementById(
        "terminal-mean"
    ).textContent = formatCurrency(
        distribution.summary.sample_mean
    );

    document.getElementById(
        "terminal-theoretical-mean"
    ).textContent = formatCurrency(
        distribution.summary.theoretical_expected_terminal_price
    );

    document.getElementById(
        "terminal-p5"
    ).textContent = formatCurrency(
        distribution.summary.sample_5th_percentile
    );

    document.getElementById(
        "terminal-p95"
    ).textContent = formatCurrency(
        distribution.summary.sample_95th_percentile
    );

    const labels = distribution.histogram.map(bin =>
        `${bin.lower.toFixed(0)}–${bin.upper.toFixed(0)}`
    );

    const counts = distribution.histogram.map(bin =>
        bin.count
    );

    destroyStage17Chart(terminalDistributionChart);

    const canvas = document.getElementById(
        "terminal-distribution-chart"
    );

    terminalDistributionChart = new Chart(canvas, {

        type: "bar",

        data: {
            labels: labels,

            datasets: [{
                label: "Simulated observations",
                data: counts,
                borderRadius: 3,
                maxBarThickness: 30
            }]
        },

        options: {

            responsive: true,
            maintainAspectRatio: false,

            plugins: {
                legend: {
                    display: false
                },

                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return (
                                "Observations: " +
                                context.raw.toLocaleString("en-IN")
                            );
                        }
                    }
                }
            },

            scales: {

                x: {
                    title: {
                        display: true,
                        text: "Terminal Stock Price Range (₹)"
                    },

                    ticks: {
                        maxTicksLimit: 10
                    }
                },

                y: {
                    beginAtZero: true,

                    title: {
                        display: true,
                        text: "Number of Simulated Observations"
                    }
                }
            }
        }
    });
}


function displaySingleOptionPayoff(payoff) {

    document.getElementById(
        "single-break-even"
    ).textContent = (
        payoff.break_even_stock_price === null
            ? "No non-negative break-even price"
            : formatCurrency(payoff.break_even_stock_price)
    );

    document.getElementById(
        "single-premium-lot"
    ).textContent = formatCurrency(
        payoff.premium_per_lot
    );

    document.getElementById(
        "single-long-max-profit"
    ).textContent = (
        payoff.long_position.maximum_profit_label === "Unlimited"
            ? "Unlimited"
            : formatCurrency(payoff.long_position.maximum_profit)
    );

    document.getElementById(
        "single-long-max-loss"
    ).textContent = formatCurrency(
        payoff.long_position.maximum_loss
    );

    document.getElementById(
        "single-short-max-profit"
    ).textContent = formatCurrency(
        payoff.short_position.maximum_profit
    );

    document.getElementById(
        "single-short-max-loss"
    ).textContent = (
        payoff.short_position.maximum_loss_label === "Unlimited"
            ? "Unlimited"
            : formatCurrency(payoff.short_position.maximum_loss)
    );


    const points = payoff.points;

    const labels = points.map(point =>
        Number(point.terminal_stock_price).toFixed(2)
    );

    const payoffValues = points.map(point =>
        point.payoff_per_lot
    );

    const longValues = points.map(point =>
        point.long_pnl_per_lot
    );

    const shortValues = points.map(point =>
        point.short_pnl_per_lot
    );


    destroyStage17Chart(singleOptionPayoffChart);

    const canvas = document.getElementById(
        "single-option-payoff-chart"
    );

    singleOptionPayoffChart = new Chart(canvas, {

        type: "line",

        data: {
            labels: labels,

            datasets: [

                {
                    label: "Expiry Payoff",
                    data: payoffValues,
                    tension: 0,
                    fill: false
                },

                {
                    label: "Long Position P&L",
                    data: longValues,
                    tension: 0,
                    fill: false
                },

                {
                    label: "Short Position P&L",
                    data: shortValues,
                    tension: 0,
                    fill: false
                }

            ]
        },

        options: {

            responsive: true,
            maintainAspectRatio: false,

            interaction: {
                mode: "index",
                intersect: false
            },

            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return (
                                context.dataset.label +
                                ": " +
                                formatCurrency(context.parsed.y)
                            );
                        }
                    }
                }
            },

            scales: {

                x: {
                    title: {
                        display: true,
                        text: "Terminal Stock Price (₹)"
                    },

                    ticks: {
                        maxTicksLimit: 12
                    }
                },

                y: {
                    title: {
                        display: true,
                        text: "Payoff / Profit and Loss per Lot (₹)"
                    }
                }
            }
        }
    });
}


async function loadStage17Analytics(data) {

    // Every call receives a unique request number.
    const requestId = ++stage17AnalyticsSequence;

    const status = document.getElementById(
        "stage17-analytics-status"
    );

    try {

        const distributionPayload = {
            option_parameters: data.option_parameters,
            sample_count: 20000,
            bins: 40,
            seed: data.option_parameters.seed ?? 42
        };

        const payoffPayload = {
            option_parameters: data.option_parameters,

            premium_per_share:
                data.pricing_result.estimated_price,

            lot_size:
                data.contract_metadata.board_lot_quantity,

            points: 101
        };

        const [
            distributionResponse,
            payoffResponse
        ] = await Promise.all([

            stage17Post(
                "/api/analytics/distribution",
                distributionPayload
            ),

            stage17Post(
                "/api/analytics/payoff",
                payoffPayload
            )

        ]);

        // Ignore responses from an older calculation.
        if (
            requestId !== stage17AnalyticsSequence ||
            data !== latestStage17PricingData
        ) {
            return;
        }

        displayTerminalDistribution(
            distributionResponse.distribution
        );

        displaySingleOptionPayoff(
            payoffResponse.payoff_analysis
        );

        if (status) {

            status.textContent =
                "Terminal distribution and payoff analysis completed.";

        }

    } catch (error) {

        // An old failed request must not overwrite
        // the status of a newer calculation.
        if (
            requestId !== stage17AnalyticsSequence ||
            data !== latestStage17PricingData
        ) {
            return;
        }

        console.error(
            "Stage 17 analytics error:",
            error
        );

        if (status) {
            status.textContent = error.message;
        }

    }
}


function updateStrategyFormVisibility() {

    const strategy = document.getElementById(
        "strategy-type"
    ).value;

    const isSpread = (
        strategy === "bull_call_spread" ||
        strategy === "bear_put_spread"
    );

    const upperContainer = document.getElementById(
        "strategy-upper-strike-container"
    );

    const upperInput = document.getElementById(
        "strategy-upper-strike"
    );

    upperContainer.classList.toggle(
        "d-none",
        !isSpread
    );

    upperInput.required = isSpread;

    upperInput.disabled = !isSpread;
}


function prefillStrategyControls(data) {

    const lowerInput = document.getElementById(
        "strategy-lower-strike"
    );

    lowerInput.value =
        data.option_parameters.strike_price;

    document.getElementById(
        "strategy-upper-strike"
    ).value = "";

    document.getElementById(
        "strategy-lots"
    ).value = 1;

    document.getElementById(
        "strategy-output"
    ).classList.add("d-none");

    document.getElementById(
        "strategy-status"
    ).textContent =
        "Use actual listed NSE strikes for all strategy legs.";

    document.getElementById(
        "analyze-strategy-button"
    ).disabled = false;

    updateStrategyFormVisibility();
}


function formatStrategyLimit(value, label) {

    if (value === null || value === undefined) {
        return "Unlimited";
    }

    return formatCurrency(value);
}


function displayStrategyAnalysis(result) {

    document.getElementById(
        "strategy-net-cashflow"
    ).textContent =
        `${result.initial_cashflow_label}: ` +
        formatCurrency(Math.abs(result.initial_net_cashflow));

    document.getElementById(
        "strategy-max-profit"
    ).textContent = formatStrategyLimit(
        result.maximum_profit,
        result.maximum_profit_label
    );

    document.getElementById(
        "strategy-max-loss"
    ).textContent = formatStrategyLimit(
        result.maximum_loss,
        result.maximum_loss_label
    );

    document.getElementById(
        "strategy-break-even"
    ).textContent = (
        result.break_even_prices.length
            ? result.break_even_prices
                .map(value => formatCurrency(value))
                .join(" / ")
            : "No non-negative break-even point"
    );


    const tableBody = document.getElementById(
        "strategy-legs-body"
    );

    tableBody.replaceChildren();

    result.legs.forEach(leg => {

        const row = document.createElement("tr");

        const values = [
            leg.position.toUpperCase(),
            leg.option_type.toUpperCase(),
            formatCurrency(leg.strike_price),
            formatCurrency(leg.premium_per_share),
            Number(leg.board_lot_quantity).toLocaleString("en-IN"),
            leg.contract_id
        ];

        values.forEach(value => {

            const cell = document.createElement("td");

            cell.textContent = value;

            row.appendChild(cell);
        });

        tableBody.appendChild(row);
    });


    document.getElementById(
        "strategy-warnings"
    ).textContent = [
        result.pricing_method,
        result.limitations,
        ...(result.warnings || [])
    ].join(" ");


    destroyStage17Chart(strategyPnlChart);

    const points = result.points;

    strategyPnlChart = new Chart(
        document.getElementById("strategy-pnl-chart"),
        {

            type: "line",

            data: {
                labels: points.map(point =>
                    Number(
                        point.terminal_stock_price
                    ).toFixed(2)
                ),

                datasets: [{
                    label: "Strategy P&L",
                    data: points.map(point =>
                        point.strategy_pnl
                    ),
                    tension: 0,
                    fill: false
                }]
            },

            options: {

                responsive: true,
                maintainAspectRatio: false,

                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return (
                                    "Strategy P&L: " +
                                    formatCurrency(context.parsed.y)
                                );
                            }
                        }
                    }
                },

                scales: {

                    x: {
                        title: {
                            display: true,
                            text: "Terminal Stock Price (₹)"
                        },

                        ticks: {
                            maxTicksLimit: 12
                        }
                    },

                    y: {
                        title: {
                            display: true,
                            text: "Strategy Profit / Loss (₹)"
                        }
                    }
                }
            }
        }
    );


    document.getElementById(
        "strategy-output"
    ).classList.remove("d-none");
}


async function analyzeSelectedStrategy() {

    const requestId = ++strategyAnalysisSequence;

    const latest = latestStage17PricingData;

    if (!latest) {
        throw new Error(
            "Calculate an option first."
        );
    }

    const strategy = document.getElementById(
        "strategy-type"
    ).value;

    const lowerStrike = Number(
        document.getElementById("strategy-lower-strike").value
    );

    const upperInput = document.getElementById(
        "strategy-upper-strike"
    );

    const upperStrike = (
        upperInput.disabled
            ? null
            : Number(upperInput.value)
    );

    const lots = Number(
        document.getElementById("strategy-lots").value
    );


    if (!Number.isFinite(lowerStrike) || lowerStrike <= 0) {
        throw new Error(
            "Enter a valid lower or selected strike."
        );
    }

    if (
        upperStrike !== null &&
        (!Number.isFinite(upperStrike) || upperStrike <= 0)
    ) {
        throw new Error("Enter a valid upper strike.");
    }

    if (
        !Number.isInteger(lots) ||
        lots < 1 ||
        lots > 50
    ) {
        throw new Error(
            "Number of lots must be an integer between 1 and 50."
        );
    }


    const payload = {

        option_parameters: latest.option_parameters,

        symbol: latest.contract_metadata.symbol,

        expiry_date: latest.contract_metadata.expiry_date,

        strategy: strategy,

        lower_strike: lowerStrike,

        upper_strike: upperStrike,

        lots: lots
    };


    const button = document.getElementById(
        "analyze-strategy-button"
    );

    const status = document.getElementById(
        "strategy-status"
    );

    button.disabled = true;
    button.textContent = "Analyzing...";

    status.textContent =
        "Validating NSE contracts and calculating theoretical strategy P&L...";

    try {

        const response = await stage17Post(
            "/api/strategies/analyze",
            payload
        );

        // Ignore a response if the main pricing result
        // has changed while strategy analysis was running.
        if (
            requestId !== strategyAnalysisSequence ||
            latest !== latestStage17PricingData
        ) {
            return;
        }

        displayStrategyAnalysis(
            response.strategy_analysis
        );

        status.textContent =
            "Strategy analysis completed successfully.";

    } finally {

        if (requestId === strategyAnalysisSequence) {

            button.disabled = false;

            button.textContent = "Analyze Strategy";

        }

    }
}


// Stage 17 strategy selection.
document.getElementById("strategy-type").addEventListener(
    "change",
    updateStrategyFormVisibility
);


// Stage 17 strategy analysis button.
document.getElementById(
    "analyze-strategy-button"
).addEventListener(
    "click",
    async function() {

        const status = document.getElementById(
            "strategy-status"
        );

        try {

            hideError();

            await analyzeSelectedStrategy();

        } catch (error) {

            console.error(
                "Strategy analysis error:",
                error
            );

            status.textContent = error.message;

        }
    }
);


updateStrategyFormVisibility();


// Initialize volatility selector
volatilityModeInput.addEventListener(
    "change",
    updateVolatilityMode
);

updateVolatilityMode();
initializeContractSelectors();

// Pricing form submission
form.addEventListener("submit", async function(event) {

    event.preventDefault();

    // Mark this as the newest pricing request.
    const requestId = ++pricingRequestSequence;

    // Invalidate pending analytics and strategy requests
    // associated with the previous pricing result.
    stage17AnalyticsSequence += 1;

    strategyAnalysisSequence += 1;

    // Do not allow the previous pricing result to be
    // used while a newer calculation is in progress.
    latestStage17PricingData = null;

    hideError();

    resultsPanel.classList.add("d-none");
    emptyState.classList.add("d-none");

    setLoading(true);

    try {

        // Read form inputs
        const symbol = document
            .getElementById("symbol")
            .value.trim()
            .toUpperCase();

        const strikePrice = Number(
            document.getElementById("strike-price").value
        );

        const riskFreeRate = Number(
            document.getElementById("risk-free-rate").value
        ) / 100;

        const dividendYield = Number(
            document.getElementById("dividend-yield").value
        ) / 100;

        const expiryDate = document
            .getElementById("expiry-date")
            .value;

        const optionType = document
            .getElementById("option-type")
            .value;

        const simulations = Number(
            document.getElementById("simulations").value
        );

        const volatilityMode = volatilityModeInput.value;


        // Basic client-side validation
        if (!symbol) {
            throw new Error("Please enter a stock symbol.");
        }

        if (!Number.isFinite(strikePrice) || strikePrice <= 0) {
            throw new Error("Strike price must be positive.");
        }

        if (!Number.isFinite(riskFreeRate)) {
            throw new Error("Enter a valid risk-free rate.");
        }

        if (!Number.isFinite(dividendYield)) {
            throw new Error("Enter a valid dividend yield.");
        }

        if (!expiryDate) {
            throw new Error("Please select an expiry date.");
        }


        // Construct request
        const payload = {

            symbol: symbol,

            exchange: "nse",

            strike_price: strikePrice,

            risk_free_rate: riskFreeRate,

            dividend_yield: dividendYield,

            expiry_date: expiryDate,

            option_type: optionType,

            volatility_mode: volatilityMode,

            simulations: simulations,

            seed: 42

        };


        // Add manual volatility only in manual mode
        if (volatilityMode === "manual") {

            const manualVolatilityPercent = Number(
                manualVolatilityInput.value
            );

            if (
                !Number.isFinite(manualVolatilityPercent) ||
                manualVolatilityPercent <= 0
            ) {
                throw new Error(
                    "Manual volatility must be a positive percentage."
                );
            }

            // Convert percentage to decimal
            payload.manual_volatility =
                manualVolatilityPercent / 100;

        }


        // Send request to Flask
        const response = await fetch("/api/price", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify(payload)

        });


        const result = await response.json();

        // Discard an outdated pricing response.
        if (requestId !== pricingRequestSequence) {
            return;
        }

        if (!response.ok) {

            throw new Error(
                result.error?.message ||
                "Unable to calculate option premium."
            );

        }


        displayResults(result);

    } catch (error) {

        // Ignore errors from outdated pricing requests.
        if (requestId !== pricingRequestSequence) {
            return;
        }

        console.error(
            "OptionLab pricing error:",
            error
        );

        showError(error.message);

        emptyState.classList.remove("d-none");

    } finally {

        // An older request must not switch off the
        // loading state of a newer request.
        if (requestId === pricingRequestSequence) {
            setLoading(false);
        }

    }

});
