from .generic_cfg import Register
from .def_use import DefUseAnalysis

class Skeletonizer:
    def __init__(self, cfg):
        self.cfg = cfg
        self.da = DefUseAnalysis(self.cfg)
        self.da.build_definitions()
        self.da.reaching_defns()

    def _mark_important(self, important):
        to_process = list(important)

        while len(to_process):
            new_to_process = []
            for il in to_process:
                rdefs = self.da.rdefs[il]
                for _, rdil in rdefs:
                    if rdil not in important:
                        new_to_process.append(rdil)
                        important.add(rdil)

            to_process = new_to_process

        return important

    def build_skeleton(self):
        important = set()

        for b in self.cfg.blocks:
            if len(b.code) == 0: continue
            last_insn = b.code[-1]
            if last_insn.is_control():
                if last_insn.label not in important:
                    important.add(last_insn.label)

        self.important = self._mark_important(important)

    def get_skeleton_cfg(self):
        ocfg = self.cfg.copy()
        for b in ocfg.blocks:
            b._target = b.target()
            b.code = [i for i in b.code if i.label in self.important]

        return ocfg


def main():
    from gpucodeanalyzer.isa.sass import SASSFile
    from gpucodeanalyzer.generic_cfg import CFG
    import argparse

    p = argparse.ArgumentParser(description="Process SASS file")
    p.add_argument("sassfile")
    args = p.parse_args()

    code = SASSFile(args.sassfile)
    cfg = CFG(code)
    cfg.build()

    sk = Skeletonizer(cfg)
    sk.build_skeleton()

    sk_cfg = sk.get_skeleton_cfg()

    with open("skel.dot", "w") as f:
        sk_cfg.dump_dot(f)
        #cfg.dump_dot(f, xinsn = lambda i: i.insn if i.label in sk.important else '')

if __name__ == "__main__":
    main()
