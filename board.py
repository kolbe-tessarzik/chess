import pygame as pg
import ctypes
from enum import Enum
from typing import Any, Callable, Self

class Color(Enum):
    NO_COLOR = 0
    WHITE = -1
    BLACK =  1

str_for_color = {
    Color.NO_COLOR: "no_color",
    Color.WHITE: "white",
    Color.BLACK: "black",
}

class PieceType(Enum):
    NO_PIECE = None
    BISHOP   = "bishop"
    ROOK     = "rook"
    KNIGHT   = "knight"
    QUEEN    = "queen"
    KING     = "king"
    PAWN     = "pawn"


# def invert_colors(surface):
#     inv_surface = pg.Surface(surface.get_size())

#     inv_surface.fill((255, 255, 255))

#     inv_surface.blit(surface, (0, 0), special_flags=pg.BLEND_RGB_SUB)

#     inv_surface.set_colorkey((255, 255, 255))

#     return inv_surface

class Piece:
    def __init__(self, piece_type: PieceType, color: Color):
        self.color = color
        self.type = piece_type
        self.has_moved = False
        self.surf = None

    def try_single_move(self, board: list[list[Self]], test_pos: tuple[int, int]):
        if not self.check_dim(test_pos) or board[test_pos[1]][test_pos[0]].color == self.color:
            return None, None
        if board[test_pos[1]][test_pos[0]].color.value == -self.color.value:
            return None, test_pos
        return test_pos, None

    def try_linear_moves(self, board: list[list[Self]], pos: tuple[int, int], diff: tuple[int, int]):
        moves:   list[tuple[int, int]] = []
        attacks: list[tuple[int, int]] = []

        for i in range(1, 8):
            test_pos = (pos[0] + diff[0], pos[1] + diff[1]*i)
            move, attack = self.try_single_move(board, test_pos)
            if move is not None:
                moves.append(move)
            elif attack is not None:
                attacks.append(attack)
                break
            else:
                # edge of the board
                break

        return moves, attacks

    def update_moves_and_attacks(self, pair: tuple[tuple[int, int] | None, tuple[int, int] | None], moves: list[tuple[int, int]], attacks: list[tuple[int, int]]):
        move, attack = pair
        if move is not None:
            moves.append(move)
        elif attack is not None:
            attacks.append(attack)

    def check_dim(self, pos: tuple[int, int]):
        return 8 > pos[0] >= 0 and 8 > pos[1] >= 0

    def get_legal_moves(self, board: list[list[Self]], pos: tuple[int, int]):
        assert(self.check_dim(pos))
        assert(board[pos[1]][pos[0]] is self)
        moves: list[tuple[int, int]] = []
        attacks: list[tuple[int, int]] = []

        if self.type in (PieceType.QUEEN, PieceType.ROOK):
            for diff in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                more_moves, more_attacks = self.try_linear_moves(board, pos, diff)
                moves   += more_moves
                attacks += more_attacks

        if self.type in (PieceType.QUEEN, PieceType.BISHOP):
            for x_step in (-1, 1):
                for y_step in (-1, 1):
                    self.try_linear_moves(board, pos, (x_step, y_step))

        if self.type == PieceType.KNIGHT:
            for base in (3, 2), (2, 3):
                for mod_x in (1, -1):
                    for mod_y in (1, -1):
                        diff = (base[0] * mod_x, base[1] * mod_y)
                        test_pos = (pos[0] + diff[0], pos[1] + diff[1])
                    self.update_moves_and_attacks(self.try_single_move(board, test_pos), moves, attacks)

        if self.type == PieceType.KING:
            for diff_x in (-1, 0, 1):
                for diff_y in (-1, 0, 1):
                    if not diff_x and not diff_y:
                        continue
                    test_pos = (pos[0] + diff_x, pos[1] + diff_y)
                    self.update_moves_and_attacks(self.try_single_move(board, test_pos), moves, attacks)

        if self.type == PieceType.PAWN:
            test_pos = (pos[0], pos[1] + self.color.value)
            move, _ = self.try_single_move(board, test_pos) # can't attack forward
            if move is not None:
                moves.append(move)

            if self.has_moved:
                test_pos = (pos[0], pos[1] + self.color.value)
                move, _ = self.try_single_move(board, test_pos) # can't attack forward
                if move is not None:
                    moves.append(move)

            for diff_x in (1, -1):
                test_pos = (pos[0] + diff_x, pos[1] + self.color.value)
                _, attack = self.try_single_move(board, test_pos) # can't move diagonal
                if attack is not None:
                    attacks.append(attack)

        return moves, attacks

    def draw(self, screen: pg.Surface, center_pos: tuple[float, float]):
        if self.type == PieceType.NO_PIECE:
            return

        if self.surf is None:
            self.surf = pg.image.load(f"{str_for_color[self.color]}_{self.type.value}.png").convert_alpha()
            if self.color == Color.BLACK and self.type == PieceType.PAWN:
                print(self.surf.get_size())


        pos = (center_pos[0] - self.surf.get_width()/2, center_pos[1] - self.surf.get_height()/2)
        screen.blit(self.surf, pos)

