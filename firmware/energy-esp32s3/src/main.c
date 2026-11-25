/**
 * @file main.c
 * @brief Firmware do nang luong cho devkit ESP32-S3 (Brief 07): Mamba huan luyen lai va MLP
 *        trong mot firmware, GPIO marker bao quanh moi khoi 10 suy luan.
 *
 * Phan dich vu: INA226 + logger XIAO (Brief 08) do dong cap cho devkit; chan marker (mac dinh
 * GPIO4) cho logger biet khoi suy luan bat dau/ket thuc. Giao thuc, trinh tu phien va dinh dang
 * dong in nam o Brief 07 muc 3 (chep nguyen van trong README.md).
 *
 * Adapted from MambaLite-Micro (MIT License, commit 44d51fc), nhu firmware/mamba-retrained-esp32s3:
 * upstream csrc/matrix.c include theo duong dan tuong doi; mamba.c/mambahar.c vendored o
 * firmware/common/ (khong sua). Mamba: ml/results/mamba_retrained/mamba_weights.h (platformio.ini dat
 * thu muc do dau tien trong -I). MLP: firmware/common/mlp_har.c + mlp_weights.h. Hai mo hinh duoc goi
 * NGUYEN VAN qua mambahar_forward_logits va mlp_har_forward_logits.
 *
 * Cau hinh build giong firmware Mamba huan luyen lai: -Og, 160 MHz (sdkconfig byte-identical),
 * nen so do khong dai dien hieu nang toi uu. Nguong sai so 1e-4 / 1e-5 chua duoc GVHD xac nhan;
 * maxdl chi la so do, khong phai ket luan dat/khong dat.
 *
 * Trong vung marker cao KHONG in, KHONG doc UART, KHONG vTaskDelay: chi chep truoc 10 mau vao RAM,
 * keo marker len, 10 suy luan, keo xuong. Ket qua duoc in SAU khi marker xuong.
 */
#include <inttypes.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "sdkconfig.h"
#include "driver/gpio.h"
#include "driver/uart.h"
#include "esp_attr.h"
#include "esp_rom_sys.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

/* MLP truoc: mlp_har.c keo <math.h>; mambahar.c dinh nghia cac macro B, T, F, H, C. */
#include "../../common/mlp_har.c"
#include "../../../MambaLite-Micro/csrc/matrix.c"
#include "../../common/mamba.c"
#include "../../common/mambahar.c"

#include "build_info.h"
#include "energy_samples.h"
#include "energy_sched.h"

/* ---- Chan (doi duoc luc build: -DENERGY_MARKER_GPIO=n) ---- */
#ifndef ENERGY_MARKER_GPIO
#define ENERGY_MARKER_GPIO 4
#endif
#if ENERGY_MARKER_GPIO == 0 || ENERGY_MARKER_GPIO == 3 || \
    (ENERGY_MARKER_GPIO >= 19 && ENERGY_MARKER_GPIO <= 20) || \
    (ENERGY_MARKER_GPIO >= 26 && ENERGY_MARKER_GPIO <= 37) || \
    (ENERGY_MARKER_GPIO >= 43 && ENERGY_MARKER_GPIO <= 48)
#error "ENERGY_MARKER_GPIO khong duoc la GPIO 0, 3, 19, 20, 26-37, 43-48 (Brief 07, muc 3)"
#endif
#define CMD_UART UART_NUM_0 /* console mac dinh: GPIO43 TX, GPIO44 RX, 115200 8N1 */

/* ---- Tham so phien (Brief 07, muc 3) ---- */
#ifndef ENERGY_EMPTY_PULSE_US
/* Xung rong giu cao ~1 ms de logger (ISR) tach duoc hai canh; brief khong ghi do rong. */
#define ENERGY_EMPTY_PULSE_US 1000
#endif
#define IDLE_START_MS 10000 /* nghi nen dau phien */
#define WARMUP_RUNS 20
#define WARMUP_REST_MS 2000
#define EMPTY_GAP_MS 100
#define BLOCK_REST_MS 2000
#define CFG_REST_MS 5000
#define READY_EVERY_US 2000000
#define LINE_CAP 64
#define BOOT_MAGIC 0x48415231u /* "HAR1" */

