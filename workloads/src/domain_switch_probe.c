#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef USE_M5OPS
#include <gem5/m5ops.h>
#else
static inline void m5_work_begin(uint64_t workid, uint64_t threadid) {
    (void)workid;
    (void)threadid;
}
#endif

static volatile uint64_t sink = 0;

static void touch_hot(uint64_t *arr, size_t words, int iters) {
    uint64_t acc = sink;
    for (int it = 0; it < iters; it++) {
        for (size_t i = 0; i < words; i += 8) {
            acc += arr[i];
            arr[i] = acc ^ i;
        }
    }
    sink = acc;
}

static void stream_large(uint64_t *arr, size_t words, int iters, size_t stride_words) {
    uint64_t acc = sink;
    if (stride_words == 0) stride_words = 8;
    for (int it = 0; it < iters; it++) {
        for (size_t i = 0; i < words; i += stride_words) {
            acc += arr[i];
            arr[i] = acc + i;
        }
    }
    sink = acc;
}

static long arg_long(int argc, char **argv, const char *key, long def) {
    for (int i = 1; i + 1 < argc; i++) {
        if (strcmp(argv[i], key) == 0) return strtol(argv[i + 1], NULL, 0);
    }
    return def;
}

int main(int argc, char **argv) {
    int phases = (int)arg_long(argc, argv, "--phases", 4);
    int phase_iters = (int)arg_long(argc, argv, "--phase-iters", 50);
    long hot_kb = arg_long(argc, argv, "--hot-kb", 64);
    long stream_kb = arg_long(argc, argv, "--stream-kb", 1024);
    long stride = arg_long(argc, argv, "--stride", 64);

    size_t hot_words = (size_t)hot_kb * 1024 / sizeof(uint64_t);
    size_t stream_words = (size_t)stream_kb * 1024 / sizeof(uint64_t);
    size_t stride_words = (size_t)stride / sizeof(uint64_t);

    uint64_t *hot = NULL;
    uint64_t *stream = NULL;
    if (posix_memalign((void **)&hot, 64, hot_words * sizeof(uint64_t)) != 0) return 2;
    if (posix_memalign((void **)&stream, 64, stream_words * sizeof(uint64_t)) != 0) return 3;

    for (size_t i = 0; i < hot_words; i++) hot[i] = i + 1;
    for (size_t i = 0; i < stream_words; i++) stream[i] = i + 3;

    for (int p = 0; p < phases; p++) {
        /* Domain A-like phase: smaller hot working set. */
        touch_hot(hot, hot_words, phase_iters);

        /* Boundary: next phase represents a different security domain. */
        m5_work_begin((uint64_t)(2 * p + 1), 0);

        /* Domain B-like phase: large streaming footprint. */
        stream_large(stream, stream_words, phase_iters, stride_words);

        /* Boundary back to domain A. */
        m5_work_begin((uint64_t)(2 * p + 2), 0);
    }

    printf("domain_switch_probe done sink=%llu\n", (unsigned long long)sink);
    free(hot);
    free(stream);
    return 0;
}
