#pragma once

#include <cstddef>
#include <cstdint>

#include "Option.h"

namespace optionlab {

struct MonteCarloResult {
    double estimated_price;
    double standard_error;

    double confidence_interval_lower;
    double confidence_interval_upper;

    std::size_t simulations;
};

MonteCarloResult price_option_monte_carlo(
    const OptionParameters& option,
    std::size_t num_simulations,
    std::uint64_t seed = 42
);

}