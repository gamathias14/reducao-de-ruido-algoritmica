#pragma once

#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>

namespace dfn_bench {

struct WavInfo {
    std::uint16_t audio_format = 0;
    std::uint16_t channels = 0;
    std::uint32_t sample_rate = 0;
    std::uint16_t bits_per_sample = 0;
    std::uint16_t block_align = 0;
    std::uint64_t frames = 0;
};

struct AudioMono {
    std::uint32_t sample_rate = 0;
    WavInfo source_info;
    std::vector<float> samples;
};

AudioMono read_wav_mono_float32(const std::filesystem::path& path);
void write_wav_pcm16_mono(const std::filesystem::path& path, std::uint32_t sample_rate, const std::vector<float>& samples);

std::string wav_info_string(const WavInfo& info);

} // namespace dfn_bench
