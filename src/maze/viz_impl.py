from typing import Dict

from pygame import Rect
import pygame

import random

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
    CellKind.END: {s: Color.ORANGE for s in list(CellState)},
}

cell_colors[CellKind.WALL_OFF] = {**cell_colors[CellKind.REGULAR], CellState.UNDISCOVERED: WALL_COLOR}
cell_colors[CellKind.WALL_ON] = {**cell_colors[CellKind.WALL_OFF], CellState.NORMAL: WALL_COLOR}



class PyGameTermination(Exception):
    pass

class PyGamePen(GridPen):
    """
    Implementation of GridPen using pygame as a backend.
    """


    def __init__(self, maze: Maze,
                 speed_factor: float = 1.0,
                 cell_width=6,
                 cell_margin=0):
        super().__init__(maze)
        pygame.init()
        pygame.display.set_caption("A maze")

        self.clock = pygame.time.Clock()
        self.speed_factor = speed_factor  # this uses the custom setter
        self.cell_width = cell_width
        self.cell_margin = cell_margin
        self.__screen: pygame.Surface = self.__size_window(maze)
        self.__cell_kind_map = {}
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


    @property
    def speed_factor(self):
        return self.__speed_factor


    @speed_factor.setter
    def speed_factor(self, sf: float):
        # A maze with many cells will show a higher framerate than a smaller maze for the same speed factor
        # Otherwise some algorithms would be impossibly slow in big mazes
        # The perceived "speed" depends on the algorithm
        self.__speed_factor = max(sf, 0.01)
        # Requirements, for any maze size:
        # - at > 30% speed_factor, we want the framerate to be fluid (>= 20)
        # - at the highest speed_factor, we want that any maze be generated in under 15 seconds (for linear generators)

        if self.speed_factor <= .30:
            self.__algo_framerate = self.speed_factor * 100
        else:
            self.__algo_framerate = max(self.speed_factor * self.maze.num_cells // 10, 20)


    def __single_update(self, rect: pygame.Rect, color: Color):
        pygame.draw.rect(self.__screen, conv_color(color), rect)
        pygame.display.update(rect)
        pygame.event.pump()


    def algo_tick(self, algo_instance, frontier_size=1):
        frontier_size = max(frontier_size, 1)
        tick_weight = 1
        if frontier_size != 1 and self.speed_factor > .30 and frontier_size / self.maze.num_cells >= 0.2:
            #  algo_tick slows down BFS-type algorithms (eg Prim), where the algo advances a whole
            #  frontier. A tick is registered for each member of the frontier, so as the frontier grows,
            #  it hits the framerate limit much earlier than algos like DFS, which have a single cell as
            #  frontier

            tick_weight = 5
        self.clock.tick(tick_weight * self.__algo_framerate)
        self.check_terminated()


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


    def reset_maze(self, maze: Maze):
        prev_maze: Maze = self.maze
        super().reset_maze(maze)  # self.maze = maze
        if prev_maze is not maze:
            self.__screen = self.__size_window(maze)


    def draw_entire_maze(self, cell_state: CellState, is_walled: bool = True):
        self.__screen.fill(conv_color(WALL_COLOR))

        self.update_cells(*self.maze.all_cells(), state=cell_state, global_update=True)

        if self.maze.mod_count != 0 or not is_walled:
            self.update_walls(*self.maze.distinct_walls(on=False), global_update=True)


    def __size_window(self, maze: Maze) -> pygame.Surface:
        # Set the width and height of the screen [width, height]

        screen_width = self.__grid_size(maze.ncols, self.cell_width)
        screen_height = self.__grid_size(maze.nrows, self.cell_height)
        window_size = (screen_width, screen_height)
        return pygame.display.set_mode(window_size)


    def __grid_size(self, dim: int, inc: int):
        return (2 * dim + 1) * (inc + self.cell_margin) + self.cell_margin * 2


    def loop_until_exit(self):
        while True:
            self.check_terminated()
            self.clock.tick(60)


    def check_terminated(self):
        if pygame.event.get(eventtype=pygame.QUIT):
            raise PyGameTermination()


    def get_mouse_cell(self):
        # User moves the mouse. Get the position
        pos = pygame.mouse.get_pos()
        # Change the x/y screen coordinates to grid coordinates
        column = pos[0] // (self.cell_width + self.cell_margin)
        row = pos[1] // (self.cell_height + self.cell_margin)
        return Cell(row=(row - 1) // 2, col=(column - 1) // 2)



def generate(generator,
             nrows,
             ncols,
             random_seed=random.randint(0, 100_000),
             cell_width=6,
             speed_factor: float = 1.0,
             visualize=True) -> PyGamePen:
    maze = Maze(nrows=nrows, ncols=ncols, random_seed=random_seed)
    pygame_pen = PyGamePen(maze, speed_factor=speed_factor, cell_width=cell_width)
    if visualize:
        apply_gen(generator, pen=pygame_pen)
    else:
        apply_gen(generator, pen=GridPen.noop_pen(maze))
        pygame_pen.draw_entire_maze(cell_state=CellState.NORMAL)

    return pygame_pen



gen_map = {
    "DFS": DfsGenerate(),
    "Wilson": WilsonGenerate(),
    "Prim": PrimGenerate(),
    "Rec. division": RecursiveDivisionGenerate(),
    "Sidewinder": SidewinderGenerate(),
}

solver_map = {
    "DFS (Manhattan heuristic)": DfsSolver(heuristic=ManhattanDistance()),
    "DFS (no heuristic)": DfsSolver(heuristic=NoHeuristic()),
    "BFS": BfsSolver(),
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
        row_label(text="Speed")
        self.speed_slider = slider(label_text="Speed", from_=1, to=100, default=100, unit=" %")

        row += 1
        go_button = tk.Button(self.root, text="Go", command=self.go_button_press, background="lightyellow")
        go_button.grid(row=row, columnspan=3)

        self.root.mainloop()


    def go_button_press(self):
        try:
            self.launch_pygame()
        except PyGameTermination:
            pygame.quit()
        except:
            pygame.quit()
            raise



    def launch_pygame(self):
        pygame_pen = generate(
            generator=gen_map[self.generator_choicebox.get()],
            random_seed=int(self.seedvar.get()),
            speed_factor=self.speed_slider.get() / 100,
            nrows=int(self.height_slider.get()),
            ncols=int(self.width_slider.get()),
            visualize=self.visualize_gen_var.get(),
            cell_width=int(self.cell_width_slider.get()),
        )
        if True:  # TODO
            solver = solver_map[self.solver_choicebox.get()]
            solver.solve(pygame_pen.maze, pygame_pen)

        pygame_pen.loop_until_exit()

