from typing import Dict

from pygame import Rect
import pygame

from maze.viz import *
from maze.gen import *
from maze.solver import *
from maze.model import *



def conv_color(color: Color) -> pygame.Color:
    return pygame.Color(color.value)



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



class PyGamePen(GridPen):
    """
    Implementation of GridPen using pygame as a backend.
    """


    def __init__(self, maze: Maze, speed_factor: float = 1.0,
                 tick_progress=None,
                 cell_width=6, cell_margin=0):
        super().__init__(maze)
        pygame.init()
        self.tick_progress = tick_progress
        self.clock = pygame.time.Clock()
        self.speed_factor = max(speed_factor, 0.1)  # this uses the custom setter
        self.cell_width = cell_width
        self.cell_margin = cell_margin
        self.__screen = self.__size_window(maze)
        self.__cell_kind_map = {}
        self.reset_maze(maze)


    @property
    def cell_height(self):
        return self.cell_width  # cells are squares


    def _cell_rect(self, cell: Cell) -> pygame.Rect:
        return self._rect(2 * cell.x + 1, 2 * cell.y + 1)


    def _wall_rect(self, wall: Wall) -> pygame.Rect:
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

        return self._rect(x, y)


    def _rect(self, x, y) -> pygame.Rect:
        return Rect(
            (self.cell_margin + self.cell_width) * y + self.cell_margin,
            (self.cell_margin + self.cell_height) * x + self.cell_margin,
            self.cell_width,
            self.cell_height
        )


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
            self.__single_update(rect=self._wall_rect(walls[0]), color=get_color(walls[0]))
        else:
            self._batched_update(walls, get_color, get_rect=self._wall_rect)


    def update_cells(self, *cells: Cell, state: CellStateSelector, global_update: bool = False) -> None:

        sel = state_selector(state)


        def get_color(cell: Cell):
            s = sel(cell)
            return cell_colors[self.get_kind(cell)][s] if s else None


        if len(cells) == 1:
            self.__single_update(rect=self._cell_rect(cells[0]), color=get_color(cells[0]))
        else:
            self._batched_update(cells, get_color, get_rect=self._cell_rect)


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
            self.__screen = self.__size_window(maze)

        self.draw_entire_maze(cell_state=CellState.UNDISCOVERED)


    def draw_entire_maze(self, cell_state):
        self.__screen.fill(conv_color(WALL_COLOR))
        self.maze.draw_regular_tiles(self, cell_state=cell_state)
        pygame.display.flip()


    def __size_window(self, maze: Maze) -> pygame.Surface:
        # Set the width and height of the screen [width, height]

        screen_width = self.__grid_size(maze.width, self.cell_width)
        screen_height = self.__grid_size(maze.height, self.cell_height)
        window_size = (screen_width, screen_height)

        return pygame.display.set_mode(window_size)


    def __grid_size(self, dim: int, inc: int):
        return (2 * dim + 1) * (inc + self.cell_margin) + self.cell_margin * 2


    def loop_until_exit(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return None

            self.clock.tick(30)


    def get_mouse_cell(self):
        # User moves the mouse. Get the position
        pos = pygame.mouse.get_pos()
        # Change the x/y screen coordinates to grid coordinates
        column = pos[0] // (self.cell_width + self.cell_margin)
        row = pos[1] // (self.cell_height + self.cell_margin)
        return Cell(x=(row - 1) // 2, y=(column - 1) // 2)



def generate(generator,
             nrows,
             ncols,
             random_seed=random.randint(0, 100_000),
             speed_factor: float = 1.0,
             tick_progress=None,
             visualize=True) -> PyGamePen:
    maze = Maze(nrows=nrows, ncols=ncols, random_seed=random_seed)
    pygame_pen = PyGamePen(maze, speed_factor=speed_factor, tick_progress=tick_progress)
    if visualize:
        maze.apply_gen(generator, pen=pygame_pen)
    else:
        maze.apply_gen(generator, pen=GridPen.noop_pen(maze, tick_progress=tick_progress))
        pygame_pen.draw_entire_maze(cell_state=CellState.NORMAL)

    return pygame_pen



gen_map = {
    "DFS": DfsGenerate(),
    "Wilson": WilsonGenerate(),
    "Prim": PrimGenerate(),
}

solver_map = {
    "DFS (Manhattan heuristic)": DfsSolver(heuristic=ManhattanDistance()),
    "DFS (no heuristic)": DfsSolver(heuristic=NoHeuristic()),
    "Right-hand rule": HandRuleSolver(is_right_hand_rule=True),
    "Left-hand rule": HandRuleSolver(is_right_hand_rule=False),
}

solvers_key_list = list(solver_map.keys())
solvers_key_list.sort()

gen_key_list = list(gen_map.keys())
gen_key_list.sort()



class ControlPanel(object):

    def __init__(self):
        import tkinter as tk
        import tkinter.ttk as ttk
        self.root = tk.Tk()


        def slider(label, from_, to, default, row, unit=""):
            assert from_ <= default <= to

            tk.Label(self.root, text=label).grid(row=row)

            label = tk.Label(self.root, text=str(default))
            scale = None


            def update(event):
                label["text"] = "%d%s" % (scale.get(), unit)


            scale = ttk.Scale(self.root, from_=from_, to=to, orient=tk.HORIZONTAL, command=update)

            scale.setvar("command", update)

            scale.set(default)

            label.grid(row=row, column=1)
            scale.grid(row=row, column=2)
            return scale


        row = 0
        self.width_slider = slider(label="Width", from_=5, to=120, default=50, row=row)

        row += 1
        self.height_slider = slider(label="Height", from_=5, to=120, default=50, row=row)

        row += 1
        tk.Label(self.root, text="Seed").grid(row=row)
        self.seedvar = tk.StringVar(value=str(random.randrange(0, 100_000)))
        self.seed_entry = tk.Entry(self.root, textvariable=self.seedvar)
        self.seed_entry.grid(row=row, column=1, columnspan=2)

        row += 1
        tk.Label(self.root, text="Generator").grid(row=row)
        self.generator_choicebox = ttk.Combobox(self.root, values=gen_key_list)
        self.generator_choicebox.current(0)
        self.generator_choicebox.grid(row=row, column=1, columnspan=2)

        row += 1
        tk.Label(self.root, text="See generation?").grid(row=row)
        self.visualize_gen_var = tk.BooleanVar(value=True)
        self.visualize_checkbox = tk.Checkbutton(self.root, variable=self.visualize_gen_var, onvalue=True,
                                                 offvalue=False)
        self.visualize_checkbox.grid(row=row, column=1)

        row += 1
        tk.Label(self.root, text="Solver").grid(row=row)
        self.solver_choicebox = ttk.Combobox(self.root, values=solvers_key_list)
        self.solver_choicebox.current(0)
        self.solver_choicebox.grid(row=row, column=1, columnspan=2)

        row += 1
        tk.Label(self.root, text="Speed").grid(row=row)
        self.speed_slider = slider(label="Speed", from_=1, to=100, default=100, row=row, unit=" %")

        row += 1
        go_button = tk.Button(self.root, text="Go", command=self.go_button_press, background="lightyellow")
        go_button.grid(row=row, columnspan=3)

        self.root.mainloop()


    def go_button_press(self):
        pygame_pen = generate(
            generator=gen_map[self.generator_choicebox.get()],
            random_seed=int(self.seedvar.get()),
            speed_factor=self.speed_slider.get() / 100,
            nrows=int(self.height_slider.get()),
            ncols=int(self.width_slider.get()),
            visualize=self.visualize_gen_var.get(),
        )

        if True:  # TODO
            solver = solver_map[self.solver_choicebox.get()]
            solver.solve(pygame_pen.maze, pygame_pen)

        pygame_pen.loop_until_exit()



if __name__ == "__main__":
    control = ControlPanel()
