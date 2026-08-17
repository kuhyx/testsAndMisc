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
#include "atop_agg_internal.h"

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>

/* Knuth multiplicative hash → index in an open-addressed table. */

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
    /* Both PRC and PRM need >= 12 fields: the 6-field generic prefix, pid,
       (name), state, atop's per-label extra field (HZ for PRC / pagesize for
       PRM), then the first data column we read at index 10/11. */
    if (n < 12)
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
        /* atop inserts its clock-tick rate (HZ) at tokens[9], between the
           state field and utime/stime, so the CPU columns live at [10]/[11].
           Reading [9] charged a constant HZ (100) as CPU to every record —
           the bug this fixes. */
        long utime = strtol(tokens[10], NULL, 10);
        long stime = strtol(tokens[11], NULL, 10);
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
    /* PRM: rsize_kb sits at tokens[11] (after state, pagesize, vsize); the
       n < 12 length guard at the top already guarantees it is present. */
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
