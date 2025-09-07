// Heuristic engine with optional explanation and analysis output
// Usage:
//   random_engine [--seed N] [--fen FEN] [--explain] [--analyze UCI] <move1> <move2> ...
// Behavior:
//   - If --fen is provided, the engine parses the position and computes features per move
//     (check, capture value, promotion gain, material delta) directly from the position.
//   - If no --fen is provided but a move is annotated as 'uci;key=value;...' the engine
//     parses features from annotations. Recognized keys: chk (0/1), c (capture cp), prom (cp gain),
//     mat (cp delta), mate (0/1).
//   - Otherwise, assigns a pseudo-random score using the seed.
//   - Picks the highest-scoring move
//   - Default output: prints chosen move
//   - With --explain: prints JSON including scores, chosen index, seed, and optional analysis of a provided candidate

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <ctype.h>
#include <math.h>

// --- Minimal chess board utilities for FEN, move application, and attacks ---

typedef struct {
    char squares[64];   // 0..63 (a1=0, h8=63). Lowercase black, uppercase white; '.' empty
    int white_to_move;  // 1 if white to move, 0 if black
} Board;

static int file_of(int idx) { return idx % 8; }
static int rank_of(int idx) { return idx / 8; }
static int idx_from_fr(int f, int r) { return r * 8 + f; }

static int is_white(char p) { return p >= 'A' && p <= 'Z'; }
static int is_black(char p) { return p >= 'a' && p <= 'z'; }
static int same_color(char a, char b) { return (is_white(a) && is_white(b)) || (is_black(a) && is_black(b)); }

static int piece_value_cp(char p) {
    switch (tolower((unsigned char)p)) {
        case 'p': return 100;
        case 'n': return 320;
        case 'b': return 330;
        case 'r': return 500;
        case 'q': return 900;
        case 'k': return 0; // king's value excluded for material sums
        default: return 0;
    }
}

static int parse_fen(Board *b, const char *fen) {
    // Parse piece placement and active color; ignore castling, ep, halfmove, fullmove
    memset(b->squares, '.', sizeof(b->squares));
    b->white_to_move = 1;
    if (!fen || !*fen) return 0;
    // piece placement
    int f = 0, r = 7; // start at a8
    const char *p = fen;
    while (*p && !(p[0] == ' ')) {
        char c = *p++;
        if (c == '/') { f = 0; r--; if (r < 0) return 0; continue; }
        if (c >= '1' && c <= '8') { f += (c - '0'); if (f > 8) return 0; continue; }
        if (isalpha((unsigned char)c)) {
            if (f >= 8 || r < 0) return 0;
            b->squares[idx_from_fr(f, r)] = c;
            f++;
        } else {
            return 0;
        }
    }
    if (*p == ' ') p++;
    // active color
    if (*p == 'w') { b->white_to_move = 1; p++; }
    else if (*p == 'b') { b->white_to_move = 0; p++; }
    // done
    return 1;
}

static int find_king(const Board *b, int white) {
    char k = white ? 'K' : 'k';
    for (int i = 0; i < 64; ++i) if (b->squares[i] == k) return i;
    return -1;
}

static int on_board(int f, int r) { return f >= 0 && f < 8 && r >= 0 && r < 8; }

static int sq_attacked_by(const Board *b, int target_idx, int by_white) {
    int tf = file_of(target_idx), tr = rank_of(target_idx);
    // Knights
    const int kdf[8] = {1,2, 2,1, -1,-2, -2,-1};
    const int kdr[8] = {2,1, -1,-2, 2,1, -1,-2};
    for (int i = 0; i < 8; ++i) {
        int f = tf + kdf[i], r = tr + kdr[i];
        if (on_board(f, r)) {
            char p = b->squares[idx_from_fr(f, r)];
            if (by_white ? p == 'N' : p == 'n') return 1;
        }
    }
    // King
    for (int df = -1; df <= 1; ++df) for (int dr = -1; dr <= 1; ++dr) if (df || dr) {
        int f = tf + df, r = tr + dr;
        if (on_board(f, r)) {
            char p = b->squares[idx_from_fr(f, r)];
            if (by_white ? p == 'K' : p == 'k') return 1;
        }
    }
    // Pawns
    if (by_white) {
        int f1 = tf - 1, r1 = tr - 1;
        int f2 = tf + 1, r2 = tr - 1;
        if (on_board(f1, r1) && b->squares[idx_from_fr(f1, r1)] == 'P') return 1;
        if (on_board(f2, r2) && b->squares[idx_from_fr(f2, r2)] == 'P') return 1;
    } else {
        int f1 = tf - 1, r1 = tr + 1;
        int f2 = tf + 1, r2 = tr + 1;
        if (on_board(f1, r1) && b->squares[idx_from_fr(f1, r1)] == 'p') return 1;
        if (on_board(f2, r2) && b->squares[idx_from_fr(f2, r2)] == 'p') return 1;
    }
    // Sliding: bishops/queens (diagonals)
    const int dsf[4] = {1, 1, -1, -1};
    const int dsr[4] = {1, -1, 1, -1};
    for (int d = 0; d < 4; ++d) {
        int f = tf + dsf[d], r = tr + dsr[d];
        while (on_board(f, r)) {
            char p = b->squares[idx_from_fr(f, r)];
            if (p != '.') {
                if (by_white ? (p == 'B' || p == 'Q') : (p == 'b' || p == 'q')) return 1;
                break;
            }
            f += dsf[d]; r += dsr[d];
        }
    }
    // Sliding: rooks/queens (orthogonals)
    const int rsf[4] = {1, -1, 0, 0};
    const int rsr[4] = {0, 0, 1, -1};
    for (int d = 0; d < 4; ++d) {
        int f = tf + rsf[d], r = tr + rsr[d];
        while (on_board(f, r)) {
            char p = b->squares[idx_from_fr(f, r)];
            if (p != '.') {
                if (by_white ? (p == 'R' || p == 'Q') : (p == 'r' || p == 'q')) return 1;
                break;
            }
            f += rsf[d]; r += rsr[d];
        }
    }
    return 0;
}

