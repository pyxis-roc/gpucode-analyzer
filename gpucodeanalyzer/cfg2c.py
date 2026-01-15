from .generic_cfg import Register
from .def_use import DefUseAnalysis

def test():
    from gpucodeanalyzer.isa.sass import SASSFile, SASS2C
    from gpucodeanalyzer.generic_cfg import CFG
    from gpucodeanalyzer.skeletonizer import Skeletonizer

    import yaml
    import sys
    import argparse

    p = argparse.ArgumentParser(description="Convert SASS file to C after skeletonizing it")
    p.add_argument("sassfile", help="SASS file, usually a single module only.")
    p.add_argument("xlatinfo", help="Translation information, YAML")
    p.add_argument("-f", dest="func_name", help="Function name")
    p.add_argument("output")

    args = p.parse_args()

    code = SASSFile(args.sassfile)
    cfg = CFG(code)
    cfg.build()

    sk = Skeletonizer(cfg)
    sk.build_skeleton()

    sk_cfg = sk.get_skeleton_cfg()

    with open(args.xlatinfo, "r") as f:
        xlatinfo = yaml.safe_load(f)

    if args.func_name is None:
        if xlatinfo is not None and len(xlatinfo) == 1:
            args.func_name = list(xlatinfo.keys())[0]
        else:
            print("ERROR: You need to specify a function to translate using -f") # for now
            sys.exit(1)


    with open(args.output, "w") as f:
        op = SASS2C(f, xlatinfo)
        op.init_module()
        sk_cfg.convert(op, args.func_name)
        op.finish()

if __name__ == "__main__":
    test()
