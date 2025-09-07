#include "movegen.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static unsigned long long perft(Position pos, int depth){
    if (depth==0) return 1ULL;
    Move moves[256];
    unsigned long long nodes = 0ULL;
    int n = gen_moves(&pos, moves, 256, 0);
    for (int i=0;i<n;i++){
        Position child = pos;
        Piece cap=EMPTY;
        make_move(&child, &moves[i], &cap);
        nodes += perft(child, depth-1);
    }
    return nodes;
}

static void uci_from_move(const Move *m, char *buf){
    int ff = (m->from & 7), fr = (m->from >> 4);
    int tf = (m->to & 7), tr = (m->to >> 4);
    buf[0] = 'a' + ff; buf[1] = '1' + fr; buf[2] = 'a' + tf; buf[3] = '1' + tr; int i=4;
    if (m->promo){ char pc='q'; switch(m->promo){ case WQ: case BQ: pc='q'; break; case WR: case BR: pc='r'; break; case WB: case BB: pc='b'; break; case WN: case BN: pc='n'; break; default: pc='q'; }
        buf[i++]=pc; }
    buf[i]=0;
}

static void run_case(const char *fen, int depth, unsigned long long expected){
    Position p; if (!parse_fen(&p, fen)){ fprintf(stderr, "Bad FEN: %s\n", fen); return; }
    unsigned long long n = perft(p, depth);
    printf("perft(%d) = %llu  %s\n", depth, n, (expected? (n==expected?"OK":"MISMATCH"):""));
}

int main(int argc, char**argv){
    if (argc>=3){
        const char *fen = argv[1];
        int depth = atoi(argv[2]);
        Position p; if (!parse_fen(&p, fen)){ fprintf(stderr, "Bad FEN input\n"); return 2; }
        if (argc>=4 && strcmp(argv[3], "--divide")==0){
            Move moves[256]; int n = gen_moves(&p, moves, 256, 0);
            unsigned long long total=0ULL;
            for (int i=0;i<n;i++){
                Position c = p; Piece cap=EMPTY; make_move(&c, &moves[i], &cap);
                unsigned long long sub = perft(c, depth-1);
                char u[8]; uci_from_move(&moves[i], u);
                printf("%s: %llu\n", u, sub);
                total += sub;
            }
            printf("Total: %llu\n", total);
        } else if (argc>=4 && strcmp(argv[3], "--divide-pseudo")==0){
            Move moves[256]; int n = gen_moves_pseudo(&p, moves, 256, 0);
            for (int i=0;i<n;i++){ char u[8]; uci_from_move(&moves[i], u); printf("%s\n", u); }
            printf("Total pseudo: %d\n", n);
        } else {
            unsigned long long n = perft(p, depth);
            printf("%llu\n", n);
        }
        return 0;
    }

    // Some well-known positions (depth limited to be fast). Expected nodes are standard perft values.
    // Start position
    run_case("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 1, 20ULL);
    run_case("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 2, 400ULL);
    // Kiwipete
    run_case("r3k2r/p1ppqpb1/bn2pnp1/2PpP3/1p2P3/2N2N2/PBPP1PPP/R2Q1RK1 w kq - 0 1", 1, 48ULL);
    run_case("r3k2r/p1ppqpb1/bn2pnp1/2PpP3/1p2P3/2N2N2/PBPP1PPP/R2Q1RK1 w kq - 0 1", 2, 2039ULL);
    // Simple EP
    run_case("rnbqkbnr/pppppppp/8/8/3Pp3/8/PPP1PPPP/RNBQKBNR b KQkq d3 0 1", 1, 29ULL);
    return 0;
}
