#include <math.h>
#include <stdint.h>
#include <stdio.h>

/*
 * TinyML Activity Classifier Benchmark
 *
 * The benchmark emulates a typical TinyML workload that runs on a microcontroller:
 *  - Ingest a sliding window of raw IMU samples (3 axes, 16 samples each)
 *  - Extract lightweight statistical features
 *  - Execute a very small neural-network classifier (single dense layer + softmax)
 *  - Produce class probabilities for three gestures (still, wave, shake)
 *
 * The implementation is intentionally self-contained (no external libraries) so it
 * can be compiled for bare-metal targets or the GEM5 RISC-V simulation targets
 * used in this project.
 */

#define AXES 3
#define WINDOW_SIZE 16
#define FEATURE_DIM (AXES * 3) /* mean, mobility, energy per axis */
#define NUM_CLASSES 3
#define NUM_SAMPLES 12
#define INFERENCE_LOOP_COUNT 250

typedef enum {
    CLASS_STILL = 0,
    CLASS_WAVE = 1,
    CLASS_SHAKE = 2
} activity_class_t;

typedef struct {
    int8_t signal[AXES * WINDOW_SIZE];
    uint8_t label;
} tinyml_sample_t;

static const char *const CLASS_NAMES[NUM_CLASSES] = {"still", "wave", "shake"};

/* Hand-crafted micro-dataset covering three activity classes. */
static const tinyml_sample_t DATASET[NUM_SAMPLES] = {
    {
        .signal = {
            /* X axis */
            1, 1, 2, 0, -1, 0, 1, 0, 1, 0, -1, 0, 1, 0, 1, 0,
            /* Y axis */
            0, 1, 0, 1, 0, -1, 0, 0, 1, 0, 0, 1, -1, 0, 1, 0,
            /* Z axis */
            1, 0, 1, 0, 1, 0, 1, -1, 0, 1, 0, 1, 0, 1, 0, -1},
        .label = CLASS_STILL},
    {
        .signal = {
            /* X axis */
            0, 0, 1, 0, -1, 1, 0, 0, 1, 0, -1, 0, 1, 0, 0, 0,
            /* Y axis */
            1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0,
            /* Z axis */
            0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0},
        .label = CLASS_STILL},
    {
        .signal = {
            /* X axis */
            1, 0, 1, -1, 1, 0, 1, 0, -1, 0, 1, 0, 1, -1, 0, 1,
            /* Y axis */
            0, 1, 0, 1, 0, 1, 0, -1, 0, 1, 0, 1, 0, 1, 0, -1,
            /* Z axis */
            0, 1, 0, 1, 0, 1, 0, 1, 0, -1, 0, 1, 0, 1, 0, 1},
        .label = CLASS_STILL},
    {
        .signal = {
            /* X axis */
            1, -1, 0, 0, 1, 0, 0, -1, 0, 1, 0, 1, 0, 0, -1, 1,
            /* Y axis */
            0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, -1, 0, 1, 0, 1,
            /* Z axis */
            1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1},
        .label = CLASS_STILL},
    {
        .signal = {
            /* X axis */
            8, 7, -6, -7, 9, 8, -9, -10, 7, 6, -8, -7, 9, 8, -9, -8,
            /* Y axis */
            1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0,
            /* Z axis */
            0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1},
        .label = CLASS_WAVE},
    {
        .signal = {
            /* X axis */
            9, -8, 7, -6, 8, -7, 9, -8, 7, -6, 8, -7, 9, -8, 7, -6,
            /* Y axis */
            0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1,
            /* Z axis */
            1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0},
        .label = CLASS_WAVE},
    {
        .signal = {
            /* X axis */
            6, 5, -6, -5, 6, 5, -6, -5, 6, 5, -6, -5, 6, 5, -6, -5,
            /* Y axis */
            1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0,
            /* Z axis */
            0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1},
        .label = CLASS_WAVE},
    {
        .signal = {
            /* X axis */
            10, -9, 8, -7, 9, -8, 10, -9, 8, -7, 9, -8, 10, -9, 8, -7,
            /* Y axis */
            1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0,
            /* Z axis */
            0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1},
        .label = CLASS_WAVE},
    {
        .signal = {
            /* X axis */
            9, -9, 8, -8, 7, -7, 9, -9, 8, -8, 7, -7, 9, -9, 8, -8,
            /* Y axis */
            7, -7, 8, -8, 7, -7, 8, -8, 7, -7, 8, -8, 7, -7, 8, -8,
            /* Z axis */
            6, -6, 7, -7, 6, -6, 7, -7, 6, -6, 7, -7, 6, -6, 7, -7},
        .label = CLASS_SHAKE},
    {
        .signal = {
            /* X axis */
            8, -8, 9, -9, 8, -8, 9, -9, 8, -8, 9, -9, 8, -8, 9, -9,
            /* Y axis */
            9, -9, 8, -8, 9, -9, 8, -8, 9, -9, 8, -8, 9, -9, 8, -8,
            /* Z axis */
            7, -7, 8, -8, 7, -7, 8, -8, 7, -7, 8, -8, 7, -7, 8, -8},
        .label = CLASS_SHAKE},
    {
        .signal = {
            /* X axis */
            10, -10, 9, -9, 10, -10, 9, -9, 10, -10, 9, -9, 10, -10, 9, -9,
            /* Y axis */
            8, -8, 7, -7, 8, -8, 7, -7, 8, -8, 7, -7, 8, -8, 7, -7,
            /* Z axis */
            9, -9, 8, -8, 9, -9, 8, -8, 9, -9, 8, -8, 9, -9, 8, -8},
        .label = CLASS_SHAKE},
    {
        .signal = {
            /* X axis */
            7, -7, 8, -8, 9, -9, 7, -7, 8, -8, 9, -9, 7, -7, 8, -8,
            /* Y axis */
            8, -8, 7, -7, 9, -9, 8, -8, 7, -7, 9, -9, 8, -8, 7, -7,
            /* Z axis */
            9, -9, 8, -8, 7, -7, 9, -9, 8, -8, 7, -7, 9, -9, 8, -8},
        .label = CLASS_SHAKE},
};

