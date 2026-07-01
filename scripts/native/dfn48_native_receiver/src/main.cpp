#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <bcrypt.h>
#include <mmsystem.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstring>
#include <cstdint>
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

namespace {

constexpr char kProtocolMagic[8] = {'P', 'T', 'C', 'D', 'F', 'N', '3', '\0'};
constexpr char kAckMagic[8] = {'P', 'T', 'C', 'D', 'A', 'K', '3', '\0'};
constexpr char kUdpHelloMagic[8] = {'P', 'T', 'C', 'U', 'H', 'L', 'O', '\0'};
constexpr uint32_t kProtocolVersion = 1;
constexpr uint32_t kSampleRate = 48000;
constexpr uint32_t kFramesPerBlock = 480;
constexpr uint32_t kBytesPerBlock = 960;
constexpr uint32_t kChannels = 1;
constexpr uint32_t kSampleWidthBytes = 2;
constexpr uint64_t kBlockDurationNs = 10000000;
constexpr double kBlockDurationMs = 10.0;
constexpr uint32_t kBlocksPerSecond = 100;

#pragma pack(push, 1)
struct Preamble {
    char magic[8];
    uint32_t version;
    uint32_t sample_rate;
    uint32_t frames_per_block;
    uint32_t bytes_per_block;
    uint64_t block_count;
};

struct PacketHeader {
    uint64_t sequence;
    uint64_t scheduled_offset_ns;
    uint32_t payload_bytes;
    uint32_t checksum;
};

struct Ack {
    char magic[8];
    uint64_t received;
    uint32_t lost_blocks;
    uint32_t sequence_errors;
    uint32_t crc_errors;
    uint32_t framing_errors;
};
#pragma pack(pop)

static_assert(sizeof(Preamble) == 32, "unexpected preamble size");
static_assert(sizeof(PacketHeader) == 24, "unexpected packet header size");
static_assert(sizeof(Ack) == 32, "unexpected ACK size");

struct Args {
    std::string host = "10.0.2.2";
    int port = 35280;
    std::string transport = "tcp";
    double connect_timeout_s = 180.0;
    double socket_timeout_s = 45.0;
    int blocks_per_packet = 1;
    std::filesystem::path output;
    std::filesystem::path trace;
    std::filesystem::path consumer_trace;
    std::filesystem::path progress_output;
    std::filesystem::path scheduler_trace;
    std::filesystem::path hash_output;
    std::string sink = "memory";
    bool queue_diagnostic = false;
    int queue_buffer_blocks = 20;
    bool ring_diagnostic = false;
    int ring_capacity_blocks = 12;
    int ring_prebuffer_blocks = 8;
    double ring_resync_lateness_ms = 0.0;
    std::string consumer_wait_mode = "hybrid";
    std::string consumer_thread_priority = "normal";
    std::string receiver_thread_priority = "normal";
    std::string process_priority = "normal";
    int progress_interval_blocks = 100;
    double scheduler_interval_ms = 2.0;
};

struct Row {
    uint64_t sequence = 0;
    double scheduled_offset_ms = 0.0;
    int64_t read_start_qpc_ns = 0;
    int64_t receive_qpc_ns = 0;
    double receive_offset_ms = 0.0;
    double receive_interval_ms = 0.0;
    double arrival_jitter_ms = 0.0;
    double pre_read_gap_ms = 0.0;
    int crc_ok = 0;
    int framing_error = 0;
    double packet_read_ms = 0.0;
    double header_wait_ms = 0.0;
    double payload_read_ms = 0.0;
    double crc_ms = 0.0;
    uint64_t transport_packet_sequence = 0;
    int transport_batch_index = 0;
    int transport_blocks_in_packet = 0;
    uint32_t transport_payload_bytes = 0;
};

struct PacketEvent {
    uint64_t sequence = 0;
    int64_t read_start_qpc_ns = 0;
    int64_t receive_qpc_ns = 0;
    double receive_offset_ms = 0.0;
    double receive_interval_ms = 0.0;
    double pre_read_gap_ms = 0.0;
    int transport_blocks_in_packet = 0;
    uint32_t transport_payload_bytes = 0;
    double packet_read_ms = 0.0;
    double header_wait_ms = 0.0;
    double payload_read_ms = 0.0;
    double crc_ms = 0.0;
};

struct SchedulerSample {
    uint64_t index = 0;
    int64_t qpc_ns = 0;
    double interval_ms = 0.0;
    double lateness_ms = 0.0;
};

struct ConsumerRow {
    uint64_t sequence = 0;
    int64_t consume_qpc_ns = 0;
    double consume_offset_ms = 0.0;
    double consume_interval_ms = 0.0;
    int queue_depth_before_blocks = 0;
    int queue_depth_after_blocks = 0;
    int underflow = 0;
    int recovered = 0;
    int resynced = 0;
    double playout_latency_ms = 0.0;
    uint64_t overflow_drops_total = 0;
    uint64_t recoveries_total = 0;
    uint64_t resyncs_total = 0;
    double deadline_lateness_ms = 0.0;
};

struct QueueState {
    std::mutex mutex;
    bool started = false;
    bool receiving_done = false;
    bool stop_requested = false;
    int64_t first_receive_ns = 0;
    uint64_t queue_depth_blocks = 0;
    bool ring_enabled = false;
    uint64_t ring_capacity_blocks = 0;
    size_t ring_head = 0;
    std::vector<int64_t> ring_arrival_ns;
    uint64_t overflow_drops = 0;
    uint64_t recoveries = 0;
    uint64_t resyncs = 0;
    uint64_t max_depth_blocks = 0;
    bool consumer_priority_applied = false;
    bool consumer_waitable_timer_created = false;
};

struct Stats {
    double mean = 0.0;
    double p50 = 0.0;
    double p95 = 0.0;
    double p99 = 0.0;
    double max = 0.0;
};

std::string last_wsa_error(const std::string& context) {
    std::ostringstream oss;
    oss << context << " failed with WSA error " << WSAGetLastError();
    return oss.str();
}

void ensure_parent_dir(const std::filesystem::path& path) {
    const auto parent = path.parent_path();
    if (!parent.empty()) {
        std::filesystem::create_directories(parent);
    }
}

std::string json_escape(const std::string& value) {
    std::ostringstream oss;
    for (const unsigned char c : value) {
        switch (c) {
            case '\\': oss << "\\\\"; break;
            case '"': oss << "\\\""; break;
            case '\b': oss << "\\b"; break;
            case '\f': oss << "\\f"; break;
            case '\n': oss << "\\n"; break;
            case '\r': oss << "\\r"; break;
            case '\t': oss << "\\t"; break;
            default:
                if (c < 0x20) {
                    oss << "\\u" << std::hex << std::setw(4)
                        << std::setfill('0') << static_cast<int>(c)
                        << std::dec << std::setfill(' ');
                } else {
                    oss << static_cast<char>(c);
                }
        }
    }
    return oss.str();
}

void comma(std::ostream& os, bool& first) {
    if (!first) {
        os << ",\n";
    }
    first = false;
}

void add_string(std::ostream& os, bool& first, const std::string& key,
                const std::string& value) {
    comma(os, first);
    os << "  \"" << key << "\": \"" << json_escape(value) << "\"";
}

void add_int(std::ostream& os, bool& first, const std::string& key,
             uint64_t value) {
    comma(os, first);
    os << "  \"" << key << "\": " << value;
}

void add_double(std::ostream& os, bool& first, const std::string& key,
                double value) {
    comma(os, first);
    os << "  \"" << key << "\": " << std::setprecision(15) << value;
}

Stats summarize_ms(std::vector<double> values) {
    Stats stats;
    if (values.empty()) {
        return stats;
    }
    const double sum = std::accumulate(values.begin(), values.end(), 0.0);
    std::sort(values.begin(), values.end());
    const auto percentile = [&](double p) {
        if (values.size() == 1) {
            return values.front();
        }
        const double rank = (static_cast<double>(values.size() - 1) * p) / 100.0;
        const auto lower = static_cast<size_t>(rank);
        const auto upper = std::min(lower + 1, values.size() - 1);
        const double fraction = rank - static_cast<double>(lower);
        return values[lower] * (1.0 - fraction) + values[upper] * fraction;
    };
    stats.mean = sum / static_cast<double>(values.size());
    stats.p50 = percentile(50.0);
    stats.p95 = percentile(95.0);
    stats.p99 = percentile(99.0);
    stats.max = values.back();
    return stats;
}

void add_stats(std::ostream& os, bool& first, const std::string& prefix,
               const Stats& stats) {
    add_double(os, first, prefix + "_mean", stats.mean);
    add_double(os, first, prefix + "_p50", stats.p50);
    add_double(os, first, prefix + "_p95", stats.p95);
    add_double(os, first, prefix + "_p99", stats.p99);
    add_double(os, first, prefix + "_max", stats.max);
}

int64_t qpc_ns() {
    LARGE_INTEGER counter;
    LARGE_INTEGER frequency;
    QueryPerformanceCounter(&counter);
    QueryPerformanceFrequency(&frequency);
    const long double ns =
        (static_cast<long double>(counter.QuadPart) * 1000000000.0L) /
        static_cast<long double>(frequency.QuadPart);
    return static_cast<int64_t>(ns);
}

double ns_to_ms(int64_t ns) {
    return static_cast<double>(ns) / 1000000.0;
}

uint32_t crc32(const uint8_t* data, size_t size) {
    static uint32_t table[256] = {};
    static bool initialized = false;
    if (!initialized) {
        for (uint32_t i = 0; i < 256; ++i) {
            uint32_t c = i;
            for (int bit = 0; bit < 8; ++bit) {
                c = (c & 1U) ? (0xEDB88320U ^ (c >> 1U)) : (c >> 1U);
            }
            table[i] = c;
        }
        initialized = true;
    }
    uint32_t c = 0xFFFFFFFFU;
    for (size_t i = 0; i < size; ++i) {
        c = table[(c ^ data[i]) & 0xFFU] ^ (c >> 8U);
    }
    return c ^ 0xFFFFFFFFU;
}

class Sha256 {
public:
    Sha256() {
        open_algorithm();
        create_hash();
    }

