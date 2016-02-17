"""
A Genome is composed of two parts; the metagenome and the coding region.

Metagenome: This is composed of floating point numbers in the following order.
    4 x <r><g><b>       colors: four colour triplets that determine the hue of a goomba's vertices.
                        Internal colours are interpolated from the corners.

    <fuzziness>         determines the fuzziness of the comparison operators. If this value is 2.0,
                        fuzzy equality of two numbers is 1.0 if they are equal, 0.0 if their
                        difference is greater than 2.0, values linearly interpolated in the
                        intermediate region. Things are similar for inequality operators.

    <low> <high>        const_bound limits: the range of values possible for newly-generated
                        numbers, for example inside constant leaf nodes of arithmetic trees.

    <fun_gen_depth>     the maximum height that a newly-generated random function tree may attain

    <incr> <mult>       max value of increment or multiple factors involved in mutating constants

    <mute>              the mutation rate of the mutation rate genes

    <genome>            mute rate of other genes

    <gene_action>       chance to mutate a gene's action; complement of prob to mutate its function

    <struct_mod>        chance to perform a structure-modifying mutation, or otherwise

    <leaf_type>         chance to mutate a leaf's type versus its value

    genome_rel          composed of individual relative genome mute rates:
                        <insert> <dupe> <delete> <invert> <mutegene>

    const_rel           composed of individual relative constant mute rates:
                        <incr> <decr> <mult> <div>

    leaf_rel            relative prevalence of leaf types:
                        <pure_call> <impure_call> <poll_sensor> <constant>

    enum_rel            relative prevalence of enum mutations:
                        <increment> <decrement> <random>

    struct_rel          relative rates for gene mutations:
                        <replace_subtree> <operator_above> <swap_operands>


    These latter compounds ending in "_rel" determine the approximate proportions with which
    the corresponding actions will be taken, or objects will occur.

Coding Region: This is a sequence of individual genes.
    Each contains first a number, the action code, which determines what the gene does,
    followed by an arithmetic expression in polish notation, determining the value of the function.

    When a gene is expressed, this expression is unpacked into a binary tree, whose internal nodes
    may include any of the following operators: + - * / % ^ = < >
    Each internal node has two children, each of which may be either another internal node,
    or else a leaf node.
    Leaf nodes contain a value and a reference, and may be any one of four types:

        Constants: when evaluated simply return the value they contain.
                   In the genome, these simply appear as numbers.

        Sensors: their references are functions returning the state of the sensor determined by
                 this leaf's value.
                 A sensor is denoted by $n in the genome, where n is the sensor number.

        Pure Offset Calls: refers to the function inside the gene a number of places down
                           the genome, modulo the genome's length.
                           The number of places down is determined by the leaf's value.
                           Evaluating this leaf calls the referenced function, without performing
                           its gene's action.
                           An offset call increments the stack depth, and so may not be made
                           if the stack is already full.

                           Pure offset calls appear as [n in the genome, n being the value
                           of the offset.

        Impure Offset Call: Exactly as a pure call, but the genetic action is performed,
                            as if the gene was in the gene queue.
                            Such calls still respect maximum stack depth.

                            Impure calls look like {n in the genome.


When a genome is instantiated from a sequence, these function trees are built.
However, if not inside an agent, it's possible to encode infinite recursive loops,
and sensors are obviously not hooked up to anything.
So a genome is non-functional unless expressed by an agent.
"""

import random
from enum import IntEnum
from functree import Op, FTreeNode, FTreeLeaf, RefType, parse_func
from util import weighted_choice
import goomba

class GenomeMutes(IntEnum):
    """All possible genome-level mutations.

    When performing a mutation, first a gene index is selected, then the mutation applied.

    Insert:    places a new random gene in the genome immediately before the selected gene.
    Dupe:      duplicates the selected gene.
    Delete:    deletes the selected gene.
    Invert:    swaps the positions of the selected gene and the one following.
    MuteGene:  performs an internal mutation upon the selected gene.
    """

    Insert = 0
    Dupe = 1
    Delete = 2
    Invert = 3
    MuteGene = 4

