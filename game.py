import pygame as pg
from board import Board, Game, PieceType, Color, Piece, Player

game = Game(players=(Player(Color.WHITE), Player(Color.BLACK)))

screen = pg.display.set_mode((800, 800))

running = True
while running:
    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False
    game.draw(screen)
    pg.display.flip()
