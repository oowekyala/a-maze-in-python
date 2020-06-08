from abc import abstractmethod, ABCMeta
from typing import List, NamedTuple, Set
from enum import Enum, auto

from mazepie.viz import *



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
    pen.tick_frame(gen, force_refresh=True)



def _break_wall(wall: Wall, pen: GridPen):
    pen.maze.set_walls(wall, is_present=False)
    pen.update_walls(wall)


class BlankGen(GenerationAlgo):

    def start_state(self) -> StartState:
        return StartState.CLEAR

    def generate(self, pen: GridPen) -> None:
        pass



class Chamber(NamedTuple):
    """A rectangular region of a maze"""

    top_left: Cell  # inclusive
    bot_right: Cell  # inclusive


    @property
    def width(self):
        return self.bot_right.col - self.top_left.col + 1


    @property
    def height(self):
        return self.bot_right.row - self.top_left.row + 1


    @property
    def is_unit(self):
        return self.height < 2 or self.width < 2


    def border_wall(self, side: Side) -> List[Wall]:
        """Returns the range of walls bordering this chamber on a particular side"""
        if side == Side.EAST or side == Side.WEST:
            const_col = self.bot_right.col if side == Side.EAST else self.top_left.col

            return [Wall(Cell(row, const_col), side) for row in range(self.top_left.row, self.bot_right.row + 1)]
        else:
            const_row = self.bot_right.row if side == Side.SOUTH else self.top_left.row

            return [Wall(Cell(const_row, col), side) for col in range(self.top_left.col, self.bot_right.col + 1)]


class RecursiveDivisionGenerate(GenerationAlgo):

    def start_state(self) -> StartState:
        return StartState.CLEAR


    def divide(self, pen: GridPen, chamber: Chamber, h_divider: int, v_divider: int) -> Iterable[Chamber]:
        """Trace two walls dividing the chamber, return the four subchambers"""

        top_left  = Chamber(chamber.top_left,                                         Cell(row=h_divider,             col=v_divider))
        top_right = Chamber(Cell(row=chamber.top_left.row, col=v_divider + 1),        Cell(row=h_divider,             col=chamber.bot_right.col))
        bot_right = Chamber(Cell(row=h_divider + 1,        col=v_divider + 1),        chamber.bot_right)
        bot_left  = Chamber(Cell(row=h_divider + 1,        col=chamber.top_left.col), Cell(row=chamber.bot_right.row, col=v_divider))

        new_walls = [
            top_right.border_wall(Side.WEST),
            bot_right.border_wall(Side.WEST),

            bot_left.border_wall(Side.NORTH),
            bot_right.border_wall(Side.NORTH),
        ]

        random = pen.maze.random

        # cut out 3 passages out of 4 (remove one of the walls)
        for wall_range in random.sample(new_walls, 3):
            wall_range.pop(random.randrange(0, len(wall_range)))

        for walls in new_walls:
            pen.maze.set_walls(*walls, is_present=True)
            pen.update_walls(*walls)
            pen.tick_frame(self)

        return [top_left, top_right, bot_right, bot_left]


    def generate(self, pen: GridPen) -> None:
        maze = pen.maze


        def cut(c1: int, c2: int):
            return (c1 + c2) // 2  # could use random


        chambers = [Chamber(Cell(0, 0), Cell(row=maze.nrows - 1, col=maze.ncols - 1))]

        while len(chambers) > 0:

            chamber = chambers.pop()

            if chamber.is_unit:
                continue

            h_wall = cut(chamber.top_left.row, chamber.bot_right.row)
            v_wall = cut(chamber.top_left.col, chamber.bot_right.col)

            chambers.extend(self.divide(pen=pen, chamber=chamber, h_divider=h_wall, v_divider=v_wall))



class PrimGenerate(GenerationAlgo):

    def generate(self, pen: GridPen) -> None:
        maze: Maze = pen.maze

        visited = maze.new_cell_set()


        def walls_around(cell: Cell):
            return maze.walls_around(cell, blacklist=visited)


        seed = maze.rand_cell()
        walls = set(walls_around(seed))
        pen.update_cells(seed, state=CellState.NORMAL)
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

            pen.tick_frame(self)



