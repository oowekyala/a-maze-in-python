from typing import Dict

import pygame

from maze import Maze
from maze.viz import *



class PyGamePen(GridPen):
    CELL_WIDTH = CELL_HEIGHT = 7
    # Margin separating each cell
    WALL_WIDTH = 1
    BUTTON_HEIGHT = 0  # TODO

    CORRIDOR_COLOR = Color.WHITE
    WALL_COLOR = Color.BLACK

    state_colors: Dict[CellState, Color] = {
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
        self.screen = self.__size_window(maze)


    def update_cell(self, cell: Cell, state: CellState) -> None:
        pygame.draw.rect(
            self.screen,
            PyGamePen.state_colors[state],
            [
                (PyGamePen.WALL_WIDTH + PyGamePen.CELL_WIDTH) * cell.x + PyGamePen.WALL_WIDTH,
                (PyGamePen.WALL_WIDTH + PyGamePen.CELL_HEIGHT) * cell.y + PyGamePen.WALL_WIDTH,
                PyGamePen.CELL_WIDTH,
                PyGamePen.CELL_HEIGHT
            ]
        )
        pygame.event.pump()


    def update_wall(self, wall: Wall, active: bool) -> None:
        # TODO off-by-ones
        if wall.side.direction() == Direction.VERTICAL:
            rect = [
                (PyGamePen.WALL_WIDTH + PyGamePen.CELL_WIDTH) * wall.x + PyGamePen.WALL_WIDTH,
                (PyGamePen.WALL_WIDTH + PyGamePen.CELL_HEIGHT) * wall.y + PyGamePen.WALL_WIDTH,
                PyGamePen.WALL_WIDTH,
                PyGamePen.CELL_HEIGHT
            ]
        else:
            rect = [
                (PyGamePen.WALL_WIDTH + PyGamePen.CELL_WIDTH) * wall.x + PyGamePen.WALL_WIDTH,
                (PyGamePen.WALL_WIDTH + PyGamePen.CELL_HEIGHT) * wall.y + PyGamePen.WALL_WIDTH,
                PyGamePen.CELL_WIDTH,
                PyGamePen.WALL_WIDTH
            ]

        pygame.draw.rect(
            self.screen,
            PyGamePen.WALL_COLOR if active else PyGamePen.CORRIDOR_COLOR,
            rect
        )
        pass


    def reset_maze(self, maze: Maze):
        prev_maze = self.maze
        super().reset_maze(maze)
        if prev_maze is not maze:
            self.screen = PyGamePen.__size_window(maze)
        # TODO draw entire maze

    @staticmethod
    def __size_window(maze: Maze) -> pygame.display.Surface:
        # Set the width and height of the screen [width, height]

        def grid_size(dim: int):
            return dim * (PyGamePen.CELL_WIDTH + PyGamePen.WALL_WIDTH) + PyGamePen.WALL_WIDTH * 2


        screen_width = grid_size(maze.width)
        grid_height = grid_size(maze.height)
        screen_height = grid_height + PyGamePen.BUTTON_HEIGHT * 3
        window_size = (screen_width, screen_height)

        return pygame.display.set_mode(window_size)



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
