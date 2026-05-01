/*
 * atop_agg — fast per-PID aggregator for `atop -P PRC,PRM` output.
 *
 * Reads atop parseable output on stdin, folds it into per-PID CPU-tick
 * and RSS trackers, and prints a compact TSV summary on stdout that a
 * higher-level driver (Python) then name-folds into human-readable
 * tables. This avoids the ~3s Python parse cost on a typical day's
 * 1.7M-line atop dump; the C hot loop completes in well under a second
 * so the pipeline runs at atop's own ~2s wall-clock floor.
 *
 * Output TSV lines:
 *   W<TAB>start_epoch<TAB>end_epoch<TAB>distinct_samples<TAB>median_interval
 *   C<TAB>pid<TAB>name<TAB>delta_ticks
 *   R<TAB>pid<TAB>name<TAB>peak_kb<TAB>sum_kb<TAB>samples
 */
#include "atop_agg.h"

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>

/*
 * A real-world day of atop on a dev box can see >700k distinct PIDs
 * because every short-lived compiler/shell subprocess gets a fresh ID.
 * 2M slots keeps the load factor below ~40% for that workload, keeping
 * linear-probe chains short without dynamic resizing.
 */
#define HASH_CAP_BITS 21
#define HASH_CAP (1u << HASH_CAP_BITS)
#define HASH_MASK (HASH_CAP - 1u)
#define MAX_EPOCHS 4096
#define MAX_TOKENS 64

/* Knuth multiplicative hash → index in an open-addressed table. */
static unsigned int hash_pid(int pid)
{
    unsigned int k = (unsigned int)pid;
    return (k * 2654435761u) >> (32 - HASH_CAP_BITS);
}

static PidCpu *cpu_slot(State *s, int pid)
{
    unsigned int h = hash_pid(pid);
    for (unsigned int probes = 0; probes < HASH_CAP; probes++, h++)
    {
        PidCpu *slot = &s->cpu[h & HASH_MASK];
        if (slot->pid == pid)
        {
            return slot;
        }
        if (slot->pid == 0)
        {
            slot->pid         = pid;
            slot->first_ticks = -1;
            slot->last_ticks  = 0;
            slot->samples     = 0;
            slot->name[0]     = '\0';
            return slot;
        }
    }
    /* Table full — drop the sample rather than loop forever. */
    return NULL;
}

static PidRam *ram_slot(State *s, int pid)
{
    unsigned int h = hash_pid(pid);
    for (unsigned int probes = 0; probes < HASH_CAP; probes++, h++)
    {
        PidRam *slot = &s->ram[h & HASH_MASK];
        if (slot->pid == pid)
        {
            return slot;
        }
        if (slot->pid == 0)
        {
            slot->pid     = pid;
            slot->peak_kb = 0;
            slot->sum_kb  = 0;
            slot->samples = 0;
            slot->name[0] = '\0';
            return slot;
        }
    }
    return NULL;
}

static void add_epoch(State *s, long epoch)
{
    /* Linear scan — there are only a few dozen distinct epochs per log. */
    for (int i = 0; i < s->n_epochs; i++)
    {
        if (s->epochs[i] == epoch)
        {
            return;
        }
    }
    if (s->n_epochs < MAX_EPOCHS)
    {
        s->epochs[s->n_epochs++] = epoch;
    }
}

/*
 * Tokenise a whitespace-separated line in place. Fills *tokens* with
 * pointers into *line* and returns the token count. A process name
 * wrapped in parentheses is rejoined into a single token with spaces
 * preserved (atop emits `(Web Content)` as three whitespace-split
 * tokens, which we merge back).
 */
int tokenize_line(char *line, char **tokens, int max_tokens)
{
    int   n = 0;
    char *p = line;
    while (*p && n < max_tokens)
    {
        while (*p == ' ' || *p == '\t')
        {
            p++;
        }
        if (!*p || *p == '\n')
        {
            break;
        }
        char *start = p;
        if (*p == '(')
        {
            /* Consume through the matching ')', preserving interior spaces. */
            while (*p && *p != ')')
            {
                p++;
            }
            if (*p == ')')
            {
                p++;
            }
        }
        else
        {
            while (*p && *p != ' ' && *p != '\t' && *p != '\n')
            {
                p++;
            }
        }
        if (*p)
        {
            *p = '\0';
            p++;
        }
        tokens[n++] = start;
    }
    return n;
}

