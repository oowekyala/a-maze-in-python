import random
from typing import Callable, List, Tuple

from maze import Maze
from maze.viz import *



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
