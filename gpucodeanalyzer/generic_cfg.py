#!/usr/bin/env python3

class Instruction:
    label = None

    def targets(self):
        if self.is_control():
            raise NotImplementedError

    def is_control(self):
        return isinstance(self, ControlInsn)

    def reads(self):
        raise NotImplementedError

    def writes(self):
        raise NotImplementedError


class ControlInsn(Instruction):
    def target(self):
        """Returns pc of target"""
        raise NotImplementedError

    def is_conditional(self):
        raise NotImplementedError


class Register:
    def __init__(self, n):
        self.n = n

    def __str__(self):
        return f"Register({self.n})"

    __repr__ = __str__

class Memory:
    pass


class BasicBlock:
    def __init__(self, name, code):
        self.name = name
        self.code = code
        self.successors = {}

    def add_successor(self, label, bb):
        # TODO: prevent duplicate adding?
        assert label not in self.successors, f"Duplicate successor label {label}"
        self.successors[label] = bb

    def __str__(self):
        return f"{self.name}: {self.successors}\n" + "\n".join([f"  {c}" for c in self.code])

    def __repr__(self):
        return f"BasicBlock({self.name}, ...)"

class CFG:
    def __init__(self, codefile):
        self.codefile = codefile
        self.blocks = []
        self.labels_to_blocks = {'_start': BasicBlock('start', []),
                                 '_exit': BasicBlock('exit', [])}

    def build(self):
        def add_bb(bbcode, ndx, last_bb):
            bb = BasicBlock(f"BB{ndx}", bbcode)
            self.blocks.append(bb)
            self.labels_to_blocks[bb.code[0].label] = bb

            if last_bb and len(last_bb.code):
                if last_bb.code[-1].is_control():
                    if last_bb.code[-1].is_conditional():
                        last_bb.add_successor('false', bb)
                else:
                    last_bb.add_successor('next', bb)

            return [], ndx + 1, bb

        starts = set()
        ends = set()
        next_is_start = False

        for i in self.codefile.code:
            if next_is_start:
                starts.add(i)
                next_is_start = False

            if i.is_control():
                ends.add(i.label)
                starts.add(i.target())
                next_is_start = True

        bbndx = 0
        last_bb = self.labels_to_blocks['_start']
        current = []
        for i in self.codefile.code:
            if i.label in starts:
                if len(current):
                    current, bbndx, last_bb = add_bb(current, bbndx, last_bb)
            elif i.label in ends:
                current.append(i)
                current, bbndx, last_bb = add_bb(current, bbndx, last_bb)
                continue

            current.append(i)

        if len(current):
            current, bbndx, last_bb = add_bb(current, bbndx, last_bb)

        # fix up branch targets to bb; could be avoided
        for bb in self.blocks:
            #print(bb)
            last_insn = bb.code[-1]
            if last_insn.is_control():
                target = last_insn.target()
                if last_insn.is_conditional():
                    bb.add_successor('true',
                                     self.labels_to_blocks[target])
                else:
                    bb.add_successor('next',
                                     self.labels_to_blocks[target])

    def dump(self):
        for b in self.blocks:
            print(b)

    def dump_dot(self, output, code=True):
        print("digraph {", file=output)
        for b in self.blocks:
            bbcode = '"' + b.code[0].label + "\\n" + "\\n".join([str(s.insn) for s in b.code]) + '"'
            print(b.name + f" [label={bbcode},shape=rect];", file=output)
            print("\n".join(f"{b.name} -> {succ.name} [label=\"{lbl if lbl != 'next' else ''}\"];" for lbl, succ in b.successors.items()), file=output)
        print("}", file=output)
