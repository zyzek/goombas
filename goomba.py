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
from random import randint
from enum import Enum
import functree

class Action(Enum):
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

Effects = [Action.Forward, Action.Backward, 
           Action.LeftTurn, Action.RightTurn, Action.Suck, Action.Wait]

class Sensor(Enum):
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

    
class Goomba:
    EXEC_STACK_SIZE = 10
    NUM_INIT_FUNS = 30
    GENE_QUEUE_SIZE = 100
    MEM_SIZE = 200
    
    def __init__(self, sequence, pos=[0,0], ori=[0,1]):
        self.pos = pos
        self.ori = ori
        
        self.sensors = {Sensor.Tile: 0,
                        Sensor.Bump: 0,
                        Sensor.Rand: 0,
                        Sensor.Left: 0,
                        Sensor.Front: 0,
                        Sensor.Right: 0}
        self.state = 0

        self.intent_weights = {e: 0 for e in Effects}
        self.intent = Action.Wait
        
        self.gene_queue = deque([], Goomba.GENE_QUEUE_SIZE)
        self.exec_depth = 0
        self.memory = deque([], Goomba.MEM_SIZE)

        self.genome = Genome(sequence)
        self.express_genome()
        self.expr_order = list(range(len(self.genome)))
        
        self.score = 0
    

    def express_genome(self):
        """Hook up genome function references so that it can operate within an agent."""
        for gene in self.genome.genes:
            func_refs = functree.all_ref_nodes(gene.function)
            
            for ref in func_refs:
                if ref.reftype == RefType.Pure_Offset_Call:
                    ref.ref = lambda: self.run_func(ref.ref)
                elif ref.reftype == RefType.Impure_Offset_Call:
                    ref.ref = lambda: self.run_gene(ref.ref)
                elif ref.reftype == RefType.Poll_Sensor:
                    sensor = int(ref.name[1:])
                    
                    if sensor == Sensor.PosX:
                        ref.ref = lambda: self.pos[0]
                    elif sensor == Sensor.PosY:
                        ref.ref = lambda: self.pos[1]
                    elif sensor == Sensor.OriX:
                        ref.ref = lambda: self.ori[0]
                    elif sensor == Sensor.OriY:
                        ref.ref = lambda: self.ori[1]
                    elif sensor == Sensor.State:
                        ref.ref = lambda: self.state
                    elif sensor == Sensor.Mem:
                        ref.ref = lambda: self.peek_memory
                    else:
                        ref.ref = lambda: self.sensors[sensor]
            
    def peek_memory(self):
        if len(self.memory) > 0:
            return self.memory[-1]
        return 0

    def run_func(self, f):
        """Run a pure function, respecting max recursion depth."""
        if self.exec_depth >= Goomba.EXEC_STACK_SIZE:
            return 0
        
        self.exec_depth += 1
        retval = f()
        self.exec_depth -= 1

        return retval

    def run_gene(self, g):
        """Run a gene's function and execute its action, respecting max recursion depth."""
        if self.exec_depth >= Goomba.Stack_Size:
            return 0

        self.exec_depth += 1
        retval = g.evaluate()
        gedanken_action(g.action, retval)
        self.exec_depth -= 1

        return retval

    def gedanken_action(self, action, val):
        index = round(val) % self.genome.size()
        # We wrap out-of-range indices so that genes are not useless over most of their range

        if action == Action.Nop:
            pass
        elif action == Action.Call:
            if len(self.gene_queue) < Goomba.GENE_QUEUE_SIZE:
                self.gene_queue.append(self.genome.gene[index])
        elif action == Action.Promote:
            order_index = expr_order.index(index)
            if order_index != 0:
                expr_order[order_index] = expr_order[order_index - 1]
                expr_order[order_index - 1] = index
        elif action == Action.Demote:
            order_index = expr_order.index(index)
            if order_index != self.genome.size() - 1:
                expr_order[order_index] = expr_order[order_index + 1]
                expr_order[order_index + 1] = index
        elif action == Action.Remember:
            self.memory.append(val)
        elif action == Action.Forget:
            if len(self.memory) > 0:
                self.memory.pop()
        elif action == Action.SetState:
            self.state = value
        else:
            self.intent_weights[action] += val
            
    def sense(self, w):
        """World calls me to set sensor vals once per step."""
        self.sensors[Sensor.Tile] = w.get_tile(*self.pos)
        self.sensors[Sensor.Rand] = randint(0,1)

        fcoord = [self.pos[0]+self.ori[0], self.pos[1]+self.ori[1]]
        lcoord = [self.pos[0]-self.ori[1], self.pos[1]+self.ori[0]]
        rcoord = [self.pos[0]+self.ori[1], self.pos[1]-self.ori[0]]

        self.sensors[Sensor.Front] = w.get_tile(*fcoord)
        self.sensors[Sensor.Left] = w.get_tile(*lcoord)
        self.sensors[Sensor.Right] = w.get_tile(*rcoord)

    def fresh_intent(self):
        self.intent = Action.Wait
        self.intent_weights = {e: 0 for e in Effects}
        self.gene_queue.clear()

    def think(self):
        self.fresh_intent()
        for i in range(min(Goomba.NUM_INIT_FUNS, len(self.expr_order))):
            self.gene_queue.append(self.genome.genes[i])
        
        i = 0
        while i < len(self.gene_queue):
            gene = self.gene_queue[i]
            self.run_gene(gene)
            i += 1
        
    def choose_action(self):
        strongest = (Action.Wait, 0)
        for impulse in self.intent_weights:
            if impulse[1] >= strongest[1]:
                strongest = impulse
        self.intent = m[0]

    
        
