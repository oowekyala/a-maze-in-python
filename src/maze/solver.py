from maze.model import *
from maze.gen import *
from maze.viz import *
import random, time
from typing import Callable, List, Tuple
from abc import abstractmethod, ABCMeta



class SolverAlgo(metaclass=ABCMeta):

    @abstractmethod
    def solve(self, maze: Maze, pen: GridPen) -> None:
        """
        Find the path from maze.start_cell to maze.end_cell and use the pen to display it.

        :param maze:            Receiver maze
        :param pen:             Pen to draw the generation
        """
        pass



class DfsSolver(SolverAlgo):

    def solve(self, maze: Maze, pen: GridPen) -> None:

        visited = maze.new_cell_set(False)
        stack = []
        cell = maze.start_cell

        pen.update_cells(cell, state=CellState.BEST_PATH)

        while cell != maze.end_cell:
            time.sleep(0.02)
            visited += cell

            walls: List[Wall] = maze.walls_around(cell, only_passages=True, blacklist=visited)

            if len(walls) == 0:
                # prev_wall.next_cell == cell on first iteration
                while len(stack) > 0 and len(walls) == 0:
                    (prev_wall, others) = stack.pop()
                    pen.paint_wall_path(prev_wall, state=CellState.IGNORED)

                    walls = [w for w in others if w.next_cell not in visited]

                    if len(walls) == 0:
                        pen.update_walls(*others, state=CellState.IGNORED)
                        continue

                assert len(walls) > 0, "Unreachable end cell"

            # choose a random passage
            next_wall: Wall = walls.pop()
            stack.append((next_wall, walls))
            cell = next_wall.next_cell

            pen.paint_wall_path(next_wall, state=CellState.BEST_PATH)
            pen.paint_wall_path(*walls, state=CellState.ACTIVE)
