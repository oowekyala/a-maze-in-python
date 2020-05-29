from maze.model import *
from abc import abstractmethod, ABCMeta
from enum import Enum, auto, unique

@unique
class CellState(Enum):
    ACTIVE = auto()  # Current path
    BEST_PATH = auto()  # Best path
    IGNORED = auto()  # Abandoned path
    BLANK = auto()
    WALL = auto()

    START = auto()
    END = auto()



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



class GridPen(metaclass=ABCMeta):

    def __init__(self, maze: 'Maze'):
        self.__maze = maze


    @property
    def maze(self):
        return self.__maze

    @abstractmethod
    def update_cell(self, cell: Cell, state: CellState) -> None:
        """Update the state of a cell (and repaint)"""
        pass

    def reset_maze(self, maze: 'Maze'):
        """Repaint the whole grid, the maze may have different dimensions (resize window)"""
        self.__maze = maze

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

            def update_cell(self, cell: Cell, state: CellState) -> None:
                pass

        return __NoopPen()
