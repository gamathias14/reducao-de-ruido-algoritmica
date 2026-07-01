#include "df_capi_loader.h"
#include "wav_io.h"

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif

#include <avrt.h>
#include <bcrypt.h>
#include <mmsystem.h>
#include <windows.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <condition_variable>
#include <cstdint>
#include <deque>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace dfn_bench {
namespace {

constexpr std::uint32_t kDfnSampleRate = 48000;
constexpr std::size_t kDfnFrameLen = 480;
constexpr std::uint32_t kBridgeSampleRate = 16000;
constexpr std::size_t kBridgeFramesPerBlock = 320;
constexpr std::size_t kBridgeBytesPerBlock = 640;
constexpr std::size_t kDfnFramesPerBridgeBlock = 2;
constexpr std::size_t kDfnSamplesPerBridgeBlock = kDfnFrameLen * kDfnFramesPerBridgeBlock;
constexpr double kBridgeBlockMs = 20.0;

std::string path_string(const std::filesystem::path& path) {
    return path.u8string();
}

std::string json_escape(const std::string& text) {
    std::ostringstream out;
    for (char c : text) {
        switch (c) {
            case '\\': out << "\\\\"; break;
            case '"': out << "\\\""; break;
            case '\n': out << "\\n"; break;
            case '\r': out << "\\r"; break;
            case '\t': out << "\\t"; break;
            default: out << c; break;
        }
    }
    return out.str();
}

class QpcClock {
public:
    QpcClock() {
        LARGE_INTEGER f{};
        if (!QueryPerformanceFrequency(&f)) {
            throw std::runtime_error("QueryPerformanceFrequency failed");
        }
        freq_ = f.QuadPart;
    }

    std::int64_t now() const {
        LARGE_INTEGER t{};
        QueryPerformanceCounter(&t);
        return t.QuadPart;
    }

    double delta_us(std::int64_t start, std::int64_t end) const {
        return (static_cast<double>(end - start) * 1'000'000.0) /
            static_cast<double>(freq_);
    }

    double frequency_hz() const { return static_cast<double>(freq_); }

private:
    std::int64_t freq_ = 0;
};

class TimePeriodScope {
public:
    TimePeriodScope() { ok_ = (timeBeginPeriod(1) == TIMERR_NOERROR); }
    ~TimePeriodScope() {
        if (ok_) timeEndPeriod(1);
    }
    bool ok() const { return ok_; }

private:
    bool ok_ = false;
};

class PriorityScope {
public:
    PriorityScope() {
        process_ok_ = SetPriorityClass(GetCurrentProcess(), HIGH_PRIORITY_CLASS) != 0;
        thread_ok_ = SetThreadPriority(GetCurrentThread(), THREAD_PRIORITY_HIGHEST) != 0;
    }
    bool process_ok() const { return process_ok_; }
    bool thread_ok() const { return thread_ok_; }

private:
    bool process_ok_ = false;
    bool thread_ok_ = false;
};

class MmcssScope {
public:
    explicit MmcssScope(const wchar_t* task_name) {
        DWORD task_index = 0;
        handle_ = AvSetMmThreadCharacteristicsW(task_name, &task_index);
    }
    ~MmcssScope() {
        if (handle_) AvRevertMmThreadCharacteristics(handle_);
    }
    bool ok() const { return handle_ != nullptr; }

private:
    HANDLE handle_ = nullptr;
};

class Sha256 {
public:
    Sha256() {
        NTSTATUS status = BCryptOpenAlgorithmProvider(
            &algorithm_, BCRYPT_SHA256_ALGORITHM, nullptr, 0);
        if (status != 0) throw std::runtime_error("BCryptOpenAlgorithmProvider failed");
        status = BCryptCreateHash(algorithm_, &hash_, nullptr, 0, nullptr, 0, 0);
        if (status != 0) throw std::runtime_error("BCryptCreateHash failed");
    }

    ~Sha256() {
        if (hash_) BCryptDestroyHash(hash_);
        if (algorithm_) BCryptCloseAlgorithmProvider(algorithm_, 0);
    }

    Sha256(const Sha256&) = delete;
    Sha256& operator=(const Sha256&) = delete;

    void update(const void* data, std::size_t size) {
        if (size == 0) return;
        const auto status = BCryptHashData(
            hash_,
            reinterpret_cast<PUCHAR>(const_cast<void*>(data)),
            static_cast<ULONG>(size),
            0);
        if (status != 0) throw std::runtime_error("BCryptHashData failed");
    }

