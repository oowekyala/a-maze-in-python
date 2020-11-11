from amaze.model import *
from amaze.viz import *
from random import Random
from typing import Callable, List, Tuple, NamedTuple, Set, Generic, TypeVar
from collections import namedtuple
from queue import PriorityQueue
from abc import abstractmethod, ABCMeta



class SolverAlgo(metaclass=ABCMeta):

    @abstractmethod
    def solve(self, pen: GridPen) -> None:
        """
        Find the path from maze.start_cell to maze.end_cell and use the pen to display it.

        :param pen:             Pen to draw the generation (contains the maze)
        """
        pass



# TODO remove this shit
# TODO A*
class Heuristic(metaclass=ABCMeta):

    @abstractmethod
    def pick_path(self, maze: Maze, cell: Cell, walls: List[Wall]) -> (Wall, List[Wall]):
        """
        Pick the wall to cross at a junction with the given choices. Returns
        the wall and the list without the walls.

        :param maze:            Maze
        :param cell:            Cell of the crossroad (wall.cell for wall in walls)
        :param walls:           Available choices
        """
        pass



def best_by(target: Cell, walls: List[Wall], cost_fun: Callable[[Cell, Cell], int]) -> (Wall, int, int):
    """Minimizes the metric"""
    best_cost: Optional[int] = None
    best_wall = None
    best_i = None

    for i, wall in enumerate(walls):
        cost = cost_fun(wall.next_cell, target)
        if not best_cost or best_cost > cost:
            best_cost = cost
            best_wall = wall
            best_i = i

    return best_wall, best_cost, best_i



class ManhattanDistance(Heuristic):

    @staticmethod
    def manhattan(c1: Cell, c2: Cell):
        return abs(c2.row - c1.row) + abs(c1.col - c2.col)


    def pick_path(self, maze: Maze, cell: Cell, walls: List[Wall]) -> (Wall, List[Wall]):
        (_, _, best_i) = best_by(maze.end_cell, walls, cost_fun=ManhattanDistance.manhattan)

        return walls.pop(best_i), walls



class NoHeuristic(Heuristic):

    def pick_path(self, maze: Maze, cell: Cell, walls: List[Wall]) -> (Wall, List[Wall]):
        return walls.pop(), walls



class ShuffleHeuristic(Heuristic):

    def __init__(self, seed: Optional[int] = None):
        self.random = Random(x=seed)


    def pick_path(self, maze: Maze, cell: Cell, walls: List[Wall]) -> (Wall, List[Wall]):
        i = self.random.randrange(0, len(walls))
        return walls.pop(i), walls


class NoSolver(SolverAlgo):

    def solve(self, pen: GridPen) -> None:
        pass


class DfsSolver(SolverAlgo):

    def __init__(self, heuristic: Heuristic = ManhattanDistance()):
        self.heuristic = heuristic


    def solve(self, pen: GridPen, visited: Cell.CellSet = None) -> None:
        maze = pen.maze
        if not visited:
            visited = maze.new_cell_set(False)
        stack = []
        cell = maze.start_cell

        pen.update_cells(cell, state=CellState.BEST_PATH)

        while cell != maze.end_cell:
            visited += cell

            walls: List[Wall] = maze.walls_around(cell, only_passages=True, blacklist=visited)

            if len(walls) == 0:
                # prev_wall.next_cell == cell on first iteration
                while len(stack) > 0 and len(walls) == 0:
                    (prev_wall, others) = stack.pop()
                    pen.paint_wall_path(prev_wall, state=CellState.IGNORED)
                    pen.tick_frame(self)

                    walls = [w for w in others if w.next_cell not in visited]

                    if len(walls) == 0:
                        pen.update_walls(*others, state=CellState.IGNORED)
                        continue

                assert len(walls) > 0, "Unreachable end cell"

            # choose a random passage
            (next_wall, walls) = self.heuristic.pick_path(maze, cell, walls)
            stack.append((next_wall, walls))
            cell = next_wall.next_cell

            pen.paint_wall_path(next_wall, state=CellState.BEST_PATH)
            pen.paint_wall_path(*walls, state=CellState.ACTIVE)
            pen.tick_frame(self)



class BfsSolver(SolverAlgo):

    def solve(self, pen: GridPen) -> None:
        maze = pen.maze

        visited = maze.new_cell_set(False)
        queue = []
        queue2 = []
        cell = maze.start_cell

        pen.update_cells(cell, state=CellState.BEST_PATH)

        while cell != maze.end_cell:
            if cell not in visited:

                visited += cell

                pen.update_cells(cell, state=CellState.IGNORED)

                new_walls: List[Wall] = maze.walls_around(cell, only_passages=True, blacklist=visited)
                queue2.extend(new_walls)

                # pen.paint_wall_path(*new_walls, state=CellState.BEST_PATH)

            if len(queue) == 0:
                assert len(queue2) > 0, "Unreachable end cell"

                pen.paint_wall_path(*queue2, state=CellState.BEST_PATH)

                # swap queues
                tmp = queue
                queue = queue2
                queue2 = tmp

                # algo ticks correspond to one step of the whole frontier
                pen.tick_frame(self)

            next_wall = queue.pop(0)

            pen.update_walls(next_wall, state=CellState.IGNORED)
            cell = next_wall.next_cell

        pen.tick_frame(self)




