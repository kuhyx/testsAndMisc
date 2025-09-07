#ifndef SEARCH_H
#define SEARCH_H

#include "movegen.h"

typedef struct {
    int depth;
    int nodes;
} SearchLimits;

// Evaluate position in centipawns from the side-to-move perspective.
int evaluate(const Position *pos);

// Negamax alpha-beta returning score in centipawns from side-to-move perspective.
int alphabeta(Position pos, int depth, int alpha, int beta, int *pv_from, int *pv_to);

#endif // SEARCH_H