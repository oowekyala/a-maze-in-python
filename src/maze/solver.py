from maze.model import *
from maze.viz import *
from random import Random
from typing import Callable, List, Tuple
from abc import abstractmethod, ABCMeta



class SolverAlgo(metaclass=ABCMeta):

    @abstractmethod
    def solve(self, pen: GridPen) -> None:
        """
        Find the path from maze.start_cell to maze.end_cell and use the pen to display it.

        :param pen:             Pen to draw the generation (contains the maze)
        """
        pass



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



class ManhattanDistance(Heuristic):

    @staticmethod
    def manhattan(c1: Cell, c2: Cell):
        return abs(c2.row - c1.row) + abs(c1.col - c2.col)


    @staticmethod
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


    def pick_path(self, maze: Maze, cell: Cell, walls: List[Wall]) -> (Wall, List[Wall]):
        (_, _, best_i) = ManhattanDistance.best_by(maze.end_cell, walls, cost_fun=ManhattanDistance.manhattan)

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



class DfsSolver(SolverAlgo):

    def __init__(self, heuristic: Heuristic = ManhattanDistance()):
        self.heuristic = heuristic


    def solve(self, pen: GridPen) -> None:
        maze = pen.maze

        visited = maze.new_cell_set(False)
        stack = []
        cell = maze.start_cell

        pen.update_cells(cell, state=CellState.BEST_PATH)

        while cell != maze.end_cell:
            pen.algo_tick(self)
            visited += cell

            walls: List[Wall] = maze.walls_around(cell, only_passages=True, blacklist=visited)

            if len(walls) == 0:
                # prev_wall.next_cell == cell on first iteration
                while len(stack) > 0 and len(walls) == 0:
                    (prev_wall, others) = stack.pop()
                    pen.paint_wall_path(prev_wall, state=CellState.IGNORED)
                    pen.algo_tick(self)

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



class BfsSolver(SolverAlgo):

    def solve(self, pen: GridPen) -> None:
        maze = pen.maze

        visited = maze.new_cell_set(False)
        queue = []
        queue2 = []
        cell = maze.start_cell

        pen.update_cells(cell, state=CellState.BEST_PATH)

        while cell != maze.end_cell:
            visited += cell

            pen.update_cells(cell, state=CellState.IGNORED)

            new_walls: List[Wall] = maze.walls_around(cell, only_passages=True, blacklist=visited)
            queue2.extend(new_walls)

            pen.paint_wall_path(*new_walls, state=CellState.BEST_PATH)

            if len(queue) == 0:
                assert len(queue2) > 0, "Unreachable end cell"

                # swap queues
                tmp = queue
                queue = queue2
                queue2 = tmp

                # algo ticks correspond to one step of the whole frontier
                pen.algo_tick(self)

            next_wall = queue.pop(0)

            pen.update_walls(next_wall, state=CellState.IGNORED)
            cell = next_wall.next_cell



class HandRuleSolver(SolverAlgo):

    def __init__(self, is_right_hand_rule: bool = True):
        self.right_hand = is_right_hand_rule


    def solve(self, pen: GridPen) -> None:
        maze = pen.maze

        cell = maze.start_cell
        pen.update_cells(cell, state=CellState.BEST_PATH)

        # The orientation depends on the last turn you took
        # Eg if you're looking down (towards Side.BOT), your right-hand is at Side.LEFT, your back is Side.TOP, etc
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

        while cell != maze.end_cell:
            pen.algo_tick(self)

            next_wall = None
            for i in range(num_sides):
                next_side = sides[(orientation + i) % num_sides]
                next_wall = cell.wall(next_side)
                if not maze.has_wall(next_wall):
                    orientation = orientation_map[next_side]  # yeah we could use modulos...
                    break

            assert next_wall is not None

            cell = next_wall.next_cell

            pen.paint_wall_path(next_wall, state=CellState.BEST_PATH)
