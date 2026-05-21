import ptxparser as pp
from ptxparser import ptxast as pa
from ptxparser import ast2ptx as a2p
from io import StringIO
from ...generic_cfg import Instruction, ControlInsn, Register, Memory, Operand
import re

def ptx2code(p):
    out = StringIO()
    vis = a2p.PTXAST2Code(out)
    vis.visit(p)
    v = out.getvalue()
    out.close()
    return v

class PTXInstruction(Instruction):
    def __init__(self, pc, ast, opcode, insn):
        self.label = pc
        self.ast = ast
        self.insn = insn
        self.opcode = opcode

        self.predicate = self.ast.predicate
        self.args = []

    def __str__(self):
        return f"{self.label}: {self.insn}"

    __repr__ = __str__

    def code(self):
        return ptx2code(self.insn)

    def predicated(self):
        return self.predicate is not None

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
        for pc, i in enumerate(fn.body):
            if isinstance(i, pa.Statement):

                opcode = a2p._mks(i.opcode)
                insn = ptx2code(i)

                if self.PTX_CONTROL_INSN.match(opcode):
                    out.append(PTXControlInsn(label or str(pc), i, opcode, insn))
                else:
                    out.append(PTXInstruction(label or str(pc), i, opcode, insn))
                label = None
            elif isinstance(i, pa.Label):
                label = i.name

        return out

    def resolve_indirects(self, cfg, indirects):
        pass

    def dump(self):
        pass
