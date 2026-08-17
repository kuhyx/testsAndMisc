/*
 * The per-PID hash tables and the State they live in: slot lookup by PID,
 * epoch recording, and allocation/teardown.
 *
 * Split from atop_agg.c so the ingest half is just parsing. Open-addressed
 * with linear probing; the geometry is in atop_agg_internal.h because the
 * reporting half walks the same tables.
 */
#include "atop_agg.h"
#include "atop_agg_internal.h"

#include <stdlib.h>
#include <string.h>

unsigned int hash_pid(int pid)
{
    unsigned int k = (unsigned int)pid;
    return (k * 2654435761u) >> (32 - HASH_CAP_BITS);
}

PidCpu *cpu_slot(State *s, int pid)
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

PidRam *ram_slot(State *s, int pid)
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

void add_epoch(State *s, long epoch)
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
