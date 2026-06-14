#include <stdio.h>
#include <stdlib.h>

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

#include "rnnoise.h"

static int write_frame(const float *frame, int frame_size) {
  return fwrite(frame, sizeof(float), frame_size, stdout) == (size_t)frame_size;
}

int main(void) {
  const int frame_size = rnnoise_get_frame_size();
  const int state_size = rnnoise_get_size();
  DenoiseState *state = rnnoise_create(NULL);
  float *input;
  float *output;
  int first = 1;
#ifdef _WIN32
  if (_setmode(_fileno(stdin), _O_BINARY) == -1 ||
      _setmode(_fileno(stdout), _O_BINARY) == -1) {
    fprintf(stderr, "binary mode setup failed\n");
    return 1;
  }
#endif
  if (state == NULL || frame_size <= 0) {
    fprintf(stderr, "rnnoise initialization failed\n");
    return 2;
  }
  input = (float *)calloc((size_t)frame_size, sizeof(float));
  output = (float *)calloc((size_t)frame_size, sizeof(float));
  if (input == NULL || output == NULL) {
    fprintf(stderr, "allocation failed\n");
    rnnoise_destroy(state);
    free(input);
    free(output);
    return 3;
  }

  while (1) {
    size_t count = fread(input, sizeof(float), (size_t)frame_size, stdin);
    int index;
    if (count == 0) {
      break;
    }
    for (index = 0; index < frame_size; ++index) {
      input[index] = index < (int)count ? input[index] * 32768.0f : 0.0f;
    }
    rnnoise_process_frame(state, output, input);
    if (!first) {
      for (index = 0; index < frame_size; ++index) {
        output[index] /= 32768.0f;
      }
      if (!write_frame(output, frame_size)) {
        fprintf(stderr, "output write failed\n");
        return 4;
      }
    }
    first = 0;
    if (count < (size_t)frame_size) {
      break;
    }
  }

  if (!first) {
    int index;
    for (index = 0; index < frame_size; ++index) {
      input[index] = 0.0f;
    }
    rnnoise_process_frame(state, output, input);
    for (index = 0; index < frame_size; ++index) {
      output[index] /= 32768.0f;
    }
    if (!write_frame(output, frame_size)) {
      fprintf(stderr, "tail write failed\n");
      return 5;
    }
  }

  fprintf(
      stderr,
      "frame_size=%d state_size=%d latency_samples=%d\n",
      frame_size,
      state_size,
      frame_size);
  rnnoise_destroy(state);
  free(input);
  free(output);
  return 0;
}
