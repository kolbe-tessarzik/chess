#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>

#define MIN(a, b) (((a) < (b)) ? (a) : (b))
#define MAX(a, b) (((a) > (b)) ? (a) : (b))

#define GET_BOOL(num, i) ((num) & (UINT64_C(1) << (i)))
#define GET_BIT(num, i) (GET_BOOL((num), (i)) >> (i))
#define SET_BIT(num, i, val) (((num) & ~(UINT64_C(1) << (i))) | ((uint64_t)(val) << (i)))

enum Color
{
    WHITE,
    BLACK,
};

enum PieceType
{
    PAWN,
    KING,
    QUEEN,
    BISHOP,
    KNIGHT,
    ROOK,
};

enum Piece
{
    WHITE_PAWN,
    WHITE_KING,
    WHITE_QUEEN,
    WHITE_BISHOP,
    WHITE_KNIGHT,
    WHITE_ROOK,

    BLACK_PAWN,
    BLACK_KING,
    BLACK_QUEEN,
    BLACK_BISHOP,
    BLACK_KNIGHT,
    BLACK_ROOK,
};

struct Coord
{
    int8_t x;
    int8_t y;
};

#define CHECK_BOUND(val) (val < 8 && val >= 0)
#define BOARD_CHECK(coord) (CHECK_BOUND((coord)->x) && CHECK_BOUND((coord)->y))

struct Board
{
    uint64_t by_piece[12];

    uint64_t white_pieces;
    uint64_t black_pieces;

    uint8_t castling_rights; // 0 0 0 0 BKS BQS WKS WQS
};

struct Move
{
    uint8_t i;
    uint64_t initial;
    uint64_t result;
    int8_t attack_index;
};

const struct Move wks_castle = {WHITE_KING, 0b00001000, 0b00000010, -1};
const struct Move wqs_castle = {WHITE_KING, 0b00001000, 0b00100000, -1};
const struct Move bks_castle = {BLACK_KING, 0b00001000ULL << 56, 0b00000010ULL << 56, -1};
const struct Move bqs_castle = {BLACK_KING, 0b00001000ULL << 56, 0b00100000ULL << 56, -1};

/* Board bit indices; x increases rightward and y increases downward.
   Square (x, y) uses bit (7 - x) + (7 - y) * 8.

    63 62 61 60 59 58 57 56
    55 54 53 52 51 50 49 48
    47 46 45 44 43 42 41 40
    39 38 37 36 35 34 33 32
    31 30 29 28 27 26 25 24
    23 22 21 20 19 18 17 16
    15 14 13 12 11 10  9  8
     7  6  5  4  3  2  1  0
*/

#define BISHOP_NESW UINT64_C(0x8040201008040201)
#define BISHOP_NWSE UINT64_C(0x0102040810204080)

const uint64_t KNIGHT_ATTACKS_FOR_X[8] = {
    0b0000000000000000000000000100000000100000000000000010000001000000,
    0b0000000000000000000000001010000000010000000000000001000010100000,
    0b0000000000000000000000000101000010001000000000001000100001010000,
    0b0000000000000000000000000010100001000100000000000100010000101000,
    0b0000000000000000000000000001010000100010000000000010001000010100,
    0b0000000000000000000000000000101000010001000000000001000100001010,
    0b0000000000000000000000000000010100001000000000000000100000000101,
    0b0000000000000000000000000000001000000100000000000000010000000010,
};

void redo_board(struct Board* board)
{
    board->white_pieces = board->by_piece[0] | board->by_piece[1] | board->by_piece[2] | board->by_piece[3] | board->by_piece[4] | board->by_piece[5];
    board->black_pieces = board->by_piece[6] | board->by_piece[7] | board->by_piece[8] | board->by_piece[9] | board->by_piece[10] | board->by_piece[11];
}

#define BISHOP_PURE(pos, target) (abs((pos).x - (target).x) == abs((pos).y - (target).y))
#define ROOK_PURE(pos, target) ((pos).x == (target).x || (pos).y == (target).y)

