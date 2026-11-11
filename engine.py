import ctypes
from enum import Enum

lib = ctypes.CDLL('./engine.dylib')

class Color(Enum):
    WHITE = 0
    BLACK = 1

class PieceType(Enum):
    PAWN   = 0
    KING   = 1
    QUEEN  = 2
    BISHOP = 3
    KNIGHT = 4
    ROOK   = 5

class ColoredPiece(Enum):
    WHITE_PAWN   = 0
    WHITE_KING   = 1
    WHITE_QUEEN  = 2
    WHITE_BISHOP = 3
    WHITE_KNIGHT = 4
    WHITE_ROOK   = 5

    BLACK_PAWN   = 6
    BLACK_KING   = 7
    BLACK_QUEEN  = 8
    BLACK_BISHOP = 9
    BLACK_KNIGHT = 10
    BLACK_ROOK   = 11

class Coord(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_int8),
        ("y", ctypes.c_int8),
    ]

class Board(ctypes.Structure):
    def copy(self):
        return Board(tuple(self.by_piece), self.white_pieces, self.black_pieces, self.castling_rights)

    _fields_ = [
        ("by_piece", ctypes.c_uint64 * 12),
        ("white_pieces", ctypes.c_uint64),
        ("black_pieces", ctypes.c_uint64),
        ("castling_rights", ctypes.c_uint8),
    ]

class Move(ctypes.Structure):
    _fields_ = [
        ("i", ctypes.c_uint8),
        ("initial", ctypes.c_uint64),
        ("result" , ctypes.c_uint64),
        ("attack_index", ctypes.c_int8),
    ]

# ctypes.byref to pointerify

lib.check_move.argtypes = [ctypes.POINTER(Board), ctypes.POINTER(Move)]
lib.make_move.argtypes = [ctypes.POINTER(Board), ctypes.POINTER(Move)]

def pos_to_mask(pos: tuple[int, int]):
    return 1 << ((7-pos[1])*8 + (7-pos[0]))

def check_move(board: Board, move: Move):
    return lib.check_move(ctypes.byref(board), ctypes.byref(move))

def make_move(board: Board, move: Move):
    return lib.make_move(ctypes.byref(board), ctypes.byref(move))

# Bit indices follow engine.c: bit 0 is h1 and bit 63 is a8.
INITIAL_SETUP = Board(
    by_piece=(
        0x000000000000FF00,  # White pawns
        0x0000000000000008,  # White king (e1)
        0x0000000000000010,  # White queen (d1)
        0x0000000000000024,  # White bishops (c1, f1)
        0x0000000000000042,  # White knights (b1, g1)
        0x0000000000000081,  # White rooks (a1, h1)
        0x00FF000000000000,  # Black pawns
        0x0800000000000000,  # Black king (e8)
        0x1000000000000000,  # Black queen (d8)
        0x2400000000000000,  # Black bishops (c8, f8)
        0x4200000000000000,  # Black knights (b8, g8)
        0x8100000000000000,  # Black rooks (a8, h8)
    ),
    white_pieces=0x000000000000FFFF,
    black_pieces=0xFFFF000000000000,
    castling_rights=0b1111,
)

def color_of(i):
    return i > 5
