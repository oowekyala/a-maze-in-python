# Amaze - maze visualisation
# Copyright (C) 2020 Clément Fournier
# Some rights reserved. See LICENSE, or <https://www.gnu.org/licenses/gpl-3.0.html>

import textwrap
from enum import Enum, unique, auto
from typing import NamedTuple, Optional, Union, Iterable, Any, List
from bitarray import bitarray
from bitarray.util import rindex
from copy import copy
from random import Random



@unique
class Side(Enum):
    # (delta row, delta col)
    WEST = (0, -1)
    NORTH = (-1, 0)
    EAST = (0, +1)
    SOUTH = (+1, 0)


    def __invert__(self):
        return Side._opp_table[self]

    @property
    def d_row(self):
        return self.value[0]


    @property
    def d_col(self):
        return self.value[1]


Side._opp_table = {Side.WEST: Side.EAST, Side.EAST: Side.WEST, Side.NORTH: Side.SOUTH, Side.SOUTH: Side.NORTH}


@unique
class Neighbour(Enum):
    WW = (Side.WEST, Side.WEST)
    NW = (Side.NORTH, Side.WEST)
    NN = (Side.NORTH, Side.NORTH)
    NE = (Side.NORTH, Side.EAST)
    EE = (Side.EAST, Side.EAST)
    SE = (Side.SOUTH, Side.EAST)
    SS = (Side.SOUTH, Side.SOUTH)
    SW = (Side.SOUTH, Side.WEST)



class Cell(NamedTuple):
    """
    A cell position in a maze.
    """
    row: int
    col: int


    def __hash__(self):
        return self.row * 200_000 + self.col


    def wall(self, side: Side) -> 'Wall':
        return Wall(self, side=side)


    def next(self, side) -> 'Cell':
        return Cell(self.row + side.d_row,
                    self.col + side.d_col)


    def next_path(self, side, *others) -> 'Cell':
        (row, col) = self

        row += side.d_row
        col += side.d_col

        for s in others:
            row += s.d_row
            col += s.d_col

        return Cell(row, col)


    @staticmethod
    def iterate(from_cell=None, *, w: int, h: int, step=1):
        if not from_cell:
            from_cell = Cell(0, 0)

        for col in range(from_cell.col, w, step):
            yield Cell(from_cell.row, col)

        for row in range(from_cell.row + 1, h, step):
            for col in range(0, w, step):
                yield Cell(row, col)

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
            return cell.row * self.width + cell.col


        def __rev_position_of(self, idx: int) -> 'Cell':
            return Cell(row=idx // self.width, col=idx % self.width)


        def __repr__(self):
            return '\n'.join(textwrap.wrap(self.__arr.to01(), width=self.width))



class Wall(NamedTuple):
    """ Wall of a cell. """
    cell: Cell
    side: Side

    @property
    def next_cell(self):
        return self.cell.next(side=self.side)


class Maze(object):
    """A maze with fixed-dimensions."""


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
        self.end_cell = Cell(row=self.nrows - 1, col=self.ncols - 1)

        # 2 bitarrays: 1 for TOP walls, one for LEFT ones
        # All walls are set
        self.__walls = {
            Side.NORTH: self.new_cell_set(initial_value=True),
            Side.WEST: self.new_cell_set(initial_value=True),
        }

    def __wall_map(self):
        return {
            Side.NORTH: self.new_cell_set(initial_value=True),
            Side.WEST: self.new_cell_set(initial_value=True),
        }


    def rand_cell(self):
        """Generate a random cell in this maze"""
        return Cell(row=self.random.randrange(0, self.nrows),
                    col=self.random.randrange(0, self.ncols))


    def reset(self, walls_on: bool):
        for wall_set in self.__walls.values():
            wall_set.setall(walls_on)


    def new_cell_set(self, initial_value: bool = False) -> Cell.CellSet:
        return Cell.CellSet.with_initial(height=self.nrows, width=self.ncols, initial_value=initial_value)


    def walls_around(self, cell: Cell, except_sides: Iterable[Side] = (), only_passages=False, blacklist=None) -> List[Wall]:
        """
        Returns the walls surrounding the given cell. By default doesn't check whether the wall is
        up or down, just checks that the wall does not lead out of the labyrinth (next_cell in maze).

        :param cell: Cell
        :param except_sides: Don't consider sides found in this iterable
        :param only_passages: Filter to return only walls that are down
        :param blacklist: Exclude walls if their next_cell is in this CellSet
        :return:
        """
        return [w
                for s in list(Side)
                if s not in except_sides
                # these should use python 3.8's assignment expression (:=)
                for w in [cell.wall(s)]
                for next_cell in [w.next_cell]
                if next_cell in self
                if (not only_passages) or (not self.has_wall(w))
                if (not blacklist or next_cell not in blacklist)]


    @property
    def nrows(self) -> int:
        """Number of rows, ie height"""
        return self.__nrows


    @property
    def ncols(self) -> int:
        """Number of columns, ie width"""
        return self.__ncols


    @property
    def num_cells(self) -> int:
        """Number of cells in the maze"""
        return self.__size


    def has_wall(self, wall: Wall) -> bool:
        """True if the wall exists, false if not. Throws IndexError if cell is out-of-bounds."""
        self.__check_pos(wall.cell)
        next_cell = wall.next_cell
        if next_cell not in self:
            return True

        (cell, side) = wall

        if side == Side.EAST or side == Side.SOUTH:
            return next_cell in self.__walls[~side]
        else:
            return cell in self.__walls[side]


    def set_walls(self, *walls: Wall, is_present: bool = True) -> None:
        """Set the given walls, or unsets them. Boundaries of the maze cannot be set."""
        for wall in walls:
            self.__check_pos(wall.cell)
            if wall.next_cell not in self:
                continue

            (cell, side) = wall

            if side == Side.EAST or side == Side.SOUTH:
                self.__walls[~side][wall.next_cell] = is_present
            else:
                self.__walls[side][cell] = is_present

        self.mod_count += len(walls)


    def __check_pos(self, cell: Cell) -> None:
        if cell not in self:
            raise IndexError(cell)


    def __contains__(self, cell: Cell) -> bool:
        return 0 <= cell.row < self.nrows \
               and 0 <= cell.col < self.ncols


    def all_cells(self, from_cell=None):
        return Cell.iterate(from_cell=from_cell, h=self.nrows, w=self.ncols)


    def __str__(self):
        res = ""
        for row in range(self.nrows):
            hline = "   "
            vline = "   "

            for col in range(self.ncols):
                cell = Cell(row, col)
                has_top = cell in self.__walls[Side.NORTH]
                has_left = cell in self.__walls[Side.WEST]
                hline += "+--" if has_top else "+  "
                vline += "|" if has_left else " "
                vline += "<>" if self.start_cell == cell \
                    else "><" if self.end_cell == cell \
                    else "  "

            res += hline + "+\n"
            res += vline + "|\n"

        res += "   "
        res += ("+--" * self.ncols)
        res += "+"
        return res


    def distinct_walls(self, on: bool) -> Iterable[Wall]:
        """
        Return all distinct walls that are either on or off, depending on the parameter 'on'
        """
        for cell in self.all_cells():

            if on == (cell in self.__walls[Side.NORTH]):
                yield cell.wall(Side.NORTH)

            if on == (cell in self.__walls[Side.WEST]):
                yield cell.wall(Side.WEST)
