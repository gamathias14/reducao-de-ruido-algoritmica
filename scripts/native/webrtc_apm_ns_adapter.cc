#include <algorithm>
#include <array>
#include <cstdio>

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

#include "api/audio/audio_processing.h"
#include "api/audio/builtin_audio_processing_builder.h"
#include "api/environment/environment_factory.h"

namespace {

constexpr int kSampleRateHz = 16000;
constexpr int kChannelCount = 1;
constexpr int kFrameSamples = kSampleRateHz / 100;

bool SetBinaryMode() {
#ifdef _WIN32
  return _setmode(_fileno(stdin), _O_BINARY) != -1 &&
         _setmode(_fileno(stdout), _O_BINARY) != -1;
#else
  return true;
#endif
}

}  // namespace

int main() {
  if (!SetBinaryMode()) {
    std::fprintf(stderr, "binary mode setup failed\n");
    return 1;
  }

  webrtc::AudioProcessing::Config config;
  config.noise_suppression.enabled = true;

  webrtc::scoped_refptr<webrtc::AudioProcessing> apm =
      webrtc::BuiltinAudioProcessingBuilder(config).Build(
          webrtc::CreateEnvironment());
  if (!apm) {
    std::fprintf(stderr, "WebRTC APM initialization failed\n");
    return 2;
  }

  const webrtc::StreamConfig stream_config(kSampleRateHz, kChannelCount);
  std::array<float, kFrameSamples> frame{};
  float* channels[] = {frame.data()};
  size_t frame_count = 0;

  while (true) {
    const size_t count =
        std::fread(frame.data(), sizeof(float), frame.size(), stdin);
    if (count == 0) {
      break;
    }
    if (count < frame.size()) {
      if (std::ferror(stdin)) {
        std::fprintf(stderr, "input read failed\n");
        return 3;
      }
      std::fill(frame.begin() + count, frame.end(), 0.0f);
    }

    const int error =
        apm->ProcessStream(channels, stream_config, stream_config, channels);
    if (error != webrtc::AudioProcessing::Error::kNoError) {
      std::fprintf(stderr, "ProcessStream failed: %d\n", error);
      return 4;
    }
    if (std::fwrite(frame.data(), sizeof(float), count, stdout) != count) {
      std::fprintf(stderr, "output write failed\n");
      return 5;
    }
    ++frame_count;
    if (count < frame.size()) {
      break;
    }
  }

  std::fprintf(stderr,
               "sample_rate=%d frame_size=%d frames=%zu ns_level=moderate\n",
               kSampleRateHz, kFrameSamples, frame_count);
  return 0;
}