    std::string hexdigest() {
        std::uint8_t digest[32]{};
        const auto status = BCryptFinishHash(hash_, digest, sizeof(digest), 0);
        if (status != 0) throw std::runtime_error("BCryptFinishHash failed");
        std::ostringstream out;
        out << std::hex << std::setfill('0');
        for (std::uint8_t byte : digest) {
            out << std::setw(2) << static_cast<unsigned int>(byte);
        }
        return out.str();
    }

private:
    BCRYPT_ALG_HANDLE algorithm_ = nullptr;
    BCRYPT_HASH_HANDLE hash_ = nullptr;
};

struct Args {
    std::filesystem::path dll = "tmp/t_release/x86_64-pc-windows-msvc/release/df.dll";
    std::filesystem::path model = "tmp/dfn_native/DeepFilterNet3_onnx.tar.gz";
    std::filesystem::path input = "tmp/dfn_native/wasapi_worker_bench/b3_inputs/mixed_60s_capi_input48.wav";
    std::filesystem::path output_dir = "resultados/dfn3_pcm_bridge_cpp_simulator";
    double post_filter_beta = 1.0;
    double atten_lim = 100.0;
    std::uint32_t ring_capacity_frames = 32;
    std::uint32_t prebuffer_frames = 12;
    std::uint32_t warmup_frames = 10;
    std::uint32_t bridge_target_depth = 2;
    std::uint32_t bridge_capacity_blocks = 50;
    std::uint32_t max_bridge_blocks = 0;
};

std::filesystem::path require_path(int& i, int argc, char** argv, const std::string& opt) {
    if (i + 1 >= argc) throw std::runtime_error("missing value for " + opt);
    return std::filesystem::path(argv[++i]);
}

double require_double(int& i, int argc, char** argv, const std::string& opt) {
    if (i + 1 >= argc) throw std::runtime_error("missing value for " + opt);
    return std::stod(argv[++i]);
}

std::uint32_t require_u32(int& i, int argc, char** argv, const std::string& opt) {
    if (i + 1 >= argc) throw std::runtime_error("missing value for " + opt);
    const auto value = std::stoll(argv[++i]);
    if (value < 0) throw std::runtime_error(opt + " must be >= 0");
    return static_cast<std::uint32_t>(value);
}

void print_usage(const char* exe) {
    std::cerr
        << "Usage:\n"
        << "  " << exe << " [options]\n\n"
        << "Options:\n"
        << "  --input PATH\n"
        << "  --dll PATH\n"
        << "  --model PATH\n"
        << "  --output-dir PATH\n"
        << "  --ring-capacity-frames N        default: 32\n"
        << "  --prebuffer-frames N            default: 12\n"
        << "  --warmup-frames N               default: 10\n"
        << "  --bridge-target-depth N         default: 2\n"
        << "  --bridge-capacity-blocks N      default: 50\n"
        << "  --max-bridge-blocks N           0 means full input\n"
        << "  --post-filter-beta VALUE        default: 1.0\n"
        << "  --atten-lim VALUE               default: 100.0\n";
}

Args parse_args(int argc, char** argv) {
    Args args;
    for (int i = 1; i < argc; ++i) {
        const std::string token = argv[i];
        if (token == "--help" || token == "-h") {
            print_usage(argv[0]);
            std::exit(0);
        } else if (token == "--input") {
            args.input = require_path(i, argc, argv, token);
        } else if (token == "--dll") {
            args.dll = require_path(i, argc, argv, token);
        } else if (token == "--model") {
            args.model = require_path(i, argc, argv, token);
        } else if (token == "--output-dir") {
            args.output_dir = require_path(i, argc, argv, token);
        } else if (token == "--ring-capacity-frames") {
            args.ring_capacity_frames = require_u32(i, argc, argv, token);
        } else if (token == "--prebuffer-frames") {
            args.prebuffer_frames = require_u32(i, argc, argv, token);
        } else if (token == "--warmup-frames") {
            args.warmup_frames = require_u32(i, argc, argv, token);
        } else if (token == "--bridge-target-depth") {
            args.bridge_target_depth = require_u32(i, argc, argv, token);
        } else if (token == "--bridge-capacity-blocks") {
            args.bridge_capacity_blocks = require_u32(i, argc, argv, token);
        } else if (token == "--max-bridge-blocks") {
            args.max_bridge_blocks = require_u32(i, argc, argv, token);
        } else if (token == "--post-filter-beta") {
            args.post_filter_beta = require_double(i, argc, argv, token);
        } else if (token == "--atten-lim") {
            args.atten_lim = require_double(i, argc, argv, token);
        } else if (token.rfind("--", 0) == 0) {
            throw std::runtime_error("unknown option: " + token);
        } else {
            args.input = std::filesystem::path(token);
        }
    }
    if (args.ring_capacity_frames < 4) throw std::runtime_error("ring capacity must be >= 4");
    if (args.prebuffer_frames < 1) throw std::runtime_error("prebuffer must be >= 1");
    if (args.bridge_target_depth < 1) throw std::runtime_error("bridge target depth must be >= 1");
    if (args.bridge_capacity_blocks <= args.bridge_target_depth) {
        throw std::runtime_error("bridge capacity must exceed target depth");
    }
    return args;
}

struct Stats {
    double mean = 0.0;
    double p50 = 0.0;
    double p95 = 0.0;
    double p99 = 0.0;
    double p999 = 0.0;
    double max = 0.0;
};

Stats stats_of(std::vector<double> values) {
    Stats s{};
    if (values.empty()) return s;
    std::sort(values.begin(), values.end());
    const auto pick = [&](double q) {
        if (values.size() == 1) return values[0];
        const double pos = q * static_cast<double>(values.size() - 1);
        const auto lo = static_cast<std::size_t>(std::floor(pos));
        const auto hi = static_cast<std::size_t>(std::ceil(pos));
        const double frac = pos - static_cast<double>(lo);
        return values[lo] * (1.0 - frac) + values[hi] * frac;
    };
    s.mean = std::accumulate(values.begin(), values.end(), 0.0) / static_cast<double>(values.size());
    s.p50 = pick(0.50);
    s.p95 = pick(0.95);
    s.p99 = pick(0.99);
    s.p999 = pick(0.999);
    s.max = values.back();
    return s;
}

class BlockingFloatRing {
public:
    explicit BlockingFloatRing(std::size_t capacity_samples)
        : capacity_(capacity_samples) {}

