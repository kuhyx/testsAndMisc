/*
 * Private constants shared between atop_agg.c (ingest) and atop_agg_emit.c
 * (reporting). Not part of the public interface in atop_agg.h: callers of the
 * library never need the table geometry, but both translation units size their
 * loops and stack buffers from it, so it cannot live in either .c file alone.
 */
#ifndef ATOP_AGG_INTERNAL_H
#define ATOP_AGG_INTERNAL_H

#include "atop_agg.h"

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


/*
 * Table internals, shared because ingest (atop_agg.c) looks slots up while
 * allocation and epoch recording live in atop_agg_state.c. Not `static` any
 * more precisely because they now cross a translation-unit boundary.
 */
unsigned int hash_pid(int pid);
PidCpu *cpu_slot(State *s, int pid);
PidRam *ram_slot(State *s, int pid);
void add_epoch(State *s, long epoch);

#endif /* ATOP_AGG_INTERNAL_H */
