#ifndef ATOP_AGG_H
#define ATOP_AGG_H

#include <stdio.h>

/* NAME_MAX capped to keep slot size compact; typical atop comm is 15 chars. */
#define ATOP_AGG_NAME_MAX 40

typedef struct
{
    int  pid;
    char name[ATOP_AGG_NAME_MAX];
    long first_ticks;
    long last_ticks;
    int  samples;
} PidCpu;

typedef struct
{
    int  pid;
    char name[ATOP_AGG_NAME_MAX];
    long peak_kb;
    long sum_kb;
    int  samples;
} PidRam;

typedef struct
{
    PidCpu *cpu;
    PidRam *ram;
    long   *epochs;
    int     n_epochs;
} State;

State *state_new(void);
void   state_free(State *s);
int    tokenize_line(char *line, char **tokens, int max_tokens);
void   copy_name(char *dst, size_t cap, const char *src);
void   process_line(char *line, State *s);
void   emit_results(State *s, FILE *out);

#endif
