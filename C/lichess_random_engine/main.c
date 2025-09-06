// Heuristic engine with optional explanation and analysis output
// Usage:
//   random_engine [--seed N] [--explain] [--analyze UCI] <move1> <move2> ...
// Behavior:
//   - If a move is annotated as 'uci;key=value;...' the engine parses features and
//     computes a heuristic score. Recognized keys: chk (0/1), c (capture cp), prom (cp gain),
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
    double cap_cp;         // capture centipawns
    double prom_cp;        // promotion centipawns
    double mat_cp;         // material delta centipawns
    double score;          // computed score
} MoveInfo;

static void parse_move_spec(const char *spec, MoveInfo *mi) {
    // Copy UCI up to ';' or end
    mi->arg_raw = spec;
    mi->uci[0] = '\0';
    mi->has_anno = 0;
    mi->chk = 0;
    mi->mate = 0;
    mi->cap_cp = 0.0;
    mi->prom_cp = 0.0;
    mi->mat_cp = 0.0;
    mi->score = 0.0;

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
    if (mi->chk) s += 50.0;                 // modest bonus for checks
    s += 1.0 * mi->cap_cp;                  // prioritize raw capture value
    s += 1.2 * mi->prom_cp;                 // promotions are very strong
    s += 2.0 * mi->mat_cp;                  // overall material delta dominates
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
    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--explain") == 0) {
            explain = 1;
            for (int j = i; j + 1 < argc; ++j) argv[j] = argv[j + 1];
            argc -= 1;
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
    for (int i = 0; i < n; ++i) {
        parse_move_spec(moves[i], &info[i]);
        if (info[i].has_anno) {
            // compute heuristic score
            unsigned int local = seed ^ (unsigned int)i * 2654435761u;
            info[i].score = heuristic_score(&info[i], local);
        } else {
            // fallback: random score
            info[i].score = (double)rand() / (double)RAND_MAX;
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
    printf("  \"n\": %d,\n", n);
    printf("  \"moves\": [");
    for (int i = 0; i < n; ++i) {
        printf("\"%s\"%s", info[i].uci, (i + 1 < n ? ", " : ""));
    }
    printf("],\n");
    printf("  \"scores\": [");
    for (int i = 0; i < n; ++i) {
        printf("%.6f%s", info[i].score, (i + 1 < n ? ", " : ""));
    }
    printf("],\n");
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
