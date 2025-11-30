// Readable micro-Max (https://home.hccnet.nl/h.g.muller/max-src2.html) inspired engine:
// CLI-compatible with engine.py Usage:
//   micro_max_engine [--seed N] [--fen FEN] [--explain] [--analyze UCI] <move1> <move2> ...
// Behavior: ranks provided UCI moves using a simple material/king-safety heuristic derived
// from the FEN position (if given). Prints chosen move by default, or JSON with --explain.

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

typedef struct
{
    char squares[64];   // a1=0 .. h8=63, '.' empty, uppercase white, lowercase black
    int  white_to_move; // 1 white, 0 black
} Board;

static int file_of(int idx) { return idx % 8; }
static int rank_of(int idx) { return idx / 8; }
static int idx_from_fr(int f, int r) { return (r * 8) + f; }
static int on_board(int f, int r) { return f >= 0 && f < 8 && r >= 0 && r < 8; }
static int is_white(char p) { return p >= 'A' && p <= 'Z'; }
static int is_black(char p) { return p >= 'a' && p <= 'z'; }

static int piece_value_cp(char p)
{
    switch (tolower((unsigned char)p))
    {
    case 'p':
        return 100;
    case 'n':
        return 320;
    case 'b':
        return 330;
    case 'r':
        return 500;
    case 'q':
        return 900;
    case 'k':
        return 0;
    default:
        return 0;
    }
}

static int parse_fen(Board *b, const char *fen)
{
    memset(b->squares, '.', sizeof(b->squares));
    b->white_to_move = 1;
    if (!fen || !*fen)
    {
        return 0;
    }
    int         f = 0;
    int         r = 7;
    const char *p = fen;
    while (*p && *p != ' ')
    {
        char c = *p++;
        if (c == '/')
        {
            f = 0;
            r--;
            if (r < 0)
            {
                return 0;
            }
            continue;
        }
        if (c >= '1' && c <= '8')
        {
            f += (c - '0');
            if (f > 8)
            {
                return 0;
            }
            continue;
        }
        if (isalpha((unsigned char)c))
        {
            if (f >= 8 || r < 0)
            {
                return 0;
            }
            b->squares[idx_from_fr(f, r)] = c;
            f++;
        }
        else
        {
            return 0;
        }
    }
    if (*p == ' ')
    {
        p++;
    }
    if (*p == 'w')
    {
        b->white_to_move = 1;
        p++;
    }
    else if (*p == 'b')
    {
        b->white_to_move = 0;
        p++;
    }
    return 1;
}

static int find_king(const Board *b, int white)
{
    char k = white ? 'K' : 'k';
    for (int i = 0; i < 64; ++i)
    {
        if (b->squares[i] == k)
        {
            return i;
        }
    }
    return -1;
}

