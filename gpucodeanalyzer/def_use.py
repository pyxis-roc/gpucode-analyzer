from .generic_cfg import Register

class DefUseAnalysis:
    def __init__(self, cfg):
        self.cfg = cfg
        self.defns = {}

    def build_definitions(self):
        defs_r2n = {}
        defs_n2ri = {}
        defs_i2n = {}

        defno = 0
        for b in self.cfg.blocks:
            for i in b.code:
                for r in i.writes():
                    if isinstance(r, Register):
                        if r.n not in defs_r2n:
                            defs_r2n[r.n] = set()

                        if i.label not in defs_i2n:
                            defs_i2n[i.label] = set()

                        defs_n2ri[defno] = (r.n, i.label)
                        defs_r2n[r.n].add(defno)
                        defs_i2n[i.label].add(defno)

                        defno += 1

        self.defns_r2n = defs_r2n
        self.defns_n2ri = defs_n2ri
        self.defns_i2n = defs_i2n


    def reaching_defns(self):
        def get_predecessor_rd(n, b):
            if n == 0:
                # first instruction in block, look at predecessors of block
                out = set()
                for p in b.predecessors.values():
                    out = out.union(rd[p.code[-1].label])
                return out
            else:
                return rd[b.code[n-1].label]

        kills = {}
        gens = {}

        rd = {}
        rd_in = {}
        for b in self.cfg.blocks:
            for i in b.code:
                k = set()
                g = self.defns_i2n.get(i.label, set()) # could be empty
                for r in i.writes():
                    if isinstance(r, Register):
                        all_defs = self.defns_r2n[r.n]
                        k = k.union(all_defs)
                        k = k - g

                kills[i.label] = k
                gens[i.label] = g
                rd[i.label] = set()

        changed = True
        while changed:
            changed = False
            for b in self.cfg.blocks:
                for n, i in enumerate(b.code):
                    x = get_predecessor_rd(n, b)
                    if n == 0:
                        rd_in[i.label] = x
                    else:
                        rd_in[i.label] = rd[b.code[n-1].label]

                    rdnew = gens[i.label].union(x - kills[i.label])
                    if rdnew != rd[i.label]:
                        rd[i.label] = rdnew
                        changed = True

        rdefs = {}
        for b in self.cfg.blocks:
            for i in b.code:
                reaching = rd_in[i.label]

                reads = set([r.n for r in i.reads() if isinstance(r, Register) and not r.is_constant()])

                rsub = [self.defns_n2ri[d] for d in reaching]
                rsub = [x for x in rsub if x[0] in reads]

                if len(reads) != len(set([x[0] for x in rsub])):
                    print("*** MISSING DEFNS ***", i.label, reads, rsub)

                rdefs[i.label] = rsub

        self.rdefs = rdefs

def test():
    from gpucodeanalyzer.isa.sass import SASSFile
    from gpucodeanalyzer.generic_cfg import CFG
    import argparse

    p = argparse.ArgumentParser(description="Process SASS file")
    p.add_argument("sassfile")
    args = p.parse_args()

    code = SASSFile(args.sassfile)
    cfg = CFG(code)
    cfg.build()
    da = DefUseAnalysis(cfg)
    da.build_definitions()
    da.reaching_defns()
    for insn in cfg.all_instructions():
        print(insn.label, insn.insn, da.rdefs[insn.label], "reads", insn.reads(), "writes", insn.writes())


if __name__=="__main__":
    test()
