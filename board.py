from __future__ import annotations
from pathlib import Path
import engine
from engine import Board, Color

import pygame as pg # pyright: ignore[reportMissingImports]
from typing import Any, Callable, Self

ASSET_PATH = Path("assets") / "image"

# def invert_colors(surface):
#     inv_surface = pg.Surface(surface.get_size())

#     inv_surface.fill((255, 255, 255))

#     inv_surface.blit(surface, (0, 0), special_flags=pg.BLEND_RGB_SUB)

#     inv_surface.set_colorkey((255, 255, 255))

#     return inv_surface

class Player:
    def __init__(self, color: Color):
        self.color = color

    def get_move(self, board: Board) -> tuple[tuple[int, int], tuple[int, int]] | None:
        raise NotImplementedError("This method should be implemented by subclasses")

    def __repr__(self):
        return f"Player({"black" if self.color.value else "white"})"

class Game:
    def __init__(self, players: tuple[Player, Player]):
        self.board = engine.INITIAL_SETUP.copy()
        self.turn = int(Color.WHITE.value)
        self.players = {
            Color.WHITE.value: players[0],
            Color.BLACK.value: players[1],
        }
        self.board_surf = pg.Surface((800, 800))
        self.redraw = True
        self.winner = None
        self.surf_for_piece: dict[int, str | pg.Surface] = {
            0 : "white_pawn.png",
            1 : "white_king.png",
            2 : "white_queen.png",
            3 : "white_bishop.png",
            4 : "white_knight.png",
            5 : "white_rook.png",
            6 : "black_pawn.png",
            7 : "black_king.png",
            8 : "black_queen.png",
            9 : "black_bishop.png",
            10: "black_knight.png",
            11: "black_rook.png",
        }

    def update(self):
        player = self.players[self.turn]
        move = player.get_move(self.board)
        if move:
            old_pos, new_pos = move

            old_pos_mask = engine.pos_to_mask(old_pos)
            new_pos_mask = engine.pos_to_mask(new_pos)
            attack_index = -1
            i = None
            # have to get correct piece index
            for piece_index in range(12):
                if (engine.color_of(piece_index) == self.turn) and self.board.by_piece[piece_index] & old_pos_mask:
                    print(f"{piece_index=}")
                    i = piece_index
                    continue
                if (engine.color_of(piece_index) != self.turn) and (self.board.by_piece[piece_index] & new_pos_mask):
                    attack_index = piece_index
            if i is None:
                # bad move; no piece
                print("bad move, no piece")
                return

            c_move = engine.Move(initial=old_pos_mask, result=new_pos_mask, i=i, attack_index=attack_index)
            if engine.check_move(self.board, c_move):
                engine.make_move(self.board, c_move)
                self.turn = int(not self.turn)
                self.redraw = True

    def draw_squares(self, screen: pg.Surface):
        w = screen.get_width()
        h = screen.get_height()
        for y in range(8):
            for x in range(8):
                color = (240, 25, 55) if (x + y) % 2 == 0 else (0, 0, 0)
                pg.draw.rect(screen, color, (x * w/8, y * h/8, w/8, h/8))

    def draw(self, screen: pg.Surface):
        if self.redraw:
            self.draw_squares(self.board_surf)
            for i in range(12):
                if type(self.surf_for_piece[i]) == str:
                    self.surf_for_piece[i] = pg.image.load(ASSET_PATH / self.surf_for_piece[i])
                remaining = self.board.by_piece[i]
                while remaining:
                    lsb = remaining & -remaining
                    bit_index = (lsb - 1).bit_length()
                    pos = (7 - (bit_index % 8), 7 - (bit_index // 8))

                    self.board_surf.blit(self.surf_for_piece[i], (pos[0]*100+50-self.surf_for_piece[i].get_width()//2, pos[1]*100+50-self.surf_for_piece[i].get_height()//2)) # pyright: ignore[reportAttributeAccessIssue]
                    remaining &= remaining - 1
            self.redraw = False
        screen.blit(self.board_surf, (0, 0))