#define IN_STRIDE (ENERGY_N_FEAT + 9) /* 561 + 9 so 0 = 570 (Mamba); MLP chi doc 561 so dau */

static const char *const cfg_str[2] = {"mamba", "mlp"};

// Chi dung de in ma reset + dem lan boot luc khoi dong (khong in trong phien).
RTC_NOINIT_ATTR static uint32_t g_boot_magic;
RTC_NOINIT_ATTR static uint32_t g_boot_count;

// Bo dem dau vao nap san: 10 mau. 9 so 0 cuoi moi hang khong bao gio bi ghi -> luon bang 0 (.bss).
static float g_in[ENERGY_BLOCK_INF][IN_STRIDE];
static float g_lg[ENERGY_BLOCK_INF][6];
static int g_pred[ENERGY_BLOCK_INF];
static int64_t g_emp_rise[ENERGY_N_EMPTY], g_emp_fall[ENERGY_N_EMPTY];
static uint8_t g_perm[ENERGY_N_PERM];
static volatile int g_sink; // giu lan chay on dinh khoi bi toi uu bo

static int mamba_fwd(float *x, float *lg) { return mambahar_forward_logits(x, lg); }
static int mlp_fwd(float *x, float *lg) { return mlp_har_forward_logits(x, lg); }
typedef int (*fwd_fn)(float *, float *);
static const fwd_fn fwd_of[2] = {mamba_fwd, mlp_fwd};

static const char *reset_reason_name(esp_reset_reason_t r)
{
    switch ((int)r) {
    case ESP_RST_POWERON: return "POWERON";
    case ESP_RST_EXT: return "EXT";
    case ESP_RST_SW: return "SW";
    case ESP_RST_PANIC: return "PANIC";
    case ESP_RST_INT_WDT: return "INT_WDT";
    case ESP_RST_TASK_WDT: return "TASK_WDT";
    case ESP_RST_WDT: return "WDT";
    case ESP_RST_DEEPSLEEP: return "DEEPSLEEP";
    case ESP_RST_BROWNOUT: return "BROWNOUT";
    case ESP_RST_SDIO: return "SDIO";
    case ESP_RST_USB: return "USB";
    case ESP_RST_JTAG: return "JTAG";
    case ESP_RST_EFUSE: return "EFUSE";
    case ESP_RST_PWR_GLITCH: return "PWR_GLITCH";
    case ESP_RST_CPU_LOCKUP: return "CPU_LOCKUP";
    default: return "UNKNOWN";
    }
}

static inline void marker_high(void) { gpio_set_level(ENERGY_MARKER_GPIO, 1); }
static inline void marker_low(void) { gpio_set_level(ENERGY_MARKER_GPIO, 0); }

static void rest_ms(uint32_t ms) { vTaskDelay(pdMS_TO_TICKS(ms)); }

/* Doc tung ky tu tu UART0 (driver, ngat). Tra 1 khi co du mot dong (bo '\r' '\n'), 0 neu chua,
 * -1 neu dong qua dai (da bo toi het dong). Cho toi da wait_ms ky tu dau tien (vTaskDelay ben trong driver). */
static int poll_line(char *buf, int wait_ms)
{
    static int len = 0;
    static int overflow = 0;
    for (;;) {
        uint8_t c;
        int n = uart_read_bytes(CMD_UART, &c, 1, pdMS_TO_TICKS(wait_ms));
        if (n <= 0)
            return 0;
        wait_ms = 0;
        if (c == '\r')
            continue;
        if (c == '\n') {
            int ok = !overflow;
            buf[len] = '\0';
            len = 0;
            overflow = 0;
            return ok ? 1 : -1;
        }
        if (len < LINE_CAP - 1)
            buf[len++] = (char)c;
        else
            overflow = 1;
    }
}

/* Chay mot lan 20 suy luan on dinh (khong marker, khong in). */
static void warmup(int cfg)
{
    for (int i = 0; i < WARMUP_RUNS; i++) {
        int idx = g_perm[i % ENERGY_N_PERM];
        memcpy(g_in[0], energy_features[idx], ENERGY_N_FEAT * sizeof(float));
        g_sink += fwd_of[cfg](g_in[0], g_lg[0]);
        vTaskDelay(1); // ngoai vung do: nhuong IDLE de task WDT duoc nuoi
    }
}

