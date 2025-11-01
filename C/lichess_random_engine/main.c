// Minimal chess engine CLI: random fallback + alpha-beta search for provided move list
// Contract expected by PYTHON/lichess_bot/engine.py:
// - Usage without explanation:  random_engine --fen "<FEN>" <uci1> <uci2> ...
//   -> prints the chosen UCI move on stdout
// - With explanation:           random_engine --fen "<FEN>" --explain [--analyze <uci>] <uci1>
// <uci2> ...
//   -> prints a compact JSON object containing chosen_move and a simple analyze block
//
// Notes:
// - We don't validate or parse FEN yet; it's accepted for future use.
// - We choose a uniformly random move among the provided UCIs.
// - For "--analyze" the candidate score is a placeholder (0.0) for now.

#include "movegen.h"
#include "search.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

typedef struct
{
    const char  *fen;
    int          explain;
    const char  *analyze_move;
    const char **moves;
    int          move_count;
} Args;

static void print_usage(const char *prog)
{
    fprintf(stderr, "Usage: %s --fen '<FEN>' [--explain] [--analyze <uci>] <uci_moves...>\n", prog);
}

static int parse_args(int argc, char **argv, Args *out)
{
    memset(out, 0, sizeof(*out));
    out->moves      = NULL;
    out->move_count = 0;

    // Collect options regardless of order; every non-option token is a move.
    const char **moves     = NULL;
    int          moves_cap = 0;
    int          moves_len = 0;

    for (int i = 1; i < argc; ++i)
    {
        const char *a = argv[i];
        if (strcmp(a, "--fen") == 0)
        {
            if (i + 1 >= argc)
            {
                fprintf(stderr, "--fen requires an argument\n");
                free(moves);
                return 0;
            }
            out->fen = argv[++i];
            continue;
        }
        if (strcmp(a, "--explain") == 0)
        {
            out->explain = 1;
            continue;
        }
        if (strcmp(a, "--analyze") == 0)
        {
            if (i + 1 >= argc)
            {
                fprintf(stderr, "--analyze requires a UCI move\n");
                free(moves);
                return 0;
            }
            out->analyze_move = argv[++i];
            continue;
        }
        // Otherwise treat as move
        if (moves_len >= moves_cap)
        {
            int          new_cap = moves_cap == 0 ? 8 : moves_cap * 2;
            const char **tmp =
                (const char **)realloc(moves, (size_t)new_cap * sizeof(const char *));
            if (!tmp)
            {
                fprintf(stderr, "Out of memory\n");
                free(moves);
                return 0;
            }
            moves     = tmp;
            moves_cap = new_cap;
        }
        moves[moves_len++] = a;
    }

    if (!out->fen)
    {
        fprintf(stderr, "Missing --fen argument\n");
        free(moves);
        return 0;
    }

    if (moves_len > 0)
    {
        out->moves      = moves; // keep ownership until program end
        out->move_count = moves_len;
    }
    else
    {
        free(moves);
        out->moves      = NULL;
        out->move_count = 0;
    }
    return 1;
}

static int pick_random_index(int n, const char *fen)
{
    if (n <= 0)
    {
        return -1;
    }
    // Mix in time and a simple FEN hash for a touch of variety/repeatability.
    unsigned long hash = 1469598103934665603ULL; // FNV offset basis
    if (fen)
    {
        const unsigned char *p = (const unsigned char *)fen;
        while (*p)
        {
            hash ^= (unsigned long)(*p++);
            hash *= 1099511628211ULL; // FNV prime
        }
    }
    unsigned long seed = (unsigned long)time(NULL) ^ hash;
    srand((unsigned int)(seed ^ (seed >> 32)));
    int idx = rand() % n;
    return idx;
}

static int find_best_move_from_ucis(const char **ucis, int n_ucis, const char *fen, int depth,
                                    int *out_index)
{
    Position pos;
    if (!parse_fen(&pos, fen))
    {
        return 0;
    }
    // Convert UCI list into legal moves vetted by our generator, but preserve provided order as
    // fallback
    Move legal[256];
    int  map_idx[256];
    int  L = 0;
    for (int i = 0; i < n_ucis; i++)
    {
        Move m;
        if (move_from_uci(&pos, ucis[i], &m))
        {
            legal[L]   = m;
            map_idx[L] = i;
            L++;
        }
    }
    if (L == 0)
    {
        return 0;
    }
    int best_idx   = 0;
    int best_score = -2147483647;
    for (int i = 0; i < L; i++)
    {
        Position child = pos;
        Piece    cap   = EMPTY;
        make_move(&child, &legal[i], &cap);
        PrincipalVariation pv    = {.from = -1, .to = -1};
        int                score = -alphabeta(child, depth - 1, -30000, 30000, &pv);
        if (score > best_score)
        {
            best_score = score;
            best_idx   = i;
        }
    }
    // Map best move back to index in original ucis list using map_idx
    if (out_index)
    {
        *out_index = map_idx[best_idx];
    }
    return 1;
}

int main(int argc, char **argv)
{
    Args args;
    if (!parse_args(argc, argv, &args))
    {
        print_usage(argv[0]);
        return 2;
    }

    if (args.move_count <= 0)
    {
        // No legal moves provided; output nothing to keep contract simple.
        if (args.explain)
        {
            // Still return a valid JSON object for callers expecting it.
            printf("{\"chosen_index\":-1,\"chosen_move\":\"\",\"analyze\":{\"candidate_move\":\"%"
                   "s\",\"candidate_score\":0.0}}\n",
                   args.analyze_move ? args.analyze_move : "");
        }
        return 0;
    }

    // If we have a FEN and move list, run a shallow alpha-beta to choose among provided moves.
    int chosen_idx = -1;
    if (args.fen && args.move_count > 0)
    {
        if (!find_best_move_from_ucis(args.moves, args.move_count, args.fen, 3, &chosen_idx))
        {
            chosen_idx = pick_random_index(args.move_count, args.fen);
        }
    }
    else
    {
        chosen_idx = pick_random_index(args.move_count, args.fen);
    }
    if (chosen_idx < 0 || chosen_idx >= args.move_count)
    {
        (void)fprintf(stderr, "Internal error picking move index\n");
        return 1;
    }
    const char *chosen = args.moves[chosen_idx];

    if (!args.explain)
    {
        printf("%s\n", chosen);
        return 0;
    }

    // Minimal JSON explanation compatible with engine.py's parser
    // Fields consumed by Python wrapper:
    // - chosen_move (string)
    // - chosen_index (int)
    // - analyze.candidate_score (number) [optional but provided]
    // Additionally include analyze.candidate_move for easier debugging.
    const char *cand       = args.analyze_move ? args.analyze_move : "";
    double      cand_score = 0.0; // placeholder; real eval will come later

    printf("{\"chosen_index\":%d,\"chosen_move\":\"%s\",\"analyze\":{\"candidate_move\":\"%s\","
           "\"candidate_score\":%.1f}}\n",
           chosen_idx, chosen, cand, cand_score);
    return 0;
}