class ConstMutes(IntEnum):
    """Constant values may be incremented or multiplied by a genetically-determined quantity."""

    Increment = 0
    Decrement = 1
    Incremult = 2
    Decremult = 3

class EnumMutes(IntEnum):
    """Enums, such as sensor or action codes are mutated as discrete values in a finite range."""

    Increment = 0
    Decrement = 1
    Random = 2

class StructMutes(IntEnum):
    """All structure-modifying mutations.

    SubTree:    replace a node with an entirely new random subtree.
    OpAbove:    introduce a new operator in place of the selected node, which becomes one of the
                operands, where the other operand is randomly generated.
    Swap:       swap a pair of operands. If a leaf was selected, swap the operands of its parent.
    """

    SubTree = 0
    OpAbove = 1
    Swap = 2


class Gene(object):
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

    def __str__(self):
        return str(self.action.value) + " " + str(self.function)

    def size(self):
        return self.function.size()

    def mutate(self, genome):
        if random.random() < genome.mute_rates["gene_action"]:
            # Mutate this gene's action
            self.action = mutated_intenum(self.action, goomba.Action,
                                          1.0, genome.mute_rates["enum_rel"])

        elif random.random() < genome.mute_rates["struct_mod"]:
            # Structure-modifying function mutations.

            # Select a random node and mutation
            node = random.choice(self.function.as_list())
            mute = weighted_choice(genome.mute_rates["struct_rel"])

            if mute == StructMutes.SubTree:
                new_node = FTreeNode.random(round(genome.fun_gen_depth),
                                            len(genome),
                                            genome.const_bounds,
                                            genome.mute_rates["leaf_rel"],
                                            node.parent)
                if node.parent is None:
                    self.function = new_node
                elif node.parent.left == node:
                    node.parent.left = new_node
                else:
                    node.parent.right = new_node

            elif mute == StructMutes.OpAbove:
                new_node = FTreeNode(random.choice(list(Op)), None, None, node.parent)
                
                if node.parent is None:
                    self.function = new_node
                elif node.parent.left == node:
                    node.parent.left = new_node
                else:
                    node.parent.right = new_node
                
                new_child = FTreeNode.random(round(genome.fun_gen_depth),
                                             len(genome),
                                             genome.const_bounds,
                                             genome.mute_rates["leaf_rel"],
                                             new_node)

                if random.random() < 0.5:
                    new_node.left = node
                    new_node.right = new_child
                else:
                    new_node.left = new_child
                    new_node.right = node
                    
            elif mute == StructMutes.Swap:
                if isinstance(node, FTreeLeaf):
                    if node.parent is not None:
                        node = node.parent
                    else:
                        return
            # swap operands
                tmp = node.left
                node.left = node.right
                node.right = tmp

        else:
            # Non-strucure-modifying function mutation
            
            # Select a random node
            node = random.choice(self.function.as_list())

            if isinstance(node, FTreeNode):
                # mutate operator
                node.operator = mutated_intenum(node.operator, Op, 
                                                1.0, genome.mute_rates["enum_rel"])
            else:
                if random.random() < genome.mute_rates["leaf_type"]:
                    # mutate the leaf type

                    new_type = node.ref_type
                    # Keep trying to mutate until the value actually changes
                    while new_type == node.ref_type:
                        new_type = mutated_intenum(node.ref_type, RefType,
                                                   1.0, genome.mute_rates["leaf_rel"])
                    if node.ref_type == RefType.Constant:
                        node.val = round(node.val)  # In case mutating from float to int
                    node.ref_type = new_type
                    
                else:
                    # mutate the leaf value
                    if node.ref_type == RefType.Constant:
                        node.val = mutated_num(node.val, 1.0,
                                               genome, [None, None])
                    elif node.ref_type in [RefType.Pure_Offset_Call, RefType.Impure_Offset_Call]:
                        node.val = mutated_int_in_range(node.val, 1.0,
                                                        [-len(genome), len(genome)],
                                                        genome.mute_rates["enum_rel"])
                    elif node.ref_type == RefType.Poll_Sensor:
                        node.val = mutated_int_in_range(node.val, 1.0,
                                                        [0, len(goomba.Sensor) - 1],
                                                        genome.mute_rates["enum_rel"])


    def copy(self):
        return Gene(self.action, self.function.copy())

