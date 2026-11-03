/**
 * @file main.c
 * @brief Mamba HAR inference benchmark on the ESP32-S3 (DATN target platform).
 *
 * Adapted from MambaLite-Micro (MIT License, commit 44d51fc):
 *  - examples/mambakws-esp32-3/src/main.c (ESP-IDF app shell)
 *  - examples/mambahar-arduino-6 (HAR model wrapper + weights)
 * Upstream sources are included by relative path and stay unmodified; the HAR
 * model wrapper + mamba kernel are vendored under firmware/common/ so thesis
 * changes stay outside the upstream checkout (see HUONG_PHAT_TRIEN.md).
 *
 * Scope: the ESP32-S3 is the project's primary target (the switch from Portenta
 * H7 was agreed with the advisor by message; no written record yet). Error
 * thresholds (1e-4 / 1e-5) are pending advisor confirmation, so the measured
 * errors are reported as numbers, not as "passed". The build is -Og at 160 MHz,
 * so the timings are not representative of performance.
 *
 * Mode: 1000 consecutive inferences on 20 rotating UCI samples (all 6 classes),
 * single boot, no per-run prints inside the timing loop, WDT fed by a one-tick
 * delay outside the measured window. Firmware prints its git commit + build
 * time, esp_reset_reason(), and an RTC_NOINIT boot counter so "no reset" is
 * evidence, not a fixed string. Host reference logits are embedded, so the
 * board reports max|dlogit| / MAE / label mismatches on-device.
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>
#include "sdkconfig.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_attr.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "../../../MambaLite-Micro/csrc/matrix.c"
#include "../../common/mamba.c"
#include "../../common/mambahar.c"
#include "build_info.h"
#include "uci_samples.h"

#define N_SAMPLES 20
#define N_RUNS 1000
#define HEAP_EVERY 50
#define BOOT_MAGIC 0x48415231u /* "HAR1" */
#define TEST_IDLE 0u
#define TEST_RUNNING 0x52554E31u /* "RUN1" */
#define TEST_DONE 0x444F4E45u    /* "DONE" */

static uint32_t t_us[N_RUNS]; // 4 KB .bss; sorted in place for percentiles
static uint32_t heap_samples[N_RUNS / HEAP_EVERY + 1];

// Survive software/WDT resets (not a power cycle).
RTC_NOINIT_ATTR static uint32_t g_boot_magic;
RTC_NOINIT_ATTR static uint32_t g_boot_count;
// A TEST_RUNNING value left here by a previous boot proves that run was
// interrupted by a reset. Comparing counters at the start and end of one
// app_main call proves nothing (they always match; after a reset the final
// line is simply never printed). "No reset" evidence is: reason=POWERON,
// exactly one "Test start" line, and boot_count=1.
RTC_NOINIT_ATTR static uint32_t g_test_state;

static int cmp_u32(const void *a, const void *b)
{
    uint32_t x = *(const uint32_t *)a, y = *(const uint32_t *)b;
    return (x > y) - (x < y);
}

static const char *reset_reason_name(esp_reset_reason_t r)
{
    switch ((int)r) {
    case ESP_RST_POWERON:
        return "POWERON";
    case ESP_RST_EXT:
        return "EXT";
    case ESP_RST_SW:
        return "SW";
    case ESP_RST_PANIC:
        return "PANIC";
    case ESP_RST_INT_WDT:
        return "INT_WDT";
    case ESP_RST_TASK_WDT:
        return "TASK_WDT";
    case ESP_RST_WDT:
        return "WDT";
    case ESP_RST_DEEPSLEEP:
        return "DEEPSLEEP";
    case ESP_RST_BROWNOUT:
        return "BROWNOUT";
    case ESP_RST_SDIO:
        return "SDIO";
    case ESP_RST_USB:
        return "USB";
    case ESP_RST_JTAG:
        return "JTAG";
    case ESP_RST_EFUSE:
        return "EFUSE";
    case ESP_RST_PWR_GLITCH:
        return "PWR_GLITCH";
    case ESP_RST_CPU_LOCKUP:
        return "CPU_LOCKUP";
    default:
        return "UNKNOWN";
    }
}

