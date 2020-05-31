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

        self.start_cell = self.rand_cell()
        self.end_cell = self.rand_cell()

        self.reset()


    def rand_cell(self):
        """Generate a random cell in this maze"""
        return Cell(x=random.randrange(0, self.height),
                    y=random.randrange(0, self.width))


    def apply_gen(self, gen: 'GenerationAlgo', pen: GridPen):
        self.reset()
        pen.reset_maze(maze=self)

        pen.update_cells(self.all_cells(), state=CellState.UNDISCOVERED, global_update=True)

        gen.generate(maze=self, seed=self.start_cell, pen=pen)


    def break_wall(self, wall: Wall, pen: GridPen):
        self.set_wall(wall, False)
        pen.update_wall(wall, WallState.OFF)


    def reset(self):
        # 2 bitarrays: 1 for TOP walls, one for LEFT ones
        # All walls are set
        self.__walls = {
            Side.TOP: self.new_cell_set(),
            Side.LEFT: self.new_cell_set(),
        }

    def new_cell_set(self, initial_value: bool = False) -> Cell.CellSet:
        return Cell.CellSet.with_initial(height=self.height, width=self.width, initial_value=initial_value)

    def walls_around(self, cell: Cell, *, blacklist=None):
        return [w
                for s in list(Side)
                for w in [cell.wall(s)]
                if w.next_cell in self
                if (not blacklist or w.next_cell not in blacklist)]


    @property
    def height(self) -> int:
        """Number of rows, ie height, ie max value (exclusive) of the x coordinate of a Cell"""
        return self.__nrows


    @property
    def width(self) -> int:
        """Number of columns, ie width, ie max value (exclusive) of the y coordinate of a Cell"""
        return self.__ncols


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


    def set_wall(self, wall: Wall, is_present: bool = True) -> None:
        """Set the given wall, or unsets it. Boundaries of the maze cannot be set."""
        self.__check_pos(wall.cell)
        if wall.next_cell not in self:
            return None

        (cell, side) = wall

        if side == Side.RIGHT or side == Side.BOT:
            self.__walls[~side][wall.next_cell] = is_present
        else:
            self.__walls[side][cell] = is_present


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


    def draw_regular_tiles(self, pen: GridPen) -> None:
        """Draw walls & blanks, special tiles are added later"""
        for cell in self.all_cells():

            if cell in self.__walls[Side.TOP]:
                pen.update_wall(cell.wall(Side.TOP), WallState.ON)

            if cell in self.__walls[Side.LEFT]:
                pen.update_wall(cell.wall(Side.LEFT), WallState.ON)

            if cell.x == self.height - 1:
                pen.update_wall(cell.wall(Side.BOT), WallState.ON)

            if cell.y == self.width - 1:
                pen.update_wall(cell.wall(Side.RIGHT), WallState.ON)



