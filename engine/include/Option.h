#pragma once

namespace optionlab {

enum class OptionType {
    Call,
    Put
};

struct OptionParameters {
    double spot_price;
    double strike_price;
    double risk_free_rate;
    double dividend_yield;
    double volatility;
    double time_to_expiry_years;

    OptionType type;
};

}