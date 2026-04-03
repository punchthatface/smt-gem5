#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    uint64_t n = 200000000ULL;
    if (argc > 1) {
        n = strtoull(argv[1], NULL, 10);
    }

    volatile uint64_t x = 1;
    for (uint64_t i = 0; i < n; i++) {
        x = x * 1664525ULL + 1013904223ULL;
        x ^= (x >> 13);
        x ^= (x << 7);
    }

    printf("compute_done %llu\n", (unsigned long long)x);
    return 0;
}