    Sha256(const Sha256&) = delete;
    Sha256& operator=(const Sha256&) = delete;

    ~Sha256() {
        if (hash_) {
            BCryptDestroyHash(hash_);
        }
        if (algorithm_) {
            BCryptCloseAlgorithmProvider(algorithm_, 0);
        }
    }

    void update(const uint8_t* data, size_t size) {
        if (size == 0) {
            return;
        }
        NTSTATUS status = BCryptHashData(
            hash_,
            const_cast<PUCHAR>(reinterpret_cast<const UCHAR*>(data)),
            static_cast<ULONG>(size),
            0);
        if (status < 0) {
            throw std::runtime_error("BCryptHashData failed");
        }
    }

    std::string hexdigest() {
        std::vector<uint8_t> digest(hash_length_);
        NTSTATUS status = BCryptFinishHash(
            hash_, digest.data(), static_cast<ULONG>(digest.size()), 0);
        if (status < 0) {
            throw std::runtime_error("BCryptFinishHash failed");
        }
        std::ostringstream oss;
        for (const uint8_t byte : digest) {
            oss << std::hex << std::setw(2) << std::setfill('0')
                << static_cast<int>(byte);
        }
        return oss.str();
    }

private:
    void open_algorithm() {
        NTSTATUS status = BCryptOpenAlgorithmProvider(
            &algorithm_, BCRYPT_SHA256_ALGORITHM, nullptr, 0);
        if (status < 0) {
            throw std::runtime_error("BCryptOpenAlgorithmProvider failed");
        }
        ULONG result_size = 0;
        DWORD cb_data = 0;
        status = BCryptGetProperty(
            algorithm_, BCRYPT_OBJECT_LENGTH,
            reinterpret_cast<PUCHAR>(&result_size),
            sizeof(result_size), &cb_data, 0);
        if (status < 0) {
            throw std::runtime_error("BCryptGetProperty object length failed");
        }
        hash_object_.resize(result_size);
        status = BCryptGetProperty(
            algorithm_, BCRYPT_HASH_LENGTH,
            reinterpret_cast<PUCHAR>(&hash_length_),
            sizeof(hash_length_), &cb_data, 0);
        if (status < 0) {
            throw std::runtime_error("BCryptGetProperty hash length failed");
        }
    }

    void create_hash() {
        NTSTATUS status = BCryptCreateHash(
            algorithm_, &hash_, hash_object_.data(),
            static_cast<ULONG>(hash_object_.size()), nullptr, 0, 0);
        if (status < 0) {
            throw std::runtime_error("BCryptCreateHash failed");
        }
    }

    BCRYPT_ALG_HANDLE algorithm_ = nullptr;
    BCRYPT_HASH_HANDLE hash_ = nullptr;
    std::vector<uint8_t> hash_object_;
    ULONG hash_length_ = 0;
};

class WsaSession {
public:
    WsaSession() {
        WSADATA data;
        if (WSAStartup(MAKEWORD(2, 2), &data) != 0) {
            throw std::runtime_error(last_wsa_error("WSAStartup"));
        }
    }
    ~WsaSession() {
        WSACleanup();
    }
};

class SchedulerMonitor {
public:
    explicit SchedulerMonitor(double interval_ms)
        : interval_ms_(interval_ms) {}

    void start() {
        timeBeginPeriod(1);
        timer_period_active_ = true;
        worker_ = std::thread([this]() { run(); });
    }

    void stop() {
        stop_.store(true);
        if (worker_.joinable()) {
            worker_.join();
        }
        if (timer_period_active_) {
            timeEndPeriod(1);
            timer_period_active_ = false;
        }
    }

    const std::vector<SchedulerSample>& samples() const {
        return samples_;
    }

    double interval_ms() const {
        return interval_ms_;
    }

private:
    void run() {
        const auto sleep_duration =
            std::chrono::duration<double, std::milli>(interval_ms_);
        const int64_t interval_ns = static_cast<int64_t>(interval_ms_ * 1000000.0);
        int64_t previous = qpc_ns();
        uint64_t index = 0;
        while (!stop_.load()) {
            std::this_thread::sleep_for(sleep_duration);
            const int64_t current = qpc_ns();
            const double interval = ns_to_ms(current - previous);
            samples_.push_back(SchedulerSample{
                index,
                current,
                interval,
                std::max(0.0, ns_to_ms(current - previous - interval_ns)),
            });
            previous = current;
            ++index;
        }
    }

