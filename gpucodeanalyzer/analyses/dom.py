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

    def compute_idom(self):
        self.IDOM = {}
        for b in self.cfg.blocks:
            bdom = self.DOM(b)
            max_ob = 0
            max_b = None

            for o in bdom:
                if o == b.name: continue
                ob = self.DOM(self.cfg.names_to_blocks[o])
                if len(ob) > max_ob:
                    max_ob = len(ob)
                    max_b = o

            self.IDOM[b.name] = max_b

    def compute_dominance_frontiers(self):
        self.DF = dict([(b.name, set()) for b in self.cfg.blocks])

        for b in self.cfg.blocks:
            is_join = len(b.predecessors) > 1
            if not is_join: continue

            for p in b.predecessors:
                while p != self.IDOM[b.name]:
                    self.DF[p].add(b.name)
                    p = self.IDOM[p]

    def DOM(self, block, as_targets = False):
        dom = self.OUT[block.name]
        if as_targets:
            return set([self.cfg.names_to_blocks[d].target() for d in dom])
        else:
            return dom

    def reverse(self):
        self.cfg = self.cfg.copy()
        self.cfg.reverse()
        self.reversed = True

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
    dom.reverse()
    dom.cfg.dump_dot(open('rev.dot', 'w'))
    dom.compute_dominators()
    for b in cfg.blocks:
        print(b.name, dom.DOM(b))
        print(b.target(), dom.DOM(b, as_targets=True))

    dom.compute_idom()
    dom.compute_dominance_frontiers()
    for d, df in dom.DF.items():
        print(dom.cfg.names_to_blocks[d].target(), [dom.cfg.names_to_blocks[dff].target() for dff in df])


if __name__ == "__main__":
    main()
