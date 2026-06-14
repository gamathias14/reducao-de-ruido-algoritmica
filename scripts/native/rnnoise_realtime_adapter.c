#include <math.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

#include "rnnoise.h"

#ifdef _WIN32
#define PTC3527_EXPORT __declspec(dllexport)
#else
#define PTC3527_EXPORT
#endif

#define PTC_INPUT_SAMPLES 320
#define PTC_NATIVE_SAMPLES 960
#define PTC_RATE_FACTOR 3
#define PTC_FIR_TAPS 63
#define PTC_PI 3.14159265358979323846

typedef struct {
  DenoiseState *rnnoise;
  float taps[PTC_FIR_TAPS];
  float up_history[PTC_FIR_TAPS];
  float down_history[PTC_FIR_TAPS];
  float native_input[PTC_NATIVE_SAMPLES];
  float native_output[PTC_NATIVE_SAMPLES];
  float frame_input[480];
  float frame_output[480];
  int up_position;
  int down_position;
  int down_phase;
} Ptc3527RNNoiseState;

static void initialize_taps(float *taps) {
  const double cutoff = 0.95 / (2.0 * PTC_RATE_FACTOR);
  const double center = 0.5 * (PTC_FIR_TAPS - 1);
  double sum = 0.0;
  int index;
  for (index = 0; index < PTC_FIR_TAPS; ++index) {
    const double offset = index - center;
    const double sinc = offset == 0.0
        ? 2.0 * cutoff
        : sin(2.0 * PTC_PI * cutoff * offset) / (PTC_PI * offset);
    const double window =
        0.54 - 0.46 * cos(2.0 * PTC_PI * index / (PTC_FIR_TAPS - 1));
    taps[index] = (float)(sinc * window);
    sum += taps[index];
  }
  for (index = 0; index < PTC_FIR_TAPS; ++index) {
    taps[index] = (float)(taps[index] / sum);
  }
}

static float fir_sample(
    float *history,
    int *position,
    const float *taps,
    float input) {
  float output = 0.0f;
  int history_index;
  int tap_index;
  history[*position] = input;
  history_index = *position;
  for (tap_index = 0; tap_index < PTC_FIR_TAPS; ++tap_index) {
    output += taps[tap_index] * history[history_index];
    --history_index;
    if (history_index < 0) {
      history_index = PTC_FIR_TAPS - 1;
    }
  }
  *position = (*position + 1) % PTC_FIR_TAPS;
  return output;
}

PTC3527_EXPORT Ptc3527RNNoiseState *ptc3527_rnnoise_create(void) {
  Ptc3527RNNoiseState *state =
      (Ptc3527RNNoiseState *)calloc(1, sizeof(Ptc3527RNNoiseState));
  if (state == NULL) {
    return NULL;
  }
  state->rnnoise = rnnoise_create(NULL);
  if (state->rnnoise == NULL) {
    free(state);
    return NULL;
  }
  initialize_taps(state->taps);
  return state;
}

PTC3527_EXPORT int ptc3527_rnnoise_reset(Ptc3527RNNoiseState *state) {
  if (state == NULL || state->rnnoise == NULL) {
    return -1;
  }
  if (rnnoise_init(state->rnnoise, NULL) != 0) {
    return -2;
  }
  memset(state->up_history, 0, sizeof(state->up_history));
  memset(state->down_history, 0, sizeof(state->down_history));
  memset(state->native_input, 0, sizeof(state->native_input));
  memset(state->native_output, 0, sizeof(state->native_output));
  memset(state->frame_input, 0, sizeof(state->frame_input));
  memset(state->frame_output, 0, sizeof(state->frame_output));
  state->up_position = 0;
  state->down_position = 0;
  state->down_phase = 0;
  return 0;
}

PTC3527_EXPORT void ptc3527_rnnoise_destroy(Ptc3527RNNoiseState *state) {
  if (state == NULL) {
    return;
  }
  rnnoise_destroy(state->rnnoise);
  free(state);
}

PTC3527_EXPORT int ptc3527_rnnoise_get_state_size(void) {
  return (int)sizeof(Ptc3527RNNoiseState) + rnnoise_get_size();
}

PTC3527_EXPORT int ptc3527_rnnoise_get_input_size(void) {
  return PTC_INPUT_SAMPLES;
}

PTC3527_EXPORT float ptc3527_rnnoise_process(
    Ptc3527RNNoiseState *state,
    float *output,
    const float *input) {
  float vad_probability = 0.0f;
  int input_index;
  int native_index = 0;
  int frame_offset;
  int output_index = 0;
  if (state == NULL || state->rnnoise == NULL || output == NULL || input == NULL) {
    return -1.0f;
  }

  for (input_index = 0; input_index < PTC_INPUT_SAMPLES; ++input_index) {
    int phase;
    for (phase = 0; phase < PTC_RATE_FACTOR; ++phase) {
      const float sample = phase == 0 ? input[input_index] : 0.0f;
      state->native_input[native_index++] =
          PTC_RATE_FACTOR * fir_sample(
              state->up_history,
              &state->up_position,
              state->taps,
              sample);
    }
  }

  for (frame_offset = 0; frame_offset < PTC_NATIVE_SAMPLES; frame_offset += 480) {
    float frame_vad;
    int frame_index;
    for (frame_index = 0; frame_index < 480; ++frame_index) {
      state->frame_input[frame_index] =
          32768.0f * state->native_input[frame_offset + frame_index];
    }
    frame_vad = rnnoise_process_frame(
        state->rnnoise,
        state->frame_output,
        state->frame_input);
    if (frame_vad > vad_probability) {
      vad_probability = frame_vad;
    }
    for (frame_index = 0; frame_index < 480; ++frame_index) {
      state->native_output[frame_offset + frame_index] =
          state->frame_output[frame_index] / 32768.0f;
    }
  }

  for (native_index = 0; native_index < PTC_NATIVE_SAMPLES; ++native_index) {
    const float filtered = fir_sample(
        state->down_history,
        &state->down_position,
        state->taps,
        state->native_output[native_index]);
    if (state->down_phase == 0) {
      output[output_index++] = filtered;
    }
    state->down_phase = (state->down_phase + 1) % PTC_RATE_FACTOR;
  }
  return output_index == PTC_INPUT_SAMPLES ? vad_probability : -2.0f;
}
