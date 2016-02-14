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
    <low> <high>        the range of values possible for newly-generated floats
    <fun_gen_depth>     the maximum depth that a newly-generated random function may extend to
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
            increment op
            decrement op
            swap operands
            convert to leaf
        Operations on leaves
            convert type (const, pure, impure, sensor)
            add operator above
            convert to larger subtree
"""

import random
from enum import IntEnum
from functree import Op, FTreeNode, FTreeLeaf, RefType, parse_func
import goomba
class GenomeMutes(IntEnum):
    Insert = 0
    Dupe = 1
    Delete = 2
    Invert = 3
    MuteGene = 4

class EnumMutes(IntEnum):
    increment = 0
    decrement = 1
    random = 2

class NumMutes(IntEnum):
    zero = 0
    increment = 1
    decrement = 2 #TODO: Make the summand genetically determined
    incremult = 3
    decremult = 4 #TODO: Make the factor genetically determined


class Gene:
    def __init__(self, action, function):
        self.function = function
        self.action = action

    @classmethod
    def random(cls, max_depth, gen_len, const_bounds):
        action = random.choice(list(goomba.Action))
        function = FTreeNode.random(max_depth, gen_len, const_bounds)
        return cls(action, function)

    def evaluate(self):
        return self.function()

    def mutate(self):
        #TODO: FILLME
        pass

    def copy(self):
        return Gene(self.action, self.function.copy())

class Genome:
    def __init__(self, meta, sequence):

        # Set up first the metagenome
        meta_genes = [float(g) for g in meta.strip().split()]

        self.fuzziness = meta_genes[0]
        self.const_bounds = [meta_genes[1], meta_genes[2]]
        self.fun_gen_depth = meta_genes[3]

        self.colors = [meta_genes[i:i+3] + [1.0] for i in range(4, 15, 3)]

        self.mute_rates = {}
        self.mute_rates["mute"] = meta_genes[16]
        self.mute_rates["genome"] = meta_genes[17]

        for key, val in zip(list(GenomeMutes), meta_genes[18:23]):
            self.mute_rates[key] = val

        genome_rel_mute_rates = []
        total = 0

        # Running sum, for later random selection.
        for k in list(GenomeMutes):
            total += self.mute_rates[k]
            genome_rel_mute_rates.append(total)

        # Normalised
        for i, _ in enumerate(genome_rel_mute_rates):
            genome_rel_mute_rates[i] *= self.mute_rates["genome"] / total

        genome_rel_mute_rates = list(zip(list(GenomeMutes), genome_rel_mute_rates))
        self.mute_rates["genome_rel"] = genome_rel_mute_rates

        # Now handle the behavioural genes
        gene_sequences = [s.strip().split() for s in sequence.split("|")]
        self.genes = [Gene(None, None) for _ in range(len(gene_sequences))]

        for i in range(len(self.genes)):
            action = goomba.Action(int(gene_sequences[i].pop(0)))
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
        elif isinstance(func_node, FTreeLeaf):
            ref_index = (func_node.val + index) % len(self.genes)
            if func_node.ref_type == RefType.Pure_Offset_Call:
                func_node.ref = self.genes[ref_index].function
            elif func_node.ref_type == RefType.Impure_Offset_Call:
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
        # 1. Iterate through genome, checking each item for mutation
        i = 0
        while i < len(self):

            # 2. Check if the gene mutates.
            rand = random.random()
            mutation = None
            for k, v in self.mute_rates["genome_rel"]:
                if rand < v:
                    mutation = k
                    break

            # 3. Apply appropriate mutations, if any.
            if mutation:
                fuzz = -1
                if mutation == GenomeMutes.Insert:
                    new_gene = Gene.random(round(self.fun_gen_depth), len(self), self.const_bounds)
                    self.genes.insert(i, new_gene)
                    fuzz = i
                    i += 1
                elif mutation == GenomeMutes.Dupe:
                    self.genes.insert(i, self.genes[i].copy())
                    fuzz = i
                    i += 1
                elif mutation == GenomeMutes.Delete:
                    del self.genes[i]
                    i -= 1
                elif mutation == GenomeMutes.Invert:
                    swapindex = (i + 1)%len(self)
                    tmp = self.genes[i]
                    self.genes[i] = self.genes[swapindex]
                    self.genes[swapindex] = tmp
                elif mutation == GenomeMutes.MuteGene:
                    self.genes[i].mutate()
                    fuzz = i

                if fuzz != -1:
                    self.fuzzify(self.genes[fuzz].function)
            i += 1

        # 4. Reset genome consistency
        self.link()

        # 5. Mutate the metagenome
        # fuzz [0.0, inf)
        # const bounds (-inf, inf), but small smaller than large
        # fun gen depth [0.0, 1.0]
        # colors [0.0, 1.0]
        # mute_rates "mute", "genome" [0.0, 1.0]
        # other mute_rates [0.0, inf)
        #TODO FILLME

    def __len__(self):
        return len(self.genes)

