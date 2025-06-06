#!/usr/bin/env python3

import re

SASS_INSN_RE = re.compile(r"^\s*/\*([0-9a-f]+)\*/\s+(.+) ;$")
SASS_REG_RE = re.compile(r"(((UR|R|!?P|B)\d+)(.reuse)?)|(PT|RZ|SRZ|SR_CTAID\.?)")

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

class SASSInstruction(Instruction):
    WRITE_COUNT = {}
    def __init__(self, pc, pred, opcode, args, insn):
        self.label = pc
        self.predicate = pred
        self.opcode = opcode
        self.args = args
        self.insn = insn

        out = []
        for a in self.args:
            m = SASS_REG_RE.match(a)
            if m is not None:
                if a[0] == "!":
                    a = a[1:]
                if a.endswith(".reuse"):
                    a = a[:-len(".reuse")]
                out.append(Register(a))
            else:
                out.append(a)

        self.args = out

    def __str__(self):
        return f"{self.label}: {self.predicate if self.predicate else ''} {self.opcode} {self.args} {self.reads()} {self.writes()}"

    __repr__ = __str__

    def reads(self):
        write_args = SASSInstruction.WRITE_COUNT.get(self.opcode, 1)
        return list(x for x in self.args[write_args:] if isinstance(x, Register))

    def writes(self):
        write_args = SASSInstruction.WRITE_COUNT.get(self.opcode, 1)
        return list(x for x in self.args[:write_args] if isinstance(x, Register))

    @staticmethod
    def parse(insn):
        if insn[0] == "@":
            predicate, insn = insn.split(" ", 1)
            predicate = predicate[1:]
        else:
            predicate = None

        opcode_args = insn.split(" ", 1)
        if len(opcode_args) == 1:
            opcode = opcode_args[0]
            args = []
        else:
            opcode = opcode_args[0]
            args = opcode_args[1].split(", ")

        return (predicate, opcode, args)

class SASSControlInsn(SASSInstruction, ControlInsn):
    def target(self):
        if self.opcode == "EXIT":
            return "_exit"
        else:
            if self.args[0].startswith('0x'):
                tgt = self.args[0][2:]
                if len(tgt) < 4:
                    tgt = "0"*(4 - len(tgt)) + tgt
                return tgt
            else:
                return self.args[0]

    def is_conditional(self):
        return self.predicate is not None

class SASSFile:
    SASS_CONTROL_INSN = re.compile("EXIT|BRA")

    def __init__(self, f):
        self.f = f
        self.code = []
        self._parse(f)

    def _parse(self, sassfile):
        with open(sassfile, "r") as f:
            self.code = list(filter(None, (self._mkinsn(l) for l in f)))

    def _mkinsn(self, sassinsn):
        m = SASS_INSN_RE.match(sassinsn)
        if m:
            pc = m.group(1)
            pred, o, a = SASSInstruction.parse(m.group(2))

            if SASSFile.SASS_CONTROL_INSN.match(o):
                i = SASSControlInsn(pc, pred, o, a, m.group(2))
            else:
                i = SASSInstruction(pc, pred, o, a, m.group(2))

            return i

        return None

    def dump(self):
        for i in self.code:
            print(i)

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

    def dump_dot(self):
        for b in self.blocks:
            print(b.name + ";")
            print("\n".join(f"{b.name} -> {succ.name} [label='{lbl if lbl != 'next' else ''}'];" for lbl, succ in b.successors.items()))


class Skeletonizer:
    def __init__(self, cfg):
        self.cfg = cfg

    def build_skeleton(self):
        important = set()
        to_process = []

        for b in self.cfg.blocks:
            last_insn = b.code[-1]
            if last_insn.is_control():
                if last_insn.label not in important:
                    important.add(last_insn.label)
                    to_process.append(last_insn)


        for i in to_process:
            reads = set(i.reads())
            if i.predicate:
                reads.add(i.predicate[1:] if i.predicate[0] == "!" else i.predicate)
            print(reads)

        for b in self.cfg.blocks:
            for i in b.code:
                if i.label in important:
                    print(i)


EXT= {'.sass': SASSFile}
if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Construct a CFG generically")
    p.add_argument("code")

    args = p.parse_args()

    if args.code.endswith(".sass"):
        code = EXT[".sass"](args.code)
    else:
        print("Unrecognized extension")

    #code.dump()
    cfg = CFG(code)
    cfg.build()
    #cfg.dump()
    sk = Skeletonizer(cfg)
    sk.build_skeleton()
    #cfg.dump_dot()
