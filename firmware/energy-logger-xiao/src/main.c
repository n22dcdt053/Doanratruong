/**
 * @file main.c
 * @brief Logger do nang luong tren XIAO ESP32S3 (Brief 08, H1).
 *
 * Doc INA226 (I2C, ma tho thanh ghi shunt 0x01 / bus 0x02) va bat canh len/xuong cua chan marker tu devkit,
 * gan cung mot dong ho esp_timer (us), gui ra PC qua USB Serial/JTAG (CDC), mot dong/ban ghi, CSV:
 *   S,<t_us>,<shunt_raw>,<bus_raw>          mot mau INA226 (shunt la so co dau 16 bit)
 *   E,<t_us>,<level 0|1>                    mot canh marker (1 = len)
 *   X,<t_us>,<ma loi i2c>                   loi I2C (esp_err_t)
 *   STAT,<t_us>,samples=<n>,edges=<n>,drops=<n>,i2c_err=<n>   moi 5 s
 *   PING,<t_us>   SELFTEST_DONE   ERR <ly do>
 * Dong tieu de '# fw=...' in luc khoi dong va lap lai sau moi dong STAT (de capture mo muon van thay).
 * Khong dung thanh ghi calibration/current/power cua INA226; quy doi o PC.
 *
 * Chan (XIAO ESP32S3): I2C SDA=D4=GPIO5, SCL=D5=GPIO6; marker vao D0=GPIO1; tu kiem ra D3=GPIO4.
 */
#include <inttypes.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "driver/usb_serial_jtag.h"
#include "esp_attr.h"
#include "esp_rom_sys.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "hal/gpio_ll.h"
#include "soc/gpio_struct.h"

#include "build_info.h"

#ifndef LOGGER_SDA_GPIO
#define LOGGER_SDA_GPIO 5 /* D4 */
#endif
#ifndef LOGGER_SCL_GPIO
#define LOGGER_SCL_GPIO 6 /* D5 */
#endif
#ifndef LOGGER_MARKER_GPIO
#define LOGGER_MARKER_GPIO 1 /* D0 */
#endif
#ifndef LOGGER_SELFTEST_GPIO
#define LOGGER_SELFTEST_GPIO 4 /* D3 (khong dung D2 = GPIO3: chan strapping) */
#endif
#if LOGGER_MARKER_GPIO == LOGGER_SELFTEST_GPIO || LOGGER_MARKER_GPIO == LOGGER_SDA_GPIO || \
    LOGGER_MARKER_GPIO == LOGGER_SCL_GPIO || LOGGER_SELFTEST_GPIO == LOGGER_SDA_GPIO || \
    LOGGER_SELFTEST_GPIO == LOGGER_SCL_GPIO
#error "cac chan logger phai khac nhau"
#endif

#define INA_ADDR 0x40
#define INA_REG_CONFIG 0x00
#define INA_REG_SHUNT 0x01
#define INA_REG_BUS 0x02
#define INA_REG_MASK 0x06
#define INA_REG_MANUF 0xFE
#define INA_REG_DIE 0xFF
#define INA_MANUF_ID 0x5449
#define INA_MASK_CVRF (1u << 3)
/* AVG = 000 (1), VBUSCT = VSHCT = 100 (1,1 ms), MODE = 111 (shunt + bus, lien tuc); bit 14 luon = 1 */
#define INA_CFG ((uint16_t)(0x4000 | (0u << 9) | (4u << 6) | (4u << 3) | 7u))
#define INA_AVG_SAMPLES 1
#define INA_VCT_US 1100
#define I2C_TIMEOUT_MS 20
#define I2C_FREQ_HZ 400000

#define QUEUE_LEN 2048
#define STAT_PERIOD_US 5000000
#define BATCH_BYTES 1024
#define TX_RING_BYTES 8192
#define USB_WRITE_TICKS pdMS_TO_TICKS(20)

#define SELFTEST_PULSES 20
#define SELFTEST_HIGH_US 1000
#define SELFTEST_LOW_US 4000

enum { REC_S = 0, REC_E = 1, REC_X = 2 };

typedef struct {
    int64_t t;
    int32_t a; /* S: shunt_raw | E: level | X: ma loi */
    int32_t b; /* S: bus_raw */
    uint8_t type;
} rec_t;

static QueueHandle_t g_q;
static SemaphoreHandle_t g_out_mx;
static i2c_master_bus_handle_t g_bus;
static i2c_master_dev_handle_t g_dev;
static char g_header[200];

static volatile uint32_t g_samples, g_edges, g_drops, g_i2c_err;