#define KING_PURE(pos, target) (abs((pos).x - (target).x) <= 1 && abs((pos).y - (target).y) <= 1)
#define QUEEN_PURE(pos, target) (ROOK_PURE((pos), (target)) || BISHOP_PURE((pos), (target)))

#define KNIGHT_PURE(pos, target) ({                               \
    int8_t x_diff = abs((pos).x - (target).x);                    \
    int8_t y_diff = abs((pos).y - (target).y);                    \
    (x_diff == 1 && y_diff == 2) || (x_diff == 2 && y_diff == 1); \
})

#define PAWN_ATTACK_PURE(pos, target, color) (abs((pos).x - (target).x) == 1 && ((pos).y - (target).y == ((color) * 2 - 1)))

#define MASK_ROWS_BOTTOM(up_to) ((up_to == 0) ? UINT64_C(0) : UINT64_MAX << (8 - (up_to))*8)
#define MASK_ROWS_TOP(up_to) ((up_to == 7) ? UINT64_C(0) : UINT64_MAX >> ((up_to)+1)*8)

uint64_t mask_rows_right(uint8_t up_to) {
    uint64_t accum = 0;
    for (uint8_t i = 0; i < (7 - (up_to)); i++)
    {
        accum |= 0x0101010101010101 << i;
    }
    return accum;
}

uint64_t mask_rows_left(uint8_t up_to) {
    uint64_t accum = 0;
    for (uint8_t i = 0; i < (up_to); i++)
    {
        accum |= 0x8080808080808080 >> i;
    }
    return accum;
}

#define INDEX_TO_POS(i) (struct Coord){(7 - ((i) % 8)), 7 - ((i) / 8)}
#define MASK_POS(pos)  (UINT64_C(1) << ((7 - (pos)->x) + (7 - (pos)->y) * 8))
#define POS_INDEX(pos) ((7 - (pos)->x) + (7 - (pos)->y) * 8)

#define ROOK_NS_PURE(x) (UINT64_C(0x0101010101010101) << (7 - (x)))
#define ROOK_EW_PURE(y) (UINT64_C(0xFF) << ((7 - (y)) * 8))

uint8_t pop_lsb(uint64_t* num)
{
    uint8_t i = __builtin_ctzll(*num);
    *num &= *num - 1;
    return i;
}

void pop_lsb_pos(uint64_t* num, struct Coord* pos)
{
    uint8_t i = pop_lsb(num);
    *pos = INDEX_TO_POS(i);
}

void make_temp_move_ip(struct Board* board, struct Move* move);
void unmake_move(struct Board* board, struct Move* move);

uint64_t get_all_rook_moves_pure(struct Coord *pos)
{
    uint64_t lines = ROOK_EW_PURE(pos->y) | ROOK_NS_PURE(pos->x);
    uint64_t maskpos = MASK_POS(pos);
    return lines & ~maskpos;
}

uint64_t bishop_nesw_pure(struct Coord *pos)
{
    // how far above the longest ne/sw diag?
    int nesw_offset = pos->x - pos->y;
    return nesw_offset >= 0
                        ? BISHOP_NESW << (nesw_offset * 8)
                        : BISHOP_NESW >> (-nesw_offset * 8);

}

uint64_t bishop_nwse_pure(struct Coord *pos)
{
    // how far above the longest nw/se diag?
    int nwse_offset = pos->x + pos->y - 7;
    return nwse_offset >= 0
                        ? BISHOP_NWSE >> (nwse_offset * 8)
                        : BISHOP_NWSE << (-nwse_offset * 8);

}

uint64_t get_all_bishop_moves_pure(struct Coord *pos)
{
    return (bishop_nesw_pure(pos) | bishop_nwse_pure(pos)) & ~MASK_POS(pos);
}

