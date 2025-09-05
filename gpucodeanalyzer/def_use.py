from .generic_cfg import Register

class DefUseAnalysis:
    def __init__(self, cfg):
        self.cfg = cfg
        self.defns = {}

    def build_definitions(self):
        defs = {}
        for b in self.cfg.blocks:
            for i in b.code:
                for r in i.writes():
                    if isinstance(r, Register):
                        if r.n not in defs:
                            defs[r.n] = set()

                        defs[r.n].add(i.label)

        self.defns = defs

    def reaching_defns(self):
        kills = {}
        gens = {}

        for b in self.cfg.blocks:
            for i in b.code:
                k = {}
                g = set()
                for r in i.writes():
                    if isinstance(r, Register):
                        all_defs = self.defns[r.n]
                        k[r.n] = k.get(r.n, set()).union(all_defs)
                        k[r.n] = k[r.n] - set([i.label])

                        g.add(r.n)

                kills[i.label] = k
                gens[i.label] = g

        print(kills)
        print(gens)


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

if __name__=="__main__":
    test()
