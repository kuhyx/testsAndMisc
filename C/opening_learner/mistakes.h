#ifndef MISTAKES_H
#define MISTAKES_H

#include <stdbool.h>
#include <stddef.h>

// A lightweight mistake store in memory + file persistence.

typedef struct
{
    char fen[128];
    char best_move[8];
    // PGN-like ply list in UCI for context
    char line[512];
} Mistake;

typedef struct
{
    Mistake *items;
    size_t   count;
    size_t   cap;
} MistakeList;

typedef struct
{
    const char *fen;
    const char *best_move;
    const char *line;
} MistakeEntry;

void mistakes_init(MistakeList *ml);
void mistakes_free(MistakeList *ml);
void mistakes_add(MistakeList *ml, const MistakeEntry *entry);
bool mistakes_save(const MistakeList *ml, const char *path);
bool mistakes_load(MistakeList *ml, const char *path);

#endif
