/**
 * @file host_main_mlp.c
 * @brief Runner host cho MLP 561-64-6: doc batch N x 570 float32 LE,
 *        dung 561 so dau (bo 9 so 0 dem), ghi CSV giong host_main --batch.
 *
 * Build/run qua firmware/host/run_mlp_host_test.sh (gcc -O2 -I firmware/common ... -lm).
 */
#include <stdio.h>
#include <string.h>

#include "mlp_har.h"

#define N_FEAT (10 * 57)

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
        int pred = mlp_har_forward_logits(sample, logits); /* 561 so dau */
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

    fprintf(stderr, "usage: %s --batch IN.f32 OUT.csv\n", argv[0]);
    return 1;
}