class Genome(object):

    META_INDICES = {"colors": [0, 12],
                    "fuzziness": [12, 13],
                    "const_bounds": [13, 15],
                    "fun_gen_depth": [15, 16],
                    "incr_range": [16, 17],
                    "mult_range": [17, 18],
                    "mute": [18, 19],
                    "genome": [19, 20],
                    "gene_action": [20, 21],
                    "struct_mod": [21, 22],
                    "leaf_type": [22, 23],
                    "genome_rel": [23, 28],
                    "const_rel": [28, 32],
                    "leaf_rel": [32, 36],
                    "enum_rel": [36, 39],
                    "struct_rel": [39, 42]}


    def __init__(self, meta, sequence):

        # Set up first the metagenome
        meta_genes = [float(g) for g in meta.strip().split()]

        self.colors = [meta_genes[i:i+3] + [1.0] for i in range(*Genome.META_INDICES["colors"], 3)]

        self.fuzziness = Genome.meta_item(meta_genes, "fuzziness")
        self.const_bounds = Genome.meta_item(meta_genes, "const_bounds")
        self.fun_gen_depth = Genome.meta_item(meta_genes, "fun_gen_depth")
        self.incr_range = Genome.meta_item(meta_genes, "incr_range")
        self.mult_range = Genome.meta_item(meta_genes, "mult_range")

        self.mute_rates = {}
        self.mute_rates["mute"] = Genome.meta_item(meta_genes, "mute")
        self.mute_rates["genome"] = Genome.meta_item(meta_genes, "genome")
        self.mute_rates["gene_action"] = Genome.meta_item(meta_genes, "gene_action")
        self.mute_rates["struct_mod"] = Genome.meta_item(meta_genes, "struct_mod")
        self.mute_rates["leaf_type"] = Genome.meta_item(meta_genes, "leaf_type")

        self.mute_rates["genome_rel"] = dict(zip(list(GenomeMutes),
                                                 Genome.meta_item(meta_genes, "genome_rel")))
        self.mute_rates["const_rel"] = dict(zip(list(ConstMutes),
                                                Genome.meta_item(meta_genes, "const_rel")))
        self.mute_rates["leaf_rel"] = dict(zip(list(RefType),
                                               Genome.meta_item(meta_genes, "leaf_rel")))
        self.mute_rates["enum_rel"] = dict(zip(list(EnumMutes),
                                               Genome.meta_item(meta_genes, "enum_rel")))
        self.mute_rates["struct_rel"] = dict(zip(list(StructMutes),
                                                 Genome.meta_item(meta_genes, "struct_rel")))

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

    @classmethod
    def random_coding(cls, meta, length):
        meta_nums = [float(g) for g in meta.strip().split()]

        const_bounds = Genome.meta_item(meta_nums, "const_bounds")
        leaf_rel = dict(zip(list(RefType), Genome.meta_item(meta_nums, "leaf_rel")))
        fun_gen_depth = Genome.meta_item(meta_nums, "fun_gen_depth")

        genes = [Gene.random(fun_gen_depth, length, const_bounds, leaf_rel) \
                 for _ in range(length)]

        g_string = " | ".join(str(gene) for gene in genes)

        return cls(meta, g_string)

    @classmethod
    def meta_item(cls, meta_sequence, name):
        start, stop = Genome.META_INDICES[name]
        item = meta_sequence[start:stop]

        if len(item) == 1:
            return item[0]

        return item

    
    
    def sequences(self):
        metastr = ""
        for col in self.colors:
            metastr += " ".join(str(c) for c in col[:3]) + " "

        metastr += str(self.fuzziness) + " "
        metastr += str(self.const_bounds[0]) + " "
        metastr += str(self.const_bounds[1]) + " "
        metastr += str(self.fun_gen_depth) + " "
        metastr += str(self.incr_range) + " "
        metastr += str(self.mult_range) + " "
        
        for key in ["mute", "genome", "gene_action", "struct_mod", "leaf_type"]:
            metastr += str(self.mute_rates[key]) + " "
        
        for key in ["genome_rel", "const_rel", "leaf_rel", "enum_rel", "struct_rel"]:
            metastr += " ".join(str(v) for v in self.mute_rates[key].values()) + " "

        mainstr = " | ".join(str(gene) for gene in self.genes).strip()

        return [metastr, mainstr]


    def link(self):
        for i in range(len(self.genes)):
            self.link_func(self.genes[i].function, i)

    def link_func(self, func_node, index):
        if isinstance(func_node, FTreeNode):
            self.link_func(func_node.left, index)
            self.link_func(func_node.right, index)
        elif isinstance(func_node, FTreeLeaf):
            ref_index = (round(func_node.val) + index) % len(self.genes)
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
                    self.genes[i].mutate(self)
                    fuzz = i

                if fuzz != -1:
                    self.fuzzify(self.genes[fuzz].function)
                
                # Mutate the colours when a functional mutation occurs, for a visual
                # indication of genetic distance.
                self.mutate_colors()

            i += 1

        # 4. Reset genome consistency
        self.link()

        # 5. Mutate the metagenome
        # fuzz [0.0, inf)
        self.fuzziness = mutated_num(self.fuzziness, 
                                     self.mute_rates["genome"], 
                                     self,
                                     [0.001, None])

        # const bounds (-inf, inf), but small smaller than large
        self.const_bounds[0] = mutated_num(self.const_bounds[0],
                                           self.mute_rates["genome"],
                                           self,
                                           [None, None])
        self.const_bounds[1] = mutated_num(self.const_bounds[1],
                                           self.mute_rates["genome"], 
                                           self,
                                           [None, None])
        if self.const_bounds[0] > self.const_bounds[1]:
            self.const_bounds = self.const_bounds[::-1]

        # fun gen depth [0.0, 5.0]
        self.fun_gen_depth = mutated_by_factor(self.fun_gen_depth,
                                               1.7, self.mute_rates["genome"], [0.001, 5.0])

        # incr_range [0.0, inf)
        self.incr_range = mutated_num(self.incr_range,
                                      self.mute_rates["genome"], 
                                      self, 
                                      [0.001, None])
        # mult_range [1.0, inf)
        self.mult_range = mutated_num(self.mult_range, 
                                      self.mute_rates["genome"],
                                      self,
                                      [1.0, None])

        # Colours used to be mutated here.

        # mute_rates "mute", "genome" [0.0, 1.0]
        self.mute_rates["mute"] = mutated_by_const(self.mute_rates["mute"],
                                                   0.04, self.mute_rates["genome"], [0.001, 1.0])
        self.mute_rates["genome"] = mutated_by_const(self.mute_rates["genome"],
                                                     0.04, self.mute_rates["mute"], [0.001, 1.0])

        # other mute_rates [0.0, inf)
        rel_lists = [self.mute_rates["genome_rel"],
                     self.mute_rates["const_rel"],
                     self.mute_rates["leaf_rel"]]

        for rel_list in rel_lists:
            for k in rel_list:
                rel_list[k] = mutated_num(rel_list[k],
                                          self.mute_rates["mute"],
                                          self,
                                          [0.001, None])

    def __len__(self):
        """Number of genes in the genome."""
        return len(self.genes)

    def size(self):
        """Number of function nodes in the genome."""
        return sum(gene.size() for gene in self.genes)
        


    def mutate_colors(self):
        # colours must reside within [0.0, 1.0]
        # The colour mute rate is high for visual appeal;
        # since no fitness value, would otherwise simply drift
        for col in self.colors:
            for i, _ in enumerate(col[:3]):
                col[i] = mutated_by_factor(col[i], 1.7, 0.7, [0.0, 1.0])

