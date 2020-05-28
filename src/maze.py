import random
from enum import Enum, unique, auto
from typing import List, NamedTuple, Optional, Tuple

import bitarray.util as bitutils
from bitarray import bitarray



class Cell(NamedTuple):
    x: int
    y: int



@unique
class Direction(Enum):
    HORIZONTAL = auto()
    VERTICAL = auto()



class GenerationMethod(Enum):
    # https://en.wikipedia.org/wiki/Maze_generation_algorithm#Depth-first_search
    # Biased towards long corridors, pretty easy
    DFS = auto()

    # https://en.wikipedia.org/wiki/Maze_generation_algorithm#Wilson's_algorithm
    # Unbiased random walk
    RANDOM = auto()



@unique
class Side(Enum):
    LEFT = auto()
    TOP = auto()
    RIGHT = auto()
    BOT = auto()


    def wall(self, cell: Cell):
        return Wall(cell.x, cell.y, self)


    def direction(self):
        is_horiz = self is Side.LEFT or self is Side.RIGHT
        return Direction.HORIZONTAL if is_horiz else Direction.VERTICAL


    def next_cell(self, w, h, x, y) -> Optional[Cell]:
        if self is Side.LEFT:
            x = x - 1
        elif self is Side.RIGHT:
            x = x + 1
        elif self is Side.TOP:
            y = y - 1
        elif self is Side.BOT:
            y = y + 1
        else:
            raise AssertionError("dead code")

        return Side.clip(w, h, x, y)


    @staticmethod
    def clip(w, h, x, y) -> Optional[Cell]:
        return Cell(x, y) if x in range(w) and y in range(h) else None



class Wall(NamedTuple):
    x: int
    y: int
    side: Side


    @property
    def cell(self):
        return Cell(self.x, self.y)