/* Single-layer network weights generated offline for the above feature set. */
static const float DENSE_WEIGHTS[NUM_CLASSES][FEATURE_DIM] = {
    /* CLASS_STILL */
    {-0.04f, -0.18f, -0.08f, -0.02f, -0.16f, -0.08f, -0.02f, -0.18f, -0.08f},
    /* CLASS_WAVE */
    {-0.01f, 0.18f, 0.14f, 0.00f, -0.12f, -0.06f, 0.00f, -0.10f, -0.06f},
    /* CLASS_SHAKE */
    {-0.02f, 0.08f, 0.10f, -0.02f, 0.09f, 0.11f, -0.02f, 0.08f, 0.11f},
};

static const float DENSE_BIAS[NUM_CLASSES] = {2.20f, -1.35f, -2.40f};

static void extract_features(const int8_t *window, float *features) {
    for (size_t axis = 0; axis < AXES; ++axis) {
        const int8_t *axis_data = window + axis * WINDOW_SIZE;
        float sum = 0.0f;
        float energy = 0.0f;
        float diff_sum = 0.0f;
        int8_t previous = axis_data[0];

        for (size_t i = 0; i < WINDOW_SIZE; ++i) {
            const float sample = (float)axis_data[i];
            sum += sample;
            energy += sample * sample;
            if (i > 0) {
                const float delta = fabsf(sample - (float)previous);
                diff_sum += delta;
            }
            previous = axis_data[i];
        }

        const float mean = sum / (float)WINDOW_SIZE;
        const float mobility =
            diff_sum / (float)(WINDOW_SIZE - 1); /* average absolute diff */
        const float mean_energy = energy / (float)WINDOW_SIZE;

        const size_t base = axis * 3;
        features[base + 0] = mean;
        features[base + 1] = mobility;
        features[base + 2] = mean_energy;
    }
}

static uint8_t dense_softmax(const float *features, float *probabilities) {
    float logits[NUM_CLASSES];
    for (size_t cls = 0; cls < NUM_CLASSES; ++cls) {
        float acc = DENSE_BIAS[cls];
        for (size_t feat = 0; feat < FEATURE_DIM; ++feat) {
            acc += DENSE_WEIGHTS[cls][feat] * features[feat];
        }
        logits[cls] = acc;
    }

    float max_logit = logits[0];
    for (size_t cls = 1; cls < NUM_CLASSES; ++cls) {
        if (logits[cls] > max_logit) {
            max_logit = logits[cls];
        }
    }

    float sum = 0.0f;
    for (size_t cls = 0; cls < NUM_CLASSES; ++cls) {
        probabilities[cls] = expf(logits[cls] - max_logit);
        sum += probabilities[cls];
    }

    float best_score = 0.0f;
    uint8_t best_class = 0;
    for (size_t cls = 0; cls < NUM_CLASSES; ++cls) {
        probabilities[cls] /= sum;
        if (probabilities[cls] > best_score) {
            best_score = probabilities[cls];
            best_class = (uint8_t)cls;
        }
    }
    return best_class;
}

static uint8_t tinyml_inference(const int8_t *window, float *probabilities) {
    float features[FEATURE_DIM];
    extract_features(window, features);
    return dense_softmax(features, probabilities);
}

static void run_dataset_evaluation(void) {
    size_t correct = 0;
    float probabilities[NUM_CLASSES];

    for (size_t i = 0; i < NUM_SAMPLES; ++i) {
        const tinyml_sample_t *sample = &DATASET[i];
        const uint8_t predicted =
            tinyml_inference(sample->signal, probabilities);
        if (predicted == sample->label) {
            ++correct;
        }

        printf("Sample %2zu -> predicted=%s (%.2f, %.2f, %.2f) | expected=%s\n",
               i, CLASS_NAMES[predicted], probabilities[0], probabilities[1],
               probabilities[2], CLASS_NAMES[sample->label]);
    }

    const float accuracy =
        (float)correct / (float)NUM_SAMPLES * 100.0f;
    printf("\nDataset accuracy: %.1f%% (%zu/%d)\n", accuracy, correct,
           NUM_SAMPLES);
}

static void run_microbenchmark(void) {
    float probabilities[NUM_CLASSES];
    uint32_t checksum = 0;

    for (int loop = 0; loop < INFERENCE_LOOP_COUNT; ++loop) {
        for (size_t i = 0; i < NUM_SAMPLES; ++i) {
            const uint8_t pred =
                tinyml_inference(DATASET[i].signal, probabilities);
            checksum += (uint32_t)(pred + loop);
        }
    }

    /*
     * Printing the checksum keeps the compiler from optimizing the loops away
     * and gives the simulator a deterministic data dependency to track.
     */
    printf("Microbenchmark checksum: %u (loops=%d)\n", checksum,
           INFERENCE_LOOP_COUNT);
}

int main(void) {
    printf("TinyML activity classifier benchmark\n");
    printf("------------------------------------\n\n");

    run_dataset_evaluation();
    run_microbenchmark();

    puts("\nBenchmark completed.");
    return 0;
}

