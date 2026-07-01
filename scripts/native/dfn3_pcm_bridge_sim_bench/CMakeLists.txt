cmake_minimum_required(VERSION 3.20)
project(dfn3_pcm_bridge_sim_bench LANGUAGES CXX)

add_executable(dfn3_pcm_bridge_sim_bench
    src/main.cpp
    src/df_capi_loader.cpp
    src/wav_io.cpp
)

target_include_directories(dfn3_pcm_bridge_sim_bench PRIVATE
    src
)

target_compile_features(dfn3_pcm_bridge_sim_bench PRIVATE cxx_std_17)

target_compile_definitions(dfn3_pcm_bridge_sim_bench PRIVATE
    WIN32_LEAN_AND_MEAN
    NOMINMAX
    _CRT_SECURE_NO_WARNINGS
)

if (MSVC)
    target_compile_options(dfn3_pcm_bridge_sim_bench PRIVATE /W4 /permissive- /EHsc)
endif()

if (WIN32)
    target_link_libraries(dfn3_pcm_bridge_sim_bench PRIVATE avrt winmm bcrypt)
endif()
