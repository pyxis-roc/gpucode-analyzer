#!/usr/bin/env python3

from .isa.sass import SASSFile
from .generic_cfg import CFG

EXT= {'.sass': SASSFile}

def main():
    import argparse

    p = argparse.ArgumentParser(description="Construct a CFG generically")
    p.add_argument("code")
    p.add_argument("-o", "--output", help="Output CFG as a dot file")

    args = p.parse_args()

    if args.code.endswith(".sass"):
        code = EXT[".sass"](args.code)
    else:
        print("Unrecognized extension")

    #code.dump()
    cfg = CFG(code)
    cfg.build()
    #cfg.dump()
    if args.output:
        with open(args.output, "w") as f:
            cfg.dump_dot(f)

if __name__ == "__main__":
    main()
