import pygame as pg
from board import Board, Game, PieceType, Color, Piece, Player

class HumanPlayer(Player):
    def __init__(self, color: Color):
        super().__init__(color)
        self.selected_square: tuple[int, int] | None = None
        self.move: tuple[tuple[int, int], tuple[int, int]] | None = None

    def click(self, pos: tuple[int, int]) -> None:
        """
        Handle a click event at the pixel position. Only call when it is this player's turn.
        """
        square = (pos[0] // 100, pos[1] // 100)
        if self.selected_square == square:
            print(f"Deselected {square}")
            self.selected_square = None
        elif self.move:
            return
        elif self.selected_square is None and not self.move:
            print(f"Selected {square}")
            self.selected_square = square
        elif self.selected_square is not None:
            print(f"Picked move: {self.selected_square} to {square}")
            self.move = (self.selected_square, square)
            self.selected_square = None

    def get_move(self, board: Board) -> tuple[tuple[int, int], tuple[int, int]] | None:
        if self.move:
            move = self.move
            self.move = None
            return move
        return None

game = Game(players=(HumanPlayer(Color.WHITE), HumanPlayer(Color.BLACK)))

screen = pg.display.set_mode((800, 800))

running = True
while running:
    for event in pg.event.get():
        match event.type:
            case pg.QUIT:
                running = False
            case pg.MOUSEBUTTONDOWN:
                print(game.turn)
                print(game.players[game.turn])
                game.players[game.turn].click(event.pos)
            case _:
                pass

    game.update()
    game.draw(screen)
    pg.display.flip()