class DfsGenerate(GenerationAlgo):

    def generate(self, pen: GridPen) -> None:
        maze: Maze = pen.maze

        visited = maze.new_cell_set(False)
        stack = []
        cell = maze.rand_cell()

        while True:
            visited += cell
            pen.update_cells(cell, state=CellState.NORMAL)

            pen.tick_frame(self)

            walls: List[Wall] = maze.walls_around(cell, blacklist=visited)

            if len(walls) == 0:
                while len(stack) > 0 and len(walls) == 0:
                    (cell, walls_p) = stack.pop()
                    walls = []
                    for w in walls_p:
                        if w.next_cell in visited:
                            pen.tick_frame(self)
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
                pen.tick_frame(self)

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

        top_row = [Cell(0, y) for y in range(0, maze.ncols)]
        top_walls = [Wall(c, Side.WEST) for c in top_row]

        # Clear the top row
        maze.set_walls(*top_walls, is_present=False)
        pen.update_cells(*top_row, state=CellState.NORMAL)
        pen.update_walls(*top_walls)

        active: List[Wall] = []

        for row in range(1, maze.nrows):

            for col in range(0, maze.ncols):
                cell = Cell(row, col)
                break_north = maze.random.randint(0, 1)
                if col == maze.ncols - 1 or break_north:
                    pen.update_cells(cell, state=CellState.NORMAL)

                    # cleanup active set
                    active.append(cell.wall(Side.WEST))
                    (cell, _) = maze.random.choice(active)
                    north_wall = Wall(cell, Side.NORTH)
                    _break_wall(north_wall, pen)
                    active.clear()
                else:
                    east_wall = Wall(cell, Side.EAST)
                    _break_wall(east_wall, pen)
                    pen.update_cells(cell, east_wall.next_cell, state=CellState.NORMAL)
                    active.append(east_wall)

                pen.tick_frame(self)



class _KruskalConnectedComp(object):
    """Data structure used to keep track of connectivity between cells.
       2 cells are connected if their KTree share the same root.

       This needs fast is_connected, and connect. This implementation is
       amortized O(1) for both, I think (paths to the root are explored
       at most once, the __root is relinked for subsequent uses).
    """


    def __init__(self):
        self.__root: _KruskalConnectedComp = self


    def root(self, replacement=None):
        r = self
        to_update = []
        while r.__root is not r:
            to_update.append(r)
            r = r.__root

        real_root = replacement or r
        r.__root = real_root

        for tree in to_update:
            tree.__root = real_root

        return r


    def is_connected(self, tree: '_KruskalConnectedComp'):
        return self is tree or self.root() is tree.root()


    def connect(self, tree: '_KruskalConnectedComp'):
        tree.root(replacement=self)


class KruskalGenerate(GenerationAlgo):

    def generate(self, pen: GridPen) -> None:
        maze = pen.maze

        # all edges of the maze
        edges = [
            w
            for cell in maze.all_cells()
            for w in [cell.wall(Side.WEST), cell.wall(Side.NORTH)]
        ]

        maze.random.shuffle(edges)

        # 2D array of tree sets
        sets = [[_KruskalConnectedComp() for _ in range(maze.ncols)] for _ in range(maze.nrows)]


        def set_of(cell) -> _KruskalConnectedComp:
            return sets[cell.row][cell.col]


        # kruskal
        while len(edges) > 0:
            wall = edges.pop()
            if wall.next_cell not in maze:
                continue
            (set1, set2) = set_of(wall.cell), set_of(wall.next_cell)

            if not set1.is_connected(set2):
                set1.connect(set2)

                _break_wall(wall, pen)
                pen.update_cells(wall.cell, wall.next_cell, state=CellState.NORMAL)

                pen.tick_frame(self)