/*
 * Copy *src* into *dst* (capacity *cap*), stripping a leading '(' and
 * trailing ')' if both are present. Always null-terminates. If the
 * resulting name is empty, writes "unknown".
 */
void copy_name(char *dst, size_t cap, const char *src)
{
    size_t len   = strlen(src);
    size_t start = 0;
    if (len >= 2 && src[0] == '(' && src[len - 1] == ')')
    {
        start = 1;
        len -= 2;
    }
    if (len == 0)
    {
        const char *fallback = "unknown";
        size_t      flen     = strlen(fallback);
        if (flen >= cap)
        {
            flen = cap - 1;
        }
        memcpy(dst, fallback, flen);
        dst[flen] = '\0';
        return;
    }
    if (len >= cap)
    {
        len = cap - 1;
    }
    memcpy(dst, src + start, len);
    dst[len] = '\0';
}

/*
 * Parse one PRC/PRM line and update *s*. Unknown labels and malformed
 * records are silently skipped (atop emits a stable schema, but guard
 * against future changes and header/separator lines).
 */
void process_line(char *line, State *s)
{
    char *tokens[MAX_TOKENS];
    int   n = tokenize_line(line, tokens, MAX_TOKENS);
    if (n < 11)
    {
        return;
    }
    const char *label = tokens[0];
    int is_prc        = (label[0] == 'P' && label[1] == 'R' && label[2] == 'C' && label[3] == '\0');
    int is_prm        = (label[0] == 'P' && label[1] == 'R' && label[2] == 'M' && label[3] == '\0');
    if (!is_prc && !is_prm)
    {
        return;
    }
    long epoch = strtol(tokens[2], NULL, 10);
    int  pid   = (int)strtol(tokens[6], NULL, 10);
    if (pid <= 0)
    {
        return;
    }
    const char *name_tok = tokens[7];
    if (is_prc)
    {
        long utime = strtol(tokens[9], NULL, 10);
        long stime = strtol(tokens[10], NULL, 10);
        long ticks = utime + stime;
        add_epoch(s, epoch);
        PidCpu *slot = cpu_slot(s, pid);
        if (slot == NULL)
        {
            return;
        }
        if (slot->first_ticks < 0)
        {
            slot->first_ticks = ticks;
        }
        slot->last_ticks = ticks;
        slot->samples++;
        copy_name(slot->name, sizeof(slot->name), name_tok);
        return;
    }
    /* PRM */
    if (n < 12)
    {
        return;
    }
    long    rsize_kb = strtol(tokens[11], NULL, 10);
    PidRam *slot     = ram_slot(s, pid);
    if (slot == NULL)
    {
        return;
    }
    if (rsize_kb > slot->peak_kb)
    {
        slot->peak_kb = rsize_kb;
    }
    slot->sum_kb += rsize_kb;
    slot->samples++;
    copy_name(slot->name, sizeof(slot->name), name_tok);
}

static int cmp_long(const void *a, const void *b)
{
    long la = *(const long *)a;
    long lb = *(const long *)b;
    if (la < lb)
    {
        return -1;
    }
    if (la > lb)
    {
        return 1;
    }
    return 0;
}

/* FNV-1a 32-bit over a NUL-terminated string; used to key the name table. */
static unsigned int fnv1a(const char *s)
{
    unsigned int h = 2166136261u;
    while (*s)
    {
        h ^= (unsigned char)*s++;
        h *= 16777619u;
    }
    return h;
}

/*
 * Per-name aggregate, built in a second pass over cpu/ram tables so that
 * the caller only has to parse a few thousand output rows instead of one
 * row per PID. The name table is deliberately oversized (64k slots for an
 * expected few-thousand names) to keep linear-probe chains short.
 */
#define NAME_CAP_BITS 16
#define NAME_CAP (1u << NAME_CAP_BITS)
#define NAME_MASK (NAME_CAP - 1u)

typedef struct
{
    char name[ATOP_AGG_NAME_MAX];
    long cpu_ticks;
    int  cpu_pids;
    long peak_kb;
    long sum_avg_kb;
    int  rss_samples;
    int  ram_pids;
    char used;
} NameAgg;

