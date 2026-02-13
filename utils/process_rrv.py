#!/usr/bin/env python3

import argparse
import re
try:
    import compression.bz2 as bz2
except ImportError:
    import bz2

from gpucodeanalyzer.isa.sass import SASSInstruction, SASSControlInsn, SASSFile, SASSRegister

INSN_START = re.compile(r"^CTA (?P<ctax>\d+),(?P<ctay>\d+),(?P<ctaz>\d+) - warp (?P<warp>\d+) - (?P<op_idx>\d+) - (?P<insn>.*) ;:$")
KERNEL_START = re.compile(r"Kernel (?P<name>.*) - grid size (?P<gridx>\d+),(?P<gridy>\d+),(?P<gridz>\d+) - block size (?P<blockx>\d+),(?P<blocky>\d+),(?P<blockz>\d+) - nregs (?P<nregs>\d+) - shmem (?P<shmem>\d+) - cuda stream id (?P<stream>\d+)$")
VALUES_START = re.compile(r"\* (R|C|U|W)")
UREG_VALUE = re.compile(r"UReg(?P<reg>\d+): (?P<value>0x.+)$")
CONST_VALUE = re.compile(r"C(?P<size>\d+): (?P<value>0x.+)$")
REG_VALUE = re.compile(r"Reg(?P<reg>\d+)_T(?P<thread>\d+): (?P<value>0x[a-f0-9]+) ")
WIDTH_VALUE = re.compile(r"Width: (?P<value>\d+)$")

class KernelData:
    def __init__(self, kernel_match, kernel_idx):
        #self.kernel_match = kernel_match
        self.kernel = kernel_match.group('name')
        self.grid = (kernel_match.group('gridx'), kernel_match.group('gridy'), kernel_match.group('gridz'))
        self.blockdim = (kernel_match.group('blockx'), kernel_match.group('blocky'), kernel_match.group('blockz'))
        self.nregs = kernel_match.group('nregs')
        self.shmem = kernel_match.group('shmem')
        self.stream = kernel_match.group('stream')
        self.kernel_idx = kernel_idx

    def __str__(self):
        return f"Kernel #{self.kernel_idx} {self.kernel} - {self.grid} - {self.blockdim}"

    __repr__ = __str__

class InsnData:
    def __init__(self, insn_match, kernel_idx = None):
        self.cta = (insn_match.group('ctax'), insn_match.group('ctay'), insn_match.group('ctaz'))
        self.warp_id = int(insn_match.group('warp'))
        self.op_idx = int(insn_match.group('op_idx'))
        self.insn = insn_match.group('insn')
        self.regs = []
        self.uregs = []
        self.constant = None
        self.kernel_idx = kernel_idx

    def add_regs(self, regs):
        self.regs.append(regs)

    def add_ureg(self, ureg):
        self.uregs.append(ureg)

    def set_constant(self, sz, constant):
        self.constant_sz = sz
        self.constant = constant

    def set_width(self, width):
        self.width = width

    def __str__(self):
        return f"{self.op_idx} {self.insn}"

    __repr__ = __str__

class RawTrace:
    def __init__(self, trace):
        self.trace = trace

    def _parse_regs(self, l):
        out = []
        for m in  REG_VALUE.finditer(l):
            out.append((m.group('reg'), m.group('thread'), m.group('value')))

        return out

    def parse_raw(self):
        if self.trace.endswith('bz2'):
            f = bz2.open(self.trace, mode="rt", encoding='utf-8')
        else:
            f = open(self.trace, "r")

        insn_data = None
        kno = 0

        for l in f:
            m = INSN_START.match(l)
            if m:
                if insn_data is not None:
                    yield insn_data

                insn_data = InsnData(m)
            else:
                m = KERNEL_START.match(l)
                if m:
                    kernel = KernelData(m, kno)
                    kno += 1
                    yield kernel
                else:
                    m = VALUES_START.match(l)
                    if m:
                        ty = m.group(1)
                        if ty == 'U':
                            val = UREG_VALUE.match(l[2:])
                            assert insn_data is not None
                            insn_data.add_ureg((val.group('reg'), val.group('value')))
                        elif ty == 'C':
                            val = CONST_VALUE.match(l[2:])
                            assert insn_data is not None
                            insn_data.set_constant(val.group('size'), val.group('value'))
                        elif ty == 'R':
                            assert insn_data is not None
                            val = self._parse_regs(l[2:])
                            insn_data.add_regs(val)
                        elif ty == 'W':
                            assert insn_data is not None
                            val = WIDTH_VALUE.match(l[2:])
                            insn_data.set_width(int(val.group('value')))
                        else:
                            raise NotImplementedError
                    else:
                        if l.strip():
                            print("ERROR: Not matched", l)

        if insn_data:
            yield insn_data

    def parse_kernel_order(self):
        kernels = []
        delayed = []

        kernel_ndx = -1

        for l in self.parse_raw():
            if isinstance(l, InsnData):
                if l.cta == ('0', '0', '0') and l.warp_id == 0 and l.op_idx == 0:
                    assert len(delayed) == 0
                    kernel_ndx += 1
                    if kernel_ndx < len(kernels):
                        yield kernels[kernel_ndx]

                if kernel_ndx < len(kernels):
                    yield l
                else:
                    delayed.append(l)
            elif isinstance(l, KernelData):
                kernels.append(l)
                if len(delayed):
                    yield l
                    for insn in delayed:
                        yield insn

                    delayed = []
            else:
                raise NotImplemented(l)

        assert len(delayed) == 0

    def make_insn(self, insn_data):
        # TODO: have a nicer parser
        # currently based on _mkinsn
        pred, op, args = SASSInstruction.parse(insn_data.insn)

        if SASSFile.SASS_CONTROL_INSN.match(op):
            i = SASSControlInsn(insn_data.op_idx, pred, op, args, insn_data.insn)
        else:
            i = SASSInstruction(insn_data.op_idx, pred, op, args, insn_data.insn)

        return i

    def annotate_insn_regs(self, insn_data):
        insn = self.make_insn(insn_data)

        regs_written = len([r for r in insn.writes() if isinstance(r, SASSRegister) and r.is_regular()])

        reg_ptr = 0
        ureg_ptr = 0
        for o in insn.operands():
            if isinstance(o.operand, SASSRegister):
                r = o.operand
                if r.is_regular():
                    if r.is_uniform():
                        if o.access() == 'W' and regs_written < insn_data.width:
                           for r in o.operand.adjacent(insn_data.width):
                               print(o.access(), r.n, insn_data.uregs[ureg_ptr])
                               ureg_ptr += 1
                        else:
                            print(o.access(), o.operand.n, insn_data.uregs[ureg_ptr])
                            ureg_ptr += 1
                    else:
                        if o.access() == 'W' and regs_written < insn_data.width:
                           for r in o.operand.adjacent(insn_data.width):
                               print(o.access(), r.n, insn_data.regs[reg_ptr])
                               reg_ptr += 1
                        else:
                            print(o.access(), o.operand.n, insn_data.regs[reg_ptr])
                            reg_ptr += 1

        assert reg_ptr == len(insn_data.regs)
        assert ureg_ptr == len(insn_data.uregs)

def main():
    p = argparse.ArgumentParser(description="Parse a trace produced by NVBit tool record_reg_vals_thread")
    p.add_argument("tracefile")
    args = p.parse_args()

    t = RawTrace(args.tracefile)
    for l in t.parse_kernel_order():
        print(l)
        if isinstance(l, InsnData):
            #print(t.make_insn(l))
            t.annotate_insn_regs(l)

if __name__ == "__main__":
    main()


