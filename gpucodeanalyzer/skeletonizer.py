from .generic_cfg import Register

class Skeletonizer:
    def __init__(self, cfg):
        self.cfg = cfg

    def build_skeleton(self):
        important = set()
        to_process = []

        for b in self.cfg.blocks:
            last_insn = b.code[-1]
            if last_insn.is_control():
                if last_insn.label not in important:
                    important.add(last_insn.label)
                    to_process.append(last_insn)

        while len(to_process):
            writers_of = set()
            for i in to_process:
                reads = set([r.n for r in i.reads() if isinstance(r, Register)])
                if i.predicate:
                    reads.add(i.predicate[1:] if i.predicate[0] == "!" else i.predicate)

                writers_of = writers_of.union(reads)

            to_process = []
            for b in self.cfg.blocks:
                for i in b.code:
                    for o in i.writes():
                        if isinstance(o, Register):
                            if o.n in writers_of and i.label not in important:
                                important.add(i.label)
                                to_process.append(i)
                                break

        #for b in self.cfg.blocks:
        #    for i in b.code:
        #        if i.label in important:
        #            print(i)
        #            pass
        self.important = important

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

    sk = Skeletonizer(cfg)
    sk.build_skeleton()

    with open("skel.dot", "w") as f:
        cfg.dump_dot(f, xinsn = lambda i: i.insn if i.label in sk.important else '')

if __name__ == "__main__":
    test()
