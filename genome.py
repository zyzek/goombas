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

from functree import Op, STRING_OPS, FTreeNode, FTreeRef, FTreeConst, RefType


class Gene:
    def __init__(self, action, function):
        self.function = function
        self.action = action

    def evaluate(self):
        return self.function()

class Genome:
    def __init__(self, sequence):
        gene_sequences = [s.strip().split() for s in sequence.split("|")]

        self.fuzziness = float(gene_sequences[0][0])
        del gene_sequences[0]

        colorvals = [float(v) for v in gene_sequences[0]]
        self.colors = [colorvals[i:i+3] + [1.0] for i in range(0, len(colorvals), 3)]


        del gene_sequences[0]

        self.genes = [Gene(None, None) for _ in range(len(gene_sequences))]

        for i in range(self.size()):
            action = int(gene_sequences[i].pop(0))
            func = parse_gene(gene_sequences[i], i, self)
            self.genes[i].action = action
            self.genes[i].function = func

    def size(self):
        return len(self.genes)

class RefDelim():
    Pure = '['
    Impure = '{'
    Sensor = '$'

def parse_gene(sequence, gene_index, genome):
    curr_sym = sequence.pop(0)
    node = None

    if curr_sym in STRING_OPS:
        # binary operator

        left = parse_gene(sequence, gene_index, genome)
        right = parse_gene(sequence, gene_index, genome)

        node = FTreeNode(STRING_OPS[curr_sym], left, right)

        # Replace equality and comparison operators with fuzzy versions
        if node.operator == Op.Equ:
            node._evaluate_ = lambda l, r: max(0, (genome.fuzziness - abs(l - r))) / genome.fuzziness
        elif node.operator == Op.Les:
            node._evaluate_ = lambda l, r: min(genome.fuzziness, max(0, r - l)) / genome.fuzziness
        elif node.operator == Op.Gre:
            node._evaluate_ = lambda l, r: min(genome.fuzziness, max(0, l - r)) / genome.fuzziness

    elif curr_sym[0] == RefDelim.Pure:
        # offset gene no action

        offset = int(curr_sym[1:])
        index = (gene_index + offset) % len(genome.genes)
        node = FTreeRef(genome.genes[index].function, RefType.Pure_Offset_Call, curr_sym)
    elif curr_sym[0] == RefDelim.Impure:
        # offset gene with action

        offset = int(curr_sym[1:])
        index = (gene_index + offset) % len(genome.genes)
        node = FTreeRef(genome.genes[index], RefType.Impure_Offset_Call, curr_sym)
    elif curr_sym[0] == RefDelim.Sensor:
        # poll sensor

        node = FTreeRef(lambda: 0, RefType.Poll_Sensor, curr_sym)
    else:
        # otherwise, assume integer

        node = FTreeConst(int(curr_sym))

    return node

