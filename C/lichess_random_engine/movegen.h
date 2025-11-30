#ifndef MOVEGEN_H
#define MOVEGEN_H

#include <stdint.h>

// 0x88 board representation
enum
{
    BOARD_SIZE = 128
};

typedef enum
{
    WHITE = 0,
    BLACK = 1
} Color;

typedef enum
{
    EMPTY = 0,
    WP    = 1,
    WN    = 2,
    WB    = 3,
    WR    = 4,
    WQ    = 5,
    WK    = 6,
    BP    = 7,
    BN    = 8,
    BB    = 9,
    BR    = 10,
    BQ    = 11,
    BK    = 12
} Piece;

typedef struct
{
    // from and to squares in 0x88 (0..127), promotion piece in Piece enum or 0
    uint8_t from, to;
    uint8_t promo;        // 0 if none
    uint8_t is_capture;   // 1 if capture
    uint8_t is_enpassant; // 1 if en-passant capture
    uint8_t is_castle;    // 1 if castle
} Move;

typedef struct
{
    Piece board[BOARD_SIZE];
    Color side;
    // Castling rights: bit 0 white king-side, 1 white queen-side, 2 black king-side, 3 black
    // queen-side
    uint8_t castle;
    int8_t  ep_square; // -1 if none, else 0x88 square index
    int     halfmove_clock;
    int     fullmove_number;
} Position;

// Parsing and utilities
int  parse_fen(Position *pos, const char *fen);
void set_startpos(Position *pos);
int  square_from_algebraic(const char *uci4, int is_from);
int  move_from_uci(const Position *pos, const char *uci, Move *out);
void make_move(Position *pos, const Move *m, Piece *captured_out);
void unmake_move(Position *pos, const Move *m, Piece captured);
int  in_check(const Position *pos, Color side);

// Move generation
// Generates all pseudo-legal moves into moves[], returns count. If captures_only!=0, only captures
// (incl. ep) are generated
int gen_moves(const Position *pos, Move *moves, int max_moves, int captures_only);
int gen_moves_pseudo(const Position *pos, Move *moves, int max_moves, int captures_only);

#endif // MOVEGEN_H
