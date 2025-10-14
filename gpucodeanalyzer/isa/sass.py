import re
from ..generic_cfg import Instruction, ControlInsn, Register, Memory

SASS_INSN_RE = re.compile(r"^\s*/\*([0-9a-f]+)\*/\s+(.+) ;$")
SASS_REG_RE = re.compile(r"(((UR|R|!?P|B)\d+)(.reuse)?)|(PT|RZ|SRZ|SR_CTAID\.?)")

class SASSRegister(Register):
    def __init__(self, n, is_inverted = False):
        super().__init__(n)

        # todo: reuse, !, .cc
        self.is_inverted = is_inverted

    def is_constant(self):
        return self.n == "RZ" or self.n == "PT"

class SASSInstruction(Instruction):
    WRITE_COUNT = {'BSYNC': 0}
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
                if a[0] == "!":
                    a = a[1:]
                    r = SASSRegister(a, is_inverted = True)

                if a.endswith(".reuse"):
                    assert r is None
                    a = a[:-len(".reuse")]
                    r = SASSRegister(a) #TODO: is_reuse
                else:
                    r = SASSRegister(a)

                out.append(r)
            else:
                out.append(a)

        self.args = out

    def __str__(self):
        return f"{self.label}: {self.predicate if self.predicate else ''} {self.opcode} {self.args} {self.reads()} {self.writes()}"

    __repr__ = __str__

    def reads(self):
        write_args = SASSInstruction.WRITE_COUNT.get(self.opcode, 1)
        rds = list(x for x in self.args[write_args:] if isinstance(x, Register))
        if self.predicate:
            n = self.predicate
            if n[0] == "!": n = n[1:]
            rds.append(SASSRegister(n,
                                    is_inverted = self.predicate[0] == "!"))

        return rds

    def writes(self):
        write_args = SASSInstruction.WRITE_COUNT.get(self.opcode, 1)
        return list(x for x in self.args[:write_args] if isinstance(x, Register) and not x.is_constant())

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
