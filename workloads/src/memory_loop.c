#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    uint64_t n = 20000000ULL;
    size_t sz = 16 * 1024 * 1024;

    if (argc > 1) {
        n = strtoull(argv[1], NULL, 10);
    }
    if (argc > 2) {
        sz = (size_t)strtoull(argv[2], NULL, 10);
    }

    uint8_t *arr = (uint8_t *)malloc(sz);
    if (!arr) {
        perror("malloc");
        return 1;
    }

    for (size_t i = 0; i < sz; i++) {
        arr[i] = (uint8_t)(i & 0xff);
    }

    volatile uint64_t sum = 0;
    for (uint64_t iter = 0; iter < n; iter++) {
        size_t idx = (iter * 64) % sz;
        arr[idx] ^= (uint8_t)(iter & 0xff);
        sum += arr[idx];
    }

    printf("memory_done %llu\n", (unsigned long long)sum);
    free(arr);
    return 0;
}
