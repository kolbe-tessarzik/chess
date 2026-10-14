from pathlib import Path
import itertools

import pygame as pg
import ctypes
from enum import Enum
from typing import Any, Callable, Self

ASSET_PATH = Path("assets") / "image"

class Color(Enum):
    NO_COLOR = 0
    WHITE = -1
    BLACK =  1

def not_color(color: Color):
    if color == Color.NO_COLOR:
        raise(ValueError("No color has no opposite"))
    return Color.WHITE if color == Color.BLACK else Color.BLACK

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
        self.safe_moves = []

    def check_safe_moves(self, board: list[list[Self]], pos: tuple[int, int], only_current = False) -> list[tuple[int, int]]:
        """
        Function only to be called on a king to check which moves are safe
        """
        assert(self.type == PieceType.KING)

        self.safe_moves = [(pos[0] + diff[0], pos[1] + diff[1]) for diff in ([(0, 0)] if only_current else itertools.product((-1, 0, 1), (-1, 0, 1)))]

        board[pos[1]][pos[0]] = NO_PIECE # type: ignore

        for move in self.safe_moves:
            if not self.check_dim(move) or board[move[1]][move[0]].type != NO_PIECE:
                self.safe_moves.remove(move)
                continue

            board[move[1]][move[0]] = self

            for piece_type in PieceType:
                if piece_type == PieceType.NO_PIECE:
                    continue
                _, attackers = self.get_legal_moves(board, move, reverse_as=piece_type)
                for attacker in attackers:
                    piece = board[attacker[1]][attacker[0]]
                    if piece.type == piece_type:
                        self.safe_moves.remove(move)
                        break
                else:
                    continue
                break

            board[move[1]][move[0]] = NO_PIECE

        board[pos[1]][pos[0]] = self

        return self.safe_moves

    def try_single_move(self, board: list[list[Self]], test_pos: tuple[int, int]):
        if not self.check_dim(test_pos) or board[test_pos[1]][test_pos[0]].color == self.color:
            return None, None
        if board[test_pos[1]][test_pos[0]].color.value == -self.color.value:
            return None, test_pos
        return test_pos, None

    def try_linear_moves(self, board: list[list[Self]], pos: tuple[int, int], diff: tuple[int, int]):
        moves:   list[tuple[int, int]] = []
        attacks: list[tuple[int, int]] = []

        if diff[0] and diff[1]:
            print("Debug active")
            debug = True
        else:
            debug = False

        for i in range(1, 8):
            test_pos = (pos[0] + diff[0]*i, pos[1] + diff[1]*i)
            if debug:
                print(test_pos)
            move, attack = self.try_single_move(board, test_pos)
            if move is not None:
                moves.append(move)
            elif attack is not None:
                if debug:
                    print(f"Attack at pos: {test_pos}")
                attacks.append(attack)
                break
            else:
                print(f"Failed at {test_pos}")
                # edge of the board
                break

        if debug:
            print(moves, attacks)

        return moves, attacks

    def update_moves_and_attacks(self, pair: tuple[tuple[int, int] | None, tuple[int, int] | None], moves: list[tuple[int, int]], attacks: list[tuple[int, int]]):
        move, attack = pair
        if move is not None:
            moves.append(move)
        elif attack is not None:
            attacks.append(attack)

    def check_dim(self, pos: tuple[int, int]):
        return 8 > pos[0] >= 0 and 8 > pos[1] >= 0

    def get_legal_moves(self, board: list[list[Self]], pos: tuple[int, int], *, king: Self | None = None, reverse_as: PieceType | None = None):
        """
        Returns (legal moves, legal attacks) for this piece at the given position
        """
        assert(self.check_dim(pos))
        assert(board[pos[1]][pos[0]] is self)
        moves: list[tuple[int, int]] = []
        attacks: list[tuple[int, int]] = []

        my_type = reverse_as or self.type
        if reverse_as is not None:
            self.color = not_color(self.color)

        if my_type in (PieceType.QUEEN, PieceType.ROOK):
            for diff in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                more_moves, more_attacks = self.try_linear_moves(board, pos, diff)
                moves   += more_moves
                attacks += more_attacks

        if my_type in (PieceType.QUEEN, PieceType.BISHOP):
            for x_step in (-1, 1):
                for y_step in (-1, 1):
                    more_moves, more_attacks = self.try_linear_moves(board, pos, (x_step, y_step))
                    moves   += more_moves
                    attacks += more_attacks

        if my_type == PieceType.KNIGHT:
            for base in (1, 2), (2, 1):
                for mod_x in (1, -1):
                    for mod_y in (1, -1):
                        diff = (base[0] * mod_x, base[1] * mod_y)
                        test_pos = (pos[0] + diff[0], pos[1] + diff[1])
                        self.update_moves_and_attacks(self.try_single_move(board, test_pos), moves, attacks)

        if self.type == PieceType.KING:
            for good_pos in self.safe_moves:
                if good_pos == (3, 1):
                    print("Oops")
                self.update_moves_and_attacks(self.try_single_move(board, good_pos), moves, attacks)

        if my_type == PieceType.PAWN:
            test_pos = (pos[0], pos[1] + self.color.value)
            move, _ = self.try_single_move(board, test_pos) # can't attack forward
            if move is not None:
                moves.append(move)

            if not self.has_moved:
                test_pos = (pos[0], pos[1] + self.color.value*2)
                move, _ = self.try_single_move(board, test_pos) # can't attack forward
                if move is not None:
                    moves.append(move)

            for diff_x in (1, -1):
                test_pos = (pos[0] + diff_x, pos[1] + self.color.value)
                _, attack = self.try_single_move(board, test_pos) # can't move diagonal
                if attack is not None:
                    attacks.append(attack)

        if reverse_as is not None:
            self.color = not_color(self.color)

        return moves, attacks

    def draw(self, screen: pg.Surface, center_pos: tuple[float, float]):
        if self.type == PieceType.NO_PIECE:
            return

        if self.surf is None:
            self.surf = pg.image.load(ASSET_PATH / f"{str_for_color[self.color]}_{self.type.value}.png").convert_alpha()

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
            self.taken_pieces[not_color(piece.color)].append(self.layout[new_pos[1]][new_pos[0]])
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

    def __repr__(self):
        return f"Player({str_for_color[self.color]})"

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
        king = None
        king_pos = None
        if move is not None:
            for y in range(8):
                for x in range(8):
                    piece = self.board.layout[y][x]
                    if piece.type == PieceType.KING and piece.color == self.turn:
                        king = piece
                        king_pos = (x, y)
            king.check_safe_moves(self.board.layout, king_pos)
            old_pos, new_pos = move
            if not self.board.layout[old_pos[1]][old_pos[0]].check_dim(old_pos) or not self.board.layout[new_pos[1]][new_pos[0]].check_dim(new_pos):
                raise(ValueError("Move out of bounds"))
            target_color = self.board.layout[new_pos[1]][new_pos[0]].color
            if self.board.layout[old_pos[1]][old_pos[0]].color != self.turn:
                print(f"Wrong color: {self.board.layout[old_pos[1]][old_pos[0]].color} vs {self.turn}")
                return
            if new_pos not in self.board.layout[old_pos[1]][old_pos[0]].get_legal_moves(self.board.layout, old_pos)[int(target_color != Color.NO_COLOR)]:
                print(f"Illegal move: {old_pos} to {new_pos}")
                return
            self.board.make_move(old_pos, new_pos, self.turn)
            self.turn = not_color(self.turn)
            self.redraw = True

    def draw(self, screen: pg.Surface):
        if self.redraw:
            self.board.draw(self.board_surf)
            self.redraw = False
        screen.blit(self.board_surf, (0, 0))