    void push_block(const float* src, std::size_t n, std::atomic<bool>& stop) {
        std::unique_lock<std::mutex> lock(mutex_);
        can_write_.wait(lock, [&] {
            return stop.load(std::memory_order_acquire) || data_.size() + n <= capacity_;
        });
        if (stop.load(std::memory_order_acquire)) return;
        for (std::size_t i = 0; i < n; ++i) data_.push_back(src[i]);
        can_read_.notify_all();
    }

    std::size_t pop_block(float* dst, std::size_t n) {
        std::lock_guard<std::mutex> lock(mutex_);
        std::size_t count = 0;
        while (count < n && !data_.empty()) {
            dst[count++] = data_.front();
            data_.pop_front();
        }
        can_write_.notify_all();
        return count;
    }

    std::size_t size() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return data_.size();
    }

    void notify_all() {
        can_write_.notify_all();
        can_read_.notify_all();
    }

private:
    std::size_t capacity_ = 0;
    mutable std::mutex mutex_;
    std::condition_variable can_write_;
    std::condition_variable can_read_;
    std::deque<float> data_;
};

struct WorkerMetric {
    std::uint64_t frame_id = 0;
    double proc_us = 0.0;
    double push_wait_us = 0.0;
    std::size_t ring_after_samples = 0;
};

struct BridgeMetric {
    std::uint64_t block_id = 0;
    double write_us = 0.0;
    double write_interval_ms = 0.0;
    std::size_t source_ring_before_samples = 0;
    std::size_t source_ring_after_samples = 0;
    std::uint32_t driver_depth_before = 0;
    std::uint32_t driver_depth_after = 0;
};

struct SimBridgeStats {
    std::uint64_t accepted = 0;
    std::uint64_t consumed = 0;
    std::uint64_t underruns = 0;
    std::uint64_t overruns = 0;
    std::uint64_t rejected = 0;
    std::uint64_t sequence_errors = 0;
    std::uint64_t last_sequence = 0;
    std::uint32_t final_depth = 0;
    std::uint32_t max_depth = 0;
    double depth_mean = 0.0;
    double consumer_lateness_p99_ms = 0.0;
    double consumer_lateness_max_ms = 0.0;
    double consumer_interval_p99_ms = 0.0;
    double consumer_interval_max_ms = 0.0;
};

class SimulatedBridge {
public:
    SimulatedBridge(std::uint32_t target_depth, std::uint32_t capacity, const QpcClock& clock)
        : target_depth_(target_depth), capacity_(capacity), clock_(clock) {}

    void advance(std::int64_t now) {
        if (!started_) return;
        while (next_consume_qpc_ <= now) {
            const double lateness_ms = clock_.delta_us(next_consume_qpc_, now) / 1000.0;
            if (!queue_.empty()) {
                queue_.pop_front();
                ++consumed_;
                if (last_consume_qpc_ != 0) {
                    consumer_intervals_ms_.push_back(
                        clock_.delta_us(last_consume_qpc_, next_consume_qpc_) / 1000.0);
                }
                last_consume_qpc_ = next_consume_qpc_;
                consumer_lateness_ms_.push_back(std::max(0.0, lateness_ms));
            } else {
                ++underruns_;
            }
            record_depth();
            next_consume_qpc_ += bridge_block_qpc();
        }
    }

    void write(std::uint64_t sequence, const std::vector<std::int16_t>& block, std::int64_t now) {
        advance(now);
        if (block.size() != kBridgeFramesPerBlock) {
            ++rejected_;
            return;
        }
        if (sequence != expected_sequence_) {
            ++sequence_errors_;
            expected_sequence_ = sequence + 1;
        } else {
            ++expected_sequence_;
        }
        if (queue_.size() >= capacity_) {
            ++overruns_;
            return;
        }
        queue_.push_back(block);
        ++accepted_;
        last_sequence_ = sequence;
        max_depth_ = std::max<std::uint32_t>(max_depth_, depth());
        record_depth();
        if (!started_ && depth() >= target_depth_) {
            started_ = true;
            next_consume_qpc_ = now + bridge_block_qpc();
        }
    }