/* Ly do khoi dong that bai (de lap lai moi 5 s, vi dong ERR luc boot co the mat khi chua co ben doc USB) */
static const char *g_fail_reason = "";
static int g_fail_err;      /* esp_err_t cua lenh I2C that bai (0 neu khong phai loi bus) */
static uint16_t g_fail_mfr; /* ina226_id: gia tri doc duoc; ina226_cfg: thanh ghi cau hinh doc lai */

/* ------------------------------------------------------------------ dau ra USB-CDC */

/* Ghi mot khoi (gom nhieu dong day du) duoi mutex de cac task khong chen giua dong. Tra true neu ghi het. */
static bool out_write(const char *s, size_t n)
{
    bool ok = true;
    xSemaphoreTake(g_out_mx, portMAX_DELAY);
    size_t off = 0;
    int stalls = 0;
    while (off < n) {
        int w = usb_serial_jtag_write_bytes(s + off, n - off, USB_WRITE_TICKS);
        if (w <= 0) {
            if (++stalls >= 2) {
                ok = false;
                break;
            }
            continue;
        }
        off += (size_t)w;
    }
    xSemaphoreGive(g_out_mx);
    return ok;
}

static void out_line(const char *fmt, ...) __attribute__((format(printf, 1, 2)));
static void out_line(const char *fmt, ...)
{
    char buf[160];
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(buf, sizeof buf - 1, fmt, ap);
    va_end(ap);
    if (n < 0)
        return;
    if ((size_t)n > sizeof buf - 2)
        n = (int)sizeof buf - 2;
    buf[n++] = '\n';
    if (!out_write(buf, (size_t)n))
        g_drops++;
}

static int fmt_rec(char *dst, size_t cap, const rec_t *r)
{
    switch (r->type) {
    case REC_S:
        return snprintf(dst, cap, "S,%lld,%d,%d\n", (long long)r->t, (int)r->a, (int)r->b);
    case REC_E:
        return snprintf(dst, cap, "E,%lld,%d\n", (long long)r->t, (int)r->a);
    default:
        return snprintf(dst, cap, "X,%lld,%d\n", (long long)r->t, (int)r->a);
    }
}

/* Task in: lay ban ghi tu hang doi, gom thanh khoi, ghi USB; moi 5 s in STAT va lap lai dong tieu de. */
static void printer_task(void *arg)
{
    (void)arg;
    static char batch[BATCH_BYTES + 128];
    size_t n = 0;
    uint32_t lines = 0;
    int64_t next_stat = esp_timer_get_time() + STAT_PERIOD_US;
    rec_t r;
    for (;;) {
        TickType_t wait = n ? 0 : pdMS_TO_TICKS(20);
        if (xQueueReceive(g_q, &r, wait) == pdTRUE) {
            int k = fmt_rec(batch + n, sizeof batch - n, &r);
            if (k > 0) {
                n += (size_t)k;
                lines++;
            }
        }
        bool flush = n >= BATCH_BYTES || (n && uxQueueMessagesWaiting(g_q) == 0);
        int64_t now = esp_timer_get_time();
        if (now >= next_stat) {
            int k = snprintf(batch + n, sizeof batch - n,
                             "STAT,%lld,samples=%lu,edges=%lu,drops=%lu,i2c_err=%lu\n%s\n", (long long)now,
                             (unsigned long)g_samples, (unsigned long)g_edges, (unsigned long)g_drops,
                             (unsigned long)g_i2c_err, g_header);
            if (k > 0 && (size_t)k < sizeof batch - n) {
                n += (size_t)k;
                lines += 2;
            }
            next_stat += STAT_PERIOD_US;
            flush = true;
        }
        if (flush && n) {
            if (!out_write(batch, n))
                g_drops += lines;
            n = 0;
            lines = 0;
        }
    }
}

/* ------------------------------------------------------------------ INA226 */

static esp_err_t ina_read(uint8_t reg, uint16_t *out)
{
    uint8_t b[2];
    esp_err_t e = i2c_master_transmit_receive(g_dev, &reg, 1, b, 2, I2C_TIMEOUT_MS);
    if (e == ESP_OK)
        *out = (uint16_t)((b[0] << 8) | b[1]);
    return e;
}

static esp_err_t ina_write(uint8_t reg, uint16_t v)
{
    uint8_t b[3] = {reg, (uint8_t)(v >> 8), (uint8_t)v};
    return i2c_master_transmit(g_dev, b, sizeof b, I2C_TIMEOUT_MS);
}

