from gpucodeanalyzer.generic_cfg import CFG, BasicBlock
from gpucodeanalyzer.analyses.dom import Dominators

class Loops:
    def __init__(self, cfg, dom = None):
        self.cfg = cfg
        self.dom = dom
        if self.dom is None:
            self.dom = Dominators(cfg)
            self.dom.compute_dominators()

    def find_backedges(self):
        be = []
        for b in self.cfg.blocks:
            bdom = self.dom.DOM(b)
            for nb in b.successors.values():
                if nb.name in bdom:
                    be.append((b, nb))

        return be

    def dfs(self, start, stop, reverse = False):
        visited = set()
        worklist = [start]

        while len(worklist):
            node = worklist.pop()
            if node.name in visited: continue
            visited.add(node.name)
            yield node

            if reverse:
                s = node.predecessors
            else:
                s = node.successors

            for n in s.values():
                if n is stop: continue
                if n.name in visited: continue
                worklist.append(n)

    def find_nat_loops(self):
        loops = {}
        be = self.find_backedges()
        for (src, dst) in be:
            loop_nodes = list(self.dfs(src, dst, True))
            loop_nodes.append(dst)
            if dst.name not in loops:
                loops[dst.name] = []

            loops[dst.name].append(loop_nodes)

        self.loops = loops

def main():
    from gpucodeanalyzer.isa.loader import get_dispatcher
    import argparse

    p = argparse.ArgumentParser(description="Construct natural loops")
    p.add_argument("asmfile")
    args = p.parse_args()

    disp = get_dispatcher(args.asmfile)
    code = disp.loader()(args.asmfile)

    cfg = CFG(code)
    cfg.build()

    li = Loops(cfg)
    li.find_nat_loops()

    for hdr in li.loops:
        print(hdr, li.loops[hdr])

if __name__ == "__main__":
    main()