def mutated_by_factor(val, factor, mute_prob, bounds):
    if random.random() > mute_prob:
        return val

    rfactor = 1.0 + (random.random() * (factor - 1.0))
    rfactor = random.choice([rfactor, 1.0/rfactor])

    return max(bounds[0], min(bounds[1], val*rfactor))

def mutated_by_const(val, const, mute_prob, bounds):
    if random.random() > mute_prob:
        return val

    rconst = random.random() * const
    rconst = random.choice([rconst, -rconst])

    return max(bounds[0], min(bounds[1], val + rconst))

def mutated_int_in_range(val, mute_prob, rand_bounds, enum_rel):
    if random.random() > mute_prob:
        return val

    mute = weighted_choice(enum_rel)
    if mute == EnumMutes.Increment:
        return val + 1
    elif mute == EnumMutes.Decrement:
        return val - 1
    else:
        return random.randint(*rand_bounds)


def mutated_num(num, mute_prob, genome, clamps):
    if random.random() > mute_prob:
        return num

    mute = weighted_choice(genome.mute_rates["const_rel"])
    if mute == ConstMutes.Increment:
        num += random.random() * genome.incr_range
    elif mute == ConstMutes.Decrement:
        num -= random.random() * genome.incr_range
    elif mute == ConstMutes.Incremult: # Assumes mult_range >= 1
        num *= (random.random() * (genome.mult_range-1)) + 1
    elif mute == ConstMutes.Decremult:
        num /= (random.random() * (genome.mult_range-1)) + 1

    if clamps[0] is not None:
        num = max(clamps[0], num)
    if clamps[1] is not None:
        num = min(clamps[1], num)

    return num

