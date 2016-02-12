"""Function trees representing arithmetic expressions."""

from enum import IntEnum

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
    Poll_Sensor: a reference to a function that returns the current state of a sensor."""

    Pure_Offset_Call = 0
    Impure_Offset_Call = 1
    Poll_Sensor = 2

REF_DELIMS = {RefType.Pure_Offset_Call: '[',
              RefType.Impure_Offset_Call: '{',
              RefType.Poll_Sensor: '$'}


class FTreeNode(object):
    """An internal node of a function tree; a binary operator with two children."""
    #pylint: disable=too-few-public-methods

    is_leaf = False

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
            self._evaluate_ = lambda l, r: l ** r
        elif self.operator == Op.Equ:
            self._evaluate_ = lambda l, r: l == r
        elif self.operator == Op.Les:
            self._evaluate_ = lambda l, r: l < r
        elif self.operator == Op.Gre:
            self._evaluate_ = lambda l, r: l > r
        else:
            self._evaluate_ = lambda l, r: 0


    def __call__(self):
        lres = self.left()
        rres = self.right()
        return self._evaluate_(lres, rres)

    def __str__(self):
        return OP_STRINGS[self.operator] + " " +  str(self.left) + " " + str(self.right)

class FTreeConst(object):
    """Leaf node of a function tree containing a constant numeric value."""
    #pylint: disable=too-few-public-methods

    is_leaf = True

    def __init__(self, v):
        self.val = v

    def __call__(self):
        return self.val

    def __str__(self):
        return str(self.val)

class FTreeRef(object):
    """Function tree leaf node containing a callable object returning an arbitrary value."""

    is_leaf = True

    def __init__(self, ref, reftype, val):
        self.ref = ref
        self.reftype = reftype
        self.val = val

    def __call__(self):
        return self.ref()

    def __str__(self):
        return REF_DELIMS[self.reftype] + str(self.val)

def all_ref_nodes(tree):
    """Return a list of all FTreeRef nodes in an arithmetic tree."""
    if tree.is_leaf:
        if type(tree).__name__ == "FTreeRef":
            return [tree]
        return []
    return all_ref_nodes(tree.left) + all_ref_nodes(tree.right)

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
        node = FTreeRef(None, RefType.Pure_Offset_Call, int(curr_sym[1:]))
    elif curr_sym[0] == REF_DELIMS[RefType.Impure_Offset_Call]:
        # offset gene with action
        node = FTreeRef(None, RefType.Impure_Offset_Call, int(curr_sym[1:]))
    elif curr_sym[0] == REF_DELIMS[RefType.Poll_Sensor]:
        # poll sensor
        node = FTreeRef(None, RefType.Poll_Sensor, int(curr_sym[1:]))
    else:
        # otherwise, assume a value
        node = FTreeConst(float(curr_sym))

    return node



