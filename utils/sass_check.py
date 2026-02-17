#!/usr/bin/env python3

import argparse
import sqlite3
import json
from process_rrv import TraceStorage
from sass_trace2test import Instruction

def main():
    p = argparse.ArgumentParser(description="Compare a recorded trace to debug output from the translated version")
    p.add_argument("tracedb", help="Output of process_rrv")
    p.add_argument("debug_output", help="Of a single thread, usually 0,0,0")
    p.add_argument("kernel_id", type=int)

    args = p.parse_args()

    db = TraceStorage(args.tracedb)
    out = []

    debug = open(args.debug_output, "r")
    l = iter(debug)
    dt = next(l)

    kernel = db.get_kernel(args.kernel_id)
    print(kernel['name'], kernel['kernel_id'],
          kernel['grid_x'], kernel['grid_y'], kernel['grid_z'],
          kernel['blockdim_x'], kernel['blockdim_y'], kernel['blockdim_z'])

    for i in db.get_kernel_trace(args.kernel_id):
        insn = Instruction(i['instruction_id'], i['opcode'], i['insn'], i['op_idx'], i['kernel_id'], json.loads(i['params']))

        args = []
        for a in db.get_instruction_args(i['instruction_id']):
            args.append(json.loads(a['arguments']))
            break

        dtpc = int(dt.split()[0], base=16)
        if dtpc // 16 == insn.op_idx:
            print(insn, args, dt)
            dt = next(l)


if __name__ == "__main__":
    main()
