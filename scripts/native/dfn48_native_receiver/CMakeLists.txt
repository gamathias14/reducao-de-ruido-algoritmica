cmake_minimum_required(VERSION 3.20)

project(dfn48_native_receiver LANGUAGES CXX)

set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")

add_executable(dfn48_native_receiver
    src/main.cpp
)

target_compile_features(dfn48_native_receiver PRIVATE cxx_std_17)

target_compile_definitions(dfn48_native_receiver PRIVATE
    WIN32_LEAN_AND_MEAN
    NOMINMAX
    _CRT_SECURE_NO_WARNINGS
    _WINSOCK_DEPRECATED_NO_WARNINGS
)

if(MSVC)
    target_compile_options(dfn48_native_receiver PRIVATE /W4 /permissive- /EHsc)
else()
    target_compile_options(dfn48_native_receiver PRIVATE -Wall -Wextra -Wpedantic)
endif()

target_link_libraries(dfn48_native_receiver PRIVATE ws2_32 bcrypt winmm)
