from abc import abstractmethod, ABCMeta
from typing import List

from maze.viz import *




class GenerationAlgo(metaclass=ABCMeta):

    @abstractmethod
    def generate(self, pen: GridPen) -> None:
        """
        Generate the maze by breaking some walls. Initially all walls are
        set.

        :param pen:             Pen to draw the generation (contains the maze)
        """
        pass



def apply_gen(gen: GenerationAlgo, pen: GridPen):
    pen.maze.reset()
    pen.reset_maze(maze=pen.maze)
    gen.generate(pen=pen)



def _break_wall(wall: Wall, pen: GridPen):
    pen.maze.set_wall(wall, is_present=False)
    pen.update_walls(wall)



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
    """


    def generate(self, pen: GridPen) -> None:
        maze: Maze = pen.maze

        in_maze: Cell.CellSet = maze.new_cell_set(False)
        in_path: Cell.CellSet = maze.new_cell_set(False)

        seed = maze.rand_cell()
        in_maze += seed  # TODO seed should be bound to the random source

        pen.update_cells(seed, state=CellState.NORMAL)

        # TODO add seeds. Problem is, each seed forms an independent mazes
        # seeds = [seed]
        # for i in range((maze.width * maze.height) // (50 * 50)):
        #     # big maze, add seeds
        #     seed = maze.rand_cell()
        #     in_maze += seed
        #     seeds.append(seed)
        #
        # pen.update_cells(*seeds, state=CellState.NORMAL)

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
