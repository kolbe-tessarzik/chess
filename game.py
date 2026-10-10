import pygame as pg
from board import Board, PieceType, Color, Piece

board = Board()

screen = pg.display.set_mode((800, 800))

running = True
while running:
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False
    board.draw(screen)
    pg.display.flip()
