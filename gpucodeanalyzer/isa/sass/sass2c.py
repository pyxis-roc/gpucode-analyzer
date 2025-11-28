from .sass import SASSRegister

class SASS2C:
    def __init__(self, output):
        self.output = output
        self.causes = {}
        self.counters = []

    def declare_registers(self):
        self.output.write("    const sass_reg RZ = 0;\n")
        self.output.write("    const sass_reg URZ = 0;\n")
        self.output.write("    const sass_predicate_reg PT = 1;\n")

        declared = set(['RZ', 'PT', 'URZ'])
        for i in self.cfg.all_instructions():
            for x in i.args:
                if isinstance(x, SASSRegister):
                    n = x.n
                    if n not in declared:
                        if n.startswith("R") or n.startswith("UR"):
                            self.output.write(f"    sass_reg {n};\n")
                            declared.add(n)
                        elif n.startswith('P'):
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
                            self.output.write(f"    // {x}\n")

    def declare_counts(self):
        for b in self.cfg.blocks:
            try:
                t = b.target()
                cv = f"bbcount_{t}"
                self.output.write(f"    uint64_t {cv} = 0;\n")
                self.counters.append(cv)
            except ValueError:
                pass

    def init_cfg(self, cfg):
        self.cfg = cfg
        self.output.write("#include <stdint.h>\n")
        self.output.write("#include <stdbool.h>\n")
        self.output.write("#include <stdio.h>\n")
        self.output.write('#include "sass_insns.h"\n\n')
        self.output.write('#include "lop3_lut.h"\n\n')

        self.output.write("typedef uint32_t sass_reg;\n")
        self.output.write("typedef bool sass_predicate_reg;\n")
        self.output.write("typedef struct { sass_reg X; sass_reg Y; sass_reg Z; } sass_vec3;\n\n")
        self.output.write("// cfg\n")
        func_name = "default_sass_name" # until we get support for functions
        args = ['sass_vec3 GRID_DIM', 'sass_vec3 CTA_DIM'] # need to work this out
        self.output.write(f"void {func_name}({','.join(args)}) {{\n")

        self.declare_counts()
        self.output.write(f"    sass_vec3 SR_CTAID;\n")
        self.output.write(f"    sass_vec3 SR_TID;\n")
        
        self.output.write("for(SR_CTAID.Z=0; SR_CTAID.Z<GRID_DIM.Z; SR_CTAID.Z++) {\n")
        self.output.write("for(SR_CTAID.Y=0; SR_CTAID.Y<GRID_DIM.Y; SR_CTAID.Y++) {\n")
        self.output.write("for(SR_CTAID.X=0; SR_CTAID.X<GRID_DIM.X; SR_CTAID.X++) {\n")

        self.output.write("  for(SR_TID.Z=0; SR_TID.Z<CTA_DIM.Z; SR_TID.Z++) {\n")
        self.output.write("  for(SR_TID.Y=0; SR_TID.Y<CTA_DIM.Y; SR_TID.Y++) {\n")
        self.output.write("  for(SR_TID.X=0; SR_TID.X<CTA_DIM.X; SR_TID.X++) {\n")

        self.declare_registers()


    def output_block_order(self):
        order = [('_start', -1)]
        for b in self.cfg.blocks:
            order.append((b.target(), int(b.target(), 16)))

        order.sort(key=lambda k: k[1])
        order = [v[0] for v in order]
        order.append('_exit')

        return order

    def _xlat_failure(self, cause):
        self.causes[cause] = self.causes.get(cause, 0) + 1

    def xlat_insn(self, i):
        def process_c_lookup(cl):
            if cl == "c[0x0][0x0]":
                return "GRID_DIM.X" # webgpu only?
            else:
                return None

        def process_cx_lookup(cx):
            return cx

        def process_args(arglist):
            o = []
            for a in arglist:
                if isinstance(a, SASSRegister):
                    o.append(a.n)
                elif isinstance(a, str):
                    if a.startswith('-') or a.startswith('0x'):
                        o.append(f"(sass_reg) {a}")
                    elif a.startswith('c['):
                        c = process_c_lookup(a)
                        if c:
                            o.append(c)
                        else:
                            self._xlat_failure('constant')
                            return None
                    elif a.startswith('cx['):
                        self._xlat_failure('cx')
                        return None
                        o.append(process_cx_lookup(a))
                    else:
                        raise NotImplementedError(a)

            return ', '.join(o)

        args = None
        opcode = None
        if i.opcode == "S2R":
            opcode = "S2R"
        elif i.opcode.startswith("IMAD"):
            opcode = i.opcode.replace(".", "_")
        elif i.opcode == "IMAD":
            opcode = "IMAD"
        elif i.opcode == "IADD3":
            opcode = "IADD3"
        elif i.opcode == "EXIT":
            opcode = "EXIT"
        elif i.opcode == "UMOV":
            opcode = "UMOV"
        elif i.opcode == "UIADD3":
            opcode = "UIADD3"
        elif i.opcode == "LOP3.LUT": # other variants not yet supported, see ptx
            opcode = "LOP3_LUT"
            assert i.args[-1] == "!PT", i.args[-1]
            args = process_args(i.args[:-1])
        elif i.opcode.startswith("ISETP."):
            cvtop = i.opcode.replace('.', '_')
            opcode = [cvtop + "_D0"]
            assert i.args[0] != "PT"
            if isinstance(i.args[1], SASSRegister) and i.args[1].n != "PT": # can't write to constant register
                opcode.append(cvtop + "_D1")
        elif i.opcode == "BRA":
            opcode = i.opcode
            assert i.args[0].startswith('0x'), i.args[0]
            label = i.args[0][2:]

            if len(label) < 4:
                label = "0"*(4-len(label)) + label

            assert len(label) == 4, label

            args = f'label_{label}'
        else:
            self._xlat_failure(f'opcode {i.opcode}')

        if opcode:
            if args is None:
                args = process_args(i.args)

            if args is not None:
                if(i.predicate):
                    self.output.write(f"    if({i.predicate})\n    ")

                if isinstance(opcode, str):
                    self.output.write(f"    {opcode}({args});\n")
                elif isinstance(opcode, list):
                    for op in opcode:
                        self.output.write(f"    {op}({args});\n")
                else:
                    raise NotImplementedError

                return True

        return False

    def convert_block(self, block):
        if not hasattr(block, '_target'): return

        self.output.write(f'label_{block.target()}:\n')
        self.output.write(f'    bbcount_{block.target()}++;\n')

        for i in block.code:
            if not self.xlat_insn(i):
                self.output.write(f"    // {i.insn}\n")

        self.output.write("\n")

    def finish_cfg(self):
        self.output.write("}}}}}}\n")
        self.output.write("label_exit:\n")
        for c in self.counters:
            self.output.write(f'    printf("{c} = %lu\\n", {c});\n')
        self.output.write("    ;\n")
        self.output.write("}\n")

    def finish(self):
        print(self.causes)
