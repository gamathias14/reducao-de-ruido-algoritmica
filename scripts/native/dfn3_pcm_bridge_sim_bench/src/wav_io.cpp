#include "wav_io.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>

namespace dfn_bench {
namespace {

constexpr std::uint16_t WAVE_FORMAT_PCM = 0x0001;
constexpr std::uint16_t WAVE_FORMAT_IEEE_FLOAT = 0x0003;
constexpr std::uint16_t WAVE_FORMAT_EXTENSIBLE = 0xFFFE;

std::string path_string(const std::filesystem::path& path) {
#if defined(_WIN32)
    return path.u8string();
#else
    return path.string();
#endif
}

std::uint16_t read_u16(std::istream& in) {
    std::array<unsigned char, 2> b{};
    in.read(reinterpret_cast<char*>(b.data()), static_cast<std::streamsize>(b.size()));
    if (!in) throw std::runtime_error("unexpected EOF while reading u16");
    return static_cast<std::uint16_t>(b[0] | (b[1] << 8));
}

std::uint32_t read_u32(std::istream& in) {
    std::array<unsigned char, 4> b{};
    in.read(reinterpret_cast<char*>(b.data()), static_cast<std::streamsize>(b.size()));
    if (!in) throw std::runtime_error("unexpected EOF while reading u32");
    return static_cast<std::uint32_t>(b[0] | (b[1] << 8) | (b[2] << 16) | (b[3] << 24));
}

void write_u16(std::ostream& out, std::uint16_t value) {
    const unsigned char b[2] = {
        static_cast<unsigned char>(value & 0xFF),
        static_cast<unsigned char>((value >> 8) & 0xFF),
    };
    out.write(reinterpret_cast<const char*>(b), 2);
}

void write_u32(std::ostream& out, std::uint32_t value) {
    const unsigned char b[4] = {
        static_cast<unsigned char>(value & 0xFF),
        static_cast<unsigned char>((value >> 8) & 0xFF),
        static_cast<unsigned char>((value >> 16) & 0xFF),
        static_cast<unsigned char>((value >> 24) & 0xFF),
    };
    out.write(reinterpret_cast<const char*>(b), 4);
}

bool read_id(std::istream& in, char id[4]) {
    in.read(id, 4);
    return static_cast<bool>(in);
}

bool id_eq(const char id[4], const char* expected) {
    return id[0] == expected[0] && id[1] == expected[1] && id[2] == expected[2] && id[3] == expected[3];
}

std::int32_t read_pcm_signed_le(const unsigned char* p, std::uint16_t bits_per_sample) {
    switch (bits_per_sample) {
    case 8:
        return static_cast<std::int32_t>(static_cast<int>(p[0]) - 128);
    case 16:
        return static_cast<std::int16_t>(p[0] | (p[1] << 8));
    case 24: {
        std::int32_t v = static_cast<std::int32_t>(p[0] | (p[1] << 8) | (p[2] << 16));
        if (v & 0x800000) v -= 0x1000000;
        return v;
    }
    case 32:
        return static_cast<std::int32_t>(p[0] | (p[1] << 8) | (p[2] << 16) | (p[3] << 24));
    default:
        throw std::runtime_error("unsupported PCM bit depth: " + std::to_string(bits_per_sample));
    }
}

float pcm_to_float(std::int32_t sample, std::uint16_t bits_per_sample) {
    switch (bits_per_sample) {
    case 8:
        return static_cast<float>(sample) / 128.0f;
    case 16:
        return static_cast<float>(sample) / 32768.0f;
    case 24:
        return static_cast<float>(sample) / 8388608.0f;
    case 32:
        return static_cast<float>(sample) / 2147483648.0f;
    default:
        throw std::runtime_error("unsupported PCM bit depth: " + std::to_string(bits_per_sample));
    }
}

float read_float32_le(const unsigned char* p) {
    static_assert(sizeof(float) == 4, "float must be 32-bit");
    std::uint32_t u = static_cast<std::uint32_t>(p[0] | (p[1] << 8) | (p[2] << 16) | (p[3] << 24));
    float f = 0.0f;
    std::memcpy(&f, &u, sizeof(float));
    return f;
}

std::uint16_t effective_format_from_extensible(const std::vector<unsigned char>& fmt_payload, std::uint16_t declared_format) {
    if (declared_format != WAVE_FORMAT_EXTENSIBLE) return declared_format;
    if (fmt_payload.size() < 40) return declared_format;
    // WAVEFORMATEXTENSIBLE SubFormat starts at byte 24 of the fmt payload.
    const std::uint16_t tag = static_cast<std::uint16_t>(fmt_payload[24] | (fmt_payload[25] << 8));
    if (tag == WAVE_FORMAT_PCM || tag == WAVE_FORMAT_IEEE_FLOAT) return tag;
    return declared_format;
}

void ensure_parent_dir(const std::filesystem::path& path) {
    const auto parent = path.parent_path();
    if (!parent.empty()) {
        std::filesystem::create_directories(parent);
    }
}

} // namespace

AudioMono read_wav_mono_float32(const std::filesystem::path& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) {
        throw std::runtime_error("cannot open WAV for read: " + path_string(path));
    }

