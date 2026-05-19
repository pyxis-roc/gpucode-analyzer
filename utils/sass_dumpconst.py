#!/usr/bin/env python3

import argparse
import sqlite3
import json
from process_rrv import TraceStorage
from sass_trace2test import Instruction
import re
import array

C_RE = re.compile(r"c\[0x0\]\[0x(?P<addr>[A-Fa-f0-9]+)\]")

def convert_to_byte_array(const):
    out = {}
    max_addr = 0
    for k in const:
        m = C_RE.match(k)
        if m is None: continue

        addr = int(m.group('addr'), base=16)
        val = int(const[k], base=16)
        sz = (len(const[k])-2)//2

        #print(k, const[k], val, sz)
        out[addr] = (val, sz)
        max_addr = max(addr+sz, max_addr)

    cbank = bytearray(max_addr)
    for k, (v, sz) in out.items():
        cbank[k:k+sz] = v.to_bytes(sz, byteorder='little')

    return out, cbank

def cbank_to_c(values, cbank):
    out = []
    for k in range(0, len(cbank), 16):
        out.append(", ".join([f"{hex(c) if c != 0 else '0'}" for c in cbank[k:k+16]]))

    out = ",\n".join(out)
    return "{" + out + "}"

def main():
    p = argparse.ArgumentParser(description="Extract values from constant memory")
    p.add_argument("tracedb", help="Output of process_rrv")
    p.add_argument("kernel_id", type=int)
    p.add_argument("output", nargs='?', default='cbank0.h')

    args = p.parse_args()

    db = TraceStorage(args.tracedb)
    out = []

    kernel = db.get_kernel(args.kernel_id)
    print(kernel['name'], kernel['kernel_id'],
          kernel['grid_x'], kernel['grid_y'], kernel['grid_z'],
          kernel['blockdim_x'], kernel['blockdim_y'], kernel['blockdim_z'])

    const = {}
    for i in db.get_kernel_trace(args.kernel_id):
        params = json.loads(i['params'])
        cindices = []
        for pi, x in enumerate(params):
            if x[1].startswith('c['):
                cindices.append(pi)

        if len(cindices) == 0: continue

        insn = Instruction(i['instruction_id'], i['opcode'], i['insn'], i['op_idx'], i['kernel_id'], params)

        #print(insn, cindices)
        iargs = []
        for a in db.get_instruction_args(i['instruction_id']):
            iargs = json.loads(a['arguments'])
            for x in cindices:
                addr = params[x][1]
                if addr in const:
                    # same addr can be loaded as 64-bit or 32-bit, keep 64-bit
                    if const[addr] != iargs[x]:
                        v1 = iargs[x][2:]
                        v2 = const[addr][2:]

                        if v2.endswith(v1) or v1.endswith(v2):
                            const[addr] = "0x" + (v1 if len(v1) > len(v2) else v2)
                        else:
                            assert f"Constant mismatch {addr} {const[addr]} {args[x]}"
                else:
                    const[addr] = iargs[x]


    with open(args.output, 'w') as out:
        print("#pragma once", file=out)
        print(f"const uint8_t {kernel['name']}_{kernel['kernel_id']}_cbank0[] = ", cbank_to_c(*convert_to_byte_array(const)) + ';', file=out)
        print(f"const uint8_t * {kernel['name']}_cbank0 = {kernel['name']}_{kernel['kernel_id']}_cbank0;", file=out)

if __name__ == "__main__":
    main()
