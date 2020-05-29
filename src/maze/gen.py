from maze.model import  *
from maze.viz import *
import random, time
from typing import Callable, List, Tuple
from abc import abstractmethod, ABCMeta



class Maze(object):
    """A maze with fixed-dimensions. Cells are either walled or free. Initially all cells are walled.
       apply_gen generates corridors by breaking some walls

            y
       ------->
       |
      x|
       v
       """


    def __init__(self, nrows: int, ncols: int):
        if nrows <= 0 or ncols <= 0:
            raise AssertionError("Dimensions must be >= 0, got %d, %d" % (nrows, ncols))

        self.__size = nrows * ncols
        self.__nrows = nrows
        self.__ncols = ncols

        self.start_cell = Cell(x=random.randint(a=0, b=nrows - 1), y=0)
        self.end_cell = Cell(x=random.randint(a=0, b=nrows - 1), y=ncols - 1)

        self.reset()


    def apply_gen(self, gen: 'GenerationAlgo', pen: GridPen):
        self.reset()
        pen.reset_maze(maze=self)
        gen.generate(maze=self, break_wall=lambda w: self.__break_wall(w, pen))


    def __break_wall(self, cell: Cell, pen: GridPen):
        self.set_wall(cell, False)
        pen.update_cell(cell, CellState.BLANK)
        time.sleep(0.001)


    def reset(self):
        # 2 bitarrays: 1 for TOP walls, one for LEFT ones
        # All walls are set
        self.__free_cells = self.new_cell_set(False)


    def new_cell_set(self, initial_value: bool = False) -> Cell.CellSet:
        return Cell.CellSet.with_initial(height=self.height, width=self.width, initial_value=initial_value)


    def wall_set(self) -> Cell.CellSet:
        """Returns a new cellset containing the walls of the current maze"""
        return ~self.__free_cells


    def neighbors_list(self,
                       cell: Cell,
                       *,
                       include_walls: bool = False,
                       blacklist: Optional[Cell.CellSet] = None,
                       whitelist: Optional[Cell.CellSet] = None):
        return [c
                for s in list(Side)
                for c in [cell.next(s)]
                if c in self
                if include_walls or c in self.__free_cells
                if (not blacklist or c not in blacklist)
                if (not whitelist or c in whitelist)
                ]


    @property
    def height(self) -> int:
        """Number of rows, ie height, ie max value (exclusive) of the y coordinate of a Cell"""
        return self.__nrows


    @property
    def width(self) -> int:
        """Number of columns, ie width, ie max value (exclusive) of the x coordinate of a Cell"""
        return self.__ncols


    def is_wall(self, cell: Cell) -> bool:
        return cell not in self.__free_cells


    def is_free(self, cell: Cell) -> bool:
        return cell in self.__free_cells


    def set_wall(self, cell: Cell, is_wall: bool = True) -> None:
        assert not (cell == self.end_cell or cell == self.start_cell) or not is_wall  # special cells cannot be walls

        self.__check_pos(cell)
        self.__free_cells[cell] = not is_wall


    def __check_pos(self, cell: Cell) -> None:
        if cell not in self:
            raise IndexError(cell)


    def __contains__(self, cell: Cell) -> bool:
        return 0 <= cell.x < self.height and 0 <= cell.y < self.width

    def all_cells(self):
        return Cell.iterate(h=self.height, w=self.width)


    def __str__(self):
        hline = ("x" * (self.width + 2))
        res = hline + "\n"
        for x in range(self.height):
            line = "x"
            for y in range(self.width):
                cell = Cell(x, y)
                if self.is_wall(cell):
                    line += "x"
                elif self.start_cell == cell:
                    line += "»"
                elif self.end_cell == cell:
                    line += "«"
                else:
                    line += " "

            res += line + "x\n"

        res += hline
        return res


    def draw_regular_tiles(self, pen: GridPen) -> None:
        """Draw walls & blanks, special tiles are added later"""
        for cell in self.all_cells():
            state = CellState.WALL if self.is_wall(cell) else CellState.BLANK
            pen.update_cell(cell, state)