class _EllerConnectedComp(_KruskalConnectedComp):
    """
    One connected component for the eller algorithm. This only cares for one
    row at a time. It needs fast enumeration of all cells in the CC, a fast
    inclusion test, and fast merge operation.
    """


    def __init__(self):
        super().__init__()
        self.__cells: List[Cell] = []


    def add(self, item: Cell):
        self.__cells.append(item)


    def connect(self, other: '_EllerConnectedComp'):
        # after this, other has a reference to self, not the reverse
        super().connect(other)
        self.__cells.extend(other.__cells)
        other.__cells = self.__cells


    def cells_in_row(self):
        return self.__cells


    def clear_row(self):
        self.__cells.clear()



class EllerGen(GenerationAlgo):

    def generate(self, pen: GridPen) -> None:
        maze = pen.maze
        random = maze.random

        # all edges of the maze
        edges = [
            w
            for cell in maze.all_cells()
            for w in [cell.wall(Side.WEST), cell.wall(Side.NORTH)]
        ]

        maze.random.shuffle(edges)

        # elements are the connected component of the cell
        cur_row: List[_EllerConnectedComp] = [_EllerConnectedComp() for _ in range(maze.ncols)]
        next_row: List[Optional[_EllerConnectedComp]] = [None for _ in range(maze.ncols)]

        for row in range(maze.nrows):

            # randomly break east walls in the same row
            for col in range(maze.ncols - 1):
                cur_cell = Cell(row, col)

                pen.update_cells(cur_cell, state=CellState.NORMAL)

                cur_cc = cur_row[col]
                next_cc = cur_row[col + 1]

                cur_cc.add(cur_cell)
                if cur_cc.is_connected(next_cc):
                    if cur_cc is not next_cc:
                        cur_row[col + 1] = cur_cc  # remove subcomponents, they don't matter
                elif row == maze.nrows - 1 or random.randint(0, 1):
                    _break_wall(cur_cell.wall(Side.EAST), pen)
                    cur_cc.connect(next_cc)
                    cur_row[col + 1] = cur_cc  # remove subcomponents, they don't matter

                pen.tick_frame(self)

            # handle last cell in row
            last_cell = Cell(row, maze.ncols - 1)
            cur_row[maze.ncols - 1].add(last_cell)
            pen.update_cells(last_cell, state=CellState.NORMAL)

            pen.tick_frame(self)

            if row == maze.nrows - 1:
                break

            # break some vertical walls to connect this row to the next
            done_cc = set([])

            for col in range(maze.ncols):
                cur_cc = cur_row[col]

                if cur_cc.root() not in done_cc:
                    done_cc.add(cur_cc.root())

                    cc_cells_in_row = cur_cc.cells_in_row()

                    # break at least 1 wall
                    for c in random.sample(cc_cells_in_row, random.randint(1, len(cc_cells_in_row))):
                        _break_wall(c.wall(Side.SOUTH), pen)
                        next_row[c.col] = cur_cc
                        pen.tick_frame(self)

                    cur_cc.clear_row()

            # finish the row by assigning fresh CCs to the next rows
            for col in range(maze.ncols):
                if not next_row[col]:
                    next_row[col] = _EllerConnectedComp()

            tmp = cur_row
            cur_row = next_row
            next_row = tmp
            for col in range(maze.ncols):
                next_row[col] = None

        # last row: connect every disjoint CC
        row = maze.nrows - 1
        for col in range(maze.ncols - 1):
            cur_cell = Cell(row, col)

            pen.update_cells(cur_cell, state=CellState.NORMAL)

            cur_cc = cur_row[col]
            next_cc = cur_row[col + 1]

            cur_cc.add(cur_cell)
            if cur_cc.is_connected(next_cc):
                if cur_cc is not next_cc:
                    cur_row[col + 1] = cur_cc  # remove subcomponents, they don't matter
            elif random.randint(0, 1):
                _break_wall(cur_cell.wall(Side.EAST), pen)
                cur_cc.connect(next_cc)
                cur_row[col + 1] = cur_cc  # remove subcomponents, they don't matter

            pen.tick_frame(self)
