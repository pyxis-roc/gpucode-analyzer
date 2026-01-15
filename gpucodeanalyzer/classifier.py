#!/usr/bin/env python3

from gpucodeanalyzer.isa.loader import get_dispatcher

def main():
    from gpucodeanalyzer.isa.sass import SASSFile
    from gpucodeanalyzer.generic_cfg import CFG
    import argparse

    p = argparse.ArgumentParser(description="Classify instructions generically")
    p.add_argument("asmfile")
    args = p.parse_args()

    disp = get_dispatcher(args.asmfile)
    code = disp.loader()(args.asmfile)
    classifier = disp.classifier()()

    cfg = CFG(code)
    cfg.build()

    class_count = {}

    for b in cfg.blocks:
        for i in b.code:
            lcls = classifier.classify(i)
            if not isinstance(lcls, list):
                lcls = [lcls]

            print(i.label, i.insn, "*", " ".join(lcls))

            for cls in lcls:
                if cls not in class_count:
                    class_count[cls] = 0

                class_count[cls] += 1


    print("===")
    kv = sorted(class_count.items(), key=lambda x: x[1], reverse=True)
    for k, v in kv:
        print(k, v)

if __name__ == "__main__":
    main()