NO_PIECE = Piece(PieceType.NO_PIECE, Color.NO_COLOR)

BACK_ROW = [PieceType.ROOK, PieceType.KNIGHT, PieceType.BISHOP, PieceType.QUEEN, PieceType.KING, PieceType.BISHOP, PieceType.KNIGHT, PieceType.ROOK]
FRONT_ROW = [PieceType.PAWN] * 8

class Board:
    def __init__(self):
        self.layout = [[Piece(PieceType.NO_PIECE, Color.NO_COLOR) for _ in range(8)] for _ in range(8)]
        self.layout[7] = [Piece(t, Color.WHITE) for t in BACK_ROW]
        self.layout[0] = [Piece(t, Color.BLACK) for t in BACK_ROW]

        self.layout[6] = [Piece(t, Color.WHITE) for t in FRONT_ROW]
        self.layout[1] = [Piece(t, Color.BLACK) for t in FRONT_ROW]

        self.taken_pieces = {
            Color.WHITE: [],
            Color.BLACK: [],
        }

    def make_move(self, old_pos, new_pos, color):
        piece = self.layout[old_pos[1]][old_pos[0]]
        if piece.color != color:
            raise(ValueError("Wrong color or no piece"))

        target = self.layout[new_pos[1]][new_pos[0]]
        if target.color == color:
            raise(ValueError("Cannot take own piece"))

        self.layout[old_pos[1]][old_pos[0]] = NO_PIECE
        if piece.color != Color.NO_COLOR:
            self.taken_pieces[-piece.color].append(self.layout[new_pos[1]][new_pos[0]])
        self.layout[new_pos[1]][new_pos[0]] = piece

    def draw_squares(self, screen: pg.Surface):
        w = screen.get_width()
        h = screen.get_height()
        for y in range(8):
            for x in range(8):
                color = (240, 25, 55) if (x + y) % 2 == 0 else (0, 0, 0)
                pg.draw.rect(screen, color, (x * w/8, y * h/8, w/8, h/8))

    def draw(self, screen: pg.Surface):
        w = screen.get_width()
        h = screen.get_height()
        self.draw_squares(screen)
        for y in range(8):
            for x in range(8):
                piece = self.layout[y][x]
                if piece.type != PieceType.NO_PIECE:
                    piece.draw(screen, (x * w/8 + w/16, y * h/8 + h/16))

class Player:
    def __init__(self, color: Color):
        self.color = color

    def get_move(self, board: Board) -> tuple[tuple[int, int], tuple[int, int]] | None:
        raise NotImplementedError("This method should be implemented by subclasses")

class Game:
    def __init__(self, players: tuple[Player, Player]):
        self.board = Board()
        self.turn = Color.WHITE
        self.players = {
            Color.WHITE: players[0],
            Color.BLACK: players[1],
        }
        self.board_surf = pg.Surface((800, 800))
        self.redraw = True

    def update(self):
        player = self.players[self.turn]
        move = player.get_move(self.board)
        if move is not None:
            old_pos, new_pos = move
            self.board.make_move(old_pos, new_pos, self.turn)
            self.turn = Color.BLACK if self.turn == Color.WHITE else Color.WHITE
            self.redraw = True

    def draw(self, screen: pg.Surface):
        if self.redraw:
            self.board.draw(self.board_surf)
            self.redraw = False
        screen.blit(self.board_surf, (0, 0))
