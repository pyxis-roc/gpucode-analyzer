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

if __name__=="__main__":
    test()
