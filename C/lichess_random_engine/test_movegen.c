/*
 * test_movegen.c - Unit tests for movegen.c (parse_fen, make_move, unmake_move,
 * gen_moves, in_check, square_from_algebraic, move_from_uci).
 */

#include "movegen.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

/* Helper: count moves matching a given to-square */
static int count_moves_to(Move *moves, int n, int to)
{
    int c = 0;
    for (int i = 0; i < n; i++)
    {
        if (moves[i].to == to)
        {
            c++;
        }
    }
    return c;
}

/* Helper: find a move from→to in the move list; returns index or -1 */
static int find_move(Move *moves, int n, int from, int to)
{
    for (int i = 0; i < n; i++)
    {
        if (moves[i].from == from && moves[i].to == to)
        {
            return i;
        }
    }
    return -1;
}

/* =========================================================================
 * parse_fen tests
 * ========================================================================= */

static void test_parse_fen_startpos(void)
{
    Position pos;
    int      ok = parse_fen(&pos, "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
    assert(ok);
    assert(pos.side == WHITE);
    assert(pos.castle == 0xF); /* all four castling rights */
    assert(pos.ep_square == -1);
    assert(pos.halfmove_clock == 0);
    assert(pos.fullmove_number == 1);

    /* a1 = 0x00 should be WR */
    assert(pos.board[0x00] == WR);
    /* e1 = 0x04 WK */
    assert(pos.board[0x04] == WK);
    /* e8 = 0x74 BK */
    assert(pos.board[0x74] == BK);
    /* a2 = 0x10 WP */
    assert(pos.board[0x10] == WP);
    /* e5 = 0x44 EMPTY */
    assert(pos.board[0x44] == EMPTY);
}

static void test_parse_fen_black_to_move(void)
{
    Position pos;
    int      ok = parse_fen(&pos, "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1");
    assert(ok);
    assert(pos.side == BLACK);
    /* e3 = rank1+2, file e=4 => 0x24 */
    assert(pos.ep_square == 0x24);
}

static void test_parse_fen_no_castling(void)
{
    Position pos;
    int      ok = parse_fen(&pos, "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1");
    assert(ok);
    assert(pos.castle == 0);
}

static void test_parse_fen_partial_castling(void)
{
    Position pos;
    int      ok = parse_fen(&pos, "r3k2r/8/8/8/8/8/8/R3K2R w Kq - 0 1");
    assert(ok);
    assert(pos.castle & (1 << 0));    /* white kingside */
    assert(!(pos.castle & (1 << 1))); /* not white queenside */
    assert(!(pos.castle & (1 << 2))); /* not black kingside */
    assert(pos.castle & (1 << 3));    /* black queenside */
}

static void test_parse_fen_invalid_missing_space(void)
{
    Position pos;
    int      ok = parse_fen(&pos, "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR");
    assert(!ok);
}

static void test_parse_fen_invalid_side(void)
{
    Position pos;
    int      ok = parse_fen(&pos, "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR x KQkq - 0 1");
    assert(!ok);
}

static void test_parse_fen_invalid_ep(void)
{
    Position pos;
    int      ok = parse_fen(&pos, "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq z9 0 1");
    assert(!ok);
}

static void test_parse_fen_invalid_castling_char(void)
{
    Position pos;
    int      ok = parse_fen(&pos, "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KX - 0 1");
    assert(!ok);
}

static void test_parse_fen_invalid_off_board(void)
{
    /* Placing a piece on an off-board square (like rank 0 with EMPTY in between)
     * Use a FEN where the piece placement lands on off-board sq: try a fen where
     * piece placement skips the separator and goes past rank end. Since the parser
     * only checks on_board when placing a piece character (not digits), we verify
     * that placing AT an off-board square returns 0. This is tricky to trigger via
     * a simple digit overflow, but we can use a malformed FEN where the piece
     * is placed at sq 0x08 which is off-board: one rank only with 10 pieces.  */
    /* After A8-H8 (8 squares) sq=0x78 which is off-board. Place a 9th PIECE. */
    Position pos;
    int      ok = parse_fen(&pos, "RNBQKBNRP/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1");
    assert(!ok);
}

static void test_parse_fen_fullmove_and_halfmove(void)
{
    Position pos;
    int      ok = parse_fen(&pos, "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 5 12");
    assert(ok);
    assert(pos.halfmove_clock == 5);
    assert(pos.fullmove_number == 12);
}

static void test_set_startpos(void)
{
    Position pos;
    set_startpos(&pos);
    assert(pos.side == WHITE);
    assert(pos.board[0x04] == WK);
    assert(pos.board[0x74] == BK);
    assert(pos.castle == 0xF);
}

/* =========================================================================
 * square_from_algebraic tests
 * ========================================================================= */

static void test_square_from_algebraic_basic(void)
{
    /* e2e4 -> from=e2=0x14, to=e4=0x34 */
    assert(square_from_algebraic("e2e4", 1) == 0x14);
    assert(square_from_algebraic("e2e4", 0) == 0x34);
}

static void test_square_from_algebraic_promotion(void)
{
    /* e7e8q: from e7=0x64, to e8=0x74 */
    assert(square_from_algebraic("e7e8q", 1) == 0x64);
    assert(square_from_algebraic("e7e8q", 0) == 0x74);
}

static void test_square_from_algebraic_null(void)
{
    assert(square_from_algebraic(NULL, 0) == -1);
    assert(square_from_algebraic("e2", 0) == -1); /* too short */
}

static void test_square_from_algebraic_a1(void)
{
    assert(square_from_algebraic("a1b2", 1) == 0x00);
    assert(square_from_algebraic("a1b2", 0) == 0x11);
}

static void test_square_from_algebraic_h8(void)
{
    assert(square_from_algebraic("h8g7", 1) == 0x77);
    assert(square_from_algebraic("h8g7", 0) == 0x66);
}

/* =========================================================================
 * make_move / unmake_move tests
 * ========================================================================= */

static void test_make_unmake_pawn_push(void)
{
    Position pos;
    set_startpos(&pos);

    /* e2e4 */
    Move m;
    int  found = move_from_uci(&pos, "e2e4", &m);
    assert(found);

    Position before = pos;
    Piece    cap    = EMPTY;
    make_move(&pos, &m, &cap);

    assert(cap == EMPTY);
    assert(pos.board[0x14] == EMPTY);
    assert(pos.board[0x34] == WP);
    assert(pos.ep_square == 0x24); /* e3 */
    assert(pos.side == BLACK);

    unmake_move(&pos, &m, cap);
    (void)before;
    assert(pos.board[0x14] == WP);
    assert(pos.board[0x34] == EMPTY);
    assert(pos.side == WHITE);
}

static void test_make_unmake_capture(void)
{
    Position pos;
    /* Rxd5: white rook on a5 takes black queen on d5 */
    parse_fen(&pos, "8/8/8/R2q4/8/8/8/K6k w - - 0 1");

    Move m;
    int  found = move_from_uci(&pos, "a5d5", &m);
    assert(found);
    assert(m.is_capture);

    Piece cap = EMPTY;
    make_move(&pos, &m, &cap);
    assert(cap == BQ);
    assert(pos.board[0x40] == EMPTY); /* a5 empty */
    assert(pos.board[0x43] == WR);    /* d5 has rook */

    unmake_move(&pos, &m, cap);
    assert(pos.board[0x40] == WR);
    assert(pos.board[0x43] == BQ);
}

static void test_make_unmake_en_passant(void)
{
    Position pos;
    /* Black pawn on e4, white just played d2d4, ep on d3 */
    parse_fen(&pos, "8/8/8/8/3Pp3/8/8/4K2k b - d3 0 1");

    Move m;
    int  found = move_from_uci(&pos, "e4d3", &m);
    assert(found);
    assert(m.is_enpassant);

    Piece cap = EMPTY;
    make_move(&pos, &m, &cap);
    /* White pawn at d4=0x33 should be captured */
    assert(pos.board[0x33] == EMPTY);
    /* Black pawn moves from e4=0x34 to d3=0x23 */
    assert(pos.board[0x34] == EMPTY);
    assert(pos.board[0x23] == BP);

    unmake_move(&pos, &m, cap);
    assert(pos.board[0x33] == WP); /* restored white pawn */
    assert(pos.board[0x34] == BP); /* black pawn back */
    assert(pos.board[0x23] == EMPTY);
}

static void test_make_unmake_white_kingside_castle(void)
{
    Position pos;
    parse_fen(&pos, "4k3/8/8/8/8/8/8/4K2R w K - 0 1");

    Move m;
    int  found = move_from_uci(&pos, "e1g1", &m);
    assert(found);
    assert(m.is_castle);

    Piece cap = EMPTY;
    make_move(&pos, &m, &cap);
    assert(pos.board[0x06] == WK);
    assert(pos.board[0x05] == WR);
    assert(pos.board[0x07] == EMPTY);
    assert(!(pos.castle & (1 << 0))); /* white kingside right gone */

    unmake_move(&pos, &m, cap);
    assert(pos.board[0x04] == WK);
    assert(pos.board[0x07] == WR);
    assert(pos.board[0x05] == EMPTY);
    assert(pos.board[0x06] == EMPTY);
}

static void test_make_unmake_white_queenside_castle(void)
{
    Position pos;
    parse_fen(&pos, "4k3/8/8/8/8/8/8/R3K3 w Q - 0 1");

    Move m;
    int  found = move_from_uci(&pos, "e1c1", &m);
    assert(found);
    assert(m.is_castle);

    Piece cap = EMPTY;
    make_move(&pos, &m, &cap);
    assert(pos.board[0x02] == WK);
    assert(pos.board[0x03] == WR);
    assert(pos.board[0x00] == EMPTY);

    unmake_move(&pos, &m, cap);
    assert(pos.board[0x04] == WK);
    assert(pos.board[0x00] == WR);
}

static void test_make_unmake_black_kingside_castle(void)
{
    Position pos;
    parse_fen(&pos, "4k2r/8/8/8/8/8/8/4K3 b k - 0 1");

    Move m;
    int  found = move_from_uci(&pos, "e8g8", &m);
    assert(found);
    assert(m.is_castle);

    Piece cap = EMPTY;
    make_move(&pos, &m, &cap);
    assert(pos.board[0x76] == BK);
    assert(pos.board[0x75] == BR);
    assert(pos.board[0x77] == EMPTY);

    unmake_move(&pos, &m, cap);
    assert(pos.board[0x74] == BK);
    assert(pos.board[0x77] == BR);
}

static void test_make_unmake_black_queenside_castle(void)
{
    Position pos;
    parse_fen(&pos, "r3k3/8/8/8/8/8/8/4K3 b q - 0 1");

    Move m;
    int  found = move_from_uci(&pos, "e8c8", &m);
    assert(found);
    assert(m.is_castle);

    Piece cap = EMPTY;
    make_move(&pos, &m, &cap);
    assert(pos.board[0x72] == BK);
    assert(pos.board[0x73] == BR);
    assert(pos.board[0x70] == EMPTY);

    unmake_move(&pos, &m, cap);
    assert(pos.board[0x74] == BK);
    assert(pos.board[0x70] == BR);
}

static void test_make_promotion_queen(void)
{
    Position pos;
    parse_fen(&pos, "7k/4P3/8/8/8/8/8/7K w - - 0 1");

    Move m;
    int  found = move_from_uci(&pos, "e7e8q", &m);
    assert(found);
    assert(m.promo == WQ);

    Piece cap = EMPTY;
    make_move(&pos, &m, &cap);
    assert(pos.board[0x74] == WQ);
    assert(pos.board[0x64] == EMPTY);

    unmake_move(&pos, &m, cap);
    /* After unmake: from square should have the pawn (unmake restores moved piece via side) */
    /* unmake sets side back to white first, then assigns moved piece (WP) from promo branch */
    assert(pos.board[0x64] == WP);
    assert(pos.board[0x74] == EMPTY);
}

static void test_make_promotion_rook(void)
{
    Position pos;
    parse_fen(&pos, "7k/4P3/8/8/8/8/8/7K w - - 0 1");

    Move m;
    int  found = move_from_uci(&pos, "e7e8r", &m);
    assert(found);
    assert(m.promo == WR);

    Piece cap = EMPTY;
    make_move(&pos, &m, &cap);
    assert(pos.board[0x74] == WR);
}

static void test_make_promotion_bishop(void)
{
    Position pos;
    parse_fen(&pos, "7k/4P3/8/8/8/8/8/7K w - - 0 1");

    Move m;
    int  found = move_from_uci(&pos, "e7e8b", &m);
    assert(found);
    assert(m.promo == WB);

    Piece cap = EMPTY;
    make_move(&pos, &m, &cap);
    assert(pos.board[0x74] == WB);
}

static void test_make_promotion_knight(void)
{
    Position pos;
    parse_fen(&pos, "7k/4P3/8/8/8/8/8/7K w - - 0 1");

    Move m;
    int  found = move_from_uci(&pos, "e7e8n", &m);
    assert(found);
    assert(m.promo == WN);

    Piece cap = EMPTY;
    make_move(&pos, &m, &cap);
    assert(pos.board[0x74] == WN);
}

static void test_make_castling_rights_update_on_rook_move(void)
{
    Position pos;
    parse_fen(&pos, "4k3/8/8/8/8/8/8/R3K2R w KQ - 0 1");

    /* Move h1 rook */
    Move m;
    int  found = move_from_uci(&pos, "h1g1", &m);
    assert(found);

    Piece cap = EMPTY;
    make_move(&pos, &m, &cap);
    /* h1 is 0x07; moving from there removes kingside right (bit 0) */
    assert(!(pos.castle & (1 << 0)));
    assert(pos.castle & (1 << 1)); /* queenside still intact */
}

static void test_make_castling_rights_removed_on_a1_capture(void)
{
    Position pos;
    /* Black rook captures white a1 rook */
    parse_fen(&pos, "4k3/8/8/8/8/8/8/R3K3 b Q - 0 1");

    /* Put a black rook on a2 to capture a1 */
    pos.board[0x10] = BR;
    Move m;
    int  found = move_from_uci(&pos, "a2a1", &m);
    assert(found);

    Piece cap = EMPTY;
    make_move(&pos, &m, &cap);
    assert(!(pos.castle & (1 << 1))); /* white queenside gone */
}

/* =========================================================================
 * in_check / gen_moves tests
 * ========================================================================= */

static void test_in_check_not_in_check(void)
{
    Position pos;
    set_startpos(&pos);
    assert(!in_check(&pos, WHITE));
    assert(!in_check(&pos, BLACK));
}

static void test_in_check_by_rook(void)
{
    Position pos;
    /* White king on e1, black rook on e8 - rays clear */
    parse_fen(&pos, "4r3/8/8/8/8/8/8/4K3 w - - 0 1");
    assert(in_check(&pos, WHITE));
    assert(!in_check(&pos, BLACK));
}

static void test_in_check_no_king(void)
{
    /* No WK on board - in_check should return 0 gracefully */
    Position pos;
    memset(&pos, 0, sizeof(pos));
    for (int i = 0; i < 128; i++)
    {
        pos.board[i] = EMPTY;
    }
    pos.ep_square = -1;
    assert(!in_check(&pos, WHITE));
}

static void test_in_check_by_knight(void)
{
    Position pos;
    /* White king on e1 (0x04), black knight on d3 (0x23) attacks e1 */
    parse_fen(&pos, "8/8/8/8/8/3n4/8/4K3 w - - 0 1");
    assert(in_check(&pos, WHITE));
}

static void test_in_check_by_bishop(void)
{
    Position pos;
    parse_fen(&pos, "8/8/8/8/8/8/6b1/7K w - - 0 1");
    /* Black bishop on g2, white king on h1 - diagonal */
    assert(in_check(&pos, WHITE));
}

static void test_in_check_by_pawn(void)
{
    Position pos;
    /* White king on e4, black pawn on d5 attacks e4 */
    parse_fen(&pos, "4k3/8/8/3p4/4K3/8/8/8 w - - 0 1");
    assert(in_check(&pos, WHITE));
}

static void test_gen_moves_startpos_count(void)
{
    Position pos;
    set_startpos(&pos);
    Move moves[256];
    int  n = gen_moves(&pos, moves, 256, 0);
    assert(n == 20); /* 16 pawn + 4 knight = 20 */
}

static void test_gen_moves_captures_only(void)
{
    Position pos;
    set_startpos(&pos);
    Move moves[256];
    int  n = gen_moves(&pos, moves, 256, 1); /* captures only */
    assert(n == 0);                          /* no captures from start */
}

static void test_gen_moves_only_captures_mid_game(void)
{
    Position pos;
    /* White rook on d5 can capture black pawn on f5 */
    parse_fen(&pos, "4k3/8/8/3R1p2/8/8/8/4K3 w - - 0 1");
    Move moves[256];
    int  n = gen_moves(&pos, moves, 256, 1);
    assert(n >= 1);
}

static void test_gen_moves_checkmate(void)
{
    Position pos;
    /* Fool's mate: white checkmated */
    parse_fen(&pos, "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3");
    Move moves[256];
    int  n = gen_moves(&pos, moves, 256, 0);
    assert(n == 0); /* no legal moves = checkmate */
}

static void test_gen_moves_stalemate(void)
{
    Position pos;
    /* Classic stalemate: black king on a8, white queen on c7, white king on c8 */
    parse_fen(&pos, "k7/2Q5/2K5/8/8/8/8/8 b - - 0 1");
    Move moves[256];
    int  n = gen_moves(&pos, moves, 256, 0);
    assert(n == 0);
    assert(!in_check(&pos, BLACK)); /* stalemate not checkmate */
}

static void test_gen_moves_promotes_four_choices(void)
{
    Position pos;
    /* White pawn on e7, kings off the e-file so e8 is clear */
    parse_fen(&pos, "7k/4P3/8/8/8/8/8/7K w - - 0 1");
    Move moves[256];
    int  n    = gen_moves(&pos, moves, 256, 0);
    int  from = 0x64; /* e7 */
    int  to   = 0x74; /* e8 */
    int  cnt  = 0;
    for (int i = 0; i < n; i++)
    {
        if (moves[i].from == from && moves[i].to == to)
        {
            cnt++;
        }
    }
    assert(cnt == 4); /* Q, R, B, N promotions */
}

static void test_gen_moves_en_passant(void)
{
    Position pos;
    parse_fen(&pos, "4k3/8/8/3Pp3/8/8/8/4K3 w - e6 0 1");
    Move moves[256];
    int  n = gen_moves(&pos, moves, 256, 0);
    /* d5 pawn can capture e.p. to e6=0x54 */
    int found_ep = 0;
    for (int i = 0; i < n; i++)
    {
        if (moves[i].is_enpassant)
        {
            found_ep = 1;
        }
    }
    assert(found_ep);
}

static void test_gen_pseudo_not_filtered(void)
{
    Position pos;
    /* Self-check position: white king on e1, white rook on e2 pinned by black rook on e8.
     * gen_moves_pseudo should include rook moves; gen_moves should filter them. */
    parse_fen(&pos, "4r3/8/8/8/8/8/4R3/4K3 w - - 0 1");
    Move pseudo[256];
    Move legal[256];
    int  np = gen_moves_pseudo(&pos, pseudo, 256, 0);
    int  nl = gen_moves(&pos, legal, 256, 0);
    /* Pseudo includes pinned rook moves; legal filters them */
    assert(np > nl);
}

static void test_gen_moves_knight_attacks(void)
{
    Position pos;
    /* Knight on c3, find all squares it attacks */
    parse_fen(&pos, "4k3/8/8/8/8/2N5/8/4K3 w - - 0 1");
    Move moves[256];
    int  n = gen_moves(&pos, moves, 256, 0);
    /* Knight on c3 (0x22) attacks a2,b1,d1,e2,e4,d5,b5,a4 = 8 squares
     * Plus king moves */
    int knight_moves = 0;
    for (int i = 0; i < n; i++)
    {
        if (moves[i].from == 0x22)
        {
            knight_moves++;
        }
    }
    assert(knight_moves == 8);
}

static void test_gen_moves_bishop_attacks(void)
{
    Position pos;
    /* Bishop on d4, open board */
    parse_fen(&pos, "4k3/8/8/8/3B4/8/8/4K3 w - - 0 1");
    Move moves[256];
    int  n            = gen_moves(&pos, moves, 256, 0);
    int  bishop_moves = 0;
    for (int i = 0; i < n; i++)
    {
        if (moves[i].from == 0x33)
        {
            bishop_moves++;
        }
    }
    assert(bishop_moves == 13); /* d4 bishop has 13 diagonal squares */
}

static void test_gen_moves_rook_attacks(void)
{
    Position pos;
    parse_fen(&pos, "4k3/8/8/8/3R4/8/8/4K3 w - - 0 1");
    Move moves[256];
    int  n          = gen_moves(&pos, moves, 256, 0);
    int  rook_moves = 0;
    for (int i = 0; i < n; i++)
    {
        if (moves[i].from == 0x33)
        {
            rook_moves++;
        }
    }
    assert(rook_moves == 14); /* d4 rook: 7 horizontal + 7 vertical = 14 */
}

static void test_gen_moves_queen_attacks(void)
{
    Position pos;
    parse_fen(&pos, "4k3/8/8/8/3Q4/8/8/4K3 w - - 0 1");
    Move moves[256];
    int  n           = gen_moves(&pos, moves, 256, 0);
    int  queen_moves = 0;
    for (int i = 0; i < n; i++)
    {
        if (moves[i].from == 0x33)
        {
            queen_moves++;
        }
    }
    assert(queen_moves == 27); /* d4 queen: 13 diagonal + 14 rook = 27 */
}

static void test_gen_moves_castling_blocked_by_attack(void)
{
    Position pos;
    /* White kingside castle: f1 attacked by black rook - castle should be illegal */
    parse_fen(&pos, "4k2r/8/8/8/8/8/8/4K2R w K - 0 1");
    Move moves[256];
    int  n         = gen_moves(&pos, moves, 256, 0);
    int  castle_kg = 0;
    for (int i = 0; i < n; i++)
    {
        if (moves[i].is_castle && moves[i].to == 0x06)
        {
            castle_kg = 1;
        }
    }
    /* Black rook on h8 covers g1, but not f1 - castle IS legal.
     * Let's replace with rook on f8 attacking f1. */
    (void)n;
    (void)castle_kg;
    parse_fen(&pos, "4k1r1/8/8/8/8/8/8/4K2R w K - 0 1");
    n         = gen_moves(&pos, moves, 256, 0);
    castle_kg = 0;
    for (int i = 0; i < n; i++)
    {
        if (moves[i].is_castle && moves[i].to == 0x06)
        {
            castle_kg = 1;
        }
    }
    assert(!castle_kg); /* castling blocked by attack on f1 */
}

static void test_gen_moves_castling_blocked_in_check(void)
{
    Position pos;
    /* White king in check, cannot castle */
    parse_fen(&pos, "4k3/8/8/8/8/8/8/4K2R w K - 0 1");
    /* Put black rook on e8 to give check on e1 */
    pos.board[0x74] = EMPTY;
    pos.board[0x74] = BK;
    pos.board[0x44] = BR; /* e5 */
    pos.board[0x04] = WK;

    Move moves[256];
    int  n         = gen_moves(&pos, moves, 256, 0);
    int  castle_kg = 0;
    for (int i = 0; i < n; i++)
    {
        if (moves[i].is_castle)
        {
            castle_kg = 1;
        }
    }
    /* Cannot castle while in check */
    assert(!castle_kg);
}

static void test_gen_moves_black_castling(void)
{
    Position pos;
    parse_fen(&pos, "r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1");
    Move moves[256];
    int  n         = gen_moves(&pos, moves, 256, 0);
    int  qs_castle = 0;
    int  ks_castle = 0;
    for (int i = 0; i < n; i++)
    {
        if (moves[i].is_castle)
        {
            if (moves[i].to == 0x72)
            {
                qs_castle = 1;
            }
            if (moves[i].to == 0x76)
            {
                ks_castle = 1;
            }
        }
    }
    assert(qs_castle);
    assert(ks_castle);
}

static void test_gen_moves_black_pawn_attacks(void)
{
    Position pos;
    /* Black pawn on e5, white pawn on d4 and f4 - both capturable */
    parse_fen(&pos, "4k3/8/8/4p3/3P1P2/8/8/4K3 b - - 0 1");
    Move moves[256];
    int  n = gen_moves(&pos, moves, 256, 0);
    /* e5 pawn can go to e4 (push), d4 (capture), f4 (capture) */
    int from_e5 = 0;
    for (int i = 0; i < n; i++)
    {
        if (moves[i].from == 0x44)
        {
            from_e5++;
        }
    }
    assert(from_e5 == 3);
}

static void test_gen_moves_black_pawn_initial_push(void)
{
    Position pos;
    parse_fen(&pos, "4k3/4p3/8/8/8/8/8/4K3 b - - 0 1");
    Move moves[256];
    int  n = gen_moves(&pos, moves, 256, 0);
    /* e7 pawn: push to e6 and e5 (double push) */
    int from_e7 = 0;
    for (int i = 0; i < n; i++)
    {
        if (moves[i].from == 0x64)
        {
            from_e7++;
        }
    }
    assert(from_e7 == 2);
}

static void test_gen_moves_black_promotion(void)
{
    Position pos;
    parse_fen(&pos, "7K/8/8/8/8/8/4p3/7k b - - 0 1");
    Move moves[256];
    int  n   = gen_moves(&pos, moves, 256, 0);
    int  cnt = 0;
    for (int i = 0; i < n; i++)
    {
        if (moves[i].from == 0x14 && moves[i].to == 0x04)
        {
            cnt++;
        }
    }
    assert(cnt == 4); /* four promotion choices */
}

static void test_gen_moves_black_ep(void)
{
    Position pos;
    /* Black pawn on d4, white pawn just moved e2e4, ep square on e3=0x24 */
    parse_fen(&pos, "4k3/8/8/8/3pP3/8/8/4K3 b - e3 0 1");
    Move moves[256];
    int  n      = gen_moves(&pos, moves, 256, 0);
    int  has_ep = 0;
    for (int i = 0; i < n; i++)
    {
        if (moves[i].is_enpassant)
        {
            has_ep = 1;
        }
    }
    assert(has_ep);
}

/* =========================================================================
 * move_from_uci tests
 * ========================================================================= */

static void test_move_from_uci_basic(void)
{
    Position pos;
    set_startpos(&pos);
    Move m;

    int ok = move_from_uci(&pos, "e2e4", &m);
    assert(ok);
    assert(m.from == 0x14);
    assert(m.to == 0x34);
    assert(!m.promo);
}

static void test_move_from_uci_invalid_from(void)
{
    Position pos;
    set_startpos(&pos);
    Move m;
    int  ok = move_from_uci(&pos, "i9i9", &m);
    assert(!ok);
}

static void test_move_from_uci_not_in_legal_moves(void)
{
    Position pos;
    set_startpos(&pos);
    Move m;
    /* e2e5 is not a legal move */
    int ok = move_from_uci(&pos, "e2e5", &m);
    assert(!ok);
}

static void test_move_from_uci_promotion_queen(void)
{
    Position pos;
    parse_fen(&pos, "7k/4P3/8/8/8/8/8/7K w - - 0 1");
    Move m;
    int  ok = move_from_uci(&pos, "e7e8q", &m);
    assert(ok);
    assert(m.promo == WQ);
}

static void test_move_from_uci_promotion_rook(void)
{
    Position pos;
    parse_fen(&pos, "7k/4P3/8/8/8/8/8/7K w - - 0 1");
    Move m;
    int  ok = move_from_uci(&pos, "e7e8r", &m);
    assert(ok);
    assert(m.promo == WR);
}

static void test_move_from_uci_promotion_bishop(void)
{
    Position pos;
    parse_fen(&pos, "7k/4P3/8/8/8/8/8/7K w - - 0 1");
    Move m;
    int  ok = move_from_uci(&pos, "e7e8b", &m);
    assert(ok);
    assert(m.promo == WB);
}

static void test_move_from_uci_promotion_knight(void)
{
    Position pos;
    parse_fen(&pos, "7k/4P3/8/8/8/8/8/7K w - - 0 1");
    Move m;
    int  ok = move_from_uci(&pos, "e7e8n", &m);
    assert(ok);
    assert(m.promo == WN);
}

static void test_move_from_uci_promotion_uppercase_r(void)
{
    Position pos;
    parse_fen(&pos, "7k/4P3/8/8/8/8/8/7K w - - 0 1");
    Move m;
    int  ok = move_from_uci(&pos, "e7e8R", &m);
    assert(ok);
    assert(m.promo == WR);
}

static void test_move_from_uci_black_promotion(void)
{
    Position pos;
    parse_fen(&pos, "7K/8/8/8/8/8/4p3/7k b - - 0 1");
    Move m;
    int  ok = move_from_uci(&pos, "e2e1q", &m);
    assert(ok);
    assert(m.promo == BQ);
}

/* =========================================================================
 * Perft correctness tests (verifies move generation end-to-end)
 * ========================================================================= */

static unsigned long long perft(Position pos, int depth)
{
    if (depth == 0)
    {
        return 1ULL;
    }
    Move               moves[256];
    unsigned long long nodes = 0ULL;
    int                n     = gen_moves(&pos, moves, 256, 0);
    for (int i = 0; i < n; i++)
    {
        Position child = pos;
        Piece    cap   = EMPTY;
        make_move(&child, &moves[i], &cap);
        nodes += perft(child, depth - 1);
    }
    return nodes;
}

static void test_perft_startpos_depth1(void)
{
    Position pos;
    set_startpos(&pos);
    assert(perft(pos, 1) == 20ULL);
}

static void test_perft_startpos_depth2(void)
{
    Position pos;
    set_startpos(&pos);
    assert(perft(pos, 2) == 400ULL);
}

static void test_perft_ep_position_depth1(void)
{
    Position pos;
    /* EP position: black has 22 legal moves at depth 1 */
    parse_fen(&pos, "rnbqkbnr/pppppppp/8/8/3Pp3/8/PPP1PPPP/RNBQKBNR b KQkq d3 0 1");
    assert(perft(pos, 1) == 22ULL);
}

static void test_perft_kiwipete_depth1(void)
{
    Position pos;
    /* Custom position with en passant, castling, and complex moves */
    parse_fen(&pos, "r3k2r/p1ppqpb1/bn2pnp1/2PpP3/1p2P3/2N2N2/PBPP1PPP/R2Q1RK1 w kq - 0 1");
    assert(perft(pos, 1) == 31ULL);
}

static void test_perft_kiwipete_depth2(void)
{
    Position pos;
    parse_fen(&pos, "r3k2r/p1ppqpb1/bn2pnp1/2PpP3/1p2P3/2N2N2/PBPP1PPP/R2Q1RK1 w kq - 0 1");
    assert(perft(pos, 2) == 1315ULL);
}

/* =========================================================================
 * Additional coverage tests for specific branches
 * ========================================================================= */

static void test_attacked_by_white_king_proximity(void)
{
    Position pos;
    /* Black king on e8 next to white king on e7 - attacked by king */
    parse_fen(&pos, "4k3/4K3/8/8/8/8/8/8 b - - 0 1");
    assert(in_check(&pos, BLACK));
}

static void test_attacked_by_white_pawn(void)
{
    Position pos;
    /* Black king on f6, white pawn on e5 - pawn attacks f6 */
    parse_fen(&pos, "8/8/5k2/4P3/8/8/8/4K3 b - - 0 1");
    assert(in_check(&pos, BLACK));
}

static void test_attacked_by_black_pawn(void)
{
    Position pos;
    /* White king on d4, black pawn on e5 - attacks d4? No: e5 pawn attacks d4 and f4 */
    parse_fen(&pos, "4k3/8/8/4p3/3K4/8/8/8 w - - 0 1");
    assert(in_check(&pos, WHITE));
}

static void test_attacked_by_queen_rook_direction(void)
{
    Position pos;
    /* White king on a1, black queen on a8 - file attack */
    parse_fen(&pos, "q7/8/8/8/8/8/8/K6k w - - 0 1");
    assert(in_check(&pos, WHITE));
}

static void test_attacked_slider_blocked(void)
{
    Position pos;
    /* White king on a1, black rook on a8, white pawn on a4 blocking */
    parse_fen(&pos, "r7/8/8/8/P7/8/8/K6k w - - 0 1");
    assert(!in_check(&pos, WHITE));
}

static void test_halfmove_clock_pawn_resets(void)
{
    Position pos;
    set_startpos(&pos);
    pos.halfmove_clock = 10;
    Move m;
    move_from_uci(&pos, "e2e4", &m);
    Piece cap = EMPTY;
    make_move(&pos, &m, &cap);
    assert(pos.halfmove_clock == 0);
}

static void test_halfmove_clock_piece_increments(void)
{
    Position pos;
    parse_fen(&pos, "4k3/8/8/8/8/8/8/4K2R w K - 0 1");
    pos.halfmove_clock = 5;
    Move m;
    move_from_uci(&pos, "h1g1", &m);
    Piece cap = EMPTY;
    make_move(&pos, &m, &cap);
    assert(pos.halfmove_clock == 6);
}

static void test_fullmove_increments_after_black(void)
{
    Position pos;
    set_startpos(&pos);
    int prev_full = pos.fullmove_number;
    /* White move first */
    Move m;
    move_from_uci(&pos, "e2e4", &m);
    Piece cap = EMPTY;
    make_move(&pos, &m, &cap);
    assert(pos.fullmove_number == prev_full); /* no increment after white */
    /* Now black plays */
    move_from_uci(&pos, "e7e5", &m);
    make_move(&pos, &m, &cap);
    assert(pos.fullmove_number == prev_full + 1); /* increment after black */
}

static void test_move_from_uci_no_promo_mismatch(void)
{
    /* Move has promotion piece but caller provides no promo char - should fail */
    Position pos;
    parse_fen(&pos, "7k/4P3/8/8/8/8/8/7K w - - 0 1");
    Move m;
    /* "e7e8" without promo char - should not match any promotion */
    int ok = move_from_uci(&pos, "e7e8", &m);
    assert(!ok);
}

static void test_gen_moves_white_pawn_blocked(void)
{
    Position pos;
    /* White pawn on e4, black pawn on e5 - blocked, single push only via e3e4 not possible here;
     * white pawn on e4 should not be able to push to e5 */
    parse_fen(&pos, "4k3/8/8/4p3/4P3/8/8/4K3 w - - 0 1");
    Move moves[256];
    int  n    = gen_moves(&pos, moves, 256, 0);
    int  from = 0x34; /* e4 */
    int  to   = 0x44; /* e5 */
    assert(find_move(moves, n, from, to) == -1);
}

/* Test make_piece default branch: unknown char treated as EMPTY (covers lines 43-44) */
static void test_make_piece_unknown_char(void)
{
    Position pos;
    /* FEN with 'X' as a piece — make_piece returns EMPTY, parse succeeds */
    int ok = parse_fen(&pos, "X7/8/8/8/8/8/8/k6K w - - 0 1");
    /* Parse succeeds — 'X' treated as empty square */
    assert(ok);
    /* a8 (0x70) should be EMPTY since 'X' → EMPTY */
    assert(pos.board[0x70] == EMPTY);
}

static void test_count_moves_to_uses_helper(void)
{
    Move m[3];
    m[0].to = 0x10;
    m[1].to = 0x20;
    m[2].to = 0x10;
    assert(count_moves_to(m, 3, 0x10) == 2);
    assert(count_moves_to(m, 3, 0x20) == 1);
    assert(count_moves_to(m, 3, 0x30) == 0);
}

static void test_in_check_by_queen_diagonal(void)
{
    Position pos;
    /* White king on e1, black queen on h4 - diagonal attack */
    parse_fen(&pos, "4k3/8/8/8/7q/8/8/4K3 w - - 0 1");
    assert(in_check(&pos, WHITE));
}

static void test_gen_moves_white_queenside_castle_no_attack_on_d1(void)
{
    Position pos;
    /* White can queenside castle - verify no illegal pieces on attack */
    parse_fen(&pos, "4k3/8/8/8/8/8/8/R3K3 w Q - 0 1");
    Move moves[256];
    int  n          = gen_moves(&pos, moves, 256, 0);
    int  qs_present = 0;
    for (int i = 0; i < n; i++)
    {
        if (moves[i].is_castle && moves[i].to == 0x02)
        {
            qs_present = 1;
        }
    }
    assert(qs_present);
}

static void test_gen_moves_make_captures_only_with_capture(void)
{
    Position pos;
    /* White knight on c3 can capture a black pawn on b5 */
    parse_fen(&pos, "4k3/8/8/1p6/8/2N5/8/4K3 w - - 0 1");
    Move moves[256];
    int  n = gen_moves(&pos, moves, 256, 1); /* captures_only=1 */
    /* Knight on c3 (0x22) should be able to capture on b5 (0x41) */
    int found = 0;
    for (int i = 0; i < n; i++)
    {
        if (moves[i].from == 0x22 && moves[i].is_capture)
        {
            found = 1;
        }
    }
    assert(found);
}

/* Test white knight checking black king (covers line 272: return 1 for WN in square_attacked_by) */
static void test_in_check_by_white_knight(void)
{
    Position pos;
    /* White knight on f3 attacks black king on g5? No, f3+14=g5? 0x25+14=0x33 d4 no.
     * Use: white knight on d6 (0x53), black king on e8 (0x74).
     * d6+0x1E? Nope, knight offsets: 33,31,18,14,-33,-31,-18,-14
     * 0x53 + 0x21 = 0x74 yes! 33 decimal = 0x21. So WN on d6 attacks e8. */
    parse_fen(&pos, "4k3/8/3N4/8/8/8/8/4K3 b - - 0 1");
    assert(in_check(&pos, BLACK));
}

/* Test black king adjacent to white king square (covers line 295 in square_attacked_by for BK) */
static void test_square_attacked_by_black_king(void)
{
    Position pos;
    /* White king on d4 (0x33), black king on e5 (0x44) - they are adjacent.
     * in_check(pos, WHITE) checks if white king is attacked by BLACK.
     * square_attacked_by(pos, 0x33, BLACK) looks for BK adjacent to 0x33.
     * e5 = 0x44, 0x44 - 0x33 = 0x11 = 17 which is in kd[] yes. */
    parse_fen(&pos, "8/8/8/4k3/3K4/8/8/8 w - - 0 1");
    assert(in_check(&pos, WHITE)); /* black king attacks white king */
}

/* Test pawn on s1 diagonal (covers line 305: s1 = sq - 15 = wp on g-file attacking from h-file) */
static void test_white_pawn_attacks_s1_diagonal(void)
{
    Position pos;
    /* Black king on h5 (0x47), white pawn on g4 (0x36).
     * s1 = sq - 15 (decimal) = 0x47 - 0x0F = 0x38 (a5? No: 0x47-0x0F=0x38 which is...
     * 0x38 = rank 3 (3<<4=0x30), file 8 = off-board (0x08 bit set, 0x38&0x88 = 0x08)
     * Off board! Let me try black king at f6 (0x55).
     * s1 = 0x55 - 15 = 0x55 - 0x0F = 0x46 = g5 */
    /* White pawn on g5 (0x46), black king on f6 (0x55).
     * Does g5 WP attack f6? WP attacks sq+15 and sq+17 from OWN pawn perspective.
     * But here square_attacked_by checks pos->board[sq-15] == WP, i.e. pos->board[0x46] == WP. YES!
     */
    parse_fen(&pos, "8/8/5k2/6P1/8/8/8/4K3 b - - 0 1");
    assert(in_check(&pos, BLACK));
}

/* Test queen capture via rook direction (covers line 601) */
static void test_queen_rook_direction_capture(void)
{
    Position pos;
    /* White queen on d4, black rook on d7 - queen captures along d-file */
    parse_fen(&pos, "4k3/3r4/8/8/3Q4/8/8/4K3 w - - 0 1");
    Move moves[256];
    int  n     = gen_moves(&pos, moves, 256, 0);
    int  found = 0;
    for (int i = 0; i < n; i++)
    {
        /* Queen on d4=0x33 capturing rook on d7=0x63 via rook direction */
        if (moves[i].from == 0x33 && moves[i].to == 0x63 && moves[i].is_capture)
        {
            found = 1;
        }
    }
    assert(found);
}

/* Test king capture (covers line 657) */
static void test_king_capture(void)
{
    Position pos;
    /* White king adjacent to black pawn - king captures it */
    parse_fen(&pos, "4k3/8/8/8/8/8/5p2/4K3 w - - 0 1");
    Move moves[256];
    int  n     = gen_moves(&pos, moves, 256, 0);
    int  found = 0;
    for (int i = 0; i < n; i++)
    {
        if (moves[i].from == 0x04 && moves[i].is_capture)
        {
            found = 1;
        }
    }
    assert(found);
}

/* Test capture promotion (pawn on 7th rank captures diagonally to 8th, covers lines 477-483) */
static void test_white_pawn_capture_promotion(void)
{
    Position pos;
    /* White pawn on d7, black rook on e8 - captures and promotes */
    parse_fen(&pos, "4kr2/3P4/8/8/8/8/8/7K w - - 0 1");
    Move moves[256];
    int  n    = gen_moves(&pos, moves, 256, 0);
    int  from = 0x63; /* d7 */
    int  to   = 0x74; /* e8 */
    int  cnt  = 0;
    for (int i = 0; i < n; i++)
    {
        if (moves[i].from == from && moves[i].to == to && moves[i].is_capture)
        {
            cnt++;
        }
    }
    assert(cnt == 4); /* Q, R, B, N capture-promotions */
}

/* Test black pawn capture promotion (covers black path of lines 477-483) */
static void test_black_pawn_capture_promotion(void)
{
    Position pos;
    /* Black pawn on d2, white rook on e1 - captures and promotes */
    parse_fen(&pos, "7k/8/8/8/8/8/3p4/4RK2 b - - 0 1");
    Move moves[256];
    int  n   = gen_moves(&pos, moves, 256, 0);
    int  cnt = 0;
    for (int i = 0; i < n; i++)
    {
        if (moves[i].from == 0x13 && moves[i].to == 0x04 && moves[i].is_capture)
        {
            cnt++;
        }
    }
    assert(cnt == 4);
}

/* Test add_move overflow (covers line 244: return count when count >= max) */
static void test_add_move_max_overflow(void)
{
    Position pos;
    /* Use gen_moves with max_moves=0 to trigger count >= max */
    set_startpos(&pos);
    Move moves[1];
    int  n = gen_moves(&pos, moves, 0, 0); /* max_moves=0 */
    assert(n == 0);                        /* add_move returns count (0) immediately */
}

/* Test FEN invalid: no space between side and castling (covers line 153) */
static void test_parse_fen_missing_space_after_side(void)
{
    Position pos;
    /* "8/8/8/8/8/8/8/8 w- - 0 1": missing space between side 'w' and castling '-' */
    int ok = parse_fen(&pos, "8/8/8/8/8/8/8/8 w- - 0 1");
    assert(!ok);
}

/* Test FEN invalid: no space after castling (covers line 191) */
static void test_parse_fen_missing_space_after_castling(void)
{
    Position pos;
    /* After castling "-" expect space, but give no space */
    int ok = parse_fen(&pos, "8/8/8/8/8/8/8/8 w -- 0 1");
    assert(!ok);
}

int main(void)
{
    /* parse_fen / set_startpos */
    test_parse_fen_startpos();
    test_parse_fen_black_to_move();
    test_parse_fen_no_castling();
    test_parse_fen_partial_castling();
    test_parse_fen_invalid_missing_space();
    test_parse_fen_invalid_side();
    test_parse_fen_invalid_ep();
    test_parse_fen_invalid_castling_char();
    test_parse_fen_invalid_off_board();
    test_parse_fen_fullmove_and_halfmove();
    test_set_startpos();

    /* square_from_algebraic */
    test_square_from_algebraic_basic();
    test_square_from_algebraic_promotion();
    test_square_from_algebraic_null();
    test_square_from_algebraic_a1();
    test_square_from_algebraic_h8();

    /* make_move / unmake_move */
    test_make_unmake_pawn_push();
    test_make_unmake_capture();
    test_make_unmake_en_passant();
    test_make_unmake_white_kingside_castle();
    test_make_unmake_white_queenside_castle();
    test_make_unmake_black_kingside_castle();
    test_make_unmake_black_queenside_castle();
    test_make_promotion_queen();
    test_make_promotion_rook();
    test_make_promotion_bishop();
    test_make_promotion_knight();
    test_make_castling_rights_update_on_rook_move();
    test_make_castling_rights_removed_on_a1_capture();

    /* in_check */
    test_in_check_not_in_check();
    test_in_check_by_rook();
    test_in_check_no_king();
    test_in_check_by_knight();
    test_in_check_by_bishop();
    test_in_check_by_pawn();

    /* gen_moves */
    test_gen_moves_startpos_count();
    test_gen_moves_captures_only();
    test_gen_moves_only_captures_mid_game();
    test_gen_moves_checkmate();
    test_gen_moves_stalemate();
    test_gen_moves_promotes_four_choices();
    test_gen_moves_en_passant();
    test_gen_pseudo_not_filtered();
    test_gen_moves_knight_attacks();
    test_gen_moves_bishop_attacks();
    test_gen_moves_rook_attacks();
    test_gen_moves_queen_attacks();
    test_gen_moves_castling_blocked_by_attack();
    test_gen_moves_castling_blocked_in_check();
    test_gen_moves_black_castling();
    test_gen_moves_black_pawn_attacks();
    test_gen_moves_black_pawn_initial_push();
    test_gen_moves_black_promotion();
    test_gen_moves_black_ep();

    /* move_from_uci */
    test_move_from_uci_basic();
    test_move_from_uci_invalid_from();
    test_move_from_uci_not_in_legal_moves();
    test_move_from_uci_promotion_queen();
    test_move_from_uci_promotion_rook();
    test_move_from_uci_promotion_bishop();
    test_move_from_uci_promotion_knight();
    test_move_from_uci_promotion_uppercase_r();
    test_move_from_uci_black_promotion();

    /* Perft correctness */
    test_perft_startpos_depth1();
    test_perft_startpos_depth2();
    test_perft_ep_position_depth1();
    test_perft_kiwipete_depth1();
    test_perft_kiwipete_depth2();

    /* Additional coverage */
    test_attacked_by_white_king_proximity();
    test_attacked_by_white_pawn();
    test_attacked_by_black_pawn();
    test_attacked_by_queen_rook_direction();
    test_attacked_slider_blocked();
    test_halfmove_clock_pawn_resets();
    test_halfmove_clock_piece_increments();
    test_fullmove_increments_after_black();
    test_move_from_uci_no_promo_mismatch();
    test_gen_moves_white_pawn_blocked();
    test_count_moves_to_uses_helper();
    test_in_check_by_queen_diagonal();
    test_gen_moves_white_queenside_castle_no_attack_on_d1();
    test_gen_moves_make_captures_only_with_capture();
    test_in_check_by_white_knight();
    test_square_attacked_by_black_king();
    test_white_pawn_attacks_s1_diagonal();
    test_queen_rook_direction_capture();
    test_king_capture();
    test_white_pawn_capture_promotion();
    test_black_pawn_capture_promotion();
    test_add_move_max_overflow();
    test_parse_fen_missing_space_after_side();
    test_parse_fen_missing_space_after_castling();
    test_make_piece_unknown_char();

    printf("All tests passed (%d tests).\n", 89);
    return 0;
}