class HandRuleSolver(SolverAlgo):

    def __init__(self, is_right_hand_rule: bool = True):
        self.right_hand = is_right_hand_rule


    def solve(self, pen: GridPen) -> None:
        maze = pen.maze

        cell = maze.start_cell
        pen.update_cells(cell, state=CellState.ACTIVE)

        # number of times the cell has been stepped on.
        num_step = {cell: 1}

        # The orientation depends on the last turn you took
        # Eg if you're looking down (towards Side.SOUTH), your right-hand is at Side.WEST, your back is Side.NORTH, etc
        # The orientation map can be read like so, eg for the right-hand rule:
        # Whatever your orientation, for the right-hand rule, on each cell, you'll prefer turning right
        # if it's free, then in front of you, then left, then go back. If you're looking in direction `s`,
        # `orientation_map[s]` is the index at which your right-hand is in `sides`, the following sides in
        # the list (wrapping around) are your next choices in order

        if self.right_hand:
            sides = [Side.EAST, Side.NORTH, Side.WEST, Side.SOUTH]  # counter-clockwise
            orientation_map = {Side.NORTH: 0, Side.EAST: 3, Side.SOUTH: 2, Side.WEST: 1}
        else:
            sides = [Side.WEST, Side.NORTH, Side.EAST, Side.SOUTH]  # clockwise
            orientation_map = {Side.NORTH: 0, Side.EAST: 1, Side.SOUTH: 2, Side.WEST: 3}

        num_sides = 4
        orientation = 0  # index in the list

        path_len = 0
        while cell != maze.end_cell:

            next_wall = None
            for i in range(num_sides):
                next_side = sides[(orientation + i) % num_sides]
                next_wall = cell.wall(next_side)
                if not maze.has_wall(next_wall):
                    orientation = orientation_map[next_side]  # yeah we could use modulos...
                    break

            assert next_wall is not None

            cell = next_wall.next_cell

            # c in {0,1,2,3}
            # if c == 0, the cell is on the best path
            c = num_step.get(cell, 0)
            num_step[cell] = c + 1

            state = CellState.BEST_PATH if c == 0 else CellState.IGNORED
            pen.paint_wall_path(next_wall, bias_prev=True, state=state)
            pen.tick_frame(self)
            path_len += 1




class DeadEndFillingSolver(SolverAlgo):

    def solve(self, pen: GridPen) -> None:
        maze = pen.maze

        filled = maze.new_cell_set()
        while True:
            # Scan maze to find dead ends

            def is_dead_end(c, walls):
                return c != maze.end_cell and c != maze.start_cell and len(walls) == 1

            dead_ends = [(c, walls)
                         for c in maze.all_cells()
                         if c not in filled
                         for walls in [maze.walls_around(c, only_passages=True, blacklist=filled)]
                         if is_dead_end(c, walls)
                         ]

            if len(dead_ends) == 0:
                break

            for c, walls in dead_ends:
                # fill up the dead end
                while is_dead_end(c, walls):
                    wall, = walls
                    pen.update_cells(c, state=CellState.IGNORED)
                    pen.update_walls(wall, state=CellState.IGNORED)
                    filled += c

                    pen.tick_frame(self)

                    c = wall.next_cell
                    walls = maze.walls_around(c, only_passages=True, blacklist=filled)

        # use the dfs solver to trace the best path
        DfsSolver(heuristic=NoHeuristic()).solve(pen, visited=filled)



Infty = 2 ** 10_000



class AStarSolver(SolverAlgo):

    def solve(self, pen: GridPen) -> None:
        maze = pen.maze
        h: Callable[[Cell], int] = lambda c: ManhattanDistance.manhattan(maze.end_cell, c)

        open_set = PriorityQueue()

        # For node n, cameFrom[n] is the wall immediately preceding it on the cheapest path from start
        # to n currently known.
        came_from: Dict[Cell, Wall] = {}
        # For node n, g_score[n] is the cost of the cheapest path from start to n currently known.
        g_score = {maze.start_cell: 0}

        # For node n, f_score[n] := g_score[n] + h(n). f_score[n] represents our current best guess as to
        # how short a path from start to finish can be if it goes through n.
        f_score = {maze.start_cell: h(maze.start_cell)}


        def edge_weight(wall: Wall) -> int:
            return 1 if not maze.has_wall(wall) else Infty


        def paint_path(current: Cell):
            while current in came_from.keys():
                # rebuilds the path in reverse
                w: Wall = came_from[current]
                pen.paint_wall_path(w, state=CellState.BEST_PATH)
                current = w.cell
                pen.tick_frame(self)

            pen.update_cells(current, state=CellState.BEST_PATH)
            pen.tick_frame(self)


        def push(ncell: Cell):
            f = f_score[ncell]
            open_set.put((f, ncell))


        def is_not_in_open_set(cell: Cell):
            for (_, c) in open_set.queue:
                if c == cell:
                    return False

            return True


        push(maze.start_cell)

        while open_set.qsize() > 0:
            (cur_f_score, cur) = open_set.get()
            if cur == maze.end_cell:
                paint_path(cur)
                break

            walls = maze.walls_around(cur)

            for wall in walls:
                neighbor = wall.next_cell
                # tentative_gScore is the distance from start to the neighbor through current
                tentative_g_score = g_score.get(cur, Infty) + edge_weight(wall)
                if tentative_g_score < g_score.get(neighbor, Infty):
                    # This path to neighbor is better than any previous one. Record it!
                    came_from[neighbor] = wall
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = g_score.get(neighbor, Infty) + h(neighbor)
                    if is_not_in_open_set(neighbor):
                        push(neighbor)
                        pen.paint_wall_path(wall, state=CellState.ACTIVE, gradient=f_score[neighbor])
                        pen.tick_frame(self)
