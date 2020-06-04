import textwrap
from enum import Enum, unique, auto
from typing import NamedTuple, Optional, Union, Iterable
from bitarray import bitarray
from bitarray.util import rindex
from copy import copy
from random import Random


@unique
class Side(Enum):
    LEFT = auto()
    TOP = auto()
    RIGHT = auto()
    BOT = auto()

    def __invert__(self):
        if self == Side.LEFT:
            return Side.RIGHT
        elif self == Side.RIGHT:
            return Side.LEFT
        elif self == Side.TOP:
            return Side.BOT
        elif self == Side.BOT:
            return Side.TOP


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


    def __hash__(self):
        return self.x * 200_000 + self.y


    def wall(self, side: Side) -> 'Wall':
        return Wall(self, side=side)


    def next(self, side: Union[Side, Neighbour], shift: int = 1) -> 'Cell':
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


    def mirror(self, *, around: 'Cell'):
        (dx, dy) = around.x - self.x, around.y - self.y
        return Cell(around.x + dx, around.y + dy)

    @staticmethod
    def iterate(from_cell=None, *, w: int, h: int, step=1):
        if not from_cell:
            from_cell = Cell(0, 0)

        for y in range(from_cell.y, w, step):
            yield Cell(from_cell.x, y)

        for x in range(from_cell.x + 1, h, step):
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



class Wall(NamedTuple):
    """ Wall of a cell. """
    cell: Cell
    side: Side

    @property
    def next_cell(self):
        return self.cell.next(side=self.side)


    @property
    def x(self):
        return self.cell.x


    @property
    def y(self):
        return self.cell.y



class Maze(object):
    """A maze with fixed-dimensions. Cells are either walled or free. Initially all cells are walled.
       apply_gen generates corridors by breaking some walls

            y
       ------->
       |
      x|
       v
       """


    def __init__(self, nrows: int, ncols: int, random_seed: int):
        if nrows <= 0 or ncols <= 0:
            raise AssertionError("Dimensions must be >= 0, got %d, %d" % (nrows, ncols))

        self.__size = nrows * ncols
        self.__nrows = nrows
        self.__ncols = ncols

        self.mod_count = 0

        self.random = Random(random_seed)
        self.random_seed = random_seed

        self.start_cell = Cell(0, 0)
        self.end_cell = Cell(x=self.height - 1, y=self.width - 1)

        # 2 bitarrays: 1 for TOP walls, one for LEFT ones
        # All walls are set
        self.__walls = {
            Side.TOP: self.new_cell_set(initial_value=True),
            Side.LEFT: self.new_cell_set(initial_value=True),
        }

    def __wall_map(self):
        return {
            Side.TOP: self.new_cell_set(initial_value=True),
            Side.LEFT: self.new_cell_set(initial_value=True),
        }


    def rand_cell(self):
        """Generate a random cell in this maze"""
        return Cell(x=self.random.randrange(0, self.height),
                    y=self.random.randrange(0, self.width))


    def reset(self, walls_on: bool):
        for wall_set in self.__walls.values():
            wall_set.setall(walls_on)


    def new_cell_set(self, initial_value: bool = False) -> Cell.CellSet:
        return Cell.CellSet.with_initial(height=self.height, width=self.width, initial_value=initial_value)


    def walls_around(self, cell: Cell, except_sides: Iterable[Side] = (), only_passages=False, blacklist=None):
        return [w
                for s in list(Side)
                if s not in except_sides
                for w in [cell.wall(s)]
                if w.next_cell in self
                if (not only_passages) or (not self.has_wall(w))
                if (not blacklist or w.next_cell not in blacklist)]


    @property
    def height(self) -> int:
        """Number of rows, ie height, ie max value (exclusive) of the x coordinate of a Cell"""
        return self.__nrows


    @property
    def width(self) -> int:
        """Number of columns, ie width, ie max value (exclusive) of the y coordinate of a Cell"""
        return self.__ncols


    @property
    def num_cells(self) -> int:
        """Number of cells in the maze"""
        return self.__size


    def has_wall(self, wall: Wall) -> bool:
        """True if the wall exists, false if not. Throws IndexError if cell is out-of-bounds."""
        self.__check_pos(wall.cell)
        if wall.next_cell not in self:
            return True

        (cell, side) = wall

        if side == Side.RIGHT or side == Side.BOT:
            return wall.next_cell in self.__walls[~side]
        else:
            return cell in self.__walls[side]


    def set_walls(self, *walls: Wall, is_present: bool = True) -> None:
        """Set the given walls, or unsets them. Boundaries of the maze cannot be set."""
        for wall in walls:
            self.__check_pos(wall.cell)
            if wall.next_cell not in self:
                continue

            (cell, side) = wall

            if side == Side.RIGHT or side == Side.BOT:
                self.__walls[~side][wall.next_cell] = is_present
            else:
                self.__walls[side][cell] = is_present

        self.mod_count += len(walls)


    def __check_pos(self, cell: Cell) -> None:
        if cell not in self:
            raise IndexError(cell)


    def __contains__(self, cell: Cell) -> bool:
        return 0 <= cell.x < self.height \
               and 0 <= cell.y < self.width


    def all_cells(self, from_cell=None):
        return Cell.iterate(from_cell=from_cell, h=self.height, w=self.width)


    def __str__(self):
        res = ""
        for x in range(0, self.height):
            hline = "   "
            vline = "   "

            for y in range(0, self.width):
                cell = Cell(x, y)
                has_top = cell in self.__walls[Side.TOP]
                has_left = cell in self.__walls[Side.LEFT]
                hline += "+--" if has_top else "+  "
                vline += "|" if has_left else " "
                vline += "<>" if self.start_cell == cell \
                    else "><" if self.end_cell == cell \
                    else "  "

            res += hline + "+\n"
            res += vline + "|\n"

        res += "   "
        res += ("+--" * self.width)
        res += "+"
        return res


    def distinct_walls(self, on: bool) -> Iterable[Wall]:
        """
        Return all distinct walls that are either on or off, depending on the parameter 'on'
        """
        for cell in self.all_cells():

            if on == (cell in self.__walls[Side.TOP]):
                yield cell.wall(Side.TOP)

            if on == (cell in self.__walls[Side.LEFT]):
                yield cell.wall(Side.LEFT)
