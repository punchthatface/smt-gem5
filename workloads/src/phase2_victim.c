// phase2_victim.c
// Controlled cache-sensitive victim for Phase 2 gem5 experiments.
// It optionally issues real x86 CLFLUSH instructions over its hot array.

#define _GNU_SOURCE
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <x86intrin.h>

static void usage(const char *prog) {
    fprintf(stderr,
        "Usage: %s [--iters N] [--array-kb N] [--flush-interval N] [--flush-bytes N]\n"
        "  --iters N            outer loop iterations, default 20000\n"
        "  --array-kb N         hot array size in KiB, default 256\n"
        "  --flush-interval N   every N iterations flush hot lines; 0 disables, default 0\n"
        "  --flush-bytes N      bytes to flush from array; 0 means whole array, default 0\n",
        prog);
}

static long parse_long(const char *s, const char *name) {
    char *end = NULL;
    errno = 0;
    long v = strtol(s, &end, 10);
    if (errno || end == s || *end != '\0' || v < 0) {
        fprintf(stderr, "Invalid %s: %s\n", name, s);
        exit(2);
    }
    return v;
}

static void flush_region(uint8_t *buf, size_t bytes) {
    const size_t line = 64;
    for (size_t off = 0; off < bytes; off += line) {
        _mm_clflush(buf + off);
    }
    _mm_mfence();
}

int main(int argc, char **argv) {
    long iters = 20000;
    long array_kb = 256;
    long flush_interval = 0;
    long flush_bytes_arg = 0;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--iters") && i + 1 < argc) {
            iters = parse_long(argv[++i], "--iters");
        } else if (!strcmp(argv[i], "--array-kb") && i + 1 < argc) {
            array_kb = parse_long(argv[++i], "--array-kb");
        } else if (!strcmp(argv[i], "--flush-interval") && i + 1 < argc) {
            flush_interval = parse_long(argv[++i], "--flush-interval");
        } else if (!strcmp(argv[i], "--flush-bytes") && i + 1 < argc) {
            flush_bytes_arg = parse_long(argv[++i], "--flush-bytes");
        } else if (!strcmp(argv[i], "--help")) {
            usage(argv[0]);
            return 0;
        } else {
            usage(argv[0]);
            return 2;
        }
    }

    if (iters <= 0 || array_kb <= 0) {
        fprintf(stderr, "iters and array-kb must be positive\n");
        return 2;
    }

    size_t bytes = (size_t)array_kb * 1024ULL;
    size_t flush_bytes = (flush_bytes_arg <= 0) ? bytes : (size_t)flush_bytes_arg;
    if (flush_bytes > bytes) flush_bytes = bytes;

    uint8_t *buf = NULL;
    if (posix_memalign((void **)&buf, 64, bytes) != 0 || buf == NULL) {
        perror("posix_memalign");
        return 1;
    }

    for (size_t i = 0; i < bytes; i++) {
        buf[i] = (uint8_t)(i * 131u + 7u);
    }

    volatile uint64_t sum = 0;
    const size_t line = 64;

    for (long iter = 0; iter < iters; iter++) {
        // Cache-line stride makes the hot set explicit and predictable.
        for (size_t off = 0; off < bytes; off += line) {
            sum += buf[off];
            buf[off] = (uint8_t)(buf[off] + 1u);
        }

        if (flush_interval > 0 && ((iter + 1) % flush_interval) == 0) {
            flush_region(buf, flush_bytes);
        }
    }

    printf("victim done: iters=%ld array_kb=%ld flush_interval=%ld flush_bytes=%zu checksum=%" PRIu64 "\n",
           iters, array_kb, flush_interval, flush_bytes, (uint64_t)sum);

    free(buf);
    return 0;
}
