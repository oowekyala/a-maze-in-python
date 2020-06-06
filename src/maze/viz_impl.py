from typing import Dict

from pygame import Rect, Surface
import pygame

import random, traceback

from maze.viz import *
from maze.gen import *
from maze.solver import *
from maze.model import *

@unique
class Color(Enum):
    BLACK = pygame.Color("black")
    WHITE = pygame.Color("white")
    GREEN = pygame.Color(133, 223, 38)
    RED = pygame.Color("red")
    BLUE = pygame.Color(5, 103, 173)
    ORANGE = pygame.Color("orange")
    PURPLE = pygame.Color("purple")
    YELLOW = pygame.Color(237, 207, 84)
    GREY = pygame.Color("darkslategrey")
    BROWN = pygame.Color("brown")


def conv_color(color: Color) -> pygame.Color:
    return color.value



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
    CellKind.END: {s: Color.RED for s in list(CellState)},
}

cell_colors[CellKind.WALL_OFF] = {**cell_colors[CellKind.REGULAR], CellState.UNDISCOVERED: WALL_COLOR}
cell_colors[CellKind.WALL_ON] = {**cell_colors[CellKind.WALL_OFF], CellState.NORMAL: WALL_COLOR}

# below this limit (inclusive), the speed factor is an actual framerate cap
# above, it depends on the algo/maze size
SPEED_FACTOR_RT_CUT = .3



class WindowTermination(Exception):
    pass



class PygameWindow(object):

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("A maze")

        self.clock = pygame.time.Clock()
        self.__screen: Optional[Surface] = None
        self.__grid_surface = None


    def set_grid_dimensions(self, width, height):
        self.__screen = pygame.display.set_mode((width, height))


    def loop_until_exit(self):
        while True:
            self.handle_window_events()
            self.clock.tick(60)


    def handle_window_events(self):
        """Process pygame events. Done on frame ticks, as control flow belongs to the algo in that case"""
        pygame.event.pump()
        if pygame.event.get(eventtype=pygame.QUIT):
            raise WindowTermination()


    def __enter__(self):
        return self


    def __exit__(self, exc_type, exc_val, exc_tb):
        pygame.quit()

        return exc_type == WindowTermination


    def update_grid(self, grid_surf: Surface, dirty: Optional[Rect]):
        if not self.__screen:
            return

        grid_top_left_corner = (0, 0)

        self.__screen.blit(source=grid_surf, dest=grid_top_left_corner, area=dirty)

        if dirty:
            pygame.display.update(rectangle=dirty)
        else:
            pygame.display.flip()


