cmake_minimum_required(VERSION 3.10)

# Project name
project(MyCppProject)

# C++ standard
set(CMAKE_CXX_STANDARD 17)

# Source files
file(GLOB SOURCES "src/*.cpp")

# Add executable
add_executable(MyCppExecutable ${SOURCES})
