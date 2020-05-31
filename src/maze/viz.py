from maze.model import *
from abc import abstractmethod, ABCMeta
from enum import Enum, auto, unique
from typing import Iterable, Union, Callable, Dict



@unique
class CellState(Enum):
    ACTIVE = auto()
    BEST_PATH = auto()
    IGNORED = auto()
    NORMAL = auto()
    UNDISCOVERED = auto()



@unique
class CellKind(Enum):
    REGULAR = auto()
    START = auto()
    END = auto()

class WallState(Enum):
    ACTIVE = auto()
    OFF = auto()
    ON = auto()

@unique
class Color(Enum):
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    GREEN = (0, 255, 0)
    RED = (255, 0, 0)
    BLUE = (0, 0, 255)
    LIGHT_BLUE = (0, 111, 255)
    ORANGE = (255, 128, 0)
    PURPLE = (128, 0, 255)
    YELLOW = (255, 255, 0)
    GREY = (143, 143, 143)
    BROWN = (186, 127, 50)
    DARK_GREEN = (0, 128, 0)
    DARKER_GREEN = (0, 50, 0)
    DARK_BLUE = (0, 0, 128)



def StateSelector(i, o):
    return Union[o, Callable[[i], Optional[o]], Dict[i, o]]



CellStateSelector = StateSelector(Cell, CellState)
WallStateSelector = StateSelector(Wall, WallState)



class GridPen(metaclass=ABCMeta):

    def __init__(self, maze: 'Maze'):
        self.__maze = maze


    @property
    def maze(self):
        return self.__maze


    @abstractmethod
    def update_cell(self, cell: Cell, state: CellStateSelector) -> None:
        """Update the state of a cell (and repaint)"""
        pass


    def update_wall(self, wall: Wall, state: WallStateSelector) -> None:
        pass


    def update_walls(self, walls: Iterable[Wall], state: WallStateSelector) -> None:
        for wall in walls:
            self.update_wall(wall, state)


    def update_cells(self, cells: Iterable[Cell], state: CellStateSelector, global_update: bool = False) -> None:
        """Batch update"""
        sel = self._state_selector(state)
        for c in cells:
            self.update_cell(c, sel(c))


    def reset_maze(self, maze: 'Maze'):
        """Repaint the whole grid, the maze may have different dimensions (resize window)"""
        self.__maze = maze


    def _state_selector(self, state):
        if isinstance(state, dict):
            return lambda c: state.get(c, None)
        elif isinstance(state, Callable):
            return state
        else:
            return lambda c: state


    @abstractmethod
    def paint_everything(self):
        """"""
        pass


    @staticmethod
    def __noop_pen(maze: 'Maze') -> 'GridPen':
        class __NoopPen(GridPen):

            def __init__(self):
                super().__init__(maze)


            def paint_everything(self):
                pass


            def update_cells(self, cells, state, global_update: bool = False) -> None:
                pass


            def update_walls(self, walls, state) -> None:
                pass


            def update_cell(self, cell, state):
                pass

        return __NoopPen()
