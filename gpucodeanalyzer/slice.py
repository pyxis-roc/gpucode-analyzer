from .generic_cfg import Register
from .def_use import DefUseAnalysis
from .skeletonizer import Skeletonizer
from .analyses.dom import Dominators

class Slicer(Skeletonizer):
    def slice(self, addresses):
        def _get_important_cdeps(block):
            rdf = self.dom.DF[block.name]
            out = set()
            for cdep in rdf:
                b = self.cfg.names_to_blocks[cdep]
                if len(b.code) and b.code[-1].is_control():
                    if b.code[-1].label not in self.important:
                        out.add(b.code[-1].label)

            return out

        self.dom = Dominators(self.cfg)
        self.dom.reverse()
        self.dom.compute_dominators()
        self.dom.compute_idom()
        self.dom.compute_dominance_frontiers()

        # TODO: unconditional?
        
        self.important = set(addresses)
        change = True
        while change:
            for b in self.cfg.blocks:
                for c in b.code:
                    if c.label in self.important:
                        addresses |= _get_important_cdeps(b)
                        break

            change = len(addresses) == 0
            self.important |= self._mark_important(addresses)
            addresses = set()

def main():
    from gpucodeanalyzer.generic_cfg import CFG
    from gpucodeanalyzer.isa.loader import get_dispatcher
    import argparse

    p = argparse.ArgumentParser(description="Classify instructions generically")
    p.add_argument("asmfile")
    p.add_argument("addresses", nargs="+")
    args = p.parse_args()

    disp = get_dispatcher(args.asmfile)
    code = disp.loader()(args.asmfile)
    classifier = disp.classifier()()

    cfg = CFG(code)
    cfg.build()

    sk = Slicer(cfg)
    sk.slice(set(args.addresses))

    sk_cfg = sk.get_skeleton_cfg()

    with open("slice.dot", "w") as f:
        sk_cfg.dump_dot(f)

if __name__ == "__main__":
    main()