class GenerationAlgo(metaclass=ABCMeta):

    @abstractmethod
    def generate(self,
                 maze: Maze,
                 break_wall: Callable[[Cell], None]) -> None:
        """
        Generate the maze by breaking some walls. Initially all walls are
        set.

        :param maze:            Receiver maze
        :param break_wall:      Function that breaks a wall
        """
        pass



class PrimGenerate(GenerationAlgo):

    def generate(self,
                 maze: Maze,
                 break_wall: Callable[[Cell], None]) -> None:

        def neighbors(cell: Cell):
            return maze.neighbors_list(cell, include_walls=True)

        for c in [maze.start_cell, maze.end_cell]:
            break_wall(c)

        walls = set(neighbors(maze.start_cell))

        # While there are walls in the list:
        # Pick a random wall from the list. If only one of the cells that the wall divides is visited, then:
        # # Make the wall a passage and mark the unvisited cell as part of the maze.
        # # Add the neighboring walls of the cell to the wall list.
        # Remove the wall from the list.
        while len(walls) > 0:
            wall = random.choice(tuple(walls))
            wall_neighbours = neighbors(wall)
            neighbouring_walls = []
            pcount = 0
            for n in wall_neighbours:
                if n == maze.start_cell or n == maze.end_cell:
                    continue
                if maze.is_free(n):
                    pcount += 1
                else:
                    neighbouring_walls.append(n)

            if pcount <= 1:
                break_wall(wall)
                walls.update(neighbouring_walls)

            walls.remove(wall)


# FIX US

class DfsGenerate(GenerationAlgo):

    def generate(self,
                 maze: Maze,
                 break_wall: Callable[[Cell], None]) -> None:

        visited = maze.new_cell_set(False)
        stack = []
        cell = Cell(0, 0)

        while True:
            visited += cell
            neighbors = maze.neighbors_list(cell, include_walls=True, blacklist=visited)

            if len(neighbors) == 0:
                if len(stack) == 0:
                    break
                (cell, neighbors) = stack.pop()
                continue

            # choose a random wall to break, continue the visit there
            next_cell: Cell = random.choice(neighbors)
            break_wall(next_cell)

            neighbors.remove(next_cell)
            if len(neighbors) != 0:
                stack.append((cell, neighbors))  # save state for later

            cell = next_cell


class WilsonGenerate(GenerationAlgo):
    """
    Wilson's algorithm, to generate unbiased random mazes.

    https://en.wikipedia.org/wiki/Maze_generation_algorithm#Wilson's_algorithm
    """


    def generate(self,
                 maze: Maze,
                 break_wall: Callable[[Cell], None]) -> None:

        in_maze: Cell.CellSet = maze.new_cell_set(False)
        visited: Cell.CellSet = maze.new_cell_set(False)
        in_path: Cell.CellSet = maze.new_cell_set(False)

        # start with a random cell
        in_maze += Cell(x=random.randint(a=0, b=maze.height),
                        y=random.randint(a=0, b=maze.width))

        while True:
            try:
                cur_cell: Cell = next(c for c in maze.all_cells() if c not in in_maze and c not in visited)
            except StopIteration:  # all cells are in the maze, we're done
                break

            in_path += cur_cell
            path: List[Cell] = []

            while cur_cell not in in_maze:  # loop-erased random walk until we find a maze cell

                available: List[Cell] = maze.neighbors_list(cur_cell, include_walls=True)

                if len(available) == 0:
                    raise AssertionError("No reachable neighbour from %s" % cur_cell)

                next_cell: Cell = random.choice(available)

                if next_cell in in_path:  # loop in the path
                    loop_start = path.index(next_cell)
                    for c in path[loop_start + 1:]:
                        in_path -= c

                    cur_cell = path[loop_start]

                    path[loop_start + 1:] = []  # erase loop, eg [a,b,c,d,b] becomes [a,b]
                else:
                    in_path += next_cell
                    path.append(next_cell)

                    cur_cell = next_cell

            # lastly add the whole path to the maze

            for c in path:
                break_wall(c)

            in_maze |= in_path
            in_path.setall(False)
