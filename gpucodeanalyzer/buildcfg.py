#!/usr/bin/env python3

from .isa.sass import SASSFile
from .generic_cfg import CFG

EXT= {'.sass': SASSFile}

def main():
    import argparse

    p = argparse.ArgumentParser(description="Construct a CFG generically")
    p.add_argument("code")
    p.add_argument("-o", "--output", help="Output CFG as a dot file")
    p.add_argument("-c", "--count", action="store_true", help="Output counts")
    p.add_argument("--nc", "--no-code", dest="show_code", action="store_false", help="Do not output code")

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
        print(args.show_code)
        with open(args.output, "w") as f:
            cfg.dump_dot(f, code=args.show_code, count=args.count)

if __name__ == "__main__":
    main()
