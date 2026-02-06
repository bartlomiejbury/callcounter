cmake_minimum_required(VERSION 3.10)
project(callcounter_lib)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(callcounter STATIC src/callcounter.cpp)

target_compile_options(callcounter INTERFACE -finstrument-functions -fno-PIE)
target_link_options(callcounter INTERFACE -no-pie)