class VirtualSurfacePen(GridPen):
    """Draws a maze algorithm on an internal Surface. Relays drawing events to a PygameWindow, which
       may perform transformations to handle zoom/position/etc"""

    def __init__(self, maze: Maze,
                 backend: PygameWindow,
                 cell_width=6,
                 cell_margin=0):
        super().__init__(maze)

        self.speed_factor = 1.0  # this uses the custom setter
        self.__tick_count = 0
        self.__overclock = 1

        self.cell_width = cell_width
        self.cell_margin = cell_margin

        self.__backend = backend

        dims = self.__surface_dimensions(maze)
        self.__grid_surface: Surface = Surface(dims)
        backend.set_grid_dimensions(*dims)
        self.__dirty: Rect = Rect(0, 0, 0, 0)
        self.__global_update = False

        self.reset_maze(maze)


    @property
    def cell_height(self):
        return self.cell_width  # cells are squares


    def _cell_rect(self, cell: Cell) -> pygame.Rect:
        return self._rect(2 * cell.row + 1, 2 * cell.col + 1)


    def _wall_rect(self, wall: Wall) -> pygame.Rect:
        ((row, col), side) = wall
        (row, col) = (2 * row + 1, 2 * col + 1)
        row += side.d_row
        col += side.d_col
        return self._rect(row, col)


    def _rect(self, row, col) -> pygame.Rect:
        return Rect(
            (self.cell_margin + self.cell_width) * col + self.cell_margin,
            (self.cell_margin + self.cell_height) * row + self.cell_margin,
            self.cell_width,
            self.cell_height
        )


    def __surface_dimensions(self, maze: Maze) -> (int, int):
        """Set the width and height of the screen, return the surface on which to draw"""

        screen_width = self.__grid_size(maze.ncols, self.cell_width)
        screen_height = self.__grid_size(maze.nrows, self.cell_height)
        return screen_width, screen_height


    def __grid_size(self, dim: int, inc: int):
        return (2 * dim + 1) * (inc + self.cell_margin) + self.cell_margin * 2


    def tick_frame(self, algo_instance, force_refresh=False):
        self.__tick_count += 1
        if force_refresh or self.__tick_count % self.__overclock == 0:

            if self.__global_update:
                self.__backend.update_grid(grid_surf=self.__grid_surface, dirty=None)
            elif self.__dirty:
                self.__backend.update_grid(grid_surf=self.__grid_surface, dirty=self.__dirty)

            self.__dirty = None
            self.__backend.handle_window_events()
            if self.speed_factor < 1.0:
                self.__backend.clock.tick(self.__algo_framerate)


    @property
    def overclock(self):
        return self.overclock


    @overclock.setter
    def overclock(self, ov: int):
        self.__overclock = min(max(ov, 1), 8)


    @property
    def speed_factor(self):
        return self.__speed_factor


    @speed_factor.setter
    def speed_factor(self, sf: float):
        # A maze with many cells will show a higher framerate than a smaller maze for the same speed factor
        # Otherwise some algorithms would be too slow in big mazes
        # The perceived "speed" depends on the algorithm
        self.__speed_factor = max(sf, 0.01)
        # Requirements, for any maze size:
        # - at > 30% speed_factor, we want the framerate to be fluid (>= 20)
        # - at 100% speed_factor, we want every algo frame to be displayed, but run as fast as possible
        # - TODO at > 100% we want to skip frame refreshes

        if self.speed_factor <= SPEED_FACTOR_RT_CUT:
            # under 30%
            self.__algo_framerate = self.speed_factor * 100
        else:
            self.__algo_framerate = max(self.speed_factor * self.maze.num_cells // 10, 20)


    def update_walls(self,
                     *walls: Wall,
                     state: CellState = CellState.NORMAL,
                     global_update: bool = False) -> None:

        def get_color(wall: Wall):
            kind = CellKind.WALL_ON if self.maze.has_wall(wall) else CellKind.WALL_OFF
            return cell_colors[kind][state]


        self._batched_update(walls, get_color, get_rect=self._wall_rect, global_update=global_update)


    def update_cells(self, *cells: Cell, state: CellStateSelector, global_update: bool = False) -> None:

        sel = state_selector(state)


        def get_color(cell: Cell):
            s = sel(cell)
            return cell_colors[self.get_kind(cell)][s] if s else None


        self._batched_update(cells, get_color, get_rect=self._cell_rect, global_update=global_update)


    T = TypeVar('T')


    def _batched_update(self,
                        cells: Iterable[T],
                        get_color: Callable[[T], Optional[Color]],
                        get_rect: Callable[[T], Rect],
                        global_update: bool = False):
        dirty: Optional[Rect] = None

        self.__global_update |= global_update

        for cell in cells:
            color = get_color(cell)
            if not color:
                continue

            rect = get_rect(cell)
            pygame.draw.rect(self.__grid_surface, conv_color(color), rect)

            if not self.__global_update:
                if dirty:
                    dirty = dirty.union(rect)
                else:
                    dirty = rect

        if dirty and not self.__global_update:
            self.__update_dirty(dirty)


    def __update_dirty(self, dirty: Rect):
        """Extend the dirty region to include the given dirty rectangle"""
        self.__dirty = self.__dirty.union(dirty) if self.__dirty else dirty


    def reset_maze(self, maze: Maze):
        prev_maze: Maze = self.maze
        super().reset_maze(maze)  # self.maze = maze
        if prev_maze is not maze:
            dims = self.__surface_dimensions(maze)
            self.__grid_surface = pygame.Surface(dims)
            self.__backend.set_grid_dimensions(dims)


    def draw_entire_maze(self, cell_state: CellState, is_walled: bool = True):
        self.__grid_surface.fill(conv_color(WALL_COLOR))

        self.update_cells(*self.maze.all_cells(), state=cell_state, global_update=True)

        if self.maze.mod_count != 0 or not is_walled:
            self.update_walls(*self.maze.distinct_walls(on=False), global_update=True)

        self.tick_frame(self, force_refresh=True)

    def loop_until_exit(self):
        self.__backend.loop_until_exit()



def do_pygame(generator,
              nrows: int,
              ncols: int,
              solver: SolverAlgo,
              random_seed: int = random.randint(0, 100_000),
              cell_width=6,
              speed_factor: float = 1.0,
              overclock: int = 1,
              visualize=True):
    with PygameWindow() as window:
        pen = None
        try:
            maze = Maze(nrows=nrows, ncols=ncols, random_seed=random_seed)
            pen = VirtualSurfacePen(maze, backend=window, cell_width=cell_width)
            pen.overclock = overclock
            pen.speed_factor = speed_factor
            if visualize:
                apply_gen(generator, pen=pen)
            else:
                apply_gen(generator, pen=GridPen.noop_pen(maze, tick_function=window.handle_window_events))
                pen.draw_entire_maze(cell_state=CellState.NORMAL)

            solver.solve(pen)

            pen.tick_frame(None, force_refresh=True)
        except Exception as ex:
            if isinstance(ex, WindowTermination):
                raise
            else:
                print(traceback.format_exc())

        if pen:
            pen.loop_until_exit()



gen_map = {
    "DFS": DfsGenerate(),
    "Wilson": WilsonGenerate(),
    "Eller": EllerGen(),
    "No walls": BlankGen(),
    "Prim": PrimGenerate(),
    "Rec. division": RecursiveDivisionGenerate(),
    "Sidewinder": SidewinderGenerate(),
    "Kruskal": KruskalGenerate(),
}

solver_map = {
    "DFS (Manhattan heuristic)": DfsSolver(heuristic=ManhattanDistance()),
    "DFS (no heuristic)": DfsSolver(heuristic=NoHeuristic()),
    "BFS": BfsSolver(),
    "Dead-end filler": DeadEndFillingSolver(),
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
        self.root.title("Configure Maze")


        def row_label(text: str):
            ttk.Label(self.root, text=text, anchor="w").grid(row=row, column=0)


        def slider(label_text, from_, to, default, unit=""):
            assert from_ <= default <= to

            row_label(text=label_text)

            value_label = tk.Label(self.root, text=str(default))
            scale = None


            def update(event):
                value_label["text"] = "%d%s" % (scale.get(), unit)


            scale = tk.Scale(self.root, from_=from_, to=to, orient=tk.HORIZONTAL, command=update, showvalue=False)

            scale.setvar("command", update)

            scale.set(default)

            value_label.grid(row=row, column=1)
            scale.grid(row=row, column=2)
            return scale


        def checkbox(label_text, default=True, on_change=None):
            row_label(label_text)
            var = tk.BooleanVar(value=default)
            cbox = tk.Checkbutton(self.root, variable=var, onvalue=True, offvalue=False, command=on_change)
            cbox.grid(row=row, column=1)
            return var


        row = 0
        self.width_slider = slider(label_text="Width", from_=5, to=300, default=50)

        row += 1
        self.height_slider = slider(label_text="Height", from_=5, to=300, default=50)

        row += 1

        self.square_binding = None


        def square_handler():
            is_square = self.square_grid_var.get()
            # TODO either disable height slider ( `["state"] = tk.DISABLED` does not work properly)
            #  or backsync height to width (see stash)
            if is_square:
                self.height_slider.set(self.width_slider.get())
                self.square_binding = self.width_slider.bind("<ButtonRelease-1>",
                                                             lambda e: self.height_slider.set(self.width_slider.get()))
            elif self.square_binding:
                self.width_slider.unbind("<ButtonRelease-1>", funcid=self.square_binding)
                self.square_binding = None


        self.square_grid_var = checkbox("Square", on_change=square_handler)
        square_handler()

        row += 1
        self.cell_width_slider = slider(label_text="Cell size", from_=3, to=15, default=6)

        row += 1
        row_label(text="Seed")

        self.seedvar = tk.StringVar()


        def gen_seed():
            return self.seedvar.set(str(random.randrange(0, 100_000)))


        gen_seed()
        tk.Button(text="gen", padx=3, pady=3, command=gen_seed).grid(row=row, column=1)

        self.seed_entry = ttk.Entry(self.root, textvariable=self.seedvar)
        self.seed_entry.grid(row=row, column=2)

        row += 1
        row_label(text="Generator")
        self.generator_choicebox = ttk.Combobox(self.root, values=gen_key_list)
        self.generator_choicebox.current(0)
        self.generator_choicebox.grid(row=row, column=1, columnspan=2)

        row += 1
        row_label(text="Solver")
        self.solver_choicebox = ttk.Combobox(self.root, values=solvers_key_list)
        self.solver_choicebox.current(0)
        self.solver_choicebox.grid(row=row, column=1, columnspan=2)

        row += 1
        row_label(text="See generation?")
        self.visualize_gen_var = checkbox(label_text="See generation?", default=True)

        row += 1
        self.speed_slider = slider(label_text="Speed", from_=1, to=100, default=100, unit=" %")

        row += 1
        self.overclock_slider = slider(label_text="Frame skip", from_=1, to=8, default=1, unit="x")

        row += 1
        ttk.Separator(self.root).grid(row=row, column=0, columnspan=3)

        row += 1
        go_button = tk.Button(self.root, text="Go", command=self.go_button_press, background="lightyellow")
        go_button.grid(row=row, columnspan=3)

        self.root.mainloop()


    def go_button_press(self):
        do_pygame(
            generator=gen_map[self.generator_choicebox.get()],
            random_seed=int(self.seedvar.get()),
            speed_factor=self.speed_slider.get() / 100,
            overclock=int(self.overclock_slider.get()),
            nrows=int(self.height_slider.get()),
            ncols=int(self.width_slider.get()),
            visualize=self.visualize_gen_var.get(),
            cell_width=int(self.cell_width_slider.get()),
            solver=solver_map[self.solver_choicebox.get()]
        )
