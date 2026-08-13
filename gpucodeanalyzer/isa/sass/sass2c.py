from .sass import SASSRegister, SASSConstantRef
from itertools import chain
import re
from sassparser import AST2SASS
from sassparser.sasstokens import Hexadecimal

DECIMAL_RE = re.compile(r'-?[0-9]+')

class XlatInfo:
    def __init__(self, data):
        self.data = data

    def functions(self):
        return self.data.keys()

    def is_cbank(self, fn):
        return self.data[fn].get('cbank', False)

    def get_function_data(self, fn):
        return self.data[fn]

    def get_global_decls(self, fn):
        return self.data[fn].get("global_decl", [])

    def get_main_inject_code(self, fn):
        return self.data[fn].get("main_inject_code", "")

    def get_args(self, fn):
        return self.data[fn].get("args", [])

    def get_arg_names(self, fn):
        #TODO: more robust
        argnames = [x.split(" ")[-1] for x in self.get_args(fn)]
        return argnames

    def get_block_dim(self, fn):
        return self.data[fn].get('block_dim', None)

    def get_grid_dim(self, fn):
        return self.data[fn].get('grid_dim', None)

    def get_arg_values(self, fn):
        return self.data[fn].get('arg_values', [])

    def map_constant(self, fn, constant, cref, sz = '32'):
        if self.is_cbank(fn):
            if isinstance(cref.bank, Hexadecimal):
                bank = cref.bank.value
            else:
                raise NotImplementedError(bank)

            if len(cref.offset) == 1:
                if isinstance(cref.offset[0], Hexadecimal):
                    offset = cref.offset[0].raw
                else:
                    raise NotImplementedError(cref.offset[0])
            else:
                raise NotImplementedError(cref.offset)

            return f"READ_U{sz}(&cbank{bank}[{offset}])"
        else:
            return self.data[fn].get("constant_map", {}).get(constant, None)

    @staticmethod
    def create(sassfile, cbank = False):
        out = {}
        for c in sassfile.codes:
            out[c] = {'global_decl': [], # C global declarations
                      'args': [], # C argument declarations, for now
                      'block_dim': None, # 3-element vector
                      'grid_dim': None, # 3-element vector
                      'arg_values': [{}],
                      'constant_map': {},
                      'cbank': cbank,    # one arg with cbank
                      'main_inject_code': "",
                      }

            if sassfile.metadata:
                fnmeta = sassfile.metadata[c]
                if not 'EIATTR_PARAM_CBANK' in fnmeta: continue

                if cbank:
                    out[c]['args'] = ['uint8_t* cbank0']
                    out[c]['arg_values'][0]['cbank0'] = f'{c}_cbank0'
                    out[c]['global_decl'].append('#include "cbank0.h"')
                    continue

                start = fnmeta['EIATTR_PARAM_CBANK']['start']
                out[c]['args'] = ['']*len(fnmeta['EIATTR_KPARAM_INFO'])
                for kpi in fnmeta['EIATTR_KPARAM_INFO']:
                    cparam = f"c[0x0][0x{start+kpi['offset']:x}]"
                    cc = cparam.replace("[", "_").replace("]", "_")

                    out[c]['constant_map'][cparam] = cc

                    sz = kpi['size']
                    if sz == 1:
                        sztype = 'uint8_t'
                    elif sz == 4:
                        sztype = 'uint32_t'
                    elif sz == 8:
                        sztype = 'uint64_t' # could also be pointer
                    elif sz > 8:
                        sztype = f'uint8_t[{sz}]'
                    else:
                        raise NotImplementedError(f'Unknown argument size {sz}')

                    out[c]['args'][kpi['ordinal']] = f"{sztype} {cc}"
                    out[c]['arg_values'][0][cc] = ''

        return out

class Hook:
    name = None
    def gencode(self, translator, where, output):
        pass

    def params(self, what):
        return []

    def args(self, what):
        return []

class BlockHook(Hook):
    def block_entry_hook(self, translator, block, output):
        pass

    # TODO: think about exit hooks, complicated by control flow.

