import ctypes
from engine import Board, Move
import engine
import board

lib = ctypes.CDLL('./bot.dylib')
lib.get_move.argtypes = [ctypes.POINTER(Board), ctypes.POINTER(Move), ctypes.c_int]

class Bot(board.Player):
    def get_move(self, board: Board):
        move = Move()
        lib.get_move(ctypes.byref(board), ctypes.byref(move), int(self.color))
        ret = []
        for masked_pos in (move.initial, move.result):
            lsb = masked_pos & -masked_pos
            bit_index = (lsb - 1).bit_length()
            pos = (7 - (bit_index % 8), 7 - (bit_index // 8))
            ret.append(pos)
        return tuple(ret)
