#include "engine.c"

struct ScoredMove
{
    struct Move move;
    int score;
    uint8_t exists;
};

void minimax(struct Board *board, struct ScoredMove* ret_move, enum Color color, int (*score)(struct Board *, enum Color), uint8_t choose_best, uint8_t depth)
{
    uint8_t next_depth = depth - 1;
    struct ScoredMove best_so_far;

    for (uint8_t board_index = color * 6; board_index < ((color * 6) + 6); board_index++)
    {
        uint64_t remaining = board->by_piece[board_index];

        while (remaining)
        {
            enum PieceType type = board_index % 6;
            struct Coord pos;
            pop_lsb_pos(&remaining, &pos);

            uint64_t mask;

            switch (type)
            {
                case ROOK:
                    mask = get_all_rook_moves_obstacles(board, &pos, color);
                    break;

                case BISHOP:
                    mask = get_all_bishop_moves_obstacles(board, &pos, color);
                    break;

                case QUEEN:
                    mask = get_all_rook_moves_obstacles(board, &pos, color) | get_all_bishop_moves_obstacles(board, &pos, color);
                    break;

                case PAWN:
                    mask = get_all_pawn_attacks(&pos, color);
                    break;

                case KNIGHT:
                    mask = get_all_knight_moves(&pos);
                    break;

                case KING:
                    mask = check_king_move_threats(board, &pos, color);
                    break;
            }

            while (mask)
            {
                uint8_t target_bit = pop_lsb(&mask);
                uint64_t result = 1ULL << target_bit;
                int8_t attack_index = -1;
                for (uint8_t attacked_piece_type = (!color) * 6; attacked_piece_type < (((!color) * 6) + 6); attacked_piece_type++)
                {
                    if (result & board->by_piece[attacked_piece_type])
                    {
                        attack_index = attacked_piece_type;
                        break;
                    }
                }
                struct Move move = {board_index, MASK_POS(&pos), result, attack_index};
                if (!check_move(board, &move))
                {
                    continue;
                }
                struct Board test_board = make_temp_move(board, &move);
                int move_score;
                if (next_depth)
                {
                    struct ScoredMove ret;
                    minimax(&test_board, &ret, !color, score, !choose_best, next_depth);
                    move_score = ret.score;
                }
                else
                {
                    move_score = score(&test_board, color);
                }
                if (!best_so_far.exists || (choose_best ? move_score > best_so_far.score : move_score < best_so_far.score))
                {
                    best_so_far.move = move;
                    best_so_far.score = move_score;
                    best_so_far.exists = 1;
                }
            }
        }
    }
    *ret_move = best_so_far;
}

uint16_t score_for_piece[6] = {100, 0, 900, 320, 330, 500};

int score_board_material(struct Board* board, enum Color color)
{
    int ret = 0;
    for (enum PieceType i = 0; i < 12; i++)
    {
        uint8_t num_pieces = __builtin_popcountll(board->by_piece[i]);
        uint16_t total_score = num_pieces * score_for_piece[i % 6];
        ret += (i / 6) == color ? num_pieces : -num_pieces;
    }
    return ret;
}

void get_move(struct Board* board, struct Move* ret, enum Color color)
{
    struct ScoredMove ret_scored;
    minimax(board, &ret_scored, color, score_board_material, 1, 2);
    *ret = ret_scored.move;
}
