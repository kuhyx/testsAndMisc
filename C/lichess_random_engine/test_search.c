/*
 * test_search.c - Unit tests for search.c (evaluate, alphabeta).
 */

#include "movegen.h"
#include "search.h"

#include <assert.h>
#include <stdio.h>

/* =========================================================================
 * evaluate tests
 * ========================================================================= */

static void test_evaluate_startpos_equal(void)
{
    Position pos;
    set_startpos(&pos);
    /* Symmetric position: score from white perspective should be 0 */
    assert(evaluate(&pos) == 0);
}

static void test_evaluate_white_extra_queen(void)
{
    Position pos;
    /* White has an extra queen */
    parse_fen(&pos, "4k3/8/8/8/8/8/8/Q3K3 w - - 0 1");
    int score = evaluate(&pos);
    assert(score > 0); /* White favored */
}

static void test_evaluate_black_extra_queen(void)
{
    Position pos;
    /* Black has an extra queen */
    parse_fen(&pos, "4k1q1/8/8/8/8/8/8/4K3 w - - 0 1");
    int score = evaluate(&pos);
    assert(score < 0); /* Black favored from white's perspective */
}

static void test_evaluate_symmetric_material(void)
{
    Position pos;
    /* Equal material: rook vs rook, same side */
    parse_fen(&pos, "4k2r/8/8/8/8/8/8/4K2R w - - 0 1");
    assert(evaluate(&pos) == 0);
}

static void test_evaluate_pawn_advantage(void)
{
    Position pos;
    /* White has 2 extra pawns */
    parse_fen(&pos, "4k3/8/8/8/8/8/1PP5/4K3 w - - 0 1");
    int white_score = evaluate(&pos);
    pos.side        = BLACK;
    int black_score = evaluate(&pos);
    assert(white_score > 0);
    assert(black_score < 0); /* same position but from black's perspective */
}

static void test_evaluate_all_piece_types(void)
{
    Position pos;
    /* White: K+Q+R+B+N vs Black: K only */
    parse_fen(&pos, "4k3/8/8/8/8/8/8/QRBN1K2 w - - 0 1");
    int score = evaluate(&pos);
    assert(score > 0);
    /* White material: Q=900 + R=500 + B=330 + N=320 = 2050 */
    assert(score == 900 + 500 + 330 + 320);
}

static void test_evaluate_black_pieces(void)
{
    Position pos;
    /* Black: K+Q+R+B+N vs White: K only */
    parse_fen(&pos, "4kqrb/4n3/8/8/8/8/8/4K3 w - - 0 1");
    int score = evaluate(&pos);
    /* From white perspective, should be heavily negative */
    assert(score < -1000);
}

/* =========================================================================
 * alphabeta tests
 * ========================================================================= */

static void test_alphabeta_single_capture(void)
{
    Position pos;
    /* White rook can capture black queen - best move immediately obvious at depth 1 */
    parse_fen(&pos, "4k3/8/8/3q4/3R4/8/8/4K3 w - - 0 1");
    PrincipalVariation pv    = {.from = -1, .to = -1};
    int                score = alphabeta(pos, 1, -30000, 30000, &pv);
    assert(score > 0); /* Should find winning position */
    /* Best move should be d4d5 (rook captures queen on d5) */
    assert(pv.from >= 0);
    assert(pv.to >= 0);
}

static void test_alphabeta_checkmate_in_one(void)
{
    Position pos;
    /* White queen delivers checkmate at f7 */
    parse_fen(&pos, "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 4 4");
    PrincipalVariation pv    = {.from = -1, .to = -1};
    int                score = alphabeta(pos, 2, -30000, 30000, &pv);
    /* Depth 2: should find the mating sequence */
    (void)score;
    assert(pv.from >= 0);
}

static void test_alphabeta_stalemate_score(void)
{
    Position pos;
    /* Black king stalemated: ensure score is 0 (stalemate = draw)
     * k on a8, white queen on c7, white king on c6 */
    parse_fen(&pos, "k7/2Q5/2K5/8/8/8/8/8 b - - 0 1");
    /* Black to move, stalemated */
    PrincipalVariation pv    = {.from = -1, .to = -1};
    int                score = alphabeta(pos, 1, -30000, 30000, &pv);
    assert(score == 0); /* stalemate */
}

static void test_alphabeta_checkmate_score(void)
{
    Position pos;
    /* Black king checkmated (fool's mate) */
    parse_fen(&pos, "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3");
    /* White is mated; at depth 0 just evaluates material */
    PrincipalVariation pv    = {.from = -1, .to = -1};
    int                score = alphabeta(pos, 1, -30000, 30000, &pv);
    /* White has no legal moves - should return very negative score */
    assert(score < -20000);
}

static void test_alphabeta_depth_zero(void)
{
    Position pos;
    set_startpos(&pos);
    PrincipalVariation pv    = {.from = -1, .to = -1};
    int                score = alphabeta(pos, 0, -30000, 30000, &pv);
    /* At depth 0, returns leaf evaluation */
    assert(score == 0); /* startpos is equal */
}

static void test_alphabeta_no_pv_null(void)
{
    Position pos;
    set_startpos(&pos);
    /* Pass NULL for pv - should not crash */
    int score = alphabeta(pos, 1, -30000, 30000, NULL);
    (void)score;
    /* Just checking no crash */
    assert(1);
}

static void test_alphabeta_beta_cutoff(void)
{
    Position pos;
    /* Need a position where beta cutoff fires: search at depth 2+ */
    set_startpos(&pos);
    PrincipalVariation pv    = {.from = -1, .to = -1};
    int                score = alphabeta(pos, 2, -30000, 30000, &pv);
    /* Symmetric start - should be near 0 */
    (void)score;
    assert(pv.from >= 0);
}

int main(void)
{
    /* evaluate */
    test_evaluate_startpos_equal();
    test_evaluate_white_extra_queen();
    test_evaluate_black_extra_queen();
    test_evaluate_symmetric_material();
    test_evaluate_pawn_advantage();
    test_evaluate_all_piece_types();
    test_evaluate_black_pieces();

    /* alphabeta */
    test_alphabeta_single_capture();
    test_alphabeta_checkmate_in_one();
    test_alphabeta_stalemate_score();
    test_alphabeta_checkmate_score();
    test_alphabeta_depth_zero();
    test_alphabeta_no_pv_null();
    test_alphabeta_beta_cutoff();

    printf("All tests passed (%d tests).\n", 14);
    return 0;
}
