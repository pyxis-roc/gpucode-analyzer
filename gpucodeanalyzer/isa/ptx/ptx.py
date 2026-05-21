import ptxparser as pp
from ptxparser import ptxast as pa
from ptxparser import ast2ptx as a2p
from io import StringIO
from ...generic_cfg import Instruction, ControlInsn, Register, Memory, Operand
import re

CONSTANT_REGS = {'%tid', '%ntid'}

def ptx2code(p):
    out = StringIO()
    vis = a2p.PTXAST2Code(out)
    vis.visit(p)
    v = out.getvalue()
    out.close()
    return v

class PTXLabelOrName:
    def __init__(self, n):
        self.n = n

class PTXRegister(Register):
    def __init__(self, n):
        self.n = n

    def is_constant(self):
        return self.n in CONSTANT_REGS

class PTXAddress(Memory):
    def __init__(self, value, offset):
        self.value = value
        self.offset = offset

    def registers(self):
        out = []
        if isinstance(self.value, PTXRegister):
            out.append(self.value)

        assert not isinstance(self.offset, PTXRegister), self.value

        return out

class PTXInstruction(Instruction):
    NON_WRITING = {"bra"}

    def __init__(self, pc, ast, opcode, insn, labels):
        self.label = pc
        self.ast = ast
        self.insn = insn
        self.opcode = opcode

        self.predicate = self.ast.predicate
        self.args = self._parse_args(self.ast.args, labels)

    def _parse_args(self, args, labels):
        out = []
        for a in args:
            if isinstance(a, pa.Id):
                if a.name not in labels:
                    out.append(PTXRegister(a.name))
                else:
                    out.append(PTXLabelOrName(a.name))
            elif isinstance(a, pa.AddressOpr):
                assert a.offset is None, a.offset
                out.append(PTXAddress(PTXRegister(a.value.name),
                                      a.offset))
            elif isinstance(a, pa.VectorComp):
                out.append(PTXRegister(a.var.name))
            elif isinstance(a, pa.ConstExpr):
                pass
            else:
                raise NotImplementedError(a)

        return out

    def __str__(self):
        return f"{self.label}: {self.insn}"

    __repr__ = __str__

    def code(self):
        return self.insn

    def predicated(self):
        return self.predicate is not None

    def write_count(self):
        if self.opcode in self.NON_WRITING:
            return 0
        else:
            return 1

    def operands(self):
        raise NotImplementedError

    def reads(self):
        write_regs = self.write_count()
        rds = list(x for x in self.args[write_regs:] if isinstance(x, Register))
        if self.predicate:
            rds.append(PTXRegister(self.predicate.reg.name))

        #TODO: address
        return rds

    def writes(self):
        write_args = self.write_count()
        writes = list(x for x in self.args[:write_args] if isinstance(x, Register) and not x.is_constant() and x.n != "_")

        return writes

# for declarations, etc.
class PTXNullInstruction(Instruction):
    def __init__(self, pc, ast, insn):
        self.label = pc
        self.ast = ast
        self.insn = insn

        self.args = []

    def __str__(self):
        return f"{self.label}: {self.insn}"

    __repr__ = __str__

    def code(self):
        return self.insn

    def predicated(self):
        return False

    def write_count(self):
        return 0

    def operands(self):
        return []

    def reads(self):
        return []

    def writes(self):
        return []

class PTXControlInsn(PTXInstruction, ControlInsn):
    def targets(self):
        if self.indirect_targets is None:
            return [self.target()]
        else:
            return self.indirect_targets

    def target(self):
        if self.opcode == "ret":
            return "_exit"
        elif self.opcode == "bra":
            return self.ast.args[0].name
        else:
            raise NotImplementedError(self.opcode)

    def is_conditional(self):
        return self.predicated()

    def is_indirect(self):
        return False

class PTXFile:
    PTX_CONTROL_INSN = re.compile(r"ret|bra")

    def __init__(self, f, metadata=None):
        self.f = f
        self.code = []
        self.codes = {}
        self.metadata = metadata
        self._parse(f)

    def _parse(self, ptxfile):
        with open(ptxfile, 'r') as f:
            src = f.read()
            self.ptxast = pp.ptx_parse(src, parse_unsupported = True)

            for s in self.ptxast.body:
                if isinstance(s, pa.Linker):
                    if isinstance(s.identifier, (pa.Func,
                                                 pa.Entry)):
                        name = s.identifier.name
                        code = self.make_insns(s.identifier)
                        self.codes[name] = code

            if len(self.codes) == 1:
                self.code  = self.codes[list(self.codes.keys())[0]]

            print(self.ptxast)

    def make_insns(self, fn):
        out = []
        label = None

        # TODO: labels inside blocks
        labels = set([x.name for x in fn.body if isinstance(x, pa.Label)])

        for pc, i in enumerate(fn.body):
            if isinstance(i, pa.Statement):

                opcode = a2p._mks(i.opcode)
                insn = ptx2code(i)

                if self.PTX_CONTROL_INSN.match(opcode):
                    out.append(PTXControlInsn(label or str(pc), i, opcode, insn, labels))
                else:
                    out.append(PTXInstruction(label or str(pc), i, opcode, insn, labels))
                label = None
            elif isinstance(i, pa.Label):
                label = i.name
            elif isinstance(i, pa.MultivarDecl):
                insn = ptx2code(i)
                out.append(PTXNullInstruction(str(pc), i, insn))
            elif isinstance(i, pa.Block):
                raise NotImplementedError

        return out

    def resolve_indirects(self, cfg, indirects):
        pass

    def dump(self):
        pass