    std::uint32_t depth() const {
        return static_cast<std::uint32_t>(queue_.size());
    }

    SimBridgeStats stats() const {
        SimBridgeStats s{};
        s.accepted = accepted_;
        s.consumed = consumed_;
        s.underruns = underruns_;
        s.overruns = overruns_;
        s.rejected = rejected_;
        s.sequence_errors = sequence_errors_;
        s.last_sequence = last_sequence_;
        s.final_depth = depth();
        s.max_depth = max_depth_;
        if (!depth_samples_.empty()) {
            s.depth_mean = std::accumulate(depth_samples_.begin(), depth_samples_.end(), 0.0) /
                static_cast<double>(depth_samples_.size());
        }
        const auto lateness = stats_of(consumer_lateness_ms_);
        const auto intervals = stats_of(consumer_intervals_ms_);
        s.consumer_lateness_p99_ms = lateness.p99;
        s.consumer_lateness_max_ms = lateness.max;
        s.consumer_interval_p99_ms = intervals.p99;
        s.consumer_interval_max_ms = intervals.max;
        return s;
    }

private:
    std::int64_t bridge_block_qpc() const {
        return static_cast<std::int64_t>(std::llround(clock_.frequency_hz() * 0.020));
    }

    void record_depth() {
        depth_samples_.push_back(static_cast<double>(depth()));
    }

    std::uint32_t target_depth_ = 0;
    std::uint32_t capacity_ = 0;
    const QpcClock& clock_;
    bool started_ = false;
    std::int64_t next_consume_qpc_ = 0;
    std::int64_t last_consume_qpc_ = 0;
    std::deque<std::vector<std::int16_t>> queue_;
    std::uint64_t expected_sequence_ = 0;
    std::uint64_t accepted_ = 0;
    std::uint64_t consumed_ = 0;
    std::uint64_t underruns_ = 0;
    std::uint64_t overruns_ = 0;
    std::uint64_t rejected_ = 0;
    std::uint64_t sequence_errors_ = 0;
    std::uint64_t last_sequence_ = 0;
    std::uint32_t max_depth_ = 0;
    std::vector<double> depth_samples_;
    std::vector<double> consumer_lateness_ms_;
    std::vector<double> consumer_intervals_ms_;
};

std::vector<float> padded_to_frame_multiple(const std::vector<float>& input) {
    const std::size_t padded_len = ((input.size() + kDfnFrameLen - 1) / kDfnFrameLen) * kDfnFrameLen;
    std::vector<float> out(padded_len, 0.0f);
    std::copy(input.begin(), input.end(), out.begin());
    return out;
}

std::int16_t float_to_i16(float value) {
    const float clamped = std::max(-1.0f, std::min(1.0f, value));
    return static_cast<std::int16_t>(std::lrint(clamped * 32767.0f));
}

std::vector<std::int16_t> downsample_48k_to_bridge_block(const std::vector<float>& source) {
    if (source.size() != kDfnSamplesPerBridgeBlock) {
        throw std::runtime_error("unexpected source block size for bridge conversion");
    }
    std::vector<std::int16_t> out(kBridgeFramesPerBlock, 0);
    for (std::size_t i = 0; i < kBridgeFramesPerBlock; ++i) {
        const std::size_t j = i * 3;
        const float mean = (source[j] + source[j + 1] + source[j + 2]) / 3.0f;
        out[i] = float_to_i16(mean);
    }
    return out;
}

void sleep_until_qpc(const QpcClock& clock, std::int64_t deadline) {
    while (true) {
        const auto now = clock.now();
        if (now >= deadline) return;
        const double remaining_us = clock.delta_us(now, deadline);
        if (remaining_us > 3000.0) {
            std::this_thread::sleep_for(std::chrono::microseconds(
                static_cast<int>(remaining_us - 1000.0)));
        } else {
            std::this_thread::yield();
        }
    }
}

void write_worker_csv(const std::filesystem::path& path, const std::vector<WorkerMetric>& rows) {
    std::filesystem::create_directories(path.parent_path());
    std::ofstream out(path, std::ios::binary);
    out << "frame_id,proc_us,push_wait_us,ring_after_samples\n";
    out << std::fixed << std::setprecision(6);
    for (const auto& r : rows) {
        out << r.frame_id << ',' << r.proc_us << ',' << r.push_wait_us << ',' << r.ring_after_samples << '\n';
    }
}

void write_bridge_csv(const std::filesystem::path& path, const std::vector<BridgeMetric>& rows) {
    std::filesystem::create_directories(path.parent_path());
    std::ofstream out(path, std::ios::binary);
    out << "block_id,write_us,write_interval_ms,source_ring_before_samples,source_ring_after_samples,driver_depth_before,driver_depth_after\n";
    out << std::fixed << std::setprecision(6);
    for (const auto& r : rows) {
        out << r.block_id << ',' << r.write_us << ',' << r.write_interval_ms << ','
            << r.source_ring_before_samples << ',' << r.source_ring_after_samples << ','
            << r.driver_depth_before << ',' << r.driver_depth_after << '\n';
    }
}

