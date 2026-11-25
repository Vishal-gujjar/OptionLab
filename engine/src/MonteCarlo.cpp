#include "MonteCarlo.h"

#include <algorithm>
#include <cmath>
#include <random>
#include <stdexcept>

namespace optionlab {

namespace {

void validate_inputs(
    const OptionParameters& option,
    std::size_t num_simulations
) {
    if (!std::isfinite(option.spot_price) ||
        !std::isfinite(option.strike_price) ||
        !std::isfinite(option.risk_free_rate) ||
        !std::isfinite(option.dividend_yield) ||
        !std::isfinite(option.volatility) ||
        !std::isfinite(option.time_to_expiry_years)) {

        throw std::invalid_argument(
            "All option parameters must be finite."
        );
    }

    if (option.spot_price <= 0.0) {
        throw std::invalid_argument(
            "Spot price must be positive."
        );
    }

    if (option.strike_price <= 0.0) {
        throw std::invalid_argument(
            "Strike price must be positive."
        );
    }

    if (option.volatility < 0.0) {
        throw std::invalid_argument(
            "Volatility cannot be negative."
        );
    }

    if (option.time_to_expiry_years < 0.0) {
        throw std::invalid_argument(
            "Time to expiry cannot be negative."
        );
    }

    if (num_simulations < 2) {
        throw std::invalid_argument(
            "At least two simulations are required."
        );
    }

    if (option.type != OptionType::Call &&
        option.type != OptionType::Put) {

        throw std::invalid_argument(
            "Invalid option type."
        );
    }
}

}

MonteCarloResult price_option_monte_carlo(
    const OptionParameters& option,
    std::size_t num_simulations,
    std::uint64_t seed
) {
    validate_inputs(option, num_simulations);

    // Random number generator
    std::mt19937_64 generator(seed);

    // Standard normal distribution: mean = 0, standard deviation = 1
    std::normal_distribution<double> normal_distribution(
        0.0, 1.0
    );

    // Risk-neutral stock-price model
    const double drift =
        (option.risk_free_rate
         - option.dividend_yield
         - 0.5 * option.volatility * option.volatility)
        * option.time_to_expiry_years;

    const double diffusion =
        option.volatility *
        std::sqrt(option.time_to_expiry_years);

    const double discount_factor =
        std::exp(
            -option.risk_free_rate *
            option.time_to_expiry_years
        );

    // Welford's algorithm for online mean and variance
    double mean = 0.0;
    double m2 = 0.0;

    // Generate simulations
    for (std::size_t i = 0; i < num_simulations; ++i) {

        // Generate one random normal number
        const double z = normal_distribution(generator);

        // Simulate terminal stock price
        const double terminal_price =
            option.spot_price *
            std::exp(drift + diffusion * z);

        if (!std::isfinite(terminal_price)) {
            throw std::runtime_error(
                "Non-finite simulated stock price. "
                "Check the input parameters."
            );
        }

        // Calculate option payoff
        double payoff = 0.0;

        if (option.type == OptionType::Call) {

            payoff = std::max(
                terminal_price - option.strike_price,
                0.0
            );

        } else {

            payoff = std::max(
                option.strike_price - terminal_price,
                0.0
            );

        }

        // Discount future payoff to present value
        const double discounted_payoff =
            discount_factor * payoff;

        if (!std::isfinite(discounted_payoff)) {
            throw std::runtime_error(
                "Non-finite discounted payoff."
            );
        }

        // Update running mean and variance
        const double delta = discounted_payoff - mean;

        mean += delta / static_cast<double>(i + 1);

        const double delta_after =
            discounted_payoff - mean;

        m2 += delta * delta_after;
    }

    // Calculate sample variance
    const double sample_variance =
        std::max(
            0.0,
            m2 / static_cast<double>(num_simulations - 1)
        );

    // Standard error
    const double standard_error =
        std::sqrt(
            sample_variance /
            static_cast<double>(num_simulations)
        );

    // Approximate 95% confidence interval
    constexpr double z_value = 1.96;

    MonteCarloResult result;

    result.estimated_price = mean;

    result.standard_error = standard_error;

    result.confidence_interval_lower =
        mean - z_value * standard_error;

    result.confidence_interval_upper =
        mean + z_value * standard_error;

    result.simulations = num_simulations;

    return result;
}

}