static int count_attackers(const Board *b, int target_idx, int by_white) {
    int tf = file_of(target_idx), tr = rank_of(target_idx);
    int cnt = 0;
    // Knights
    const int kdf[8] = {1,2, 2,1, -1,-2, -2,-1};
    const int kdr[8] = {2,1, -1,-2, 2,1, -1,-2};
    for (int i = 0; i < 8; ++i) {
        int f = tf + kdf[i], r = tr + kdr[i];
        if (on_board(f, r)) {
            char p = b->squares[idx_from_fr(f, r)];
            if (by_white ? p == 'N' : p == 'n') cnt++;
        }
    }
    // King
    for (int df = -1; df <= 1; ++df) for (int dr = -1; dr <= 1; ++dr) if (df || dr) {
        int f = tf + df, r = tr + dr;
        if (on_board(f, r)) {
            char p = b->squares[idx_from_fr(f, r)];
            if (by_white ? p == 'K' : p == 'k') cnt++;
        }
    }
    // Pawns
    if (by_white) {
        int f1 = tf - 1, r1 = tr - 1;
        int f2 = tf + 1, r2 = tr - 1;
        if (on_board(f1, r1) && b->squares[idx_from_fr(f1, r1)] == 'P') cnt++;
        if (on_board(f2, r2) && b->squares[idx_from_fr(f2, r2)] == 'P') cnt++;
    } else {
        int f1 = tf - 1, r1 = tr + 1;
        int f2 = tf + 1, r2 = tr + 1;
        if (on_board(f1, r1) && b->squares[idx_from_fr(f1, r1)] == 'p') cnt++;
        if (on_board(f2, r2) && b->squares[idx_from_fr(f2, r2)] == 'p') cnt++;
    }
    // Sliding: bishops/queens (diagonals)
    const int dsf[4] = {1, 1, -1, -1};
    const int dsr[4] = {1, -1, 1, -1};
    for (int d = 0; d < 4; ++d) {
        int f = tf + dsf[d], r = tr + dsr[d];
        while (on_board(f, r)) {
            char p = b->squares[idx_from_fr(f, r)];
            if (p != '.') {
                if (by_white ? (p == 'B' || p == 'Q') : (p == 'b' || p == 'q')) cnt++;
                break;
            }
            f += dsf[d]; r += dsr[d];
        }
    }
    // Sliding: rooks/queens (orthogonals)
    const int rsf[4] = {1, -1, 0, 0};
    const int rsr[4] = {0, 0, 1, -1};
    for (int d = 0; d < 4; ++d) {
        int f = tf + rsf[d], r = tr + rsr[d];
        while (on_board(f, r)) {
            char p = b->squares[idx_from_fr(f, r)];
            if (p != '.') {
                if (by_white ? (p == 'R' || p == 'Q') : (p == 'r' || p == 'q')) cnt++;
                break;
            }
            f += rsf[d]; r += rsr[d];
        }
    }
    return cnt;
}

static int min_attacker_value(const Board *b, int target_idx, int by_white) {
    int tf = file_of(target_idx), tr = rank_of(target_idx);
    int best = 1e9;
    // Knights
    const int kdf[8] = {1,2, 2,1, -1,-2, -2,-1};
    const int kdr[8] = {2,1, -1,-2, 2,1, -1,-2};
    for (int i = 0; i < 8; ++i) {
        int f = tf + kdf[i], r = tr + kdr[i];
        if (on_board(f, r)) {
            char p = b->squares[idx_from_fr(f, r)];
            if (by_white ? p == 'N' : p == 'n') { int v = piece_value_cp(p); if (v < best) best = v; }
        }
    }
    // King
    for (int df = -1; df <= 1; ++df) for (int dr = -1; dr <= 1; ++dr) if (df || dr) {
        int f = tf + df, r = tr + dr;
        if (on_board(f, r)) {
            char p = b->squares[idx_from_fr(f, r)];
            if (by_white ? p == 'K' : p == 'k') { int v = piece_value_cp(p); if (v < best) best = v; }
        }
    }
    // Pawns
    if (by_white) {
        int f1 = tf - 1, r1 = tr - 1;
        int f2 = tf + 1, r2 = tr - 1;
        if (on_board(f1, r1) && b->squares[idx_from_fr(f1, r1)] == 'P') { int v = 100; if (v < best) best = v; }
        if (on_board(f2, r2) && b->squares[idx_from_fr(f2, r2)] == 'P') { int v = 100; if (v < best) best = v; }
    } else {
        int f1 = tf - 1, r1 = tr + 1;
        int f2 = tf + 1, r2 = tr + 1;
        if (on_board(f1, r1) && b->squares[idx_from_fr(f1, r1)] == 'p') { int v = 100; if (v < best) best = v; }
        if (on_board(f2, r2) && b->squares[idx_from_fr(f2, r2)] == 'p') { int v = 100; if (v < best) best = v; }
    }
    // Sliding: bishops/queens (diagonals)
    const int dsf[4] = {1, 1, -1, -1};
    const int dsr[4] = {1, -1, 1, -1};
    for (int d = 0; d < 4; ++d) {
        int f = tf + dsf[d], r = tr + dsr[d];
        while (on_board(f, r)) {
            char p = b->squares[idx_from_fr(f, r)];
            if (p != '.') {
                if (by_white ? (p == 'B' || p == 'Q') : (p == 'b' || p == 'q')) { int v = piece_value_cp(p); if (v < best) best = v; }
                break;
            }
            f += dsf[d]; r += dsr[d];
        }
    }
    // Sliding: rooks/queens (orthogonals)
    const int rsf[4] = {1, -1, 0, 0};
    const int rsr[4] = {0, 0, 1, -1};
    for (int d = 0; d < 4; ++d) {
        int f = tf + rsf[d], r = tr + rsr[d];
        while (on_board(f, r)) {
            char p = b->squares[idx_from_fr(f, r)];
            if (p != '.') {
                if (by_white ? (p == 'R' || p == 'Q') : (p == 'r' || p == 'q')) { int v = piece_value_cp(p); if (v < best) best = v; }
                break;
            }
            f += rsf[d]; r += rsr[d];
        }
    }
    if (best == (int)1e9) return 0;
    return best;
}

