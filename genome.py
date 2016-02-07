"""

A Genome is a sequence of genes each of which is first a number determining
what action the gene contributes to, followed by an arithmetic expression in
polish notation, whose operators include:
    + - / * ^ < > =
Leaf nodes in the arithmetic tree, the atoms of the arithmetic include:
    numbers; 
    sensors: <px>, <py>, <ox>, <oy>, <t>, <b>, <r>, <sf>, <sl>, <sr>, <s>, <m>
    [n] the result of calling the function in the gene n places along the genome
    {n} the result of evaluating the function of the gene n places along, and performing its action

Actions:
    Forward, Backwards, LeftTurn, RightTurn, Suck, Nop are as they appear
    Then, where V represents the value of the gene's function
    Call: add a call to the function [V] places along the genome to the function queue
    Promote: Promote a gene [V] places along  to the top of this goomba's expression order
    Demote: Demote a gene [V] places along to the bottom of the expression order

When a genome is instantiated from a sequence, it builds the corresponding function,
However, if not inside an agent, it's possible to encode infinite recursive loops,
and sensors are obviously not hooked up to anything.
"""

from enum import Enum
from functree import Op, stringops, FTreeNode, FTreeRef, FTreeConst, RefType
from goomba.py import Action


class Gene:
    def __init__(self, action, function):
        self.function = function
        self.action = action

    def evaluate(self):
        return self.function()

# TODO: Consider switching to undelimited genes. Investigate gene separation at parse fail point.
class Genome:
    def __init__(self, sequence):
        gene_sequences = [s.strip().split() for s in sequence.split("|")]
        
        self.fuzziness = float(gene_sequences[0][0])
        del gene_sequences[0]

        self.genes = [Gene(None, None) for _ in range(len(gene_sequences))]

        for i in range(self.size()):
            action = int(gene_sequences[i].pop(0))
            func = parse_gene(gene_sequences[i], i, self)
            self.genes[i].action = action
            self.genes[i].function = func

    def size(self):
        return len(self.genes)

class Delim(Enum):
    Pure = '['
    Impure = '{'
    Sensor = '<'

def parse_gene(sequence, gene_index, genome):
    curr_sym = sequence.pop(0)
    node = None
    
    if curr_sym in stringops:
        # binary operator

        left = parse_gene(sequence, gene_index, genome.genes)
        right = parse_gene(sequence, gene_index, genome.genes)
        
        node = FTreeNode(stringops[curr_sym], left, right)
        
        # Replace equality and comparison operators with fuzzy versions
        if node.op == Op.Eq:
            f = lambda l, r: max(0, (genome.fuzziness - abs(l - r))) / genome.fuzziness
            node._evaluate_ = f
        elif node.op == Op.LT:
            f = lambda l, r: min(genome.fuzziness, max(0, r - l)) / genome.fuzziness
            node._evaluate_ = f
        elif node.op == Op.GT:
            f = lambda l, r: min(genome.fuzziness, max(0, l - r)) / genome.fuzziness
            node._evaluate_ = f

    elif curr_sym[0] == Delim.Pure:
        # offset gene no action
        
        offset = int(curr_sym[1:-1])
        index = (gene_index + offset) % len(genome.genes)

        #index = max(0, min(gene_index + offset, len(genome.genes) - 1)) #clamped

        node = FTreeRef(genome.genes[index].function, RefType.Pure_Offset_Call, curr_sym)
        # We make sure that the genotype itself is not clamped. Numbers out of range might
        # become meaningful after mutation.
    elif curr_sym[0] == Delim.Impure:
        # offset gene with action

        offset = int(curr_sym[1:-1])
        index = (gene_index + offset) % len(genome.genes)
        
        #index = max(0, min(gene_index + offset, len(genome.genes) - 1)) 

        node = FTreeRef(genome.genes[index], RefType.Impure_Offset_Call, curr_sym)
    elif curr_sym[0] == Delim.Sensor:
        # poll sensor

        node = FTreeRef(lambda: 0, RefType.Poll_Sensor, curr_sym)
    else:
        # otherwise, assume integer

        node = FTreeConst(int(curr_sym))

    return node

