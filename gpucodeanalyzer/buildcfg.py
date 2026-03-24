#!/usr/bin/env python3

from .isa.sass import SASSFile
from .generic_cfg import CFG

def main():
    import argparse
    from gpucodeanalyzer.isa.loader import get_dispatcher, get_metadata

    p = argparse.ArgumentParser(description="Construct a CFG generically")
    p.add_argument("code")
    p.add_argument("-m", dest="metadata", help="Metadata file")
    p.add_argument("-o", "--output", help="Output CFG as a dot file")
    p.add_argument("-c", "--count", action="store_true", help="Output counts")
    p.add_argument("--nc", "--no-code", dest="show_code", action="store_false", help="Do not output code")
    p.add_argument("--fn", help="Function to slice (if multiple)")

    args = p.parse_args()

    metadata = get_metadata(args.metadata)
    disp = get_dispatcher(args.code)
    code = disp.loader()(args.code, metadata=metadata)

    #code.dump()
    cfg = CFG(code, args.fn)
    cfg.build()
    #cfg.dump()
    if args.output:
        print(args.show_code)
        with open(args.output, "w") as f:
            cfg.dump_dot(f, code=args.show_code, count=args.count)

if __name__ == "__main__":
    main()
