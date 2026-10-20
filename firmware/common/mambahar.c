/**
 * @file mambahar.c
 * @brief mambahar model — dev (vendor) copy for the DATN firmware.
 * Copyright (c) 2025 MambaLite-Micro Authors
 * Licensed under the MIT License.
 *
 * Upstream (unmodified, MIT, commit 44d51fc):
 *   MambaLite-Micro/examples/mambahar-arduino-6/include/mambahar.c
 * Every change vs upstream is recorded with its diff in HUONG_PHAT_TRIEN.md,
 * section "Diff cua ban vendor so voi upstream". Never edit the upstream file.
 */
#include <stdlib.h> /* free(): the csrc headers do not pull in <stdlib.h> */

#define B 1
#define T 10
#define F 57
#define H 64
#define C 6

/**
 * Same computation as upstream mambahar_forward(), plus the six pre-softmax
 * logits (MT2). logits may be NULL.
 * Return: argmax 0..C-1; -1 = allocation/kernel failure; -2 = non-finite
 * logits (invalid output — must NOT be counted as class 0).
 */
int mambahar_forward_logits(float *input, float *logits)
{
    Tensor *mamba_input = NULL, *output = NULL, *output_T = NULL;
    Matrix *pooled = NULL, *y = NULL;
    Mamba_Variables *model = NULL;
    int pred = -1;
    int max_idx = 0;

    mamba_input = tensor_zeros(B, T, H);
    if (!mamba_input)
        goto cleanup;
    for (int b = 0; b < B; b++)
    {
        for (int t = 0; t < T; t++)
        {
            for (int h = 0; h < H; h++)
            {
                float sum =linear_in_bias[h];
                for (int f = 0; f < F; f++)
                {
                    int input_idx = (b * T + t) * F + f;
                    int weight_idx = h * F + f;
                    sum += input[input_idx] * linear_in_weight_matrix.data[weight_idx];
                }
                int output_idx = (b * T + t) * H + h;
                mamba_input->data[output_idx] = sum;
            }
        }
    }
    model = Mamba_Init();
    if (!model)
        goto cleanup;
    output = tensor_zeros(B, T, H);
    if (!output)
        goto cleanup;
    if (Mamba_Forward(model, mamba_input, output) != Mamba_OK)
        goto cleanup;
    output_T = tensor_zeros(B, T, H);
    if (!output_T)
        goto cleanup;
    for (int b = 0; b < B; b++)
    {
        for (int t = 0; t < T; t++)
        {
            for (int h = 0; h < H; h++)
            {
                int in_idx = (b * T + t) * H + h;
                int out_idx = (b * H + h) * T + t;
                output_T->data[out_idx] = output->data[in_idx];
            }
        }
    }

    pooled = matrix_zeros(B, H);
    if (!pooled)
        goto cleanup;
    for (int b = 0; b < B; b++)
    {
        for (int h = 0; h < H; h++)
        {
            float sum = 0.0f;
            for (int t = 0; t < T; t++)
            {
                int idx = (b * H + h) * T + t; // [B, H, T]
                sum += output_T->data[idx];
            }
            pooled->data[b * H + h] = sum / T;
        }
    }
    y = matrix_zeros(B, C);
    if (!y)
        goto cleanup;
    for (int b_idx = 0; b_idx < B; b_idx++)
    {
        for (int c = 0; c < C; c++)
        {
            float sum = classifier_bias[c];
            for (int h = 0; h < H; h++)
            {
                sum += pooled->data[b_idx * H + h] * classifier_weight_matrix.data[c * H + h];
            }
            y->data[b_idx * C + c] = sum;
        }
    }
    for (int c = 0; c < C; c++)
    {
        if (logits)
        {
            logits[c] = y->data[c];
        }
        if (!isfinite(y->data[c]))
        {
            pred = -2; /* non-finite logits: report invalid, never a class */
            goto cleanup;
        }
    }
    for (int b = 0; b < B; b++)
    {
        max_idx = 0;
        float max_val = y->data[b * C];
        for (int c = 1; c < C; c++)
        {
            float val = y->data[b * C + c];
            if (val > max_val)
            {
                max_val = val;
                max_idx = c;
            }
        }
    }
    pred = max_idx;

cleanup:
    if (y)
        matrix_free(y);
    if (pooled)
        matrix_free(pooled);
    if (output_T)
        tensor_free(output_T);
    if (output)
        tensor_free(output);
    if (model)
        free(model);
    if (mamba_input)
        tensor_free(mamba_input);
    if (pred < 0 && logits)
    {
        for (int c = 0; c < C; c++)
        {
            logits[c] = NAN;
        }
    }
    return pred;
}

int mambahar_forward(float *input)
{
    return mambahar_forward_logits(input, NULL);
}
