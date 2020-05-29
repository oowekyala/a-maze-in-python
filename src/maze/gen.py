from maze.model import  *
from maze.viz import *
import random
from typing import Callable, List, Tuple
from abc import abstractmethod, ABCMeta

class Maze(object):
    """A maze with fixed-dimensions. Initially all cells are walled. apply_gen generates corridors
       by breaking some walls"""


    def __init__(self, nrows: int, ncols: int):
        if nrows <= 0 or ncols <= 0:
            raise AssertionError("Dimensions must be >= 0, got %d, %d" % (nrows, ncols))

        self.__size = nrows * ncols
        self.__nrows = nrows
        self.__ncols = ncols

        self.start_cell = Cell(0, random.randint(a=0, b=nrows - 1))
        self.end_cell = Cell(ncols - 1, random.randint(a=0, b=nrows - 1))

        self.reset()


    def apply_gen(self, gen: 'GenerationAlgo', pen: GridPen):
        self.reset()
        pen.reset_maze(maze=self)
        gen.generate(maze=self, break_wall=lambda w: self.__break_wall(w, pen))


    def __break_wall(self, wall: Wall, pen: GridPen):
        self.__set_wall(wall, False)
        pen.update_wall(wall, active=False)


    def reset(self):
        # 2 bitarrays: 1 for TOP walls, one for LEFT ones
        # All walls are set
        self.__walls = {d: self.new_cell_set(True) for d in list(Direction)}


    def new_cell_set(self, initial_value: bool = False) -> Cell.CellSet:
        return Cell.CellSet(height=self.height, width=self.width, initial_value=initial_value)


    @property
    def height(self) -> int:
        """Number of rows, ie height, ie max value (exclusive) of the y coordinate of a Cell"""
        return self.__nrows


    @property
    def width(self) -> int:
        """Number of columns, ie width, ie max value (exclusive) of the x coordinate of a Cell"""
        return self.__ncols


    def has_wall(self, wall: Wall) -> bool:
        self.__check_pos(wall.cell)
        (x, y, side) = wall

        if side is Side.RIGHT:
            return (x == self.width - 1) or self.has_wall(Wall(x + 1, y, Side.LEFT))
        if side is Side.BOT:
            return (y == self.height - 1) or self.has_wall(Wall(x, y + 1, Side.TOP))
        else:
            return wall.cell in self.__walls[side.direction()]


    def __set_wall(self, wall: Wall, value: bool = True) -> None:
        self.__check_pos(wall.cell)
        (x, y, side) = wall

        if side is Side.RIGHT and x < self.width - 1:
            self.__set_wall(Wall(x + 1, y, Side.LEFT), value)
        elif side is Side.BOT and y < self.height - 1:
            self.__set_wall(Wall(x, y + 1, Side.TOP), value)
        else:
            self.__walls[side.direction()][wall.cell] = value


    def __check_pos(self, cell: Cell) -> None:
        if cell not in self:
            raise IndexError(cell)


    def __contains__(self, cell: Cell) -> bool:
        return cell.x in range(0, self.height) \
               and cell.y in range(0, self.width)


    def all_cells(self):
        return Cell.iterate(h=self.height, w=self.width)


    def __str__(self):
        res = ""
        for j in range(0, self.height):
            hline = "   "
            vline = "   "

            for i in range(0, self.width):
                cell = Cell(i, j)
                has_top = cell in self.__walls[Direction.VERTICAL]
                has_left = cell in self.__walls[Direction.HORIZONTAL]

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


    def draw_walls(self, pen: GridPen) -> None:
        for y in range(0, self.height):
            for x in range(0, self.width):
                cell = Cell(x, y)
                if cell in self.__walls[Direction.VERTICAL]:
                    pen.update_wall(cell.wall(Side.TOP), active=True)

                if cell in self.__walls[Direction.HORIZONTAL]:
                    pen.update_wall(cell.wall(Side.LEFT), active=True)

                if y == self.height - 1:
                    pen.update_wall(Cell(y, self.width).wall(Side.BOT), active=True)

                if x == self.width - 1:
                    pen.update_wall(Cell(y, self.width).wall(Side.RIGHT), active=True)




class GenerationAlgo(metaclass=ABCMeta):

    @abstractmethod
    def generate(self,
                 maze: Maze,
                 break_wall: Callable[[Wall], None]) -> None:
        """
        Generate the maze by breaking some walls. Initially all walls are
        set.

        :param maze:            Receiver maze
        :param break_wall:      Function that breaks a wall
        """
        pass



class DfsGenerate(GenerationAlgo):

    def generate(self,
                 maze: Maze,
                 break_wall: Callable[[Wall], None]) -> None:

        def can_visit_from_here(wall: Wall):
            next_cell = wall.next_cell
            return next_cell in maze and next_cell not in visited


        visited = maze.new_cell_set(False)
        stack = []
        cell = Cell(0, 0)
        neighbors = list(Side)

        while True:
            visited += cell
            neighbors = [s for s in neighbors if can_visit_from_here(cell.wall(s))]  # refilter

            if len(neighbors) == 0:
                if len(stack) == 0:
                    break
                (cell, neighbors) = stack.pop()
                continue

            # choose a random wall to break, continue the visit there
            side = random.choice(neighbors)
            wall = cell.wall(side)
            break_wall(wall)

            neighbors.remove(side)
            if len(neighbors) != 0:
                stack.append((cell, neighbors))

            cell = wall.next_cell
            neighbors = list(Side)



class WilsonGenerate(GenerationAlgo):
    """
    Wilson's algorithm, to generate unbiased random mazes.

    https://en.wikipedia.org/wiki/Maze_generation_algorithm#Wilson's_algorithm
    """


    def generate(self,
                 maze: Maze,
                 break_wall: Callable[[Wall], None]) -> None:

        in_maze: Cell.CellSet = maze.new_cell_set(False)
        in_path: Cell.CellSet = maze.new_cell_set(False)

        # start with a random cell
        in_maze += Cell(x=random.randint(a=0, b=maze.height),
                        y=random.randint(a=0, b=maze.width))

        while True:
            try:
                cur_cell: Cell = next(c for c in maze.all_cells() if c not in in_maze)
            except StopIteration:  # all cells are in the maze, we're done
                break

            in_path += cur_cell
            path: List[Wall] = []

            while cur_cell not in in_maze:  # loop-erased random walk until we find a maze cell

                available: List[Tuple[Wall, Cell]] = [(wall, cell)
                                                      for s in list(Side)
                                                      for wall in [cur_cell.wall(s)]
                                                      for cell in [wall.next_cell]
                                                      if cell in maze]

                if len(available) == 0:
                    raise AssertionError("No reachable neighbour from %s" % cur_cell)

                (next_wall, next_cell) = random.choice(available)

                if next_cell in in_path:  # loop in the path
                    loop_start = next(i for i in range(len(path)) if path[i].cell == next_cell)
                    for w in path[loop_start + 1:]:
                        in_path -= w.cell

                    cur_cell = path[loop_start].next_cell

                    path[loop_start + 1:] = []  # erase loop, eg [a,b,c,d,b] becomes [a,b]
                else:
                    in_path += next_cell
                    path.append(next_wall)

                    cur_cell = next_cell

            # lastly add the whole path to the maze

            for wall in path:
                break_wall(wall)

            in_maze |= in_path
            in_path.setall(False)