/* 10 xung rong lien tiep (nghi EMPTY_GAP_MS giua hai xung), in ket qua SAU. */
static void empty_pulses(int session, int cfg, int *pulse)
{
    for (int k = 0; k < ENERGY_N_EMPTY; k++) {
        marker_high();
        g_emp_rise[k] = esp_timer_get_time();
        esp_rom_delay_us(ENERGY_EMPTY_PULSE_US);
        g_emp_fall[k] = esp_timer_get_time();
        marker_low();
        rest_ms(EMPTY_GAP_MS);
    }
    for (int k = 0; k < ENERGY_N_EMPTY; k++) {
        printf("EMP s=%d cfg=%s pulse=%d t_rise_us=%" PRIu64 " t_fall_us=%" PRIu64 "\n", session,
               cfg_str[cfg], *pulse + 1, (uint64_t)g_emp_rise[k], (uint64_t)g_emp_fall[k]);
        (*pulse)++;
    }
}

/* Mot khoi 10 suy luan. Chep dau vao TRUOC khi keo marker len; in ket qua SAU khi marker xuong. */
static void run_block(int session, int cfg, int b, int *pulse)
{
    int idx[ENERGY_BLOCK_INF];
    for (int k = 0; k < ENERGY_BLOCK_INF; k++) {
        idx[k] = g_perm[ENERGY_BLOCK_INF * b + k];
        memcpy(g_in[k], energy_features[idx[k]], ENERGY_N_FEAT * sizeof(float));
    }
    const fwd_fn fwd = fwd_of[cfg];

    marker_high();
    int64_t t_rise = esp_timer_get_time();
    for (int k = 0; k < ENERGY_BLOCK_INF; k++)
        g_pred[k] = fwd(g_in[k], g_lg[k]);
    int64_t t_fall = esp_timer_get_time();
    marker_low();

    /* --- tu day moi duoc in / so sanh --- */
    const float(*ref)[6] = cfg == ENERGY_CFG_MAMBA ? energy_ref_mamba : energy_ref_mlp;
    const uint8_t *ref_pred = cfg == ENERGY_CFG_MAMBA ? energy_ref_mamba_pred : energy_ref_mlp_pred;
    float maxdl = 0.0f;
    int invalid = 0;
    for (int k = 0; k < ENERGY_BLOCK_INF; k++) {
        if (g_pred[k] < 0) {
            invalid++;
            continue;
        }
        for (int c = 0; c < 6; c++) {
            float d = fabsf(g_lg[k][c] - ref[idx[k]][c]);
            if (d > maxdl)
                maxdl = d;
        }
    }
    static char line[400];
    int n = snprintf(line, sizeof line,
                     "BLK s=%d b=%d cfg=%s pulse=%d t_rise_us=%" PRIu64 " t_fall_us=%" PRIu64 " n=%d idx=",
                     session, b, cfg_str[cfg], *pulse + 1, (uint64_t)t_rise, (uint64_t)t_fall,
                     ENERGY_BLOCK_INF);
    for (int k = 0; k < ENERGY_BLOCK_INF; k++)
        n += snprintf(line + n, sizeof line - n, "%s%d", k ? "," : "", idx[k]);
    n += snprintf(line + n, sizeof line - n, " pred=");
    for (int k = 0; k < ENERGY_BLOCK_INF; k++)
        n += snprintf(line + n, sizeof line - n, "%s%d", k ? "," : "", g_pred[k]);
    n += snprintf(line + n, sizeof line - n, " ref=");
    for (int k = 0; k < ENERGY_BLOCK_INF; k++)
        n += snprintf(line + n, sizeof line - n, "%s%d", k ? "," : "", (int)ref_pred[idx[k]]);
    snprintf(line + n, sizeof line - n, " maxdl=%.3e invalid=%d\n", (double)maxdl, invalid);
    fputs(line, stdout);
    (*pulse)++;
}