static void push_x(esp_err_t e)
{
    rec_t r = {.t = esp_timer_get_time(), .a = (int32_t)e, .b = 0, .type = REC_X};
    g_i2c_err++;
    if (xQueueSend(g_q, &r, 0) != pdTRUE)
        g_drops++;
}

/* Vong doc: poll thanh ghi Mask/Enable (doc xoa co CVRF); khi CVRF = 1 doc shunt roi bus; thoi diem = ngay sau
 * khi doc xong 0x02. Khong in o day. Loi I2C: dong X, thu lai sau 5 ms. */
static void reader_task(void *arg)
{
    (void)arg;
    for (;;) {
        uint16_t me;
        esp_err_t e = ina_read(INA_REG_MASK, &me);
        if (e != ESP_OK) {
            push_x(e);
            vTaskDelay(pdMS_TO_TICKS(5));
            continue;
        }
        if (!(me & INA_MASK_CVRF))
            continue; /* moi lan doc I2C da nhuong CPU (cho semaphore), khong chiem loi */
        uint16_t sh, bus;
        if ((e = ina_read(INA_REG_SHUNT, &sh)) != ESP_OK || (e = ina_read(INA_REG_BUS, &bus)) != ESP_OK) {
            push_x(e);
            vTaskDelay(pdMS_TO_TICKS(5));
            continue;
        }
        rec_t r = {.t = esp_timer_get_time(), .a = (int16_t)sh, .b = bus, .type = REC_S};
        g_samples++;
        if (xQueueSend(g_q, &r, 0) != pdTRUE)
            g_drops++;
    }
}

/* ------------------------------------------------------------------ marker */

static void IRAM_ATTR marker_isr(void *arg)
{
    (void)arg;
    rec_t r;
    r.t = esp_timer_get_time();
    r.a = gpio_ll_get_level(&GPIO, LOGGER_MARKER_GPIO);
    r.b = 0;
    r.type = REC_E;
    BaseType_t hp = pdFALSE;
    g_edges++;
    if (xQueueSendFromISR(g_q, &r, &hp) != pdTRUE)
        g_drops++;
    if (hp == pdTRUE)
        portYIELD_FROM_ISR();
}

/* ------------------------------------------------------------------ lenh tu PC */

static void selftest(void)
{
    for (int i = 0; i < SELFTEST_PULSES; i++) {
        gpio_set_level(LOGGER_SELFTEST_GPIO, 1);
        esp_rom_delay_us(SELFTEST_HIGH_US);
        gpio_set_level(LOGGER_SELFTEST_GPIO, 0);
        esp_rom_delay_us(SELFTEST_LOW_US);
    }
    vTaskDelay(pdMS_TO_TICKS(100)); /* cho cac dong E cua xung tu kiem ra truoc */
    out_line("SELFTEST_DONE");
}

static void command_task(void *arg)
{
    (void)arg;
    char line[16];
    size_t n = 0;
    bool overflow = false;
    for (;;) {
        uint8_t c;
        if (usb_serial_jtag_read_bytes(&c, 1, pdMS_TO_TICKS(100)) != 1)
            continue;
        if (c == '\r')
            continue;
        if (c != '\n') {
            if (n < sizeof line)
                line[n++] = (char)c;
            else
                overflow = true;
            continue;
        }
        if (n == 0 && !overflow)
            continue; /* dong trong: bo qua */
        if (!overflow && n == 1 && line[0] == 'P')
            out_line("PING,%lld", (long long)esp_timer_get_time());
        else if (!overflow && n == 1 && line[0] == 'T')
            selftest();
        else
            out_line("ERR cmd");
        n = 0;
        overflow = false;
    }
}

/* ------------------------------------------------------------------ khoi dong */

static esp_err_t init_i2c(void)
{
    i2c_master_bus_config_t bc = {
        .i2c_port = I2C_NUM_0,
        .sda_io_num = LOGGER_SDA_GPIO,
        .scl_io_num = LOGGER_SCL_GPIO,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = true, /* them pull-up noi bo; module INA226 thuong co pull-up rieng */
    };
    esp_err_t e = i2c_new_master_bus(&bc, &g_bus);
    if (e != ESP_OK)
        return e;
    i2c_device_config_t dc = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = INA_ADDR,
        .scl_speed_hz = I2C_FREQ_HZ,
    };
    return i2c_master_bus_add_device(g_bus, &dc, &g_dev);
}

