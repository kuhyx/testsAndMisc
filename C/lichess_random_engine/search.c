#include "search.h"
#include <limits.h>
#include <stddef.h>

static int piece_value(Piece p){
    switch(p){
        case WP: case BP: return 100;
        case WN: case BN: return 320;
        case WB: case BB: return 330;
        case WR: case BR: return 500;
        case WQ: case BQ: return 900;
        case WK: case BK: return 0; // king is invaluable; PST handled later if needed
        default: return 0;
    }
}

int evaluate(const Position *pos){
    int score = 0;
    for (int sq=0; sq<BOARD_SIZE; ++sq){
        if ((sq & 0x88)) { sq = (sq|7); continue; }
        Piece p = pos->board[sq];
        if (p==EMPTY) continue;
        int v = piece_value(p);
        if (p>=WP && p<=WK) score += v; else if (p>=BP && p<=BK) score -= v;
    }
    // Score from side-to-move perspective
    return (pos->side==WHITE)? score : -score;
}

int alphabeta(Position pos, int depth, int alpha, int beta, int *pv_from, int *pv_to){
    if (depth<=0){
        return evaluate(&pos);
    }
    Move moves[256];
    int n = gen_moves(&pos, moves, 256, 0);
    if (n==0){
        // Checkmate or stalemate
        if (in_check(&pos, pos.side)) return -30000 + (10 - depth); // checkmated
        return 0; // stalemate
    }

    int best_score = INT_MIN/2;
    int best_from = -1, best_to = -1;
    for (int i=0;i<n;i++){
        Position child = pos;
        Piece cap=EMPTY;
        make_move(&child, &moves[i], &cap);
        int score = -alphabeta(child, depth-1, -beta, -alpha, NULL, NULL);
        if (score > best_score){
            best_score = score;
            best_from = moves[i].from;
            best_to = moves[i].to;
        }
        if (best_score > alpha) alpha = best_score;
        if (alpha >= beta) break; // beta cutoff
    }
    if (pv_from) *pv_from = best_from;
    if (pv_to) *pv_to = best_to;
    return best_score;
}
