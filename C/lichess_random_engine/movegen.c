#include "movegen.h"
#include <ctype.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

static inline int on_board(int sq) { return (sq & 0x88) == 0; }
static inline int rank_of(int sq) { return sq >> 4; }
static inline int file_of(int sq) { return sq & 7; }

static inline int color_of(Piece p) { return (p >= BP); }
static inline int is_white(Piece p) { return p >= WP && p <= WK; }
static inline int is_black(Piece p) { return p >= BP && p <= BK; }

static Piece make_piece(char c)
{
    switch (c)
    {
    case 'P':
        return WP;
    case 'N':
        return WN;
    case 'B':
        return WB;
    case 'R':
        return WR;
    case 'Q':
        return WQ;
    case 'K':
        return WK;
    case 'p':
        return BP;
    case 'n':
        return BN;
    case 'b':
        return BB;
    case 'r':
        return BR;
    case 'q':
        return BQ;
    case 'k':
        return BK;
    default:
        return EMPTY;
    }
}

static char piece_to_char(Piece p)
{
    switch (p)
    {
    case WP:
        return 'P';
    case WN:
        return 'N';
    case WB:
        return 'B';
    case WR:
        return 'R';
    case WQ:
        return 'Q';
    case WK:
        return 'K';
    case BP:
        return 'p';
    case BN:
        return 'n';
    case BB:
        return 'b';
    case BR:
        return 'r';
    case BQ:
        return 'q';
    case BK:
        return 'k';
    default:
        return '.';
    }
}

void set_startpos(Position *pos)
{
    memset(pos, 0, sizeof(*pos));
    for (int i = 0; i < BOARD_SIZE; i++)
    {
        pos->board[i] = EMPTY;
    }
    const char *start = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR";
    char        fen[128];
    strcpy(fen, start);
    strcat(fen, " w KQkq - 0 1");
    parse_fen(pos, fen);
}

