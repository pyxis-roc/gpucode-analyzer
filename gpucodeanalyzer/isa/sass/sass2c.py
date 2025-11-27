from .sass import SASSRegister

class SASS2C:
    def __init__(self, output):
        self.output = output


    def declare_registers(self):
        self.output.write("\tconst sass_reg RZ = 0;\n")
        self.output.write("\tconst sass_predicate_reg PT = 1;\n")

        declared = set(['RZ', 'PT'])
        for i in self.cfg.all_instructions():
            for x in i.args:
                if isinstance(x, SASSRegister):
                    n = x.n
                    if n not in declared:
                        if n.startswith("R"):
                            self.output.write(f"\tsass_reg {n};\n")
                            declared.add(n)
                        elif n.startswith('P'):
                            self.output.write(f"\tsass_predicate_reg {n};\n")
                            declared.add(n)
                        elif n.startswith('SR_CTAID'):
                            self.output.write(f"\tsass_vec3 SR_CTAID;\n")
                            declared.add('SR_CTAID.X')
                            declared.add('SR_CTAID.Y')
                            declared.add('SR_CTAID.Z')
                        elif n.startswith('SR_TID'):
                            self.output.write(f"\tsass_vec3 SR_TID;\n")
                            declared.add('SR_TID.X')
                            declared.add('SR_TID.Y')
                            declared.add('SR_TID.Z')
                        else:
                            self.output.write(f"\t// {x}\n")

    def init_cfg(self, cfg):
        self.cfg = cfg
        self.output.write("#include <stdint.h>\n")
        self.output.write("#include <stdbool.h>\n")
        self.output.write("typedef uint32_t sass_reg;\n")
        self.output.write("typedef bool sass_predicate_reg;\n")
        self.output.write("typedef struct { sass_reg X; sass_reg Y; sass_reg Z; } sass_vec3;\n")
        self.output.write("// cfg\n")
        func_name = "default_sass_name" # until we get support for functions
        args = [] # need to work this out
        self.output.write(f"void {func_name}({','.join(args)}) {{\n")

        self.declare_registers()

    def output_block_order(self):
        order = [('_start', -1)]
        for b in self.cfg.blocks:
            order.append((b.target(), int(b.target(), 16)))

        order.sort(key=lambda k: k[1])
        order = [v[0] for v in order]
        order.append('_exit')

        return order


    def convert_block(self, block):
        for i in block.code:
            self.output.write(f"\t// {i}\n")

        self.output.write("\n")

    def finish_cfg(self):
        self.output.write("}\n")

    def finish(self):
        pass
