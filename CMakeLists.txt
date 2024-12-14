cmake_minimum_required(VERSION 3.10)

# Project name
project(MyCppProject)

# Specify the C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# Automatically find all .cpp files in the current directory
file(GLOB_RECURSE SOURCES "*.cpp")

# Add the executable
add_executable(MyCppExecutable ${SOURCES})
