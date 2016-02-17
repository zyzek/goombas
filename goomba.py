""" Specification:

    World:  A rectangular grid of cells which may be either boundaries, clean, or dirty.

    Agent:  A robotic vacuum cleaner which must suck up dirt.
            Sensors:
                Current position and orientation: robot always knows its absolute coordinates.
                Current tile: robot can tell if the current tile is clean or dirty.
                Bump: active if the last move tried to go through a boundary
                Random: returns either 0 or 1 randomly

            Actuators:
                Move: the vacuum can move forward one tile in the direction it is facing,
                      but not onto a boundary.
                Rotate: the vacuum may rotate either left or right a quarter turn
                Suck: the vacuum can suck up dirt, but it has a 25% chance of dirtying any tile
                      that it sucks on.
            Mind:
                State:  an integer representing the current state of the vacuum
                Memory: a robot possesses a stack of values it can push, pop, peek.
                        Top value is zero if empty.
                Program: The robot has a queue of functions to compute on a given turn,
                         top n executed, highest weight action from summation of said functions
                         is executed.
                Also: execution stack to prevent loops,
                Also: genetic activation/promotion

                Actions:
                    Move Forwards, Move backwards
                    Turn Left, Turn Right
                    Suck,
                    Nop,
                    Call Function +val places forward in the genome
                    Promote Function +val places forward in the genome
                    Demote Function +val places forward in the genome

    Perf:   The robot is given a period of time to traverse the world, and its final score is:
            10 * (net dirt sucked up)
            - (actions performed (anything other than Nop))
            - (computations performed) / 100
            - 100 * (1 - (genome size / largest genome))

            In other words, a bot is rewarded for sucking up a lot of dirt,
            for not wasting energy moving around,
            for being computationally efficient,
            for having a small genome

    Todo: work out how to go to a particular state or offset, how to handle coordinates,
          how to deal with gene regulation.
"""

from collections import deque
from random import randint, choice, random
from enum import IntEnum
from functree import RefType
import world
import genome

class Action(IntEnum):
    """ All actions a goomba may perform.

    Nop: do nothing at all.
    Forward: Move forward one square.
    Backward: Move backward one square.
    LeftTurn: Rotate anti-clockwise a quarter of a turn.
    RightTurn: Rotate clockwise a quarter of a turn.
    Suck: Attempt to suck up dirt from the current tile.
    Wait: Sit still.
    Call: Add a gene to the expression queue.
    Promote: Promote a gene one rank in the expression order.
    Demote: Demote a gene one rank in the expression order.
    Remember: Push a value to the stack.
    Forget: Pop the top value from the stack.
    SetState: set the current state.
    """

    Nop = 0
    Forward = 1
    Backward = 2
    LeftTurn = 3
    RightTurn = 4
    Suck = 5
    Wait = 6
    Call = 7
    Promote = 8
    Demote = 9
    Remember = 10
    Forget = 11
    SetState = 12

# Actions that actually affect the world.
EFFECTS = [Action.Forward, Action.Backward,
           Action.LeftTurn, Action.RightTurn, Action.Suck, Action.Wait]

class Sensor(IntEnum):
    """All sensors a goomba has access to.

    Bump: 1 if goomba attempted an impossible move last step, 0 otherwise.
    Rand: randomly 1 or 0 in a given timestep.
    Tile: the state of the tile directly underneath the goomba 0 for clean, 1 for dirty.
    Left, Right, Front: state of the tiles located in the orthogonal directions, sans behind.
    PosX, PosY: the bot's absolute position.
    OriX, OriY: the bot's absolute orientation: sum of position and orientation is one move forward.
                |OriX| + |OriY| = 1
    State: the current internal state of the goomba.
    Mem: the value of the item at the top of the goomba's memory stack; 0 if empty.
    """

    Bump = 0
    Rand = 1
    Tile = 2
    Left = 3
    Right = 4
    Front = 5
    PosX = 6
    PosY = 7
    OriX = 8
    OriY = 9
    State = 10
    Mem = 11

class Count(IntEnum):
    Dirt = 0
    FwdMoves = 1
    BckwdMoves = 2
    Bumps = 3
    LeftTurns = 4
    RightTurns = 5
    Sucks = 6
    Thoughts = 7
    GenomeSize = 8
    TilesCovered = 9


