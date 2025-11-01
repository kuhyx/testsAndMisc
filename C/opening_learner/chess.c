#include "chess.h"
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const int knight_offsets[8] = {15, 17, -15, -17, 10, -10, 6, -6};
static const int bishop_dirs[4]    = {9, 7, -9, -7};
static const int rook_dirs[4]      = {8, -8, 1, -1};
static const int king_dirs[8]      = {8, -8, 1, -1, 9, 7, -9, -7};

static inline int  file_of(int sq) { return sq % 8; }
static inline int  rank_of(int sq) { return sq / 8; }
static inline bool on_board(int sq) { return sq >= 0 && sq < 64; }
static inline bool same_color(char a, char b)
{
    return (isupper(a) && isupper(b)) || (islower(a) && islower(b));
}
static inline bool is_white(char p) { return isupper((unsigned char)p); }

typedef struct
{
    int  from;
    int  to;
    char promo;
    char captured;
} MoveCandidate;

void chess_init_start(Position *pos)
{
    // a1..h1 (0..7) are white back rank; rank 8 at indexes 56..63 are black back rank
    const char *start = "RNBQKBNRPPPPPPPP................................pppppppprnbqkbnr";
    for (int i = 0; i < 64; i++)
        pos->board[i] = start[i];
    pos->white_to_move = true;
    pos->castle_wk = pos->castle_wq = pos->castle_bk = pos->castle_bq = true;
    pos->ep_square                                                    = -1;
    pos->halfmove_clock                                               = 0;
    pos->fullmove_number                                              = 1;
}

void chess_copy(Position *dst, const Position *src) { *dst = *src; }

static bool is_empty(const Position *p, int sq) { return p->board[sq] == '.'; }

bool chess_square_attacked(const Position *pos, int sq, bool by_white)
{
    // pawns
    int r = rank_of(sq), f = file_of(sq);
    if (by_white)
    {
        int s1 = (r - 1) * 8 + (f - 1);
        if (f > 0 && r > 0 && on_board(s1) && pos->board[s1] == 'P')
            return true;
        int s2 = (r - 1) * 8 + (f + 1);
        if (f < 7 && r > 0 && on_board(s2) && pos->board[s2] == 'P')
            return true;
    }
    else
    {
        int s1 = (r + 1) * 8 + (f - 1);
        if (f > 0 && r < 7 && on_board(s1) && pos->board[s1] == 'p')
            return true;
        int s2 = (r + 1) * 8 + (f + 1);
        if (f < 7 && r < 7 && on_board(s2) && pos->board[s2] == 'p')
            return true;
    }
    // knights
    for (int i = 0; i < 8; i++)
    {
        int t = sq + knight_offsets[i];
        if (!on_board(t))
            continue;
        int df = file_of(t) - f;
        int dr = rank_of(t) - r;
        if (df < -2 || df > 2 || dr < -2 || dr > 2)
            continue; // edge wrap guard
        char pc = pos->board[t];
        if (by_white && pc == 'N')
            return true;
        if (!by_white && pc == 'n')
            return true;
    }
    // bishops/queens
    for (int d = 0; d < 4; d++)
    {
        int off = bishop_dirs[d];
        int t   = sq + off;
        while (on_board(t) && abs(file_of(t) - f) == abs(rank_of(t) - r))
        {
            char pc = pos->board[t];
            if (pc != '.')
            {
                if (by_white && (pc == 'B' || pc == 'Q'))
                    return true;
                if (!by_white && (pc == 'b' || pc == 'q'))
                    return true;
                break;
            }
            t += off;
        }
    }
    // rooks/queens
    for (int d = 0; d < 4; d++)
    {
        int off = rook_dirs[d];
        int t   = sq + off;
        while (on_board(t) && (file_of(t) == f || rank_of(t) == r))
        {
            char pc = pos->board[t];
            if (pc != '.')
            {
                if (by_white && (pc == 'R' || pc == 'Q'))
                    return true;
                if (!by_white && (pc == 'r' || pc == 'q'))
                    return true;
                break;
            }
            t += off;
        }
    }
    // king
    for (int i = 0; i < 8; i++)
    {
        int t = sq + king_dirs[i];
        if (!on_board(t))
            continue;
        if (abs(file_of(t) - f) > 1 || abs(rank_of(t) - r) > 1)
            continue;
        char pc = pos->board[t];
        if (by_white && pc == 'K')
            return true;
        if (!by_white && pc == 'k')
            return true;
    }
    return false;
}

