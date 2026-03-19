from .generic_cfg import Register
from .def_use import DefUseAnalysis
from .skeletonizer import Skeletonizer
from .analyses.dom import Dominators
import re

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
                        new_addr = _get_important_cdeps(b)
                        addresses |= new_addr

            change = not (len(addresses) == 0)
            self.important |= self._mark_important(addresses)
            addresses = set()

def get_labels(cfg, labels_or_re):
    res = []
    labels = set()
    for lr in labels_or_re:
        if lr.startswith("re:"):
            rexp = re.compile(lr[3:])
            res.append(rexp)
        else:
            labels.add(lr)

    for i in cfg.all_instructions():
        if i.label in labels: continue
        if any(r.match(i.opcode) for r in res):
            labels.add(i.label)

    return labels

def main():
    from gpucodeanalyzer.generic_cfg import CFG
    from gpucodeanalyzer.isa.loader import get_dispatcher
    import argparse

    p = argparse.ArgumentParser(description="Classify instructions generically")
    p.add_argument("asmfile")
    p.add_argument("-o", dest="outputdot", help="Output skeleton in DOT format", default="slice.dot")
    p.add_argument("labels_or_re", nargs="+", help="Instruction labels or regular expressions")


    args = p.parse_args()

    disp = get_dispatcher(args.asmfile)
    code = disp.loader()(args.asmfile)
    classifier = disp.classifier()()

    cfg = CFG(code)
    cfg.build()

    sk = Slicer(cfg)
    sk.slice(get_labels(cfg, args.labels_or_re))

    sk_cfg = sk.get_skeleton_cfg()

    with open(args.outputdot, "w") as f:
        sk_cfg.dump_dot(f)
        print(f"Written output to {args.outputdot}")

if __name__ == "__main__":
    main()
