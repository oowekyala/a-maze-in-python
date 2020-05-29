from abc import abstractmethod, ABCMeta

from maze.util import *
from maze import Maze



@unique
class CellState(Enum):
    ON_PATH = auto()  # Current path
    IGNORED = auto()  # Abandoned path
    BLANK = auto()

    START = auto()
    END = auto()



class GridPen(metaclass=ABCMeta):

    @abstractmethod
    def update_cell(self, cell: Cell, state: CellState) -> None:
        """Update the state of a cell (and repaint)"""
        pass


    @abstractmethod
    def update_wall(self, wall: Wall, active: bool) -> None:
        """Update a wall (and repaint)"""
        pass


    @abstractmethod
    def repaint_grid(self, maze: Maze):
        """Repaint the whole grid"""
        pass


    @staticmethod
    def __noop_pen() -> 'GridPen':
        class __NoopPen(GridPen):

            def update_cell(self, cell: Cell, state: CellState) -> None:
                pass


            def update_wall(self, wall: Wall, active: bool) -> None:
                pass


            def repaint_grid(self, maze: Maze):
                pass

        return __NoopPen()