/* Kiem ID, reset + ghi cau hinh + doc lai. Tra true neu duoc phep do. Sai -> in ERR va KHONG do. */
static bool init_ina226(uint16_t *mfr, uint16_t *die)
{
    esp_err_t e = ina_read(INA_REG_MANUF, mfr);
    if (e == ESP_OK)
        e = ina_read(INA_REG_DIE, die);
    if (e != ESP_OK) {
        g_fail_reason = "ina226_id";
        g_fail_err = (int)e;
        out_line("X,%lld,%d", (long long)esp_timer_get_time(), (int)e);
        out_line("ERR ina226_id");
        return false;
    }
    if (*mfr != INA_MANUF_ID) {
        g_fail_reason = "ina226_id";
        g_fail_mfr = *mfr;
        out_line("ERR ina226_id");
        return false;
    }
    uint16_t back = 0;
    e = ina_write(INA_REG_CONFIG, 0x8000); /* RST */
    if (e != ESP_OK) {
        g_fail_reason = "ina226_cfg";
        g_fail_err = (int)e;
        out_line("ERR ina226_cfg");
        return false;
    }
    vTaskDelay(pdMS_TO_TICKS(2));
    e = ina_write(INA_REG_CONFIG, INA_CFG);
    if (e == ESP_OK)
        e = ina_read(INA_REG_CONFIG, &back);
    if (e != ESP_OK || back != INA_CFG) {
        g_fail_reason = "ina226_cfg";
        g_fail_err = (int)e;
        g_fail_mfr = back; /* gia tri doc lai thanh ghi cau hinh */
        out_line("ERR ina226_cfg");
        return false;
    }
    return true;
}

void app_main(void)
{
    g_out_mx = xSemaphoreCreateMutex();
    g_q = xQueueCreate(QUEUE_LEN, sizeof(rec_t));
    usb_serial_jtag_driver_config_t uc = USB_SERIAL_JTAG_DRIVER_CONFIG_DEFAULT();
    uc.tx_buffer_size = TX_RING_BYTES;
    usb_serial_jtag_driver_install(&uc);

    gpio_config_t st = {
        .pin_bit_mask = 1ULL << LOGGER_SELFTEST_GPIO,
        .mode = GPIO_MODE_OUTPUT,
    };
    gpio_config(&st);
    gpio_set_level(LOGGER_SELFTEST_GPIO, 0);

    xTaskCreatePinnedToCore(printer_task, "printer", 4096, NULL, 5, NULL, 0);
    xTaskCreatePinnedToCore(command_task, "command", 3072, NULL, 6, NULL, 0);

    uint16_t mfr = 0, die = 0;
    bool measure = false;
    esp_err_t ie = init_i2c();
    if (ie == ESP_OK) {
        measure = init_ina226(&mfr, &die);
    } else {
        g_fail_reason = "ina226_id";
        g_fail_err = (int)ie;
        out_line("ERR ina226_id");
    }

    if (measure) {
        snprintf(g_header, sizeof g_header,
                 "# fw=%s cfg=0x%04x avg=%d vct_us=%d rshunt_nominal_ohm=0.1 marker_gpio=%d mfr_id=0x%04x "
                 "die_id=0x%04x fw_tree=%s",
                 FW_GIT_COMMIT, (unsigned)INA_CFG, INA_AVG_SAMPLES, INA_VCT_US, LOGGER_MARKER_GPIO,
                 (unsigned)mfr, (unsigned)die, FW_GIT_DIRTY);
        out_write(g_header, strlen(g_header));
        out_write("\n", 1);
    } else {
        snprintf(g_header, sizeof g_header,
                 "# fw=%s ERR ina226 (khong do) reason=%s i2c_esp_err=%d value=0x%04x\nERR %s", FW_GIT_COMMIT,
                 g_fail_reason, g_fail_err, (unsigned)g_fail_mfr, g_fail_reason);
    }

    /* canh marker o ca hai che do (marker van ghi ngay ca khi INA226 loi) */
    gpio_config_t mk = {
        .pin_bit_mask = 1ULL << LOGGER_MARKER_GPIO,
        .mode = GPIO_MODE_INPUT,
        .pull_down_en = GPIO_PULLDOWN_ENABLE,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .intr_type = GPIO_INTR_ANYEDGE,
    };
    gpio_config(&mk);
    gpio_install_isr_service(ESP_INTR_FLAG_IRAM);
    gpio_isr_handler_add(LOGGER_MARKER_GPIO, marker_isr, NULL);

    if (measure)
        xTaskCreatePinnedToCore(reader_task, "reader", 4096, NULL, 20, NULL, 1);
    vTaskDelete(NULL);
}
