from typing import Dict

from pygame import Rect
import pygame

from maze.viz import *
from maze.gen import *
from maze.model import *



class PyGamePen(GridPen):
    CELL_WIDTH = CELL_HEIGHT = 20
    # Margin separating each cell
    WALL_WIDTH = CELL_HEIGHT
    BUTTON_HEIGHT = 0  # TODO

    CORRIDOR_COLOR = Color.WHITE
    WALL_COLOR = Color.BLACK

    state_colors = {
        CellState.BLANK: CORRIDOR_COLOR,
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


    def update_cell(self, cell: Cell, state: CellState) -> None:
        pygame.draw.rect(
            self.__screen,
            PyGamePen.state_colors[state].value,
            [
                (PyGamePen.WALL_WIDTH + PyGamePen.CELL_WIDTH) * cell.x + PyGamePen.WALL_WIDTH,
                (PyGamePen.WALL_WIDTH + PyGamePen.CELL_HEIGHT) * cell.y + PyGamePen.WALL_WIDTH,
                PyGamePen.CELL_WIDTH,
                PyGamePen.CELL_HEIGHT
            ]
        )
        pygame.event.pump()


    def __rect_of_wall(self, wall: Wall):

        if wall.side == Side.LEFT or wall.side == Side.RIGHT:  # vertical walls
            (width, height) = (PyGamePen.WALL_WIDTH, PyGamePen.CELL_HEIGHT + PyGamePen.WALL_WIDTH)
        else:  # horizontal walls
            (width, height) = (PyGamePen.CELL_WIDTH + PyGamePen.WALL_WIDTH, PyGamePen.WALL_WIDTH)

        (left, top) = \
            (
                (PyGamePen.WALL_WIDTH + PyGamePen.CELL_WIDTH) * wall.x + PyGamePen.WALL_WIDTH,
                (PyGamePen.WALL_WIDTH + PyGamePen.CELL_HEIGHT) * wall.y + PyGamePen.WALL_WIDTH
            )

        if wall.side == Side.RIGHT:
            left += PyGamePen.CELL_WIDTH + PyGamePen.WALL_WIDTH
        elif wall.side == Side.BOT:
            top += PyGamePen.CELL_HEIGHT + PyGamePen.WALL_WIDTH

        return Rect(left, top, width, height)


    def update_wall(self, wall: Wall, active: bool) -> None:
        # TODO off-by-ones
        rect = self.__rect_of_wall(wall)

        pygame.draw.rect(
            self.__screen,
            (PyGamePen.WALL_COLOR if active else PyGamePen.CORRIDOR_COLOR).value,
            rect
        )
        pass


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
        maze.draw_walls(self)
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
        return dim * (PyGamePen.CELL_WIDTH + PyGamePen.WALL_WIDTH) + PyGamePen.WALL_WIDTH * 2


def get_mouse_cell():
    # User moves the mouse. Get the position
    pos = pygame.mouse.get_pos()

    # Change the x/y screen coordinates to grid coordinates
    column = pos[0] // (PyGamePen.CELL_WIDTH + PyGamePen.WALL_WIDTH)
    row = pos[1] // (PyGamePen.CELL_HEIGHT + PyGamePen.WALL_WIDTH)
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
    maze = Maze(nrows=5, ncols=6)
    pen = PyGamePen(maze)
    maze.apply_gen(DfsGenerate(), pen=pen)
    print(maze)
    loop(pen)



launch()
