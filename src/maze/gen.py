from abc import abstractmethod, ABCMeta
from typing import List, NamedTuple
from enum import Enum, auto

from maze.viz import *



class StartState(Enum):
    WALLED = auto()
    CLEAR = auto()



class GenerationAlgo(metaclass=ABCMeta):

    def start_state(self) -> StartState:
        """The state the algorithm should start in.
            WALLED: all walls are set, the algorithm's job is to break walls
            CLEAR: no walls are set, the algorithm's job is to create walls
        """
        return StartState.WALLED


    @abstractmethod
    def generate(self, pen: GridPen) -> None:
        """
        Generate the maze by breaking some walls. Initially all walls are
        set or unset, according to the start_state.

        :param pen:             Pen to draw the generation (contains the maze)
        """
        pass



def apply_gen(gen: GenerationAlgo, pen: GridPen):
    is_walled = gen.start_state() == StartState.WALLED
    state = CellState.UNDISCOVERED if is_walled else CellState.NORMAL

    pen.maze.reset(walls_on=is_walled)
    pen.reset_maze(maze=pen.maze)
    pen.draw_entire_maze(cell_state=state, is_walled=is_walled)

    gen.generate(pen=pen)



def _break_wall(wall: Wall, pen: GridPen):
    pen.maze.set_walls(wall, is_present=False)
    pen.update_walls(wall)



class Chamber(NamedTuple):
    """A rectangular region of a maze"""

    top_left: Cell  # inclusive
    bot_right: Cell  # inclusive


    @property
    def width(self):
        return self.bot_right.y - self.top_left.y + 1


    @property
    def height(self):
        return self.bot_right.x - self.top_left.x + 1


    @property
    def is_unit(self):
        return self.height < 2 or self.width < 2


    def border_wall(self, side: Side) -> List[Wall]:
        """Returns the range of walls bordering this chamber on a particular side"""
        if side == Side.RIGHT or side == Side.LEFT:
            const_y = self.bot_right.y if side == Side.RIGHT else self.top_left.y

            return [Wall(Cell(x, const_y), side) for x in range(self.top_left.x, self.bot_right.x + 1)]
        else:
            const_x = self.bot_right.x if side == Side.BOT else self.top_left.x

            return [Wall(Cell(const_x, y), side) for y in range(self.top_left.y, self.bot_right.y + 1)]


class RecursiveDivisionGenerate(GenerationAlgo):

    def start_state(self) -> StartState:
        return StartState.CLEAR


    def divide(self, pen: GridPen, chamber: Chamber, x_divider: int, y_divider: int) -> Iterable[Chamber]:
        """Trace two walls dividing the chamber, return the four subchambers"""

        top_left =  Chamber(chamber.top_left,                            Cell(x=x_divider, y=y_divider))
        top_right = Chamber(Cell(x=chamber.top_left.x, y=y_divider + 1), Cell(x=x_divider, y=chamber.bot_right.y))
        bot_right = Chamber(Cell(x=x_divider + 1, y=y_divider + 1),      chamber.bot_right)
        bot_left =  Chamber(Cell(x=x_divider + 1, y=chamber.top_left.y), Cell(x=chamber.bot_right.x, y=y_divider))

        new_walls = [
            top_right.border_wall(Side.LEFT),
            bot_right.border_wall(Side.LEFT),

            bot_left.border_wall(Side.TOP),
            bot_right.border_wall(Side.TOP),
        ]

        random = pen.maze.random

        # cut out 3 passages out of 4 (remove one of the walls)
        for wall_range in random.sample(new_walls, 3):
            wall_range.pop(random.randrange(0, len(wall_range)))

        for walls in new_walls:
            pen.maze.set_walls(*walls, is_present=True)
            pen.update_walls(*walls)
            pen.algo_tick(self)

        return [top_left, top_right, bot_right, bot_left]


    def generate(self, pen: GridPen) -> None:
        maze = pen.maze


        def cut(c1: int, c2: int):
            return (c1 + c2) // 2  # could use random


        chambers = [Chamber(Cell(0, 0), Cell(x=maze.height - 1, y=maze.width - 1))]

        while len(chambers) > 0:

            chamber = chambers.pop()

            if chamber.is_unit:
                continue

            wall_x = cut(chamber.top_left.x, chamber.bot_right.x)
            wall_y = cut(chamber.top_left.y, chamber.bot_right.y)

            chambers.extend(self.divide(pen=pen, chamber=chamber, x_divider=wall_x, y_divider=wall_y))



class PrimGenerate(GenerationAlgo):

    def generate(self, pen: GridPen) -> None:
        maze: Maze = pen.maze

        visited = maze.new_cell_set()


        def walls_around(cell: Cell):
            return maze.walls_around(cell, blacklist=visited)


        seed = maze.rand_cell()
        walls = set(walls_around(seed))
        pen.update_walls(*walls, state=CellState.ACTIVE)

        visited += seed

        # While there are walls in the list:
        # Pick a random wall from the list. If only one of the cells that the wall divides is visited, then:
        # # Make the wall a passage and mark the unvisited cell as part of the maze.
        # # Add the neighboring walls of the cell to the wall list.
        # Remove the wall from the list.
        while len(walls) > 0:
            wall: Wall = maze.random.choice(tuple(walls))
            walls.remove(wall)

            if (wall.cell in visited) ^ (wall.next_cell in visited):  # exactly one was visited
                _break_wall(wall, pen)

                # assert wall.next_cell not in visited  # if it was added to the set of walls, then the src cell was visited
                # assert wall.next_cell in maze  # if it was added to the set of walls, then it is in the maze

                visited += wall.next_cell

                new_walls = walls_around(wall.next_cell)
                walls.update(new_walls)

                pen.update_cells(wall.next_cell, state=CellState.NORMAL)
                pen.update_walls(*new_walls, state=CellState.ACTIVE)
            else:
                pen.update_walls(wall)  # Remove ACTIVE status

            pen.algo_tick(self, frontier_size=len(walls))



