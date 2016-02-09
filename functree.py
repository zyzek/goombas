from enum import IntEnum

class Op(IntEnum):
    Add = 0
    Sub = 1
    Mul = 2
    Div = 3
    Mod = 4
    Pow = 5
    Eq = 6
    LT = 7
    GT = 8

opstrings = {Op.Add: "+",
             Op.Sub: "-",
             Op.Mul: "*",
             Op.Div: "/",
             Op.Mod: "%",
             Op.Pow: "^",
             Op.Eq: "=",
             Op.LT: "<",
             Op.GT: ">"}

stringops = {v: k for k, v in opstrings.items()}

class FTreeNode(object):
    is_leaf = False

    def __init__(self, op, l, r):
        self.op = op
        self.left = l
        self.right = r

        if self.op == Op.Add:
            self._evaluate_ = lambda l, r: l + r
        elif self.op == Op.Sub:
            self._evaluate_ = lambda l, r: l - r
        elif self.op == Op.Mul:
            self._evaluate_ = lambda l, r: l * r
        elif self.op == Op.Div:
            self._evaluate_ = lambda l, r: l if (r == 0) else (l / r)
        elif self.op == Op.Mod:
            self._evaluate_ = lambda l, r: l if (r == 0) else (l % r)
        elif self.op == Op.Pow:
            self._evaluate_ = lambda l, r: l ** r
        elif self.op == Op.Eq:
            self._evaluate_ = lambda l, r: l == r
        elif self.op == Op.LT:
            self._evaluate_ = lambda l, r: l < r
        elif self.op == Op.GT:
            self._evaluate_ = lambda l, r: l > r
        else:
            self._evaluate_ = lambda l, r: 0


    def __call__(self):
        lres = self.left()
        rres = self.right()
        return self._evaluate_(lres, rres)

    def __str__(self):
        return opstrings[self.op] + " " +  str(self.left) + " " + str(self.right)

class FTreeConst(object):
    is_leaf = True

    def __init__(self, i):
        self.val = i

    def __call__(self):
        return self.val

    def __str__(self):
        return str(self.val)

class RefType(IntEnum):
    Pure_Offset_Call = 0
    Impure_Offset_Call  = 1
    Poll_Sensor = 2

class FTreeRef(object):
    is_leaf = True

    def __init__(self, r, t, name):
        self.ref = r
        self.reftype = t
        self.name = name

    def __call__(self):
        return self.ref()

    def __str__(self):
        return self.name

def all_ref_nodes(tree):
    if tree.is_leaf:
        if type(tree).__name__ == "FTreeRef":
            return [tree]
        return []
    
    return all_ref_nodes(tree.left) + all_ref_nodes(tree.right)

"""
class incremental(object):
    def __init__(self):
        self.i = 0

    def __call__(self):
        ret = self.i
        self.i += 1
        return ret

if __name__ == '__main__':
    incr = FTreeRef(incremental(), "incr")
    one = FTreeConst(1)
    two = FTreeConst(2)
    ten = FTreeConst(10)

    two_plus_ten = FTreeNode(Op.Add, two, ten)
    minus_one = FTreeNode(Op.Sub, two_plus_ten, one)
    reciprocal_incr = FTreeNode(Op.Div, one, incr)
    root = FTreeNode(Op.Pow, minus_one, reciprocal_incr)

    print(root())
    print(root())
    print(root())
    print(root())
    print(root())

    print(root)
"""
