#include "MonteCarlo.h"

#include <algorithm>
#include <cmath>
#include <functional>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

using namespace optionlab;

// --------------------------------------------------
// Basic testing utilities
// --------------------------------------------------

int total_tests = 0;
int passed_tests = 0;

void require(bool condition, const std::string& message) {

    if (!condition) {
        throw std::runtime_error(message);
    }
}

void require_near(
    double actual,
    double expected,
    double tolerance,
    const std::string& message
) {
    if (std::abs(actual - expected) > tolerance) {

        throw std::runtime_error(
            message +
            " | Expected: " + std::to_string(expected) +
            " | Actual: " + std::to_string(actual)
        );
    }
}

void run_test(
    const std::string& name,
    const std::function<void()>& test
) {

    total_tests++;

    try {

        test();

        passed_tests++;

        std::cout << "[PASS] " << name << '\n';

    }
    catch (const std::exception& error) {

        std::cout << "[FAIL] " << name
                  << " -> " << error.what() << '\n';
    }
}

// --------------------------------------------------
// Analytical reference for testing only
// --------------------------------------------------

double normal_cdf(double x) {

    return 0.5 * std::erfc(-x / std::sqrt(2.0));
}

double black_scholes_reference(
    const OptionParameters& option
) {

    const double S = option.spot_price;
    const double K = option.strike_price;
    const double r = option.risk_free_rate;
    const double q = option.dividend_yield;
    const double sigma = option.volatility;
    const double T = option.time_to_expiry_years;

    if (T == 0.0) {

        return option.type == OptionType::Call
            ? std::max(S - K, 0.0)
            : std::max(K - S, 0.0);
    }

    const double sqrt_T = std::sqrt(T);

    const double d1 =
        (std::log(S / K) +
        (r - q + 0.5 * sigma * sigma) * T)
        / (sigma * sqrt_T);

    const double d2 = d1 - sigma * sqrt_T;

    const double discount_stock = std::exp(-q * T);
    const double discount_strike = std::exp(-r * T);

    if (option.type == OptionType::Call) {

        return S * discount_stock * normal_cdf(d1)
             - K * discount_strike * normal_cdf(d2);

    }

    return K * discount_strike * normal_cdf(-d2)
         - S * discount_stock * normal_cdf(-d1);
}

// --------------------------------------------------
// Default test parameters
// --------------------------------------------------

OptionParameters default_option(OptionType type) {

    return {
        271.86,
        280.00,
        0.06,
        0.00,
        0.321758,
        1.0,
        type
    };
}

// --------------------------------------------------
// Test 1: European Call
// --------------------------------------------------

void test_european_call() {

    const auto option = default_option(OptionType::Call);

    const auto result = price_option_monte_carlo(
        option, 100000, 42
    );

    const double reference =
        black_scholes_reference(option);

    const double tolerance =
        4.0 * result.standard_error + 1e-9;

    require(
        std::abs(result.estimated_price - reference) <= tolerance,
        "Monte Carlo Call price differs excessively from reference."
    );
}

// --------------------------------------------------
// Test 2: European Put
// --------------------------------------------------

void test_european_put() {

    const auto option = default_option(OptionType::Put);

    const auto result = price_option_monte_carlo(
        option, 100000, 42
    );

    const double reference =
        black_scholes_reference(option);

    const double tolerance =
        4.0 * result.standard_error + 1e-9;

    require(
        std::abs(result.estimated_price - reference) <= tolerance,
        "Monte Carlo Put price differs excessively from reference."
    );
}

// --------------------------------------------------
// Test 3: Put-Call Parity
// --------------------------------------------------

void test_put_call_parity() {

    const auto call_option = default_option(OptionType::Call);

    const auto put_option = default_option(OptionType::Put);

    const auto call_result = price_option_monte_carlo(
        call_option, 100000, 42
    );

    const auto put_result = price_option_monte_carlo(
        put_option, 100000, 42
    );

    const double expected_difference =
        call_option.spot_price *
        std::exp(-call_option.dividend_yield *
                 call_option.time_to_expiry_years)
        -
        call_option.strike_price *
        std::exp(-call_option.risk_free_rate *
                 call_option.time_to_expiry_years);

    const double actual_difference =
        call_result.estimated_price -
        put_result.estimated_price;

    const double tolerance =
        4.0 * (
            call_result.standard_error +
            put_result.standard_error
        ) + 1e-9;

    require_near(
        actual_difference,
        expected_difference,
        tolerance,
        "Put-Call parity check failed."
    );
}

