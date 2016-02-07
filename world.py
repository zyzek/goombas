from enum import Enum
from functools import reduce
import random

class Tile_State(Enum):
    boundary = -1
    clean = 0
    dirty = 1

class World:
    def __init__(self, w, h, goombas):
        self.width = w
        self.height = h

        self.state = [[random.choice(list(Tile_State)) for _ in range(w)] for _ in range(h)]
    
        for i in range(w):
            self.state[i][0] = Tile_State.boundary
            self.state[i][h-1] = Tile_State.boundary
        for j in range(h):
            self.state[0][j] = Tile_State.boundary
            self.state[w-1][j] = Tile_State.boundary

        self.goombas = goombas

    def set_tile(self, x, y, z):
        if is_in_bounds(x, y):
            self.state[x][y] = z

    def get_tile(self, x, y):
        if is_in_bounds(x, y):
            return self.state[x][y]
        return Tile_State.boundary
    
    def is_in_bounds(self, x, y):
        return x >= 0 and x < self.width and y >= 0 and y < self.height

    def current_score(self):
        # Sum over the values of the 2d world array
        return reduce(lambda acc, i: acc + sum(t == Tile_State.clean for t in i), self.state, 0)


    def turn_left(self, g):
        g.ori = [-g.ori[1], g.ori[0]]

    def turn_right(self, g):
        g.ori = [g.ori[1], -g.ori[0]]

    def move_forward(self, g):
        newpos = [p+o for p, o in zip(g.pos, g.ori)]
        if self.is_in_bounds(*newpos):
            if self.get_tile(*newpos) != Tile_State.boundary:
                g.pos = newpos
    
    def move_backward(self, g):
        newpos = [p-o for p, o in zip(g.pos, g.ori)]
        if self.is_in_bounds(*newpos):
            if self.get_tile(*newpos) != Tile_State.boundary:
                g.pos = newpos
