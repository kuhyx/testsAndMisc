#ifndef SEARCH_H
#define SEARCH_H

#include "movegen.h"

typedef struct
{
    int depth;
    int nodes;
} SearchLimits;

typedef struct
{
    int from;
    int to;
} PrincipalVariation;

// Evaluate position in centipawns from the side-to-move perspective.
int evaluate(const Position *pos);

// Negamax alpha-beta returning score in centipawns from side-to-move perspective.
int alphabeta(Position pos, int depth, int alpha, int beta, PrincipalVariation *pv);

#endif // SEARCH_H
