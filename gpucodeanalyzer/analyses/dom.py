#!/usr/bin/env python3

from .dfa import DFA

class Dominators(DFA):
    def initialize(self, block):
        self.IN[block.name] = set()
        self.OUT[block.name] = set(self.cfg.names_to_blocks.keys())

    def xfer(self, block, flowfacts):
        return flowfacts.union(set([block.name]))

    def merge(self, predecessors):
        out = None

        for p in predecessors:
            if out is None:
                out = set(self.OUT[p])
            else:
                out = out.intersection(self.OUT[p])

        return out if out is not None else set()

    def compute_dominators(self):
        self.forward()

    def DOM(self, block, as_targets = False):
        dom = self.OUT[block.name]
        if as_targets:
            return set([self.cfg.names_to_blocks[d].target() for d in dom])
        else:
            return dom

def main():
    from gpucodeanalyzer.generic_cfg import CFG
    from gpucodeanalyzer.isa.loader import get_dispatcher
    import argparse

    p = argparse.ArgumentParser(description="Print dominators for each block")
    p.add_argument("asmfile")
    args = p.parse_args()

    disp = get_dispatcher(args.asmfile)
    code = disp.loader()(args.asmfile)

    cfg = CFG(code)
    cfg.build()

    dom = Dominators(cfg)
    dom.compute_dominators()
    for b in cfg.blocks:
        print(b.name, dom.DOM(b))
        print(b.target(), dom.DOM(b, as_targets=True))

if __name__ == "__main__":
    main()