static int material_cp(const Board *b) {
    int w = 0, bl = 0;
    for (int i = 0; i < 64; ++i) {
        char p = b->squares[i];
        if (p == '.') continue;
        int v = piece_value_cp(p);
        if (is_white(p)) w += v; else bl += v;
    }
    return w - bl; // positive if white ahead
}

static int parse_uci_move(const char *uci, int *from, int *to, char *prom) {
    // uci like e2e4, e7e8q
    if (!uci || strlen(uci) < 4) return 0;
    int f1 = uci[0] - 'a';
    int r1 = uci[1] - '1';
    int f2 = uci[2] - 'a';
    int r2 = uci[3] - '1';
    if (!on_board(f1, r1) || !on_board(f2, r2)) return 0;
    *from = idx_from_fr(f1, r1);
    *to = idx_from_fr(f2, r2);
    *prom = 0;
    if (uci[4]) {
        *prom = uci[4];
    }
    return 1;
}

static void apply_move(const Board *in, const char *uci, Board *out, int *cap_cp, int *prom_gain_cp) {
    *out = *in; // shallow copy
    *cap_cp = 0;
    *prom_gain_cp = 0;
    int from, to; char prom;
    if (!parse_uci_move(uci, &from, &to, &prom)) return;
    char mover = out->squares[from];
    char captured = out->squares[to];
    if (captured != '.') *cap_cp = piece_value_cp(captured);
    // move piece
    out->squares[to] = mover;
    out->squares[from] = '.';
    // handle promotion
    if (prom) {
        int is_w = is_white(mover);
        char p = (char)tolower((unsigned char)prom);
        char prom_piece = p == 'q' ? (is_w ? 'Q' : 'q') : p == 'r' ? (is_w ? 'R' : 'r') : p == 'b' ? (is_w ? 'B' : 'b') : (is_w ? 'N' : 'n');
        int gain = piece_value_cp(prom_piece) - piece_value_cp(is_w ? 'P' : 'p');
        *prom_gain_cp = gain;
        out->squares[to] = prom_piece;
    }
    // toggle side to move
    out->white_to_move = !in->white_to_move;
}

static unsigned int parse_seed_or_default(int *pargc, char ***pargv) {
    unsigned int seed = (unsigned int)time(NULL) ^ (unsigned int)getpid();
    int argc = *pargc;
    char **argv = *pargv;
    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--seed") == 0 && i + 1 < argc) {
            seed = (unsigned int)strtoul(argv[i + 1], NULL, 10);
            // remove the two args
            for (int j = i; j + 2 < argc; ++j) argv[j] = argv[j + 2];
            *pargc -= 2;
            return seed;
        }
    }
    return seed;
}

typedef struct {
    const char *arg_raw;   // original argument string
    char uci[16];          // extracted UCI (up to 7-8 chars normally)
    int has_anno;          // whether annotations were present
    // parsed features
    int chk;               // 0/1
    int mate;              // 0/1
    int in_check;          // 0/1: side to move is currently in check (pre-move)
    double cap_cp;         // capture centipawns
    double prom_cp;        // promotion centipawns
    double mat_cp;         // material delta centipawns
    // attackers/defenders heuristic after the move lands on destination
    double opp_min_att_cp; // opponent's least valuable attacker on destination (after move)
    double us_min_att_cp;  // our least valuable attacker on destination (after move)
    double piece_cp;       // our moved piece's value after move (post-promotion)
    double see_cp;         // simple SEE: cap_cp - opp_min_att_cp (captures only)
    double risk_cp;        // if non-capture and square is attacked by opp and not defended by us, risk ~= min(piece_cp, opp_min_att_cp)
    // king attack/mobility features
    double atk_opp_king;   // number of our attackers to opponent's king square after move
    double opp_king_mob;   // opponent king escape squares after move (lower is better)
    // threat features
    double threat_q;       // after move, our side attacks enemy queen square
    double threat_r;       // after move, our side attacks enemy rook square (any)
    double prox_king;      // destination square adjacent to enemy king
    double score;          // computed score
    // check characterization
    int checker_is_slider;     // 1 if checking piece is rook/bishop/queen
    int line_check_blockable;  // 1 if sliding check has at least one interposing square (thus blockable)
    // opponent threats on our heavy pieces after our move
    double opp_threat_our_q;   // opponent attacks our queen square (after move)
    double opp_threat_our_r;   // opponent attacks our rook squares (sum over rooks, 0.5 each)
    // our defenders of our heavy pieces (to scale penalties)
    double our_q_def;          // number of our attackers defending our queen square
    double our_r_def;          // aggregated (0.5 per rook with at least one defender)
} MoveInfo;