void write_bridge_wav(const std::filesystem::path& path, const std::vector<std::int16_t>& samples) {
    std::vector<float> as_float;
    as_float.reserve(samples.size());
    for (const auto s : samples) as_float.push_back(static_cast<float>(s) / 32768.0f);
    write_wav_pcm16_mono(path, kBridgeSampleRate, as_float);
}

void write_summary_json(
    const std::filesystem::path& path,
    const Args& args,
    bool time_period_ok,
    bool process_priority_ok,
    bool submit_thread_priority_ok,
    bool worker_mmcss_ok,
    const QpcClock& clock,
    std::uint64_t input_samples,
    std::uint64_t padded_samples,
    std::uint64_t expected_bridge_blocks,
    double wall_elapsed_s,
    const std::vector<WorkerMetric>& worker_rows,
    const std::vector<BridgeMetric>& bridge_rows,
    const SimBridgeStats& bridge_stats,
    const std::string& bridge_payload_sha256) {

    std::vector<double> proc_us;
    std::vector<double> push_wait_us;
    std::vector<double> write_us;
    std::vector<double> write_intervals_ms;
    for (const auto& r : worker_rows) {
        proc_us.push_back(r.proc_us);
        push_wait_us.push_back(r.push_wait_us);
    }
    for (const auto& r : bridge_rows) {
        write_us.push_back(r.write_us);
        if (r.block_id > 0) write_intervals_ms.push_back(r.write_interval_ms);
    }
    const auto proc = stats_of(proc_us);
    const auto push = stats_of(push_wait_us);
    const auto write = stats_of(write_us);
    const auto intervals = stats_of(write_intervals_ms);
    const auto over_4 = std::count_if(proc_us.begin(), proc_us.end(), [](double v) { return v > 4000.0; });
    const auto over_8 = std::count_if(proc_us.begin(), proc_us.end(), [](double v) { return v > 8000.0; });
    const auto over_10 = std::count_if(proc_us.begin(), proc_us.end(), [](double v) { return v > 10000.0; });

    std::vector<std::string> reasons;
    if (worker_rows.size() * kDfnFrameLen != padded_samples) reasons.push_back("worker_frame_count_mismatch");
    if (bridge_rows.size() != expected_bridge_blocks) reasons.push_back("bridge_write_count_mismatch");
    if (bridge_stats.accepted != expected_bridge_blocks) reasons.push_back("bridge_accept_count_mismatch");
    if (bridge_stats.underruns != 0) reasons.push_back("bridge_underruns");
    if (bridge_stats.overruns != 0) reasons.push_back("bridge_overruns");
    if (bridge_stats.rejected != 0) reasons.push_back("bridge_rejected");
    if (bridge_stats.sequence_errors != 0) reasons.push_back("bridge_sequence_errors");
    if (proc.p99 > 4000.0) reasons.push_back("worker_p99_over_4ms");
    if (proc.p999 > 8000.0) reasons.push_back("worker_p999_over_8ms");
    if (proc.max > 10000.0) reasons.push_back("worker_max_over_10ms");
    if (write.p99 > 1000.0) reasons.push_back("bridge_write_p99_over_1ms");
    if (intervals.p99 > 25.0) reasons.push_back("bridge_interval_p99_over_25ms");
    if (intervals.max > 100.0) reasons.push_back("bridge_interval_max_over_100ms");

    std::filesystem::create_directories(path.parent_path());
    std::ofstream out(path, std::ios::binary);
    out << std::fixed << std::setprecision(6);
    out << "{\n";
    out << "  \"phase\": \"R15_CPP_DFN3_PCM_BRIDGE_SIMULATOR\",\n";
    out << "  \"status\": \"" << (reasons.empty() ? "PASS" : "CHECK") << "\",\n";
    out << "  \"gate_reasons\": [";
    for (std::size_t i = 0; i < reasons.size(); ++i) {
        if (i) out << ", ";
        out << "\"" << json_escape(reasons[i]) << "\"";
    }
    out << "],\n";
    out << "  \"input\": \"" << json_escape(path_string(args.input)) << "\",\n";
    out << "  \"output_dir\": \"" << json_escape(path_string(args.output_dir)) << "\",\n";
    out << "  \"dfn_sample_rate\": " << kDfnSampleRate << ",\n";
    out << "  \"dfn_frame_samples\": " << kDfnFrameLen << ",\n";
    out << "  \"bridge_sample_rate\": " << kBridgeSampleRate << ",\n";
    out << "  \"bridge_frames_per_block\": " << kBridgeFramesPerBlock << ",\n";
    out << "  \"bridge_block_ms\": " << kBridgeBlockMs << ",\n";
    out << "  \"bridge_target_depth\": " << args.bridge_target_depth << ",\n";
    out << "  \"bridge_capacity_blocks\": " << args.bridge_capacity_blocks << ",\n";
    out << "  \"ring_capacity_frames\": " << args.ring_capacity_frames << ",\n";
    out << "  \"prebuffer_frames\": " << args.prebuffer_frames << ",\n";
    out << "  \"timeBeginPeriod_ok\": " << (time_period_ok ? "true" : "false") << ",\n";
    out << "  \"process_priority_high_ok\": " << (process_priority_ok ? "true" : "false") << ",\n";
    out << "  \"submit_thread_priority_highest_ok\": " << (submit_thread_priority_ok ? "true" : "false") << ",\n";
    out << "  \"worker_mmcss_ok\": " << (worker_mmcss_ok ? "true" : "false") << ",\n";
    out << "  \"qpc_frequency_hz\": " << clock.frequency_hz() << ",\n";
    out << "  \"input_samples\": " << input_samples << ",\n";
    out << "  \"padded_samples\": " << padded_samples << ",\n";
    out << "  \"expected_bridge_blocks\": " << expected_bridge_blocks << ",\n";
    out << "  \"wall_elapsed_s\": " << wall_elapsed_s << ",\n";
    out << "  \"bridge_payload_sha256\": \"" << bridge_payload_sha256 << "\",\n";
    out << "  \"worker_frames\": " << worker_rows.size() << ",\n";
    out << "  \"worker_proc_mean_us\": " << proc.mean << ",\n";
    out << "  \"worker_proc_p95_us\": " << proc.p95 << ",\n";
    out << "  \"worker_proc_p99_us\": " << proc.p99 << ",\n";
    out << "  \"worker_proc_p999_us\": " << proc.p999 << ",\n";
    out << "  \"worker_proc_max_us\": " << proc.max << ",\n";
    out << "  \"worker_proc_over_4ms\": " << over_4 << ",\n";
    out << "  \"worker_proc_over_8ms\": " << over_8 << ",\n";
    out << "  \"worker_proc_over_10ms\": " << over_10 << ",\n";
    out << "  \"worker_push_wait_p99_us\": " << push.p99 << ",\n";
    out << "  \"worker_push_wait_max_us\": " << push.max << ",\n";
    out << "  \"bridge_blocks_written\": " << bridge_rows.size() << ",\n";
    out << "  \"bridge_write_p99_us\": " << write.p99 << ",\n";
    out << "  \"bridge_write_max_us\": " << write.max << ",\n";
    out << "  \"bridge_write_interval_p99_ms\": " << intervals.p99 << ",\n";
    out << "  \"bridge_write_interval_max_ms\": " << intervals.max << ",\n";
    out << "  \"sim_bridge_accepted\": " << bridge_stats.accepted << ",\n";
    out << "  \"sim_bridge_consumed\": " << bridge_stats.consumed << ",\n";
    out << "  \"sim_bridge_final_depth\": " << bridge_stats.final_depth << ",\n";
    out << "  \"sim_bridge_max_depth\": " << bridge_stats.max_depth << ",\n";
    out << "  \"sim_bridge_depth_mean\": " << bridge_stats.depth_mean << ",\n";
    out << "  \"sim_bridge_underruns\": " << bridge_stats.underruns << ",\n";
    out << "  \"sim_bridge_overruns\": " << bridge_stats.overruns << ",\n";
    out << "  \"sim_bridge_rejected\": " << bridge_stats.rejected << ",\n";
    out << "  \"sim_bridge_sequence_errors\": " << bridge_stats.sequence_errors << ",\n";
    out << "  \"sim_bridge_consumer_lateness_p99_ms\": " << bridge_stats.consumer_lateness_p99_ms << ",\n";
    out << "  \"sim_bridge_consumer_lateness_max_ms\": " << bridge_stats.consumer_lateness_max_ms << ",\n";
    out << "  \"sim_bridge_consumer_interval_p99_ms\": " << bridge_stats.consumer_interval_p99_ms << ",\n";
    out << "  \"sim_bridge_consumer_interval_max_ms\": " << bridge_stats.consumer_interval_max_ms << "\n";
    out << "}\n";
}

