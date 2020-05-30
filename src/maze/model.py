import textwrap
from enum import Enum, unique, auto
from typing import NamedTuple, Optional, Union, Iterable
from bitarray import bitarray
from bitarray.util import rindex
from copy import copy



@unique
class Side(Enum):
    LEFT = auto()
    TOP = auto()
    RIGHT = auto()
    BOT = auto()



@unique
class Neighbour(Enum):
    LL = (Side.LEFT, Side.LEFT)
    UL = (Side.TOP, Side.LEFT)
    UU = (Side.TOP, Side.TOP)
    UR = (Side.TOP, Side.RIGHT)
    RR = (Side.RIGHT, Side.RIGHT)
    DR = (Side.BOT, Side.RIGHT)
    DD = (Side.BOT, Side.BOT)
    DL = (Side.BOT, Side.LEFT)



class Cell(NamedTuple):
    """
    A cell position in a maze. Mazes are row-major: x is the row, y is the column.
    """
    x: int
    y: int


    def next(self, side: Union[Side, Neighbour], shift: int = 1):
        (x, y) = self

        sides = tuple([side]) if isinstance(side, Side) else side.value

        if Side.LEFT in sides:
            y = y - shift
        if Side.RIGHT in sides:
            y = y + shift
        if Side.TOP in sides:
            x = x - shift
        if Side.BOT in sides:
            x = x + shift
        return Cell(x, y)


    @staticmethod
    def iterate(w: int, h: int, step=1):
        for x in range(0, h, step):
            for y in range(0, w, step):
                yield Cell(x, y)

    class CellSet(object):
        """
        Set of cells (grid-like). Partially implemented.
        """

        def __init__(self, height: int, width: int, barr: bitarray):
            assert barr.length() == (height * width)

            self.__arr = barr
            self.height = height
            self.width = width


        @classmethod
        def with_initial(cls,  height: int, width: int, initial_value: bool = False):
            barr = bitarray(height * width)
            barr.setall(initial_value)
            return cls(height, width, barr)

        def __copy__(self):
            cp = self.__class__(height=self.height, width=self.width, barr=self.__arr.copy())
            return cp

        def __contains__(self, item: 'Cell'):
            p = self.__position_of(item)
            return 0 <= p < self.__arr.length() and self.__arr[p]


        def __iadd__(self, other: 'Cell'):
            self[other] = True
            return self


        def __isub__(self, other: 'Cell'):
            self[other] = False
            return self


        def add_all(self, cells: Iterable['Cell']):
            for cell in cells:
                self.__iadd__(cell)


        def remove_all(self, cells: Iterable['Cell']):
            for cell in cells:
                self.__isub__(cell)


        def __invert__(self):
            """Invert the set (copying it)"""
            cp = copy(self)
            cp.__arr.invert()
            return cp

        def invert(self):
            """Invert the set in-place"""
            self.__arr.invert()
            return self


        def __setitem__(self, key: 'Cell', value: bool):
            self.__arr[self.__position_of(key)] = value


        def setall(self, value: bool):
            self.__arr.setall(value)


        def any_zero(self):
            try:
                i = rindex(self.__arr, False)
                c = self.__rev_position_of(i)
                return c
            except ValueError:
                return None


        def __ior__(self, other: 'Cell.CellSet'):
            self.__arr |= other.__arr
            return self


        def __iand__(self, other: 'Cell.CellSet'):
            self.__arr &= other.__arr
            return self


        def __position_of(self, cell: 'Cell'):
            return cell.x * self.width + cell.y


        def __rev_position_of(self, idx: int) -> 'Cell':
            return Cell(x=idx // self.width, y=idx % self.width)


        def __repr__(self):
            return '\n'.join(textwrap.wrap(self.__arr.to01(), width=self.width))