class PathTraceBlockHook(BlockHook):
    def gencode(self, translator, where, output):
        if where == 'includes':
            output.write("#include <pathtrace.h>\n")
        elif where == 'kernel':
            output.write(f'    printf("# pathtrace metadata: %d %d %d %d %d %d\\n", GRID_DIM.X, GRID_DIM.Y, GRID_DIM.Z, CTA_DIM.X, CTA_DIM.Y, CTA_DIM.Z);\n')
            output.write(f"    struct path_traces *pt = path_trace_create(GRID_DIM.X*GRID_DIM.Y*GRID_DIM.Z*CTA_DIM.X*CTA_DIM.Y*CTA_DIM.Z); \n")
            output.write(f'    if(!pt) fprintf(stderr, "ERROR: Failed to create path trace.\\n");\n')
            output.write(f'    uint64_t pt_trace_id = 0;\n')
        elif where == 'threadloop':
            output.write(f"        path_trace_init(pt, pt_trace_id, pt_trace_id);\n")
        elif where == 'kernel_end':
            output.write(f"        path_trace_dump(pt);\n")

    def params(self, what):
        if what == 'thread':
            return ['struct trace *trace']

        return []

    def args(self, what):
        if what == 'thread':
            return ['pt == NULL ? NULL : &pt->trace[pt_trace_id++]']

        return []

    def block_entry_hook(self, translator, block, output):
        output.write(f'    path_trace_add_entry_fast(trace, 0x{block.target()}, 1);\n')

class DebugFlowBlockHook(BlockHook):
    def gencode(self, translator, where, output):
        if where == 'global':
            output.write("bool debug_flow;\n");

    def block_entry_hook(self, translator, block, output):
        output.write(f'    if(debug_flow) printf("{block.target()}\\n");\n')

class BBCountBlockHook(BlockHook):
    def block_entry_hook(self, translator, block, output):
        output.write(f'    {translator.func_name}_bbcount_{block.target()}++;\n')

    def gencode(self, translator, where, output):
        if where == 'global_cfg':
            counters = []
            for b in translator.cfg.blocks:
                try:
                    t = b.target()
                    if t in ('_start', '_exit'): continue
                    cv = f"{translator.func_name}_bbcount_{t}"
                    output.write(f"    uint64_t {cv} = 0;\n")
                    counters.append(cv)
                except ValueError:
                    pass

            output.write(f"void {translator.func_name}_counters() {{\n")
            for c in counters:
                output.write(f'    printf("{c} = %lu\\n", {c});\n')

            output.write("}\n")

class InsnHook(Hook):
    def pre_hook(self, insn, output, translated):
        pass

    def post_hook(self, insn, output, translated):
        pass

class DebugOutputInsnHook(InsnHook):
    name = 'DebugOutput' # should be class name?
    def gencode(self, translator, where, output):
        if where == 'global':
            output.write("bool debug_output;\n");
        elif where == 'kernel_end':
            output.write(f"    {translator.func_name}_counters();\n")

    def post_hook(self, insn, output, translated):
        if not translated:
            return

        dbg_spec = []
        dbg_args = []
        for r in insn.writes():
            if isinstance(r, SASSRegister):
                dbg_spec.append(f"{r.n}: %x ")
                dbg_args.append(r.n)

        if len(dbg_spec):
            fmt_str = '"' + ''.join(dbg_spec) + '"'
            fmt_val = ", ".join(dbg_args)
            if insn.predicate:
                debug_predicate = f"{insn.predicate} && "
            else:
                debug_predicate = ""

            output.write(f'    if({debug_predicate}debug_output) printf("{insn.label} " {fmt_str}"\\n", {fmt_val});\n')