static int sq_attacked_by(const Board *b, int target_idx, int by_white)
{
    int tf = file_of(target_idx);
    int tr = rank_of(target_idx);
    // Knights
    const int kdf[8] = {1, 2, 2, 1, -1, -2, -2, -1};
    const int kdr[8] = {2, 1, -1, -2, 2, 1, -1, -2};
    for (int i = 0; i < 8; ++i)
    {
        int f = tf + kdf[i];
        int r = tr + kdr[i];
        if (on_board(f, r))
        {
            char p = b->squares[idx_from_fr(f, r)];
            if (by_white ? p == 'N' : p == 'n')
            {
                return 1;
            }
        }
    }
    // King
    for (int df = -1; df <= 1; ++df)
    {
        for (int dr = -1; dr <= 1; ++dr)
        {
            if (df || dr)
            {
                int f = tf + df;
                int r = tr + dr;
                if (on_board(f, r))
                {
                    char p = b->squares[idx_from_fr(f, r)];
                    if (by_white ? p == 'K' : p == 'k')
                    {
                        return 1;
                    }
                }
            }
        }
    }
    // Pawns
    if (by_white)
    {
        int f1 = tf - 1;
        int r1 = tr - 1;
        int f2 = tf + 1;
        int r2 = tr - 1;
        if (on_board(f1, r1) && b->squares[idx_from_fr(f1, r1)] == 'P')
        {
            return 1;
        }
        if (on_board(f2, r2) && b->squares[idx_from_fr(f2, r2)] == 'P')
        {
            return 1;
        }
    }
    else
    {
        int f1 = tf - 1;
        int r1 = tr + 1;
        int f2 = tf + 1;
        int r2 = tr + 1;
        if (on_board(f1, r1) && b->squares[idx_from_fr(f1, r1)] == 'p')
        {
            return 1;
        }
        if (on_board(f2, r2) && b->squares[idx_from_fr(f2, r2)] == 'p')
        {
            return 1;
        }
    }
    // Bishops/queens
    const int dsf[4] = {1, 1, -1, -1};
    const int dsr[4] = {1, -1, 1, -1};
    for (int d = 0; d < 4; ++d)
    {
        int f = tf + dsf[d];
        int r = tr + dsr[d];
        while (on_board(f, r))
        {
            char p = b->squares[idx_from_fr(f, r)];
            if (p != '.')
            {
                if (by_white ? (p == 'B' || p == 'Q') : (p == 'b' || p == 'q'))
                {
                    return 1;
                }
                break;
            }
            f += dsf[d];
            r += dsr[d];
        }
    }
    // Rooks/queens
    const int rsf[4] = {1, -1, 0, 0};
    const int rsr[4] = {0, 0, 1, -1};
    for (int d = 0; d < 4; ++d)
    {
        int f = tf + rsf[d];
        int r = tr + rsr[d];
        while (on_board(f, r))
        {
            char p = b->squares[idx_from_fr(f, r)];
            if (p != '.')
            {
                if (by_white ? (p == 'R' || p == 'Q') : (p == 'r' || p == 'q'))
                {
                    return 1;
                }
                break;
            }
            f += rsf[d];
            r += rsr[d];
        }
    }
    return 0;
}

static int count_attackers(const Board *b, int target_idx, int by_white)
{
    int       tf     = file_of(target_idx);
    int       tr     = rank_of(target_idx);
    int       cnt    = 0;
    const int kdf[8] = {1, 2, 2, 1, -1, -2, -2, -1};
    const int kdr[8] = {2, 1, -1, -2, 2, 1, -1, -2};
    for (int i = 0; i < 8; ++i)
    {
        int f = tf + kdf[i];
        int r = tr + kdr[i];
        if (on_board(f, r))
        {
            char p = b->squares[idx_from_fr(f, r)];
            if (by_white ? p == 'N' : p == 'n')
            {
                cnt++;
            }
        }
    }
    for (int df = -1; df <= 1; ++df)
    {
        for (int dr = -1; dr <= 1; ++dr)
        {
            if (df || dr)
            {
                int f = tf + df;
                int r = tr + dr;
                if (on_board(f, r))
                {
                    char p = b->squares[idx_from_fr(f, r)];
                    if (by_white ? p == 'K' : p == 'k')
                    {
                        cnt++;
                    }
                }
            }
        }
    }
    if (by_white)
    {
        int f1 = tf - 1;
        int r1 = tr - 1;
        int f2 = tf + 1;
        int r2 = tr - 1;
        if (on_board(f1, r1) && b->squares[idx_from_fr(f1, r1)] == 'P')
        {
            cnt++;
        }
        if (on_board(f2, r2) && b->squares[idx_from_fr(f2, r2)] == 'P')
        {
            cnt++;
        }
    }
    else
    {
        int f1 = tf - 1;
        int r1 = tr + 1;
        int f2 = tf + 1;
        int r2 = tr + 1;
        if (on_board(f1, r1) && b->squares[idx_from_fr(f1, r1)] == 'p')
        {
            cnt++;
        }
        if (on_board(f2, r2) && b->squares[idx_from_fr(f2, r2)] == 'p')
        {
            cnt++;
        }
    }
    const int dsf[4] = {1, 1, -1, -1};
    const int dsr[4] = {1, -1, 1, -1};
    for (int d = 0; d < 4; ++d)
    {
        int f = tf + dsf[d];
        int r = tr + dsr[d];
        while (on_board(f, r))
        {
            char p = b->squares[idx_from_fr(f, r)];
            if (p != '.')
            {
                if (by_white ? (p == 'B' || p == 'Q') : (p == 'b' || p == 'q'))
                {
                    cnt++;
                }
                break;
            }
            f += dsf[d];
            r += dsr[d];
        }
    }
    const int rsf[4] = {1, -1, 0, 0};
    const int rsr[4] = {0, 0, 1, -1};
    for (int d = 0; d < 4; ++d)
    {
        int f = tf + rsf[d];
        int r = tr + rsr[d];
        while (on_board(f, r))
        {
            char p = b->squares[idx_from_fr(f, r)];
            if (p != '.')
            {
                if (by_white ? (p == 'R' || p == 'Q') : (p == 'r' || p == 'q'))
                {
                    cnt++;
                }
                break;
            }
            f += rsf[d];
            r += rsr[d];
        }
    }
    return cnt;
}

