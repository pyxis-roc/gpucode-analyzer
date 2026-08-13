def main():
    from gpucodeanalyzer.isa.loader import get_dispatcher, get_metadata
    from gpucodeanalyzer.isa.sass import SASSFile, SASS2C
    from gpucodeanalyzer.generic_cfg import CFG
    from gpucodeanalyzer.skeletonizer import Skeletonizer
    from gpucodeanalyzer.slice import Slicer, get_labels

    import yaml
    import sys
    import argparse
    from pathlib import Path

    p = argparse.ArgumentParser(description="Convert SASS file to C after skeletonizing it")
    p.add_argument("asmfile", help="SASS file")
    p.add_argument("xlatinfo", help="Translation information, YAML", type=Path)
    p.add_argument("--path-info", action="store_true", help="Compute path information")
    p.add_argument("-f", "--fn", dest="func_name", help="Function name")
    p.add_argument("-m", dest="metadata", help="Metadata file")
    p.add_argument("-x", dest="addl_xdata", help="Additional metadata files to merge", action="append", default=[])
    p.add_argument("--sass-cbank", dest="sass_cbank", action="store_true")

    p.add_argument("--slice", dest="slice", help="Use slicer instead of skeletonizer, with argument being comma-separated addresses/re")

    p.add_argument("output")

    args = p.parse_args()

    metadata = get_metadata(args.metadata)
    disp = get_dispatcher(args.asmfile)
    code = disp.loader()(args.asmfile, metadata=metadata)
    cfg = CFG(code, fn_name=args.func_name)
    cfg.build()

    if args.slice:
        sk = Slicer(cfg)
        sk.slice(get_labels(cfg, args.slice.split(",")))
    else:
        sk = Skeletonizer(cfg)
        sk.build_skeleton()

    sk_cfg = sk.get_skeleton_cfg()

    if not args.xlatinfo.exists():
        xlatinfo_args = {}
        if disp.name == 'sass':
            xlatinfo_args['cbank'] = args.sass_cbank

        xlatinfo = disp.converter().create_xlatinfo(code, **xlatinfo_args)
        with open(args.xlatinfo, "w") as f:
            f.write(yaml.dump(xlatinfo))

        print(f"INFO: Created {args.xlatinfo} with default arguments")

    with open(args.xlatinfo, "r") as f:
        xlatinfo = yaml.safe_load(f)

    for xd in args.addl_xdata:
        with open(xd, "r") as f:
            addlxd = yaml.safe_load(f)

            for fn in addlxd:
                xlatinfo[fn].update(addlxd[fn])
                if 'addl_constant_map' in addlxd[fn]:
                    xlatinfo[fn]['constant_map'].update(addlxd[fn]['addl_constant_map'])

    config = set()
    if args.path_info:
        config.add('gen_path_info')

    if args.func_name is None:
        if metadata is not None:
            if len(metadata) == 1:
                args.func_name = list(metadata.keys())[0]
            else:
                print("ERROR: Multiple functions present, use -f to select one")
                for k in metadata:
                    print(k)

                sys.exit(1)

    with open(args.output, "w") as f:
        op = disp.converter()(f, xlatinfo, config=config)
        op.init_module()
        sk_cfg.convert(op, args.func_name)
        op.finish()

if __name__ == "__main__":
    main()