class DfsGenerate(GenerationAlgo):

    def generate(self, pen: GridPen) -> None:
        maze: Maze = pen.maze

        visited = maze.new_cell_set(False)
        stack = []
        cell = maze.rand_cell()

        while True:
            visited += cell
            pen.update_cells(cell, state=CellState.NORMAL)

            pen.algo_tick(self)

            walls: List[Wall] = maze.walls_around(cell, blacklist=visited)

            if len(walls) == 0:
                while len(stack) > 0 and len(walls) == 0:
                    (cell, walls_p) = stack.pop()
                    walls = []
                    for w in walls_p:
                        if w.next_cell in visited:
                            pen.algo_tick(self)
                        else:
                            walls.append(w)

                    pen.update_cells(cell, state=CellState.NORMAL)

                if len(walls) == 0:
                    break

            # choose a random wall to break, continue the visit there
            next_wall: Wall = maze.random.choice(walls)

            _break_wall(next_wall, pen)

            walls.remove(next_wall)
            if len(walls) != 0:
                pen.update_cells(cell, state=CellState.ACTIVE)
                stack.append((cell, walls))

            cell = next_wall.next_cell


class WilsonGenerate(GenerationAlgo):
    """
    Wilson's algorithm, to generate unbiased random mazes.

    https://en.wikipedia.org/wiki/Maze_generation_algorithm#Wilson's_algorithm


    TODO an interesting idea would be to have two random walks at the same time

    """


    def generate(self, pen: GridPen) -> None:
        maze: Maze = pen.maze

        in_maze: Cell.CellSet = maze.new_cell_set(False)
        in_path: Cell.CellSet = maze.new_cell_set(False)

        seed = maze.rand_cell()
        in_maze += seed

        pen.update_cells(seed, state=CellState.NORMAL)

        last_cell = Cell(0, 0)


        def random_not_in_maze():
            # Linear brute force, memos last try so that it doesn't slow down over time
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
            pen.update_cells(cur_cell, state=CellState.ACTIVE)
            path_start = cur_cell
            path: List[Wall] = []
            forbidden_moves: Iterable[Side] = ()

            while cur_cell not in in_maze:  # loop-erased random walk until we find a maze cell
                pen.algo_tick(self)

                neighbors: List[Wall] = maze.walls_around(cur_cell, except_sides=forbidden_moves)

                if len(neighbors) == 0:
                    raise AssertionError("No reachable neighbour from %s" % cur_cell)

                next_wall: Wall = maze.random.choice(neighbors)
                next_cell: Cell = next_wall.next_cell

                if next_cell in in_path:  # loop in the path
                    if next_cell == path_start:
                        loop_start = -1
                    else:
                        loop_start = next(i for i in range(len(path)) if path[i].cell == next_cell)

                    for wall in path[loop_start + 1:]:
                        nc = wall.next_cell
                        in_path -= nc
                        pen.paint_wall_path(wall, state=CellState.UNDISCOVERED)

                    cur_cell = path_start if loop_start < 0 else path[loop_start].next_cell

                    path[loop_start + 1:] = []  # erase loop, eg [a,b,c,d,b] becomes [a,b]
                    forbidden_moves = ()
                else:
                    in_path += next_cell
                    path.append(next_wall)
                    forbidden_moves = (~next_wall.side,)

                    pen.paint_wall_path(next_wall, state=CellState.ACTIVE)

                    cur_cell = next_cell

            # lastly add the whole path to the maze, meaning
            # break walls separating items of the path

            for wall in path:
                _break_wall(wall, pen)
                pen.paint_wall_path(wall, state=CellState.NORMAL)

            pen.update_cells(path_start, state=CellState.NORMAL)

            in_maze |= in_path
            in_path.setall(False)



class SidewinderGenerate(GenerationAlgo):

    def generate(self, pen: GridPen) -> None:
        maze = pen.maze

        top_row = [Cell(0, y) for y in range(0, maze.width)]
        top_walls = [Wall(c, Side.LEFT) for c in top_row]

        # Clear the top row
        maze.set_walls(*top_walls, is_present=False)
        pen.update_cells(*top_row, state=CellState.NORMAL)
        pen.update_walls(*top_walls)

        active: List[Wall] = []

        for row in range(1, maze.height):

            for col in range(0, maze.width):
                cell = Cell(row, col)
                break_north = maze.random.randint(0, 1)
                if col == maze.width - 1 or break_north:
                    pen.update_cells(cell, state=CellState.NORMAL)

                    # cleanup active set
                    active.append(cell.wall(Side.LEFT))
                    (cell, _) = maze.random.choice(active)
                    north_wall = Wall(cell, Side.TOP)
                    _break_wall(north_wall, pen)
                    active.clear()
                else:
                    east_wall = Wall(cell, Side.RIGHT)
                    _break_wall(east_wall, pen)
                    pen.update_cells(cell, east_wall.next_cell, state=CellState.NORMAL)
                    active.append(east_wall)

                pen.algo_tick(self)
