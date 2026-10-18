/**
 * @file host_main.c
 * @brief PC (host) build of the exact C inference chain used by the
 *        Portenta H7 firmware (firmware/mambahar-portenta-h7/src/main.cpp).
 *
 * Purpose: smoke-test the C model without any MCU — same sources, same call:
 *   upstream csrc/{matrix,tensor,mamba}.c + example mambahar.c + sample_input.h
 * Build/run via run_host_test.ps1 (WSL gcc). Timing here is host wall clock,
 * NOT MCU evidence — board numbers still require the Portenta H7.
 * When firmware/common/mambahar.c becomes the modified dev copy, add its
 * directory as an earlier -I so this build picks it up instead of upstream.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>

#include "../../MambaLite-Micro/csrc/matrix.c"
#include "../../MambaLite-Micro/csrc/tensor.c"
#include "../../MambaLite-Micro/csrc/mamba.c"
#include "mambahar.c"
#include "sample_input.h"

static double now_us(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec * 1e6 + (double)ts.tv_nsec / 1e3;
}

static long rss_kb(void)
{
    FILE *f = fopen("/proc/self/statm", "r");
    long total = 0, resident = 0;
    if (!f)
        return -1;
    if (fscanf(f, "%ld %ld", &total, &resident) != 2)
        resident = -1;
    fclose(f);
    return resident < 0 ? -1 : resident * 4; /* Linux page = 4 KiB */
}

int main(int argc, char **argv)
{
    int iterations = argc > 1 ? atoi(argv[1]) : 1;
    if (iterations < 1)
        iterations = 1;

    long rss0 = rss_kb();
    double t0 = now_us();
    int pred = mambahar_forward(input_data); /* first 570 floats = [1, 10, 57] */
    for (int i = 1; i < iterations; i++)
        pred = mambahar_forward(input_data);
    double t1 = now_us();
    long rss1 = rss_kb();

    printf("Model_Forward completed.\n");
    printf("Prediction: %d\n", pred);
    printf("Elapsed time: %.0f us (host wall clock, %d run(s), NOT MCU timing)\n",
           t1 - t0, iterations);
    printf("Host RSS: %ld KB -> %ld KB (delta %ld KB over %d run(s))\n",
           rss0, rss1, rss1 - rss0, iterations);
    return 0;
}
