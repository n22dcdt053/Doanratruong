/**
 * @file energy_sched.c
 * @brief Cai dat energy_sched.h. Thuan C11, khong ESP-IDF, khong cap phat dong.
 */
#include "energy_sched.h"

#include <stddef.h>
#include <string.h>

uint32_t xorshift32(uint32_t *s)
{
    uint32_t x = *s;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *s = x;
    return x;
}

void energy_permutation(uint32_t seed, uint8_t perm[ENERGY_N_PERM])
{
    uint32_t s = seed ? seed : 1u;
    for (int i = 0; i < ENERGY_N_PERM; i++)
        perm[i] = (uint8_t)i;
    for (int i = ENERGY_N_PERM - 1; i >= 1; i--) {
        uint32_t j = xorshift32(&s) % (uint32_t)(i + 1);
        uint8_t t = perm[i];
        perm[i] = perm[j];
        perm[j] = t;
    }
}

void energy_pulse_plan(int order_mf, energy_pulse_t plan[ENERGY_PULSES_PER_SESSION])
{
    int n = 0;
    for (int c = 0; c < 2; c++) {
        uint8_t cfg = (uint8_t)((c == 0) == (order_mf != 0) ? ENERGY_CFG_MAMBA : ENERGY_CFG_MLP);
        for (int k = 0; k < ENERGY_N_EMPTY; k++) {
            plan[n].cfg = cfg;
            plan[n].kind = ENERGY_KIND_EMP;
            plan[n].block = 0;
            n++;
        }
        for (int b = 0; b < ENERGY_N_BLOCKS; b++) {
            plan[n].cfg = cfg;
            plan[n].kind = ENERGY_KIND_BLK;
            plan[n].block = (uint8_t)b;
            n++;
        }
    }
}

/* Tach mot token tu *p (cach nhau bang dau cach/tab). Tra con tro dau token va do dai; NULL neu het. */
static const char *next_token(const char **p, size_t *len)
{
    const char *q = *p;
    while (*q == ' ' || *q == '\t')
        q++;
    if (*q == '\0')
        return NULL;
    const char *start = q;
    while (*q != '\0' && *q != ' ' && *q != '\t')
        q++;
    *len = (size_t)(q - start);
    *p = q;
    return start;
}

int energy_parse_start(const char *line, int *session, int *order_mf, uint32_t *seed,
                       const char **reason)
{
    const char *p = line;
    size_t n;
    const char *t = next_token(&p, &n);
    if (t == NULL || n != 5 || memcmp(t, "START", 5) != 0) {
        *reason = "cmd";
        return -1;
    }
    const char *t_session = next_token(&p, &n);
    size_t n_session = n;
    const char *t_order = t_session ? next_token(&p, &n) : NULL;
    size_t n_order = n;
    const char *t_seed = t_order ? next_token(&p, &n) : NULL;
    size_t n_seed = n;
    if (t_session == NULL || t_order == NULL || t_seed == NULL || next_token(&p, &n) != NULL) {
        *reason = "argc";
        return -1;
    }
    if (n_session != 1 || t_session[0] < '1' || t_session[0] > '5') {
        *reason = "session";
        return -1;
    }
    int om;
    if (n_order == 2 && memcmp(t_order, "MF", 2) == 0)
        om = 1;
    else if (n_order == 2 && memcmp(t_order, "LF", 2) == 0)
        om = 0;
    else {
        *reason = "order";
        return -1;
    }
    if (n_seed == 0 || n_seed > 10) {
        *reason = "seed";
        return -1;
    }
    uint64_t v = 0;
    for (size_t i = 0; i < n_seed; i++) {
        if (t_seed[i] < '0' || t_seed[i] > '9') {
            *reason = "seed";
            return -1;
        }
        v = v * 10u + (uint64_t)(t_seed[i] - '0');
    }
    if (v > 0xFFFFFFFFull) {
        *reason = "seed";
        return -1;
    }
    *session = t_session[0] - '0';
    *order_mf = om;
    *seed = (uint32_t)v;
    return 0;
}
