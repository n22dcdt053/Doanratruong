/**
 * @file main.c
 * @brief Mamba HAR inference on ESP32-S3 - bring-up proxy for the DATN.
 *
 * Adapted from MambaLite-Micro (MIT License, commit 44d51fc):
 *  - examples/mambakws-esp32-3/src/main.c (ESP-IDF app shell)
 *  - examples/mambahar-arduino-6 (HAR model wrapper + weights)
 * Upstream sources are included by relative path and stay unmodified; the HAR
 * model wrapper + mamba kernel are vendored under firmware/common/ so thesis
 * changes stay outside the upstream checkout (see HUONG_PHAT_TRIEN.md).
 *
 * Scope: ESP32-S3 bring-up only (protocol + numerics smoke test). This is NOT
 * acceptance evidence: the thesis criteria (1.000-run stability, Flash/RAM map
 * file, energy) require the Portenta H7 target.
 *
 * Mode: 1000 consecutive inferences on 20 rotating UCI samples (all 6 classes),
 * single boot, no per-run prints inside the timing loop, WDT fed by a one-tick
 * delay outside the measured window. Host reference logits are embedded so the
 * board prints tier-B error (max|dlogit|, MAE, label mismatches) on-device.
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>
#include "sdkconfig.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_timer.h"
#include "esp_system.h"
#include "../../../MambaLite-Micro/csrc/matrix.c"
#include "../../common/mamba.c"
#include "../../common/mambahar.c"
#include "uci_samples.h"

#define N_SAMPLES 20
#define N_RUNS 1000

static uint32_t t_us[N_RUNS]; // 4 KB .bss; sorted in place for percentiles

static int cmp_u32(const void *a, const void *b)
{
    uint32_t x = *(const uint32_t *)a, y = *(const uint32_t *)b;
    return (x > y) - (x < y);
}

void app_main(void)
{
    for (int i = 3; i >= 0; i--) {
        printf("starting in %d seconds...\n", i);
        vTaskDelay(1000 / portTICK_PERIOD_MS);
    }

    printf("ESP32-S3 bring-up (proxy for Portenta H7; NOT acceptance evidence)\n");
    printf("Stability+numerics: %d runs x %d UCI samples, quiet loop, WDT fed\n", N_RUNS, N_SAMPLES);
    printf("Free heap at start: %" PRIu32 " bytes\n", esp_get_free_heap_size());

    float e_max = 0.0f;
    float per_sample_max[N_SAMPLES];
    int last_pred[N_SAMPLES];
    for (int s = 0; s < N_SAMPLES; s++) {
        per_sample_max[s] = 0.0f;
        last_pred[s] = -3;
    }
    double mae_sum = 0.0;
    long comparisons = 0, invalid = 0, label_mismatch = 0;

    for (int r = 0; r < N_RUNS; r++) {
        int s = r % N_SAMPLES;
        float logits[6];
        int64_t t0 = esp_timer_get_time();
        int pred = mambahar_forward_logits((float *)uci_samples[s], logits);
        int64_t t1 = esp_timer_get_time();
        t_us[r] = (uint32_t)(t1 - t0);
        last_pred[s] = pred;

        if (pred < 0) {
            invalid++;
        } else {
            if (pred != (int)uci_host_pred[s]) {
                label_mismatch++;
            }
            for (int c = 0; c < 6; c++) {
                float d = fabsf(logits[c] - uci_host_logits[s][c]);
                if (d > e_max) {
                    e_max = d;
                }
                if (d > per_sample_max[s]) {
                    per_sample_max[s] = d;
                }
                mae_sum += d;
                comparisons++;
            }
        }
        // Outside the measured window: yield to IDLE0 so the task watchdog is fed.
        vTaskDelay(1);
    }

    qsort(t_us, N_RUNS, sizeof(t_us[0]), cmp_u32);
    printf("BENCH DONE: runs=%d samples=%d invalid=%ld label_mismatch=%ld\n",
           N_RUNS, N_SAMPLES, invalid, label_mismatch);
    printf("tierB (on-device, vs embedded host logits): comparisons=%ld max|dlogit|=%.3e MAE=%.3e\n",
           comparisons, (double)e_max, mae_sum / (double)comparisons);
    printf("time_us: min=%" PRIu32 " p50=%" PRIu32 " p95=%" PRIu32 " max=%" PRIu32 "\n",
           t_us[0], t_us[N_RUNS / 2], t_us[(int)(N_RUNS * 95 / 100)], t_us[N_RUNS - 1]);
    printf("heap: end=%" PRIu32 " min_ever=%" PRIu32 " bytes\n",
           esp_get_free_heap_size(), esp_get_minimum_free_heap_size());

    for (int s = 0; s < N_SAMPLES; s++) {
        printf("sample %d (idx %d): pred=%d host_pred=%d max|d|=%.3e\n",
               s, uci_index[s], last_pred[s], (int)uci_host_pred[s],
               (double)per_sample_max[s]);
    }
    printf("No reset during test; no prints inside the timing loop.\n");
}