uint64_t get_all_knight_moves(struct Coord *pos)
{
    uint64_t unshifted_mask = KNIGHT_ATTACKS_FOR_X[pos->x];
    return (pos->y > 5) ? unshifted_mask >> 8*(pos->y-5) : unshifted_mask << 8*(5-pos->y);
}

uint64_t get_all_pawn_attacks(struct Coord *pos, enum Color color)
{
    int8_t dir = -(color * 2 - 1);
    uint8_t bit_pos = POS_INDEX(pos);
    uint8_t row = bit_pos / 8;
    if (color ? !row : row == 7)
    {
        return 0ULL;
    }
    uint64_t left = pos->x > 0 ? (1ULL << (bit_pos + dir * 8 + 1)) : 0;
    uint64_t right = pos->x < 7 ? (1ULL << (bit_pos + dir * 8 - 1)) : 0;
    return left | right;
}

uint64_t get_all_pawn_moves(struct Board* board, struct Coord *pos, enum Color color)
{
    uint8_t bit_pos = (7-pos->y)*8 + (7-pos->x);

    uint8_t start_bit_row = color ? 6 : 1;
    int8_t diff = ((color*-2)+1)*8;

    int8_t one_fwd_bit = bit_pos + diff;
    if (one_fwd_bit < 0 || one_fwd_bit > 63)
    {
        return 0;
    }

    uint64_t board_mask = ~(board->white_pieces | board->black_pieces);

    uint64_t ret = SET_BIT(0, one_fwd_bit, 1) & board_mask;

    if (ret && (uint64_t)(bit_pos / 8) == start_bit_row)
    {
        ret = SET_BIT(ret, bit_pos + diff*2, 1) & board_mask;
    }

    return ret;
}

uint64_t linear_ns(struct Board* board, struct Coord* pos, enum Color color, uint64_t pure)
{
    uint64_t my_pieces = color ? board->black_pieces : board->white_pieces;

    // masked is 1 at every point on the pure line that has a piece
    uint64_t masked = pure & (board->white_pieces | board->black_pieces);

    // mask off the top section and the bottom section
    uint64_t masked_top = masked & MASK_ROWS_TOP(pos->y);
    uint64_t masked_bottom = masked & MASK_ROWS_BOTTOM(pos->y);

    // MASK_ROWS_TOP selects lower rows; MASK_ROWS_BOTTOM selects upper rows.
    // Find the nearest blocker in each direction, defaulting to the board edge.
    uint8_t cut_row_top = masked_top ? __builtin_clzll(masked_top) / 8 : 7;
    uint8_t cut_row_bottom = masked_bottom ? 7 - __builtin_ctzll(masked_bottom) / 8 : 0;

    // Retain rows between the blockers, including their squares for capture filtering.
    uint64_t mask_for_top = ~MASK_ROWS_TOP(cut_row_top);
    uint64_t mask_for_bottom = ~MASK_ROWS_BOTTOM(cut_row_bottom);

    pure &= mask_for_top & mask_for_bottom;

    pure &= ~my_pieces;

    return pure;

}

uint64_t rook_component_ns(struct Board* board, struct Coord* pos, enum Color color)
{
    return linear_ns(board, pos, color, ROOK_NS_PURE(pos->x) & ~MASK_POS(pos));
}

uint64_t rook_component_ew(struct Board* board, struct Coord* pos, enum Color color)
{
    uint64_t my_pieces = color ? board->black_pieces : board->white_pieces;

    uint64_t pure = ROOK_EW_PURE(pos->y) & ~MASK_POS(pos);

    // masked is 1 at every point on the pure line that has a piece
    uint64_t masked = pure & (board->white_pieces | board->black_pieces);

    // mask off the left section and the right section

    uint64_t masked_left  = masked & mask_rows_left(pos->x);
    uint64_t masked_right = masked & mask_rows_right(pos->x);

    uint8_t cut_col_left  = masked_left ?  7 - __builtin_ctzll(masked_left ) % 8 : 0;
    uint8_t cut_col_right = masked_right ? 7 - __builtin_clzll(masked_right) % 8 : 7;

    // Retain columns between the blockers, including their squares for capture filtering.
    uint64_t mask_for_left  = ~mask_rows_left( cut_col_left );
    uint64_t mask_for_right = ~mask_rows_right(cut_col_right);

    pure &= mask_for_left & mask_for_right;

    pure &= ~my_pieces;

    return pure;
}