int parse_fen(Position *pos, const char *fen)
{
    memset(pos, 0, sizeof(*pos));
    for (int i = 0; i < BOARD_SIZE; i++)
    {
        pos->board[i] = EMPTY;
    }
    pos->ep_square       = -1;
    pos->castle          = 0;
    pos->halfmove_clock  = 0;
    pos->fullmove_number = 1;

    // pieces
    int         sq = 0x70; // A8
    const char *p  = fen;
    while (*p && *p != ' ')
    {
        if (*p == '/')
        {
            sq = (sq & 0x70) - 0x10;
            p++;
            continue;
        }
        if (isdigit((unsigned char)*p))
        {
            sq += (*p - '0');
            p++;
            continue;
        }
        Piece pc = make_piece(*p++);
        if (!on_board(sq))
        {
            return 0;
        }
        pos->board[sq++] = pc;
    }
    if (*p != ' ')
    {
        return 0;
    }
    p++;

    // side
    if (*p == 'w')
    {
        pos->side = WHITE;
    }
    else if (*p == 'b')
    {
        pos->side = BLACK;
    }
    else
    {
        return 0;
    }
    p++;
    if (*p != ' ')
    {
        return 0;
    }
    p++;

    // castling
    if (*p == '-')
    {
        p++;
    }
    else
    {
        while (*p && *p != ' ')
        {
            if (*p == 'K')
            {
                pos->castle |= 1 << 0;
            }
            else if (*p == 'Q')
            {
                pos->castle |= 1 << 1;
            }
            else if (*p == 'k')
            {
                pos->castle |= 1 << 2;
            }
            else if (*p == 'q')
            {
                pos->castle |= 1 << 3;
            }
            else
            {
                return 0;
            }
            p++;
        }
    }
    if (*p != ' ')
    {
        return 0;
    }
    p++;

    // en-passant
    if (*p == '-')
    {
        pos->ep_square = -1;
        p++;
    }
    else
    {
        if (p[0] >= 'a' && p[0] <= 'h' && p[1] >= '1' && p[1] <= '8')
        {
            int f          = p[0] - 'a';
            int r          = p[1] - '1';
            pos->ep_square = (r << 4) | f;
            p += 2;
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

    // halfmove clock
    if (isdigit((unsigned char)*p))
    {
        pos->halfmove_clock = strtol(p, (char **)&p, 10);
    }
    if (*p == ' ')
    {
        p++;
    }

    // fullmove number
    if (isdigit((unsigned char)*p))
    {
        pos->fullmove_number = strtol(p, NULL, 10);
    }

    return 1;
}

static int add_move(Move *moves, int count, int max, int from, int to, int cap, int promo, int ep,
                    int castle)
{
    if (count >= max)
    {
        return count;
    }
    Move m;
    m.from         = (uint8_t)from;
    m.to           = (uint8_t)to;
    m.promo        = (uint8_t)promo;
    m.is_capture   = (uint8_t)cap;
    m.is_enpassant = (uint8_t)ep;
    m.is_castle    = (uint8_t)castle;
    moves[count++] = m;
    return count;
}

// Check detection via attack lookup
static int square_attacked_by(const Position *pos, int sq, Color by)
{
    // Knights
    static const int kn[] = {33, 31, 18, 14, -33, -31, -18, -14};
    for (int i = 0; i < 8; i++)
    {
        int s = sq + kn[i];
        if (!on_board(s))
        {
            continue;
        }
        Piece p = pos->board[s];
        if (by == WHITE && p == WN)
        {
            return 1;
        }
        if (by == BLACK && p == BN)
        {
            return 1;
        }
    }
    // Kings
    static const int kd[] = {1, -1, 16, -16, 17, 15, -17, -15};
    for (int i = 0; i < 8; i++)
    {
        int s = sq + kd[i];
        if (!on_board(s))
        {
            continue;
        }
        Piece p = pos->board[s];
        if (by == WHITE && p == WK)
        {
            return 1;
        }
        if (by == BLACK && p == BK)
        {
            return 1;
        }
    }
    // Pawns
    if (by == WHITE)
    {
        int s1 = sq - 15;
        int s2 = sq - 17; // white pawns attack up-left/up-right from their perspective
        if (on_board(s1) && pos->board[s1] == WP)
        {
            return 1;
        }
        if (on_board(s2) && pos->board[s2] == WP)
        {
            return 1;
        }
    }
    else
    {
        int s1 = sq + 15;
        int s2 = sq + 17;
        if (on_board(s1) && pos->board[s1] == BP)
        {
            return 1;
        }
        if (on_board(s2) && pos->board[s2] == BP)
        {
            return 1;
        }
    }
    // Sliders: bishops/queens diagonals
    static const int bd[] = {17, 15, -17, -15};
    for (int d = 0; d < 4; ++d)
    {
        int s = sq + bd[d];
        while (on_board(s))
        {
            Piece p = pos->board[s];
            if (p != EMPTY)
            {
                if (by == WHITE && (p == WB || p == WQ))
                {
                    return 1;
                }
                if (by == BLACK && (p == BB || p == BQ))
                {
                    return 1;
                }
                break;
            }
            s += bd[d];
        }
    }
    // Rooks/queens
    static const int rd[] = {1, -1, 16, -16};
    for (int d = 0; d < 4; ++d)
    {
        int s = sq + rd[d];
        while (on_board(s))
        {
            Piece p = pos->board[s];
            if (p != EMPTY)
            {
                if (by == WHITE && (p == WR || p == WQ))
                {
                    return 1;
                }
                if (by == BLACK && (p == BR || p == BQ))
                {
                    return 1;
                }
                break;
            }
            s += rd[d];
        }
    }
    return 0;
}

int in_check(const Position *pos, Color side)
{
    // find king square
    Piece k  = (side == WHITE) ? WK : BK;
    int   ks = -1;
    for (int sq = 0; sq < BOARD_SIZE; ++sq)
    {
        if (!on_board(sq))
        {
            sq = (sq | 7);
            continue;
        }
        if (pos->board[sq] == k)
        {
            ks = sq;
            break;
        }
    }
    if (ks < 0)
    {
        return 0;
    }
    return square_attacked_by(pos, ks, (side == WHITE) ? BLACK : WHITE);
}

static int gen_moves_internal(const Position *pos, Move *moves, int max_moves, int captures_only)
{
    int   count      = 0;
    Color us         = pos->side;
    int   forward    = (us == WHITE) ? 16 : -16;
    int   start_rank = (us == WHITE) ? 1 : 6;
    int   promo_rank = (us == WHITE) ? 6 : 1; // rank before promotion move (from rank)

    for (int sq = 0; sq < BOARD_SIZE; ++sq)
    {
        if (!on_board(sq))
        {
            sq = (sq | 7);
            continue;
        }
        Piece p = pos->board[sq];
        if (p == EMPTY)
        {
            continue;
        }
        if ((us == WHITE && !is_white(p)) || (us == BLACK && !is_black(p)))
        {
            continue;
        }

        switch (p)
        {
        case WP:
        case BP:
        {
            int dir = (p == WP) ? 16 : -16;
            int r   = rank_of(sq);
            // quiet pushes
            if (!captures_only)
            {
                int to = sq + dir;
                if (on_board(to) && pos->board[to] == EMPTY)
                {
                    if (r == promo_rank)
                    {
                        count = add_move(moves, count, max_moves, sq, to, 0,
                                         (us == WHITE ? WQ : BQ), 0, 0);
                        count = add_move(moves, count, max_moves, sq, to, 0,
                                         (us == WHITE ? WR : BR), 0, 0);
                        count = add_move(moves, count, max_moves, sq, to, 0,
                                         (us == WHITE ? WB : BB), 0, 0);
                        count = add_move(moves, count, max_moves, sq, to, 0,
                                         (us == WHITE ? WN : BN), 0, 0);
                    }
                    else
                    {
                        count = add_move(moves, count, max_moves, sq, to, 0, 0, 0, 0);
                        // double push from start rank
                        if (r == start_rank)
                        {
                            int to2 = to + dir;
                            if (on_board(to2) && pos->board[to2] == EMPTY)
                            {
                                count = add_move(moves, count, max_moves, sq, to2, 0, 0, 0, 0);
                            }
                        }
                    }
                }
            }
            // captures
            int caps[2] = {sq + dir + 1, sq + dir - 1};
            for (int i = 0; i < 2; i++)
            {
                int to = caps[i];
                if (!on_board(to))
                {
                    continue;
                }
                Piece tp = pos->board[to];
                if (tp != EMPTY && color_of(tp) != us)
                {
                    if (r == promo_rank)
                    {
                        count = add_move(moves, count, max_moves, sq, to, 1,
                                         (us == WHITE ? WQ : BQ), 0, 0);
                        count = add_move(moves, count, max_moves, sq, to, 1,
                                         (us == WHITE ? WR : BR), 0, 0);
                        count = add_move(moves, count, max_moves, sq, to, 1,
                                         (us == WHITE ? WB : BB), 0, 0);
                        count = add_move(moves, count, max_moves, sq, to, 1,
                                         (us == WHITE ? WN : BN), 0, 0);
                    }
                    else
                    {
                        count = add_move(moves, count, max_moves, sq, to, 1, 0, 0, 0);
                    }
                }
            }
            // en-passant
            if (pos->ep_square >= 0)
            {
                for (int i = 0; i < 2; i++)
                {
                    int to = caps[i];
                    if (!on_board(to))
                    {
                        continue;
                    }
                    if (to == pos->ep_square)
                    {
                        count = add_move(moves, count, max_moves, sq, to, 1, 0, 1, 0);
                    }
                }
            }
        }
        break;
        case WN:
        case BN:
        {
            static const int d[8] = {33, 31, 18, 14, -33, -31, -18, -14};
            for (int i = 0; i < 8; i++)
            {
                int to = sq + d[i];
                if (!on_board(to))
                {
                    continue;
                }
                Piece tp = pos->board[to];
                if (tp == EMPTY)
                {
                    if (!captures_only)
                    {
                        count = add_move(moves, count, max_moves, sq, to, 0, 0, 0, 0);
                    }
                }
                else if (color_of(tp) != us)
                {
                    count = add_move(moves, count, max_moves, sq, to, 1, 0, 0, 0);
                }
            }
        }
        break;
        case WB:
        case BB:
        case WR:
        case BR:
        case WQ:
        case BQ:
        {
            static const int bd[4] = {17, 15, -17, -15};
            static const int rd[4] = {1, -1, 16, -16};
            const int       *dirs  = NULL;
            int              ndirs = 0;
            if (p == WB || p == BB)
            {
                dirs  = bd;
                ndirs = 4;
            }
            else if (p == WR || p == BR)
            {
                dirs  = rd;
                ndirs = 4;
            }
            else
            { // queen
                // iterate both sets
                for (int i = 0; i < 4; i++)
                {
                    int to = sq + bd[i];
                    while (on_board(to))
                    {
                        Piece tp = pos->board[to];
                        if (tp == EMPTY)
                        {
                            if (!captures_only)
                            {
                                count = add_move(moves, count, max_moves, sq, to, 0, 0, 0, 0);
                            }
                        }
                        else
                        {
                            if (color_of(tp) != us)
                            {
                                count = add_move(moves, count, max_moves, sq, to, 1, 0, 0, 0);
                            }
                            break;
                        }
                        to += bd[i];
                    }
                }
                for (int i = 0; i < 4; i++)
                {
                    int to = sq + rd[i];
                    while (on_board(to))
                    {
                        Piece tp = pos->board[to];
                        if (tp == EMPTY)
                        {
                            if (!captures_only)
                            {
                                count = add_move(moves, count, max_moves, sq, to, 0, 0, 0, 0);
                            }
                        }
                        else
                        {
                            if (color_of(tp) != us)
                            {
                                count = add_move(moves, count, max_moves, sq, to, 1, 0, 0, 0);
                            }
                            break;
                        }
                        to += rd[i];
                    }
                }
                break;
            }
            for (int i = 0; i < ndirs; i++)
            {
                int to = sq + dirs[i];
                while (on_board(to))
                {
                    Piece tp = pos->board[to];
                    if (tp == EMPTY)
                    {
                        if (!captures_only)
                        {
                            count = add_move(moves, count, max_moves, sq, to, 0, 0, 0, 0);
                        }
                    }
                    else
                    {
                        if (color_of(tp) != us)
                        {
                            count = add_move(moves, count, max_moves, sq, to, 1, 0, 0, 0);
                        }
                        break;
                    }
                    to += dirs[i];
                }
            }
        }
        break;
        case WK:
        case BK:
        {
            static const int kd[8] = {1, -1, 16, -16, 17, 15, -17, -15};
            for (int i = 0; i < 8; i++)
            {
                int to = sq + kd[i];
                if (!on_board(to))
                {
                    continue;
                }
                Piece tp = pos->board[to];
                if (tp == EMPTY)
                {
                    if (!captures_only)
                    {
                        count = add_move(moves, count, max_moves, sq, to, 0, 0, 0, 0);
                    }
                }
                else if (color_of(tp) != us)
                {
                    count = add_move(moves, count, max_moves, sq, to, 1, 0, 0, 0);
                }
            }
            // castling (very basic, no check-through validation here; filter later)
            if (!captures_only)
            {
                // Only if not currently in check and path squares are not attacked
                Color them = (us == WHITE) ? BLACK : WHITE;
                if (us == WHITE)
                {
                    if ((pos->castle & (1 << 0)) && pos->board[0x04] == WK &&
                        pos->board[0x05] == EMPTY && pos->board[0x06] == EMPTY)
                    {
                        if (!in_check(pos, WHITE) && !square_attacked_by(pos, 0x05, them) &&
                            !square_attacked_by(pos, 0x06, them))
                        {
                            count = add_move(moves, count, max_moves, sq, 0x06, 0, 0, 0, 1);
                        }
                    }
                    if ((pos->castle & (1 << 1)) && pos->board[0x03] == EMPTY &&
                        pos->board[0x02] == EMPTY && pos->board[0x01] == EMPTY)
                    {
                        if (!in_check(pos, WHITE) && !square_attacked_by(pos, 0x03, them) &&
                            !square_attacked_by(pos, 0x02, them))
                        {
                            count = add_move(moves, count, max_moves, sq, 0x02, 0, 0, 0, 1);
                        }
                    }
                }
                else
                {
                    if ((pos->castle & (1 << 2)) && pos->board[0x74] == BK &&
                        pos->board[0x75] == EMPTY && pos->board[0x76] == EMPTY)
                    {
                        if (!in_check(pos, BLACK) && !square_attacked_by(pos, 0x75, them) &&
                            !square_attacked_by(pos, 0x76, them))
                        {
                            count = add_move(moves, count, max_moves, sq, 0x76, 0, 0, 0, 1);
                        }
                    }
                    if ((pos->castle & (1 << 3)) && pos->board[0x73] == EMPTY &&
                        pos->board[0x72] == EMPTY && pos->board[0x71] == EMPTY)
                    {
                        if (!in_check(pos, BLACK) && !square_attacked_by(pos, 0x73, them) &&
                            !square_attacked_by(pos, 0x72, them))
                        {
                            count = add_move(moves, count, max_moves, sq, 0x72, 0, 0, 0, 1);
                        }
                    }
                }
            }
        }
        break;
        default:
            break;
        }
    }

    return count;
}

int gen_moves_pseudo(const Position *pos, Move *moves, int max_moves, int captures_only)
{
    return gen_moves_internal(pos, moves, max_moves, captures_only);
}

int gen_moves(const Position *pos, Move *moves, int max_moves, int captures_only)
{
    int count = gen_moves_internal(pos, moves, max_moves, captures_only);
    // Filter illegal moves leaving our king in check
    for (int i = 0; i < count;)
    {
        Position tmp = *pos;
        Piece    cap = EMPTY;
        make_move(&tmp, &moves[i], &cap);
        int illegal = in_check(&tmp, pos->side);
        if (illegal)
        {
            moves[i] = moves[count - 1];
            count--;
        }
        else
        {
            i++;
        }
    }
    return count;
}

void make_move(Position *pos, const Move *m, Piece *captured_out)
{
    Piece fromP   = pos->board[m->from];
    Piece toP     = pos->board[m->to];
    *captured_out = toP;

    // en-passant capture
    if (m->is_enpassant)
    {
        int cap_sq         = (pos->side == WHITE) ? (m->to - 16) : (m->to + 16);
        *captured_out      = pos->board[cap_sq];
        pos->board[cap_sq] = EMPTY;
    }

    // move piece
    pos->board[m->to]   = fromP;
    pos->board[m->from] = EMPTY;

    // promotion
    if (m->promo)
    {
        pos->board[m->to] = (Piece)m->promo;
    }

    // castling rook move
    if (m->is_castle)
    {
        if (fromP == WK && m->to == 0x06)
        {
            pos->board[0x05] = WR;
            pos->board[0x07] = EMPTY;
        }
        else if (fromP == WK && m->to == 0x02)
        {
            pos->board[0x03] = WR;
            pos->board[0x00] = EMPTY;
        }
        else if (fromP == BK && m->to == 0x76)
        {
            pos->board[0x75] = BR;
            pos->board[0x77] = EMPTY;
        }
        else if (fromP == BK && m->to == 0x72)
        {
            pos->board[0x73] = BR;
            pos->board[0x70] = EMPTY;
        }
    }

    // update castling rights conservatively
    if (fromP == WK)
    {
        pos->castle &= ~(1 << 0);
        pos->castle &= ~(1 << 1);
    }
    if (fromP == BK)
    {
        pos->castle &= ~(1 << 2);
        pos->castle &= ~(1 << 3);
    }
    if (m->from == 0x00 || m->to == 0x00)
    {
        pos->castle &= ~(1 << 1);
    }
    if (m->from == 0x07 || m->to == 0x07)
    {
        pos->castle &= ~(1 << 0);
    }
    if (m->from == 0x70 || m->to == 0x70)
    {
        pos->castle &= ~(1 << 3);
    }
    if (m->from == 0x77 || m->to == 0x77)
    {
        pos->castle &= ~(1 << 2);
    }

    // en-passant square
    pos->ep_square = -1;
    if (fromP == WP && (m->to - m->from) == 32)
    {
        pos->ep_square = m->from + 16;
    }
    if (fromP == BP && (m->from - m->to) == 32)
    {
        pos->ep_square = m->from - 16;
    }

    // halfmove clock
    if (fromP == WP || fromP == BP || m->is_capture)
    {
        pos->halfmove_clock = 0;
    }
    else
    {
        pos->halfmove_clock++;
    }

    // side to move
    pos->side = (pos->side == WHITE) ? BLACK : WHITE;
    if (pos->side == WHITE)
    {
        pos->fullmove_number++;
    }
}

void unmake_move(Position *pos, const Move *m, Piece captured)
{
    pos->side = (pos->side == WHITE) ? BLACK : WHITE;
    if (pos->side == BLACK)
    {
        pos->fullmove_number--;
    }

    Piece moved = pos->board[m->to];

    // undo castling rook move
    if (m->is_castle)
    {
        if (moved == WK && m->to == 0x06)
        {
            pos->board[0x07] = WR;
            pos->board[0x05] = EMPTY;
        }
        else if (moved == WK && m->to == 0x02)
        {
            pos->board[0x00] = WR;
            pos->board[0x03] = EMPTY;
        }
        else if (moved == BK && m->to == 0x76)
        {
            pos->board[0x77] = BR;
            pos->board[0x75] = EMPTY;
        }
        else if (moved == BK && m->to == 0x72)
        {
            pos->board[0x70] = BR;
            pos->board[0x73] = EMPTY;
        }
    }

    // undo promotion
    if (m->promo)
    {
        moved = (pos->side == WHITE) ? WP : BP;
    }

    pos->board[m->from] = moved;
    if (m->is_enpassant)
    {
        pos->board[m->to]  = EMPTY;
        int cap_sq         = (pos->side == WHITE) ? (m->to - 16) : (m->to + 16);
        pos->board[cap_sq] = captured;
    }
    else
    {
        pos->board[m->to] = captured;
    }

    // Note: We do not restore previous castle/ep/halfmove here (for perft driver we will handle
    // state by copying Position before make_move) For correctness in deeper engine, we’d need a
    // move stack with state; perft here uses position copies for make/unmake. To keep unmake
    // consistent for our usage (make->unmake on a copy), we keep simple.
}

int square_from_algebraic(const char *uci4, int is_from)
{
    // uci like e2e4 or e7e8q
    if (!uci4 || strlen(uci4) < 4)
    {
        return -1;
    }
    int f = uci4[is_from ? 0 : 2] - 'a';
    int r = uci4[is_from ? 1 : 3] - '1';
    if (f < 0 || f > 7 || r < 0 || r > 7)
    {
        return -1;
    }
    return (r << 4) | f;
}

int move_from_uci(const Position *pos, const char *uci, Move *out)
{
    int from = square_from_algebraic(uci, 1);
    int to   = square_from_algebraic(uci, 0);
    if (from < 0 || to < 0)
    {
        return 0;
    }
    char promo = 0;
    if (strlen(uci) >= 5)
    {
        promo = uci[4];
    }
    Move moves[256];
    int  n = gen_moves(pos, moves, 256, 0);
    for (int i = 0; i < n; i++)
    {
        if (moves[i].from == from && moves[i].to == to)
        {
            if (moves[i].promo)
            {
                // map promo char
                Piece pp = 0;
                if (promo == 'q' || promo == 'Q')
                {
                    pp = (pos->side == WHITE) ? WQ : BQ;
                }
                else if (promo == 'r' || promo == 'R')
                {
                    pp = (pos->side == WHITE) ? WR : BR;
                }
                else if (promo == 'b' || promo == 'B')
                {
                    pp = (pos->side == WHITE) ? WB : BB;
                }
                else if (promo == 'n' || promo == 'N')
                {
                    pp = (pos->side == WHITE) ? WN : BN;
                }
                if (pp && pp == moves[i].promo)
                {
                    *out = moves[i];
                    return 1;
                }
            }
            else
            {
                if (!promo)
                {
                    *out = moves[i];
                    return 1;
                }
            }
        }
    }
    return 0;
}
