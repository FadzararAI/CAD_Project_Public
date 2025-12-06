#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stddef.h>

static void init_input(float *input, size_t width, size_t height) {
    for (size_t y = 0; y < height; ++y) {
        for (size_t x = 0; x < width; ++x) {
            input[y * width + x] = (float)((x + y) % 97) / 96.0f;
        }
    }
}

static void init_kernel(float *kernel, size_t kernel_size) {
    const float center_weight = (float)kernel_size;
    for (size_t ky = 0; ky < kernel_size; ++ky) {
        for (size_t kx = 0; kx < kernel_size; ++kx) {
            int dy = (int)ky - (int)(kernel_size / 2);
            int dx = (int)kx - (int)(kernel_size / 2);
            kernel[ky * kernel_size + kx] = 1.0f / (1.0f + dx * dx + dy * dy + center_weight);
        }
    }
}

static void zero_buffer(float *buffer, size_t length) {
    for (size_t i = 0; i < length; ++i) {
        buffer[i] = 0.0f;
    }
}

static void convolve(const float *restrict input,
                     const float *restrict kernel,
                     float *restrict output,
                     size_t width,
                     size_t height,
                     size_t kernel_size) {
    const size_t out_width = width - kernel_size + 1;
    const size_t out_height = height - kernel_size + 1;

    for (size_t y = 0; y < out_height; ++y) {
        for (size_t x = 0; x < out_width; ++x) {
            float sum = 0.0f;
            for (size_t ky = 0; ky < kernel_size; ++ky) {
                const size_t in_row = (y + ky) * width;
                const size_t kernel_row = ky * kernel_size;
                for (size_t kx = 0; kx < kernel_size; ++kx) {
                    sum += input[in_row + x + kx] * kernel[kernel_row + kx];
                }
            }
            output[y * out_width + x] = sum;
        }
    }
}

static void usage(const char *prog) {
    fprintf(stderr,
            "Usage: %s [width height kernel_size iterations]\n"
            "Defaults: width=128 height=128 kernel=3 iterations=64\n",
            prog);
}

int main(int argc, char **argv) {
    size_t width = 128;
    size_t height = 128;
    size_t kernel_size = 3;
    size_t iterations = 64;

    if (argc == 2 && (argv[1][0] == '-' && argv[1][1] == 'h')) {
        usage(argv[0]);
        return 0;
    }

    if (argc > 1) {
        width = (size_t)strtoul(argv[1], NULL, 10);
    }
    if (argc > 2) {
        height = (size_t)strtoul(argv[2], NULL, 10);
    }
    if (argc > 3) {
        kernel_size = (size_t)strtoul(argv[3], NULL, 10);
    }
    if (argc > 4) {
        iterations = (size_t)strtoul(argv[4], NULL, 10);
    }
    if (argc > 5) {
        usage(argv[0]);
        return 1;
    }

    if (width < kernel_size || height < kernel_size || kernel_size == 0) {
        fprintf(stderr, "Invalid dimensions: ensure width/height >= kernel_size > 0.\n");
        return 1;
    }
    if (kernel_size % 2 == 0) {
        fprintf(stderr, "Kernel size must be odd.\n");
        return 1;
    }
    if (iterations == 0) {
        iterations = 1;
    }

    const size_t input_elems = width * height;
    const size_t kernel_elems = kernel_size * kernel_size;
    const size_t out_width = width - kernel_size + 1;
    const size_t out_height = height - kernel_size + 1;
    const size_t output_elems = out_width * out_height;

    float *input = (float *)malloc(sizeof(float) * input_elems);
    float *kernel = (float *)malloc(sizeof(float) * kernel_elems);
    float *output = (float *)malloc(sizeof(float) * output_elems);

    if (!input || !kernel || !output) {
        fprintf(stderr, "Failed to allocate buffers.\n");
        free(input);
        free(kernel);
        free(output);
        return 1;
    }

    init_input(input, width, height);
    init_kernel(kernel, kernel_size);
    zero_buffer(output, output_elems);

    for (size_t iter = 0; iter < iterations; ++iter) {
        convolve(input, kernel, output, width, height, kernel_size);
        // Simple data reuse pattern for subsequent iterations.
        if (iter + 1 < iterations) {
            float *tmp = input;
            input = output;
            output = tmp;
        }
    }

    volatile float checksum = 0.0f;
    for (size_t i = 0; i < output_elems; ++i) {
        checksum += output[i];
    }

    printf("Checksum: %.6f (w=%zu h=%zu k=%zu iters=%zu)\n",
           checksum, width, height, kernel_size, iterations);

    free(input);
    free(kernel);
    free(output);
    return 0;
}