bool chess_is_in_check(const Position *pos, bool white)
{
    int  ks = -1;
    char k  = white ? 'K' : 'k';
    for (int i = 0; i < 64; i++)
        if (pos->board[i] == k)
        {
            ks = i;
            break;
        }
    if (ks == -1)
        return false; // malformed
    return chess_square_attacked(pos, ks, !white);
}

static void add_move_if_legal(const Position *pos, MoveCandidate candidate, Move *out, size_t *n,
                              size_t max)
{
    if (*n >= max)
        return;
    Position tmp;
    chess_copy(&tmp, pos);
    char captured_piece = candidate.captured ? candidate.captured : pos->board[candidate.to];
    Move m              = {0};
    m.from              = candidate.from;
    m.to                = candidate.to;
    m.promo             = candidate.promo;
    m.moved             = pos->board[candidate.from];
    m.captured          = captured_piece;
    int prev_ep         = tmp.ep_square;
    m.prev_ep           = prev_ep;
    m.prev_wk           = tmp.castle_wk;
    m.prev_wq           = tmp.castle_wq;
    m.prev_bk           = tmp.castle_bk;
    m.prev_bq           = tmp.castle_bq;
    m.prev_halfmove     = tmp.halfmove_clock;
    if (!chess_make_move(&tmp, &m))
        return;
    if (chess_is_in_check(&tmp, !tmp.white_to_move))
        return;      // after make, side switched
    out[(*n)++] = m; // store pseudo move with added flags from make_move
}

