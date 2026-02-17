#!/usr/bin/env python3

import argparse
import sqlite3
import json
from process_rrv import TraceStorage
from collections import namedtuple

from gpucodeanalyzer.isa.sass import SASSFile, SASS2C
from gpucodeanalyzer.generic_cfg import CFG

import tempfile

Instruction = namedtuple('Instruction', 'instruction_id  opcode insn op_idx kernel_id params')

class TestcaseGenerator:
    def __init__(self, insn_args):
        self.insn_args = insn_args

    def generate(self):
        self.insns = []
        out = []
        for i, a in self.insn_args:
            out.extend([f'/*{(i.op_idx+ndx)*16:04x}*/ {i.insn} ; /* 0x0000000000000000 */' for ndx in range(len(a))])
            assert len(a)
            for aa in a:
                self.insns.append((i, aa))

        sassfile = None
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sass') as f:
            sassfile = f.name
            print("\n".join(out), file=f)
            print("/*ffff*/ EXIT ; \n", file=f);
            #self.insns.append(None)

        self._generate_c(sassfile, 'x.c')

    def pre_hook(self, insn, output, translated):
        if not translated: return

        i, a = self.insns[self._insn_count]

        for (m, r), a in zip(i.params, a):
            if m == 'R' and (r[0] == 'R' or r[0] == 'U'):
                if r != 'RZ' and r!= 'URZ' and r != 'UPT':
                    output.write(f"{r} = {a};\n")

    def post_hook(self, insn, output, translated):
        self._insn_count += 1
        if not translated: return

        i, a = self.insns[self._insn_count-1]

        for (m, r), a in zip(i.params, a):
            if m == 'W' and (r[0] == 'R' or r[0] == 'U'):
                output.write(f"assert({r} == {a});\n")

    def _generate_c(self, sassfile, output):
        code = SASSFile(sassfile)
        cfg = CFG(code)
        cfg.build()
        for b in cfg.blocks:
            if b.target() not in ('_start', '_exit'):
                b._target = b.target()

        xlatinfo = {'test_kernel':
                    {'args': {},
                     'grid_dim': [1,1,1],
                     'block_dim': [1,1,1]}}

        func_name = 'test_kernel'

        self._insn_count = 0
        with open(output, "w") as f:
            op = SASS2C(f, xlatinfo, pre_insn_hook = self.pre_hook,
                        post_insn_hook = self.post_hook)
            op.init_module()
            cfg.convert(op, func_name)
            op.finish()

def main():
    p = argparse.ArgumentParser(description="Generate test cases from a recorded trace")
    p.add_argument("tracedb", help="Output of process_rrv")
    p.add_argument("instruction")
    p.add_argument("--oi", dest="op_idx", type=int)
    p.add_argument("--opc", dest="op_pc", type=lambda x: int(x, base=16))
    p.add_argument("--ki", dest="kernel_id", type=int)

    args = p.parse_args()

    db = TraceStorage(args.tracedb)
    out = []

    op_idx = args.op_idx or (args.op_pc // 16 if args.op_pc else None)

    for i in db.get_instructions_by_opcode(args.instruction, op_idx = op_idx, kernel_id = args.kernel_id):
        insn = Instruction(i['instruction_id'], i['opcode'], i['insn'], i['op_idx'], i['kernel_id'], json.loads(i['params']))

        args = []
        for a in db.get_instruction_args(i['instruction_id']):
            args.append(json.loads(a['arguments']))

        out.append((insn, args))

    tgc = TestcaseGenerator(out)
    tgc.generate()

if __name__ == "__main__":
    main()
