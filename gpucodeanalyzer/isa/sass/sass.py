import re
from ...generic_cfg import Instruction, ControlInsn, Register, Memory

SASS_INSN_RE = re.compile(r"^\s*/\*([0-9a-f]+)\*/\s+(.+) ;$")
SASS_REG_RE = re.compile(r"-?(((UR|R|!?P|B|!?UP)\d+)(.reuse)?)|(UPT|PT|RZ|URZ|SRZ|SR_CTAID\.?|SR_TID\.?)")

CX_RE = re.compile(r"-?cx\[(?P<regbase>.+)\]\[(?P<offset>.+)\]")

CONSTANT_REGS = set(['RZ', 'SRZ', 'URZ', 'PT', 'UPT', 'SR_TID.X', 'SR_CTAID.X',
                     'SR_TID.Y', 'SR_TID.Z', 'SR_CTAID.Y', 'SR_CTAID.Z'])


class SASSRegister(Register):
    def __init__(self, n, is_inverted = False, is_negated = False, is_reuse = False):
        super().__init__(n)

        # todo: reuse, !, .cc
        self.is_inverted = is_inverted
        self.is_negated = is_negated
        self.is_reuse = is_reuse

    def is_constant(self):
        return self.n in CONSTANT_REGS

    def operand(self, reuse = True):
        n = self.n

        if reuse and self.is_reuse:
            n = n + ".reuse"

        if self.is_inverted:
            return "!" + n

        if self.is_negated:
            return "-" + n

        return n

class SASSInstruction(Instruction):
    WRITE_COUNT = {'BSYNC': 0,
                   ('IADD3', 5): 2}

    MULTI_WRITER = {'LDG.E.128.STRONG.GPU': {0: 4},
                    'LDG.E.128.CONSTANT': {0: 4}}

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
                r = None
                is_inverted = False
                is_negated = False
                is_reuse = False

                if a[0] == "!":
                    a = a[1:]
                    is_inverted = True

                if a[0] == "-":
                    a = a[1:]
                    is_negated = True

                if a.endswith(".reuse"):
                    a = a[:-len(".reuse")]
                    is_reuse = True

                r = SASSRegister(a, is_inverted = is_inverted,
                                 is_negated = is_negated,
                                 is_reuse = is_reuse)

                out.append(r)
            else:
                out.append(a)

        self.args = out

    def __str__(self):
        return f"{self.label}: {self.predicate if self.predicate else ''} {self.opcode} {self.args} {self.reads()} {self.writes()}"

    __repr__ = __str__

    def write_count(self):
        if self.opcode in SASSInstruction.WRITE_COUNT:
            write_args = SASSInstruction.WRITE_COUNT[self.opcode]
        elif (self.opcode, len(self.args)) in SASSInstruction.WRITE_COUNT:
            write_args = SASSInstruction.WRITE_COUNT[(self.opcode, len(self.args))]
        else:
            write_args = 1

        return write_args

    def reads(self):
        write_args = self.write_count()
        rds = list(x for x in self.args[write_args:] if isinstance(x, Register))
        if self.predicate:
            n = self.predicate
            if n[0] == "!": n = n[1:]

            rds.append(SASSRegister(n,
                                    is_inverted = self.predicate[0] == "!"))

        # TODO: multi-readers

        # hack, need to fix this.
        for x in self.args[write_args:]:
            if isinstance(x, str):
                cxm = CX_RE.match(x)
                if cxm:
                    rds.append(SASSRegister(cxm.group('regbase')))

        return rds

    def writes(self):
        def extend(r, n):
            assert r.n[0] == "R"
            rno = int(r.n[1:])
            return [SASSRegister(f"R{d}") for d in range(rno, rno+n)]

        write_args = self.write_count()
        writes = list(x for x in self.args[:write_args] if isinstance(x, Register) and not x.is_constant())

        if self.opcode in SASSInstruction.MULTI_WRITER:
            for arg, ext in SASSInstruction.MULTI_WRITER[self.opcode].items():
                writes[arg] = extend(writes[arg], ext)

            o = []
            for x in writes:
                if isinstance(x, list):
                    o.extend(x)
                else:
                    o.add(x)

            return o
        else:
            return writes

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
    SASS_CONTROL_INSN = re.compile("EXIT|BRA|CALL.REL.NOINC")

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
