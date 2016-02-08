from enum import Enum
from functools import reduce
import random

from goomba import Action, Sensor

class Tile_State(Enum):
    boundary = -1
    clean = 0
    dirty = 1

class World:
    def __init__(self, w, h, goomba_genomes):
        self.width = w
        self.height = h

        distrib = [Tile_State.boundary] + [Tile_State.dirty] + [Tile_State.clean]*3

        self.state = [[random.choice(distrib) for _ in range(w)] for _ in range(h)]
    
        for i in range(w):
            self.state[i][0] = Tile_State.boundary
            self.state[i][h-1] = Tile_State.boundary
        for j in range(h):
            self.state[0][j] = Tile_State.boundary
            self.state[w-1][j] = Tile_State.boundary
        
        poss_starts = []
        for y in range(h):
            for x in range(w):
                if self.state[x][y] == Tile_State.clean:
                    poss_starts.append((x, y))
        
        starts = random.sample(poss_starts, len(goomba_genomes))
        self.goombas = [Goomba(s, p) for s, p in zip(goomba_genomes, starts)]

        self.suck_distrib = [Tile_State.clean]*3 + [Tile_State.dirty]

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


    def step(self):
        """Step the world once, moving all goombas within it."""
        for goomba in self.goombas:
            goomba.sense(self)
            goomba.think()
            goomba.choose_action()
            self.perform_action(goomba)

    def perform_action(self, g):
        action = g.intent

        if action == Action.Forward:
            bumped = self.move_forward(g)
            g.sensors[Sensor.Bump] = bumped
        elif action == Action.Backward:
            bumped = self.move_backward(g)
            g.sensors[Sensor.Bump] = bumped
        elif action == Action.LeftTurn:
            self.turn_left(g)
        elif action == Action.RightTurn:
            self.turn_right(g)
        elif action == Action.Suck:
            self.suck(*g.pos)



    def turn_left(self, g):
        """Rotate an agent anti-clockwise a quarter-turn."""
        g.ori = [-g.ori[1], g.ori[0]]

    def turn_right(self, g):
        """Rotate an agent clockwise a quarter-turn."""
        g.ori = [g.ori[1], -g.ori[0]]

    def move_forward(self, g):
        """ Move an agent one tile in the anti-facing direction.
        Returns 1 if a collision occurred, 0 otherwise.
        """

        newpos = [p+o for p, o in zip(g.pos, g.ori)]
        if self.is_in_bounds(*newpos):
            if self.get_tile(*newpos) != Tile_State.boundary:
                g.pos = newpos
                return 0
        return 1
    
    def move_backward(self, g):
        """ Move an agent one tile in the anti-facing direction.
        Returns 1 if a collision occurred, 0 otherwise.
        """
        newpos = [p-o for p, o in zip(g.pos, g.ori)]
        if self.is_in_bounds(*newpos):
            if self.get_tile(*newpos) != Tile_State.boundary:
                g.pos = newpos
                return 0
        return 1

    def suck(self, x, y):
        """Attempt to clean the dirt from a given tile.
        There is a chance that the tile will be made dirty instead of clean.
        No effect on boundary tiles.
        Returns 1 if the tile went from clean to dirty, -1 if it went the other way, 0 otherwise.
        """
        tile_before = get_tile(x, y)

        if (not is_in_bounds(x, y)) or (tile_before == Tile_State.boundary):
            return 0
        
        tile_after = random.choice(self.suck_distrib)
        set_tile(x, y, tile_after)
        
        if (tile_before == Tile_State.clean) and (tile_after == Tile_State.dirty):
            return -1

        if (tile_before == Tile_State.dirty) and (tile_after == Tile_State.clean):
            return 1

        return 0

