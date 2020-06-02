from abc import abstractmethod, ABCMeta
from typing import Callable, Dict, TypeVar
from enum import Enum, auto, unique
from maze.model import *



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


@unique
class Color(Enum):
    BLACK = "black"
    WHITE = "white"
    GREEN = "green"
    RED = "red"
    BLUE = "blue"
    ORANGE = "orange"
    PURPLE = "purple"
    YELLOW = "yellow"
    GREY = "darkslategrey"
    BROWN = "brown"


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
    def maze(self):
        return self.__maze


    def update_walls(self,
                     *walls: Wall,
                     state: CellState = CellState.NORMAL,
                     global_update: bool = False) -> None:
        pass


    def algo_tick(self, algo_instance):
        """Record one step in the algorithm currently executing. This may be used to slow down some algorithms."""
        pass

    def paint_wall_path(self, *walls: Wall, state: CellState):
        self.update_cells(*[w.next_cell for w in walls], state=state)
        self.update_walls(*walls, state=state)


    def update_cells(self, *cells: Cell, state: CellStateSelector, global_update: bool = False) -> None:
        """Batch update"""
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
        """Repaint the whole grid, the maze may have different dimensions (resize window)"""
        self.__maze = maze
        self.__reset_kind_map()


    def __reset_kind_map(self):
        self.__cell_kind_map = {
            self.maze.end_cell: CellKind.END,
            self.maze.start_cell: CellKind.START,
            CellKind.END: self.maze.end_cell,
            CellKind.START: self.maze.start_cell,
        }


    @staticmethod
    def noop_pen(maze: Maze) -> 'GridPen':
        class __NoopPen(GridPen):

            def __init__(self):
                super().__init__(maze)

            def update_cells(self, *args, **kwargs) -> None:
                pass


            def update_walls(self, *args, **kwargs) -> None:
                pass


            def paint_wall_path(self, *args, **kwargs) -> None:
                pass

        return __NoopPen()
