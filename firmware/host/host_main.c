/**
 * @file host_main.c
 * @brief PC (host) build of the C inference chain used by the Portenta H7
 *        firmware (firmware/mambahar-portenta-h7/src/main.cpp).
 *
 * Sources: firmware/common/mamba.c + mambahar.c (vendored dev copies) +
 * upstream csrc/{matrix,tensor}.c + upstream weights/sample headers.
 * Timing here is host wall clock, NOT MCU evidence.
 *
 * Modes (via run_host_test.ps1 / run_host_test.sh):
 *   host_main <iterations>            single-sample: prediction, logits, RSS
 *   host_main --batch IN.f32 OUT.csv  N x 570 float32 (LE) -> idx,pred,6 logits
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>

#include "../../MambaLite-Micro/csrc/matrix.c"
#include "../../MambaLite-Micro/csrc/tensor.c"
#include "mamba.c"
#include "mambahar.c"
#include "sample_input.h"

#define N_FEAT (10 * 57)

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

static int run_batch(const char *in_path, const char *out_path)
{
    FILE *fin = fopen(in_path, "rb");
    if (!fin)
    {
        fprintf(stderr, "cannot open input %s\n", in_path);
        return 1;
    }
    FILE *fout = fopen(out_path, "w");
    if (!fout)
    {
        fprintf(stderr, "cannot open output %s\n", out_path);
        fclose(fin);
        return 1;
    }

    float sample[N_FEAT];
    long idx = 0;
    int bad = 0;
    fprintf(fout, "sample_index,pred,logit0,logit1,logit2,logit3,logit4,logit5\n");
    while (fread(sample, sizeof(float), N_FEAT, fin) == N_FEAT)
    {
        float logits[6] = {0};
        int pred = mambahar_forward_logits(sample, logits);
        fprintf(fout, "%ld,%d,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g\n", idx, pred,
                (double)logits[0], (double)logits[1], (double)logits[2],
                (double)logits[3], (double)logits[4], (double)logits[5]);
        idx++;
    }
    if (!feof(fin))
    {
        fprintf(stderr, "trailing partial sample in %s\n", in_path);
        bad = 1;
    }
    fclose(fin);
    fclose(fout);
    printf("Batch: %ld samples -> %s%s\n", idx, out_path,
           bad ? " (PARTIAL TRAILING DATA)" : "");
    return bad;
}

int main(int argc, char **argv)
{
    if (argc == 4 && strcmp(argv[1], "--batch") == 0)
        return run_batch(argv[2], argv[3]);

    int iterations = argc > 1 ? atoi(argv[1]) : 1;
    if (iterations < 1)
        iterations = 1;

    long rss0 = rss_kb();
    double t0 = now_us();
    float logits[6] = {0};
    int pred = mambahar_forward_logits(input_data, logits); /* first 570 floats = [1, 10, 57] */
    for (int i = 1; i < iterations; i++)
        pred = mambahar_forward_logits(input_data, logits);
    double t1 = now_us();
    long rss1 = rss_kb();

    printf("Model_Forward completed.\n");
    printf("Prediction: %d\n", pred);
    if (pred < 0)
        printf("Output: INVALID (%s), pred=%d is not a class\n",
               pred == -2 ? "non-finite logits" : "allocation/kernel failure", pred);
    printf("Logits: %.9g %.9g %.9g %.9g %.9g %.9g\n",
           (double)logits[0], (double)logits[1], (double)logits[2],
           (double)logits[3], (double)logits[4], (double)logits[5]);
    printf("Elapsed time: %.0f us (host wall clock, %d run(s), NOT MCU timing)\n",
           t1 - t0, iterations);
    printf("Host RSS: %ld KB -> %ld KB (delta %ld KB over %d run(s))\n",
           rss0, rss1, rss1 - rss0, iterations);
    return pred == -1 ? 1 : 0; /* -2 = invalid input/output, run itself completed */
}
