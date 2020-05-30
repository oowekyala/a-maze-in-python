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

        self.start_cell = Cell(x=random.randrange(0, nrows, 2), y=random.randrange(0, ncols, 2))
        self.end_cell = Cell(x=random.randrange(0, nrows, 2), y=random.randrange(0, ncols, 2))

        self.reset()


    def apply_gen(self, gen: 'GenerationAlgo', pen: GridPen):
        self.reset()
        pen.reset_maze(maze=self)
        gen.generate(maze=self, pen=pen, break_wall=lambda w: self.__break_wall(w, pen))


    def __break_wall(self, cell: Cell, pen: GridPen):
        self.set_wall(cell, False)
        if cell != self.start_cell and cell != self.end_cell:
            pen.update_cell(cell, CellState.BLANK)

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
                       shift: int = 1,
                       include_walls: bool = False,
                       include_diag: bool = False,
                       blacklist: Optional[Cell.CellSet] = None,
                       whitelist: Optional[Cell.CellSet] = None):
        return [c
                for s in (list(Neighbour) if include_diag else list(Side))
                for c in [cell.next(s, shift=shift)]
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


    def all_even_cells(self):
        return Cell.iterate(h=self.height, w=self.width, step=2)


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
        pen.update_cells(self.all_cells(), state=lambda c: CellState.WALL if self.is_wall(c) else CellState.BLANK,
                         global_update=True)


class GenerationAlgo(metaclass=ABCMeta):

    @abstractmethod
    def generate(self,
                 maze: Maze,
                 pen: GridPen,
                 break_wall: Callable[[Cell], None]) -> None:
        """
        Generate the maze by breaking some walls. Initially all walls are
        set.

        :param maze:            Receiver maze
        :param pen:             Pen to draw the generation (breaking a wall already updates the pen)
        :param break_wall:      Function that breaks a wall
        """
        pass


    def _break_wall_between(self, break_wall_fun, c1, c2):
        break_wall_fun(Cell(x=(c1.x + c2.x) // 2,
                            y=(c1.y + c2.y) // 2))



class PrimGenerate(GenerationAlgo):

    def generate(self,
                 maze: Maze,
                 pen: GridPen,
                 break_wall: Callable[[Cell], None]) -> None:

        def neighbors(c: Cell):
            return maze.neighbors_list(c, include_walls=True, include_diag=False)


        def is_dormant(c: Cell):
            return (c.x & 1) == 0 and (c.y & 1) == 0


        def rand_cell():
            # Those must end up on dormant cells (even x and y)
            return Cell(x=random.randrange(0, maze.height, 2), y=random.randrange(0, maze.width, 2))

        maze.start_cell = rand_cell()
        maze.end_cell = rand_cell()

        pen.update_cells(maze.all_cells(),
                         state=lambda c: CellState.IGNORED if is_dormant(c) else CellState.WALL,
                         global_update=True)

        break_wall(maze.start_cell)

        pen.update_cell(maze.start_cell, CellState.START)
        pen.update_cell(maze.end_cell, CellState.END)

        walls = set([w for w in neighbors(maze.start_cell) if maze.is_wall(w) and not is_dormant(w)])
        pen.update_cells(walls, CellState.ACTIVE)

        while len(walls) > 0:
            wall = random.choice(tuple(walls))
            visited = 0
            dormant_neighbors = set([])
            new_walls = []

            ns = neighbors(wall)
            for n in ns:

                # Every dormant node eventually becomes a blank node, while the regular walls
                # sometimes become a passage between blanks and are sometimes left as walls

                if is_dormant(n) and maze.is_wall(n):
                    dormant_neighbors.add(n)
                elif maze.is_free(n):
                    visited += 1

            if visited <= 1:
                break_wall(wall)

                if len(dormant_neighbors) > 0:
                    cell = dormant_neighbors.pop()
                    break_wall(cell)

                    new_walls = [n for n in neighbors(cell) if maze.is_wall(n)]
            else:
                pen.update_cell(wall, CellState.WALL)

            walls.update(new_walls)
            walls.remove(wall)
            pen.update_cells(new_walls, CellState.ACTIVE)



# FIX US

class DfsGenerate(GenerationAlgo):

    def generate(self,
                 maze: Maze,
                 pen: GridPen,
                 break_wall: Callable[[Cell], None]) -> None:

        visited = maze.new_cell_set(False)
        stack = []
        cell = Cell(0, 0)

        while True:
            visited += cell
            break_wall(cell)
            neighbors = maze.neighbors_list(cell, include_walls=True, blacklist=visited, shift=2)

            if len(neighbors) == 0:
                if len(stack) == 0:
                    break
                cell = stack.pop()
                continue

            # choose a random wall to break, continue the visit there
            next_cell: Cell = random.choice(neighbors)
            self._break_wall_between(break_wall, cell, next_cell)

            neighbors.remove(next_cell)
            if len(neighbors) != 0:
                pen.update_cells(neighbors, CellState.ACTIVE)
                stack.append(cell)

            cell = next_cell


class WilsonGenerate(GenerationAlgo):
    """
    Wilson's algorithm, to generate unbiased random mazes.

    https://en.wikipedia.org/wiki/Maze_generation_algorithm#Wilson's_algorithm
    """


    def generate(self,
                 maze: Maze,
                 pen: GridPen,
                 break_wall: Callable[[Cell], None]) -> None:

        in_maze: Cell.CellSet = maze.new_cell_set(False)
        in_path: Cell.CellSet = maze.new_cell_set(False)


        def random_not_in_maze():
            # Linear brute force
            try:
                return next(c for c in maze.all_even_cells() if c not in in_maze)
            except StopIteration:  # all cells are in the maze, we're done
                return None


        # start with a random cell
        in_maze += maze.start_cell
        break_wall(maze.start_cell)

        while True:
            cur_cell: Cell = random_not_in_maze()
            if not cur_cell:  # all cells are in the maze, we're done
                break

            in_path += cur_cell
            pen.update_cell(cur_cell, CellState.ACTIVE)
            path: List[Cell] = [cur_cell]

            while cur_cell not in in_maze:  # loop-erased random walk until we find a maze cell
                time.sleep(0.001)

                available: List[Cell] = maze.neighbors_list(cur_cell, include_walls=True, shift=2)

                if len(available) == 0:
                    raise AssertionError("No reachable neighbour from %s" % cur_cell)

                next_cell: Cell = random.choice(available)

                if next_cell in in_path:  # loop in the path
                    loop_start = path.index(next_cell)
                    loop_slice = path[loop_start + 1:]
                    for c in loop_slice:
                        in_path -= c

                    pen.update_cells(loop_slice, CellState.WALL)

                    cur_cell = path[loop_start]

                    path[loop_start + 1:] = []  # erase loop, eg [a,b,c,d,b] becomes [a,b]
                else:
                    in_path += next_cell
                    path.append(next_cell)

                    pen.update_cell(next_cell, CellState.ACTIVE)

                    cur_cell = next_cell

            # lastly add the whole path to the maze, meaning
            # break walls separating items of the path

            for c1, c2 in zip(path, path[1:]):
                self._break_wall_between(break_wall, c1, c2)

            pen.update_cells(path, lambda c: CellState.BLANK if c not in [maze.start_cell, maze.end_cell] else None)

            in_maze |= in_path
            in_path.setall(False)
