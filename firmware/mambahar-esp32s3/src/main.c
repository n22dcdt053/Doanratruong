/**
 * @file main.c
 * @brief Mamba HAR inference on ESP32-S3 — dev project for DATN.
 *
 * Adapted from MambaLite-Micro (MIT License, commit 44d51fc):
 *  - examples/mambakws-esp32-3/src/main.c (ESP-IDF app shell)
 *  - examples/mambahar-arduino-6 (HAR model wrapper + weights + sample input)
 * Upstream sources are included by relative path and stay unmodified; the HAR
 * model wrapper + mamba kernel are vendored under firmware/common/ so thesis
 * changes stay outside the upstream checkout (see HUONG_PHAT_TRIEN.md).
 */
#include <stdio.h>
#include <inttypes.h>
#include "sdkconfig.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_timer.h"
#include "esp_system.h"
#include "../../../MambaLite-Micro/csrc/matrix.c"
#include "../../common/mamba.c"
#include "../../common/mambahar.c"
#include "sample_input.h"

// shortcut: single-sample run then reboot, same as upstream examples; multi-sample
// loop arrives with the thesis MT2 work (UART protocol + logits output).
void app_main(void)
{
    for (int i = 5; i >= 0; i--) {
        printf("starting in %d seconds...\n", i);
        vTaskDelay(1000 / portTICK_PERIOD_MS);
    }

    printf("Free heap before: %" PRIu32 " bytes\n", esp_get_free_heap_size());

    int64_t start = esp_timer_get_time();
    int pred = mambahar_forward(input_data);
    int64_t end = esp_timer_get_time();

    printf("Model_Forward completed.\n");
    printf("Prediction: %d\n", pred);
    if (pred < 0) {
        printf("Output: INVALID (%s), pred=%d is not a class\n",
               pred == -2 ? "non-finite logits" : "allocation/kernel failure", pred);
    }
    printf("Elapsed time: %lld microseconds (%.2f milliseconds)\n",
           end - start, (end - start) / 1000.0);
    printf("Free heap after: %" PRIu32 " bytes\n", esp_get_free_heap_size());
    printf("Min free heap ever: %" PRIu32 " bytes\n", esp_get_minimum_free_heap_size());

    for (int i = 10; i >= 0; i--) {
        printf("Restarting in %d seconds...\n", i);
        vTaskDelay(1000 / portTICK_PERIOD_MS);
    }
    printf("Restarting now.\n");
    fflush(stdout);
    esp_restart();
}
