cmake_minimum_required(VERSION 3.16)

project(OptionLab LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Core pricing library
add_library(optionlab_core
    engine/src/MonteCarlo.cpp
)

target_include_directories(optionlab_core
    PUBLIC engine/include
)

# Main application
add_executable(optionlab_engine
    engine/src/main.cpp
)

target_link_libraries(optionlab_engine
    PRIVATE optionlab_core
)

# Automated tests
enable_testing()

add_executable(optionlab_tests
    tests/test_montecarlo.cpp
)

target_link_libraries(optionlab_tests
    PRIVATE optionlab_core
)

# Compiler warnings
foreach(target optionlab_core optionlab_engine optionlab_tests)

    if(MSVC)

        target_compile_options(${target}
            PRIVATE /W4
        )

    else()

        target_compile_options(${target}
            PRIVATE -Wall -Wextra -Wpedantic
        )

    endif()

endforeach()

# Register tests with CTest
add_test(
    NAME MonteCarloTests
    COMMAND optionlab_tests
)



