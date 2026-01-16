#!/usr/bin/env python3

import re
from collections import namedtuple

BBCount = namedtuple('BBCount', 'function label count')
COUNT_RE = re.compile(r'^(?P<function>.*)_bbcount_(?P<label>.*) = (?P<count>\d+)$')

def raw_instruction_counts(cfg, fncounts, classifier):
    for b in cfg.blocks:
        tgt = b.target()
        if tgt not in fncounts:
            print(f"WARNING: Basic block {tgt} does not have counts")
        else:
            countinfo = fncounts[b.target()]
            print(" ")
            for i in b.code:
                cls = classifier.classify(i)
                if not isinstance(cls, list): cls = [cls]
                print(i.label, i.insn, "*", countinfo.count, "*", " ".join(cls))

def get_instruction_counts(cfg, fncounts, classifier):
    class_count = {}
    intensity = {}

    for b in cfg.blocks:
        tgt = b.target()
        if tgt not in fncounts:
            print(f"WARNING: Basic block {tgt} does not have counts")
        else:
            countinfo = fncounts[b.target()]
            for i in b.code:
                lcls = classifier.classify(i)
                if not isinstance(lcls, list):
                    lcls = [lcls]

                for cls in lcls:
                    if cls not in class_count:
                        class_count[cls] = 0

                    class_count[cls] += countinfo.count
                    ins = classifier.intensity(cls)
                    for k in ins:
                        intensity[k] = intensity.get(k, 0) + ins[k] * countinfo.count

                    if cls == "unknown":
                        print(i.label, i.insn, countinfo.count, cls)

    print(class_count)
    print(intensity)

def load_bbcount(countfile):
    out = {}
    with open(countfile, "r") as f:
        for l in f:
            m = COUNT_RE.match(l)
            if m is not None:
                o = BBCount(m.group('function'), m.group('label'), int(m.group('count')))
                if o.function not in out:
                    out[o.function] = {}

                out[o.function][o.label] = o

    return out

def main():
    from gpucodeanalyzer.isa.sass import SASSFile, SASS2C, SASSClassifier
    from gpucodeanalyzer.generic_cfg import CFG

    import yaml
    import sys
    import argparse

    p = argparse.ArgumentParser(description="Count instructions")
    p.add_argument("sassfile", help="SASS file, usually a single module only.")
    p.add_argument("bbcount", help="Output of a basic-block counter")
    p.add_argument("--raw", action="store_true", help="Output raw counts")

    args = p.parse_args()

    code = SASSFile(args.sassfile)
    cfg = CFG(code)
    cfg.build()

    counts = load_bbcount(args.bbcount)
    clsfy = SASSClassifier()

    if len(counts) > 1:
        raise NotImplementedError("Do not support multiple functions in CFG")

    for fn in counts:
        if args.raw:
            raw_instruction_counts(cfg, counts[fn], clsfy)
        else:
            get_instruction_counts(cfg, counts[fn], clsfy)

if __name__ == "__main__":
    main()