static void run_session(int session, int order_mf, uint32_t seed)
{
    printf("ACK session=%d order=%s seed=%" PRIu32 "\n", session, order_mf ? "MF" : "LF", seed);

    rest_ms(IDLE_START_MS); // 1. nghi nen (marker thap)
    energy_permutation(seed, g_perm); // 2. cung mot hoan vi cho ca hai cau hinh

    int pulse = 0;
    for (int c = 0; c < 2; c++) { // 3.
        int cfg = (c == 0) == (order_mf != 0) ? ENERGY_CFG_MAMBA : ENERGY_CFG_MLP;
        warmup(cfg); // a.
        rest_ms(WARMUP_REST_MS);
        empty_pulses(session, cfg, &pulse); // b.
        rest_ms(BLOCK_REST_MS);
        for (int b = 0; b < ENERGY_N_BLOCKS; b++) { // c.
            run_block(session, cfg, b, &pulse);
            if (b < ENERGY_N_BLOCKS - 1)
                rest_ms(BLOCK_REST_MS);
        }
        rest_ms(CFG_REST_MS); // d.
    }
    printf("SESSION_DONE session=%d\n", session); // 4.
    uart_flush_input(CMD_UART);
}

#define ENERGY_TASK_STACK 8192
static void energy_task(void *arg);

void app_main(void)
{
    // Marker thap ngay tu dau app_main (dat muc truoc, roi moi doi sang dau ra, tranh xung gai).
    gpio_reset_pin(ENERGY_MARKER_GPIO);
    gpio_set_level(ENERGY_MARKER_GPIO, 0);
    gpio_set_direction(ENERGY_MARKER_GPIO, GPIO_MODE_OUTPUT);

    esp_reset_reason_t rr = esp_reset_reason();
    if (g_boot_magic != BOOT_MAGIC) {
        g_boot_magic = BOOT_MAGIC;
        g_boot_count = 0;
    }
    const uint32_t boot_no = ++g_boot_count;

#if defined(CONFIG_COMPILER_OPTIMIZATION_PERF)
    const char *opt = "perf(-O2)";
#elif defined(CONFIG_COMPILER_OPTIMIZATION_SIZE)
    const char *opt = "size(-Os)";
#elif defined(CONFIG_COMPILER_OPTIMIZATION_DEBUG)
    const char *opt = "debug(-Og)";
#else
    const char *opt = "custom";
#endif

    uart_driver_install(CMD_UART, 256, 0, 0, NULL, 0);

    printf("\nFW commit %s (%s) built %s UTC | opt=%s\n", FW_GIT_COMMIT, FW_GIT_DIRTY, FW_BUILD_UTC, opt);
    printf("Reset: reason=%d (%s) | boot #%" PRIu32 " since RTC_NOINIT init\n", (int)rr,
           reset_reason_name(rr), boot_no);
    printf("Energy firmware: Mamba (retrained, seed 42) + MLP, %d samples, marker GPIO%d, UART0 115200\n",
           ENERGY_N_SAMPLES, ENERGY_MARKER_GPIO);

    // sdkconfig co dinh (byte-identical) nen stack app_main chi 3584 B; vong phien (snprintf %e + chuoi goi
    // sau hon) chay trong task rieng 8 KB, cung loi 0 va cung muc uu tien voi app_main.
    xTaskCreatePinnedToCore(energy_task, "energy", ENERGY_TASK_STACK, NULL, uxTaskPriorityGet(NULL), NULL, 0);
}

static void energy_task(void *arg)
{
    (void)arg;
    static char cmd[LINE_CAP];
    int64_t next_ready = 0;
    for (;;) {
        int64_t now = esp_timer_get_time();
        if (now >= next_ready) {
            printf("READY fw=%s gpio=%d\n", FW_GIT_COMMIT, ENERGY_MARKER_GPIO);
            next_ready = now + READY_EVERY_US;
        }
        int r = poll_line(cmd, 100); // cho lenh: blocking trong driver, khong busy-wait
        if (r == 0)
            continue;
        if (r < 0) {
            printf("ERR argc\n"); // dong qua dai
            continue;
        }
        int session, order_mf;
        uint32_t seed;
        const char *why = "";
        if (energy_parse_start(cmd, &session, &order_mf, &seed, &why) != 0) {
            printf("ERR %s\n", why);
            continue;
        }
        run_session(session, order_mf, seed);
        next_ready = 0; // in READY ngay sau SESSION_DONE
    }
}