    double interval_ms_ = 2.0;
    std::atomic_bool stop_{false};
    bool timer_period_active_ = false;
    std::thread worker_;
    std::vector<SchedulerSample> samples_;
};

void recv_exact(SOCKET socket, uint8_t* data, size_t size) {
    size_t received = 0;
    while (received < size) {
        const int chunk = recv(
            socket,
            reinterpret_cast<char*>(data + received),
            static_cast<int>(std::min<size_t>(size - received, 1 << 20)),
            0);
        if (chunk == 0) {
            throw std::runtime_error("stream ended before expected bytes arrived");
        }
        if (chunk == SOCKET_ERROR) {
            throw std::runtime_error(last_wsa_error("recv"));
        }
        received += static_cast<size_t>(chunk);
    }
}

void send_exact(SOCKET socket, const uint8_t* data, size_t size) {
    size_t sent = 0;
    while (sent < size) {
        const int chunk = send(
            socket,
            reinterpret_cast<const char*>(data + sent),
            static_cast<int>(std::min<size_t>(size - sent, 1 << 20)),
            0);
        if (chunk == SOCKET_ERROR) {
            throw std::runtime_error(last_wsa_error("send"));
        }
        sent += static_cast<size_t>(chunk);
    }
}

SOCKET connect_with_retry(const Args& args) {
    const auto deadline =
        std::chrono::steady_clock::now() +
        std::chrono::duration<double>(args.connect_timeout_s);
    std::string last_error = "no attempt";
    while (std::chrono::steady_clock::now() < deadline) {
        addrinfo hints{};
        hints.ai_family = AF_INET;
        hints.ai_socktype = SOCK_STREAM;
        hints.ai_protocol = IPPROTO_TCP;
        addrinfo* result = nullptr;
        const std::string port = std::to_string(args.port);
        const int gai = getaddrinfo(args.host.c_str(), port.c_str(), &hints, &result);
        if (gai != 0) {
            last_error = "getaddrinfo failed";
            std::this_thread::sleep_for(std::chrono::milliseconds(250));
            continue;
        }
        for (addrinfo* ptr = result; ptr != nullptr; ptr = ptr->ai_next) {
            SOCKET socket = WSASocket(
                ptr->ai_family, ptr->ai_socktype, ptr->ai_protocol,
                nullptr, 0, WSA_FLAG_NO_HANDLE_INHERIT);
            if (socket == INVALID_SOCKET) {
                last_error = last_wsa_error("socket");
                continue;
            }
            const int timeout_ms = static_cast<int>(args.socket_timeout_s * 1000.0);
            setsockopt(socket, SOL_SOCKET, SO_RCVTIMEO,
                       reinterpret_cast<const char*>(&timeout_ms), sizeof(timeout_ms));
            setsockopt(socket, SOL_SOCKET, SO_SNDTIMEO,
                       reinterpret_cast<const char*>(&timeout_ms), sizeof(timeout_ms));
            const BOOL no_delay = TRUE;
            setsockopt(socket, IPPROTO_TCP, TCP_NODELAY,
                       reinterpret_cast<const char*>(&no_delay), sizeof(no_delay));
            if (connect(socket, ptr->ai_addr, static_cast<int>(ptr->ai_addrlen)) == 0) {
                freeaddrinfo(result);
                return socket;
            }
            last_error = last_wsa_error("connect");
            closesocket(socket);
        }
        freeaddrinfo(result);
        std::this_thread::sleep_for(std::chrono::milliseconds(250));
    }
    throw std::runtime_error("could not connect to host: " + last_error);
}

SOCKET connect_udp_and_send_hello(const Args& args) {
    addrinfo hints{};
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_DGRAM;
    hints.ai_protocol = IPPROTO_UDP;
    addrinfo* result = nullptr;
    const std::string port = std::to_string(args.port);
    const int gai = getaddrinfo(args.host.c_str(), port.c_str(), &hints, &result);
    if (gai != 0 || result == nullptr) {
        throw std::runtime_error("getaddrinfo failed for UDP peer");
    }

    SOCKET udp_socket = INVALID_SOCKET;
    std::string last_error = "no attempt";
    for (addrinfo* ptr = result; ptr != nullptr; ptr = ptr->ai_next) {
        udp_socket = WSASocket(
            ptr->ai_family, ptr->ai_socktype, ptr->ai_protocol,
            nullptr, 0, WSA_FLAG_NO_HANDLE_INHERIT);
        if (udp_socket == INVALID_SOCKET) {
            last_error = last_wsa_error("udp socket");
            continue;
        }
        const int timeout_ms = static_cast<int>(args.socket_timeout_s * 1000.0);
        setsockopt(udp_socket, SOL_SOCKET, SO_RCVTIMEO,
                   reinterpret_cast<const char*>(&timeout_ms), sizeof(timeout_ms));
        setsockopt(udp_socket, SOL_SOCKET, SO_SNDTIMEO,
                   reinterpret_cast<const char*>(&timeout_ms), sizeof(timeout_ms));
        if (connect(udp_socket, ptr->ai_addr, static_cast<int>(ptr->ai_addrlen)) == 0) {
            const int sent = send(
                udp_socket, kUdpHelloMagic, sizeof(kUdpHelloMagic), 0);
            if (sent == static_cast<int>(sizeof(kUdpHelloMagic))) {
                freeaddrinfo(result);
                return udp_socket;
            }
            last_error = last_wsa_error("udp hello send");
        } else {
            last_error = last_wsa_error("udp connect");
        }
        closesocket(udp_socket);
        udp_socket = INVALID_SOCKET;
    }
    freeaddrinfo(result);
    throw std::runtime_error("could not prepare UDP peer: " + last_error);
}

bool valid_contract(const Preamble& preamble) {
    return std::equal(std::begin(kProtocolMagic), std::end(kProtocolMagic),
                      std::begin(preamble.magic)) &&
           preamble.version == kProtocolVersion &&
           preamble.sample_rate == kSampleRate &&
           preamble.frames_per_block == kFramesPerBlock &&
           preamble.bytes_per_block == kBytesPerBlock;
}

std::vector<double> intervals_from_rows(const std::vector<Row>& rows) {
    std::vector<double> values;
    for (size_t i = 1; i < rows.size(); ++i) {
        values.push_back(rows[i].receive_interval_ms);
    }
    return values;
}

std::vector<double> packet_intervals(const std::vector<PacketEvent>& packets) {
    std::vector<double> values;
    for (size_t i = 1; i < packets.size(); ++i) {
        values.push_back(packets[i].receive_interval_ms);
    }
    return values;
}

void write_trace(const std::filesystem::path& path, const std::vector<Row>& rows) {
    if (path.empty()) {
        return;
    }
    ensure_parent_dir(path);
    std::ofstream out(path, std::ios::binary);
    out << std::setprecision(15) << "[\n";
    for (size_t i = 0; i < rows.size(); ++i) {
        const Row& row = rows[i];
        out << "  {\n"
            << "    \"sequence\": " << row.sequence << ",\n"
            << "    \"scheduled_offset_ms\": " << row.scheduled_offset_ms << ",\n"
            << "    \"read_start_qpc_ns\": " << row.read_start_qpc_ns << ",\n"
            << "    \"receive_qpc_ns\": " << row.receive_qpc_ns << ",\n"
            << "    \"receive_offset_ms\": " << row.receive_offset_ms << ",\n"
            << "    \"receive_interval_ms\": " << row.receive_interval_ms << ",\n"
            << "    \"arrival_jitter_ms\": " << row.arrival_jitter_ms << ",\n"
            << "    \"pre_read_gap_ms\": " << row.pre_read_gap_ms << ",\n"
            << "    \"crc_ok\": " << row.crc_ok << ",\n"
            << "    \"framing_error\": " << row.framing_error << ",\n"
            << "    \"packet_read_ms\": " << row.packet_read_ms << ",\n"
            << "    \"header_wait_ms\": " << row.header_wait_ms << ",\n"
            << "    \"payload_read_ms\": " << row.payload_read_ms << ",\n"
            << "    \"crc_ms\": " << row.crc_ms << ",\n"
            << "    \"transport_packet_sequence\": " << row.transport_packet_sequence << ",\n"
            << "    \"transport_batch_index\": " << row.transport_batch_index << ",\n"
            << "    \"transport_blocks_in_packet\": " << row.transport_blocks_in_packet << ",\n"
            << "    \"transport_payload_bytes\": " << row.transport_payload_bytes << "\n"
            << "  }" << (i + 1 == rows.size() ? "\n" : ",\n");
    }
    out << "]\n";
}

void wait_until_qpc_ns(int64_t deadline_ns) {
    while (true) {
        const int64_t remaining_ns = deadline_ns - qpc_ns();
        if (remaining_ns <= 0) {
            return;
        }
        if (remaining_ns > 2000000) {
            std::this_thread::sleep_for(
                std::chrono::nanoseconds(remaining_ns - 1000000));
        }
    }
}

int thread_priority_value(const std::string& name) {
    if (name == "normal") {
        return THREAD_PRIORITY_NORMAL;
    }
    if (name == "above_normal") {
        return THREAD_PRIORITY_ABOVE_NORMAL;
    }
    if (name == "highest") {
        return THREAD_PRIORITY_HIGHEST;
    }
    if (name == "time_critical") {
        return THREAD_PRIORITY_TIME_CRITICAL;
    }
    throw std::runtime_error("invalid consumer thread priority: " + name);
}

DWORD process_priority_value(const std::string& name) {
    if (name == "normal") {
        return NORMAL_PRIORITY_CLASS;
    }
    if (name == "above_normal") {
        return ABOVE_NORMAL_PRIORITY_CLASS;
    }
    if (name == "high") {
        return HIGH_PRIORITY_CLASS;
    }
    if (name == "realtime") {
        return REALTIME_PRIORITY_CLASS;
    }
    throw std::runtime_error("invalid process priority: " + name);
}

bool apply_process_priority(const std::string& name) {
    return SetPriorityClass(GetCurrentProcess(), process_priority_value(name)) != 0;
}

void wait_until_qpc_ns_mode(int64_t deadline_ns, HANDLE wait_timer,
                            const std::string& wait_mode) {
    if (wait_mode == "hybrid") {
        wait_until_qpc_ns(deadline_ns);
        return;
    }
    while (true) {
        const int64_t remaining_ns = deadline_ns - qpc_ns();
        if (remaining_ns <= 0) {
            return;
        }
        if (wait_timer != nullptr && remaining_ns > 1000000) {
            const int64_t wait_ns = std::max<int64_t>(100000, remaining_ns - 250000);
            LARGE_INTEGER due_time{};
            due_time.QuadPart = -static_cast<LONGLONG>(wait_ns / 100);
            if (SetWaitableTimer(wait_timer, &due_time, 0, nullptr, nullptr, FALSE)) {
                WaitForSingleObject(wait_timer, INFINITE);
                continue;
            }
        }
        if (remaining_ns > 2000000) {
            std::this_thread::sleep_for(
                std::chrono::nanoseconds(remaining_ns - 1000000));
        }
    }
}

void run_consumer(QueueState& queue_state, uint64_t block_count,
                  int buffer_blocks, double resync_lateness_ms,
                  const std::string& wait_mode,
                  const std::string& thread_priority,
                  std::vector<ConsumerRow>& rows) {
    const bool priority_applied =
        SetThreadPriority(GetCurrentThread(), thread_priority_value(thread_priority)) != 0;
    HANDLE wait_timer = nullptr;
    if (wait_mode == "waitable_timer") {
        wait_timer = CreateWaitableTimerW(nullptr, TRUE, nullptr);
    }
    {
        std::lock_guard<std::mutex> lock(queue_state.mutex);
        queue_state.consumer_priority_applied = priority_applied;
        queue_state.consumer_waitable_timer_created = wait_timer != nullptr;
    }
    rows.reserve(static_cast<size_t>(block_count));
    int64_t start_ns = 0;
    while (start_ns == 0) {
        {
            std::lock_guard<std::mutex> lock(queue_state.mutex);
            if (queue_state.started) {
                start_ns = queue_state.first_receive_ns +
                    static_cast<int64_t>(buffer_blocks) *
                    static_cast<int64_t>(kBlockDurationNs);
            } else if (queue_state.receiving_done || queue_state.stop_requested) {
                if (wait_timer != nullptr) {
                    CloseHandle(wait_timer);
                }
                return;
            }
        }
        if (start_ns == 0) {
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
    }

    int64_t previous_consume_ns = 0;
    int64_t schedule_shift_ns = 0;
    for (uint64_t sequence = 0; sequence < block_count; ++sequence) {
        {
            std::lock_guard<std::mutex> lock(queue_state.mutex);
            if (queue_state.stop_requested) {
                if (wait_timer != nullptr) {
                    CloseHandle(wait_timer);
                }
                return;
            }
        }
        const int64_t deadline_ns =
            start_ns + static_cast<int64_t>(sequence * kBlockDurationNs) +
            schedule_shift_ns;
        wait_until_qpc_ns_mode(deadline_ns, wait_timer, wait_mode);
        const int64_t consume_ns = qpc_ns();
        const double deadline_lateness_ms =
            std::max(0.0, ns_to_ms(consume_ns - deadline_ns));
        const bool should_resync =
            queue_state.ring_enabled &&
            resync_lateness_ms > 0.0 &&
            deadline_lateness_ms > resync_lateness_ms;
        if (should_resync) {
            schedule_shift_ns += consume_ns - deadline_ns;
        }
        int depth_before = 0;
        int depth_after = 0;
        int underflow = 0;
        int recovered = 0;
        int resynced = should_resync ? 1 : 0;
        double playout_latency_ms = 0.0;
        uint64_t overflow_drops_total = 0;
        uint64_t recoveries_total = 0;
        uint64_t resyncs_total = 0;
        {
            std::lock_guard<std::mutex> lock(queue_state.mutex);
            if (should_resync) {
                ++queue_state.resyncs;
            }
            depth_before = static_cast<int>(queue_state.queue_depth_blocks);
            if (queue_state.ring_enabled) {
                if (queue_state.queue_depth_blocks > 0) {
                    const int64_t arrival_ns =
                        queue_state.ring_arrival_ns[queue_state.ring_head];
                    queue_state.ring_head =
                        (queue_state.ring_head + 1) %
                        static_cast<size_t>(queue_state.ring_capacity_blocks);
                    --queue_state.queue_depth_blocks;
                    playout_latency_ms = std::max(0.0, ns_to_ms(consume_ns - arrival_ns));
                } else {
                    underflow = 1;
                    recovered = 1;
                    ++queue_state.recoveries;
                }
            } else {
                if (queue_state.queue_depth_blocks > 0) {
                    --queue_state.queue_depth_blocks;
                } else {
                    underflow = 1;
                    recovered = 1;
                }
            }
            depth_after = static_cast<int>(queue_state.queue_depth_blocks);
            overflow_drops_total = queue_state.overflow_drops;
            recoveries_total = queue_state.recoveries;
            resyncs_total = queue_state.resyncs;
        }
        rows.push_back(ConsumerRow{
            sequence,
            consume_ns,
            ns_to_ms(consume_ns - start_ns),
            previous_consume_ns == 0
                ? 0.0
                : ns_to_ms(consume_ns - previous_consume_ns),
            depth_before,
            depth_after,
            underflow,
            recovered,
            resynced,
            playout_latency_ms,
            overflow_drops_total,
            recoveries_total,
            resyncs_total,
            deadline_lateness_ms,
        });
        previous_consume_ns = consume_ns;
    }
    if (wait_timer != nullptr) {
        CloseHandle(wait_timer);
    }
}

void write_consumer_trace(const std::filesystem::path& path,
                          const std::vector<ConsumerRow>& rows) {
    if (path.empty()) {
        return;
    }
    ensure_parent_dir(path);
    std::ofstream out(path, std::ios::binary);
    out << std::setprecision(15) << "[\n";
    for (size_t i = 0; i < rows.size(); ++i) {
        const ConsumerRow& row = rows[i];
        out << "  {\n"
            << "    \"sequence\": " << row.sequence << ",\n"
            << "    \"consume_qpc_ns\": " << row.consume_qpc_ns << ",\n"
            << "    \"consume_offset_ms\": " << row.consume_offset_ms << ",\n"
            << "    \"consume_interval_ms\": " << row.consume_interval_ms << ",\n"
            << "    \"queue_depth_before_blocks\": " << row.queue_depth_before_blocks << ",\n"
            << "    \"queue_depth_after_blocks\": " << row.queue_depth_after_blocks << ",\n"
            << "    \"underflow\": " << row.underflow << ",\n"
            << "    \"recovered\": " << row.recovered << ",\n"
            << "    \"resynced\": " << row.resynced << ",\n"
            << "    \"playout_latency_ms\": " << row.playout_latency_ms << ",\n"
            << "    \"overflow_drops_total\": " << row.overflow_drops_total << ",\n"
            << "    \"recoveries_total\": " << row.recoveries_total << ",\n"
            << "    \"resyncs_total\": " << row.resyncs_total << ",\n"
            << "    \"deadline_lateness_ms\": " << row.deadline_lateness_ms << "\n"
            << "  }" << (i + 1 == rows.size() ? "\n" : ",\n");
    }
    out << "]\n";
}

void write_progress(const Args& args, const std::string& stage,
                    uint64_t expected_blocks, uint64_t received_blocks,
                    uint64_t expected_sequence, uint64_t lost_blocks,
                    uint32_t sequence_errors, uint32_t crc_errors,
                    uint32_t framing_errors, QueueState* queue_state,
                    size_t consumer_rows) {
    if (args.progress_output.empty()) {
        return;
    }
    ensure_parent_dir(args.progress_output);
    uint64_t queue_depth = 0;
    uint64_t ring_capacity = 0;
    uint64_t overflow_drops = 0;
    uint64_t recoveries = 0;
    uint64_t resyncs = 0;
    uint64_t max_depth = 0;
    bool consumer_priority_applied = false;
    bool consumer_waitable_timer_created = false;
    bool consumer_started = false;
    bool receiving_done = false;
    if (queue_state != nullptr) {
        std::lock_guard<std::mutex> lock(queue_state->mutex);
        queue_depth = queue_state->queue_depth_blocks;
        ring_capacity = queue_state->ring_capacity_blocks;
        overflow_drops = queue_state->overflow_drops;
        recoveries = queue_state->recoveries;
        resyncs = queue_state->resyncs;
        max_depth = queue_state->max_depth_blocks;
        consumer_priority_applied = queue_state->consumer_priority_applied;
        consumer_waitable_timer_created = queue_state->consumer_waitable_timer_created;
        consumer_started = queue_state->started;
        receiving_done = queue_state->receiving_done;
    }
    const auto tmp = args.progress_output.string() + ".tmp";
    const std::string status =
        stage == "completed" ? "completed" :
        stage == "failed" ? "failed" :
        "running";
    {
        std::ofstream out(tmp, std::ios::binary);
        out << "{\n"
            << "  \"status\": \"" << status << "\",\n"
            << "  \"stage\": \"" << json_escape(stage) << "\",\n"
            << "  \"expected_blocks\": " << expected_blocks << ",\n"
            << "  \"received_blocks\": " << received_blocks << ",\n"
            << "  \"expected_sequence\": " << expected_sequence << ",\n"
            << "  \"lost_blocks\": " << lost_blocks << ",\n"
            << "  \"sequence_errors\": " << sequence_errors << ",\n"
            << "  \"crc_errors\": " << crc_errors << ",\n"
            << "  \"framing_errors\": " << framing_errors << ",\n"
            << "  \"queue_diagnostic\": " << (args.queue_diagnostic ? "true" : "false") << ",\n"
            << "  \"queue_buffer_blocks\": " << args.queue_buffer_blocks << ",\n"
            << "  \"ring_diagnostic\": " << (args.ring_diagnostic ? "true" : "false") << ",\n"
            << "  \"ring_capacity_blocks\": " << ring_capacity << ",\n"
            << "  \"ring_prebuffer_blocks\": " << args.ring_prebuffer_blocks << ",\n"
            << "  \"ring_resync_lateness_ms\": " << args.ring_resync_lateness_ms << ",\n"
            << "  \"consumer_wait_mode\": \"" << json_escape(args.consumer_wait_mode) << "\",\n"
            << "  \"consumer_thread_priority\": \"" << json_escape(args.consumer_thread_priority) << "\",\n"
            << "  \"receiver_thread_priority\": \"" << json_escape(args.receiver_thread_priority) << "\",\n"
            << "  \"process_priority\": \"" << json_escape(args.process_priority) << "\",\n"
            << "  \"process_priority_applied\": true,\n"
            << "  \"receiver_thread_priority_applied\": true,\n"
            << "  \"consumer_priority_applied\": " << (consumer_priority_applied ? "true" : "false") << ",\n"
            << "  \"consumer_waitable_timer_created\": " << (consumer_waitable_timer_created ? "true" : "false") << ",\n"
            << "  \"queue_depth_blocks\": " << queue_depth << ",\n"
            << "  \"queue_depth_limit_blocks\": " << ring_capacity << ",\n"
            << "  \"overflow_drops\": " << overflow_drops << ",\n"
            << "  \"recoveries\": " << recoveries << ",\n"
            << "  \"resyncs\": " << resyncs << ",\n"
            << "  \"max_depth_blocks\": " << max_depth << ",\n"
            << "  \"consumer_started\": " << (consumer_started ? "true" : "false") << ",\n"
            << "  \"receiving_done\": " << (receiving_done ? "true" : "false") << ",\n"
            << "  \"consumer_rows\": " << consumer_rows << "\n"
            << "}\n";
    }
    std::error_code ec;
    std::filesystem::rename(tmp, args.progress_output, ec);
    if (ec) {
        std::filesystem::copy_file(
            tmp,
            args.progress_output,
            std::filesystem::copy_options::overwrite_existing,
            ec);
        std::filesystem::remove(tmp, ec);
    }
}

Stats scheduler_stats(const std::vector<SchedulerSample>& samples,
                      bool lateness) {
    std::vector<double> values;
    values.reserve(samples.size());
    for (const auto& sample : samples) {
        values.push_back(lateness ? sample.lateness_ms : sample.interval_ms);
    }
    return summarize_ms(std::move(values));
}

std::string scheduler_summary_json(const SchedulerMonitor& scheduler,
                                   const std::string& indent) {
    const auto& samples = scheduler.samples();
    const Stats interval_stats = scheduler_stats(samples, false);
    const Stats lateness_stats = scheduler_stats(samples, true);
    const auto count_over = [&](double threshold) {
        return static_cast<uint64_t>(std::count_if(
            samples.begin(), samples.end(),
            [threshold](const SchedulerSample& sample) {
                return sample.interval_ms > threshold;
            }));
    };
    std::ostringstream out;
    bool first = true;
    out << "{\n";
    auto add = [&](const std::string& key, double value) {
        if (!first) out << ",\n";
        first = false;
        out << indent << "  \"" << key << "\": " << std::setprecision(15) << value;
    };
    auto add_u = [&](const std::string& key, uint64_t value) {
        if (!first) out << ",\n";
        first = false;
        out << indent << "  \"" << key << "\": " << value;
    };
    add("interval_ms", scheduler.interval_ms());
    add_u("sample_count", static_cast<uint64_t>(samples.size()));
    add_u("gaps_over_10ms", count_over(10.0));
    add_u("gaps_over_30ms", count_over(30.0));
    add_u("gaps_over_100ms", count_over(100.0));
    add("scheduler_interval_ms_mean", interval_stats.mean);
    add("scheduler_interval_ms_p50", interval_stats.p50);
    add("scheduler_interval_ms_p95", interval_stats.p95);
    add("scheduler_interval_ms_p99", interval_stats.p99);
    add("scheduler_interval_ms_max", interval_stats.max);
    add("scheduler_lateness_ms_mean", lateness_stats.mean);
    add("scheduler_lateness_ms_p50", lateness_stats.p50);
    add("scheduler_lateness_ms_p95", lateness_stats.p95);
    add("scheduler_lateness_ms_p99", lateness_stats.p99);
    add("scheduler_lateness_ms_max", lateness_stats.max);
    out << "\n" << indent << "}";
    return out.str();
}

void write_scheduler_trace(const std::filesystem::path& path,
                           const SchedulerMonitor& scheduler) {
    if (path.empty()) {
        return;
    }
    ensure_parent_dir(path);
    std::ofstream out(path, std::ios::binary);
    out << std::setprecision(15)
        << "{\n"
        << "  \"status\": \"completed\",\n"
        << "  \"summary\": " << scheduler_summary_json(scheduler, "  ") << ",\n"
        << "  \"samples\": [\n";
    const auto& samples = scheduler.samples();
    for (size_t i = 0; i < samples.size(); ++i) {
        const auto& sample = samples[i];
        out << "    {\n"
            << "      \"index\": " << sample.index << ",\n"
            << "      \"qpc_ns\": " << sample.qpc_ns << ",\n"
            << "      \"interval_ms\": " << sample.interval_ms << ",\n"
            << "      \"lateness_ms\": " << sample.lateness_ms << "\n"
            << "    }" << (i + 1 == samples.size() ? "\n" : ",\n");
    }
    out << "  ]\n}\n";
}

void write_hash_output(const std::filesystem::path& path, const Args& args,
                       const std::string& payload_hash,
                       uint64_t received_blocks,
                       size_t packet_count) {
    if (path.empty()) {
        return;
    }
    ensure_parent_dir(path);
    std::ofstream out(path, std::ios::binary);
    out << std::setprecision(15)
        << "{\n"
        << "  \"status\": \"completed\",\n"
        << "  \"sink\": \"" << json_escape(args.sink) << "\",\n"
        << "  \"payload_sha256\": \"" << payload_hash << "\",\n"
        << "  \"block_count\": " << received_blocks << ",\n"
        << "  \"sample_count\": " << (received_blocks * kFramesPerBlock) << ",\n"
        << "  \"duration_s\": " << (static_cast<double>(received_blocks) / kBlocksPerSecond) << ",\n"
        << "  \"transport_protocol\": \"" << json_escape(args.transport) << "\",\n"
        << "  \"transport_blocks_per_packet\": " << args.blocks_per_packet << ",\n"
        << "  \"observed_transport_packet_count\": " << packet_count << "\n"
        << "}\n";
}

void write_failed_output(const std::filesystem::path& path, const std::string& error) {
    if (path.empty()) {
        return;
    }
    ensure_parent_dir(path);
    std::ofstream out(path, std::ios::binary);
    out << "{\n"
        << "  \"status\": \"failed\",\n"
        << "  \"role\": \"client\",\n"
        << "  \"error\": \"" << json_escape(error) << "\"\n"
        << "}\n";
}

void write_summary(const std::filesystem::path& path, const Args& args,
                   const Preamble& contract, uint64_t received_blocks,
                   uint64_t lost_blocks, uint32_t sequence_errors,
                   uint32_t crc_errors, uint32_t framing_errors,
                   const std::string& payload_hash,
                   const std::vector<Row>& rows,
                   const std::vector<PacketEvent>& packet_events,
                   const std::vector<ConsumerRow>& consumer_rows,
                   const SchedulerMonitor* scheduler) {
    ensure_parent_dir(path);
    std::vector<double> intervals = intervals_from_rows(rows);
    std::vector<double> packet_int = packet_intervals(packet_events);
    std::vector<double> offsets;
    std::vector<double> jitter;
    std::vector<double> phase_error;
    std::vector<double> packet_read;
    std::vector<double> pre_read_gap;
    std::vector<double> header_wait;
    std::vector<double> payload_read;
    std::vector<double> crc_times;
    std::vector<double> packet_header_wait;
    std::vector<double> packet_payload_read;
    std::vector<double> consumer_intervals;
    std::vector<double> consumer_lateness;
    std::vector<double> consumer_playout_latency;
    offsets.reserve(rows.size());
    phase_error.reserve(rows.size());
    packet_read.reserve(rows.size());
    header_wait.reserve(rows.size());
    payload_read.reserve(rows.size());
    crc_times.reserve(rows.size());
    for (size_t i = 0; i < rows.size(); ++i) {
        const auto& row = rows[i];
        offsets.push_back(row.receive_offset_ms);
        phase_error.push_back(row.receive_offset_ms - row.scheduled_offset_ms);
        packet_read.push_back(row.packet_read_ms);
        pre_read_gap.push_back(row.pre_read_gap_ms);
        header_wait.push_back(row.header_wait_ms);
        payload_read.push_back(row.payload_read_ms);
        crc_times.push_back(row.crc_ms);
        if (i > 0) {
            jitter.push_back(row.arrival_jitter_ms);
        }
    }
    for (const auto& packet : packet_events) {
        packet_header_wait.push_back(packet.header_wait_ms);
        packet_payload_read.push_back(packet.payload_read_ms);
    }
    uint64_t consumer_underflows = 0;
    uint64_t consumer_recoveries = 0;
    uint64_t consumer_resyncs = 0;
    uint64_t producer_overflow_drops = 0;
    uint64_t consumer_min_depth = 0;
    uint64_t consumer_max_depth = 0;
    double consumer_depth_sum = 0.0;
    if (!consumer_rows.empty()) {
        consumer_min_depth = static_cast<uint64_t>(
            std::max(0, consumer_rows.front().queue_depth_before_blocks));
        for (size_t i = 0; i < consumer_rows.size(); ++i) {
            const auto& row = consumer_rows[i];
            consumer_underflows += static_cast<uint64_t>(row.underflow != 0);
            consumer_recoveries += static_cast<uint64_t>(row.recovered != 0);
            consumer_resyncs += static_cast<uint64_t>(row.resynced != 0);
            producer_overflow_drops =
                std::max(producer_overflow_drops, row.overflow_drops_total);
            const uint64_t depth = static_cast<uint64_t>(
                std::max(0, row.queue_depth_before_blocks));
            consumer_min_depth = std::min(consumer_min_depth, depth);
            consumer_max_depth = std::max(consumer_max_depth, depth);
            consumer_depth_sum += static_cast<double>(depth);
            if (i > 0) {
                consumer_intervals.push_back(row.consume_interval_ms);
            }
            consumer_lateness.push_back(row.deadline_lateness_ms);
            if (!row.recovered) {
                consumer_playout_latency.push_back(row.playout_latency_ms);
            }
        }
    }
    const double audio_duration_s =
        static_cast<double>(rows.size()) / static_cast<double>(kBlocksPerSecond);
    const double covered_duration_s = offsets.empty()
        ? 0.0
        : (offsets.back() + kBlockDurationMs) / 1000.0;
    const uint64_t max_blocks_per_packet = packet_events.empty()
        ? 0
        : static_cast<uint64_t>(std::max_element(
              packet_events.begin(), packet_events.end(),
              [](const PacketEvent& a, const PacketEvent& b) {
                  return a.transport_blocks_in_packet < b.transport_blocks_in_packet;
              })->transport_blocks_in_packet);
    const auto count_interval = [&](double threshold, bool greater) {
        return static_cast<uint64_t>(std::count_if(
            intervals.begin(), intervals.end(),
            [threshold, greater](double value) {
                return greater ? value > threshold : value < threshold;
            }));
    };

    std::ofstream out(path, std::ios::binary);
    bool first = true;
    out << std::setprecision(15) << "{\n";
    add_string(out, first, "status", "completed");
    add_string(out, first, "role", "client");
    add_string(out, first, "transport", args.transport);
    comma(out, first);
    out << "  \"contract\": {\n"
        << "    \"sample_rate\": " << kSampleRate << ",\n"
        << "    \"channels\": " << kChannels << ",\n"
        << "    \"format\": \"pcm_s16le\",\n"
        << "    \"frames_per_block\": " << kFramesPerBlock << ",\n"
        << "    \"bytes_per_block\": " << kBytesPerBlock << ",\n"
        << "    \"block_duration_ms\": " << kBlockDurationMs << ",\n"
        << "    \"blocks_per_second\": " << kBlocksPerSecond << ",\n"
        << "    \"transport_blocks_per_packet\": " << args.blocks_per_packet << ",\n"
        << "    \"transport_protocol\": \"" << json_escape(args.transport) << "\"\n"
        << "  }";
    add_int(out, first, "expected_block_count", contract.block_count);
    add_int(out, first, "block_count", received_blocks);
    add_int(out, first, "sample_count", received_blocks * kFramesPerBlock);
    add_double(out, first, "duration_s",
               static_cast<double>(received_blocks) / kBlocksPerSecond);
    add_string(out, first, "transport_protocol", args.transport);
    add_int(out, first, "transport_blocks_per_packet", args.blocks_per_packet);
    add_int(out, first, "observed_transport_packet_count",
            static_cast<uint64_t>(packet_events.size()));
    add_int(out, first, "observed_max_blocks_per_packet", max_blocks_per_packet);
    add_int(out, first, "lost_blocks", lost_blocks);
    add_int(out, first, "sequence_errors", sequence_errors);
    add_int(out, first, "crc_errors", crc_errors);
    add_int(out, first, "framing_errors", framing_errors);
    add_string(out, first, "received_payload_sha256", payload_hash);
    add_string(out, first, "sink", args.sink);
    comma(out, first);
    out << "  \"receiver_queue\": {\n"
        << "    \"type\": \""
        << (args.ring_diagnostic ? "ring_buffer_diagnostic" :
            (args.queue_diagnostic ? "diagnostic_consumer" : "none")) << "\",\n"
        << "    \"transport_thread\": \"native_receive\",\n"
        << "    \"consumer_enabled\": " << ((args.queue_diagnostic || args.ring_diagnostic) ? "true" : "false") << ",\n"
        << "    \"prebuffer_blocks\": "
        << (args.ring_diagnostic ? args.ring_prebuffer_blocks :
            (args.queue_diagnostic ? args.queue_buffer_blocks : 0)) << ",\n"
        << "    \"prebuffer_ms\": "
        << (args.ring_diagnostic ? args.ring_prebuffer_blocks * kBlockDurationMs :
            (args.queue_diagnostic ? args.queue_buffer_blocks * kBlockDurationMs : 0.0)) << ",\n"
        << "    \"capacity_blocks\": " << (args.ring_diagnostic ? args.ring_capacity_blocks : 0) << ",\n"
        << "    \"latency_cap_ms\": " << (args.ring_diagnostic ? args.ring_capacity_blocks * kBlockDurationMs : 0.0) << ",\n"
        << "    \"overflow_policy\": \"" << (args.ring_diagnostic ? "drop_oldest" : "none") << "\",\n"
        << "    \"underflow_recovery_policy\": \"" << (args.ring_diagnostic ? "recover_with_silence" : "count_only") << "\",\n"
        << "    \"consumer_resync_policy\": \""
        << (args.ring_diagnostic && args.ring_resync_lateness_ms > 0.0
            ? "shift_schedule_to_now"
            : "none") << "\",\n"
        << "    \"consumer_resync_lateness_threshold_ms\": "
        << (args.ring_diagnostic ? args.ring_resync_lateness_ms : 0.0) << ",\n"
        << "    \"consumer_wait_mode\": \"" << json_escape(args.consumer_wait_mode) << "\",\n"
        << "    \"consumer_thread_priority\": \"" << json_escape(args.consumer_thread_priority) << "\",\n"
        << "    \"receiver_thread_priority\": \"" << json_escape(args.receiver_thread_priority) << "\",\n"
        << "    \"process_priority\": \"" << json_escape(args.process_priority) << "\",\n"
        << "    \"process_priority_applied\": true,\n"
        << "    \"receiver_thread_priority_applied\": true,\n"
        << "    \"consumer_priority_requested\": "
        << ((args.queue_diagnostic || args.ring_diagnostic) ? "true" : "false") << ",\n"
        << "    \"consumer_waitable_timer_requested\": "
        << ((args.consumer_wait_mode == "waitable_timer") ? "true" : "false") << ",\n"
        << "    \"consumer_checked_blocks\": " << consumer_rows.size() << ",\n"
        << "    \"consumer_underflows\": " << consumer_underflows << ",\n"
        << "    \"consumer_underflow_rate\": "
        << (consumer_rows.empty() ? 0.0 : static_cast<double>(consumer_underflows) / consumer_rows.size()) << ",\n"
        << "    \"consumer_recoveries\": " << consumer_recoveries << ",\n"
        << "    \"consumer_resyncs\": " << consumer_resyncs << ",\n"
        << "    \"consumer_resync_rate\": "
        << (consumer_rows.empty() ? 0.0 : static_cast<double>(consumer_resyncs) / consumer_rows.size()) << ",\n"
        << "    \"producer_overflow_drops\": " << producer_overflow_drops << ",\n"
        << "    \"min_depth_before_consume_blocks\": " << consumer_min_depth << ",\n"
        << "    \"mean_depth_before_consume_blocks\": "
        << (consumer_rows.empty() ? 0.0 : consumer_depth_sum / consumer_rows.size()) << ",\n"
        << "    \"max_depth_before_consume_blocks\": " << consumer_max_depth << ",\n"
        << "    \"note\": \"native client hashes each "
        << json_escape(args.transport) << " packet in memory; "
        << (args.ring_diagnostic
            ? "ring consumer bounds queued latency with explicit drop/recovery telemetry"
            : "diagnostic consumer measures playout viability") << "\"\n"
        << "  }";
    add_stats(out, first, "receive_interval_ms", summarize_ms(intervals));
    add_double(out, first, "block_rate_hz",
               audio_duration_s == 0.0 ? 0.0 : rows.size() / audio_duration_s);
    add_double(out, first, "audio_duration_s", audio_duration_s);
    add_double(out, first, "covered_duration_s", covered_duration_s);
    add_double(out, first, "audio_to_covered_ratio",
               covered_duration_s == 0.0 ? 0.0 : audio_duration_s / covered_duration_s);
    add_int(out, first, "interval_stalls_over_20ms", count_interval(20.0, true));
    add_int(out, first, "interval_stalls_over_50ms", count_interval(50.0, true));
    add_int(out, first, "interval_stalls_over_100ms", count_interval(100.0, true));
    add_int(out, first, "interval_bursts_under_5ms", count_interval(5.0, false));
    add_stats(out, first, "arrival_jitter_ms", summarize_ms(jitter));
    add_stats(out, first, "receive_phase_error_ms", summarize_ms(phase_error));
    add_stats(out, first, "packet_read_ms", summarize_ms(packet_read));
    add_stats(out, first, "pre_read_gap_ms", summarize_ms(pre_read_gap));
    add_stats(out, first, "header_wait_ms", summarize_ms(header_wait));
    add_stats(out, first, "payload_read_ms", summarize_ms(payload_read));
    add_stats(out, first, "crc_ms", summarize_ms(crc_times));
    add_stats(out, first, "packet_receive_interval_ms", summarize_ms(packet_int));
    add_stats(out, first, "packet_header_wait_ms", summarize_ms(packet_header_wait));
    add_stats(out, first, "packet_payload_read_ms", summarize_ms(packet_payload_read));
    if (args.queue_diagnostic) {
        add_stats(out, first, "consumer_interval_ms", summarize_ms(consumer_intervals));
        add_stats(out, first, "consumer_deadline_lateness_ms", summarize_ms(consumer_lateness));
    }
    if (args.ring_diagnostic) {
        add_stats(out, first, "consumer_interval_ms", summarize_ms(consumer_intervals));
        add_stats(out, first, "consumer_deadline_lateness_ms", summarize_ms(consumer_lateness));
        add_stats(out, first, "ring_playout_latency_ms", summarize_ms(consumer_playout_latency));
    }
    if (scheduler != nullptr) {
        comma(out, first);
        out << "  \"scheduler_probe\": " << scheduler_summary_json(*scheduler, "  ");
    }
    out << "\n}\n";
}

Args parse_args(int argc, char** argv) {
    Args args;
    int index = 1;
    if (index < argc && std::string(argv[index]) == "client") {
        ++index;
    }
    while (index < argc) {
        const std::string key = argv[index++];
        const auto need_value = [&]() -> std::string {
            if (index >= argc) {
                throw std::runtime_error("missing value for " + key);
            }
            return argv[index++];
        };
        if (key == "--host") {
            args.host = need_value();
        } else if (key == "--port") {
            args.port = std::stoi(need_value());
        } else if (key == "--transport") {
            args.transport = need_value();
        } else if (key == "--connect-timeout") {
            args.connect_timeout_s = std::stod(need_value());
        } else if (key == "--socket-timeout") {
            args.socket_timeout_s = std::stod(need_value());
        } else if (key == "--blocks-per-packet") {
            args.blocks_per_packet = std::stoi(need_value());
        } else if (key == "--output") {
            args.output = need_value();
        } else if (key == "--trace") {
            args.trace = need_value();
        } else if (key == "--consumer-trace") {
            args.consumer_trace = need_value();
        } else if (key == "--progress-output") {
            args.progress_output = need_value();
        } else if (key == "--progress-interval-blocks") {
            args.progress_interval_blocks = std::stoi(need_value());
        } else if (key == "--scheduler-trace") {
            args.scheduler_trace = need_value();
        } else if (key == "--scheduler-interval-ms") {
            args.scheduler_interval_ms = std::stod(need_value());
        } else if (key == "--queue-diagnostic") {
            args.queue_diagnostic = true;
        } else if (key == "--queue-buffer-blocks") {
            args.queue_buffer_blocks = std::stoi(need_value());
        } else if (key == "--ring-diagnostic") {
            args.ring_diagnostic = true;
        } else if (key == "--ring-capacity-blocks") {
            args.ring_capacity_blocks = std::stoi(need_value());
        } else if (key == "--ring-prebuffer-blocks") {
            args.ring_prebuffer_blocks = std::stoi(need_value());
        } else if (key == "--ring-resync-lateness-ms") {
            args.ring_resync_lateness_ms = std::stod(need_value());
        } else if (key == "--consumer-wait-mode") {
            args.consumer_wait_mode = need_value();
        } else if (key == "--consumer-thread-priority") {
            args.consumer_thread_priority = need_value();
        } else if (key == "--receiver-thread-priority") {
            args.receiver_thread_priority = need_value();
        } else if (key == "--process-priority") {
            args.process_priority = need_value();
        } else if (key == "--sink") {
            args.sink = need_value();
        } else if (key == "--hash-output") {
            args.hash_output = need_value();
        } else {
            throw std::runtime_error("unknown argument: " + key);
        }
    }
    if (args.output.empty()) {
        throw std::runtime_error("--output is required");
    }
    if (args.blocks_per_packet < 1 || args.blocks_per_packet > 16) {
        throw std::runtime_error("--blocks-per-packet must be between 1 and 16");
    }
    if (args.transport != "tcp" && args.transport != "udp") {
        throw std::runtime_error("--transport must be tcp or udp");
    }
    if (args.queue_buffer_blocks < 0 || args.queue_buffer_blocks > 1000) {
        throw std::runtime_error("--queue-buffer-blocks must be between 0 and 1000");
    }
    if (args.ring_capacity_blocks < 1 || args.ring_capacity_blocks > 1000) {
        throw std::runtime_error("--ring-capacity-blocks must be between 1 and 1000");
    }
    if (args.ring_prebuffer_blocks < 0 || args.ring_prebuffer_blocks > args.ring_capacity_blocks) {
        throw std::runtime_error("--ring-prebuffer-blocks must be between 0 and --ring-capacity-blocks");
    }
    if (args.ring_resync_lateness_ms < 0.0 || args.ring_resync_lateness_ms > 10000.0) {
        throw std::runtime_error("--ring-resync-lateness-ms must be between 0 and 10000");
    }
    if (args.consumer_wait_mode != "hybrid" && args.consumer_wait_mode != "waitable_timer") {
        throw std::runtime_error("--consumer-wait-mode must be hybrid or waitable_timer");
    }
    (void)thread_priority_value(args.consumer_thread_priority);
    (void)thread_priority_value(args.receiver_thread_priority);
    (void)process_priority_value(args.process_priority);
    if (args.queue_diagnostic && args.ring_diagnostic) {
        throw std::runtime_error("--queue-diagnostic and --ring-diagnostic are mutually exclusive");
    }
    if (args.progress_interval_blocks < 1 || args.progress_interval_blocks > 100000) {
        throw std::runtime_error("--progress-interval-blocks must be between 1 and 100000");
    }
    if (args.sink != "memory") {
        throw std::runtime_error("native receiver currently supports --sink memory only");
    }
    return args;
}

void run_client(const Args& args) {
    WsaSession wsa;
    const bool process_priority_applied = apply_process_priority(args.process_priority);
    if (args.process_priority != "normal" && !process_priority_applied) {
        throw std::runtime_error(last_wsa_error("SetPriorityClass"));
    }
    const bool receiver_thread_priority_applied =
        SetThreadPriority(
            GetCurrentThread(),
            thread_priority_value(args.receiver_thread_priority)) != 0;
    if (args.receiver_thread_priority != "normal" && !receiver_thread_priority_applied) {
        throw std::runtime_error(last_wsa_error("SetThreadPriority receiver"));
    }
    SchedulerMonitor scheduler(args.scheduler_interval_ms);
    const bool use_scheduler = !args.scheduler_trace.empty();
    if (use_scheduler) {
        scheduler.start();
    }

    SOCKET control_socket = INVALID_SOCKET;
    SOCKET udp_socket = INVALID_SOCKET;
    Preamble contract{};
    std::vector<Row> rows;
    std::vector<PacketEvent> packet_events;
    std::vector<ConsumerRow> consumer_rows;
    QueueState queue_state;
    if (args.ring_diagnostic) {
        queue_state.ring_enabled = true;
        queue_state.ring_capacity_blocks =
            static_cast<uint64_t>(args.ring_capacity_blocks);
        queue_state.ring_arrival_ns.assign(
            static_cast<size_t>(args.ring_capacity_blocks),
            0);
    }
    std::thread consumer_thread;
    Sha256 payload_hash;
    uint64_t received_blocks = 0;
    uint64_t lost_blocks = 0;
    uint32_t sequence_errors = 0;
    uint32_t crc_errors = 0;
    uint32_t framing_errors = 0;
    uint64_t expected_sequence = 0;
    int64_t first_receive_ns = 0;
    int64_t previous_receive_ns = 0;
    int64_t previous_packet_receive_ns = 0;

    try {
        control_socket = connect_with_retry(args);
        recv_exact(control_socket, reinterpret_cast<uint8_t*>(&contract), sizeof(contract));
        if (!valid_contract(contract)) {
            ++framing_errors;
        }
        rows.reserve(static_cast<size_t>(contract.block_count));
        packet_events.reserve(
            static_cast<size_t>((contract.block_count + args.blocks_per_packet - 1) /
                                args.blocks_per_packet));
        write_progress(args, "connected", contract.block_count, received_blocks,
                       expected_sequence, lost_blocks, sequence_errors, crc_errors,
                       framing_errors,
                       (args.queue_diagnostic || args.ring_diagnostic) ? &queue_state : nullptr,
                       consumer_rows.size());
        if (args.queue_diagnostic || args.ring_diagnostic) {
            consumer_thread = std::thread([&]() {
                run_consumer(
                    queue_state,
                    contract.block_count,
                    args.ring_diagnostic
                        ? args.ring_prebuffer_blocks
                        : args.queue_buffer_blocks,
                    args.ring_diagnostic
                        ? args.ring_resync_lateness_ms
                        : 0.0,
                    args.consumer_wait_mode,
                    args.consumer_thread_priority,
                    consumer_rows);
            });
        }
        if (args.transport == "udp") {
            udp_socket = connect_udp_and_send_hello(args);
        }

        while (expected_sequence < contract.block_count) {
            PacketHeader header{};
            const int64_t read_start_ns = qpc_ns();
            const double packet_pre_read_gap_ms = previous_packet_receive_ns == 0
                ? 0.0
                : ns_to_ms(read_start_ns - previous_packet_receive_ns);
            int64_t header_ns = 0;
            int64_t payload_ns = 0;
            std::vector<uint8_t> pcm;
            bool datagram_size_error = false;
            if (args.transport == "udp") {
                const size_t max_packet_bytes =
                    sizeof(PacketHeader) +
                    static_cast<size_t>(args.blocks_per_packet) * kBytesPerBlock;
                std::vector<uint8_t> packet(max_packet_bytes);
                const int received = recv(
                    udp_socket,
                    reinterpret_cast<char*>(packet.data()),
                    static_cast<int>(packet.size()),
                    0);
                if (received == SOCKET_ERROR) {
                    throw std::runtime_error(last_wsa_error("udp recv"));
                }
                header_ns = qpc_ns();
                payload_ns = header_ns;
                if (received < static_cast<int>(sizeof(PacketHeader))) {
                    datagram_size_error = true;
                    header.payload_bytes = 0;
                } else {
                    std::memcpy(&header, packet.data(), sizeof(PacketHeader));
                    const int expected_datagram_bytes =
                        static_cast<int>(sizeof(PacketHeader) + header.payload_bytes);
                    datagram_size_error = received != expected_datagram_bytes;
                    if (received > static_cast<int>(sizeof(PacketHeader))) {
                        const size_t payload_bytes =
                            static_cast<size_t>(received) - sizeof(PacketHeader);
                        pcm.resize(payload_bytes);
                        std::memcpy(
                            pcm.data(),
                            packet.data() + sizeof(PacketHeader),
                            payload_bytes);
                    }
                }
            } else {
                recv_exact(
                    control_socket,
                    reinterpret_cast<uint8_t*>(&header),
                    sizeof(header));
                header_ns = qpc_ns();
                pcm.resize(header.payload_bytes);
                recv_exact(control_socket, pcm.data(), pcm.size());
                payload_ns = qpc_ns();
            }
            const bool framing_error =
                datagram_size_error ||
                header.payload_bytes == 0 ||
                (header.payload_bytes % kBytesPerBlock) != 0 ||
                pcm.size() != header.payload_bytes;
            const uint32_t actual_crc = crc32(pcm.data(), pcm.size());
            const int64_t crc_ns = qpc_ns();
            const bool crc_ok = actual_crc == header.checksum;
            const int64_t receive_ns = qpc_ns();
            if (first_receive_ns == 0) {
                first_receive_ns = receive_ns;
            }
            const int packet_block_count =
                framing_error ? 0 : static_cast<int>(pcm.size() / kBytesPerBlock);
            packet_events.push_back(PacketEvent{
                header.sequence,
                read_start_ns,
                receive_ns,
                ns_to_ms(receive_ns - first_receive_ns),
                previous_packet_receive_ns == 0
                    ? 0.0
                    : ns_to_ms(receive_ns - previous_packet_receive_ns),
                packet_pre_read_gap_ms,
                packet_block_count,
                header.payload_bytes,
                ns_to_ms(crc_ns - read_start_ns),
                ns_to_ms(header_ns - read_start_ns),
                ns_to_ms(payload_ns - header_ns),
                ns_to_ms(crc_ns - payload_ns),
            });
            previous_packet_receive_ns = receive_ns;

            if (header.sequence != expected_sequence) {
                ++sequence_errors;
                if (header.sequence > expected_sequence) {
                    lost_blocks += header.sequence - expected_sequence;
                }
            }
            if (!crc_ok) {
                crc_errors += static_cast<uint32_t>(std::max(1, packet_block_count));
            }
            if (framing_error) {
                ++framing_errors;
                break;
            }
            for (int batch_index = 0; batch_index < packet_block_count; ++batch_index) {
                const uint64_t sequence = header.sequence + static_cast<uint64_t>(batch_index);
                const size_t block_start = static_cast<size_t>(batch_index) * kBytesPerBlock;
                payload_hash.update(pcm.data() + block_start, kBytesPerBlock);
                if (args.queue_diagnostic || args.ring_diagnostic) {
                    std::lock_guard<std::mutex> lock(queue_state.mutex);
                    if (!queue_state.started) {
                        queue_state.started = true;
                        queue_state.first_receive_ns = receive_ns;
                    }
                    if (args.ring_diagnostic) {
                        if (queue_state.queue_depth_blocks >=
                            queue_state.ring_capacity_blocks) {
                            queue_state.ring_head =
                                (queue_state.ring_head + 1) %
                                static_cast<size_t>(queue_state.ring_capacity_blocks);
                            --queue_state.queue_depth_blocks;
                            ++queue_state.overflow_drops;
                        }
                        const size_t tail =
                            (queue_state.ring_head +
                             static_cast<size_t>(queue_state.queue_depth_blocks)) %
                            static_cast<size_t>(queue_state.ring_capacity_blocks);
                        queue_state.ring_arrival_ns[tail] = receive_ns;
                        ++queue_state.queue_depth_blocks;
                        queue_state.max_depth_blocks = std::max(
                            queue_state.max_depth_blocks,
                            queue_state.queue_depth_blocks);
                    } else {
                        ++queue_state.queue_depth_blocks;
                        queue_state.max_depth_blocks = std::max(
                            queue_state.max_depth_blocks,
                            queue_state.queue_depth_blocks);
                    }
                }
                ++received_blocks;
                const double receive_interval = previous_receive_ns == 0
                    ? 0.0
                    : ns_to_ms(receive_ns - previous_receive_ns);
                rows.push_back(Row{
                    sequence,
                    ns_to_ms(static_cast<int64_t>(
                        header.scheduled_offset_ns +
                        static_cast<uint64_t>(batch_index) * kBlockDurationNs)),
                    batch_index == 0 ? read_start_ns : 0,
                    receive_ns,
                    ns_to_ms(receive_ns - first_receive_ns),
                    receive_interval,
                    previous_receive_ns == 0 ? 0.0 : receive_interval - kBlockDurationMs,
                    batch_index == 0
                        ? (previous_receive_ns == 0
                            ? 0.0
                            : ns_to_ms(read_start_ns - previous_receive_ns))
                        : 0.0,
                    crc_ok ? 1 : 0,
                    framing_error ? 1 : 0,
                    batch_index == 0 ? ns_to_ms(crc_ns - read_start_ns) : 0.0,
                    batch_index == 0 ? ns_to_ms(header_ns - read_start_ns) : 0.0,
                    batch_index == 0 ? ns_to_ms(payload_ns - header_ns) : 0.0,
                    batch_index == 0 ? ns_to_ms(crc_ns - payload_ns) : 0.0,
                    header.sequence,
                    batch_index,
                    packet_block_count,
                    header.payload_bytes,
                });
                previous_receive_ns = receive_ns;
            }
            expected_sequence = header.sequence + static_cast<uint64_t>(packet_block_count);
            if (
                (received_blocks % static_cast<uint64_t>(args.progress_interval_blocks)) == 0 ||
                expected_sequence >= contract.block_count ||
                framing_errors != 0
            ) {
                write_progress(args, "receiving", contract.block_count, received_blocks,
                               expected_sequence, lost_blocks, sequence_errors, crc_errors,
                               framing_errors,
                               (args.queue_diagnostic || args.ring_diagnostic) ? &queue_state : nullptr,
                               consumer_rows.size());
            }
        }
        if (args.queue_diagnostic || args.ring_diagnostic) {
            {
                std::lock_guard<std::mutex> lock(queue_state.mutex);
                queue_state.receiving_done = true;
            }
            write_progress(args, "joining_consumer", contract.block_count, received_blocks,
                           expected_sequence, lost_blocks, sequence_errors, crc_errors,
                           framing_errors, &queue_state, consumer_rows.size());
            if (consumer_thread.joinable()) {
                consumer_thread.join();
            }
            write_progress(args, "consumer_done", contract.block_count, received_blocks,
                           expected_sequence, lost_blocks, sequence_errors, crc_errors,
                           framing_errors, &queue_state, consumer_rows.size());
        }

        Ack ack{};
        std::copy(std::begin(kAckMagic), std::end(kAckMagic), std::begin(ack.magic));
        ack.received = received_blocks;
        ack.lost_blocks = static_cast<uint32_t>(lost_blocks);
        ack.sequence_errors = sequence_errors;
        ack.crc_errors = crc_errors;
        ack.framing_errors = framing_errors;
        send_exact(
            control_socket,
            reinterpret_cast<const uint8_t*>(&ack),
            sizeof(ack));
        if (udp_socket != INVALID_SOCKET) {
            closesocket(udp_socket);
            udp_socket = INVALID_SOCKET;
        }
        closesocket(control_socket);
        control_socket = INVALID_SOCKET;

        if (use_scheduler) {
            scheduler.stop();
        }
        const std::string digest = payload_hash.hexdigest();
        write_trace(args.trace, rows);
        write_consumer_trace(args.consumer_trace, consumer_rows);
        if (use_scheduler) {
            write_scheduler_trace(args.scheduler_trace, scheduler);
        }
        write_hash_output(args.hash_output, args, digest, received_blocks,
                          packet_events.size());
        write_summary(args.output, args, contract, received_blocks, lost_blocks,
                      sequence_errors, crc_errors, framing_errors, digest, rows,
                      packet_events, consumer_rows,
                      use_scheduler ? &scheduler : nullptr);
        write_progress(args, "completed", contract.block_count, received_blocks,
                       expected_sequence, lost_blocks, sequence_errors, crc_errors,
                       framing_errors,
                       (args.queue_diagnostic || args.ring_diagnostic) ? &queue_state : nullptr,
                       consumer_rows.size());
    } catch (...) {
        if (args.queue_diagnostic || args.ring_diagnostic) {
            {
                std::lock_guard<std::mutex> lock(queue_state.mutex);
                queue_state.receiving_done = true;
                queue_state.stop_requested = true;
            }
            if (consumer_thread.joinable()) {
                consumer_thread.join();
            }
        }
        if (udp_socket != INVALID_SOCKET) {
            closesocket(udp_socket);
        }
        if (control_socket != INVALID_SOCKET) {
            closesocket(control_socket);
        }
        if (use_scheduler) {
            scheduler.stop();
        }
        write_progress(args, "failed", contract.block_count, received_blocks,
                       expected_sequence, lost_blocks, sequence_errors, crc_errors,
                       framing_errors,
                       (args.queue_diagnostic || args.ring_diagnostic) ? &queue_state : nullptr,
                       consumer_rows.size());
        throw;
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const Args args = parse_args(argc, argv);
        run_client(args);
        return 0;
    } catch (const std::exception& exc) {
        try {
            const Args args = parse_args(argc, argv);
            write_failed_output(args.output, exc.what());
        } catch (...) {
        }
        std::cerr << "dfn48_native_receiver: " << exc.what() << "\n";
        return 1;
    }
}