def mutated_intenum(curr, enum_type, mute_prob, enum_rel):
    if random.random() > mute_prob:
        return curr

    mute = weighted_choice(enum_rel)
    if mute == EnumMutes.Increment:
        return enum_type((curr + 1) % len(enum_type))
    elif mute == EnumMutes.Decrement:
        return enum_type((curr - 1) % len(enum_type))
    else:
        return random.choice(list(enum_type))


def cross_genomes(genome_a, genome_b):
    return Genome(*cross_genome_sequences(genome_a.sequences(), genome_b.sequences()))

def cross_genome_sequences(seqs_a, seqs_b):
    meta_a = seqs_a[0].strip().split()
    meta_b = seqs_b[0].strip().split()
    meta_index = random.randrange(len(meta_a))
    new_meta = meta_a[:meta_index] + meta_b[meta_index:]
    meta = " ".join(meta_a[:6] + meta_b[6:12] + new_meta[12:])

    main_a = seqs_a[1].strip().split("|")
    main_b = seqs_b[1].strip().split("|")
    main_index = random.randrange(min(len(main_a), len(main_b)))
    new_main = main_a[:main_index] + main_b[main_index:]
    new_main[main_index] = cross_gene_sequences(main_a[main_index], main_b[main_index])
    main = " | ".join(new_main)

    return (meta, main)

def cross_gene_sequences(gene_a, gene_b):
    atomised_a = gene_a.strip().split()
    atomised_b = gene_b.strip().split()

    new_action = random.choice([atomised_a.pop(0), atomised_b.pop(0)])

    func_a = parse_func(atomised_a)
    func_b = parse_func(atomised_b)

    node_a = random.choice(func_a.as_list())
    node_b = random.choice(func_b.as_list())

    if node_a.parent is None:
        return new_action + " " + str(func_b)
    elif node_a.parent.left == node_a:
        node_a.parent.left = node_b
    else:
        node_a.parent.right = node_b

    root = node_a.parent

    while root.parent is not None:
        root = root.parent

    return new_action + " " + str(root)