static void parse_move_spec(const char *spec, MoveInfo *mi) {
    // Copy UCI up to ';' or end
    mi->arg_raw = spec;
    mi->uci[0] = '\0';
    mi->has_anno = 0;
    mi->chk = 0;
    mi->mate = 0;
    mi->in_check = 0;
    mi->cap_cp = 0.0;
    mi->prom_cp = 0.0;
    mi->mat_cp = 0.0;
    mi->opp_min_att_cp = 0.0;
    mi->us_min_att_cp = 0.0;
    mi->piece_cp = 0.0;
    mi->see_cp = 0.0;
    mi->risk_cp = 0.0;
    mi->atk_opp_king = 0.0;
    mi->opp_king_mob = 0.0;
    mi->threat_q = 0.0;
    mi->threat_r = 0.0;
    mi->prox_king = 0.0;
    mi->score = 0.0;
    mi->checker_is_slider = 0;
    mi->line_check_blockable = 0;
    mi->opp_threat_our_q = 0.0;
    mi->opp_threat_our_r = 0.0;
    mi->our_q_def = 0.0;
    mi->our_r_def = 0.0;

    const char *semi = strchr(spec, ';');
    size_t uci_len = semi ? (size_t)(semi - spec) : strlen(spec);
    if (uci_len >= sizeof(mi->uci)) uci_len = sizeof(mi->uci) - 1;
    memcpy(mi->uci, spec, uci_len);
    mi->uci[uci_len] = '\0';

    if (!semi) return;
    mi->has_anno = 1;
    const char *p = semi + 1;
    while (*p) {
        // key=value; segments
        const char *kv_end = strchr(p, ';');
        size_t len = kv_end ? (size_t)(kv_end - p) : strlen(p);
        if (len > 0) {
            // Parse known keys: chk, mate, c, prom, mat
            if (strncmp(p, "chk=", 4) == 0) {
                mi->chk = atoi(p + 4);
            } else if (strncmp(p, "mate=", 5) == 0) {
                mi->mate = atoi(p + 5);
            } else if (strncmp(p, "c=", 2) == 0) {
                mi->cap_cp = atof(p + 2);
            } else if (strncmp(p, "prom=", 6) == 0) {
                mi->prom_cp = atof(p + 6);
            } else if (strncmp(p, "mat=", 4) == 0) {
                mi->mat_cp = atof(p + 4);
            }
        }
        if (!kv_end) break;
        p = kv_end + 1;
    }
}