size_t chess_generate_legal_moves(const Position *pos, Move *out, size_t max)
{
    size_t n     = 0;
    bool   white = pos->white_to_move;
    for (int sq = 0; sq < 64; sq++)
    {
        char p = pos->board[sq];
        if (p == '.')
            continue;
        if (white != is_white(p))
            continue;
        int f = file_of(sq), r = rank_of(sq);
        switch (tolower(p))
        {
        case 'p':
        {
            int dir        = white ? 8 : -8;
            int start_rank = white ? 1 : 6;
            int prom_rank  = white ? 6 : 1;
            int one        = sq + dir;
            if (on_board(one) && is_empty(pos, one))
            {
                if (r == prom_rank)
                {
                    const char *pr = white ? "QRBN" : "qrbn";
                    for (int i = 0; i < 4; i++)
                        add_move_if_legal(pos,
                                          (MoveCandidate){.from = sq, .to = one, .promo = pr[i]},
                                          out, &n, max);
                }
                else
                {
                    add_move_if_legal(pos, (MoveCandidate){.from = sq, .to = one, .promo = 0}, out,
                                      &n, max);
                }
                // two
                int two = sq + 2 * dir;
                if (r == start_rank && is_empty(pos, two))
                    add_move_if_legal(pos, (MoveCandidate){.from = sq, .to = two, .promo = 0}, out,
                                      &n, max);
            }
            // captures
            int caps[2] = {dir + 1, dir - 1};
            for (int i = 0; i < 2; i++)
            {
                int t = sq + caps[i];
                if (!on_board(t))
                    continue;
                if (abs(file_of(t) - f) != 1)
                    continue;
                if (!is_empty(pos, t) && !same_color(pos->board[sq], pos->board[t]))
                {
                    if (r == prom_rank)
                    {
                        const char *pr = white ? "QRBN" : "qrbn";
                        for (int j = 0; j < 4; j++)
                            add_move_if_legal(pos,
                                              (MoveCandidate){.from = sq, .to = t, .promo = pr[j]},
                                              out, &n, max);
                    }
                    else
                        add_move_if_legal(pos, (MoveCandidate){.from = sq, .to = t, .promo = 0},
                                          out, &n, max);
                }
            }
            // en passant
            if (pos->ep_square != -1)
            {
                int ep = pos->ep_square;
                if (abs(file_of(ep) - f) == 1 && (ep == sq + dir + 1 || ep == sq + dir - 1))
                    add_move_if_legal(pos, (MoveCandidate){.from = sq, .to = ep, .promo = 0}, out,
                                      &n, max);
            }
        }
        break;
        case 'n':
        {
            for (int i = 0; i < 8; i++)
            {
                int t = sq + knight_offsets[i];
                if (!on_board(t))
                    continue;
                if (abs(file_of(t) - f) > 2 || abs(rank_of(t) - r) > 2)
                    continue;
                if (!is_empty(pos, t) && same_color(p, pos->board[t]))
                    continue;
                add_move_if_legal(pos, (MoveCandidate){.from = sq, .to = t, .promo = 0}, out, &n,
                                  max);
            }
        }
        break;
        case 'b':
        {
            for (int d = 0; d < 4; d++)
            {
                int off = bishop_dirs[d];
                int t   = sq + off;
                while (on_board(t) && abs(file_of(t) - f) == abs(rank_of(t) - r))
                {
                    if (!is_empty(pos, t))
                    {
                        if (!same_color(p, pos->board[t]))
                            add_move_if_legal(pos, (MoveCandidate){.from = sq, .to = t, .promo = 0},
                                              out, &n, max);
                        break;
                    }
                    add_move_if_legal(pos, (MoveCandidate){.from = sq, .to = t, .promo = 0}, out,
                                      &n, max);
                    t += off;
                }
            }
        }
        break;
        case 'r':
        {
            for (int d = 0; d < 4; d++)
            {
                int off = rook_dirs[d];
                int t   = sq + off;
                while (on_board(t) && (file_of(t) == f || rank_of(t) == r))
                {
                    if (!is_empty(pos, t))
                    {
                        if (!same_color(p, pos->board[t]))
                            add_move_if_legal(pos, (MoveCandidate){.from = sq, .to = t, .promo = 0},
                                              out, &n, max);
                        break;
                    }
                    add_move_if_legal(pos, (MoveCandidate){.from = sq, .to = t, .promo = 0}, out,
                                      &n, max);
                    t += off;
                }
            }
        }
        break;
        case 'q':
        {
            for (int d = 0; d < 4; d++)
            {
                int off = bishop_dirs[d];
                int t   = sq + off;
                while (on_board(t) && abs(file_of(t) - f) == abs(rank_of(t) - r))
                {
                    if (!is_empty(pos, t))
                    {
                        if (!same_color(p, pos->board[t]))
                            add_move_if_legal(pos, (MoveCandidate){.from = sq, .to = t, .promo = 0},
                                              out, &n, max);
                        break;
                    }
                    add_move_if_legal(pos, (MoveCandidate){.from = sq, .to = t, .promo = 0}, out,
                                      &n, max);
                    t += off;
                }
            }
            for (int d = 0; d < 4; d++)
            {
                int off = rook_dirs[d];
                int t   = sq + off;
                while (on_board(t) && (file_of(t) == f || rank_of(t) == r))
                {
                    if (!is_empty(pos, t))
                    {
                        if (!same_color(p, pos->board[t]))
                            add_move_if_legal(pos, (MoveCandidate){.from = sq, .to = t, .promo = 0},
                                              out, &n, max);
                        break;
                    }
                    add_move_if_legal(pos, (MoveCandidate){.from = sq, .to = t, .promo = 0}, out,
                                      &n, max);
                    t += off;
                }
            }
        }
        break;
        case 'k':
        {
            for (int i = 0; i < 8; i++)
            {
                int t = sq + king_dirs[i];
                if (!on_board(t))
                    continue;
                if (abs(file_of(t) - f) > 1 || abs(rank_of(t) - r) > 1)
                    continue;
                if (!is_empty(pos, t) && same_color(p, pos->board[t]))
                    continue;
                add_move_if_legal(pos, (MoveCandidate){.from = sq, .to = t, .promo = 0}, out, &n,
                                  max);
            }
            // castling
            if (white)
            {
                if (pos->castle_wk && pos->board[5] == '.' && pos->board[6] == '.' &&
                    !chess_square_attacked(pos, 4, false) &&
                    !chess_square_attacked(pos, 5, false) && !chess_square_attacked(pos, 6, false))
                    add_move_if_legal(pos, (MoveCandidate){.from = 4, .to = 6, .promo = 0}, out, &n,
                                      max);
                if (pos->castle_wq && pos->board[3] == '.' && pos->board[2] == '.' &&
                    pos->board[1] == '.' && !chess_square_attacked(pos, 4, false) &&
                    !chess_square_attacked(pos, 3, false) && !chess_square_attacked(pos, 2, false))
                    add_move_if_legal(pos, (MoveCandidate){.from = 4, .to = 2, .promo = 0}, out, &n,
                                      max);
            }
            else
            {
                if (pos->castle_bk && pos->board[61] == '.' && pos->board[62] == '.' &&
                    !chess_square_attacked(pos, 60, true) &&
                    !chess_square_attacked(pos, 61, true) && !chess_square_attacked(pos, 62, true))
                    add_move_if_legal(pos, (MoveCandidate){.from = 60, .to = 62, .promo = 0}, out,
                                      &n, max);
                if (pos->castle_bq && pos->board[59] == '.' && pos->board[58] == '.' &&
                    pos->board[57] == '.' && !chess_square_attacked(pos, 60, true) &&
                    !chess_square_attacked(pos, 59, true) && !chess_square_attacked(pos, 58, true))
                    add_move_if_legal(pos, (MoveCandidate){.from = 60, .to = 58, .promo = 0}, out,
                                      &n, max);
            }
        }
        break;
        default:
            break;
        }
    }
    return n;
}

