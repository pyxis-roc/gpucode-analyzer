class SASS2C:
    def __init__(self, output):
        self.output = output

    def init_cfg(self, cfg):
        self.cfg = cfg
        self.output.write("// cfg\n")
        func_name = "default_sass_name" # until we get support for functions
        args = [] # need to work this out
        self.output.write(f"void {func_name}({','.join(args)}) {{\n")

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