class SASS2C:
    def __init__(self, output, xlatinfo, hooks = None, config = None):
        self.output = output
        self.causes = {}
        self.counters = []
        self.config = set() if config is None else config
        self.xlatinfo = XlatInfo(xlatinfo)
        self.hooks = [DebugOutputInsnHook()]
        self.block_hooks = []
        self.a2s = AST2SASS()

        if ('gen_path_info' in self.config):
            self.block_hooks.append(PathTraceBlockHook())

        self.block_hooks.append(BBCountBlockHook())
        self.block_hooks.append(DebugFlowBlockHook())

        if hooks is not None:
            self.hooks.extend(hooks)

    def call_hook_gencodes(self, where):
        for hk in chain(self.block_hooks, self.hooks):
            hk.gencode(self, where, self.output)

    def init_module(self):
        self.output.write("#include <stdint.h>\n")
        self.output.write("#include <stdbool.h>\n")
        self.output.write("#include <stdio.h>\n")
        self.output.write("#include <assert.h>\n")

        self.call_hook_gencodes('includes')

        self.output.write('#include "sass_insns.h"\n\n')
        self.output.write('#include "lop3_lut.h"\n\n')

        self.output.write("typedef uint32_t sass_reg;\n")
        self.output.write("typedef bool sass_predicate_reg;\n")
        self.output.write("typedef struct { sass_reg X; sass_reg Y; sass_reg Z; } sass_vec3;\n\n")

        self.call_hook_gencodes('global')

    def declare_registers(self):
        self.output.write("    const sass_reg RZ = 0;\n")
        self.output.write("    const sass_reg URZ = 0;\n")
        self.output.write("    const sass_reg SRZ = 0;\n")
        self.output.write("    const sass_predicate_reg PT = 1;\n")
        self.output.write("    const sass_predicate_reg UPT = 1;\n")

        declared = set(['RZ', 'PT', 'URZ', 'SRZ', 'UPT'])
        for i in self.cfg.all_instructions():
            for x in i.args:
                if isinstance(x, SASSRegister):
                    n = x.n
                    if n not in declared:
                        if n.startswith("R") or n.startswith("UR"):
                            self.output.write(f"    sass_reg {n};\n")
                            declared.add(n)
                        elif n.startswith('P') or n.startswith('UP'):
                            self.output.write(f"    sass_predicate_reg {n};\n")
                            declared.add(n)
                        elif n.startswith('SR_CTAID'):
                            #self.output.write(f"    sass_vec3 SR_CTAID;\n")
                            declared.add('SR_CTAID.X')
                            declared.add('SR_CTAID.Y')
                            declared.add('SR_CTAID.Z')
                        elif n.startswith('SR_TID'):
                            #self.output.write(f"    sass_vec3 SR_TID;\n")
                            declared.add('SR_TID.X')
                            declared.add('SR_TID.Y')
                            declared.add('SR_TID.Z')
                        else:
                            self.output.write(f"    // unsupported: {x}\n")

    def init_cfg(self, cfg, func_name):
        self.cfg = cfg
        self.func_name = func_name

        self.call_hook_gencodes('global_cfg')

        self.output.write("// cfg\n")

        args = []
        for bh in self.block_hooks:
            args.extend(bh.params('thread'))

        args.extend(['const sass_vec3 GRID_DIM', 'const sass_vec3 CTA_DIM', 'const sass_vec3 SR_CTAID', 'const sass_vec3 SR_TID'])
        args.extend(self.xlatinfo.get_args(func_name))

        # ugly, but should work, needs to be in a separate globals block
        for l in self.xlatinfo.get_global_decls(func_name):
            self.output.write(l + "\n")

        self.output.write(f"void {func_name}_thread({', '.join(args)}) {{\n")
        self.declare_registers()

    def output_block_order(self):
        order = [('_start', -1)]
        for b in self.cfg.blocks:
            if b.name in ('_start', '_exit'): continue
            order.append((b.target(), int(b.target(), 16)))

        order.sort(key=lambda k: k[1])
        order = [v[0] for v in order]
        order.append('_exit')

        return order

    def _xlat_failure(self, cause):
        self.causes[cause] = self.causes.get(cause, 0) + 1

    def xlat_insn(self, i, fn, pre_hook = None, post_hook = None):
        def process_c_lookup(ccl, sz = '32'):
            neg = "-" if ccl._parsed.neg else ""
            cl = self.a2s.visit(ccl._parsed)
            if neg: cl = cl[1:]

            mc = self.xlatinfo.map_constant(fn, cl, ccl._parsed.value, sz=sz)

            if mc is None:
                # TODO: make this a compiler-specific mapping table
                if cl == "c[0x0][0x0]":
                    return neg + "CTA_DIM.X" # in webgpu is this grid_dim.x? also cuda?
                elif cl == "c[0x0][0xc]":
                    return neg + "GRID_DIM.X" # cuda

                mc = cl
                #assert mc is not None, f"{fn} {cl}"

            return neg + mc

        def process_cx_lookup(cx, sz = '32'):
            return self.xlatinfo.map_constant(fn, cx, sz = sz)

        def _decode_regset_imm(regset):
            rs = int(regset, 16)
            assert rs < 256, rs

            out = []
            for i in range(8):
                if (rs & 1):
                    out.append(f"(P{i} << {i})")

                rs >>= 1
                if rs == 0: break

            return " | ".join(out)

        def process_args(arglist, expand_dst_adj = 0):
            o = []
            for ndx, a in enumerate(arglist):
                if isinstance(a, SASSRegister):
                    o.append(a.operand(reuse=False))
                    if ndx == 0 and expand_dst_adj:
                        o.extend([aa.operand(reuse=False) for aa in a.adjacent(expand_dst_adj)])
                elif isinstance(a, SASSConstantRef):
                    c = process_c_lookup(a) if a.ty == 'c' else process_cx_lookup(a)
                    if c:
                        o.append(c)
                    else:
                        self._xlat_failure(f'constant {a.ty} {a}')
                        return None
                elif isinstance(a, str):
                    if a.startswith('-') or a.startswith('0x'):
                        o.append(f"(sass_reg) {a}")
                    elif a == "+INF":
                        o.append('INFINITY')
                    elif a == "-INF":
                        o.append('-INFINITY')
                    elif DECIMAL_RE.match(a):
                        o.append(f'(sass_reg) {a}')
                    else:
                        # non-local lookup for i
                        raise NotImplementedError(f"Argument {a} for {i.opcode}")
                else:
                    raise NotImplementedError(a)

            return ', '.join(o)

        args = None
        opcode = None
        if i.opcode == "CS2R":
            opcode = "CS2R"
        elif i.opcode in {"S2R", "S2UR"}:
            opcode = i.opcode
        elif i.opcode.startswith("IMAD"):
            opcode = i.opcode.replace(".", "_")
        elif i.opcode in {"IMAD", "UIMAD"}:
            opcode = i.opcode
        elif i.opcode == "IADD3":
            opcode = "IADD3"
        elif i.opcode == "IADD3.X":
            opcode = "IADD3_X"
        elif i.opcode == "IABS":
            opcode = "IABS"
        elif i.opcode == "EXIT":
            opcode = "EXIT"
        elif i.opcode == "MOV":
            opcode = "MOV"
        elif i.opcode == "UMOV":
            opcode = "UMOV"
        elif i.opcode == "UIADD3":
            opcode = "UIADD3"
        elif i.opcode == "LOP3.LUT": # other variants not yet supported, see ptx
            opcode = "LOP3_LUT"
            # !PT
            assert isinstance(i.args[-1], SASSRegister) and i.args[-1].n == "PT" and i.args[-1].is_not
            args = process_args(i.args[:-1])
        elif i.opcode == "PLOP3.LUT":
            opcode = "PLOP3_LUT"
            assert i.args[-1] == "0x0", i.args[-1]
            assert i.args[1].n == "PT", i.args[1]
            args = process_args(i.args)
        elif i.opcode == "ULOP3.LUT": # other variants not yet supported, see ptx
            opcode = "ULOP3_LUT"
            assert isinstance(i.args[-1], SASSRegister) and i.args[-1].n == "UPT" and i.args[-1].is_not, i.args[-1]
            args = process_args(i.args[:-1])
        elif i.opcode == "IMNMX":
            opcode = "IMNMX"
        elif i.opcode == "IMNMX.U32":
            opcode = "IMNMX_U32"
        elif i.opcode == "I2F.RP":
            opcode = "I2F_RP"
        elif i.opcode == "I2F.U32.RP":
            opcode = "I2F_U32_RP"
        elif i.opcode == "MUFU.RCP":
            opcode = "MUFU_RCP"
        elif i.opcode == "F2I.FTZ.U32.TRUNC.NTZ":
            opcode = "F2I_FTZ_U32_TRUNC_NTZ"
        elif i.opcode == "ULDC":
            opcode = "ULDC"
        elif i.opcode == "ULEA.HI":
            opcode = "ULEA_HI"
        elif i.opcode in {"LEA", "ULEA"}:
            opcode = i.opcode
        elif i.opcode == "LEA.HI":
            opcode = "LEA_HI"
        elif i.opcode == "LEA.HI.SX32":
            opcode = "LEA_HI_SX32"
        elif i.opcode == "ULEA.HI.SX32":
            opcode = "ULEA_HI_SX32"
        elif i.opcode == "SEL" or i.opcode == "USEL":
            opcode = i.opcode
        elif i.opcode == "SGXT.U32":
            opcode = "SGXT_U32"
        elif i.opcode == "P2R":
            opcode = i.opcode
            assert i.args[1].n == "PR"
            #assert i.args[2].n == "RZ", i.args[2]
            args = process_args(i.args[:3]) + ", " + _decode_regset_imm(i.args[3])
        elif i.opcode == "ULDC.S8":
            args = process_args([i.args[1]])
            if args is not None:
                if args[0] == "&":
                    opcode = None
                    args = None
                else:
                    opcode = "ULDC_S8"
                    args = process_args(i.args)
        elif i.opcode == "ULDC.64": # usually an address
            args = process_args([i.args[1]])
            if args is not None:
                if args[0] == "&":
                    opcode = None
                    args = None
                else:
                    opcode = "ULDC_64"
                    args = process_args(i.args, expand_dst_adj = 1)
        elif i.opcode.startswith("FSETP."):
            cvtop = i.opcode.replace('.', '_')
            opcode = [cvtop + "_D0"]
            assert i.args[0] != "PT"
            if isinstance(i.args[1], SASSRegister) and i.args[1].n != "PT": # can't write to constant register
                opcode.append(cvtop + "_D1")

        elif i.opcode.startswith("ISETP."):
            cvtop = i.opcode.replace('.', '_')
            opcode = [cvtop + "_D0"]
            assert i.args[0] != "PT"
            if isinstance(i.args[1], SASSRegister) and i.args[1].n != "PT": # can't write to constant register
                opcode.append(cvtop + "_D1")

        elif i.opcode.startswith("UISETP."):
            cvtop = i.opcode.replace('.', '_')
            opcode = [cvtop + "_D0"]
            assert i.args[0] != "UPT"
            if isinstance(i.args[1], SASSRegister) and i.args[1].n != "UPT": # can't write to constant register
                opcode.append(cvtop + "_D1")
        elif i.opcode == "BRA" or i.opcode == "CALL.REL.NOINC":
            opcode = i.opcode.replace(".", "_")

            if isinstance(i.args[0], SASSRegister):
                opcode = opcode + "_PRED"
                assert i.args[1].startswith('0x'), i.args[1]
                label = i.args[1][2:]
                args = process_args(i.args[0:1]) + ", "
            else:
                assert i.args[0].startswith('0x'), i.args[0]
                label = i.args[0][2:]
                args = ''

            if len(label) < 4:
                label = "0"*(4-len(label)) + label

            assert len(label) >= 4, label

            args += f'label_{label}'
        elif i.opcode == "SHF.R.U32.HI":
            opcode = "SHF_R_U32_HI"
        elif i.opcode == "USHF.R.U32.HI":
            opcode = "USHF_R_U32_HI"
        elif i.opcode == "SHF.R.S32.HI":
            opcode = "SHF_R_S32_HI"
        elif i.opcode == "USHF.R.S32.HI":
            opcode = "USHF_R_S32_HI"
        elif i.opcode == "SHF.L.U32":
            opcode = "SHF_L_U32"
        elif i.opcode == "SHF.L.U64.HI":
            opcode = "SHF_L_U64_HI"
        elif i.opcode == "USHF.L.U32":
            opcode = "USHF_L_U32"
        else:
            self._xlat_failure(f'opcode {i.opcode}')

        if opcode:
            if args is None:
                args = process_args(i.args)

            if args is not None:
                if pre_hook: pre_hook(i, self.output, True)
                self.output.write(f"    /* {i.label} */    ")
                if(i.predicate):
                    self.output.write(f"    if({i.predicate})\n    ")

                if isinstance(opcode, str):
                    self.output.write(f"    {opcode}({args});\n")
                elif isinstance(opcode, list):
                    for op in opcode:
                        self.output.write(f"    {op}({args});\n")
                else:
                    raise NotImplementedError

                if post_hook: post_hook(i, self.output, True)
                return True

        if pre_hook: pre_hook(i, self.output, False)
        if post_hook: post_hook(i, self.output, False)

        return False

    def invoke_pre_hooks(self, insn, output, translated):
        for h in self.hooks:
            h.pre_hook(insn, output, translated)

    def invoke_post_hooks(self, insn, output, translated):
        for h in self.hooks:
            h.post_hook(insn, output, translated)


    def invoke_block_entry_hooks(self, block, output):
        for bh in self.block_hooks:
            bh.block_entry_hook(self,  block, output)

    def convert_block(self, block):
        if not hasattr(block, '_target'): return

        self.output.write(f'label_{block.target()}:\n')
        self.invoke_block_entry_hooks(block, self.output)

        for i in block.code:
            if not self.xlat_insn(i, self.func_name,
                                  self.invoke_pre_hooks, self.invoke_post_hooks):
                self.output.write(f"    // {i.label} {i.insn}\n")
                self.output.write("     assert(0);\n")

        self.output.write("\n")

    def generate_caller(self):
        self.output.write("int main(int argc, char *argv[]) {\n")

        ic = self.xlatinfo.get_main_inject_code(self.func_name)
        if ic:
            self.output.write(ic)

        bdim = self.xlatinfo.get_block_dim(self.func_name)
        gdim = self.xlatinfo.get_grid_dim(self.func_name)

        if bdim:
            bdim = ",".join(str(x) for x in bdim)
        else:
            bdim = ""

        if gdim:
            gdim = ",".join(str(x) for x in gdim)
        else:
            gdim = ""

        self.output.write(f"  sass_vec3 grid_dim = {{{gdim}}}, block_dim = {{{bdim}}};\n")

        arg_values = self.xlatinfo.get_arg_values(self.func_name)
        arg_names = self.xlatinfo.get_arg_names(self.func_name)

        if len(arg_values) > 0:
            # TODO: allow user to select which arguments
            arg_values = arg_values[0]

        arg_values = ", ".join([str(arg_values[a]) for a in arg_names])
        if arg_values != "": arg_values = ", " + arg_values

        self.output.write(f"  {self.func_name}(grid_dim, block_dim{arg_values});\n")

        self.output.write("}\n")

    def finish_cfg(self):
        self.output.write("label_exit:\n")
        self.output.write("    ;\n")
        self.output.write("}\n")

        args = ['const sass_vec3 GRID_DIM', 'const sass_vec3 CTA_DIM']
        args.extend(self.xlatinfo.get_args(self.func_name))

        self.output.write(f"void {self.func_name}({', '.join(args)}) {{\n")

        self.output.write(f"    sass_vec3 SR_CTAID;\n")
        self.output.write(f"    sass_vec3 SR_TID;\n")

        self.call_hook_gencodes('kernel')

        self.output.write("    for(SR_CTAID.Z=0; SR_CTAID.Z<GRID_DIM.Z; SR_CTAID.Z++) {\n")
        self.output.write("    for(SR_CTAID.Y=0; SR_CTAID.Y<GRID_DIM.Y; SR_CTAID.Y++) {\n")
        self.output.write("    for(SR_CTAID.X=0; SR_CTAID.X<GRID_DIM.X; SR_CTAID.X++) {\n")

        self.output.write("      for(SR_TID.Z=0; SR_TID.Z<CTA_DIM.Z; SR_TID.Z++) {\n")
        self.output.write("      for(SR_TID.Y=0; SR_TID.Y<CTA_DIM.Y; SR_TID.Y++) {\n")
        self.output.write("      for(SR_TID.X=0; SR_TID.X<CTA_DIM.X; SR_TID.X++) {\n")

        self.call_hook_gencodes('threadloop')

        call_args = []
        for h in chain(self.block_hooks, self.hooks):
            call_args.extend(h.args('thread'))

        call_args.extend(['GRID_DIM', 'CTA_DIM', 'SR_CTAID', 'SR_TID'])
        call_args.extend(self.xlatinfo.get_arg_names(self.func_name))

        call_args = ", ".join(call_args)

        self.output.write(f"       {self.func_name}_thread({call_args});\n")

        self.output.write("     }}}}}}\n")

        self.call_hook_gencodes('kernel_end')

        self.output.write("}\n")

        self.generate_caller()

        self.func_name = ""
        self.counters = []

    def finish(self):
        if len(self.causes):
            print("WARNING: Translation failed due to the following causes (missing instructions/data support + frequency of occurrence)")
            print(self.causes)

    @staticmethod
    def create_xlatinfo(sassfile, cbank = False):
        return XlatInfo.create(sassfile, cbank)
