import itertools
from gpucodeanalyzer.generic_cfg import CFG, BasicBlock

class Region:
    def __init__(self, contents, name):
        self.contents = contents
        self.name = name
        self.pred = {}
        self.succ = {}

    def __str__(self):
        return f"Region({self.name})"
        #return f"Region({[str(x) if isinstance(x, Region) else x.name for x in self.contents]})"
    __repr__ = __str__

    def add_predecessor(self, region):
        self.pred[region.name] = region

    def add_successor(self, region):
        self.succ[region.name] = region

    def remove_successors(self, *succ):
        for s in succ:
            if s.name in self.succ:
                del self.succ[s.name]

    def remove_predecessors(self, *pred):
        for p in pred:
            if p.name in self.pred:
                del self.pred[p.name]

    def t1(self):
        if self.name in self.succ:
            self.remove_successors(self)
            self.remove_predecessors(self)
            return True

        return False

    def t2(self):
        if len(self.pred) == 1:
            if self.name in self.pred: return None # t1

            pred = self.pred[list(self.pred.keys())[0]]

            nr = Region([pred, self], pred.name + "+" + self.name)

            # nr's predecessors are all of pred predecessors
            # nr's successors are all of self's successors + pred successors

            for p in pred.pred.values():
                if p in (pred, self):
                    nr.add_predecessor(nr)
                else:
                    nr.add_predecessor(p)

            for s in itertools.chain(pred.succ.values(), self.succ.values()):
                if s in (pred, self):
                    nr.add_successor(nr)
                else:
                    nr.add_successor(s)

            return nr, (pred, self)

        return None

class Regions:
    def __init__(self, cfg):
        self.cfg = cfg

    def compute_regions(self):
        regions = dict([(b.name, Region([b], b.name)) for b in self.cfg.blocks])
        pointers = dict([(r, r) for r in regions])

        # construct a region graph
        for n, r in regions.items():
            for bb in r.contents:
                for _, s in bb.successors.items():
                    r.add_successor(regions[s.name])
                    regions[s.name].add_predecessor(r)

        #for r in regions.values():
        #    print(r.name, "succ", r.succ, "pred", r.pred)
        #print("==")

        changed = True
        while changed:
            changed = False
            for r in regions:
                changed = regions[r].t1() or changed # remove self loops

            toprocess = set(regions.keys())

            while len(toprocess):
                n = toprocess.pop()
                if n not in regions: continue

                t2res = regions[n].t2()
                if t2res is None: continue
                changed = True

                #print("T2", n, t2res)

                nr, remove = t2res
                regions[nr.name] = nr

                #print("\tnr pred", nr.pred)
                #print("\tnr succ", nr.succ)

                for p in nr.pred.values():
                    if p is not nr:
                        #print("\tremoving successor", remove, p.name)
                        p.remove_successors(*remove)
                        p.add_successor(nr)
                        #print("\t\t", p.name, p.succ)

                for s in nr.succ.values():
                    if s is not nr:
                        #print("\tremoving predecessor", remove, s.name)
                        s.remove_predecessors(*remove)
                        s.add_predecessor(nr)
                        #print("\t\t", s.name, s.pred)

                del regions[remove[0].name]
                del regions[remove[1].name]

            #print("****")
            #for r in regions:
            #    print(r, regions[r].succ, regions[r].pred)

            #print("====")

        self.regions = regions

    def walk_regions(self, root = None, depth = 0):
        if isinstance(root, BasicBlock):
            return

        if root is None:
            for r in self.regions:
                yield depth, self.regions[r]
                for x in self.regions[r].contents:
                    for y in self.walk_regions(x, depth + 1):
                        yield y
        else:
            yield depth, root
            for r in root.contents:
                for j in self.walk_regions(r, depth + 1):
                    yield j

def main():
    from gpucodeanalyzer.isa.loader import get_dispatcher
    import argparse

    p = argparse.ArgumentParser(description="Construct regions")
    p.add_argument("asmfile")
    args = p.parse_args()

    disp = get_dispatcher(args.asmfile)
    code = disp.loader()(args.asmfile)

    cfg = CFG(code)
    cfg.build()

    reg = Regions(cfg)
    reg.compute_regions()

    for d, y in reg.walk_regions():
        print("  "*d, y.name)

if __name__ == "__main__":
    main()

