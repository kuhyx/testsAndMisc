/*
 * Reporting half of atop_agg: turning the accumulated per-PID tables into the
 * ranked, name-aggregated summary the report consumes.
 *
 * Split from atop_agg.c, which owns ingest (tokenising atop output and folding
 * each line into the tables). The two share only the table geometry in
 * atop_agg_internal.h and the State type in atop_agg.h.
 */
#include "atop_agg.h"
#include "atop_agg_internal.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

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
