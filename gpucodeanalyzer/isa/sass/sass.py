import re
from ...generic_cfg import Instruction, ControlInsn, Register, Memory, Operand
from ...def_use import DefUseAnalysis

# assemblies extracted from nvuc files are "bare" with no function name and have one function.
# assemblies dumped from cuobjdump usually have function name information and are multiple functions.

SASS_INSN_RE = re.compile(r"^\s*/\*([0-9a-f]+)\*/\s+(.+) ;(\s*/\* 0x([0-9a-f]+) \*/)?$")
SASS_REG_RE = re.compile(r"-?(((UR|R|!?P|B|!?UP)\d+)(\.reuse|\.B[123]|\.H0_H0)?)|(UPR|UPT|PR|PT|-?RZ|URZ|SRZ|SR_CTAID\.?|SR_TID\.?)")
SASS_ADDR_RE = re.compile(r"\[(?P<reg1>R[0-9Z]+)(\.(?P<suff>U32|X16))?(\+(?P<reg2>UR[0-9Z]+)|(?P<imm>0x.+))?\]")

CX_RE = re.compile(r"-?cx\[(?P<regbase>.+)\]\[(?P<offset>.+)\]")
C_RE = re.compile(r"-?c\[(?P<bank>.+)\]\[(?P<regoffset>R.+)\]")

CONSTANT_REGS = set(['RZ', 'SRZ', 'URZ', 'PT', 'UPT', 'SR_TID.X', 'SR_CTAID.X',
                     'SR_TID.Y', 'SR_TID.Z', 'SR_CTAID.Y', 'SR_CTAID.Z',
                     'UPR']) # ?? need to think about this, since PR would be here too?

REG_NUMBER = re.compile(r'(?P<prefix>[^0-9]+)(?P<num>\d+|T)$')
PT_NUM = 7
PR_NUM = 8

class SASSRegister(Register):
    def __init__(self, n, is_inverted = False, is_negated = False, is_reuse = False, suffix = None):
        super().__init__(n)

        # todo: reuse, !, .cc
        self.is_inverted = is_inverted
        self.is_negated = is_negated
        self.is_reuse = is_reuse
        self.suffix = suffix

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

        if self.suffix:
            n = n + suffix

        if self.is_inverted:
            return "!" + n

        if self.is_negated:
            return "-" + n

        return n

    def number(self):
        if self.n == "PR":
            return PR_NUM
        elif self.n == "UPR":
            raise NotImplementedError

        m = REG_NUMBER.search(self.n)
        assert m is not None, self.n
        num = m.group('num')
        if num  == 'T':
            return PT_NUM
        else:
            return int(num)

    def adjacent(self, adj = 1):
        if self.n == "RZ" or self.n == "URZ":
            return [self]*adj

        regno = re.compile(r'(?P<prefix>[^0-9]+)(?P<num>\d+)$')
        m = regno.search(self.n)
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
    # has multiple explicit write registers
    WRITE_COUNT = {'BSYNC': 0,
                   ('IADD3', 5): 2,
                   ('IADD3', 6): 3,
                   ('LOP3.LUT', 7): 2,
                   ('UIADD3', 6): 3,
                   'RET.REL.NODEC': 0,
                   ('BRA.U', 2): 0, # for the BRA.U UP1, 0x... form
                   'BRX': 0
                   }

    # writes to multiple registers implicitly
    MULTI_WRITER = {'LDG.E.128.STRONG.GPU': {0: 4},
                    'LDG.E.128.CONSTANT': {0: 4},
                    'LDG.E.LTC128B.CONSTANT': {0: 4},
                    'ULDC.64': {0: 2},
                    'HMMA.16816.F32': {0: 4},
                    'IMAD.WIDE.U32': {0: 2},
                    'UIMAD.WIDE.U32': {0: 2},
                    'IMAD.WIDE': {0: 2},
                    'LDSM.16.MT88.4': {0: 4},
                    'LDS.128': {0: 4},
                    'LDG.E.128': {0: 4},
                    'LDCU.64': {0: 2},
                    'FMUL2.FTZ.RZ': {0: 2},
                    'LDTM.x32': {0: 32}
                    }

    READ_WRITE = {'IMAD.HI.U32': {0}}

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

                if " " in a:
                    a = a.split()[0]
                    #a = a[:-len(" 0x0")] # RET.REL.NODEC R4 0x0 ; BRX, etc.

                if a[0] == "!":
                    a = a[1:]
                    is_inverted = True

                if a[0] == "-":
                    a = a[1:]
                    is_negated = True

                suffix = []
                reg_suffixes = [".reuse", ".B1", ".B2", ".B3", ".H0_H0",
                                ".H1", ".HI_LO", ".F32", ".F32x2"]
                while True:
                    for rs in reg_suffixes:
                        if a.endswith(rs):
                            a = a[:-len(rs)]
                            suffix.append(rs)
                            if rs == ".reuse":
                                is_reuse = True
                            break
                    else:
                        break

                suffix = "".join(reversed(suffix))
                if len(suffix) == 0:
                    suffix = None

                r = SASSRegister(a, is_inverted = is_inverted,
                                 is_negated = is_negated,
                                 is_reuse = is_reuse,
                                 suffix = suffix)

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

    def code(self):
        return f"/*{self.label}*/ {self.insn} ;"

    def predicated(self):
        return self.predicate is not None

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
            read = self.opcode in self.READ_WRITE and k in self.READ_WRITE[self.opcode]

            yield SASSOperand(a, write = True, read = read)
            if k in mw:
                for r in a.adjacent(mw[k] - 1):
                    yield SASSOperand(r, read = read, write = True, implicit = True)

        reads = self.args[write_args:]
        for a in reads:
            yield SASSOperand(a, read = True)

    def _decode_predset_imm(self, regset, uniform = ""):
        rs = int(regset, 16)
        assert rs < 256, rs

        out = []
        for i in range(8):
            if (rs & 1):
                out.append(SASSRegister(f"{uniform}P{i}"))

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
                else:
                    cm = C_RE.match(x)
                    if cm:
                        rds.append(SASSRegister(cm.group('regoffset')))

        if self.opcode == "P2R":
            rds.extend(self._decode_predset_imm(self.args[-1]))
        elif self.opcode == "UP2UR":
            assert isinstance(self.args[1], Register) and self.args[1].n == "UPR"
            rds.extend(self._decode_predset_imm(self.args[-1], uniform="U"))

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
    def targets(self):
        # TODO: at some point handle conditional branches as well
        if self.indirect_targets is None:
            return [self.target()]
        else:
            return self.indirect_targets

    def target(self):
        if self.opcode == "EXIT":
            return "_exit"
        elif self.opcode == "RET.REL.NODEC":
            if self.indirect_targets is None:
                return "_exit" # for now
            else:
                raise ValueError # must call targets()
        elif self.opcode == "BRX":
            if self.indirect_targets is None:
                # metadata must set this
                raise NotImplementedError
            else:
                raise ValueError # must call targets()
        else:
            addr_arg = 0
            if self.opcode == "BRA.U":
                addr_arg = 1 # BRA.U !UP0, addr
            elif self.opcode == "BRA":
                if isinstance(self.args[0], SASSRegister):
                    # on CC 10.0: @!P1 BRA !P2, 0xe8a0
                    addr_arg = 1

            assert isinstance(self.args[addr_arg], str), f"Expecting address: {self.opcode} {self.args[addr_arg]} {addr_arg}"
            if self.args[addr_arg].startswith('0x'):
                tgt = self.args[addr_arg][2:]
                if len(tgt) < 4:
                    tgt = "0"*(4 - len(tgt)) + tgt
                return tgt
            else:
                return self.args[0]

    def is_conditional(self):
        return (self.predicate is not None) or (self.opcode == "BRA.U" and isinstance(self.args[0], Register))

    def is_indirect(self):
        return self.opcode == "RET.REL.NODEC" or self.opcode == "BRX"


