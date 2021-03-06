# Amaze - maze visualisation
# Copyright (C) 2020 Clément Fournier
# Some rights reserved. See LICENSE, or <https://www.gnu.org/licenses/gpl-3.0.html>

from abc import abstractmethod, ABCMeta
from typing import Callable, Dict, TypeVar
from enum import Enum, auto, unique
from amaze.model import *



@unique
class CellState(Enum):
    ACTIVE = auto()
    BEST_PATH = auto()
    IGNORED = auto()
    NORMAL = auto()
    UNDISCOVERED = auto()



@unique
class CellKind(Enum):
    """The kind of a cell select the color palette for its states."""

    REGULAR = auto()
    START = auto()
    END = auto()
    # Wall kinds are internal and cannot be used for Cell
    WALL_ON = auto()
    WALL_OFF = auto()

C = TypeVar('C', Cell, Wall)
StateSelector = Union[CellState, Callable[[C], Optional[CellState]], Dict[C, (CellState)]]

CellStateSelector = StateSelector[Cell]
WallStateSelector = StateSelector[Wall]



def state_selector(state: StateSelector[C]) -> Callable[[C], Optional[CellState]]:
    if isinstance(state, dict):
        return lambda c: state.get(c, None)
    elif isinstance(state, Callable):
        return state
    else:
        return lambda c: state


class GridPen(metaclass=ABCMeta):

    def __init__(self, maze: Maze):
        self.__maze = maze
        self.__cell_kind_map = {}
        self.__reset_kind_map()


    @property
    def maze(self) -> Maze:
        return self.__maze



    def tick_frame(self, algo_instance, force_refresh=False):
        """Record one step in the algorithm currently executing.
           This update the screen with the updates done since the previous tick.

           When running with a speed factor above 100%, some ticks
           may be ignored to speed up execution. Use the force_refresh
           parameter to override this.
         """
        pass


    def paint_wall_path(self, *walls: Wall, state: CellState, bias_prev=False, gradient=0):
        """
        Paint a set of walls and their next cells.
        :param walls: Walls
        :param state: State
        :param gradient: An int, only applicable to ACTIVE state
        :return:
        """
        self.update_cells(*[(w.cell if bias_prev else w.next_cell) for w in walls], state=state, gradient=gradient)
        self.update_walls(*walls, state=state, gradient=gradient)


    def update_walls(self, *walls: Wall, state: CellState = CellState.NORMAL, global_update: bool = False, gradient=0, saturate_gradient=False) -> None:
        pass

    def update_cells(self, *cells: Cell, state: CellStateSelector, global_update: bool = False, gradient=0, saturate_gradient=False) -> None:
        pass


    def move_start_or_end(self, new_pos: Cell, kind: CellKind):
        if not kind:
            return
        assert kind != CellKind.REGULAR, "need START or END"

        old = self.__cell_kind_map[kind]
        if old == new_pos:
            return None

        if kind == CellKind.START:
            self.maze.start_cell = new_pos
        elif kind == CellKind.END:
            self.maze.end_cell = new_pos

        self.__reset_kind_map()

        self.update_cells(old, new_pos, state=CellState.NORMAL)


    def get_kind(self, cell: Cell):
        return self.__cell_kind_map.get(cell, CellKind.REGULAR)


    def reset_maze(self, maze: Maze):
        """Change the maze, it may have different dimensions (resize window)"""
        self.__maze = maze
        self.__reset_kind_map()


    def draw_entire_maze(self, cell_state: CellState, is_walled: bool = True):
        """Repaint the whole grid."""
        pass


    def __reset_kind_map(self):
        self.__cell_kind_map = {
            self.maze.end_cell: CellKind.END,
            self.maze.start_cell: CellKind.START,
            CellKind.END: self.maze.end_cell,
            CellKind.START: self.maze.start_cell,
        }


    @staticmethod
    def noop_pen(maze: Maze, tick_function: Callable = lambda: None) -> 'GridPen':
        class __NoopPen(GridPen):

            def __init__(self):
                super().__init__(maze)


            def tick_frame(self, *args, **kwargs):
                tick_function()


            def update_cells(self, *args, **kwargs) -> None:
                pass


            def update_walls(self, *args, **kwargs) -> None:
                pass


            def paint_wall_path(self, *args, **kwargs) -> None:
                pass

        return __NoopPen()
