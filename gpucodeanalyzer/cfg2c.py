from .generic_cfg import Register
from .def_use import DefUseAnalysis


def test():
    from gpucodeanalyzer.isa.sass import SASSFile, SASS2C
    from gpucodeanalyzer.generic_cfg import CFG
    from gpucodeanalyzer.skeletonizer import Skeletonizer

    import argparse

    p = argparse.ArgumentParser(description="Convert SASS file to C after skeletonizing it")
    p.add_argument("sassfile")
    p.add_argument("output")

    args = p.parse_args()

    code = SASSFile(args.sassfile)
    cfg = CFG(code)
    cfg.build()

    sk = Skeletonizer(cfg)
    sk.build_skeleton()

    sk_cfg = sk.get_skeleton_cfg()

    with open(args.output, "w") as f:
        op = SASS2C(f)
        sk_cfg.convert(op)
        op.finish()

if __name__ == "__main__":
    test()