uint64_t get_all_rook_moves_obstacles(struct Board* board, struct Coord *pos, enum Color color)
{
    return rook_component_ns(board, pos, color) | rook_component_ew(board, pos, color);
}

uint64_t get_all_bishop_moves_obstacles(struct Board* board, struct Coord *pos, enum Color color)
{
    return linear_ns(board, pos, color, bishop_nesw_pure(pos)) | linear_ns(board, pos, color, bishop_nwse_pure(pos));
}

uint8_t square_attacked(struct Board *board, struct Coord *test_pos, enum Color attacker_color)
{
    uint8_t start = attacker_color * 6;
    for (uint8_t storage_index = start; storage_index < start + 6; storage_index++)
    {
        uint64_t remaining = board->by_piece[storage_index];
        enum PieceType type = storage_index % 6;
        switch (type) {
            case ROOK:
                if (remaining & get_all_rook_moves_obstacles(board, test_pos, !attacker_color)) {
                    return 1;
                }
                continue;
            case BISHOP:
                if (remaining & get_all_bishop_moves_obstacles(board, test_pos, !attacker_color)) {
                    return 1;
                }
                continue;
            case QUEEN:
                if (remaining & (get_all_rook_moves_obstacles(board, test_pos, !attacker_color) | get_all_bishop_moves_obstacles(board, test_pos, !attacker_color))) {
                    return 1;
                }
                continue;
            case PAWN:
                if (remaining & get_all_pawn_attacks(test_pos, !attacker_color)) {
                    return 1;
                }
                continue;
            case (KNIGHT):
                if (remaining & get_all_knight_moves(test_pos)) {
                    return 1;
                }
                continue;
            default:
                break;
        }

        while (remaining)
        {
            struct Coord attacker_pos;
            pop_lsb_pos(&remaining, &attacker_pos);
            // must be king, all other pieces handled above
            if (KING_PURE(attacker_pos, *test_pos))
            {
                return 1;
            }

        }
    }
    return 0;
}

// uint64_t get_required_protection(struct Board* board, struct Coord *pos, enum Color color)
// {
//     // gets the squares that must be occupied to avoid king in check
//     uint8_t start = !color * 6;
//     uint64_t accum = 0;
//     for (uint8_t storage_index = start; storage_index < start + 6; storage_index++)
//     {
//         uint64_t remaining = board->by_piece[storage_index];
//         enum PieceType type = storage_index % 6;
//         switch (type) {
//             case ROOK:
//                 remaining &= get_all_rook_moves_obstacles(board, pos, color);
//                 break;
//             case BISHOP:
//                 remaining &= get_all_bishop_moves_obstacles(board, pos, color);
//                 break;
//             case QUEEN:
//                 remaining &= (get_all_rook_moves_obstacles(board, pos, color) | get_all_bishop_moves_obstacles(board, pos, color));
//                 break;
//             case PAWN:
//                 remaining &= get_all_pawn_attacks(pos, color);
//                 break;
//             case (KNIGHT):
//                 remaining &= get_all_knight_moves(pos);
//                 break;
//             case (KING):
//                 // king can never have another king in check
//                 continue;
//             default:
//                 break;
//         }
//         accum |= remaining;
//     }

// }