class Maze(object):
    __gen_methods_table = {
        GenerationMethod.DFS: lambda self: self.__init_walls_dfs(),
        GenerationMethod.RANDOM: lambda self: self.__init_walls_random(),
    }


    def __init__(self, width: int, gen_method: GenerationMethod = GenerationMethod.RANDOM):
        if width <= 0:
            raise AssertionError("Width must be >= 0, got %d" % width)

        self.__width = width

        start_y = random.randint(a=0, b=width - 1)
        end_y = random.randint(a=0, b=width - 1)

        self.__start_door = Wall(0, start_y, Side.LEFT)
        self.__end_door = Wall(width - 1, end_y, Side.RIGHT)

        # 2 bitarrays: 1 for TOP walls, one for LEFT ones
        # All walls are set
        self.__walls = {d: (width * width) * bitarray('1') for d in list(Direction)}

        # This breaks some walls to make the paths of the maze
        Maze.__gen_methods_table[gen_method](self)


    def border_sides(self, x: int, y: int) -> List[Side]:
        res = []

        if x == 0:
            res.append(Side.TOP)
        if x == self.width:
            res.append(Side.BOT)

        if y == 0:
            res.append(Side.LEFT)
        if y == self.width:
            res.append(Side.RIGHT)

        return res


    @property
    def width(self) -> int:
        return self.__width


    @property
    def end_pos(self) -> Wall:
        return self.__end_door


    @property
    def start_pos(self) -> Wall:
        return self.__start_door


    def has_wall(self, wall: Wall) -> bool:
        return self.__has_wall(wall.x, wall.y, wall.side)


    def __has_wall(self, x: int, y: int, side: Side) -> bool:
        self.__check_pos(x, y)

        if side is Side.RIGHT:
            return (x == self.width - 1) or self.__has_wall(x + 1, y, Side.LEFT)
        if side is Side.BOT:
            return (y == self.width - 1) or self.__has_wall(x, y + 1, Side.TOP)
        else:
            return self.__walls[side.direction()][self.__bitwise_pos(x, y)] is True


    def __set_wall(self, wall: Wall, value: bool = True) -> None:
        (x, y, side) = wall
        self.__check_pos(x, y)

        if side is Side.RIGHT and x < self.width - 1:
            self.__set_wall(Wall(x + 1, y, Side.LEFT), value)
        elif side is Side.BOT and y < self.width - 1:
            self.__set_wall(Wall(x, y + 1, Side.TOP), value)
        else:
            self.__walls[side.direction()][self.__bitwise_pos(x, y)] = value


    def __bitwise_pos(self, x: int, y: int) -> int:
        return x * self.width + y


    def __bitwise_cell_pos(self, cell: Cell) -> int:
        return self.__bitwise_pos(cell.x, cell.y)


    def __coord_pos(self, idx: int) -> Cell:
        return Cell(idx // self.width, idx % self.width)


    def __check_pos(self, x: int, y: int) -> None:
        if x >= self.width or y >= self.width or x < 0 or y < 0:
            raise IndexError("(%d, %d)" % (x, y))


    # https://en.wikipedia.org/wiki/Maze_generation_algorithm#Wilson's_algorithm
    def __init_walls_random(self) -> None:
        in_maze = bitutils.zeros(length=self.width ** 2)
        in_path = in_maze.copy()

        start = random.randint(a=0, b=in_maze.length() - 1)
        in_maze[start] = True

        while True:
            try:
                cur_pos: int = in_maze.index(False)  # choose a cell not in the maze
                cur_cell: Cell = self.__coord_pos(cur_pos)
            except ValueError:  # no more empty cells
                break

            in_path[cur_pos] = True
            path: List[Wall] = []

            while not in_maze[cur_pos]:  # loop-erased random walk until we find a maze cell

                available: List[Tuple[Wall, Cell]] = [(wall, cell)
                                                      for s in list(Side)
                                                      for wall in [Wall(cur_cell.x, cur_cell.y, s)]
                                                      for cell in [self.__next_cell_of(wall)]
                                                      if cell is not None]

                if len(available) == 0:
                    raise AssertionError("No reachable neighbour from %s" % cur_cell)

                (next_wall, next_cell) = random.choice(available)

                next_pos = self.__bitwise_cell_pos(next_cell)

                if in_path[next_pos] is True:  # loop
                    loop_start = next(i for i in range(len(path)) if path[i].cell == next_cell)
                    for w in path[loop_start:]:
                        in_path[self.__bitwise_cell_pos(w.cell)] = False

                    path[loop_start:] = []  # erase loop

                in_path[next_pos] = True
                path.append(next_wall)

                cur_pos = next_pos
                cur_cell = next_cell

            # lastly add the whole path to the maze

            for wall in path:
                self.__set_wall(wall, value=False)

            in_maze |= in_path
            in_path.setall(0)


    def __next_cell_of(self, wall: Wall) -> Optional[Cell]:
        return wall.side.next_cell(w=self.width, h=self.width, x=wall.x, y=wall.y)


    def __init_walls_dfs(self) -> None:

        def can_visit_from_here(wall: Wall):
            next_cell = self.__next_cell_of(wall)
            if next_cell is not None:
                (xn, yn) = next_cell
                return not Maze.__bget_or(w=self.width, bitarr=visited, x=xn, y=yn, default=True)
            return False


        visited = bitutils.zeros(length=self.width ** 2)
        stack = []
        x = 0
        y = 0
        neighbors = list(Side)

        while True:
            visited[self.__bitwise_pos(x, y)] = True
            neighbors = [s for s in neighbors if can_visit_from_here(Wall(x, y, s))]  # refilter

            if len(neighbors) == 0:
                if len(stack) == 0:
                    break
                (x, y, neighbors) = stack.pop()
                continue

            # choose a random wall to break, continue the visit there
            side = random.choice(neighbors)
            wall = Wall(x, y, side)
            self.__set_wall(wall, value=False)

            neighbors.remove(side)
            if len(neighbors) != 0:
                stack.append((x, y, neighbors))

            (x, y) = self.__next_cell_of(wall)
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
        for j in range(0, self.width):
            hline = "   "
            vline = "   " if start_y != j else "-> "

            for i in range(0, self.width):
                has_top = self.__walls[Direction.VERTICAL][self.__bitwise_pos(i, j)]
                has_left = self.__walls[Direction.HORIZONTAL][self.__bitwise_pos(i, j)]
                hline += "+--" if has_top else "+  "
                vline += "|  " if has_left else "   "
            res += hline + "+\n"
            res += vline + ("|\n" if end_y != j else " ->\n")

        res += "   "
        res += ("+--" * self.width)
        res += "+"

        return res