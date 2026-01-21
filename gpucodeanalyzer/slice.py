from .generic_cfg import Register
from .def_use import DefUseAnalysis
from .skeletonizer import Skeletonizer
from gpucodeanalyzer.isa.loader import get_dispatcher

class Slicer(Skeletonizer):
    def slice(self, addresses):
        self.important = self._mark_important(addresses)

def main():
    from gpucodeanalyzer.generic_cfg import CFG
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
