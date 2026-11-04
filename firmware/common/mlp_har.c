/**
 * @file mlp_har.c
 * @brief Suy luan MLP 561-64-6 (FP32), vong lap tuan tu, khong cap phat dong.
 *
 * Thu tu tinh co dinh:
 *   - tang an: acc = b1[o] + sum_i w1[o][i] * x[i], i tang dan 0..560;
 *   - ReLU: h[o] = max(acc, 0);
 *   - tang ra: acc = b2[o] + sum_i w2[o][i] * h[i], i tang dan 0..63.
 * Moi phep tich luy dung float. Khong dung nhan, khong in.
 */
#include "mlp_har.h"

#include <math.h>

#include "mlp_weights.h"

int mlp_har_forward_logits(const float *x, float *logits)
{
    if (x == 0 || logits == 0)
        return -2;

    float h[MLP_HID];
    for (int o = 0; o < MLP_HID; o++)
    {
        const float *row = &mlp_w1[o * MLP_IN];
        float acc = mlp_b1[o];
        for (int i = 0; i < MLP_IN; i++)
            acc += row[i] * x[i];
        h[o] = acc > 0.0f ? acc : 0.0f;
    }

    for (int o = 0; o < MLP_OUT; o++)
    {
        const float *row = &mlp_w2[o * MLP_HID];
        float acc = mlp_b2[o];
        for (int i = 0; i < MLP_HID; i++)
            acc += row[i] * h[i];
        logits[o] = acc;
    }

    for (int o = 0; o < MLP_OUT; o++)
    {
        if (!isfinite(logits[o]))
            return -2;
    }

    int best = 0;
    for (int o = 1; o < MLP_OUT; o++)
    {
        if (logits[o] > logits[best])
            best = o;
    }
    return best;
}
