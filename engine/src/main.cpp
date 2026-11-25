#include "MonteCarlo.h"

#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <unordered_map>

using namespace optionlab;

// --------------------------------------------------
// Parse numerical input
// --------------------------------------------------

double parse_double(
    const std::string& value,
    const std::string& name
) {
    std::size_t position = 0;

    double result = std::stod(value, &position);

    if (position != value.size() || !std::isfinite(result)) {
        throw std::invalid_argument(
            "Invalid numerical value for " + name
        );
    }

    return result;
}

// --------------------------------------------------
// Parse simulation count
// --------------------------------------------------

std::size_t parse_simulations(const std::string& value) {

    if (value.empty() || value.front() == '-') {
        throw std::invalid_argument(
            "Invalid simulation count."
        );
    }

    std::size_t position = 0;

    unsigned long long result =
        std::stoull(value, &position);

    if (position != value.size() ||
        result > std::numeric_limits<std::size_t>::max()) {

        throw std::invalid_argument(
            "Simulation count is out of range."
        );
    }

    return static_cast<std::size_t>(result);
}

// --------------------------------------------------
// Parse random seed
// --------------------------------------------------

std::uint64_t parse_seed(const std::string& value) {

    if (value.empty() || value.front() == '-') {
        throw std::invalid_argument("Invalid random seed.");
    }

    std::size_t position = 0;

    unsigned long long result =
        std::stoull(value, &position);

    if (position != value.size()) {
        throw std::invalid_argument("Invalid random seed.");
    }

    return static_cast<std::uint64_t>(result);
}

// --------------------------------------------------
// Display usage information
// --------------------------------------------------

void show_help() {

    std::cout <<
        "OPTIONLAB - Monte Carlo Option Pricing\n\n"

        "Required arguments:\n"

        "  --spot          Current stock price\n"
        "  --strike        Strike price\n"
        "  --rate          Risk-free interest rate\n"
        "  --dividend      Dividend yield\n"
        "  --volatility    Annual volatility\n"
        "  --maturity      Time to expiry in years\n"
        "  --type          call or put\n"
        "  --simulations   Number of simulations\n\n"

        "Optional arguments:\n"
        "  --seed          Random seed (default: 42)\n\n"

        "Example:\n"

        "  optionlab_engine.exe "
        "--spot 271.86 "
        "--strike 280 "
        "--rate 0.06 "
        "--dividend 0 "
        "--volatility 0.321758 "
        "--maturity 1 "
        "--type call "
        "--simulations 100000 "
        "--seed 42\n";
}

// --------------------------------------------------
// Main application
// --------------------------------------------------

int main(int argc, char* argv[]) {

    try {

        if (argc == 2 && std::string(argv[1]) == "--help") {
            show_help();
            return 0;
        }

        if (argc < 2 || argc % 2 == 0) {
            throw std::invalid_argument(
                "Missing arguments. Use --help for instructions."
            );
        }

        std::unordered_map<std::string, std::string> args;

        for (int i = 1; i < argc; i += 2) {

            const std::string key = argv[i];
            const std::string value = argv[i + 1];

            if (key.size() < 3 || key.substr(0, 2) != "--") {
                throw std::invalid_argument(
                    "Invalid argument name: " + key
                );
            }

            if (args.count(key)) {
                throw std::invalid_argument(
                    "Duplicate argument: " + key
                );
            }

            args[key] = value;
        }

        // Validate supported arguments
        const std::string allowed[] = {
            "--spot",
            "--strike",
            "--rate",
            "--dividend",
            "--volatility",
            "--maturity",
            "--type",
            "--simulations",
            "--seed"
        };

        for (const auto& arg : args) {

            bool valid = false;

            for (const auto& name : allowed) {
                if (arg.first == name) {
                    valid = true;
                    break;
                }
            }

            if (!valid) {
                throw std::invalid_argument(
                    "Unknown argument: " + arg.first
                );
            }
        }

        // Required arguments
        const std::string required[] = {
            "--spot",
            "--strike",
            "--rate",
            "--dividend",
            "--volatility",
            "--maturity",
            "--type",
            "--simulations"
        };

        for (const auto& name : required) {

            if (!args.count(name)) {
                throw std::invalid_argument(
                    "Missing required argument: " + name
                );
            }
        }

        // Construct option parameters
        OptionParameters option{};

        option.spot_price =
            parse_double(args.at("--spot"), "spot");

        option.strike_price =
            parse_double(args.at("--strike"), "strike");

        option.risk_free_rate =
            parse_double(args.at("--rate"), "rate");

        option.dividend_yield =
            parse_double(args.at("--dividend"), "dividend");

        option.volatility =
            parse_double(args.at("--volatility"), "volatility");

        option.time_to_expiry_years =
            parse_double(args.at("--maturity"), "maturity");

        const std::string type = args.at("--type");

        if (type == "call") {
            option.type = OptionType::Call;
        }
        else if (type == "put") {
            option.type = OptionType::Put;
        }
        else {
            throw std::invalid_argument(
                "Option type must be call or put."
            );
        }

        const std::size_t simulations =
            parse_simulations(args.at("--simulations"));

        const std::uint64_t seed =
            args.count("--seed")
                ? parse_seed(args.at("--seed"))
                : 42;

        // Execute Monte Carlo engine
        const MonteCarloResult result =
            price_option_monte_carlo(
                option,
                simulations,
                seed
            );

        // Return machine-readable JSON
        std::cout << std::setprecision(17);

        std::cout << "{\n";

        std::cout << "  \"estimated_price\": "
                  << result.estimated_price << ",\n";

        std::cout << "  \"standard_error\": "
                  << result.standard_error << ",\n";

        std::cout << "  \"confidence_interval_lower\": "
                  << result.confidence_interval_lower << ",\n";

        std::cout << "  \"confidence_interval_upper\": "
                  << result.confidence_interval_upper << ",\n";

        std::cout << "  \"simulations\": "
                  << result.simulations << "\n";

        std::cout << "}\n";

        return 0;

    }
    catch (const std::exception& error) {

        std::cerr << "OptionLab Error: "
                  << error.what() << '\n';

        return 2;
    }
}

