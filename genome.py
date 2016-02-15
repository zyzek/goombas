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
    <incr> <mult>       max value of increment or multiple factors involved in mutating constants
    3 x <r><g><b>       triplets determining colour
    <mute_mute_rate>    determining the mutation rate of the mutation rate genes
    <genome_mute_rate>  mute rate of genome mutations
    individual relative genome mute rates: <insert> <dupe> <delete> <invert> <mutegene>
    individual relative constant mute rates: <incr> <decr> <mult> <div>
    relative prevalence of leaf types: <pure_call> <impure_call> <poll_sensor> <constant>

"""


"""
    Genome-level mutations:
        insertion,
        duplication,
        deletion,
        inversion
    Gene-level mutations:
        Operations on numbers:
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
from functree import Op, FTreeNode, FTreeLeaf, RefType, parse_func, weighted_choice
import goomba

class GenomeMutes(IntEnum):
    Insert = 0
    Dupe = 1
    Delete = 2
    Invert = 3
    MuteGene = 4

class ConstMutes(IntEnum):
    Increment = 0
    Decrement = 1
    Incremult = 2
    Decremult = 3

class EnumMutes(IntEnum):
    Increment = 0
    Decrement = 1
    Random = 2


class Gene:
    def __init__(self, action, function):
        self.function = function
        self.action = action

    @classmethod
    def random(cls, max_depth, gen_len, const_bounds, leaf_weights):
        action = random.choice(list(goomba.Action))
        function = FTreeNode.random(max_depth, gen_len, const_bounds, leaf_weights)
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
        self.incr_range = meta_genes[4]
        self.mult_range = meta_genes[5]

        self.colors = [meta_genes[i:i+3] + [1.0] for i in range(6, 17, 3)]

        self.mute_rates = {}
        self.mute_rates["mute"] = meta_genes[18]
        self.mute_rates["genome"] = meta_genes[19]

        
        self.mute_rates["genome_rel"] = dict(zip(list(GenomeMutes), meta_genes[20:25]))
        self.mute_rates["const_rel"] = dict(zip(list(ConstMutes), meta_genes[25:29]))
        self.mute_rates["leaf_rel"] = dict(zip(list(RefType), meta_genes[29:33]))

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
                func_node.ref = self.genes[ref_index]

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
            if rand < self.mute_rates["genome"]:
                mutation = weighted_choice(self.mute_rates["genome_rel"])

              # 3. Apply appropriate mutations, if any.
            if mutation is not None:
                fuzz = -1
                if mutation == GenomeMutes.Insert:
                    new_gene = Gene.random(round(self.fun_gen_depth),
                                           len(self), self.const_bounds,
                                           self.mute_rates["leaf_rel"])
                    self.genes.insert(i, new_gene)
                    fuzz = i
                    i += 1
                    print("INSERT: " + str(new_gene.function))
                elif mutation == GenomeMutes.Dupe:
                    self.genes.insert(i, self.genes[i].copy())
                    fuzz = i
                    i += 1
                    print("DUPE: " + str(self.genes[i].function))
                elif mutation == GenomeMutes.Delete:
                    print("DELETE: " + str(self.genes[i].function))
                    del self.genes[i]
                    i -= 1
                elif mutation == GenomeMutes.Invert:
                    swapindex = (i + 1)%len(self)
                    print("INVERT: " + str(i) + ", " + str(swapindex))
                    tmp = self.genes[i]
                    self.genes[i] = self.genes[swapindex]
                    self.genes[swapindex] = tmp
                elif mutation == GenomeMutes.MuteGene:
                    print("MUTEGENE: " + str(self.genes[i].function))
                    self.genes[i].mutate()
                    fuzz = i

                if fuzz != -1:
                    self.fuzzify(self.genes[fuzz].function)
            i += 1

        # 4. Reset genome consistency
        self.link()

        # 5. Mutate the metagenome
        # fuzz [0.0, inf)
        self.fuzziness = self.mutated_num(self.fuzziness, self.mute_rates["genome"], 0.001, None)

        # const bounds (-inf, inf), but small smaller than large
        self.const_bounds[0] = self.mutated_num(self.const_bounds[0],
                                                self.mute_rates["genome"], None, None)
        self.const_bounds[1] = self.mutated_num(self.const_bounds[1],
                                                self.mute_rates["genome"], None, None)
        if self.const_bounds[0] > self.const_bounds[1]:
            self.const_bounds = reversed(self.const_bounds)

        # fun gen depth [0.0, 5.0]
        self.fun_gen_depth = self.mutated_by_factor(self.fun_gen_depth,
                                                    1.7, self.mute_rates["genome"], [0.001, 5.0])

        # incr_range [0.0, inf)
        self.incr_range = self.mutated_num(self.incr_range, self.mute_rates["genome"], 0.001, None)
        # mult_range [1.0, inf)
        self.mult_range = self.mutated_num(self.mult_range, self.mute_rates["genome"], 1.0, None)

        # colors [0.0, 1.0]
        for col in self.colors:
            for i, _ in enumerate(col[:3]):
                col[i] = self.mutated_by_factor(col[i], 1.2, 0.33, [0.0, 1.0])
                # Manually set colour mute rate high, for visual appeal, and no fitness value,
                # so this simply drifts


        # mute_rates "mute", "genome" [0.0, 1.0]
        self.mute_rates["mute"] = self.mutated_by_const(self.mute_rates["mute"],
                                                        0.04, self.mute_rates["genome"], [0.001, 1.0])
        self.mute_rates["genome"] = self.mutated_by_const(self.mute_rates["genome"],
                                                          0.04, self.mute_rates["mute"], [0.001, 1.0])

        # other mute_rates [0.0, inf)
        rel_lists = [self.mute_rates["genome_rel"],
                     self.mute_rates["const_rel"],
                     self.mute_rates["leaf_rel"]]

        for rel_list in rel_lists:
            for k in rel_list:
                rel_list[k] = self.mutated_num(rel_list[k], self.mute_rates["mute"], 0.001, None)

    def __len__(self):
        return len(self.genes)

    def mutated_by_factor(self, val, factor, mute_prob, bounds):
        if random.random() > mute_prob:
            return val

        rfactor = 1.0 + (random.random() * (factor - 1.0))
        rfactor = random.choice([rfactor, 1.0/rfactor])

        return max(bounds[0], min(bounds[1], val*rfactor))

    def mutated_by_const(self, val, const, mute_prob, bounds):
        if random.random() > mute_prob:
            return val

        rconst = random.random() * const
        rconst = random.choice([rconst, -rconst])

        return max(bounds[0], min(bounds[1], val + rconst))

    def mutated_num(self, num, probability, low_clamp, high_clamp):
        if random.random() > probability:
            return num
        
        mute = weighted_choice(self.mute_rates["const_rel"])
        muted = num
        if mute == ConstMutes.Increment:
            muted += random.random() * self.incr_range
        elif mute == ConstMutes.Decrement:
            muted -= random.random() * self.incr_range
        elif mute == ConstMutes.Incremult: # Assumes mult_range >= 1
            muted *= (random.random() * (self.mult_range-1)) + 1
        elif mute == ConstMutes.Decremult:
            muted /= (random.random() * (self.mult_range-1)) + 1

        if low_clamp is not None:
            muted = max(low_clamp, muted)
        if high_clamp is not None:
            muted = min(high_clamp, muted)

        return muted

        
