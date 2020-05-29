from maze.util import *
from maze.mazegen import *



class Maze(object):
    """A maze with fixed-dimensions. Initially all cells are walled. apply_gen generates corridors
       by breaking some walls"""


    def __init__(self, nrows: int, ncols: int):
        if nrows <= 0 or ncols <= 0:
            raise AssertionError("Dimensions must be >= 0, got %d, %d" % (nrows, ncols))

        self.__size = nrows * ncols
        self.__nrows = nrows
        self.__ncols = ncols

        self.start_cell = Cell(0, random.randint(a=0, b=nrows - 1))
        self.end_cell = Cell(ncols - 1, random.randint(a=0, b=nrows - 1))

        self.reset()


    def apply_gen(self, gen: GenerationAlgo, pen: GridPen):
        self.reset()
        pen.reset_maze(maze=self)
        gen.generate(maze=self, break_wall=lambda w: self.__break_wall(w, pen))


    def __break_wall(self, wall: Wall, pen: GridPen):
        self.__set_wall(wall, False)
        pen.update_wall(wall, active=False)


    def reset(self):
        # 2 bitarrays: 1 for TOP walls, one for LEFT ones
        # All walls are set
        self.__walls = {d: self.new_cell_set(True) for d in list(Direction)}


    def new_cell_set(self, initial_value: bool = False) -> Cell.CellSet:
        return Cell.CellSet(height=self.height, width=self.width, initial_value=initial_value)


    @property
    def height(self) -> int:
        """Number of rows, ie height, ie max value (exclusive) of the y coordinate of a Cell"""
        return self.__nrows


    @property
    def width(self) -> int:
        """Number of columns, ie width, ie max value (exclusive) of the x coordinate of a Cell"""
        return self.__ncols


    def has_wall(self, wall: Wall) -> bool:
        self.__check_pos(wall.cell)
        (x, y, side) = wall

        if side is Side.RIGHT:
            return (x == self.width - 1) or self.has_wall(Wall(x + 1, y, Side.LEFT))
        if side is Side.BOT:
            return (y == self.height - 1) or self.has_wall(Wall(x, y + 1, Side.TOP))
        else:
            return wall.cell in self.__walls[side.direction()]


    def __set_wall(self, wall: Wall, value: bool = True) -> None:
        self.__check_pos(wall.cell)
        (x, y, side) = wall

        if side is Side.RIGHT and x < self.width - 1:
            self.__set_wall(Wall(x + 1, y, Side.LEFT), value)
        elif side is Side.BOT and y < self.height - 1:
            self.__set_wall(Wall(x, y + 1, Side.TOP), value)
        else:
            self.__walls[side.direction()][wall.cell] = value


    def __check_pos(self, cell: Cell) -> None:
        if cell not in self:
            raise IndexError(cell)


    def __contains__(self, cell: Cell) -> bool:
        return cell.x in range(0, self.height) \
               and cell.y in range(0, self.width)


    def all_cells(self):
        return Cell.iterate(h=self.height, w=self.width)


    def __str__(self):
        res = ""
        for j in range(0, self.height):
            hline = "   "
            vline = "   "

            for i in range(0, self.width):
                cell = Cell(i, j)
                has_top = cell in self.__walls[Direction.VERTICAL]
                has_left = cell in self.__walls[Direction.HORIZONTAL]

                hline += "+--" if has_top else "+  "
                vline += "|" if has_left else " "
                vline += "<>" if self.start_cell == cell \
                    else "><" if self.end_cell == cell \
                    else "  "

            res += hline + "+\n"
            res += vline + "|\n"

        res += "   "
        res += ("+--" * self.width)
        res += "+"

        return res
