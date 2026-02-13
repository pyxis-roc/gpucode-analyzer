import re
from ...generic_cfg import Instruction, ControlInsn, Register, Memory, Operand

# assemblies extracted from nvuc files are "bare" with no function name and have one function.
# assemblies dumped from cuobjdump usually have function name information and are multiple functions.

SASS_INSN_RE = re.compile(r"^\s*/\*([0-9a-f]+)\*/\s+(.+) ;(\s*/\* 0x([0-9a-f]+) \*/)?$")
SASS_REG_RE = re.compile(r"-?(((UR|R|!?P|B|!?UP)\d+)(\.reuse|\.B1|\.H0_H0)?)|(UPT|PT|-?RZ|URZ|SRZ|SR_CTAID\.?|SR_TID\.?)")
SASS_ADDR_RE = re.compile(r"\[(?P<reg1>R[0-9Z]+)(\.(?P<suff>U32|X16))?(\+(?P<reg2>UR[0-9Z]+)|(?P<imm>0x.+))?\]")

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

    def is_uniform(self):
        return self.n[0] == "U"

    def is_predicate(self):
        return self.n[0] == "P" or self.n.startswith("UP")

    def is_barrier(self):
        return self.n[0] == "B"

    def is_regular(self):
        return self.n[0] == "R" or self.n.startswith("UR")

    def is_sr(self):
        return self.n.startswith('SR')

    def operand(self, reuse = True):
        n = self.n

        if reuse and self.is_reuse:
            n = n + ".reuse"

        if self.is_inverted:
            return "!" + n

        if self.is_negated:
            return "-" + n

        return n

    def adjacent(self, adj = 1):
        regno = re.compile(r'(?P<prefix>[^0-9]+)(?P<num>\d+)$')
        m = regno.search(self.n)
        if self.n == "RZ" or self.n == "URZ":
            return [self]*adj
        assert m is not None, self.n
        pfx = m.group('prefix')
        r = int(m.group('num'))

        return [SASSRegister(f"{pfx}{n}") for n in range(r+1, r+adj+1)]

class SASSAddress(Memory):
    def __init__(self, addr, reg1, suff, reg2, imm):
        self.addr = addr
        self.reg1 = SASSRegister(reg1)
        self.suff = suff
        self.reg2 = SASSRegister(reg2) if reg2 else None
        self.imm = imm

    def __str__(self):
        return self.addr

    def registers(self):
        out = [self.reg1]
        if self.reg2:
            out.append(self.reg2)

        return out

class SASSOperand(Operand):
    pass

class SASSInstruction(Instruction):
    WRITE_COUNT = {'BSYNC': 0,
                   ('IADD3', 5): 2,
                   ('LOP3.LUT', 7): 2}

    MULTI_WRITER = {'LDG.E.128.STRONG.GPU': {0: 4},
                    'LDG.E.128.CONSTANT': {0: 4},
                    'ULDC.64': {0: 2},
                    'HMMA.16816.F32': {0: 4},
                    'IMAD.WIDE.U32': {0: 2},
                    'IMAD.WIDE': {0: 2},
                    'LDSM.16.MT88.4': {0: 4},
                    'LDS.128': {0: 4},
                    'LDG.E.128': {0: 4},
                    }

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

                if a.endswith(".B1"):
                    a = a[:-len(".B1")]
                    # unknown

                if a.endswith(".H0_H0"):
                    a = a[:-len(".H0_H0")]
                    # TODO

                r = SASSRegister(a, is_inverted = is_inverted,
                                 is_negated = is_negated,
                                 is_reuse = is_reuse)

                out.append(r)
            else:
                m = SASS_ADDR_RE.match(a)
                if m:
                    addr = SASSAddress(a, reg1 = m.group('reg1'),
                                       suff = m.group('suff'),
                                       reg2 = m.group('reg2'),
                                       imm = m.group('imm'))
                    out.append(addr)
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

    def operands(self):
        write_args = self.write_count() # explicit
        writes = self.args[:write_args]

        mw = self.MULTI_WRITER[self.opcode] if self.opcode in self.MULTI_WRITER else {}

        for k, a in enumerate(writes):
            yield SASSOperand(a, write = True)
            if k in mw:
                for r in a.adjacent(mw[k] - 1):
                    yield SASSOperand(r, write = True, implicit = True)

        reads = self.args[write_args:]
        for a in reads:
            yield SASSOperand(a, read = True)

    def _decode_predset_imm(self, regset):
        rs = int(regset, 16)
        assert rs < 256, rs

        out = []
        for i in range(8):
            if (rs & 1):
                out.append(SASSRegister(f"P{i}"))

            rs >>= 1
            if rs == 0: break

        return out

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

        if self.opcode == "P2R":
            rds.extend(self._decode_predset_imm(self.args[-1]))

        for x in self.args[write_args:]:
            if isinstance(x, SASSAddress):
                rds.extend(x.registers())

        return rds

    def writes(self):
        def extend(r, n):
            if r.n[0] == "R":
                pfx = "R"
            elif r.n[0] == "U":
                pfx = "UR"

            rno = int(r.n[len(pfx):])
            return [SASSRegister(f"{pfx}{d}") for d in range(rno, rno+n)]

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

        if len(self.code) == 0:
            print(f"WARNING:sass: No instructions matched regexp in {sassfile}")

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
