/*
 * Unit tests for atop_agg helpers. Compiled with --coverage; aims for
 * 100% line coverage of atop_agg.c (excluding main, which is guarded
 * by -DATOP_AGG_NO_MAIN).
 */
#include "atop_agg.h"

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;

#define CHECK(cond)                                                                                \
    do                                                                                             \
    {                                                                                              \
        if (!(cond))                                                                               \
        {                                                                                          \
            fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);                        \
            failures++;                                                                            \
        }                                                                                          \
    } while (0)

static void test_copy_name(void)
{
    char buf[16];
    copy_name(buf, sizeof(buf), "(bash)");
    CHECK(strcmp(buf, "bash") == 0);

    copy_name(buf, sizeof(buf), "bash");
    CHECK(strcmp(buf, "bash") == 0);

    copy_name(buf, sizeof(buf), "()");
    CHECK(strcmp(buf, "unknown") == 0);

    copy_name(buf, sizeof(buf), "");
    CHECK(strcmp(buf, "unknown") == 0);

    /* Truncation. */
    copy_name(buf, sizeof(buf), "(veryverylongnameabc)");
    CHECK(strlen(buf) == sizeof(buf) - 1);

    /* Fallback truncation: buf too small for "unknown" itself. */
    char tiny[4];
    copy_name(tiny, sizeof(tiny), "");
    CHECK(strcmp(tiny, "unk") == 0);
}

static void test_tokenize(void)
{
    char  line[] = "PRC host 1000 2026/01/01 12:00:00 600 123 (bash) S 10 20\n";
    char *toks[32];
    int   n = tokenize_line(line, toks, 32);
    CHECK(n == 11);
    CHECK(strcmp(toks[0], "PRC") == 0);
    CHECK(strcmp(toks[7], "(bash)") == 0);
    CHECK(strcmp(toks[10], "20") == 0);

    /* Multi-word parenthesised name. */
    char  line2[] = "PRM host 1000 d t 600 200 (Web Content) S 4096 1 2 0 0\n";
    char *t2[32];
    int   n2 = tokenize_line(line2, t2, 32);
    CHECK(n2 >= 12);
    CHECK(strncmp(t2[7], "(Web Content)", 13) == 0);

    /* Empty / whitespace-only line. */
    char  empty[] = "   \n";
    char *t3[4];
    CHECK(tokenize_line(empty, t3, 4) == 0);

    /* Max-tokens cap respected. */
    char  big[] = "a b c d e f g h i j k";
    char *t4[3];
    CHECK(tokenize_line(big, t4, 3) == 3);

    /* Unclosed paren at EOL — consumed to end. */
    char  unclosed[] = "(abc";
    char *t5[2];
    int   n5 = tokenize_line(unclosed, t5, 2);
    CHECK(n5 == 1);
    CHECK(strcmp(t5[0], "(abc") == 0);
}

