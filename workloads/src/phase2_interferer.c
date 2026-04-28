// phase2_interferer.c
// Streaming cache/memory interferer for Phase 2 SMT experiments.

#define _GNU_SOURCE
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void usage(const char *prog) {
    fprintf(stderr,
        "Usage: %s [--iters N] [--array-kb N] [--stride N] [--write 0|1]\n"
        "  --iters N      outer loop iterations, default 20000\n"
        "  --array-kb N   streaming array size in KiB, default 4096\n"
        "  --stride N     byte stride, default 64\n"
        "  --write 0|1    whether to write while streaming, default 1\n",
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

int main(int argc, char **argv) {
    long iters = 20000;
    long array_kb = 4096;
    long stride = 64;
    long do_write = 1;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--iters") && i + 1 < argc) {
            iters = parse_long(argv[++i], "--iters");
        } else if (!strcmp(argv[i], "--array-kb") && i + 1 < argc) {
            array_kb = parse_long(argv[++i], "--array-kb");
        } else if (!strcmp(argv[i], "--stride") && i + 1 < argc) {
            stride = parse_long(argv[++i], "--stride");
        } else if (!strcmp(argv[i], "--write") && i + 1 < argc) {
            do_write = parse_long(argv[++i], "--write");
        } else if (!strcmp(argv[i], "--help")) {
            usage(argv[0]);
            return 0;
        } else {
            usage(argv[0]);
            return 2;
        }
    }

    if (iters <= 0 || array_kb <= 0 || stride <= 0) {
        fprintf(stderr, "iters, array-kb, and stride must be positive\n");
        return 2;
    }

    size_t bytes = (size_t)array_kb * 1024ULL;
    uint8_t *buf = NULL;
    if (posix_memalign((void **)&buf, 64, bytes) != 0 || buf == NULL) {
        perror("posix_memalign");
        return 1;
    }

    for (size_t i = 0; i < bytes; i++) {
        buf[i] = (uint8_t)(i * 17u + 3u);
    }

    volatile uint64_t sum = 0;
    for (long iter = 0; iter < iters; iter++) {
        // Offset rotates so the same first few lines are not the only lines touched.
        size_t start = ((size_t)iter * 64ULL) % (size_t)stride;
        for (size_t off = start; off < bytes; off += (size_t)stride) {
            sum += buf[off];
            if (do_write) {
                buf[off] = (uint8_t)(buf[off] + 1u);
            }
        }
    }

    printf("interferer done: iters=%ld array_kb=%ld stride=%ld write=%ld checksum=%" PRIu64 "\n",
           iters, array_kb, stride, do_write, (uint64_t)sum);

    free(buf);
    return 0;
}