class Goomba:
    """An autonomous robotic vacuum cleaner whose behaviour is genetically-determined."""

    # Keep this relatively low: if d is the execution stack size, L the gene queue size,
    # a goomba performs O(L * d * 2^d) function calls -- note that exponential term.
    EXEC_STACK_SIZE = 5
    NUM_INIT_FUNS = 30
    GENE_QUEUE_SIZE = 100
    MEM_SIZE = 200

    COUNT_VALUES = {Count.Dirt: 1000,
                    Count.FwdMoves: -10,
                    Count.BckwdMoves: -10,
                    Count.Bumps: -50,
                    Count.LeftTurns: -10,
                    Count.RightTurns: -10,
                    Count.Sucks: 20,
                    Count.Thoughts: -0.1, 
                    Count.GenomeSize: -5,
                    Count.TilesCovered: 100}

    SHAPE = [(-0.1, 0.3),
             (0.1, 0.3),
             (0.3, -0.3),
             (-0.3, -0.3)]

    SUCK_FAIL_PROB = 0.25

    def __init__(self, gen, pos=None):
        if pos is None:
            self.pos = [0, 0]
        else:
            self.pos = pos

        self.ori = choice([[1, 0], [-1, 0], [0, 1], [0, -1]])

        self.sensors = {Sensor.Tile: 0,
                        Sensor.Bump: 0,
                        Sensor.Rand: 0,
                        Sensor.Left: 0,
                        Sensor.Front: 0,
                        Sensor.Right: 0}
        self.state = 0

        self.intent_weights = {e: 0 for e in EFFECTS}
        self.intent = Action.Wait

        self.gene_queue = deque([], Goomba.GENE_QUEUE_SIZE)
        self.exec_depth = 0
        self.memory = deque([], Goomba.MEM_SIZE)

        self.genome = gen
        self.express_genome()
        self.expr_order = list(range(len(self.genome)))
        
        self.tiles_covered = set()

        self.counts = {k: 0 for k in list(Count)}
        self.counts[Count.GenomeSize] = self.genome.size()

    @classmethod
    def from_sequences(cls, sequences, pos=None):
        gen = genome.Genome(*sequences)
        return cls(gen, pos)


    def express_genome(self):
        """Hook up genome function references so that it can operate within an agent."""
        
        def make_run_func(ref):
            return lambda: self.run_func(ref)
        def make_run_gene(ref):
            return lambda: self.run_gene(ref)

        sensor_funcs = {Sensor.PosX: (lambda: self.pos[0]),
                        Sensor.PosY: (lambda: self.pos[1]),
                        Sensor.OriX: (lambda: self.ori[0]),
                        Sensor.OriY: (lambda: self.ori[1]),
                        Sensor.State: (lambda: self.state),
                        Sensor.Mem: (self.peek_memory),
                        Sensor.Bump: (lambda: self.sensors[Sensor.Bump]),
                        Sensor.Tile: (lambda: self.sensors[Sensor.Tile]),
                        Sensor.Front: (lambda: self.sensors[Sensor.Front]),
                        Sensor.Left: (lambda: self.sensors[Sensor.Left]),
                        Sensor.Right: (lambda: self.sensors[Sensor.Right]),
                        Sensor.Rand: (lambda: self.sensors[Sensor.Rand])}

        for gene in self.genome.genes:
            func_refs = [n for n in gene.function.as_list() if n.is_leaf()]

            for ref in func_refs:
                if ref.ref_type == RefType.Pure_Offset_Call:
                    ref.ref = make_run_func(ref.ref)
                elif ref.ref_type == RefType.Impure_Offset_Call:
                    ref.ref = make_run_gene(ref.ref)
                elif ref.ref_type == RefType.Poll_Sensor:
                    sensor = Sensor(round(ref.val) % len(Sensor))

                    if sensor in sensor_funcs:
                        ref.ref = sensor_funcs[sensor]
                    else:
                        ref.ref = lambda: 0

    def peek_memory(self):
        """Examine the value at the top of the mem stack, 0 if stack is empty."""
        if len(self.memory) > 0:
            return self.memory[-1]
        return 0

    def run_func(self, func):
        """Run a pure function, respecting max recursion depth."""
        if self.exec_depth >= Goomba.EXEC_STACK_SIZE:
            return 0

        self.exec_depth += 1
        retval = func()
        self.exec_depth -= 1

        self.counts[Count.Thoughts] += 1

        return retval

    def run_gene(self, gene):
        """Run a gene's function and execute its action, respecting max recursion depth."""
        if self.exec_depth >= Goomba.EXEC_STACK_SIZE:
            return 0

        self.exec_depth += 1
        retval = gene.evaluate()
        self.gedanken_action(gene.action, retval)
        self.exec_depth -= 1

        self.counts[Count.Thoughts] += 1

        return retval

    def gedanken_action(self, action, val):
        """Hypothesise an action.

        If an action has a world-effect, add val to that action's intent_weight.
        Otherwise, it is a mental activity: perform it.
        """

        index = round(val) % len(self.genome)
        # We wrap out-of-range indices so that genes are not useless over most of their range

        if action == Action.Nop:
            pass
        elif action == Action.Call:
            if len(self.gene_queue) < Goomba.GENE_QUEUE_SIZE:
                self.gene_queue.append(self.genome.genes[index])
        elif action == Action.Promote:
            order_index = self.expr_order.index(index)
            if order_index != 0:
                self.expr_order[order_index] = self.expr_order[order_index - 1]
                self.expr_order[order_index - 1] = index
        elif action == Action.Demote:
            order_index = self.expr_order.index(index)
            if order_index != len(self.genome) - 1:
                self.expr_order[order_index] = self.expr_order[order_index + 1]
                self.expr_order[order_index + 1] = index
        elif action == Action.Remember:
            self.memory.append(val)
        elif action == Action.Forget:
            if len(self.memory) > 0:
                self.memory.pop()
        elif action == Action.SetState:
            self.state = val
        else:
            self.intent_weights[action] += val

    def sense(self, wrld):
        """World calls me to set sensor vals once per step."""
        self.sensors[Sensor.Tile] = wrld.get_tile(*self.pos)
        self.sensors[Sensor.Rand] = randint(0, 1)

        fcoord = [self.pos[0]+self.ori[0], self.pos[1]+self.ori[1]]
        lcoord = [self.pos[0]-self.ori[1], self.pos[1]+self.ori[0]]
        rcoord = [self.pos[0]+self.ori[1], self.pos[1]-self.ori[0]]

        self.sensors[Sensor.Front] = wrld.get_tile(*fcoord)
        self.sensors[Sensor.Left] = wrld.get_tile(*lcoord)
        self.sensors[Sensor.Right] = wrld.get_tile(*rcoord)

    def fresh_intent(self):
        """Reset this goomba's intent weights and expression queue."""
        self.intent = Action.Wait
        self.intent_weights = {e: 0 for e in EFFECTS}
        self.gene_queue.clear()

    def think(self):
        """Consider this goomba's actions.

        Populate the expression queue from the expression order,
        run all genes until the queue fills up or there are none left to run.
        This should populate intent_weights."""

        self.fresh_intent()
        for i in range(min(Goomba.NUM_INIT_FUNS, len(self.expr_order))):
            self.gene_queue.append(self.genome.genes[i])

        i = 0
        while i < len(self.gene_queue):
            gene = self.gene_queue[i]
            self.run_gene(gene)
            i += 1

    def choose_action(self):
        """After having populated intent_weights, choose the strongest to actually perform."""

        strongest = (Action.Wait, 0)
        for impulse in self.intent_weights.items():
            if impulse[1] >= strongest[1]:
                strongest = impulse
        self.intent = strongest[0]


    def perform_action(self, wrld):
        action = self.intent

        self.sensors[Sensor.Bump] = 0

        if action == Action.Forward:
            self.move_forward(wrld)
        elif action == Action.Backward:
            self.move_backward(wrld)
        elif action == Action.LeftTurn:
            self.turn_left()
        elif action == Action.RightTurn:
            self.turn_right()
        elif action == Action.Suck:
            self.suck(wrld)

    def turn_left(self):
        """Rotate an agent anti-clockwise a quarter-turn."""
        self.ori = [-self.ori[1], self.ori[0]]
        self.counts[Count.LeftTurns] += 1

    def turn_right(self):
        """Rotate an agent clockwise a quarter-turn."""
        self.ori = [self.ori[1], -self.ori[0]]
        self.counts[Count.RightTurns] += 1

    def move_forward(self, wrld):
        """ Move an agent one tile in the anti-facing direction."""
        newpos = [p+o for p, o in zip(self.pos, self.ori)]
        if wrld.is_in_bounds(*newpos) and wrld.get_tile(*newpos) != world.Tile_State.boundary:
            self.pos = newpos
            self.counts[Count.FwdMoves] += 1
        else:
            self.counts[Count.Bumps] += 1
            self.sensors[Sensor.Bump] = 1

        if tuple(self.pos) not in self.tiles_covered:
            self.counts[Count.TilesCovered] += 1
            self.tiles_covered.add(tuple(self.pos))
    
    def move_backward(self, wrld):
        """ Move an agent one tile in the anti-facing direction."""
        newpos = [p-o for p, o in zip(self.pos, self.ori)]
        if wrld.is_in_bounds(*newpos) and wrld.get_tile(*newpos) != world.Tile_State.boundary:
            self.pos = newpos
            self.counts[Count.BckwdMoves] += 1
        else:
            self.counts[Count.Bumps] += 1
            self.sensors[Sensor.Bump] = 1

    def suck(self, wrld):
        """Attempt to clean the dirt from a given tile.
        There is a chance that the tile will be made dirty instead of clean.
        No effect on boundary tiles.
        """

        self.counts[Count.Sucks] += 1
        x, y = self.pos
        tile_before = wrld.get_tile(x, y)

        if wrld.is_in_bounds(x, y) and (tile_before != world.Tile_State.boundary):
            tile_after = world.Tile_State.clean
            if random() < Goomba.SUCK_FAIL_PROB:
                tile_after = world.Tile_State.dirty

            if (tile_before == world.Tile_State.clean) and \
                    (tile_after == world.Tile_State.dirty) and \
               self.counts[Count.Dirt] > 0:

                wrld.set_tile(x, y, tile_after)
                self.counts[Count.Dirt] -= 1
            
            elif (tile_before == world.Tile_State.dirty) and \
                 (tile_after == world.Tile_State.clean):
                wrld.set_tile(x, y, tile_after)
                self.counts[Count.Dirt] += 1

    def score(self):
        if self.counts[Count.FwdMoves] + self.counts[Count.BckwdMoves] == 0:
            return -9999999999999999999

        score = 0

        for count in list(Count):
            score += self.counts[count]*Goomba.COUNT_VALUES[count]

        return score



def breed(mum, dad):
    new_genome = genome.cross_genomes(mum.genome, dad.genome)
    new_genome.mutate()
    return Goomba(new_genome)
    