uint64_t check_king_move_threats(struct Board *board, struct Coord *pos, enum Color color)
{
    uint64_t origin = MASK_POS(pos);
    uint64_t my_pieces = color ? board->black_pieces : board->white_pieces;
    uint8_t king_index = color * 6 + KING;
    uint8_t enemy_start = (!color) * 6;
    uint64_t ret = 0ULL;

    for (int8_t x = pos->x - 1; x <= pos->x + 1; x++)
    {
        for (int8_t y = pos->y - 1; y <= pos->y + 1; y++)
        {
            struct Coord test_pos = {x, y};
            if (!BOARD_CHECK(&test_pos))
            {
                continue;
            }
            uint64_t destination = MASK_POS(&test_pos);
            if (destination == origin || (destination & my_pieces) ||
                (destination & board->by_piece[enemy_start + KING]))
            {
                continue;
            }

            // Keep both board representations consistent while testing the move.
            struct Board candidate = *board;
            for (uint8_t i = enemy_start; i < enemy_start + 6; i++)
            {
                candidate.by_piece[i] &= ~destination;
                redo_board(&candidate);
            }
            candidate.by_piece[king_index] &= ~origin;
            candidate.by_piece[king_index] |= destination;

            redo_board(&candidate);

            if (!square_attacked(&candidate, &test_pos, !color))
            {
                ret |= destination;
            }
        }
    }

    return ret;
}

void make_temp_move_ip(struct Board* board, struct Move* move)
{
    uint8_t enemy_start = (move->i / 6 == WHITE) ? 6 : 0;

    for (uint8_t i = enemy_start; i < enemy_start+6; i++)
    {
        if (board->by_piece[i] & move->result)
        {
            board->by_piece[i] &= ~move->result;
            break;
        }
    }
    board->by_piece[move->i] &= ~move->initial;
    board->by_piece[move->i] |= move->result;
    if (move->i % 6 == KING)
    {
        if ((move->initial == wks_castle.initial || move->initial == bks_castle.initial) && (move->result & (wks_castle.result | wqs_castle.result | bks_castle.result | bqs_castle.result)))
        {
            struct Move rook_move = {((move->i / 6) * 6) + ROOK, 0, 0, -1};

            uint8_t shift = (move->i/6)*56;

            if (move->result >> shift == wks_castle.result)
            {
                // king side
                rook_move.initial = 1ULL << shift;
                rook_move.result  = 0b100ULL << shift;
            }
            else
            {
                // queen side
                rook_move.initial = 0b10000000ULL << shift;
                rook_move.result  = 0b00010000ULL << shift;
            }
            make_temp_move_ip(board, &rook_move);
        }
        board->castling_rights &= ~(0b11 << (move->i / 6)*2);

    }

    if (move->initial & (0b10000000ULL << (move->i/6)*56))
    {
        // queen side rook
        board->castling_rights = SET_BIT(board->castling_rights, (move->i / 6)*2, 0);
    }
    else if (move->initial & (0b00000001ULL << (move->i/6)*56))
    {
        // king side rook
        board->castling_rights = SET_BIT(board->castling_rights, (move->i / 6)*2+1, 0);

    }

    if (move->attack_index >= 0)
    {
        board->by_piece[move->attack_index] &= ~move->result;
    }
    redo_board(board);
}

struct Board make_temp_move(struct Board* board, struct Move* move)
{
    struct Board ret_board = *board;
    make_temp_move_ip(&ret_board, move);
    return ret_board;
}