bool chess_make_move(Position *pos, Move *m)
{
    m->is_castle    = false;
    m->is_enpassant = false;
    char p          = pos->board[m->from];
    char tgt        = pos->board[m->to];
    if (p == '.')
        return false;
    // handle special: en passant capture
    if (tolower(p) == 'p' && m->to == pos->ep_square && file_of(m->to) != file_of(m->from) &&
        tgt == '.')
    {
        m->is_enpassant    = true;
        int cap_sq         = pos->white_to_move ? (m->to - 8) : (m->to + 8);
        m->captured        = pos->board[cap_sq];
        pos->board[cap_sq] = '.';
    }

    // move piece
    pos->board[m->to]   = p;
    pos->board[m->from] = '.';

    // promotion
    if (tolower(p) == 'p' && m->promo)
    {
        pos->board[m->to] = m->promo;
    }

    // castling rook move
    if (tolower(p) == 'k')
    {
        int from = m->from, to = m->to;
        if (from == 4 && to == 6)
        {
            pos->board[5] = 'R';
            pos->board[7] = '.';
            m->is_castle  = true;
        }
        else if (from == 4 && to == 2)
        {
            pos->board[3] = 'R';
            pos->board[0] = '.';
            m->is_castle  = true;
        }
        else if (from == 60 && to == 62)
        {
            pos->board[61] = 'r';
            pos->board[63] = '.';
            m->is_castle   = true;
        }
        else if (from == 60 && to == 58)
        {
            pos->board[59] = 'r';
            pos->board[56] = '.';
            m->is_castle   = true;
        }
    }

    // update castling rights
    if (m->from == 0 || m->to == 0)
        pos->castle_wq = false;
    if (m->from == 7 || m->to == 7)
        pos->castle_wk = false;
    if (m->from == 56 || m->to == 56)
        pos->castle_bq = false;
    if (m->from == 63 || m->to == 63)
        pos->castle_bk = false;
    if (tolower(p) == 'k')
    {
        if (is_white(p))
        {
            pos->castle_wk = pos->castle_wq = false;
        }
        else
        {
            pos->castle_bk = pos->castle_bq = false;
        }
    }

    // update ep square
    pos->ep_square = -1;
    if (tolower(p) == 'p')
    {
        int df = rank_of(m->to) - rank_of(m->from);
        if (df == 2 || df == -2)
        {
            pos->ep_square = (m->from + m->to) / 2;
        }
    }

    // halfmove clock
    if (tolower(p) == 'p' || tgt != '.')
        pos->halfmove_clock = 0;
    else
        pos->halfmove_clock++;

    // side to move
    pos->white_to_move = !pos->white_to_move;
    if (pos->white_to_move)
        pos->fullmove_number++;

    return true;
}

