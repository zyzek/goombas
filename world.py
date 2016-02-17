from enum import IntEnum
from random import choice, sample, randrange

from goomba import Goomba
from genome import Genome

class Tile_State(IntEnum):
    boundary = -1
    clean = 0
    dirty = 1

class World:
    def __init__(self, w, h, goomba_genomes, gen_time=2000):
        self.width = w
        self.height = h

        self.gen_time = gen_time
        self.steps = 0

        distrib = [Tile_State.boundary]*2 + [Tile_State.dirty] + [Tile_State.clean]*7

        self.state = [[choice(distrib) for _ in range(w)] for _ in range(h)]

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

        starts = sample(poss_starts, len(goomba_genomes))
        self.goombas = [Goomba(s, p) for s, p in zip(goomba_genomes, starts)]

        self.suck_distrib = [Tile_State.clean]*3 + [Tile_State.dirty]


    @classmethod
    def random_goombas(cls, w, h, num_goombas, meta, gen_len_range, gen_time=2000):
        gens = [Genome.random_coding(meta, randrange(*gen_len_range)) for _ in range(num_goombas)]
        gen_seqs = [genome.sequences() for genome in gens]
        return cls(w, h, gen_seqs, gen_time)

    def set_tile(self, x, y, v):
        if self.is_in_bounds(x, y):
            self.state[x][y] = v

    def get_tile(self, x, y):
        if self.is_in_bounds(x, y):
            return self.state[x][y]
        return Tile_State.boundary

    def is_in_bounds(self, x, y):
        return x >= 0 and x < self.width and y >= 0 and y < self.height

    def step(self):
        """Step the world once, moving all goombas within it."""

        self.steps += 1

        for goomba in self.goombas:
            goomba.sense(self)
            goomba.think()
            goomba.choose_action()
            goomba.perform_action(self)
           
    
