#ifndef ENGINE_H
#define ENGINE_H

#include <stdbool.h>
#include <stddef.h>

#include "chess.h"

typedef struct
{
    int  score_cp; // centipawns relative to side to move
    char uci[8];
} EngineMove;

typedef struct
{
    int  pid;
    int  in_fd;  // write to engine stdin
    int  out_fd; // read from engine stdout
    bool ready;
} Engine;

// Start engine: tries stockfish, then asmfish. Returns false if none.
bool engine_start(Engine *e);
void engine_stop(Engine *e);

// Synchronous send command
bool engine_cmd(Engine *e, const char *cmd);

// Ask for top N moves from a position (short fixed time). Returns count.
size_t engine_get_top_moves(Engine *e, const Position *pos, EngineMove *out, size_t max);

// Ask for best move only.
bool engine_get_best_move(Engine *e, const Position *pos, char out_uci[8]);

#endif
