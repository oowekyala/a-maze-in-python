import textwrap
from enum import Enum, unique, auto
from typing import NamedTuple, Optional

from bitarray import bitarray


class Cell(NamedTuple):
    x: int
    y: int


    def next(self, side):
        (x, y) = self
        if side is Side.LEFT:
            x = x - 1
        elif side is Side.RIGHT:
            x = x + 1
        elif side is Side.TOP:
            y = y - 1
        elif side is Side.BOT:
            y = y + 1
        return Cell(x, y)


    def wall(self, side: 'Side'):
        return Wall(self.x, self.y, side)


    @staticmethod
    def clip(w: int, h: int, cell: 'Cell') -> Optional['Cell']:
        return cell if cell.x in range(w) and cell.y in range(h) else None


    @staticmethod
    def iterate(w: int, h: int):
        for x in range(0, h):
            for y in range(0, w):
                yield Cell(x, y)

    class CellSet(object):
        """
        Set of cells (grid-like). Partially implemented.
        """


        def __init__(self, height: int, width: int, initial_value: bool = False):
            self.arr = bitarray(height * width)
            self.arr.setall(initial_value)
            self.height = height
            self.width = width


        def __contains__(self, item: 'Cell'):
            p = self.__position_of(item)
            return p in range(0, self.arr.length()) and self.arr[p] is True


        def __iadd__(self, other: 'Cell'):
            self[other] = True
            return self


        def __isub__(self, other: 'Cell'):
            self[other] = False
            return self


        def __setitem__(self, key: 'Cell', value: bool):
            p = self.__position_of(key)
            assert p in range(0, self.arr.length())
            self.arr[p] = value


        def setall(self, value: bool):
            self.arr.setall(value)


        def __ior__(self, other: 'Cell.CellSet'):
            self.arr |= other.arr


        def __position_of(self, cell: 'Cell'):
            return cell.x * self.height + cell.y


        def __repr__(self):
            return '\n'.join(textwrap.wrap(self.arr.to01(), width=self.width))


class Direction(Enum):
    HORIZONTAL = auto()
    VERTICAL = auto()



@unique
class Side(Enum):
    LEFT = auto()
    TOP = auto()
    RIGHT = auto()
    BOT = auto()


    def direction(self):
        is_horiz = self is Side.LEFT or self is Side.RIGHT
        return Direction.HORIZONTAL if is_horiz else Direction.VERTICAL



class Wall(NamedTuple):
    x: int
    y: int
    side: Side


    @property
    def cell(self) -> Cell:
        return Cell(self.x, self.y)


    @property
    def next_cell(self) -> Cell:
        return self.cell.next(self.side)
