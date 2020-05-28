from enum import Enum, unique, auto
from bitarray import bitarray
from typing import List, Any, Dict
import random



@unique
class Direction(Enum):
    HORIZONTAL = auto()
    VERTICAL = auto()

class Strategy(Enum):
    DFS = auto()
    RANDOM = auto()


@unique
class Side(Enum):
    LEFT = auto()
    TOP = auto()
    RIGHT = auto()
    BOT = auto()


    def direction(self):
        is_horiz = self is Side.LEFT or self is Side.RIGHT
        return Direction.HORIZONTAL if is_horiz else Direction.VERTICAL


    def next_cell(self, w, h, x, y):
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
    def clip(w, h, x, y):
        return (x, y) if x in range(w) and y in range(h) else None



class Maze(object):

    def __init__(self, width: int):
        if width <= 0:
            raise AssertionError("Width must be >= 0, got %d" % width)

        self.__width = width

        start_y = random.randint(a=0, b=width - 1)
        end_y = random.randint(a=0, b=width - 1)

        self.__start_door = Maze.make_pos(0, start_y, Side.LEFT)
        self.__end_door = Maze.make_pos(width - 1, end_y, Side.RIGHT)

        # 2 bitarrays: 1 for TOP walls, one for LEFT ones
        # All walls are set
        self.__walls = {d: (width * width) * bitarray('1') for d in list(Direction)}

        # This breaks some walls to make the paths of the maze
        self.__init_walls_dfs()


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
    def end_pos(self) -> Dict[str, Any]:
        return self.__end_door


    @property
    def start_pos(self) -> Dict[str, Any]:
        return self.__start_door


    def has_wall(self, x: int, y: int, side: Side) -> bool:
        self.__check_pos(x, y)

        if side is Side.RIGHT:
            return (x == self.width - 1) or self.has_wall(x + 1, y, Side.LEFT)
        if side is Side.BOT:
            return (y == self.width - 1) or self.has_wall(x, y + 1, Side.TOP)
        else:
            return self.__walls[side.direction()][self.__bitwise_pos(x, y)] is True


    def __set_wall(self, x: int, y: int, side: Side, value: bool = True) -> None:
        self.__check_pos(x, y)

        if side is Side.RIGHT and x < self.width - 1:
            self.__set_wall(x + 1, y, Side.LEFT, value)
        elif side is Side.BOT and y < self.width - 1:
            self.__set_wall(x, y + 1, Side.TOP, value)
        else:
            self.__walls[side.direction()][self.__bitwise_pos(x, y)] = value


    def __bitwise_pos(self, x: int, y: int) -> int:
        return x * self.width + y


    def __check_pos(self, x: int, y: int) -> None:
        if x >= self.width or y >= self.width or x < 0 or y < 0:
            raise IndexError("(%d, %d)" % (x, y))



    def __init_walls_dfs(self) -> None:
        def next_cell_of(side, x, y):
            return side.next_cell(w=self.width, h=self.width, x=x, y=y)


        def can_visit_from_here(side, x, y):
            next_cell = next_cell_of(side, x, y)
            if next_cell is not None:
                (xn, yn) = next_cell
                return not Maze.__bget_or(w=self.width, bitarr=visited, x=xn, y=yn, default=True)
            return False


        visited = (self.width ** 2) * bitarray('0')
        stack = []
        x = 0
        y = 0
        neighbors = list(Side)

        while True:
            visited[self.__bitwise_pos(x, y)] = True
            neighbors = [s for s in neighbors if can_visit_from_here(s, x, y)]  # refilter

            if len(neighbors) == 0:
                if len(stack) == 0:
                    break
                (x, y, neighbors) = stack.pop()
                continue

            # choose a random wall to break, continue the visit there
            side = random.choice(neighbors)
            self.__set_wall(x, y, side, value=False)

            neighbors.remove(side)
            if len(neighbors) != 0:
                stack.append((x, y, neighbors))

            (x, y) = next_cell_of(side, x, y)
            neighbors = list(Side)

        # lastly, break the walls for entrance & exit
        for pos in [self.start_pos, self.end_pos]:
            self.__set_wall(x=pos["x"], y=pos["y"], side=pos["side"], value=False)


    @staticmethod
    def __bget_or(w, bitarr, x, y, default=True) -> bool:
        i = x * w + y
        if i not in range(len(bitarr)):
            return default
        return bitarr[i]


    def __str__(self):
        start_y = self.start_pos["y"]
        end_y = self.end_pos["y"]

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


    @staticmethod
    def make_pos(x, y, side) -> Dict[str, Any]:
        return {"x": x, "y": y, "side": side}