static int material_cp(const Board *b)
{
    int w  = 0;
    int bl = 0;
    for (int i = 0; i < 64; ++i)
    {
        char p = b->squares[i];
        if (p == '.')
        {
            continue;
        }
        int v = piece_value_cp(p);
        if (is_white(p))
        {
            w += v;
        }
        else
        {
            bl += v;
        }
    }
    return w - bl;
}

static int parse_uci(const char *uci, int *from, int *to, char *prom)
{
    if (!uci || strlen(uci) < 4)
    {
        return 0;
    }
    int f1 = uci[0] - 'a';
    int r1 = uci[1] - '1';
    int f2 = uci[2] - 'a';
    int r2 = uci[3] - '1';
    if (!on_board(f1, r1) || !on_board(f2, r2))
    {
        return 0;
    }
    *from = idx_from_fr(f1, r1);
    *to   = idx_from_fr(f2, r2);
    *prom = (uci[4] ? uci[4] : 0);
    return 1;
}

static void apply_move(const Board *in, const char *uci, Board *out, int *cap_cp, int *prom_gain_cp)
{
    *out          = *in;
    *cap_cp       = 0;
    *prom_gain_cp = 0;
    int  from;
    int  to;
    char prom = 0;
    if (!parse_uci(uci, &from, &to, &prom))
    {
        return;
    }
    char mover    = out->squares[from];
    char captured = out->squares[to];
    if (captured != '.')
    {
        *cap_cp = piece_value_cp(captured);
    }
    out->squares[to]   = mover;
    out->squares[from] = '.';
    if (prom)
    {
        int  is_w        = is_white(mover);
        char p           = (char)tolower((unsigned char)prom);
        char prom_piece  = p == 'q'   ? (is_w ? 'Q' : 'q')
                           : p == 'r' ? (is_w ? 'R' : 'r')
                           : p == 'b' ? (is_w ? 'B' : 'b')
                                      : (is_w ? 'N' : 'n');
        int  gain        = piece_value_cp(prom_piece) - piece_value_cp(is_w ? 'P' : 'p');
        *prom_gain_cp    = gain;
        out->squares[to] = prom_piece;
    }
    out->white_to_move = !in->white_to_move;
}

typedef struct
{
    char   uci[16];
    double cap_cp;
    double prom_cp;
    double mat_cp;
    double atk_opp_king;
    double opp_king_mob;
    double piece_cp;
    double opp_min_att_cp;
    double us_min_att_cp;
    double see_cp;
    double risk_cp;
    int    gives_check;
    double score;
} MoveInfo;

static double score_move(const MoveInfo *m, unsigned int seed)
{
    double s = 0.0;
    if (m->gives_check)
    {
        double add = 200.0 + (40.0 * m->atk_opp_king) - (35.0 * m->opp_king_mob);
        if (m->opp_king_mob <= 0.0)
        {
            add += 800.0;
        }
        s += add;
    }
    s += 1.5 * m->cap_cp;
    if (m->cap_cp > 0.0)
    {
        double exch = m->cap_cp - m->piece_cp;
        s += (m->piece_cp <= 120.0 ? 1.0 : 3.0) * exch;
        if (m->piece_cp >= 850.0)
        {
            s -= 150.0;
        }
    }
    s += 2.0 * m->prom_cp;
    s += 1.2 * m->mat_cp;
    s += 0.2 * m->see_cp;
    s -= 1.0 * m->risk_cp;
    double jitter = (double)(seed % 1000) / 1000000.0;
    return s + jitter;
}

