from typing import Dict

from pygame import Rect
import pygame

from maze.viz import *
from maze.gen import *
from maze.model import *



class PyGamePen(GridPen):
    CELL_WIDTH = 8
    CELL_HEIGHT = CELL_WIDTH
    # Margin separating each cell
    MARGIN = 0
    BUTTON_HEIGHT = 0  # TODO

    CORRIDOR_COLOR = Color.WHITE
    WALL_COLOR = Color.BLACK

    state_colors = {
        CellState.BLANK: CORRIDOR_COLOR,
        CellState.WALL: WALL_COLOR,

        CellState.IGNORED: Color.YELLOW,
        CellState.BEST_PATH: Color.BLUE,
        CellState.ACTIVE: Color.GREEN,

        CellState.START: Color.RED,
        CellState.END: Color.RED,
    }


    def __init__(self, maze: Maze):
        super().__init__(maze)
        pygame.init()
        self.clock = pygame.time.Clock()
        self.__screen = PyGamePen.__size_window(maze)
        self.reset_maze(maze)


    @staticmethod
    def cell_rect(cell: Cell) -> pygame.Rect:
        return Rect(
            (PyGamePen.MARGIN + PyGamePen.CELL_WIDTH) * cell.y + PyGamePen.MARGIN,
            (PyGamePen.MARGIN + PyGamePen.CELL_HEIGHT) * cell.x + PyGamePen.MARGIN,
            PyGamePen.CELL_WIDTH,
            PyGamePen.CELL_HEIGHT
        )


    def update_cell(self, cell: Cell, state: CellState) -> None:
        rect = PyGamePen.cell_rect(cell)
        color = PyGamePen.state_colors[state].value

        pygame.draw.rect(self.__screen, color, rect)
        pygame.display.update(rect)
        pygame.event.pump()


    def update_cells(self,
                     cells: Iterable[Cell],
                     state: Union[CellState, Callable[[Cell], Optional[CellState]]],
                     global_update: bool = False) -> None:
        area_to_update: Optional[Rect] = None
        for cell in cells:
            if isinstance(state, CellState):
                s = state
            else:
                s = state(cell)

            if not s:
                continue

            color = PyGamePen.state_colors[s].value
            rect = PyGamePen.cell_rect(cell)
            pygame.draw.rect(self.__screen, color, rect)

            if not global_update:
                if area_to_update:
                    area_to_update = area_to_update.union(rect)
                else:
                    area_to_update = rect

        if area_to_update:
            pygame.display.update(area_to_update)
            pygame.event.pump()
        elif global_update:
            pygame.display.flip()
            pygame.event.pump()


    def paint_everything(self):
        pygame.display.flip()
        self.clock.tick(60)  # limit to 60 fps


    def reset_maze(self, maze: Maze):
        prev_maze = self.maze
        super().reset_maze(maze)
        if prev_maze is not maze:
            self.__screen = PyGamePen.__size_window(maze)

        self.__draw_entire_maze(maze)


    def __draw_entire_maze(self, maze: Maze):
        self.__screen.fill(PyGamePen.CORRIDOR_COLOR.value)
        maze.draw_regular_tiles(self)
        self.update_cell(maze.start_cell, CellState.START)
        self.update_cell(maze.end_cell, CellState.END)


    @staticmethod
    def __size_window(maze: Maze) -> pygame.Surface:
        # Set the width and height of the screen [width, height]

        screen_width = PyGamePen.__grid_size(maze.width)
        grid_height = PyGamePen.__grid_size(maze.height)
        screen_height = grid_height + PyGamePen.BUTTON_HEIGHT * 3
        window_size = (screen_width, screen_height)

        return pygame.display.set_mode(window_size)


    @staticmethod
    def __grid_size(dim: int):
        return dim * (PyGamePen.CELL_WIDTH + PyGamePen.MARGIN) + PyGamePen.MARGIN * 2


def get_mouse_cell():
    # User moves the mouse. Get the position
    pos = pygame.mouse.get_pos()

    # Change the x/y screen coordinates to grid coordinates
    column = pos[0] // (PyGamePen.CELL_WIDTH + PyGamePen.MARGIN)
    row = pos[1] // (PyGamePen.CELL_HEIGHT + PyGamePen.MARGIN)
    return Cell(x=column, y=row)


# -------- Main Program Loop -----------
def loop(pen: GridPen):
    maze = pen.maze
    drag_start_point = drag_end_point = False
    algo_was_run = False

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return None

            elif event.type == pygame.MOUSEBUTTONDOWN:
                clicked: Cell = get_mouse_cell()
                # If click is inside grid
                if clicked in maze and not algo_was_run:
                    if clicked == maze.start_cell:
                        drag_start_point = True
                    elif clicked == maze.end_cell:
                        drag_end_point = True


            elif event.type == pygame.MOUSEBUTTONUP:
                # Turn off all mouse drags if mouse Button released
                drag_end_point = drag_start_point = False

            elif event.type == pygame.MOUSEMOTION:

                # Boolean values saying whether left, middle and right mouse buttons are currently pressed
                left, middle, right = pygame.mouse.get_pressed()

                # Sometimes we get stuck in this loop if the mousebutton is released while not in the pygame screen
                # This acts to break out of that loop
                if not left:
                    drag_end_point = drag_start_point = False
                    continue

                mouse_cell: Cell = get_mouse_cell()

                # Turn mouse_drag off if mouse goes outside of grid
                if mouse_cell not in maze:
                    drag_end_point = drag_start_point = False
                    continue

                # Move the start point
                if drag_start_point:
                    pen.update_cell(maze.start_cell, CellState.BLANK)
                    maze.start_cell = mouse_cell
                    pen.update_cell(maze.start_cell, CellState.START)

                    if algo_was_run:
                        pen.reset_maze(maze)
                        algo_was_run = False

                elif drag_end_point:
                    pen.update_cell(maze.end_cell, CellState.BLANK)
                    maze.end_cell = mouse_cell
                    pen.update_cell(maze.end_cell, CellState.END)

                    if algo_was_run:
                        pen.reset_maze(maze)
                        algo_was_run = False

        pen.paint_everything()



def launch():
    maze = Maze(nrows=100, ncols=100)
    pen = PyGamePen(maze)
    maze.apply_gen(WilsonGenerate(), pen=pen)
    print(maze)
    loop(pen)



launch()