    char riff[4]{};
    if (!read_id(in, riff) || !id_eq(riff, "RIFF")) {
        throw std::runtime_error("not a RIFF file: " + path_string(path));
    }
    (void)read_u32(in);
    char wave[4]{};
    if (!read_id(in, wave) || !id_eq(wave, "WAVE")) {
        throw std::runtime_error("not a WAVE file: " + path_string(path));
    }

    bool have_fmt = false;
    bool have_data = false;
    WavInfo info{};
    std::vector<unsigned char> fmt_payload;
    std::vector<unsigned char> data;

    while (in) {
        char chunk_id[4]{};
        if (!read_id(in, chunk_id)) break;
        const std::uint32_t chunk_size = read_u32(in);
        std::vector<unsigned char> payload(chunk_size);
        if (chunk_size > 0) {
            in.read(reinterpret_cast<char*>(payload.data()), static_cast<std::streamsize>(payload.size()));
            if (!in) throw std::runtime_error("unexpected EOF in WAV chunk");
        }
        if (chunk_size % 2 == 1) {
            in.seekg(1, std::ios::cur);
        }

        if (id_eq(chunk_id, "fmt ")) {
            if (payload.size() < 16) throw std::runtime_error("invalid fmt chunk");
            fmt_payload = payload;
            info.audio_format = static_cast<std::uint16_t>(payload[0] | (payload[1] << 8));
            info.channels = static_cast<std::uint16_t>(payload[2] | (payload[3] << 8));
            info.sample_rate = static_cast<std::uint32_t>(payload[4] | (payload[5] << 8) | (payload[6] << 16) | (payload[7] << 24));
            info.block_align = static_cast<std::uint16_t>(payload[12] | (payload[13] << 8));
            info.bits_per_sample = static_cast<std::uint16_t>(payload[14] | (payload[15] << 8));
            info.audio_format = effective_format_from_extensible(fmt_payload, info.audio_format);
            have_fmt = true;
        } else if (id_eq(chunk_id, "data")) {
            data = std::move(payload);
            have_data = true;
        }
    }

    if (!have_fmt) throw std::runtime_error("WAV missing fmt chunk: " + path_string(path));
    if (!have_data) throw std::runtime_error("WAV missing data chunk: " + path_string(path));
    if (info.channels == 0) throw std::runtime_error("WAV has zero channels: " + path_string(path));
    if (info.sample_rate == 0) throw std::runtime_error("WAV has zero sample rate: " + path_string(path));
    if (info.block_align == 0) throw std::runtime_error("WAV has zero block align: " + path_string(path));
    if (data.size() % info.block_align != 0) throw std::runtime_error("WAV data size is not aligned to block_align");

