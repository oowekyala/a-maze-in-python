from typing import Dict

from pygame import Rect
import pygame

from maze.viz import *
from maze.gen import *
from maze.solver import *
from maze.model import *



def conv_color(color: Color) -> pygame.Color:
    return pygame.Color(color.value)



CELL_WIDTH = 5
CELL_HEIGHT = CELL_WIDTH  # Cells are square
MARGIN = 0  # Padding between cells

CORRIDOR_COLOR = Color.WHITE
WALL_COLOR = Color.BLACK

cell_colors: Dict[CellKind, Dict[CellState, Color]] = {
    CellKind.REGULAR: {
        CellState.ACTIVE: Color.GREEN,
        CellState.IGNORED: Color.YELLOW,
        CellState.BEST_PATH: Color.BLUE,
        CellState.NORMAL: CORRIDOR_COLOR,
        CellState.UNDISCOVERED: Color.GREY
    },
    CellKind.START: {s: Color.RED for s in list(CellState)},
    CellKind.END: {s: Color.ORANGE for s in list(CellState)},
}

cell_colors[CellKind.WALL_OFF] = {**cell_colors[CellKind.REGULAR], CellState.UNDISCOVERED: WALL_COLOR}
cell_colors[CellKind.WALL_ON] = {**cell_colors[CellKind.WALL_OFF], CellState.NORMAL: WALL_COLOR}



def _cell_rect(cell: Cell) -> pygame.Rect:
    return _rect(2 * cell.x + 1, 2 * cell.y + 1)



def _wall_rect(wall: Wall) -> pygame.Rect:
    ((x, y), side) = wall
    (x, y) = (2 * x + 1, 2 * y + 1)
    if side == Side.TOP:
        x -= 1
    elif side == Side.BOT:
        x += 1
    elif side == Side.LEFT:
        y -= 1
    elif side == Side.RIGHT:
        y += 1

    return _rect(x, y)



def _rect(x, y) -> pygame.Rect:
    return Rect(
        (MARGIN + CELL_WIDTH) * y + MARGIN,
        (MARGIN + CELL_HEIGHT) * x + MARGIN,
        CELL_WIDTH,
        CELL_HEIGHT
    )



