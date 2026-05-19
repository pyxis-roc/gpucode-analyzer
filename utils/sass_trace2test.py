#!/usr/bin/env python3

import argparse
import sqlite3
import json
from process_rrv import TraceStorage
from collections import namedtuple

from gpucodeanalyzer.isa.sass import SASSFile, SASS2C, InsnHook
from gpucodeanalyzer.generic_cfg import CFG

import tempfile
import os

Instruction = namedtuple('Instruction', 'instruction_id  opcode insn op_idx kernel_id params')

class TestInsnHook(InsnHook):
    name = "TestInsnHook"

    def __init__(self, gen, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.gen = gen

    def pre_hook(self, insn, output, translated):
        if not translated: return

        i, a = self.gen.insns[self.gen._insn_count]

        for (m, r), a in zip(i.params, a):
            if m in ('R', 'RW'):
                if (r[0] == 'R' or r[0] == 'U' or r[0] == 'P'):
                    if r != 'RZ' and r!= 'URZ' and r != 'UPT' and r != 'PT':
                        output.write(f"{r} = {a};\n")
                elif (r[0] == 'c'):
                    #TODO: c32 or c64.
                    output.write(f"c32 = {a};\n")

    def post_hook(self, insn, output, translated):
        self.gen._insn_count += 1
        if not translated: return

        i, a = self.gen.insns[self.gen._insn_count-1]

        for (m, r), a in zip(i.params, a):
            if m == 'W' and (r[0] == 'R' or r[0] == 'U'):
                output.write(f"assert({r} == {a});\n")

class TestcaseGenerator:
    def __init__(self, insn_args, output_file, debug = False):
        self.insn_args = insn_args
        self.output_file = output_file
        self.debug = debug
        self.hook = TestInsnHook(self)

    def generate(self):
        self.insns = []
        out = []
        for i, a in self.insn_args:
            out.extend([f'/*{(i.op_idx+ndx)*16:04x}*/ {i.insn} ; /* 0x0000000000000000 */' for ndx in range(len(a))])
            assert len(a)
            for aa in a:
                self.insns.append((i, aa))

        if len(out) == 0:
            print("ERROR: No instructions matched. No output generated.")
            return False

        sassfile = None
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sass') as f:
            sassfile = f.name
            print("\n".join(out), file=f)
            print("/*ffff*/ EXIT ; \n", file=f);
            #self.insns.append(None)

        self._generate_c(sassfile, self.output_file)
        if self.debug:
            print(sassfile)
        else:
            os.unlink(sassfile)
        return True


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
            op = SASS2C(f, xlatinfo, hooks=[self.hook])
            op.init_module()
            cfg.convert(op, func_name)
            op.finish()

def main():
    p = argparse.ArgumentParser(description="Generate test cases from a recorded trace")
    p.add_argument("tracedb", help="Output of process_rrv")
    p.add_argument("instruction")
    p.add_argument("output")
    p.add_argument("--oi", dest="op_idx", type=int)
    p.add_argument("--opc", dest="op_pc", type=lambda x: int(x, base=16))
    p.add_argument("--ki", dest="kernel_id", type=int)
    p.add_argument("-d", dest="debug", action="store_true")

    args = p.parse_args()

    db = TraceStorage(args.tracedb)
    out = []
    output_file = args.output
    debug = args.debug

    op_idx = args.op_idx or (args.op_pc // 16 if args.op_pc else None)

    for i in db.get_instructions_by_opcode(args.instruction, op_idx = op_idx, kernel_id = args.kernel_id):
        insn = Instruction(i['instruction_id'], i['opcode'], i['insn'], i['op_idx'], i['kernel_id'], json.loads(i['params']))

        insn_args = []
        for a in db.get_instruction_args(i['instruction_id']):
            insn_args.append(json.loads(a['arguments']))

        out.append((insn, insn_args))

    tgc = TestcaseGenerator(out, output_file, debug=debug)
    tgc.generate()

if __name__ == "__main__":
    main()