    const std::uint64_t frames = static_cast<std::uint64_t>(data.size() / info.block_align);
    info.frames = frames;
    const std::uint16_t bytes_per_sample = static_cast<std::uint16_t>((info.bits_per_sample + 7) / 8);
    if (bytes_per_sample == 0 || info.block_align < bytes_per_sample * info.channels) {
        throw std::runtime_error("invalid WAV block alignment");
    }

    if (info.audio_format != WAVE_FORMAT_PCM && info.audio_format != WAVE_FORMAT_IEEE_FLOAT) {
        throw std::runtime_error("unsupported WAV format tag: " + std::to_string(info.audio_format));
    }
    if (info.audio_format == WAVE_FORMAT_IEEE_FLOAT && info.bits_per_sample != 32) {
        throw std::runtime_error("only 32-bit float WAV is supported for IEEE_FLOAT");
    }

    std::vector<float> mono;
    mono.resize(static_cast<std::size_t>(frames));
    for (std::uint64_t frame = 0; frame < frames; ++frame) {
        const unsigned char* frame_ptr = data.data() + frame * info.block_align;
        double acc = 0.0;
        for (std::uint16_t ch = 0; ch < info.channels; ++ch) {
            const unsigned char* sample_ptr = frame_ptr + ch * bytes_per_sample;
            float sample = 0.0f;
            if (info.audio_format == WAVE_FORMAT_IEEE_FLOAT) {
                sample = read_float32_le(sample_ptr);
            } else {
                sample = pcm_to_float(read_pcm_signed_le(sample_ptr, info.bits_per_sample), info.bits_per_sample);
            }
            if (!std::isfinite(sample)) sample = 0.0f;
            acc += sample;
        }
        mono[static_cast<std::size_t>(frame)] = static_cast<float>(acc / static_cast<double>(info.channels));
    }

    return AudioMono{info.sample_rate, info, std::move(mono)};
}

void write_wav_pcm16_mono(const std::filesystem::path& path, std::uint32_t sample_rate, const std::vector<float>& samples) {
    ensure_parent_dir(path);
    std::ofstream out(path, std::ios::binary);
    if (!out) {
        throw std::runtime_error("cannot open WAV for write: " + path_string(path));
    }

    const std::uint16_t channels = 1;
    const std::uint16_t bits_per_sample = 16;
    const std::uint16_t block_align = channels * bits_per_sample / 8;
    const std::uint32_t byte_rate = sample_rate * block_align;
    const std::uint64_t data_size_64 = samples.size() * block_align;
    if (data_size_64 > std::numeric_limits<std::uint32_t>::max()) {
        throw std::runtime_error("WAV too large for RIFF PCM writer");
    }
    const std::uint32_t data_size = static_cast<std::uint32_t>(data_size_64);
    const std::uint32_t riff_size = 4 + (8 + 16) + (8 + data_size);

    out.write("RIFF", 4);
    write_u32(out, riff_size);
    out.write("WAVE", 4);
    out.write("fmt ", 4);
    write_u32(out, 16);
    write_u16(out, WAVE_FORMAT_PCM);
    write_u16(out, channels);
    write_u32(out, sample_rate);
    write_u32(out, byte_rate);
    write_u16(out, block_align);
    write_u16(out, bits_per_sample);
    out.write("data", 4);
    write_u32(out, data_size);

    for (float s : samples) {
        if (!std::isfinite(s)) s = 0.0f;
        const float clipped = std::max(-1.0f, std::min(1.0f, s));
        const auto q = static_cast<std::int16_t>(std::lrint(clipped * 32767.0f));
        write_u16(out, static_cast<std::uint16_t>(q));
    }
}

std::string wav_info_string(const WavInfo& info) {
    std::ostringstream oss;
    oss << "format=" << info.audio_format
        << ", channels=" << info.channels
        << ", sample_rate=" << info.sample_rate
        << ", bits_per_sample=" << info.bits_per_sample
        << ", block_align=" << info.block_align
        << ", frames=" << info.frames;
    return oss.str();
}

} // namespace dfn_bench