class SASSIndirectResolver:
    def __init__(self, cfg, indirects):
        self.cfg = cfg
        self.indirects = indirects
        self.instructions = dict([(i.label, i) for i in self.cfg.all_instructions()])

    def resolve(self):
        self.da = DefUseAnalysis(self.cfg)
        self.da.build_definitions()
        self.da.reaching_defns(quiet = True)

        iaddr = {}
        for i in self.indirects:
            iaddr[i] = self.resolve_indirect(i)
            insn = self.instructions[i]

        return self.cfg.update_indirects(iaddr)

    def resolve_indirect(self, indirect):
        if self.instructions[indirect].opcode == 'BRX':
            return self.instructions[indirect].indirect_targets

        chain = [self.instructions[indirect]]
        k = 0
        while k < len(chain):
            for r in self.da.rdefs[chain[k].label]:
                chain.append(self.instructions[r[1]])

            k = k + 1

        addresses = []
        for i in chain:
            assert i.opcode in {'RET.REL.NODEC', 'MOV'}, f"{i.opcode} {chain}"
            if i.opcode == 'MOV' and isinstance(i.args[1], str) and i.args[1].startswith('0x'):
                addr = i.args[1][2:]
                assert addr in self.instructions, f"{i} does not contain a valid address {addr}"
                addresses.append(addr)

        return addresses


class SASSFile:
    SASS_CONTROL_INSN = re.compile("EXIT|BRA|CALL.REL.NOINC|RET.REL.NODEC|BRX")

    def __init__(self, f, metadata = None):
        self.f = f
        self.code = []
        self.metadata = metadata
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

            if i.is_control() and i.is_indirect() and i.opcode == "BRX":
                assert self.metadata is not None, 'Code contains BRX and metadata about indirect branches must be provided'
                assert len(self.metadata) == 1, f"Multiple functions present, but function name is unknown"
                fn_name = list(self.metadata.keys())[0]
                brx = self.metadata[fn_name].get('EIATTR_INDIRECT_BRANCH_TARGETS', {})
                assert i.label in brx, f'No indirect targets for {i.label} found'
                i.indirect_targets = brx[i.label]

            return i

        return None

    def resolve_indirects(self, cfg, indirects):
        if len(indirects) == 0: return

        changed = True
        while changed:
            ir = SASSIndirectResolver(cfg, indirects)
            changed = ir.resolve()

    def dump(self):
        for i in self.code:
            print(i)