class GenerationAlgo(metaclass=ABCMeta):

    @abstractmethod
    def generate(self,
                 maze: Maze,
                 seed: Cell,
                 pen: GridPen) -> None:
        """
        Generate the maze by breaking some walls. Initially all walls are
        set.

        :param seed:            Seed for the algo (if it needs a starting cell)
        :param maze:            Receiver maze
        :param pen:             Pen to draw the generation
        """
        pass


    @staticmethod
    def _break_wall_between(break_wall_fun, c1, c2):
        break_wall_fun(Cell(x=(c1.x + c2.x) // 2,
                            y=(c1.y + c2.y) // 2))



class PrimGenerate(GenerationAlgo):

    def generate(self,
                 maze: Maze,
                 seed: Cell,
                 pen: GridPen) -> None:

        visited = maze.new_cell_set()

        def walls_around(cell: Cell):
            return maze.walls_around(cell, blacklist=visited)


        walls = set(walls_around(seed))
        pen.update_walls(walls, WallState.ACTIVE)

        visited += maze.start_cell

        # While there are walls in the list:
        # Pick a random wall from the list. If only one of the cells that the wall divides is visited, then:
        # # Make the wall a passage and mark the unvisited cell as part of the maze.
        # # Add the neighboring walls of the cell to the wall list.
        # Remove the wall from the list.
        while len(walls) > 0:
            wall: Wall = random.choice(tuple(walls))
            walls.remove(wall)

            if (wall.cell in visited) ^ (wall.next_cell in visited):  # exactly one was visited
                maze.break_wall(wall, pen)

                # assert wall.next_cell not in visited  # if it was added to the set of walls, then the src cell was visited
                # assert wall.next_cell in maze  # if it was added to the set of walls, then it is in the maze

                visited += wall.next_cell
                pen.update_cell(wall.next_cell, CellState.NORMAL)
                new_walls = walls_around(wall.next_cell)
                walls.update(new_walls)
                pen.update_walls(new_walls, WallState.ACTIVE)
            else:
                pen.update_wall(wall, WallState.ON)  # Remove ACTIVE status



class DfsGenerate(GenerationAlgo):

    def generate(self,
                 maze: Maze,
                 seed: Cell,
                 pen: GridPen) -> None:

        visited = maze.new_cell_set(False)
        stack = []
        cell = seed

        while True:
            visited += cell
            pen.update_cell(cell, CellState.NORMAL)

            walls: List[Wall] = maze.walls_around(cell, blacklist=visited)

            if len(walls) == 0:
                while len(stack) > 0 and len(walls) == 0:
                    (cell, walls_p) = stack.pop()
                    walls = []
                    for w in walls_p:
                        if w.next_cell in visited:
                            pen.update_wall(w, WallState.ON)
                        else:
                            walls.append(w)

                if len(walls) == 0:
                    break

            # choose a random wall to break, continue the visit there
            next_wall: Wall = random.choice(walls)

            maze.break_wall(next_wall, pen)

            walls.remove(next_wall)
            if len(walls) != 0:
                pen.update_walls(walls, WallState.ACTIVE)
                stack.append((cell, walls))

            cell = next_wall.next_cell


class WilsonGenerate(GenerationAlgo):
    """
    Wilson's algorithm, to generate unbiased random mazes.

    https://en.wikipedia.org/wiki/Maze_generation_algorithm#Wilson's_algorithm
    """


    def generate(self,
                 maze: Maze,
                 seed: Cell,
                 pen: GridPen) -> None:

        in_maze: Cell.CellSet = maze.new_cell_set(False)
        in_path: Cell.CellSet = maze.new_cell_set(False)

        in_maze += seed  # TODO first cell should not be the seed

        last_cell = Cell(0, 0)

        def random_not_in_maze():
            # Linear brute force TODO memo last try
            try:
                nonlocal last_cell
                c = next(c for c in maze.all_cells(from_cell=last_cell) if c not in in_maze)
                last_cell = c
                return c
            except StopIteration:  # all cells are in the maze, we're done
                return None


        while True:
            cur_cell: Cell = random_not_in_maze()
            if not cur_cell:  # all cells are in the maze, we're done
                break

            in_path += cur_cell
            pen.update_cell(cur_cell, CellState.ACTIVE)
            path_start = cur_cell
            path: List[Wall] = []

            while cur_cell not in in_maze:  # loop-erased random walk until we find a maze cell
                time.sleep(0.001)

                neighbors: List[Wall] = maze.walls_around(cur_cell)

                if len(neighbors) == 0:
                    raise AssertionError("No reachable neighbour from %s" % cur_cell)

                next_wall: Wall = random.choice(neighbors)
                next_cell: Cell = next_wall.next_cell

                if next_cell in in_path:  # loop in the path
                    if next_cell == path_start:
                        loop_start = -1
                    else:
                        loop_start = next(i for i in range(len(path)) if path[i].cell == next_cell)

                    for wall in path[loop_start + 1:]:
                        nc = wall.next_cell
                        in_path -= nc
                        if nc == maze.end_cell:
                            pen.update_cell(wall.next_cell, CellState.UNDISCOVERED)
                        else:
                            pen.update_cell(wall.next_cell, CellState.UNDISCOVERED)

                    cur_cell = path_start if loop_start < 0 else path[loop_start].next_cell

                    path[loop_start + 1:] = []  # erase loop, eg [a,b,c,d,b] becomes [a,b]
                else:
                    in_path += next_cell
                    path.append(next_wall)

                    pen.update_cell(next_cell, CellState.ACTIVE)

                    cur_cell = next_cell

            # lastly add the whole path to the maze, meaning
            # break walls separating items of the path

            for wall in path:
                pen.update_cell(wall.cell, CellState.NORMAL)
                maze.break_wall(wall, pen)

            pen.update_cell(cur_cell, CellState.NORMAL)

            in_maze |= in_path
            in_path.setall(False)