class PyGamePen(GridPen):
    """
    Implementation of GridPen using pygame as a backend.
    """


    def __init__(self, maze: Maze, speed_factor: float = 1.0):
        super().__init__(maze)
        pygame.init()
        self.clock = pygame.time.Clock()
        self.speed_factor = max(speed_factor, 0.1)  # this uses the custom setter
        self.__screen = PyGamePen.__size_window(maze)
        self.__cell_kind_map = {}
        self.reset_maze(maze)


    @property
    def speed_factor(self):
        return self.__speed_factor


    @speed_factor.setter
    def speed_factor(self, sf: float):
        # A maze with many cells will show a higher framerate than a smaller maze for the same speed factor
        # Otherwise some algorithms would be impossibly slow in big mazes
        # The perceived "speed" depends on the algorithm
        # Eg generation algos that solve one cell per tick (eg dfs, before i added ticks to the backtracks)
        # will have a runtime proportional to the maze size
        # The `// 10` below normalizes the execution time of these algos to 10 seconds, given a speed factor of 1
        self.__speed_factor = max(sf, 0.01)
        self.__algo_framerate = max(self.speed_factor * self.maze.num_cells // 10, 20)


    def __single_update(self, rect: pygame.Rect, color: Color):
        pygame.draw.rect(self.__screen, conv_color(color), rect)
        pygame.display.update(rect)
        pygame.event.pump()


    def algo_tick(self, algo_instance):
        self.clock.tick(self.__algo_framerate)


    def update_walls(self,
                     *walls: Wall,
                     state: CellState = CellState.NORMAL,
                     global_update: bool = False) -> None:

        def get_color(wall: Wall):
            kind = CellKind.WALL_ON if self.maze.has_wall(wall) else CellKind.WALL_OFF
            return cell_colors[kind][state]


        if len(walls) == 1:
            self.__single_update(rect=_wall_rect(walls[0]), color=get_color(walls[0]))
        else:
            self._batched_update(walls, get_color, get_rect=_wall_rect)


    def update_cells(self, *cells: Cell, state: CellStateSelector, global_update: bool = False) -> None:

        sel = state_selector(state)

        def get_color(cell: Cell):
            s = sel(cell)
            return cell_colors[self.get_kind(cell)][s] if s else None

        if len(cells) == 1:
            self.__single_update(rect=_cell_rect(cells[0]), color=get_color(cells[0]))
        else:
            self._batched_update(cells, get_color, get_rect=_cell_rect)


    T = TypeVar('T')

    def _batched_update(self,
                        cells: Iterable[T],
                        get_color: Callable[[T], Optional[Color]],
                        get_rect: Callable[[T], Rect],
                        global_update: bool = False):
        area_to_update: Optional[Rect] = None

        for cell in cells:
            color = get_color(cell)
            if not color:
                continue

            rect = get_rect(cell)
            pygame.draw.rect(self.__screen, conv_color(color), rect)

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
        super().reset_maze(maze)  # self.maze = maze
        if prev_maze is not maze:
            self.__screen = PyGamePen.__size_window(maze)

        self.__draw_entire_maze(maze)


    def __draw_entire_maze(self, maze: Maze):
        self.__screen.fill(conv_color(WALL_COLOR))
        maze.draw_regular_tiles(self)
        pygame.display.flip()


    @staticmethod
    def __size_window(maze: Maze) -> pygame.Surface:
        # Set the width and height of the screen [width, height]

        screen_width = PyGamePen.__grid_size(maze.width, CELL_WIDTH)
        screen_height = PyGamePen.__grid_size(maze.height, CELL_HEIGHT)
        window_size = (screen_width, screen_height)

        return pygame.display.set_mode(window_size)


    @staticmethod
    def __grid_size(dim: int, inc: int):
        return (2 * dim + 1) * (inc + MARGIN) + MARGIN * 2



def get_mouse_cell():
    # User moves the mouse. Get the position
    pos = pygame.mouse.get_pos()

    # Change the x/y screen coordinates to grid coordinates
    column = pos[0] // (CELL_WIDTH + MARGIN)
    row = pos[1] // (CELL_HEIGHT + MARGIN)
    return Cell(x=(row - 1) // 2, y=(column - 1) // 2)


# -------- Main Program Loop -----------
def loop(pen: GridPen):
    maze = pen.maze
    dragged_kind = None
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
                    dragged_kind = pen.get_kind(clicked)

            elif event.type == pygame.MOUSEBUTTONUP:
                # Turn off all mouse drags if mouse Button released
                dragged_kind = None

            elif event.type == pygame.MOUSEMOTION:

                # Boolean values saying whether left, middle and right mouse buttons are currently pressed
                left, middle, right = pygame.mouse.get_pressed()

                # Sometimes we get stuck in this loop if the mousebutton is released while not in the pygame screen
                # This acts to break out of that loop
                if not left:
                    dragged_kind = None
                    continue

                mouse_cell: Cell = get_mouse_cell()

                # Turn mouse_drag off if mouse goes outside of grid
                if mouse_cell not in maze:
                    dragged_kind = None
                    continue

                if dragged_kind:
                    pen.move_start_or_end(mouse_cell, dragged_kind)
                    if algo_was_run:
                        pen.reset_maze(maze)
                        algo_was_run = False

        pen.paint_everything()



def launch(generator, solver, nrows, ncols, speed_factor: float = 1.0, random_seed=random.randint(0, 100_000)):
    maze = Maze(nrows=nrows, ncols=ncols, random_seed=random_seed)
    print("Maze seed: %d" % maze.random_seed)
    pen = PyGamePen(maze, speed_factor=speed_factor)
    maze.apply_gen(generator, pen=pen)
    solver.solve(maze, pen)
    loop(pen)


if __name__ == "__main__":
    launch(generator=WilsonGenerate(),
           solver=DfsSolver(),
           speed_factor=1,
           nrows=120,
           ncols=190)
