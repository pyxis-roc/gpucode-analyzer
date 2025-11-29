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

    def is_constant(self):
        return False

    __repr__ = __str__

class Memory:
    pass


class BasicBlock:
    def __init__(self, name, code):
        self.name = name
        self.code = code
        self.successors = {}
        self.predecessors = {}

    def add_successor(self, label, bb):
        # TODO: prevent duplicate adding?
        assert label not in self.successors, f"Duplicate successor label {label}"
        self.successors[label] = bb

    def add_predecessor(self, bb):
        self.predecessors[bb.name] = bb

    def _mark_as_predecessor(self):
        # must be called once all successors have been added

        for s in self.successors:
            self.successors[s].add_predecessor(self)

    def __str__(self):
        return f"{self.name}: {self.successors}\n" + "\n".join([f"  {c}" for c in self.code])

    def __repr__(self):
        return f"BasicBlock({self.name}, ...)"

    def copy(self):
        o = BasicBlock(self.name, self.code)
        o.successors = dict(self.successors.items())
        o.predecessors = dict(self.predecessors.items())

        return o

    def target(self):
        if hasattr(self, '_target'):
            return self._target
        elif len(self.code) > 0:
            return self.code[0].label
        else:
            raise ValueError

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

        # populate predecessors
        for bb in self.blocks:
            bb._mark_as_predecessor()

    def dump(self):
        for b in self.blocks:
            print(b)

    def dump_dot(self, output, code=True, xinsn=lambda i: i.insn):
        print("digraph {", file=output)
        for b in self.blocks:
            bbcode = '"' + b.target() + "\\n" + "\\n".join([str(xinsn(s)) for s in b.code]) + '"'
            print(b.name + f" [label={bbcode},shape=rect];", file=output)
            print("\n".join(f"{b.name} -> {succ.name} [label=\"{lbl if lbl != 'next' else ''}\"];" for lbl, succ in b.successors.items()), file=output)
        print("}", file=output)

    def copy(self):
        x = CFG(self.codefile)
        x.blocks = list([b.copy() for b in self.blocks])

        l2b = {}
        l2b['_start'] = self.labels_to_blocks['_start'].copy()
        l2b['_exit'] = self.labels_to_blocks['_exit'].copy()
        l2b.update(dict((b.code[0].label, b) for b in x.blocks))

        # note, doesn't deep copy instructions
        for l in self.labels_to_blocks:
            x.labels_to_blocks[l] = l2b[l]

        return x

    def convert(self, converter, func_name): # todo: make func_name a part of cfg
        converter.init_cfg(self, func_name)
        block_order = converter.output_block_order()

        for b in block_order:
            converter.convert_block(self.labels_to_blocks[b])

        converter.finish_cfg()

    def all_instructions(self):
        for b in self.blocks:
            for i in b.code:
                yield i
