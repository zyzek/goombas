"""Function trees representing arithmetic expressions."""

import random
from enum import IntEnum
import goomba

class Op(IntEnum):
    """An enumeration of possible function tree operators."""
    Add = 0
    Sub = 1
    Mul = 2
    Div = 3
    Mod = 4
    Pow = 5
    Equ = 6
    Les = 7
    Gre = 8

OP_STRINGS = {Op.Add: "+",
              Op.Sub: "-",
              Op.Mul: "*",
              Op.Div: "/",
              Op.Mod: "%",
              Op.Pow: "^",
              Op.Equ: "=",
              Op.Les: "<",
              Op.Gre: ">"}

STRING_OPS = {v: k for k, v in OP_STRINGS.items()}

class RefType(IntEnum):
    """Enumeration of possible reference types for leaf nodes.

    Pure_Offset_Call: A call to some function in the enclosing genome without gene side-effects.
    Impure_Offset_Call: A call to such a function, but performing its gene's operation.
    Poll_Sensor: a reference to a function that returns the current state of a sensor.
    Constant: simply returns a constant value."""

    Pure_Offset_Call = 0
    Impure_Offset_Call = 1
    Poll_Sensor = 2
    Constant = 3

REF_DELIMS = {RefType.Pure_Offset_Call: '[',
              RefType.Impure_Offset_Call: '{',
              RefType.Poll_Sensor: '$',
              RefType.Constant: ''}


class FTreeNode(object):
    """An internal node of a function tree; a binary operator with two children."""

    def __init__(self, op, l, r):
        self.operator = op
        self.left = l
        self.right = r

        if self.operator == Op.Add:
            self._evaluate_ = lambda l, r: l + r
        elif self.operator == Op.Sub:
            self._evaluate_ = lambda l, r: l - r
        elif self.operator == Op.Mul:
            self._evaluate_ = lambda l, r: l * r
        elif self.operator == Op.Div:
            self._evaluate_ = lambda l, r: l if (r == 0) else (l / r)
        elif self.operator == Op.Mod:
            self._evaluate_ = lambda l, r: l if (r == 0) else (l % r)
        elif self.operator == Op.Pow:
            self._evaluate_ = lambda l, r: (l ** r).real
        elif self.operator == Op.Equ:
            self._evaluate_ = lambda l, r: l == r
        elif self.operator == Op.Les:
            self._evaluate_ = lambda l, r: l < r
        elif self.operator == Op.Gre:
            self._evaluate_ = lambda l, r: l > r
        else:
            self._evaluate_ = lambda l, r: 0

    @classmethod
    def random(cls, max_depth, gen_len, const_bounds):
        if max_depth <= 1:
            return FTreeLeaf.random(gen_len, const_bounds)

        operator = random.choice(list(Op))
        left = cls.random(random.randrange(max_depth-1), gen_len, const_bounds)
        right = cls.random(random.randrange(max_depth-1), gen_len, const_bounds)

        return cls(operator, left, right)

    def is_leaf(self):
        return False

    def __call__(self):
        lres = self.left()
        rres = self.right()
        return self._evaluate_(lres, rres)

    def __str__(self):
        return OP_STRINGS[self.operator] + " " +  str(self.left) + " " + str(self.right)

    def as_list(self):
        return self.left.as_list() + [self] + self.right.as_list()

    def copy(self):
        return FTreeNode(self.operator, self.left.copy(), self.right.copy())

class FTreeLeaf(object):
    """Function tree leaf node containing a callable object returning an arbitrary value."""

    def __init__(self, ref, ref_type, val):
        self.ref = ref
        self.ref_type = ref_type
        self.val = val

    @classmethod
    def init_const(cls, val):
        return cls(None, RefType.Constant, val)

    @classmethod
    def random(cls, gen_len, const_bounds):
        ref_type = random.choice(list(RefType))

        if ref_type == RefType.Pure_Offset_Call or ref_type == RefType.Impure_Offset_Call:
            val = random.randrange(gen_len) * random.choice([-1, 1])
        elif ref_type == RefType.Poll_Sensor:
            val = random.randrange(len(goomba.Sensor))
        else:
            val = (random.random() * (const_bounds[1]-const_bounds[0])) + const_bounds[0]
        return cls(None, ref_type, val)


    def is_leaf(self):
        return True

    def __call__(self):
        if self.ref_type == RefType.Constant:
            return self.val
        return self.ref()

    def __str__(self):
        return REF_DELIMS[self.ref_type] + str(self.val)

    def as_list(self):
        return [self]

    def copy(self):
        return FTreeLeaf(self.ref, self.ref_type, self.val)

def parse_func(sequence):
    curr_sym = sequence.pop(0)
    node = None

    if curr_sym in STRING_OPS:
        # binary operator

        left = parse_func(sequence)
        right = parse_func(sequence)

        node = FTreeNode(STRING_OPS[curr_sym], left, right)

    elif curr_sym[0] == REF_DELIMS[RefType.Pure_Offset_Call]:
        # offset gene no action
        node = FTreeLeaf(None, RefType.Pure_Offset_Call, int(curr_sym[1:]))
    elif curr_sym[0] == REF_DELIMS[RefType.Impure_Offset_Call]:
        # offset gene with action
        node = FTreeLeaf(None, RefType.Impure_Offset_Call, int(curr_sym[1:]))
    elif curr_sym[0] == REF_DELIMS[RefType.Poll_Sensor]:
        # poll sensor
        node = FTreeLeaf(None, RefType.Poll_Sensor, int(curr_sym[1:]))
    else:
        # otherwise, assume a value
        node = FTreeLeaf.init_const(float(curr_sym))

    return node



