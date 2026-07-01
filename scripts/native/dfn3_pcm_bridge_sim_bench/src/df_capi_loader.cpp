#include "df_capi_loader.h"

#include <sstream>
#include <utility>

#ifndef _WIN32
#include <dlfcn.h>
#endif

namespace dfn_bench {
namespace {

std::string path_utf8(const std::filesystem::path& path) {
#if defined(_WIN32)
    return path.u8string();
#else
    return path.string();
#endif
}

#ifdef _WIN32
std::string last_windows_error(const std::string& prefix) {
    const DWORD error = GetLastError();
    if (error == 0) {
        return std::string(prefix);
    }
    LPSTR buffer = nullptr;
    const DWORD size = FormatMessageA(
        FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
        nullptr,
        error,
        MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
        reinterpret_cast<LPSTR>(&buffer),
        0,
        nullptr);
    std::ostringstream oss;
    oss << prefix << " (GetLastError=" << error;
    if (size && buffer) {
        oss << ": " << buffer;
    }
    oss << ")";
    if (buffer) {
        LocalFree(buffer);
    }
    return oss.str();
}
#endif

} // namespace

DfCapi::DfCapi(const std::filesystem::path& dll_path) {
#ifdef _WIN32
    library_ = LoadLibraryW(dll_path.wstring().c_str());
    if (!library_) {
        throw DfCapiError(last_windows_error("LoadLibraryW failed for " + path_utf8(dll_path)));
    }
#else
    library_ = dlopen(dll_path.c_str(), RTLD_NOW);
    if (!library_) {
        throw DfCapiError(std::string("dlopen failed for ") + path_utf8(dll_path) + ": " + dlerror());
    }
#endif

    df_create_ = reinterpret_cast<df_create_fn>(load_symbol("df_create"));
    df_get_frame_length_ = reinterpret_cast<df_get_frame_length_fn>(load_symbol("df_get_frame_length"));
    df_process_frame_ = reinterpret_cast<df_process_frame_fn>(load_symbol("df_process_frame"));
    df_set_post_filter_beta_ = reinterpret_cast<df_set_post_filter_beta_fn>(load_symbol("df_set_post_filter_beta"));
    df_free_ = reinterpret_cast<df_free_fn>(load_symbol("df_free"));
}

DfCapi::~DfCapi() {
#ifdef _WIN32
    if (library_) {
        FreeLibrary(library_);
    }
#else
    if (library_) {
        dlclose(library_);
    }
#endif
}

void* DfCapi::load_symbol(const char* name) const {
#ifdef _WIN32
    void* symbol = reinterpret_cast<void*>(GetProcAddress(library_, name));
    if (!symbol) {
        throw DfCapiError(last_windows_error(std::string("GetProcAddress failed for ") + name));
    }
    return symbol;
#else
    void* symbol = dlsym(library_, name);
    if (!symbol) {
        throw DfCapiError(std::string("dlsym failed for ") + name + ": " + dlerror());
    }
    return symbol;
#endif
}

void* DfCapi::create(const std::filesystem::path& model_path, float atten_lim) const {
    const std::string model = path_utf8(model_path);
    void* state = df_create_(model.c_str(), atten_lim);
    if (!state) {
        throw DfCapiError("df_create returned null for model: " + model);
    }
    return state;
}

std::size_t DfCapi::frame_length(void* state) const {
    const std::size_t frame_len = df_get_frame_length_(state);
    if (frame_len == 0) {
        throw DfCapiError("df_get_frame_length returned 0");
    }
    return frame_len;
}

float DfCapi::process_frame(void* state, const float* input, float* output) const {
    return df_process_frame_(state, input, output);
}

void DfCapi::set_post_filter_beta(void* state, float beta) const {
    df_set_post_filter_beta_(state, beta);
}

void DfCapi::free_state(void* state) const noexcept {
    if (state && df_free_) {
        df_free_(state);
    }
}

DfState::DfState(const DfCapi& api, const std::filesystem::path& model_path, float atten_lim)
    : api_(&api), state_(api.create(model_path, atten_lim)) {}

DfState::~DfState() {
    if (api_ && state_) {
        api_->free_state(state_);
    }
}

DfState::DfState(DfState&& other) noexcept : api_(other.api_), state_(other.state_) {
    other.api_ = nullptr;
    other.state_ = nullptr;
}

DfState& DfState::operator=(DfState&& other) noexcept {
    if (this != &other) {
        if (api_ && state_) {
            api_->free_state(state_);
        }
        api_ = other.api_;
        state_ = other.state_;
        other.api_ = nullptr;
        other.state_ = nullptr;
    }
    return *this;
}

} // namespace dfn_bench
