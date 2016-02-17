from enum import IntEnum
from random import choice, sample, randrange
from math import ceil
from numpy import linspace

from goomba import Goomba, breed
from genome import Genome
from util import weighted_choice

class Tile_State(IntEnum):
    boundary = -1
    clean = 0
    dirty = 1

class World:
    CLONE_BEST_FRACTION = 0.05
    BREED_FRACTION = 0.5
    REPRO_SUCCESS_RAMP = 5
    NEW_RANDOM_FRACTION = 0.01

    def __init__(self, w, h, goomba_genomes, seed_meta, gen_len_range, gen_time=200):
        self.width = w
        self.height = h

        self.seed_meta = seed_meta
        self.gen_len_range = gen_len_range

        self.gen_time = gen_time
        self.steps = 0
        self.generation = 0

        distrib = [Tile_State.boundary]*2 + [Tile_State.dirty] + [Tile_State.clean]*7

        self.state = [[choice(distrib) for _ in range(w)] for _ in range(h)]

        for i in range(w):
            self.state[i][0] = Tile_State.boundary
            self.state[i][h-1] = Tile_State.boundary
        for j in range(h):
            self.state[0][j] = Tile_State.boundary
            self.state[w-1][j] = Tile_State.boundary

        self.init_dirt_distrib = []

        for y in range(self.height):
            for x in range(self.width):
                if self.state[x][y] == Tile_State.dirty:
                    self.init_dirt_distrib.append((x, y))


        starts = self.start_locations(len(goomba_genomes))
        self.goombas = [Goomba.from_sequences(s, p) for s, p in zip(goomba_genomes, starts)]
        self.top_five = self.goombas[:5]
        self.running = True

    @classmethod
    def random_goombas(cls, w, h, num_goombas, seed_meta, gen_len_range, gen_time=200):
        gens = [Genome.random_coding(seed_meta, randrange(*gen_len_range)) for _ in range(num_goombas)]
        gen_seqs = [genome.sequences() for genome in gens]
        return cls(w, h, gen_seqs, seed_meta, gen_len_range, gen_time)
    
    def start_locations(self, num_starts):
        poss_starts = []
        for y in range(self.height):
            for x in range(self.width):
                if self.state[x][y] == Tile_State.clean:
                    poss_starts.append([x, y])

        return sample(poss_starts, num_starts)

    def reset_dirt(self):
        for x, y in self.init_dirt_distrib:
            self.state[x][y] = Tile_State.dirty
 
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
        if self.running:
            self.steps += 1

            for goomba in self.goombas:
                goomba.sense(self)
                goomba.think()
                goomba.choose_action()
                goomba.perform_action(self)

            if self.steps > self.gen_time:
                self.next_gen()
                

    def next_gen(self):
        self.running = False
        print("Generation " + str(self.generation))
        newtops = list(self.top_five)
        for goomba in self.goombas:
            for champ in self.top_five:
                if goomba.score() > champ.score():
                    newtops.append(goomba)
                    break
        
        newtops = sorted(newtops, key = lambda goomba: goomba.score(), reverse=True)
        self.top_five = newtops[:5]

        for champ in self.top_five:
            print(champ.genome.sequences())
            print(champ.counts)
            print(champ.score())
            print()

        self.breed_pop()
        self.steps = 0
        self.generation += 1
        self.reset_dirt()
        self.running = True
           
    def breed_pop(self):
        pop_size = len(self.goombas)
        num_clones = ceil(pop_size * World.CLONE_BEST_FRACTION)
        num_bred = ceil(pop_size * World.BREED_FRACTION)
        num_rand = ceil(pop_size * World.NEW_RANDOM_FRACTION)
        num_pairs = 2 * (pop_size - (num_clones + num_rand))
        
        # Order the population by final score
        ordered_pop = sorted([gmba for gmba in self.goombas],
                             key = lambda g: g.score(),
                             reverse = True)
        
        # The top few will be cloned into the next generation unchanged
        top_dogs = ordered_pop[:num_clones]
        new_goombas = [Goomba.from_sequences(dog.genome.sequences()) for dog in top_dogs]
        
        # The bottom fraction is thrown out entirely
        breeders = ordered_pop[:num_bred]

        # The remaining goombas breed, with a higher likelihood as they rank higher
        breed_weighted = dict(zip(breeders, linspace(World.REPRO_SUCCESS_RAMP, 1, len(breeders))))
        breeding_pairs = weighted_choice(breed_weighted, num_pairs)
        for i in range(0, len(breeding_pairs), 2):
            new_goombas.append(breed(breeding_pairs[i], breeding_pairs[i + 1]))

        for i in range(num_rand):
            new_goombas.append(Goomba(Genome.random_coding(self.seed_meta, 
                                                           randrange(*self.gen_len_range))))

        starts = self.start_locations(len(new_goombas))
        for gmba, pos in zip(new_goombas, starts):
            gmba.pos = pos
        
        self.goombas = new_goombas
