# A maze: maze algorithm visualisation in Python

A toy project to teach myself Python. This uses Pygame to render mazes
 and Tkinter for the control panel.

You can see nice gifs of the supported generators/solvers below. The gifs
are slowed down, the algorithms perform well even on big mazes. There
are several options to control execution speed directly from the control
panel (slow down/speed up execution).

Only tested under Ubuntu 18.04. You need pygame, Pypy's bitarray module,
tkinter, and Python >= 3.6:
```bash
sudo apt-get install python3-tk
cat DEPENDENCIES | xargs pip3 install
```

Running in Bash:

```bash
PYTHONPATH="$(pwd)/src" python3 -m amaze
```


## Maze generators

#### DFS

![Gif](gifs/generators/dfs.gif)

Do a random walk until you hit a wall. Then backtrack and start your random walk again on the first possible turn. See also the DFS solver below.

#### Eller

<details>
    <summary>Gif...</summary>

![Gif](gifs/generators/eller.gif)

</details>

For each row, randomly break east walls and top walls, but keep track of connected components (like Kruskal's) so that you never break a wall between two cells which are already connected.

#### Kruskal

<details>
    <summary>Gif...</summary>

![Gif](gifs/generators/kruskal.gif)

</details>

 Let every cell of the maze have a reference to the connected component it's part of. Initially, all cells are disconnected, so each cell is its own connected component. Then, randomly pick two cells from different connected components and break the wall between them (merge their connected component). Continue until all cells are connected.

#### Prim

<details>
    <summary>Gif...</summary>

![Gif](gifs/generators/prim.gif)

</details>

Start with one cell in the maze. Add its walls to a set. Then pick a random wall in that set, and if one of the cells it divides is not yet part of the maze, break the wall and add the cell to the maze. Add the walls of the cell that has become accessible to the set. Repeat while that set is not empty. In this gif, the green cells are the walls in the set.

#### Recursive division

<details>
    <summary>Gif...</summary>

![Gif](gifs/generators/rec_div.gif)

</details>

This one starts with a maze where no walls exist, and build walls instead of breaking them. Divide the maze into 4 quadrants, create one passage at random in 3 of the 4 new walls. For each of the quadrants, repeat this procedure until the quadrants are too small to be divided.

#### Sidewinder

<details>
    <summary>Gif...</summary>

![Gif](gifs/generators/sidewinder.gif)

</details>

Start with a clear top row. Then, for each cell in the next row, flip a coin: either break its right wall, or break the top wall of one of the cells it is connected to (by the left, necessarily).

#### Wilson

<details>
    <summary>Gif...</summary>

![Gif](gifs/generators/wilson.gif)

</details>

Start with one cell in the maze. Then, from a cell that is outside the maze, start a random walk until you hit a cell that's in the maze. When that happens, add the whole random path to the maze and start over. When the random walk hits itself, remove the loop and continue with the shorter path.


## Maze solvers

#### A*

![Gif](gifs/solvers/a_star.gif)

Use a heuristic to explore paths that are the most likely to lead you to the exit first. Basically it's like BFS (see below), because BFS always explores the shortest path next. But with A*, instead of exploring the shortest path next, you explore the "least costly" path, where the "cost" of a path is determined by the heuristic. If the heuristic is just path length, then this is exactly BFS.

#### DFS

<details>
    <summary>Gif...</summary>

![Gif](gifs/solvers/dfs.gif)

</details>

Depth-first search: Go as far as you can randomly, marking all paths you've *not* taken yet along the way. When you hit a dead-end, backtrack to the latest mark you've done and redo the same exploration. 

#### BFS

<details>
    <summary>Gif...</summary>

![Gif](gifs/solvers/bfs.gif)

</details>

Breadth-first search: Explore all paths of length 1, then all paths of length 2, etc.

#### Dead-end filling

<details>
    <summary>Gif...</summary>

![Gif](gifs/solvers/dead_ends.gif)

</details>

Fill dead-ends until only one path remains. This is probably how you would solve a maze by hand.

#### Left-/right-hand rule

<details>
    <summary>Gif...</summary>

![Gif](gifs/solvers/lhand_rule.gif) ![Gif](gifs/solvers/rhand_rule.gif)

</details>


Keep your left (or right) hand on the wall next to you, and follow it until the end. This only works if the maze has no isles. This is probably how you would get out of a maze if you're lost one day, as this doesn't require storing any state.

