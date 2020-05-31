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

        while cell != maze.end_cell:
            time.sleep(0.5)
            visited += cell
            pen.update_cell(cell, CellState.BEST_PATH)

            walls: List[Wall] = maze.walls_around(cell, blacklist=visited)

            if len(walls) == 0:
                pen.update_cell(cell, CellState.IGNORED)
                while len(stack) > 0 and len(walls) == 0:
                    (cell, walls_p) = stack.pop()
                    if len(walls_p) == 0:
                        pen.update_cell(cell, CellState.IGNORED)
                        continue

                    walls = []
                    for w in walls_p:
                        if w.next_cell not in visited:
                            walls.append(w)

                if len(walls) == 0:
                    break

            # choose a random passage
            next_wall: Wall = next(w for w in walls if not maze.has_wall(w))

            walls.remove(next_wall)

            pen.update_cells([w.next_cell for w in walls], CellState.ACTIVE)
            stack.append((cell, walls))

            cell = next_wall.next_cell
