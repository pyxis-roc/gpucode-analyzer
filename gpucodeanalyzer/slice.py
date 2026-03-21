from .generic_cfg import Register
from .def_use import DefUseAnalysis
from .skeletonizer import Skeletonizer
from .analyses.dom import Dominators
import re
import json

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

    if len(labels) == 0:
        print("WARNING: no labels matched. Slice will be empty.")

    return labels

def main():
    from gpucodeanalyzer.generic_cfg import CFG
    from gpucodeanalyzer.isa.loader import get_dispatcher
    import argparse

    p = argparse.ArgumentParser(description="Slice a CFG")
    p.add_argument("asmfile")
    p.add_argument("-m", dest="metadata", help="Metadata file")
    p.add_argument("-o", dest="outputdot", help="Output skeleton in DOT format", default="slice.dot")
    p.add_argument("-c", dest="outputcode", help="Output skeleton as text format")

    p.add_argument("--fn", help="Function to slice (if multiple)")
    p.add_argument("labels_or_re", nargs="+", help="Instruction labels or regular expressions")


    args = p.parse_args()

    if args.metadata:
        with open(args.metadata, "r") as f:
            metadata = json.load(f)
    else:
        metadata = None

    disp = get_dispatcher(args.asmfile)
    code = disp.loader()(args.asmfile, metadata=metadata)
    classifier = disp.classifier()()

    cfg = CFG(code, args.fn)
    cfg.build()

    sk = Slicer(cfg)
    sk.slice(get_labels(cfg, args.labels_or_re))

    sk_cfg = sk.get_skeleton_cfg()

    with open(args.outputdot, "w") as f:
        sk_cfg.dump_dot(f)
        print(f"Written output to {args.outputdot}")

    if args.outputcode:
        with open(args.outputcode, "w") as f:
            sk_cfg.dump_code(f)
            print(f"Written code to {args.outputcode}")

if __name__ == "__main__":
    main()