static unsigned int parse_seed(int *pargc, char ***pargv)
{
    unsigned int seed = (unsigned int)time(NULL) ^ (unsigned int)getpid();
    int          argc = *pargc;
    char       **argv = *pargv;
    for (int i = 1; i < argc; ++i)
    {
        if (strcmp(argv[i], "--seed") == 0 && i + 1 < argc)
        {
            seed = (unsigned int)strtoul(argv[i + 1], NULL, 10);
            for (int j = i; j + 2 < argc; ++j)
            {
                argv[j] = argv[j + 2];
            }
            *pargc -= 2;
            return seed;
        }
    }
    return seed;
}

int main(int argc, char **argv)
{
    if (argc <= 1)
    {
        fprintf(stderr, "usage: %s [--seed N] [--fen FEN] [--explain] [--analyze UCI] <moves...>\n",
                argv[0]);
        return 1;
    }
    unsigned int seed = parse_seed(&argc, &argv);
    srand(seed);
    int         explain     = 0;
    const char *analyze_uci = NULL;
    const char *fen         = NULL;
    for (int i = 1; i < argc; ++i)
    {
        if (strcmp(argv[i], "--explain") == 0)
        {
            explain = 1;
            for (int j = i; j + 1 < argc; ++j)
            {
                argv[j] = argv[j + 1];
            }
            argc -= 1;
            i -= 1;
        }
        else if (strcmp(argv[i], "--fen") == 0 && i + 1 < argc)
        {
            fen = argv[i + 1];
            for (int j = i; j + 2 < argc; ++j)
            {
                argv[j] = argv[j + 2];
            }
            argc -= 2;
            i -= 1;
        }
        else if (strcmp(argv[i], "--analyze") == 0 && i + 1 < argc)
        {
            analyze_uci = argv[i + 1];
            for (int j = i; j + 2 < argc; ++j)
            {
                argv[j] = argv[j + 2];
            }
            argc -= 2;
            i -= 1;
        }
    }
    if (argc <= 1)
    {
        fprintf(stderr, "no moves provided\n");
        return 1;
    }
    int    n     = argc - 1;
    char **moves = &argv[1];
    Board  board;
    int    have_pos = 0;
    if (fen)
    {
        if (!parse_fen(&board, fen))
        {
            fprintf(stderr, "invalid FEN\n");
            return 1;
        }
        have_pos = 1;
    }
    int base_mat = 0;
    if (have_pos)
    {
        base_mat = material_cp(&board);
    }
    MoveInfo *arr = (MoveInfo *)calloc((size_t)n, sizeof(MoveInfo));
    if (!arr)
    {
        fprintf(stderr, "alloc failed\n");
        return 1;
    }
    for (int i = 0; i < n; ++i)
    {
        strncpy(arr[i].uci, moves[i], sizeof(arr[i].uci) - 1);
        arr[i].uci[sizeof(arr[i].uci) - 1] = '\0';
        if (!have_pos)
        {
            arr[i].score = (double)rand() / (double)RAND_MAX;
            continue;
        }
        Board after = board;
        int   cap   = 0;
        int   pg    = 0;
        apply_move(&board, arr[i].uci, &after, &cap, &pg);
        int mat_after  = material_cp(&after);
        int mat_raw    = mat_after - base_mat;
        int mat_signed = board.white_to_move ? mat_raw : -mat_raw;
        arr[i].cap_cp  = cap;
        arr[i].prom_cp = pg;
        arr[i].mat_cp  = (double)mat_signed;
        int  from;
        int  to;
        char pr = 0;
        if (parse_uci(arr[i].uci, &from, &to, &pr))
        {
            char landed      = after.squares[to];
            arr[i].piece_cp  = piece_value_cp(landed);
            int opp_is_white = after.white_to_move;
            int us_is_white  = !after.white_to_move;
            int opp_min      = 0;
            int us_min       = 0;
            // Use min of attackers by value (crude)
            // We'll reuse piece values by scanning all pieces; simpler via count_attackers()
            // surrogate Here we approximate with: if square attacked at all, assume min attacker is
            // pawn (100)
            if (sq_attacked_by(&after, to, opp_is_white))
            {
                opp_min = 100;
            }
            if (sq_attacked_by(&after, to, us_is_white))
            {
                us_min = 100;
            }
            arr[i].opp_min_att_cp = opp_min;
            arr[i].us_min_att_cp  = us_min;
            arr[i].see_cp         = (cap > 0) ? ((double)cap - (double)opp_min) : 0.0;
            if (cap == 0 && opp_min > 0 && us_min == 0)
            {
                double risk = (double)opp_min;
                if (risk > arr[i].piece_cp)
                {
                    risk = arr[i].piece_cp;
                }
                arr[i].risk_cp = risk;
            }
        }
        int opp_white = !board.white_to_move;
        int opp_king  = find_king(&after, opp_white);
        int gives     = 0;
        if (opp_king >= 0)
        {
            gives   = sq_attacked_by(&after, opp_king, !after.white_to_move);
            int atk = count_attackers(&after, opp_king, !after.white_to_move);
            int mob = 0;
            int kf  = file_of(opp_king);
            int kr  = rank_of(opp_king);
            for (int df = -1; df <= 1; ++df)
            {
                for (int dr = -1; dr <= 1; ++dr)
                {
                    if (df || dr)
                    {
                        int f = kf + df;
                        int r = kr + dr;
                        if (!on_board(f, r))
                        {
                            continue;
                        }
                        int  idx = idx_from_fr(f, r);
                        char occ = after.squares[idx];
                        if (occ != '.' && (opp_white ? is_white(occ) : is_black(occ)))
                        {
                            continue;
                        }
                        if (!sq_attacked_by(&after, idx, !after.white_to_move))
                        {
                            mob++;
                        }
                    }
                }
            }
            arr[i].atk_opp_king = atk;
            arr[i].opp_king_mob = mob;
        }
        arr[i].gives_check = gives;
        unsigned int local = seed ^ ((unsigned int)i * 2654435761U);
        arr[i].score       = score_move(&arr[i], local);
    }
    double best_score = -1e300;
    int    best_idx   = -1;
    for (int i = 0; i < n; ++i)
    {
        if (arr[i].score > best_score)
        {
            best_score = arr[i].score;
            best_idx   = i;
        }
    }
    if (best_idx < 0)
    {
        free(arr);
        fprintf(stderr, "no moves\n");
        return 1;
    }
    if (!explain)
    {
        printf("%s\n", arr[best_idx].uci);
        free(arr);
        return 0;
    }
    printf("{\n");
    printf("  \"seed\": %u,\n", seed);
    if (have_pos)
    {
        printf("  \"fen\": \"%s\",\n", fen);
        printf("  \"side_to_move\": \"%s\",\n", board.white_to_move ? "white" : "black");
        printf("  \"base_material_cp\": %d,\n", base_mat);
    }
    printf("  \"n\": %d,\n", n);
    printf("  \"moves\": [");
    for (int i = 0; i < n; ++i)
    {
        printf("\"%s\"%s", arr[i].uci, (i + 1 < n ? ", " : ""));
    }
    printf("],\n");
    printf("  \"scores\": [");
    for (int i = 0; i < n; ++i)
    {
        printf("%.6f%s", arr[i].score, (i + 1 < n ? ", " : ""));
    }
    printf("],\n");
    printf("  \"chosen_index\": %d,\n", best_idx);
    printf("  \"chosen_move\": \"%s\"", arr[best_idx].uci);
    if (analyze_uci)
    {
        int cand_idx = -1;
        for (int i = 0; i < n; ++i)
        {
            if (strcmp(arr[i].uci, analyze_uci) == 0)
            {
                cand_idx = i;
                break;
            }
        }
        double      cand_score = (cand_idx >= 0 ? arr[cand_idx].score : -1.0);
        const char *cmp        = "unknown";
        if (cand_idx >= 0)
        {
            cmp = (cand_score > best_score ? "higher"
                                           : (cand_score < best_score ? "lower" : "equal"));
        }
        printf(",\n  \"analyze\": { \"candidate\": \"%s\", \"candidate_index\": %d, "
               "\"candidate_score\": %.6f, \"compare_to_chosen\": \"%s\" }\n",
               analyze_uci, cand_idx, cand_score, cmp);
    }
    else
    {
        printf("\n");
    }
    printf("}\n");
    free(arr);
    return 0;
}