int run(const Args& args) {
    if (!std::filesystem::exists(args.dll)) throw std::runtime_error("df.dll not found: " + path_string(args.dll));
    if (!std::filesystem::exists(args.model)) throw std::runtime_error("model not found: " + path_string(args.model));
    if (!std::filesystem::exists(args.input)) throw std::runtime_error("input not found: " + path_string(args.input));
    std::filesystem::create_directories(args.output_dir);

    const AudioMono audio = read_wav_mono_float32(args.input);
    if (audio.sample_rate != kDfnSampleRate) throw std::runtime_error("R15 expects 48 kHz input WAV");
    auto padded_input = padded_to_frame_multiple(audio.samples);
    if ((padded_input.size() / kDfnFrameLen) % kDfnFramesPerBridgeBlock != 0) {
        padded_input.resize(padded_input.size() + kDfnFrameLen, 0.0f);
    }
    std::uint64_t expected_bridge_blocks = padded_input.size() / kDfnSamplesPerBridgeBlock;
    if (args.max_bridge_blocks > 0) {
        expected_bridge_blocks = std::min<std::uint64_t>(expected_bridge_blocks, args.max_bridge_blocks);
        padded_input.resize(static_cast<std::size_t>(expected_bridge_blocks * kDfnSamplesPerBridgeBlock));
    }

    QpcClock clock;
    TimePeriodScope time_period;
    PriorityScope priority;

    DfCapi api(args.dll);
    if (args.warmup_frames > 0) {
        DfState warmup_state(api, args.model, static_cast<float>(args.atten_lim));
        api.set_post_filter_beta(warmup_state.get(), static_cast<float>(args.post_filter_beta));
        std::vector<float> z(kDfnFrameLen, 0.0f);
        std::vector<float> y(kDfnFrameLen, 0.0f);
        for (std::uint32_t i = 0; i < args.warmup_frames; ++i) {
            (void)api.process_frame(warmup_state.get(), z.data(), y.data());
        }
    }

    BlockingFloatRing ring(static_cast<std::size_t>(args.ring_capacity_frames) * kDfnFrameLen);
    std::vector<WorkerMetric> worker_metrics;
    std::vector<BridgeMetric> bridge_metrics;
    std::vector<std::int16_t> bridge_payload;
    worker_metrics.reserve(padded_input.size() / kDfnFrameLen);
    bridge_metrics.reserve(static_cast<std::size_t>(expected_bridge_blocks));
    bridge_payload.reserve(static_cast<std::size_t>(expected_bridge_blocks * kBridgeFramesPerBlock));

    std::atomic<bool> worker_done{false};
    std::atomic<bool> worker_stop{false};
    std::atomic<bool> worker_mmcss_ok{false};
    std::exception_ptr worker_error;
    std::mutex worker_error_mutex;

    DfState worker_state(api, args.model, static_cast<float>(args.atten_lim));
    api.set_post_filter_beta(worker_state.get(), static_cast<float>(args.post_filter_beta));
    if (api.frame_length(worker_state.get()) != kDfnFrameLen) {
        throw std::runtime_error("unexpected df_get_frame_length");
    }

    const auto wall_start = clock.now();
    std::thread worker([&]() {
        try {
            MmcssScope mmcss(L"Pro Audio");
            worker_mmcss_ok.store(mmcss.ok(), std::memory_order_release);
            std::vector<float> in(kDfnFrameLen, 0.0f);
            std::vector<float> out(kDfnFrameLen, 0.0f);
            for (std::size_t cursor = 0, frame_id = 0; cursor < padded_input.size(); cursor += kDfnFrameLen, ++frame_id) {
                if (worker_stop.load(std::memory_order_acquire)) break;
                std::copy_n(padded_input.data() + cursor, kDfnFrameLen, in.data());
                const auto proc_start = clock.now();
                (void)api.process_frame(worker_state.get(), in.data(), out.data());
                const auto proc_end = clock.now();
                const auto push_start = clock.now();
                ring.push_block(out.data(), kDfnFrameLen, worker_stop);
                const auto push_end = clock.now();
                WorkerMetric m{};
                m.frame_id = static_cast<std::uint64_t>(frame_id);
                m.proc_us = clock.delta_us(proc_start, proc_end);
                m.push_wait_us = clock.delta_us(push_start, push_end);
                m.ring_after_samples = ring.size();
                worker_metrics.push_back(m);
            }
        } catch (...) {
            std::lock_guard<std::mutex> lock(worker_error_mutex);
            worker_error = std::current_exception();
        }
        worker_done.store(true, std::memory_order_release);
    });

    const auto get_worker_error = [&]() -> std::exception_ptr {
        std::lock_guard<std::mutex> lock(worker_error_mutex);
        return worker_error;
    };
    const auto stop_and_join_worker = [&]() {
        worker_stop.store(true, std::memory_order_release);
        ring.notify_all();
        if (worker.joinable()) worker.join();
    };

    const std::size_t target_prebuffer = std::max<std::size_t>(
        static_cast<std::size_t>(args.prebuffer_frames) * kDfnFrameLen,
        static_cast<std::size_t>(args.bridge_target_depth) * kDfnSamplesPerBridgeBlock);
    const auto prebuffer_start = clock.now();
    while (ring.size() < target_prebuffer && !worker_done.load(std::memory_order_acquire)) {
        if (clock.delta_us(prebuffer_start, clock.now()) > 5'000'000.0) {
            stop_and_join_worker();
            throw std::runtime_error("prebuffer timeout");
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
    if (auto err = get_worker_error()) {
        stop_and_join_worker();
        std::rethrow_exception(err);
    }

    SimulatedBridge bridge(args.bridge_target_depth, args.bridge_capacity_blocks, clock);
    Sha256 payload_hash;
    std::int64_t previous_write_qpc = 0;
    std::uint64_t sent = 0;
    while (sent < expected_bridge_blocks) {
        const auto loop_now = clock.now();
        bridge.advance(loop_now);
        if (bridge.depth() >= args.bridge_target_depth) {
            sleep_until_qpc(clock, loop_now + static_cast<std::int64_t>(clock.frequency_hz() * 0.001));
            continue;
        }
        if (ring.size() < kDfnSamplesPerBridgeBlock) {
            if (worker_done.load(std::memory_order_acquire)) {
                stop_and_join_worker();
                throw std::runtime_error("source ring underflow before bridge write");
            }
            std::this_thread::yield();
            continue;
        }
        BridgeMetric metric{};
        metric.block_id = sent;
        metric.source_ring_before_samples = ring.size();
        metric.driver_depth_before = bridge.depth();
        std::vector<float> source(kDfnSamplesPerBridgeBlock, 0.0f);
        const auto popped = ring.pop_block(source.data(), source.size());
        if (popped != source.size()) throw std::runtime_error("unexpected short ring pop");
        auto pcm = downsample_48k_to_bridge_block(source);
        const auto write_start = clock.now();
        bridge.write(sent, pcm, write_start);
        const auto write_end = clock.now();
        metric.write_us = clock.delta_us(write_start, write_end);
        metric.write_interval_ms = previous_write_qpc == 0 ? 0.0 : clock.delta_us(previous_write_qpc, write_start) / 1000.0;
        previous_write_qpc = write_start;
        metric.source_ring_after_samples = ring.size();
        metric.driver_depth_after = bridge.depth();
        payload_hash.update(pcm.data(), pcm.size() * sizeof(std::int16_t));
        bridge_payload.insert(bridge_payload.end(), pcm.begin(), pcm.end());
        bridge_metrics.push_back(metric);
        ++sent;
    }

    stop_and_join_worker();
    if (auto err = get_worker_error()) std::rethrow_exception(err);
    bridge.advance(clock.now());
    const auto wall_finish = clock.now();
    const double wall_elapsed_s = clock.delta_us(wall_start, wall_finish) / 1'000'000.0;
    const auto bridge_stats = bridge.stats();
    const auto bridge_hash = payload_hash.hexdigest();

    const auto worker_csv = args.output_dir / "worker_metrics.csv";
    const auto bridge_csv = args.output_dir / "bridge_sim_metrics.csv";
    const auto bridge_wav = args.output_dir / "bridge_input_pcm16_16k.wav";
    const auto summary = args.output_dir / "summary.json";
    write_worker_csv(worker_csv, worker_metrics);
    write_bridge_csv(bridge_csv, bridge_metrics);
    write_bridge_wav(bridge_wav, bridge_payload);
    write_summary_json(
        summary,
        args,
        time_period.ok(),
        priority.process_ok(),
        priority.thread_ok(),
        worker_mmcss_ok.load(std::memory_order_acquire),
        clock,
        static_cast<std::uint64_t>(audio.samples.size()),
        static_cast<std::uint64_t>(padded_input.size()),
        expected_bridge_blocks,
        wall_elapsed_s,
        worker_metrics,
        bridge_metrics,
        bridge_stats,
        bridge_hash);

    std::vector<double> proc_values;
    for (const auto& m : worker_metrics) proc_values.push_back(m.proc_us);
    const auto proc = stats_of(proc_values);
    const bool pass = proc.p99 <= 4000.0 && proc.p999 <= 8000.0 && proc.max <= 10000.0 &&
        bridge_stats.accepted == expected_bridge_blocks && bridge_stats.underruns == 0 &&
        bridge_stats.overruns == 0 && bridge_stats.sequence_errors == 0 && bridge_stats.rejected == 0;

    std::cout << (pass ? "PASS" : "CHECK")
              << " | bridge=" << bridge_stats.accepted << "/" << expected_bridge_blocks
              << " | worker p99=" << proc.p99 / 1000.0 << " ms"
              << " | worker max=" << proc.max / 1000.0 << " ms"
              << " | underruns=" << bridge_stats.underruns
              << " | final_depth=" << bridge_stats.final_depth << "\n";
    std::cout << "summary: " << path_string(summary) << "\n";
    return pass ? 0 : 2;
}

} // namespace
} // namespace dfn_bench

int main(int argc, char** argv) {
    try {
        using namespace dfn_bench;
        const Args args = parse_args(argc, argv);
        std::cout << "DeepFilterNet3 PCM bridge simulator bench - R15\n";
        std::cout << "input: " << path_string(args.input) << "\n";
        std::cout << "output_dir: " << path_string(args.output_dir) << "\n";
        return run(args);
    } catch (const std::exception& exc) {
        std::cerr << "ERROR: " << exc.what() << "\n";
        return 1;
    }
}