static double heuristic_score(const MoveInfo *mi, unsigned int seed_state) {
    // Weighted score from features; add tiny noise from seed to break ties
    double s = 0.0;
    if (mi->mate) s += 100000.0;            // winning immediately trumps all
    // Checks: scale by pressure; devalue "empty" checks with no material promise
    if (mi->chk) {
    double chk_bonus = 250.0 + 80.0 * mi->atk_opp_king - 60.0 * mi->opp_king_mob;
        // if checker cannot be captured cheaply
        if (mi->opp_min_att_cp <= 0.0) chk_bonus += 500.0; // no attackers on checker
        else if (mi->opp_min_att_cp >= mi->piece_cp - 1e-6) chk_bonus += 300.0; // only expensive capture
        // if our defender is cheaper than their attacker, exchange favors us
        if (mi->us_min_att_cp > 0.0 && mi->opp_min_att_cp > 0.0 && mi->us_min_att_cp < mi->opp_min_att_cp) chk_bonus += 150.0;
        // strongly devalue queen checks that only pick up a pawn (common blunder bait)
        if (mi->piece_cp >= 850.0 && mi->cap_cp <= 100.0 && mi->prom_cp <= 0.0) {
            // if king still has escapes, this is usually just a bait check
            if (mi->opp_king_mob > 0.0) chk_bonus *= 0.10; else chk_bonus *= 0.25;
        }
        // big bonus when the check leaves the opponent king with no legal escapes
        if (mi->opp_king_mob <= 0.0) {
            // Zero king mobility is a strong tactical motif even if the check can be blocked
            if (mi->checker_is_slider && mi->line_check_blockable) {
                chk_bonus += 800.0;
            } else {
                chk_bonus += 1500.0;
            }
        }
        // Checking captures are especially forcing, except when it's a queen snatching a pawn
        if (mi->cap_cp > 0.0) {
            double add = 400.0;
            if (mi->piece_cp >= 850.0 && mi->cap_cp <= 100.0 && mi->opp_king_mob > 0.0) add = 30.0;
            chk_bonus += add;
        }
    if (mi->opp_king_mob > 0.0 && mi->cap_cp <= 0.0 && mi->see_cp <= 0.0 && mi->mat_cp <= 0.0) chk_bonus *= 0.3;
        s += chk_bonus;
    }
    s += 1.5 * mi->cap_cp;                  // value captures strongly
    // prefer winning exchanges where the capturing piece is cheaper than the captured value
    if (mi->cap_cp > 0.0) {
        if (mi->piece_cp >= 850.0) {
            // Queen captures: be cautious; usually lead to heavy trades
            s += 0.4 * (mi->cap_cp - mi->piece_cp);
            s -= 200.0; // mild global discouragement of queen snatches
            if (mi->opp_min_att_cp >= 500.0) s -= 200.0; // likely immediate recapture by heavy piece
            if (mi->us_min_att_cp <= 0.0 && mi->opp_min_att_cp > 0.0) s -= 600.0; // no friendly cover on destination
        } else {
            double exch = mi->cap_cp - mi->piece_cp;
            double exch_w = (mi->piece_cp <= 120.0) ? 1.0 : 3.5; // further dampen pawn capture bias
            s += exch_w * exch;
            // Prefer minor taking heavy piece, or rook taking queen
            if ((mi->piece_cp <= 350.0 && mi->cap_cp >= 500.0) || (mi->piece_cp == 500.0 && mi->cap_cp >= 900.0)) {
                s += 300.0;
            }
            // Strongly prefer minor piece (B/N) capturing a heavy piece
            if (mi->cap_cp >= 500.0 && mi->piece_cp <= 350.0) s += 900.0;
            // No generic heavy-vs-heavy penalty; handled by context-specific terms
    }
    }
    s += 2.0 * mi->prom_cp;                 // promotions are very strong
    // material swing, but discount when the gain is from a capture that moves into enemy fire
    double mat_term = 1.5 * mi->mat_cp;
    if (mi->cap_cp > 0.0 && mi->opp_min_att_cp > 0.0) {
        // if our piece on destination is at least as expensive as their cheapest attacker, discount,
        // but keep more of the material when the exchange is clearly favorable (SEE positive or big value gap)
        if (mi->piece_cp >= mi->opp_min_att_cp - 1e-6) {
            double discount = 0.35;
            if (mi->piece_cp < 850.0) {
                double gap = mi->cap_cp - mi->piece_cp; // how favorable the capture is by piece type
                if (gap >= 150.0) discount = 0.8;        // minor takes rook/queen -> keep most of the material
                if (mi->see_cp >= 200.0) discount += 0.1; // further relax when SEE agrees
                if (discount > 0.9) discount = 0.9;
            }
            mat_term *= discount;
        }
        // queen-specific extra discount always applies for risky queen plant
        if (mi->piece_cp >= 850.0) mat_term *= 0.35;
    }
    s += mat_term;
    s += 0.2 * mi->see_cp;                  // prefer profitable captures after recapture (more tempered)
    s -= 1.0 * mi->risk_cp;                 // avoid walking into obvious captures
    s += 40.0 * mi->atk_opp_king;           // general king pressure
    s -= 40.0 * mi->opp_king_mob;           // reduce opponent king mobility (moderate impact)
    // destination safety: even if defended, prefer squares where the cheapest opponent attacker
    // is not much cheaper than our defender or our moved piece
    if (mi->opp_min_att_cp > 0.0) {
        double ref = mi->piece_cp;
        if (mi->us_min_att_cp > 0.0 && mi->us_min_att_cp < ref) ref = mi->us_min_att_cp;
        double slack = ref - mi->opp_min_att_cp; // positive means they can start a favorable exchange
        if (slack > 0.0) s -= 0.3 * slack;
    }
    // Discourage low-value recaptures that hand the initiative back (pawn taking our minor while enabling rook threats)
    if (mi->cap_cp >= 300.0 && mi->piece_cp <= 120.0 && mi->atk_opp_king <= 0.0 && mi->threat_r > 0.0) {
        s -= 600.0;
    }
    // Defensive interposition: encourage rook blocks where recapture favors us (e.g., ...Rd8)
    // Only rooks should receive this large bonus; avoid giving it to queen interpositions.
    if (mi->cap_cp <= 0.0 && mi->piece_cp == 500.0 && mi->opp_min_att_cp >= 850.0 && mi->us_min_att_cp > 0.0 && mi->us_min_att_cp <= 350.0) {
        s += 900.0;
    }
    // When in check, slightly prefer blocking with a minor piece over using the queen
    // Heuristic: non-capture, minor piece moves to a square attacked by a heavy piece (likely block),
    // and we have at least one defender covering it (safe-ish interposition)
    if (mi->in_check && mi->cap_cp <= 0.0 && mi->piece_cp > 0.0 && mi->piece_cp <= 350.0 && mi->opp_min_att_cp >= 500.0 && mi->us_min_att_cp > 0.0) {
        s += 150.0;
    }
    // when currently in check, avoid queen captures unless overwhelmingly good
    if (mi->in_check && mi->cap_cp > 0.0 && mi->piece_cp >= 850.0) {
        s -= 800.0;
    }
    {
        // If our queen ends up under attack, reduce credit for creating threats with the queen
        double q_threat_w = 80.0;
        if (mi->opp_threat_our_q > 0.0) q_threat_w *= 0.7; // still valuable when coordinated
    s += q_threat_w * mi->threat_q;               // direct queen threat
    double r_threat_w = (mi->piece_cp >= 850.0) ? 400.0 : 120.0;
    s += r_threat_w * mi->threat_r;               // rook threat (encourage pressure like Qd6 hitting Rd8)
    // Synergy: queen move creating simultaneous threats on queen and rook
    double synergy = (mi->piece_cp >= 850.0 && mi->threat_q > 0.0 && mi->threat_r > 0.0) ? 350.0 : 0.0;
        if (mi->opp_threat_our_q > 0.0) synergy *= 0.3;
        s += synergy;
    }
    // Penalize leaving our heavy pieces hanging after the move; scale by lack of defenders
    if (mi->opp_threat_our_q > 0.0) {
        double def_scale_q = (mi->our_q_def > 0.0) ? 0.5 : 1.0;
        // If our move is a defensive interposition with favorable recapture, further soften queen-under-attack penalty
        if (mi->cap_cp <= 0.0 && mi->piece_cp >= 500.0 && mi->opp_min_att_cp >= 850.0 && mi->us_min_att_cp > 0.0 && mi->us_min_att_cp <= 350.0) {
            def_scale_q *= 0.6;
        }
        // Mutual queen attack but we create extra threats (like Qd6 hitting their rook)
        if (mi->piece_cp >= 850.0 && mi->threat_q > 0.0 && mi->threat_r > 0.0) {
            def_scale_q *= 0.2; // much softer; our queen is active, not hanging
            s += 60.0; // encourage multipurpose standoff
        }
        s -= def_scale_q * 260.0;
    }
    if (mi->opp_threat_our_r > 0.0) {
        double def_scale_r = (mi->our_r_def > 0.0) ? 0.6 : 1.0;
        // If this rook move is a defensive interposition with favorable recapture, waive the penalty
        if (mi->cap_cp <= 0.0 && mi->piece_cp >= 500.0 && mi->opp_min_att_cp >= 850.0 && mi->us_min_att_cp > 0.0 && mi->us_min_att_cp <= 350.0) {
            def_scale_r = 0.0;
        }
        // If we just made a favorable minor-vs-heavy capture with good SEE, don't over-penalize residual rook exposure
        if (mi->cap_cp >= 500.0 && mi->piece_cp <= 350.0 && mi->see_cp >= 200.0) {
            def_scale_r *= 0.1;
        }
        s -= def_scale_r * (700.0 * mi->opp_threat_our_r);
    }
    // Penalize queen sidesteps that leave our rooks under fire and don't gain material
    if (mi->piece_cp >= 850.0 && mi->cap_cp <= 0.0 && mi->opp_threat_our_r > 0.0 && mi->mat_cp <= 0.0) {
        // penalize only truly passive queen sidesteps that don't create new pressure
        if (mi->threat_q <= 0.0 && mi->threat_r <= 0.0 && mi->atk_opp_king <= 0.0 && mi->prox_king <= 0.0) {
            s -= 220.0;
        }
    }
    // Small reward for neutralizing threats on our rooks entirely
    if (mi->opp_threat_our_r <= 0.0 && mi->piece_cp >= 500.0) s += 80.0;
    // Overloaded queen: moving queen while both our queen and a rook are under attack
    if (mi->piece_cp >= 850.0 && mi->cap_cp <= 0.0 && mi->opp_threat_our_q > 0.0 && mi->opp_threat_our_r > 0.0) {
        s -= 500.0;
    }
    s += 20.0 * mi->prox_king;              // piece near king often creates tactics
    // light discouragements/encouragements for piece activity
    if (mi->cap_cp <= 0.0) {
        // discourage quiet king shuffles
        if (mi->piece_cp == 0.0) s -= 50.0;
        // discourage quiet pawn pushes in tactical positions
        if (mi->piece_cp == 100.0) s -= 30.0;
        // discourage quiet queen moves unless they create threats/pressure
        if (mi->piece_cp >= 850.0 && !mi->chk) {
            if (mi->threat_q <= 0.0 && mi->threat_r <= 0.0 && mi->atk_opp_king <= 0.0 && mi->prox_king <= 0.0) {
                s -= 200.0;
            }
        }
    }
    // tiny deterministic jitter from seed
    double jitter = (double)(seed_state % 1000) / 1000000.0; // up to 0.001
    return s + jitter;
}

