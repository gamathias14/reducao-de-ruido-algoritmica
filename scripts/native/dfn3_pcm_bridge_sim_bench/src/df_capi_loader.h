#pragma once

#include <cstddef>
#include <filesystem>
#include <stdexcept>
#include <string>

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace dfn_bench {

class DfCapiError : public std::runtime_error {
public:
    explicit DfCapiError(const std::string& message) : std::runtime_error(message) {}
};

class DfCapi {
public:
    using df_create_fn = void* (*)(const char* model_path, float atten_lim);
    using df_get_frame_length_fn = std::size_t (*)(void* state);
    using df_process_frame_fn = float (*)(void* state, const float* input, float* output);
    using df_set_post_filter_beta_fn = void (*)(void* state, float beta);
    using df_free_fn = void (*)(void* state);

    explicit DfCapi(const std::filesystem::path& dll_path);
    ~DfCapi();

    DfCapi(const DfCapi&) = delete;
    DfCapi& operator=(const DfCapi&) = delete;

    DfCapi(DfCapi&&) = delete;
    DfCapi& operator=(DfCapi&&) = delete;

    void* create(const std::filesystem::path& model_path, float atten_lim) const;
    std::size_t frame_length(void* state) const;
    float process_frame(void* state, const float* input, float* output) const;
    void set_post_filter_beta(void* state, float beta) const;
    void free_state(void* state) const noexcept;

private:
#ifdef _WIN32
    HMODULE library_ = nullptr;
#else
    void* library_ = nullptr;
#endif
    df_create_fn df_create_ = nullptr;
    df_get_frame_length_fn df_get_frame_length_ = nullptr;
    df_process_frame_fn df_process_frame_ = nullptr;
    df_set_post_filter_beta_fn df_set_post_filter_beta_ = nullptr;
    df_free_fn df_free_ = nullptr;

    void* load_symbol(const char* name) const;
};

class DfState {
public:
    DfState(const DfCapi& api, const std::filesystem::path& model_path, float atten_lim);
    ~DfState();

    DfState(const DfState&) = delete;
    DfState& operator=(const DfState&) = delete;

    DfState(DfState&& other) noexcept;
    DfState& operator=(DfState&& other) noexcept;

    void* get() const noexcept { return state_; }

private:
    const DfCapi* api_ = nullptr;
    void* state_ = nullptr;
};

} // namespace dfn_bench