// --------------------------------------------------
// Test 4: Zero Volatility
// --------------------------------------------------

void test_zero_volatility() {

    auto option = default_option(OptionType::Call);

    option.volatility = 0.0;

    const auto result = price_option_monte_carlo(
        option, 10000, 42
    );

    const double future_price =
        option.spot_price *
        std::exp(
            (option.risk_free_rate - option.dividend_yield) *
            option.time_to_expiry_years
        );

    const double expected =
        std::exp(
            -option.risk_free_rate *
            option.time_to_expiry_years
        ) *
        std::max(future_price - option.strike_price, 0.0);

    require_near(
        result.estimated_price,
        expected,
        1e-9,
        "Zero volatility calculation is incorrect."
    );

    require_near(
        result.standard_error,
        0.0,
        1e-12,
        "Standard error should be zero."
    );
}

// --------------------------------------------------
// Test 5: Zero Maturity
// --------------------------------------------------

void test_zero_maturity() {

    auto option = default_option(OptionType::Call);

    option.time_to_expiry_years = 0.0;

    const auto result = price_option_monte_carlo(
        option, 10000, 42
    );

    const double expected =
        std::max(
            option.spot_price - option.strike_price,
            0.0
        );

    require_near(
        result.estimated_price,
        expected,
        1e-9,
        "Expiry payoff is incorrect."
    );

    require_near(
        result.standard_error,
        0.0,
        1e-12,
        "Expiry standard error should be zero."
    );
}

// --------------------------------------------------
// Test 6: Confidence Interval
// --------------------------------------------------

void test_confidence_interval() {

    const auto option = default_option(OptionType::Call);

    const auto result = price_option_monte_carlo(
        option, 100000, 42
    );

    require(
        result.confidence_interval_lower <=
        result.estimated_price,
        "Lower confidence bound is incorrect."
    );

    require(
        result.confidence_interval_upper >=
        result.estimated_price,
        "Upper confidence bound is incorrect."
    );

    require_near(
        result.confidence_interval_lower,
        result.estimated_price - 1.96 * result.standard_error,
        1e-10,
        "Incorrect lower confidence interval."
    );

    require_near(
        result.confidence_interval_upper,
        result.estimated_price + 1.96 * result.standard_error,
        1e-10,
        "Incorrect upper confidence interval."
    );
}

// --------------------------------------------------
// Test 7: Invalid Inputs
// --------------------------------------------------

void expect_invalid_argument(
    const OptionParameters& option,
    std::size_t simulations
) {

    bool exception_caught = false;

    try {

        price_option_monte_carlo(
            option, simulations, 42
        );

    }
    catch (const std::invalid_argument&) {

        exception_caught = true;

    }

    require(
        exception_caught,
        "Expected invalid_argument was not thrown."
    );
}

void test_invalid_inputs() {

    auto option = default_option(OptionType::Call);

    option.spot_price = 0.0;

    expect_invalid_argument(option, 10000);

    option = default_option(OptionType::Call);
    option.volatility = -0.10;

    expect_invalid_argument(option, 10000);

    option = default_option(OptionType::Call);

    expect_invalid_argument(option, 1);

    option = default_option(OptionType::Call);
    option.risk_free_rate =
        std::numeric_limits<double>::infinity();

    expect_invalid_argument(option, 10000);

    option = default_option(OptionType::Call);
    option.type = static_cast<OptionType>(99);

    expect_invalid_argument(option, 10000);
}

// --------------------------------------------------
// Main test runner
// --------------------------------------------------

int main() {

    std::cout << "\n================================\n";
    std::cout << "       OPTIONLAB TESTS\n";
    std::cout << "================================\n\n";

    run_test(
        "European Call Pricing",
        test_european_call
    );

    run_test(
        "European Put Pricing",
        test_european_put
    );

    run_test(
        "Put-Call Parity",
        test_put_call_parity
    );

    run_test(
        "Zero Volatility",
        test_zero_volatility
    );

    run_test(
        "Zero Maturity",
        test_zero_maturity
    );

    run_test(
        "Confidence Interval",
        test_confidence_interval
    );

    run_test(
        "Invalid Input Handling",
        test_invalid_inputs
    );

    std::cout << "\n================================\n";

    std::cout << "Tests Passed: "
              << passed_tests << "/" << total_tests
              << '\n';

    std::cout << "Tests Failed: "
              << total_tests - passed_tests
              << '\n';

    std::cout << "================================\n";

    return passed_tests == total_tests ? 0 : 1;
}









