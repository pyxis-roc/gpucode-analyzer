class Skeletonizer:
    def __init__(self, cfg):
        self.cfg = cfg

    def build_skeleton(self):
        important = set()
        to_process = []

        for b in self.cfg.blocks:
            last_insn = b.code[-1]
            if last_insn.is_control():
                if last_insn.label not in important:
                    important.add(last_insn.label)
                    to_process.append(last_insn)


        for i in to_process:
            reads = set(i.reads())
            if i.predicate:
                reads.add(i.predicate[1:] if i.predicate[0] == "!" else i.predicate)
            print(reads)

        for b in self.cfg.blocks:
            for i in b.code:
                if i.label in important:
                    print(i)



#    sk = Skeletonizer(cfg)
#    sk.build_skeleton()

