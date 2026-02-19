#!/usr/bin/env python3

import argparse
import sqlite3
import json
from process_rrv import TraceStorage
from collections import namedtuple

from gpucodeanalyzer.isa.sass import SASSFile, SASS2C
from gpucodeanalyzer.generic_cfg import CFG

import tempfile
import os

Instruction = namedtuple('Instruction', 'instruction_id  opcode insn op_idx kernel_id params')

def get_kernel_instruction_counts(db, kernel_id):
    kernel = db.get_kernel(kernel_id)
    if not kernel:
        return

    counts = {}
    for i in db.get_kernel_trace(kernel['kernel_id']):
        insn = Instruction(i['instruction_id'], i['opcode'],
                           i['insn'], i['op_idx'], i['kernel_id'],
                           json.loads(i['params']))

        key = (i['op_idx']*16, i['insn'])

        if key not in counts:
            counts[key] = 0

        counts[key] += 1

    print(kernel['name'])
    for k in sorted(counts.keys()):
        print("%04x %5d %s" % (k[0], counts[k], k[1]))

def main():
    p = argparse.ArgumentParser(description="Obtain instruction counts from a trace")
    p.add_argument("tracedb", help="Output of process_rrv")
    p.add_argument("kernels", nargs="*", type=int)
    p.add_argument("-d", dest="debug", action="store_true")

    args = p.parse_args()

    db = TraceStorage(args.tracedb)
    out = []
    debug = args.debug

    if len(args.kernels) == 0:
        for k in db.get_kernels():
            print(k['kernel_id'], k['name'])
    else:
        for k in args.kernels:
            get_kernel_instruction_counts(db, k)

if __name__ == "__main__":
    main()