void app_main(void)
{
    esp_reset_reason_t rr = esp_reset_reason();
    int first_init = 0;
    if (g_boot_magic != BOOT_MAGIC) {
        g_boot_magic = BOOT_MAGIC;
        g_boot_count = 0;
        g_test_state = TEST_IDLE;
        first_init = 1;
    }
    const uint32_t boot_no = ++g_boot_count;
    const int prev_interrupted = !first_init && g_test_state == TEST_RUNNING;

#if defined(CONFIG_COMPILER_OPTIMIZATION_PERF)
    const char *opt = "perf(-O2)";
#elif defined(CONFIG_COMPILER_OPTIMIZATION_SIZE)
    const char *opt = "size(-Os)";
#elif defined(CONFIG_COMPILER_OPTIMIZATION_DEBUG)
    const char *opt = "debug(-Og)";
#else
    const char *opt = "custom";
#endif

    // Print the banner after the countdown: the capture script opens the port a
    // couple of seconds after the esptool reset, so anything printed earlier is
    // lost and the log would not carry its own commit/reset evidence.
    for (int i = 5; i >= 0; i--) {
        printf("starting in %d seconds...\n", i);
        vTaskDelay(1000 / portTICK_PERIOD_MS);
    }

    printf("FW commit %s (%s) built %s UTC | opt=%s\n",
           FW_GIT_COMMIT, FW_GIT_DIRTY, FW_BUILD_UTC, opt);
    printf("Reset: reason=%d (%s) | boot #%" PRIu32 " since RTC_NOINIT init\n",
           (int)rr, reset_reason_name(rr), boot_no);
    printf("Previous test: %s\n",
           first_init ? "none"
                      : prev_interrupted ? "INTERRUPTED (reset during test)"
                                         : g_test_state == TEST_DONE ? "completed" : "none");

    printf("ESP32-S3 HAR benchmark (target platform; error thresholds pending advisor confirmation)\n");
    printf("Stability+numerics: %d runs x %d UCI samples, quiet loop, WDT fed\n",
           N_RUNS, N_SAMPLES);
    g_test_state = TEST_RUNNING;
    printf("Test start: boot #%" PRIu32 " | free heap %" PRIu32 " bytes\n",
           boot_no, esp_get_free_heap_size());

    float e_max = 0.0f;
    float per_sample_max[N_SAMPLES];
    int last_pred[N_SAMPLES];
    for (int s = 0; s < N_SAMPLES; s++) {
        per_sample_max[s] = 0.0f;
        last_pred[s] = -3;
    }
    double mae_sum = 0.0, t_sum = 0.0, t_sq = 0.0;
    long comparisons = 0, invalid = 0, label_mismatch = 0;

    for (int r = 0; r < N_RUNS; r++) {
        int s = r % N_SAMPLES;
        float logits[6];
        int64_t t0 = esp_timer_get_time();
        int pred = mambahar_forward_logits((float *)uci_samples[s], logits);
        int64_t t1 = esp_timer_get_time();
        uint32_t us = (uint32_t)(t1 - t0);
        t_us[r] = us;
        t_sum += us;
        t_sq += (double)us * us;
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
        if (r % HEAP_EVERY == 0) {
            heap_samples[r / HEAP_EVERY] = esp_get_free_heap_size();
        }
        // Outside the measured window: yield to IDLE0 so the task watchdog is fed.
        vTaskDelay(1);
    }
    g_test_state = TEST_DONE;
    heap_samples[N_RUNS / HEAP_EVERY] = esp_get_free_heap_size();

    qsort(t_us, N_RUNS, sizeof(t_us[0]), cmp_u32);
    double mean = t_sum / N_RUNS;
    double var = t_sq / N_RUNS - mean * mean;
    if (var < 0.0) {
        var = 0.0;
    }

    printf("BENCH DONE: runs=%d samples=%d invalid=%ld label_mismatch=%ld\n",
           N_RUNS, N_SAMPLES, invalid, label_mismatch);
    printf("numerics vs host (Xtensa/ESP-IDF/C; error thresholds pending advisor confirmation): "
           "comparisons=%ld (distinct sample x logit pairs=%d, each repeated %dx; deterministic) "
           "max|dlogit|=%.3e MAE=%.3e\n",
           comparisons, N_SAMPLES * 6, N_RUNS / N_SAMPLES,
           (double)e_max, mae_sum / (double)comparisons);
    printf("time_us: min=%" PRIu32 " p50=%" PRIu32 " p95=%" PRIu32 " max=%" PRIu32
           " mean=%.0f sd=%.0f\n",
           t_us[0], t_us[N_RUNS / 2], t_us[(int)(N_RUNS * 95 / 100)], t_us[N_RUNS - 1],
           mean, sqrt(var));
    printf("heap: end=%" PRIu32 " min_ever=%" PRIu32 " bytes\n",
           esp_get_free_heap_size(), esp_get_minimum_free_heap_size());
    printf("heap every %d runs (bytes):", HEAP_EVERY);
    for (int i = 0; i <= N_RUNS / HEAP_EVERY; i++) {
        printf(" %" PRIu32, heap_samples[i]);
    }
    printf("\n");

    for (int s = 0; s < N_SAMPLES; s++) {
        printf("sample %d (idx %d): pred=%d host_pred=%d max|d|=%.3e\n",
               s, uci_index[s], last_pred[s], (int)uci_host_pred[s],
               (double)per_sample_max[s]);
    }
    printf("Resets: boot_count=%" PRIu32 " prev_test_interrupted=%d | %s\n",
           g_boot_count, prev_interrupted,
           (boot_no == 1 && !prev_interrupted) ? "power-on clean run" : "REBOOTED since RTC init");
}
