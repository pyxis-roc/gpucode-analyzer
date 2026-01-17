#!/usr/bin/env python3

from gpucodeanalyzer.isa.loader import get_dispatcher
from gpucodeanalyzer.generic_cfg import CFG
from gpucodeanalyzer.def_use import DefUseAnalysis

class Graph:
    def __init__(self):
        self.nodes = {}
        self.parents = {}
        self.labels = {}

    def strip_self_cycles(self):
        for n in self.nodes:
            if n in self.nodes[n]:
                self.delete_edge(n, n)

    def delete_edge(self, src, dst):
        self.nodes[src].remove(dst)
        self.parents[dst].remove(src)

    def delete_node(self, node):
        # remove incoming edges
        for p in self.parents[node]:
            self.nodes[p].remove(node)

        # remove outgoing edges
        for c in self.nodes[node]:
            self.parents[c].remove(node)

        # remove node and metadata
        del self.nodes[node]
        del self.parents[node]
        if node in self.labels:
            del self.labels[node]

    def add_node(self, node, label):
        if node not in self.nodes:
            self.nodes[node] = set()

        if node not in self.parents:
            self.parents[node] = set()

        if node not in self.labels:
            if label is not None:
                self.labels[node] = label

    def add_edge(self, src, dst):
        if src not in self.nodes:
            self.add_node(src, None)

        if dst not in self.nodes:
            self.add_node(dst, None)

        self.nodes[src].add(dst)
        self.parents[dst].add(src)

    def draw_dot(self, outputfile):
        with open(outputfile, "w") as dotfile:
            print ("digraph {", file=dotfile)
            for n in self.nodes:
                label = self.labels.get(n, n)
                print(f'  "{n}" [label="{label}"];', file=dotfile)

                for c in self.nodes[n]:
                    print(f' "{n}" -> "{c}";', file=dotfile)

            print("}", file=dotfile)

    def copy(self):
        x = Graph()
        x.nodes = dict([(k, set(v)) for k, v in self.nodes.items()])
        x.parents = dict([(k, set(v)) for k, v in self.parents.items()])
        x.labels = dict(self.labels)
        return x

# assumes infinite dispatch width
def list_schedule(dag):
    work = dag.copy()
    out = []

    while len(work.nodes):
        ready = [n for n in work.nodes if len(work.parents[n]) == 0]
        assert len(ready) != 0, (work.nodes, work.parents)
        out.append([n for n in ready])
        for r in ready:
            work.delete_node(r)

    return out

def main():
    import argparse

    p = argparse.ArgumentParser(description="Build Dependence Graphs and analyze ILP")
    p.add_argument("asmfile")
    args = p.parse_args()

    disp = get_dispatcher(args.asmfile)
    code = disp.loader()(args.asmfile)

    cfg = CFG(code)
    cfg.build()
    da = DefUseAnalysis(cfg)
    da.build_definitions()
    da.reaching_defns()

    for b in cfg.blocks:
        dfg = Graph()
        for insn in b.code:
            label = insn.insn.split(' ')
            if label[0][0] in ('@', '!'):
                label = label[1]
            else:
                label = label[0]

            dfg.add_node(insn.label, f"{label}") # addr, opcode
            for r, src in da.rdefs[insn.label]:
                dfg.add_edge(src, insn.label)

        dfg.strip_self_cycles()

        # delete out of basic block sources by relying on the fact
        # that they aren't labeled.
        ext_nodes = [n for n in dfg.nodes if n not in dfg.labels]
        for en in ext_nodes:
            dfg.delete_node(en)

        # delete backward edges since those are loop-carried
        for n in dfg.nodes:
            nl = int(n, base=16)
            remove = [c for c in dfg.nodes[n] if int(c, base=16) < nl]
            for r in remove:
                #print("removing backward edge", n, r)
                dfg.delete_edge(n, r)

        dfg.draw_dot(b.target() + ".dot")
        schedule = list_schedule(dfg)
        print(schedule)


if __name__=="__main__":
    main()