uint8_t check_move(struct Board* board, struct Move* move)
{
    // must pass in move with non-zero initial and result values
    uint8_t initial_bit = __builtin_ctzll(move->initial);
    uint8_t result_bit  = __builtin_ctzll(move->result);

    enum Color color = move->i / 6;


    uint64_t friendly_pieces = (uint8_t)(color) ? board->black_pieces : board->white_pieces;

    if (move->result & friendly_pieces)
    {
        printf("Would land on friendly piece\n");
        return 0;
    }

    struct Coord initial_pos = {7 - initial_bit % 8, 7 - initial_bit / 8};
    struct Coord result_pos = {7 - result_bit % 8, 7 - result_bit / 8};

    uint8_t index = __builtin_ctzll(board->by_piece[(color)*6 + KING]);
    struct Coord king_pos = INDEX_TO_POS(index);
    uint64_t king_mask = check_king_move_threats(board, &king_pos, (uint8_t)(color));

    uint8_t is_castle = 0;

    if (move->i % 6 != KING)
    {
        struct Board test_board = make_temp_move(board, move);

        if (square_attacked(&test_board, &king_pos, !(color)))
        {
            return 0;
        }
    }
    else
    {
        uint8_t is_qs_castle = (GET_BOOL(board->castling_rights, (color)*2) && move->result & (wqs_castle.result | bqs_castle.result));
        uint8_t is_ks_castle = (GET_BOOL(board->castling_rights, (color)*2+1) && move->result & (wks_castle.result | bks_castle.result));
        uint64_t mask = 0;
        // check squares between

        if (is_qs_castle)
        {
            mask = 0b01110000ULL << (color)*56;
        }
        else if (is_ks_castle)
        {
            mask = 0b00000110ULL << (color)*56;
        }

        if (!(mask & (board->white_pieces | board->black_pieces)) && !square_attacked(board, &INDEX_TO_POS(__builtin_ctzll(move->initial)), !(color)))
        {
            struct Board test_board = make_temp_move(board, move);
            // no obstructions
            while (mask)
            {
                struct Coord pos;
                pop_lsb_pos(&mask, &pos);
                if (square_attacked(&test_board, &pos, !color))
                {
                    return 0;
                }
            }
        }
        else
        {
            return 0;
        }

        is_castle = is_ks_castle || is_qs_castle;
    }

    switch (move->i % 6)
    {
        case ROOK:
            return (ROOK_PURE(initial_pos, result_pos) && (move->result & get_all_rook_moves_obstacles(board, &initial_pos, color)));
        case BISHOP:
            return (BISHOP_PURE(initial_pos, result_pos) && (move->result & get_all_bishop_moves_obstacles(board, &initial_pos, color)));
        case QUEEN:
            return ((ROOK_PURE(initial_pos, result_pos) || BISHOP_PURE(initial_pos, result_pos)) && (move->result & (get_all_rook_moves_obstacles(board, &initial_pos, color) | get_all_bishop_moves_obstacles(board, &initial_pos, color))));
        case KING:
            return (move->result & king_mask) != 0 || is_castle;
        case KNIGHT:
            return KNIGHT_PURE(initial_pos, result_pos);
        case PAWN:
            printf("Pawn!\n");
            {
            uint64_t enemy_pieces = color ? board->white_pieces : board->black_pieces;
            return (((get_all_pawn_attacks(&initial_pos, color) & enemy_pieces) | get_all_pawn_moves(board, &initial_pos, color)) & move->result) != 0;};
        default:
            return 0;
    }
}

void make_move(struct Board* board, struct Move* move)
{
    if (!check_move(board, move))
    {
        printf("Bad move\n");
        return;
    }

    make_temp_move_ip(board, move);
}

void unmake_move(struct Board* board, struct Move* move)
{
    struct Move inverse_move = {move->i, move->result, move->initial, -1};
    make_temp_move_ip(board, &inverse_move);
    if (move->attack_index >= 0)
    {
        board->by_piece[move->attack_index] |= move->result;
    }
    redo_board(board);
}

// struct Move* score_all_moves(struct Board* board, enum Color color, float (*score)(struct Board*))
// {
//     const depth = 1; // stick with depth 1 for now
//     for (uint8_t board_index = color*6; board_index++; board_index < (color*6) + 6)
//     {
//         uint64_t remaining = board->by_piece[board_index];
//         while (remaining)
//         {
//             enum PieceType type = board_index % 6;
//             uint8_t i = (uint8_t)__builtin_ctzll(remaining);
//             struct Coord pos = {7 - i % 8, 7 - i / 8};

//             switch (type)
//             {
//                 case KING:

//             }

//             remaining &= remaining - 1; // Clear the bit we just read
//         }
//     }
// }