int main(int argc, char **argv) {
    if (argc <= 1) {
        fprintf(stderr, "usage: %s [--seed N] [--explain] [--analyze UCI] <move1> <move2> ...\n", argv[0]);
        return 1;
    }

    // Extract seed first (if any)
    unsigned int seed = parse_seed_or_default(&argc, &argv);
    srand(seed);

    // Parse flags --explain and --analyze UCI
    int explain = 0;
    const char *analyze_uci = NULL;
    const char *fen = NULL;
    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--explain") == 0) {
            explain = 1;
            for (int j = i; j + 1 < argc; ++j) argv[j] = argv[j + 1];
            argc -= 1;
            i -= 1;
        } else if (strcmp(argv[i], "--fen") == 0 && i + 1 < argc) {
            fen = argv[i + 1];
            for (int j = i; j + 2 < argc; ++j) argv[j] = argv[j + 2];
            argc -= 2;
            i -= 1;
        } else if (strcmp(argv[i], "--analyze") == 0 && i + 1 < argc) {
            analyze_uci = argv[i + 1];
            for (int j = i; j + 2 < argc; ++j) argv[j] = argv[j + 2];
            argc -= 2;
            i -= 1;
        }
    }

    if (argc <= 1) {
        fprintf(stderr, "no moves provided\n");
        return 1;
    }

    // Remaining args are moves
    int n = argc - 1;
    char **moves = &argv[1];

    // Parse move specs
    MoveInfo *info = (MoveInfo *)malloc(sizeof(MoveInfo) * (size_t)n);
    if (!info) {
        fprintf(stderr, "alloc failed\n");
        return 1;
    }
    Board board;
    int have_pos = 0;
    if (fen) {
        if (!parse_fen(&board, fen)) {
            fprintf(stderr, "invalid FEN\n");
            free(info);
            return 1;
        }
        have_pos = 1;
    }
    int base_mat = 0;
    if (have_pos) base_mat = material_cp(&board);

    // Precompute if current side is in check
    int side_in_check = 0;
    if (have_pos) {
        int my_king = find_king(&board, board.white_to_move);
        if (my_king >= 0) side_in_check = sq_attacked_by(&board, my_king, !board.white_to_move);
    }

    for (int i = 0; i < n; ++i) {
        parse_move_spec(moves[i], &info[i]);
        if (have_pos) {
            // derive features from position by applying the move
            Board after = board;
            int cap_cp = 0, prom_gain = 0;
            apply_move(&board, info[i].uci, &after, &cap_cp, &prom_gain);
            int mat_after = material_cp(&after);
            int mat_raw = mat_after - base_mat; // positive if white improved
            int mat_signed = board.white_to_move ? mat_raw : -mat_raw; // positive if mover improved
            // set features
            info[i].in_check = side_in_check;
            info[i].cap_cp = (double)cap_cp;
            info[i].prom_cp = (double)prom_gain;
            info[i].mat_cp = (double)mat_signed;
            // attacker/defender stats on destination square
            int from, to; char pr;
            if (parse_uci_move(info[i].uci, &from, &to, &pr)) {
                char landed = after.squares[to];
                info[i].piece_cp = (double)piece_value_cp(landed);
                int opp_is_white = after.white_to_move; // after our move, it's opponent to move
                int us_is_white = !after.white_to_move;
                int opp_min = min_attacker_value(&after, to, opp_is_white);
                int us_min = min_attacker_value(&after, to, us_is_white);
                info[i].opp_min_att_cp = (double)opp_min;
                info[i].us_min_att_cp = (double)us_min;
                // simple SEE for captures only
                if (cap_cp > 0) {
                    info[i].see_cp = (double)cap_cp - (double)opp_min;
                    if (info[i].see_cp < -1000.0) info[i].see_cp = -1000.0; // clamp extreme
                } else {
                    info[i].see_cp = 0.0;
                }
                // risk: moved into attacked square without friendly cover
                if (cap_cp == 0 && opp_min > 0 && us_min == 0) {
                    double risk = (double)(opp_min);
                    if (risk > info[i].piece_cp) risk = info[i].piece_cp;
                    info[i].risk_cp = risk;
                } else {
                    info[i].risk_cp = 0.0;
                }
            }
            // check to opponent's king after move
            int opp_white = !board.white_to_move; // after our move, opponent is opp_white
            int opp_king_sq = find_king(&after, opp_white);
            int gives_check = 0;
            if (opp_king_sq >= 0) {
                gives_check = sq_attacked_by(&after, opp_king_sq, after.white_to_move); // side to move after = opponent; attack by our side is !after.white_to_move
                // Correct attack color: our side is !after.white_to_move
                gives_check = sq_attacked_by(&after, opp_king_sq, !after.white_to_move);
                // attackers and mobility
                int atk_cnt = count_attackers(&after, opp_king_sq, !after.white_to_move);
                // mobility: count safe adjacent squares for opponent king
                int tf = file_of(opp_king_sq), tr = rank_of(opp_king_sq);
                int mob = 0;
                for (int df = -1; df <= 1; ++df) for (int dr = -1; dr <= 1; ++dr) if (df || dr) {
                    int f = tf + df, r = tr + dr;
                    if (!on_board(f, r)) continue;
                    int idx = idx_from_fr(f, r);
                    char occ = after.squares[idx];
                    if (occ != '.' && (opp_white ? is_white(occ) : is_black(occ))) continue; // own piece there
                    // square safe if not attacked by our side
                    if (!sq_attacked_by(&after, idx, !after.white_to_move)) mob++;
                }
                info[i].atk_opp_king = (double)atk_cnt;
                info[i].opp_king_mob = (double)mob;
                // prox to king
                if (parse_uci_move(info[i].uci, &from, &to, &pr)) {
                    int kf = file_of(opp_king_sq), kr = rank_of(opp_king_sq);
                    int tf2 = file_of(to), tr2 = rank_of(to);
                    int df = tf2 - kf; if (df < 0) df = -df;
                    int dr = tr2 - kr; if (dr < 0) dr = -dr;
                    if (df <= 1 && dr <= 1) info[i].prox_king = 1.0;
                    // characterize the check for blockability when delivered by a slider from the moved square
                    char landed = after.squares[to];
                    int is_slider = (tolower((unsigned char)landed) == 'r') || (tolower((unsigned char)landed) == 'b') || (tolower((unsigned char)landed) == 'q');
                    info[i].checker_is_slider = is_slider ? 1 : 0;
                    info[i].line_check_blockable = 0;
                    if (gives_check && is_slider) {
                        int df0 = file_of(to) - file_of(opp_king_sq);
                        int dr0 = rank_of(to) - rank_of(opp_king_sq);
                        int adf = df0 < 0 ? -df0 : df0;
                        int adr = dr0 < 0 ? -dr0 : dr0;
                        int stepi = 0, stepj = 0;
                        if (adf == adr) { stepi = (df0 > 0) ? 1 : -1; stepj = (dr0 > 0) ? 1 : -1; }
                        else if (df0 == 0 && adr > 0) { stepi = 0; stepj = (dr0 > 0) ? 1 : -1; }
                        else if (dr0 == 0 && adf > 0) { stepi = (df0 > 0) ? 1 : -1; stepj = 0; }
                        int gap = 0;
                        if (stepi != 0 || stepj != 0) {
                            int fcur = file_of(opp_king_sq) + stepi;
                            int rcur = rank_of(opp_king_sq) + stepj;
                            while (on_board(fcur, rcur)) {
                                int idx = idx_from_fr(fcur, rcur);
                                if (idx == to) break;
                                gap++;
                                fcur += stepi; rcur += stepj;
                            }
                        }
                        if (gap >= 1) info[i].line_check_blockable = 1;
                    }
                }
                // crude mate-ish detection
                if (gives_check && mob == 0) {
                    info[i].mate = 1;
                }
            }
            info[i].chk = gives_check ? 1 : 0;
            // threats on enemy heavy pieces after move
            int our_is_white = !after.white_to_move;
            for (int sq = 0; sq < 64; ++sq) {
                char p = after.squares[sq];
                if (p == '.') continue;
                if (opp_white ? is_white(p) : is_black(p)) {
                    if (tolower((unsigned char)p) == 'q') {
                        if (count_attackers(&after, sq, our_is_white) > 0) info[i].threat_q = 1.0;
                    } else if (tolower((unsigned char)p) == 'r') {
                        if (count_attackers(&after, sq, our_is_white) > 0) info[i].threat_r += 0.5; // multiple rooks stack
                    }
                }
            }
            // opponent threats on our heavy pieces after move
            int opp_is_white2 = after.white_to_move; // opponent color
            for (int sq = 0; sq < 64; ++sq) {
                char p2 = after.squares[sq];
                if (p2 == '.') continue;
                if (our_is_white ? is_white(p2) : is_black(p2)) {
                    int tl = (int)tolower((unsigned char)p2);
                    if (tl == 'q') {
                        int opp_atk = count_attackers(&after, sq, opp_is_white2);
                        int our_def = count_attackers(&after, sq, our_is_white);
                        if (opp_atk > 0) info[i].opp_threat_our_q = 1.0;
                        if (our_def > 0) info[i].our_q_def = (double)our_def;
                    } else if (tl == 'r') {
                        int opp_atk = count_attackers(&after, sq, opp_is_white2);
                        int our_def = count_attackers(&after, sq, our_is_white);
                        if (opp_atk > 0) info[i].opp_threat_our_r += 0.5;
                        if (our_def > 0) info[i].our_r_def += 0.5;
                    }
                }
            }
            info[i].mate = 0; // mate detection omitted in this minimal version
            unsigned int local = seed ^ (unsigned int)i * 2654435761u;
            info[i].score = heuristic_score(&info[i], local);
        } else if (info[i].has_anno) {
            unsigned int local = seed ^ (unsigned int)i * 2654435761u;
            info[i].score = heuristic_score(&info[i], local);
        } else {
            info[i].score = (double)rand() / (double)RAND_MAX;
        }
    }

    // Post-pass: if we are in check, upweight moves that give check back (box checks), and
    // slightly downweight immediate queen captures that don't resolve king safety.
    if (have_pos && side_in_check) {
        double best_box = -1e300;
        int best_box_idx = -1;
        for (int i = 0; i < n; ++i) {
            if (info[i].chk) {
                double adj = 150.0;
                if (info[i].opp_king_mob <= 0.0) adj += 400.0;
                info[i].score += adj;
                if (info[i].score > best_box) { best_box = info[i].score; best_box_idx = i; }
            }
            if (info[i].cap_cp > 0.0 && info[i].piece_cp >= 850.0 && info[i].opp_min_att_cp >= 500.0) {
                info[i].score -= 120.0;
            }
        }
    }

    double best_score = -1e300;
    int best_idx = -1;
    for (int i = 0; i < n; ++i) {
        if (info[i].score > best_score) {
            best_score = info[i].score;
            best_idx = i;
        }
    }

    if (best_idx < 0) {
        free(info);
        fprintf(stderr, "no moves\n");
        return 1;
    }

    if (!explain) {
        printf("%s\n", info[best_idx].uci);
        free(info);
        return 0;
    }

    // JSON explanation output
    printf("{\n");
    printf("  \"seed\": %u,\n", seed);
    if (have_pos) {
        printf("  \"fen\": \"%s\",\n", fen);
        printf("  \"side_to_move\": \"%s\",\n", board.white_to_move ? "white" : "black");
        printf("  \"base_material_cp\": %d,\n", base_mat);
    }
    printf("  \"n\": %d,\n", n);
    printf("  \"moves\": [");
    for (int i = 0; i < n; ++i) {
        printf("\"%s\"%s", info[i].uci, (i + 1 < n ? ", " : ""));
    }
    printf("],\n");
    // Detailed per-move features for debugging
    printf("  \"scores\": [");
    for (int i = 0; i < n; ++i) {
        printf("%.6f%s", info[i].score, (i + 1 < n ? ", " : ""));
    }
    printf("],\n");
    printf("  \"features\": [\n");
    for (int i = 0; i < n; ++i) {
        // For transparency, include raw and signed material components via re-derivation
        int from, to; char pr;
        int mat_raw = 0, mat_signed = 0;
        if (have_pos && parse_uci_move(info[i].uci, &from, &to, &pr)) {
            Board tmp; int cc=0, pg=0; apply_move(&board, info[i].uci, &tmp, &cc, &pg);
            int mat_after = material_cp(&tmp);
            mat_raw = mat_after - base_mat;
            mat_signed = board.white_to_move ? mat_raw : -mat_raw;
        }
    printf("    { \"uci\": \"%s\", \"chk\": %d, \"mate\": %d, \"in_check\": %d, \"cap_cp\": %.1f, \"prom_cp\": %.1f, \"mat_cp_signed\": %.1f, \"mat_cp_raw\": %.1f, \"opp_min_att_cp\": %.1f, \"us_min_att_cp\": %.1f, \"piece_cp\": %.1f, \"see_cp\": %.1f, \"risk_cp\": %.1f, \"atk_opp_king\": %.1f, \"opp_king_mob\": %.1f, \"threat_q\": %.1f, \"threat_r\": %.1f, \"opp_threat_our_q\": %.1f, \"opp_threat_our_r\": %.1f, \"our_q_def\": %.1f, \"our_r_def\": %.1f, \"prox_king\": %.1f, \"score\": %.6f }%s\n",
           info[i].uci, info[i].chk, info[i].mate, info[i].in_check, info[i].cap_cp, info[i].prom_cp, info[i].mat_cp, (double)mat_raw,
           info[i].opp_min_att_cp, info[i].us_min_att_cp, info[i].piece_cp, info[i].see_cp, info[i].risk_cp, info[i].atk_opp_king, info[i].opp_king_mob, info[i].threat_q, info[i].threat_r, info[i].opp_threat_our_q, info[i].opp_threat_our_r, info[i].our_q_def, info[i].our_r_def, info[i].prox_king, info[i].score,
               (i + 1 < n ? "," : ""));
    }
    printf("  ],\n");
    printf("  \"chosen_index\": %d,\n", best_idx);
    printf("  \"chosen_move\": \"%s\"", info[best_idx].uci);

    if (analyze_uci) {
        int cand_idx = -1;
        for (int i = 0; i < n; ++i) {
            if (strcmp(info[i].uci, analyze_uci) == 0) { cand_idx = i; break; }
        }
        double cand_score = (cand_idx >= 0 ? info[cand_idx].score : -1.0);
        const char *cmp = "unknown";
        if (cand_idx >= 0) {
            cmp = (cand_score > best_score ? "higher" : (cand_score < best_score ? "lower" : "equal"));
        }
        printf(
            ",\n  \"analyze\": { \"candidate\": \"%s\", \"candidate_index\": %d, \"candidate_score\": %.6f, \"compare_to_chosen\": \"%s\" }\n",
            analyze_uci, cand_idx, cand_score, cmp
        );
    } else {
        printf("\n");
    }
    printf("}\n");
    free(info);
    return 0;
}