static void test_process_and_emit(void)
{
    State *s = state_new();
    assert(s != NULL);

    /* Two PRC samples for PID 100: first utime+stime=30, last=100.
       Delta should be 70. */
    char prc1[] = "PRC h 1000 d t 600 100 (cc1) S 10 20\n";
    char prc2[] = "PRC h 1600 d t 600 100 (cc1) S 70 30\n";
    process_line(prc1, s);
    process_line(prc2, s);

    /* One PRM sample for PID 100: rss=4096 kB. */
    char prm1[] = "PRM h 1000 d t 600 100 (cc1) S 4096 100 4096 0 0\n";
    process_line(prm1, s);

    /* PRC sample for PID 200 seen only once → delta == last_ticks. */
    char prc3[] = "PRC h 1000 d t 600 200 (short) S 5 5\n";
    process_line(prc3, s);

    /* Header / separator / unknown label should be ignored. */
    char header[] = "# comment line\n";
    process_line(header, s);
    char sep[] = "SEP\n";
    process_line(sep, s);
    char other[] = "CPU h 1000 d t 600 0 0 0 0 0 0 0 0\n";
    process_line(other, s);

    /* Malformed: pid <= 0. */
    char bad_pid[] = "PRC h 1000 d t 600 0 (x) S 1 1\n";
    process_line(bad_pid, s);

    /* PRC short (<11 tokens) should not crash. */
    char prc_short[] = "PRC h 1000 d t 600 300 (y) S 1\n";
    process_line(prc_short, s);

    /* PRM short (<12 tokens) should not crash. */
    char prm_short[] = "PRM h 1000 d t 600 300 (y) S 4096 1 1 0\n";
    process_line(prm_short, s);

    /* Emit and sanity-check the output. */
    char  *buf = NULL;
    size_t sz  = 0;
    FILE  *out = open_memstream(&buf, &sz);
    assert(out != NULL);
    emit_results(s, out);
    fclose(out);
    CHECK(strstr(buf, "W\t1000\t1600\t2\t600\n") != NULL);
    /* cc1: cpu delta 70 (pid 100 two samples) + 0 pids column via max(cpu,ram).
       Peak RSS 4096, sum_avg 4096, rss_samples 1, pids max(1,1)=1. */
    CHECK(strstr(buf, "N\tcc1\t70\t4096\t4096\t1\t1\n") != NULL);
    /* short: single-sample pid 200 → delta == 10; no RAM, so peak/sum/rss=0. */
    CHECK(strstr(buf, "N\tshort\t10\t0\t0\t0\t1\n") != NULL);
    free(buf);
    state_free(s);
}

static void test_empty_and_single_epoch(void)
{
    State *s = state_new();
    /* No input at all → window line with zeroes. */
    char  *buf = NULL;
    size_t sz  = 0;
    FILE  *out = open_memstream(&buf, &sz);
    emit_results(s, out);
    fclose(out);
    CHECK(strstr(buf, "W\t0\t0\t0\t0\n") != NULL);
    free(buf);
    state_free(s);

    /* Exactly one epoch → median interval stays 0. */
    s          = state_new();
    char prc[] = "PRC h 500 d t 600 50 (a) S 1 1\n";
    process_line(prc, s);
    buf = NULL;
    sz  = 0;
    out = open_memstream(&buf, &sz);
    emit_results(s, out);
    fclose(out);
    CHECK(strstr(buf, "W\t500\t500\t1\t0\n") != NULL);
    free(buf);
    state_free(s);
}

static void test_delta_clamped_to_zero(void)
{
    /* Counter reset: last < first → delta must clamp to 0. */
    State *s   = state_new();
    char   a[] = "PRC h 100 d t 600 77 (x) S 50 50\n";
    char   b[] = "PRC h 700 d t 600 77 (x) S 10 10\n";
    process_line(a, s);
    process_line(b, s);
    char  *buf = NULL;
    size_t sz  = 0;
    FILE  *out = open_memstream(&buf, &sz);
    emit_results(s, out);
    fclose(out);
    CHECK(strstr(buf, "N\tx\t0\t") != NULL);
    free(buf);
    state_free(s);
}

static void test_hash_collision(void)
{
    /* Force two PIDs into adjacent slots (Knuth hash rarely collides on
       small integers, but we sweep a range to exercise the linear-probe
       branch). */
    State *s = state_new();
    for (int pid = 1; pid <= 2000; pid++)
    {
        char line[128];
        snprintf(line, sizeof(line), "PRC h 1000 d t 600 %d (p) S 1 1\n", pid);
        process_line(line, s);
        snprintf(line, sizeof(line), "PRM h 1000 d t 600 %d (p) S 4096 1 1 0 0\n", pid);
        process_line(line, s);
    }
    state_free(s);
}

static void test_state_free_null(void)
{
    /* Freeing NULL must be safe. */
    state_free(NULL);
}

int main(void)
{
    test_copy_name();
    test_tokenize();
    test_process_and_emit();
    test_empty_and_single_epoch();
    test_delta_clamped_to_zero();
    test_hash_collision();
    test_state_free_null();
    if (failures > 0)
    {
        fprintf(stderr, "%d test failures\n", failures);
        return 1;
    }
    printf("atop_agg tests: OK\n");
    return 0;
}
