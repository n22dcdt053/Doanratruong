/**
 * @file sched_host.c
 * @brief Chuong trinh PC (gcc, khong ESP-IDF) in ket qua lap lich ra stdout theo dinh dang co dinh.
 *        Ket qua luu o test/sched_expected.txt; tools/energy/schedule.py (Brief 08) so tung byte voi tep do.
 *        Build/chay: bash test/run_sched_host.sh [--update]
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif

#include "../src/energy_sched.h"

static int failures;

#define CHECK(cond)                                                          \
    do {                                                                     \
        if (!(cond)) {                                                       \
            fprintf(stderr, "CHECK FAILED %s:%d: %s\n", __FILE__, __LINE__, #cond); \
            failures++;                                                      \
        }                                                                    \
    } while (0)

static const char *cfg_name(int c) { return c == ENERGY_CFG_MAMBA ? "mamba" : "mlp"; }

static void print_perm(uint32_t seed)
{
    uint8_t perm[ENERGY_N_PERM];
    energy_permutation(seed, perm);
    int seen[ENERGY_N_PERM] = {0};
    for (int i = 0; i < ENERGY_N_PERM; i++) {
        CHECK(perm[i] < ENERGY_N_PERM);
        if (perm[i] < ENERGY_N_PERM)
            seen[perm[i]]++;
    }
    for (int i = 0; i < ENERGY_N_PERM; i++)
        CHECK(seen[i] == 1); /* du, khong trung */
    printf("# permutation seed=%u\n", (unsigned)seed);
    for (int i = 0; i < ENERGY_N_PERM; i++)
        printf("%s%u", i ? " " : "", (unsigned)perm[i]);
    printf("\n");
}

static void print_plan(int order_mf)
{
    energy_pulse_t plan[ENERGY_PULSES_PER_SESSION];
    energy_pulse_plan(order_mf, plan);
    printf("# pulse_plan order=%s pulses=%d\n", order_mf ? "MF" : "LF", ENERGY_PULSES_PER_SESSION);
    int emp[2] = {0, 0}, blk[2] = {0, 0};
    for (int i = 0; i < ENERGY_PULSES_PER_SESSION; i++) {
        if (plan[i].kind == ENERGY_KIND_EMP) {
            emp[plan[i].cfg]++;
            printf("pulse=%d cfg=%s kind=EMP block=-\n", i + 1, cfg_name(plan[i].cfg));
        } else {
            CHECK(plan[i].block == blk[plan[i].cfg]); /* khoi 0..5 theo thu tu */
            blk[plan[i].cfg]++;
            printf("pulse=%d cfg=%s kind=BLK block=%u\n", i + 1, cfg_name(plan[i].cfg), (unsigned)plan[i].block);
        }
    }
    for (int c = 0; c < 2; c++) {
        CHECK(emp[c] == ENERGY_N_EMPTY);
        CHECK(blk[c] == ENERGY_N_BLOCKS);
    }
    /* cau hinh dau chiem 16 xung dau */
    int first = order_mf ? ENERGY_CFG_MAMBA : ENERGY_CFG_MLP;
    for (int i = 0; i < ENERGY_PULSES_PER_CFG; i++)
        CHECK(plan[i].cfg == first);
    for (int i = ENERGY_PULSES_PER_CFG; i < ENERGY_PULSES_PER_SESSION; i++)
        CHECK(plan[i].cfg != first);
}

static void try_start(const char *line)
{
    int s = 0, mf = 0;
    uint32_t seed = 0;
    const char *why = "";
    if (energy_parse_start(line, &s, &mf, &seed, &why) == 0)
        printf("%s -> ACK session=%d order=%s seed=%u pulses=%d plan=%s\n", line, s, mf ? "MF" : "LF",
               (unsigned)seed, ENERGY_PULSES_PER_SESSION, mf ? "MF" : "LF");
    else
        printf("%s -> ERR %s\n", line, why);
}

int main(void)
{
#ifdef _WIN32
    _setmode(_fileno(stdout), _O_BINARY); /* giu LF */
#endif
    printf("# energy_sched host test (Brief 07, muc 3). Dinh dang co dinh; Brief 08 so tung byte.\n");

    uint32_t s = 1;
    printf("# xorshift32 seed=1 five outputs:");
    for (int i = 0; i < 5; i++)
        printf(" %u", (unsigned)xorshift32(&s));
    printf("\n");
    s = 1;
    CHECK(xorshift32(&s) == 270369u);

    print_perm(1);
    print_perm(42);
    print_perm(123456789);

    /* seed 0 dung nhu seed 1 */
    uint8_t p0[ENERGY_N_PERM], p1[ENERGY_N_PERM];
    energy_permutation(0, p0);
    energy_permutation(1, p1);
    CHECK(memcmp(p0, p1, sizeof p0) == 0);
    printf("# seed 0 == seed 1: %s\n", memcmp(p0, p1, sizeof p0) == 0 ? "yes" : "no");

    printf("# START hop le (seed 42), 5 phien x 2 thu tu; ke hoach xung khong phu thuoc phien\n");
    char line[64];
    for (int ss = 1; ss <= 5; ss++) {
        for (int o = 0; o < 2; o++) {
            snprintf(line, sizeof line, "START %d %s 42", ss, o ? "LF" : "MF");
            try_start(line);
        }
    }
    printf("# START sai/bien\n");
    const char *bad[] = {"", "START", "START 1 MF", "STOP 1 MF 1", "START 0 MF 1", "START 6 MF 1",
                         "START 10 MF 1", "START 1 XX 1", "START 1 mf 1", "START 1 MF -5",
                         "START 1 MF 4294967296", "START 1 MF 4294967295", "START 1 MF 0",
                         "START 1 MF 1 extra", "START 1 MF 12ab", "START 1 MF 00000000042"};
    for (size_t i = 0; i < sizeof bad / sizeof bad[0]; i++)
        try_start(bad[i]);

    print_plan(1);
    print_plan(0);

    /* ke hoach chi phu thuoc order */
    energy_pulse_t a[ENERGY_PULSES_PER_SESSION], b[ENERGY_PULSES_PER_SESSION];
    energy_pulse_plan(1, a);
    energy_pulse_plan(1, b);
    CHECK(memcmp(a, b, sizeof a) == 0);

    if (failures) {
        fprintf(stderr, "%d CHECK that bai\n", failures);
        return 1;
    }
    return 0;
}