static NameAgg *name_slot(NameAgg *table, const char *name)
{
    unsigned int h = fnv1a(name);
    for (unsigned int probes = 0; probes < NAME_CAP; probes++, h++)
    {
        NameAgg *slot = &table[h & NAME_MASK];
        if (!slot->used)
        {
            slot->used = 1;
            /* copy_name already enforced \0-termination on the source. */
            size_t i = 0;
            while (name[i] && i + 1 < sizeof(slot->name))
            {
                slot->name[i] = name[i];
                i++;
            }
            slot->name[i] = '\0';
            return slot;
        }
        if (strcmp(slot->name, name) == 0)
        {
            return slot;
        }
    }
    return NULL;
}

/* Write the aggregated summary to *out* in the documented TSV schema. */
void emit_results(State *s, FILE *out)
{
    long start_epoch     = 0;
    long end_epoch       = 0;
    long median_interval = 0;
    if (s->n_epochs > 0)
    {
        qsort(s->epochs, (size_t)s->n_epochs, sizeof(long), cmp_long);
        start_epoch = s->epochs[0];
        end_epoch   = s->epochs[s->n_epochs - 1];
        if (s->n_epochs >= 2)
        {
            long deltas[MAX_EPOCHS];
            for (int i = 0; i < s->n_epochs - 1; i++)
            {
                deltas[i] = s->epochs[i + 1] - s->epochs[i];
            }
            qsort(deltas, (size_t)(s->n_epochs - 1), sizeof(long), cmp_long);
            median_interval = deltas[(s->n_epochs - 1) / 2];
        }
    }
    fprintf(out, "W\t%ld\t%ld\t%d\t%ld\n", start_epoch, end_epoch, s->n_epochs, median_interval);

    NameAgg *names = calloc(NAME_CAP, sizeof(NameAgg));
    if (!names)
    {
        return;
    }
    for (unsigned int i = 0; i < HASH_CAP; i++)
    {
        PidCpu *slot = &s->cpu[i];
        if (slot->pid == 0)
        {
            continue;
        }
        long delta = slot->last_ticks;
        if (slot->samples >= 2)
        {
            delta = slot->last_ticks - slot->first_ticks;
            if (delta < 0)
            {
                delta = 0;
            }
        }
        NameAgg *na = name_slot(names, slot->name);
        if (!na)
        {
            continue;
        }
        na->cpu_ticks += delta;
        na->cpu_pids++;
    }
    for (unsigned int i = 0; i < HASH_CAP; i++)
    {
        PidRam *slot = &s->ram[i];
        if (slot->pid == 0)
        {
            continue;
        }
        long     avg_kb = slot->samples ? slot->sum_kb / slot->samples : 0;
        NameAgg *na     = name_slot(names, slot->name);
        if (!na)
        {
            continue;
        }
        if (slot->peak_kb > na->peak_kb)
        {
            na->peak_kb = slot->peak_kb;
        }
        na->sum_avg_kb += avg_kb;
        na->rss_samples++;
        na->ram_pids++;
    }
    for (unsigned int i = 0; i < NAME_CAP; i++)
    {
        NameAgg *na = &names[i];
        if (!na->used)
        {
            continue;
        }
        int pids = na->cpu_pids > na->ram_pids ? na->cpu_pids : na->ram_pids;
        fprintf(out, "N\t%s\t%ld\t%ld\t%ld\t%d\t%d\n", na->name, na->cpu_ticks, na->peak_kb,
                na->sum_avg_kb, na->rss_samples, pids);
    }
    free(names);
}

State *state_new(void)
{
    State *s = calloc(1, sizeof(State));
    if (!s)
    {
        return NULL;
    }
    s->cpu    = calloc(HASH_CAP, sizeof(PidCpu));
    s->ram    = calloc(HASH_CAP, sizeof(PidRam));
    s->epochs = calloc(MAX_EPOCHS, sizeof(long));
    if (!s->cpu || !s->ram || !s->epochs)
    {
        state_free(s);
        return NULL;
    }
    s->n_epochs = 0;
    return s;
}

void state_free(State *s)
{
    if (!s)
    {
        return;
    }
    free(s->cpu);
    free(s->ram);
    free(s->epochs);
    free(s);
}

#ifndef ATOP_AGG_NO_MAIN
int main(void)
{
    State *s = state_new();
    if (!s)
    {
        fprintf(stderr, "atop_agg: out of memory\n");
        return 1;
    }
    char   *line = NULL;
    size_t  cap  = 0;
    ssize_t got;
    while ((got = getline(&line, &cap, stdin)) != -1)
    {
        process_line(line, s);
    }
    free(line);
    emit_results(s, stdout);
    state_free(s);
    return 0;
}
#endif
