#ifndef CHESS_H
#define CHESS_H

#include <stdbool.h>
#include <stddef.h>

// Board is 64 chars, a1=0, b1=1, ..., h8=63
// Pieces: 'P','N','B','R','Q','K' for white, lowercase for black, '.' empty

typedef struct
{
    char board[64];
    bool white_to_move;
    bool castle_wk, castle_wq, castle_bk, castle_bq;
    int  ep_square; // -1 if none
    int  halfmove_clock;
    int  fullmove_number;
} Position;

typedef struct
{
    int  from, to;
    char promo;    // 0 or 'q','r','b','n' (lowercase for black)
    char captured; // piece captured or 0
    char moved;    // piece moved
    bool is_castle;
    bool is_enpassant;
    int  prev_ep;
    bool prev_wk, prev_wq, prev_bk, prev_bq;
    int  prev_halfmove;
} Move;

void chess_init_start(Position *pos);
void chess_copy(Position *dst, const Position *src);

// Move gen and make/unmake
size_t chess_generate_legal_moves(const Position *pos, Move *out, size_t max);
bool   chess_make_move(Position *pos, Move *m);
void   chess_unmake_move(Position *pos, const Move *m);

// Utility
bool chess_is_in_check(const Position *pos, bool white);
bool chess_square_attacked(const Position *pos, int sq, bool by_white);

// Conversions
void sq_to_coord(int sq, int *file, int *rank);
int  coord_to_sq(int file, int rank);

// UCI strings like e2e4, with optional promotion char
void move_to_uci(const Move *m, char buf[8]);
bool parse_uci_move(const char *s, const Position *pos, Move *out);

// FEN
bool chess_to_fen(const Position *pos, char *out, size_t outsz);

#define MAX_MOVES 256

#endif
