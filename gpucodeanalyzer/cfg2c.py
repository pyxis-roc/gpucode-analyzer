def main():
    from gpucodeanalyzer.isa.loader import get_dispatcher, get_metadata
    from gpucodeanalyzer.isa.sass import SASSFile, SASS2C
    from gpucodeanalyzer.generic_cfg import CFG
    from gpucodeanalyzer.skeletonizer import Skeletonizer

    import yaml
    import sys
    import argparse
    from pathlib import Path

    p = argparse.ArgumentParser(description="Convert SASS file to C after skeletonizing it")
    p.add_argument("asmfile", help="SASS file")
    p.add_argument("xlatinfo", help="Translation information, YAML", type=Path)
    p.add_argument("-f", "--fn", dest="func_name", help="Function name")
    p.add_argument("-m", dest="metadata", help="Metadata file")
    p.add_argument("output")

    args = p.parse_args()

    metadata = get_metadata(args.metadata)
    disp = get_dispatcher(args.asmfile)
    code = disp.loader()(args.asmfile, metadata=metadata)
    cfg = CFG(code, fn_name=args.func_name)
    cfg.build()

    sk = Skeletonizer(cfg)
    sk.build_skeleton()

    sk_cfg = sk.get_skeleton_cfg()

    if not args.xlatinfo.exists():
        xlatinfo = disp.converter().create_xlatinfo(code)
        with open(args.xlatinfo, "w") as f:
            f.write(yaml.dump(xlatinfo))

        print(f"INFO: Created {args.xlatinfo} with default arguments")

    with open(args.xlatinfo, "r") as f:
        xlatinfo = yaml.safe_load(f)

    with open(args.output, "w") as f:
        op = disp.converter()(f, xlatinfo)
        op.init_module()
        sk_cfg.convert(op, args.func_name)
        op.finish()

if __name__ == "__main__":
    main()
