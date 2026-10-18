import board as chess
from board import Color

POINTS_FOR_PIECE = {
    chess.PieceType.NO_PIECE: 0,
    chess.PieceType.KING: 0,
    chess.PieceType.PAWN: 1,
    chess.PieceType.BISHOP: 3,
    chess.PieceType.KNIGHT: 3,
    chess.PieceType.ROOK: 5,
    chess.PieceType.QUEEN: 9,
}

WEIGHTS = {
    "score_up": 1,
    "threat": 0.5,
}

def score_up(board: list[list[chess.Piece]], color: Color):
    accum = 0
    color_mult = color.value
    for x in range(8):
        for y in range(8):
            piece = board[y][x]
            accum += piece.color.value * color_mult * POINTS_FOR_PIECE[piece.type]
    return accum

def threat(board: list[list[chess.Piece]], king_data, color: Color):
    threatened_pieces = []
    for x in range(8):
        for y in range(8):
            piece = board[y][x]
            if piece.color == Color.NO_COLOR:
                continue
            _, attacks = piece.get_legal_moves(board, (x, y), king_data=king_data)
            for attack in attacks:
                if (attack, (piece.color, piece.type)) not in threatened_pieces:
                    threatened_pieces.append((attack, (piece.color, piece.type)))

    accum = 0
    color_mult = color.value

    for (x, y), (threat_color, threat_type) in threatened_pieces:
        piece = board[y][x]
        if threat_color == piece.color:
            continue
        mult = 2 if piece.color == color else 1
        accum -= piece.color.value * color_mult * mult * POINTS_FOR_PIECE[piece.type] / POINTS_FOR_PIECE[threat_type]

    return accum

class BotPlayer(chess.Player):
    def score(self, board, king_data) -> float:
        points_up = score_up(board, self.color)
        threat_up = threat(board, king_data, self.color)
        return (
            points_up * WEIGHTS["score_up"] +
            threat_up * WEIGHTS["threat"]
        )

    def get_move(self, board: chess.Board) -> tuple[tuple[int, int], tuple[int, int]] | None:
        options: list[tuple[tuple[int, int], tuple[int, int]]] = []
        king_data = None
        for y in range(8):
            for x in range(8):
                piece = board.layout[y][x]
                if piece.color == self.color and piece.type == chess.PieceType.KING:
                    king_data = (piece, (x, y))
                    break
        assert(king_data is not None)

        king_data[0].safe_moves = king_data[0].check_safe_moves(board.layout, king_data[1])

        for y in range(8):
            for x in range(8):
                piece = board.layout[y][x]
                if piece.color != self.color:
                    continue
                legal_moves, legal_attacks = piece.get_legal_moves(board.layout, (x, y), king_data=king_data)
                options += [((x, y), pos) for pos in legal_moves + legal_attacks]

        option_scores: dict[tuple[tuple[int, int], tuple[int, int]], float] = {}

        for old_pos, new_pos in options:
            piece = board.layout[old_pos[1]][old_pos[0]]
            piece.temp_move(board.layout, old_pos, new_pos)
            option_scores[(old_pos, new_pos)] = self.score(board.layout, king_data)
            piece.undo_temp_move(board.layout)

        return max(option_scores, key=option_scores.__getitem__, default=None)