void chess_unmake_move(Position *pos, const Move *m)
{
    pos->white_to_move = !pos->white_to_move;
    if (!pos->white_to_move)
        pos->fullmove_number--;
    // restore halfmove/flags
    pos->ep_square      = m->prev_ep;
    pos->castle_wk      = m->prev_wk;
    pos->castle_wq      = m->prev_wq;
    pos->castle_bk      = m->prev_bk;
    pos->castle_bq      = m->prev_bq;
    pos->halfmove_clock = m->prev_halfmove;

    char p = m->moved;
    // undo promotions
    if (tolower(p) == 'p' && m->promo)
    {
        p = is_white(p) ? 'P' : 'p';
    }

    pos->board[m->from] = p;
    pos->board[m->to]   = m->captured ? m->captured : '.';
    if (m->is_enpassant)
    {
        int cap_sq         = pos->white_to_move ? (m->to - 8) : (m->to + 8);
        pos->board[m->to]  = '.';
        pos->board[cap_sq] = m->captured;
    }
    if (m->is_castle)
    {
        if (m->from == 4 && m->to == 6)
        {
            pos->board[7] = 'R';
            pos->board[5] = '.';
        }
        else if (m->from == 4 && m->to == 2)
        {
            pos->board[0] = 'R';
            pos->board[3] = '.';
        }
        else if (m->from == 60 && m->to == 62)
        {
            pos->board[63] = 'r';
            pos->board[61] = '.';
        }
        else if (m->from == 60 && m->to == 58)
        {
            pos->board[56] = 'r';
            pos->board[59] = '.';
        }
    }
}

void sq_to_coord(int sq, int *file, int *rank)
{
    if (file)
        *file = file_of(sq);
    if (rank)
        *rank = rank_of(sq);
}
int coord_to_sq(int file, int rank) { return rank * 8 + file; }

void move_to_uci(const Move *m, char buf[8])
{
    int f1 = file_of(m->from), r1 = rank_of(m->from), f2 = file_of(m->to), r2 = rank_of(m->to);
    buf[0] = (char)('a' + f1);
    buf[1] = (char)('1' + r1);
    buf[2] = (char)('a' + f2);
    buf[3] = (char)('1' + r2);
    int i  = 4;
    if (m->promo)
    {
        buf[i++] = (char)tolower((unsigned char)m->promo);
    }
    buf[i] = '\0';
}

bool parse_uci_move(const char *s, const Position *pos, Move *out)
{
    if (!s || strlen(s) < 4)
        return false;
    int f1 = s[0] - 'a', r1 = s[1] - '1', f2 = s[2] - 'a', r2 = s[3] - '1';
    if (f1 < 0 || f1 > 7 || f2 < 0 || f2 > 7 || r1 < 0 || r1 > 7 || r2 < 0 || r2 > 7)
        return false;
    int  from = r1 * 8 + f1, to = r2 * 8 + f2;
    char promo = s[4] ? s[4] : 0;
    if (promo)
        promo = pos->white_to_move ? toupper((unsigned char)promo) : tolower((unsigned char)promo);
    Move   list[MAX_MOVES];
    size_t n = chess_generate_legal_moves(pos, list, MAX_MOVES);
    for (size_t i = 0; i < n; i++)
    {
        if (list[i].from == from && list[i].to == to)
        {
            *out       = list[i];
            out->promo = promo ? promo : list[i].promo;
            return true;
        }
    }
    return false;
}

bool chess_to_fen(const Position *pos, char *out, size_t outsz)
{
    char buf[256];
    int  idx = 0;
    for (int r = 7; r >= 0; r--)
    {
        int empty = 0;
        for (int f = 0; f < 8; f++)
        {
            char p = pos->board[r * 8 + f];
            if (p == '.')
                empty++;
            else
            {
                if (empty)
                {
                    buf[idx++] = (char)('0' + empty);
                    empty      = 0;
                }
                buf[idx++] = p;
            }
        }
        if (empty)
            buf[idx++] = (char)('0' + empty);
        if (r)
            buf[idx++] = '/';
    }
    buf[idx++] = ' ';
    buf[idx++] = pos->white_to_move ? 'w' : 'b';
    buf[idx++] = ' ';
    int start  = idx;
    if (pos->castle_wk)
        buf[idx++] = 'K';
    if (pos->castle_wq)
        buf[idx++] = 'Q';
    if (pos->castle_bk)
        buf[idx++] = 'k';
    if (pos->castle_bq)
        buf[idx++] = 'q';
    if (idx == start)
        buf[idx++] = '-';
    buf[idx++] = ' ';
    if (pos->ep_square == -1)
    {
        buf[idx++] = '-';
    }
    else
    {
        int f = file_of(pos->ep_square), r = rank_of(pos->ep_square);
        buf[idx++] = (char)('a' + f);
        buf[idx++] = (char)('1' + r);
    }
    idx +=
        snprintf(buf + idx, sizeof(buf) - idx, " %d %d", pos->halfmove_clock, pos->fullmove_number);
    buf[idx] = '\0';
    snprintf(out, outsz, "%s", buf);
    return true;
}
