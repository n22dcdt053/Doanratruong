/**
 * @file energy_sched.h
 * @brief Lap lich phien do nang luong (Brief 07, muc 3). Ham thuan, khong phu thuoc ESP-IDF:
 *        xorshift32, hoan vi 60 mau, ke hoach 32 xung cua mot phien, phan tich lenh START.
 *        Ban Python tuong ung: tools/energy/schedule.py (Brief 08) phai khop tung byte
 *        voi test/sched_expected.txt.
 */
#ifndef ENERGY_SCHED_H
#define ENERGY_SCHED_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define ENERGY_N_PERM 60
#define ENERGY_BLOCK_INF 10 /* so suy luan moi khoi */
#define ENERGY_N_BLOCKS 6   /* khoi moi cau hinh */
#define ENERGY_N_EMPTY 10   /* xung rong moi cau hinh */
#define ENERGY_PULSES_PER_CFG (ENERGY_N_EMPTY + ENERGY_N_BLOCKS)
#define ENERGY_PULSES_PER_SESSION (2 * ENERGY_PULSES_PER_CFG) /* 32 */

enum { ENERGY_CFG_MAMBA = 0, ENERGY_CFG_MLP = 1 };
enum { ENERGY_KIND_EMP = 0, ENERGY_KIND_BLK = 1 };

typedef struct {
    uint8_t cfg;   /* ENERGY_CFG_* */
    uint8_t kind;  /* ENERGY_KIND_* */
    uint8_t block; /* 0..5 voi BLK; 0 voi EMP (khong dung) */
} energy_pulse_t;

/* x ^= x << 13; x ^= x >> 17; x ^= x << 5 (uint32). Trang thai khac 0. */
uint32_t xorshift32(uint32_t *s);

/* perm[i] = i; i tu 59 xuong 1: j = xorshift32(&s) % (i + 1); doi perm[i], perm[j]. seed 0 -> dung 1. */
void energy_permutation(uint32_t seed, uint8_t perm[ENERGY_N_PERM]);

/* Ke hoach 32 xung theo thu tu thuc te. order_mf != 0: Mamba truoc (MF); 0: MLP truoc (LF).
 * Moi cau hinh: 10 xung EMP roi 6 xung BLK (block 0..5). pulse = chi so + 1. */
void energy_pulse_plan(int order_mf, energy_pulse_t plan[ENERGY_PULSES_PER_SESSION]);

/* Phan tich mot dong lenh "START <session 1..5> <order MF|LF> <seed uint32>" (da bo '\r' '\n' cuoi).
 * Thanh cong: tra 0 va dien session/order_mf/seed. That bai: tra -1 va *reason la
 * chuoi ngan ("cmd", "argc", "session", "order", "seed") de in "ERR <reason>". */
int energy_parse_start(const char *line, int *session, int *order_mf, uint32_t *seed,
                       const char **reason);

#ifdef __cplusplus
}
#endif

#endif /* ENERGY_SCHED_H */
