from util import *
import random
from typing import NamedTuple, Optional,List,Tuple


class GenerationMethod(Enum):
    # https://en.wikipedia.org/wiki/Maze_generation_algorithm#Depth-first_search
    # Biased towards long corridors, pretty easy
    DFS = auto()

    # https://en.wikipedia.org/wiki/Maze_generation_algorithm#Wilson's_algorithm
    # Unbiased random walk
    RANDOM = auto()


class Maze(object):
    __gen_methods_table = {
        GenerationMethod.DFS: lambda self: self.__init_walls_dfs(),
        GenerationMethod.RANDOM: lambda self: self.__init_walls_random(),
    }


    @classmethod
    def square(cls, width: int, gen_method: GenerationMethod = GenerationMethod.RANDOM) -> 'Maze':
        return cls(nrows=width, ncols=width, gen_method=gen_method)


    def __init__(self, nrows: int, ncols: int, gen_method: GenerationMethod = GenerationMethod.RANDOM):
        if nrows <= 0 or ncols <= 0:
            raise AssertionError("Dimensions must be >= 0, got %d, %d" % (nrows, ncols))

        self.__size = nrows * ncols
        self.__nrows = nrows
        self.__ncols = ncols

        start_y = random.randint(a=0, b=nrows - 1)
        end_y = random.randint(a=0, b=nrows - 1)

        self.__start_door = Wall(0, start_y, Side.LEFT)
        self.__end_door = Wall(ncols - 1, end_y, Side.RIGHT)

        # 2 bitarrays: 1 for TOP walls, one for LEFT ones
        # All walls are set
        self.__walls = {d: self.__size * bitarray('1') for d in list(Direction)}

        # This breaks some walls to make the paths of the maze
        Maze.__gen_methods_table[gen_method](self)


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


    @property
    def end_pos(self) -> Wall:
        return self.__end_door


    @property
    def start_pos(self) -> Wall:
        return self.__start_door


    def has_wall(self, wall: Wall) -> bool:
        self.__check_pos(wall.cell)
        (x, y, side) = wall

        if side is Side.RIGHT:
            return (x == self.width - 1) or self.has_wall(Wall(x + 1, y, Side.LEFT))
        if side is Side.BOT:
            return (y == self.height - 1) or self.has_wall(Wall(x, y + 1, Side.TOP))
        else:
            return self.__walls[side.direction()][self.__bitwise_pos(wall.cell)] is True


    def __set_wall(self, wall: Wall, value: bool = True) -> None:
        self.__check_pos(wall.cell)
        (x, y, side) = wall

        if side is Side.RIGHT and x < self.width - 1:
            self.__set_wall(Wall(x + 1, y, Side.LEFT), value)
        elif side is Side.BOT and y < self.height - 1:
            self.__set_wall(Wall(x, y + 1, Side.TOP), value)
        else:
            self.__walls[side.direction()][self.__bitwise_pos(wall.cell)] = value


    def __bitwise_pos(self, cell: Cell) -> int:
        return cell.x * self.height + cell.y


    def __coord_pos(self, idx: int) -> Cell:
        return Cell(idx // self.height, idx % self.height)


    def __check_pos(self, cell: Cell) -> None:
        if cell not in self:
            raise IndexError(cell)


    def __contains__(self, cell: Cell) -> bool:
        return cell.x in range(0, self.height) \
               and cell.y in range(0, self.width)


    def all_cells(self):
        for x in range(0, self.height):
            for y in range(0, self.width):
                yield Cell(x, y)


    # https://en.wikipedia.org/wiki/Maze_generation_algorithm#Wilson's_algorithm
    def __init_walls_random(self) -> None:

        in_maze: Cell.CellSet = self.new_cell_set(False)
        in_path: Cell.CellSet = self.new_cell_set(False)

        # start with a random cell
        in_maze += Cell(x=random.randint(a=0, b=self.height),
                        y=random.randint(a=0, b=self.width))

        while True:
            try:
                cur_cell: Cell = next(c for c in self.all_cells() if c not in in_maze)
            except StopIteration:  # all cells are in the maze, we're done
                break

            in_path += cur_cell
            path: List[Wall] = []

            while cur_cell not in in_maze:  # loop-erased random walk until we find a maze cell

                available: List[Tuple[Wall, Cell]] = [(wall, cell)
                                                      for s in list(Side)
                                                      for wall in [cur_cell.wall(s)]
                                                      for cell in [wall.next_cell]
                                                      if cell in self]

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
                self.__set_wall(wall, value=False)

            in_maze |= in_path
            in_path.setall(False)


    def __init_walls_dfs(self) -> None:

        def can_visit_from_here(wall: Wall):
            next_cell = wall.next_cell
            return next_cell in self and next_cell not in visited


        visited = self.new_cell_set()
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
            self.__set_wall(wall, value=False)

            neighbors.remove(side)
            if len(neighbors) != 0:
                stack.append((cell, neighbors))

            cell = wall.next_cell
            neighbors = list(Side)

        # lastly, break the walls for entrance & exit
        for pos in [self.start_pos, self.end_pos]:
            self.__set_wall(pos, value=False)


    @staticmethod
    def __bget_or(w, bitarr, x, y, default=True) -> bool:
        i = x * w + y
        if i not in range(len(bitarr)):
            return default
        return bitarr[i]


    def __str__(self):
        start_y = self.start_pos.y
        end_y = self.end_pos.y

        res = ""
        for j in range(0, self.height):
            hline = "   "
            vline = "   " if start_y != j else "-> "

            for i in range(0, self.width):
                has_top = self.__walls[Direction.VERTICAL][self.__bitwise_pos(Cell(i, j))]
                has_left = self.__walls[Direction.HORIZONTAL][self.__bitwise_pos(Cell(i, j))] \
                           and not (j == start_y and i == 0)

                hline += "+--" if has_top else "+  "
                vline += "|  " if has_left else "   "

            res += hline + "+\n"
            res += vline + ("|\n" if end_y != j else " ->\n")

        res += "   "
        res += ("+--" * self.width)
        res += "+"

        return res
