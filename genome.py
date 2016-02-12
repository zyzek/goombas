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

metagenome, composed of floating point numbers, like <gene>
    <fuzziness>         determines the fuzziness of the comparison operators
    three <r><g><b>     triplets determining colour
    <mute_mute_rate>    determining the mutation rate of the mutation rate genes
    <genome_mute_rate>  mute rate of genome mutations
    individual relative genome mute rates: <insert>, <dupe>, <delete>, <invert>, <mutegene>

"""


"""
    Genome-level mutations:
        insertion,
        duplication,
        deletion,
        inversion
    Gene-level mutations:
        Operations on numbers:
            zero
            increment
            decrement
            increase 10%
            decrease 10%
        Operations on operators
            random operation
            increment
            decrement
            convert to constant
        Operations on leaves
            convert type (const, pure, impure, sensor)

"""

from functree import Op, FTreeNode, FTreeRef, RefType, parse_func
from enum import IntEnum

class GenomeMutes(IntEnum):
    Insert = 0
    Dupe = 1
    Delete = 2
    Invert = 3
    MuteGene = 4

class Gene:
    def __init__(self, action, function):
        self.function = function
        self.action = action

    def evaluate(self):
        return self.function()

class Genome:
    def __init__(self, meta, sequence):

        # Set up first the metagenome
        meta_genes = [float(g) for g in meta.strip().split()]

        self.fuzziness = meta_genes[0]

        self.colors = [meta_genes[i:i+3] + [1.0] for i in range(1, 12, 3)]

        self.mute_mute_rate = meta_genes[13]
        self.genome_mute_rate = meta_genes[14]
        self.genome_rel_mute_rates = []
        total = 0

        # Running sum, for later random selection.
        for i in range(15, 20):
            total += meta_genes[i]
            self.genome_rel_mute_rates.append(total)

        # Normalised
        for i in range(len(self.genome_rel_mute_rates)):
            self.genome_rel_mute_rates[i] /= total

        self.genome_rel_mute_rates = zip(list(GenomeMutes), self.genome_rel_mute_rates)


        # Now handle the behavioural genes
        gene_sequences = [s.strip().split() for s in sequence.split("|")]
        self.genes = [Gene(None, None) for _ in range(len(gene_sequences))]

        for i in range(len(self.genes)):
            action = int(gene_sequences[i].pop(0))
            func = parse_func(gene_sequences[i])
            self.fuzzify(func)
            self.genes[i].action = action
            self.genes[i].function = func

        self.link()

    def link(self):
        for i in range(len(self.genes)):
            self.link_func(self.genes[i].function, i)

    def link_func(self, func_node, index):
        if isinstance(func_node, FTreeNode):
            self.link_func(func_node.left, index)
            self.link_func(func_node.right, index)
        elif isinstance(func_node, FTreeRef):
            ref_index = (func_node.val + index) % len(self.genes)
            if func_node.reftype == RefType.Pure_Offset_Call:
                func_node.ref = self.genes[ref_index].function
            elif func_node.reftype == RefType.Impure_Offset_Call:
                ref_index = (func_node.val + index) % len(self.genes)

    def fuzzify(self, func_node):
        if isinstance(func_node, FTreeNode):
            # Replace equality and comparison operators with fuzzy versions
            if func_node.operator == Op.Equ:
                func_node._evaluate_ = lambda l, r: max(0, (self.fuzziness - abs(l - r))) / self.fuzziness
            elif func_node.operator == Op.Les:
                func_node._evaluate_ = lambda l, r: min(self.fuzziness, max(0, r - l)) / self.fuzziness
            elif func_node.operator == Op.Gre:
                func_node._evaluate_ = lambda l, r: min(self.fuzziness, max(0, l - r)) / self.fuzziness

            self.fuzzify(func_node.left)
            self.fuzzify(func_node.right)

    def mutate(self):
        # 2. Iterate through genome, checking each item for mutation
        # 3. Apply mutations
        # 4. Reset genome consistency
        # 5. Mutate the metagenome
        pass
    
    def __len__(self):
        return len(self.genes)

