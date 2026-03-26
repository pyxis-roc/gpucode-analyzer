#!/usr/bin/env python3

from .generic_cfg import CFG
from .analyses.dom import Dominators
from .analyses.region import Regions
from .analyses.loops import Loops
import json

def build_cfginfo(cfg):
    out = {}

    for b in cfg.blocks:
        successors = [(k, s.target()) for k, s in b.successors.items()]
        predecessors = [p.target() for _, p in b.predecessors.items()]

        out[b.target()] = {'succ': successors, 'pred': predecessors,
                           'name': b.name}

    return out

def build_dominfo(cfg, reverse = False):
    dom = Dominators(cfg)
    if reverse: dom.reverse()
    dom.compute_dominators()

    dominfo = {}
    for b in cfg.blocks:
        dominfo[b.target()] = list(dom.DOM(b, as_targets=True))

    dom.compute_idom()
    idom = {}
    for b in cfg.blocks:
        idom[b.target()] = cfg.names_to_blocks[dom.IDOM[b.name]].target() if dom.IDOM[b.name] else None

    dom.compute_dominance_frontiers()
    dfinfo = {}
    for b in cfg.blocks:
        dfinfo[b.target()] = list([cfg.names_to_blocks[x].target() for x in dom.DF[b.name]])

    return {f'{"r" if reverse else ""}dom': dominfo, f'{"r" if reverse else ""}idom': idom, f'{"r" if reverse else ""}df': dfinfo}

def build_regioninfo(cfg):
    region = Regions(cfg)
    region.compute_regions()

    return {"reducible": len(region.regions) == 1}

def build_loopinfo(cfg):
    li = Loops(cfg)
    li.find_nat_loops()

    out = {}
    for hdr in li.loops:
        out[cfg.names_to_blocks[hdr].target()] = [[x.target() for x in l] for l in li.loops[hdr]]

    return {'loopinfo': out}


def main():
    import argparse
    from gpucodeanalyzer.isa.loader import get_dispatcher, get_metadata

    p = argparse.ArgumentParser(description="Construct a CFG generically")
    p.add_argument("code")
    p.add_argument("-m", dest="metadata", help="Metadata file")
    p.add_argument("-o", "--output", help="Output CFG as a dot file")
    p.add_argument("--fn", help="Functions to analyze (all if not specified)", action="append")

    args = p.parse_args()

    metadata = get_metadata(args.metadata)
    disp = get_dispatcher(args.code)
    code = disp.loader()(args.code, metadata=metadata)

    functions = args.fn or list(code.codes.keys())

    out = {}
    for fn in functions:
        cfg = CFG(code, args.fn)
        cfg.build()
        out[fn] = {}

        out[fn]['cfg'] = build_cfginfo(cfg)
        out[fn].update(build_dominfo(cfg))
        out[fn].update(build_dominfo(cfg, reverse=True))
        out[fn].update(build_regioninfo(cfg))
        out[fn].update(build_loopinfo(cfg))

    print(json.dumps(out, indent='  '))

if __name__ == "__main__":
    main()
