#include "mistakes.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

void mistakes_init(MistakeList *ml) {
    ml->items = NULL; ml->count = 0; ml->cap = 0;
}

void mistakes_free(MistakeList *ml) {
    free(ml->items); ml->items = NULL; ml->count = ml->cap = 0;
}

static void ensure_cap(MistakeList *ml, size_t need) {
    if (need <= ml->cap) return;
    size_t ncap = ml->cap ? ml->cap*2 : 16;
    while (ncap < need) ncap *= 2;
    Mistake *ni = realloc(ml->items, ncap * sizeof(Mistake));
    if (!ni) return; // OOM silently ignored
    ml->items = ni; ml->cap = ncap;
}

void mistakes_add(MistakeList *ml, const char *fen, const char *best_move, const char *line) {
    ensure_cap(ml, ml->count+1);
    Mistake *m = &ml->items[ml->count++];
    snprintf(m->fen, sizeof(m->fen), "%s", fen);
    snprintf(m->best_move, sizeof(m->best_move), "%s", best_move);
    snprintf(m->line, sizeof(m->line), "%s", line);
}

bool mistakes_save(const MistakeList *ml, const char *path) {
    FILE *f = fopen(path, "w");
    if (!f) return false;
    for (size_t i=0;i<ml->count;i++) {
        const Mistake *m = &ml->items[i];
        fprintf(f, "FEN:%s\nBEST:%s\nLINE:%s\n.\n", m->fen, m->best_move, m->line);
    }
    fclose(f); return true;
}

bool mistakes_load(MistakeList *ml, const char *path) {
    FILE *f = fopen(path, "r");
    if (!f) return false;
    char buf[1024]; char fen[128] = ""; char best[16] = ""; char line[512] = "";
    while (fgets(buf, sizeof(buf), f)) {
        if (strncmp(buf, "FEN:", 4) == 0) {
            // copy up to 127 chars, strip newline
            size_t l = strnlen(buf+4, sizeof(fen)-1);
            memcpy(fen, buf+4, l); fen[l]='\0';
            if (l && fen[l-1]=='\n') fen[l-1]='\0';
        } else if (strncmp(buf, "BEST:", 5) == 0) {
            size_t l = strnlen(buf+5, sizeof(best)-1);
            memcpy(best, buf+5, l); best[l]='\0';
            if (l && best[l-1]=='\n') best[l-1]='\0';
        } else if (strncmp(buf, "LINE:", 5) == 0) {
            size_t l = strnlen(buf+5, sizeof(line)-1);
            memcpy(line, buf+5, l); line[l]='\0';
            if (l && line[l-1]=='\n') line[l-1]='\0';
        } else if (buf[0]=='.') {
            mistakes_add(ml, fen, best, line);
            fen[0]=best[0]=line[0]='\0';
        }
    }
    fclose(f); return true;
}
