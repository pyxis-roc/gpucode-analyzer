#!/usr/bin/env python3

import argparse
import itertools
import re
import json
import sqlite3

try:
    import compression.bz2 as bz2
except ImportError:
    import bz2

from gpucodeanalyzer.isa.sass import SASSInstruction, SASSControlInsn, SASSFile, SASSRegister, PR_NUM

INSN_START = re.compile(r"^CTA (?P<ctax>\d+),(?P<ctay>\d+),(?P<ctaz>\d+) - warp (?P<warp>\d+) - (?P<op_idx>\d+) - (?P<insn>.*) ;:$")
KERNEL_START = re.compile(r"Kernel (?P<name>.*) - grid size (?P<gridx>\d+),(?P<gridy>\d+),(?P<gridz>\d+) - block size (?P<blockx>\d+),(?P<blocky>\d+),(?P<blockz>\d+) - nregs (?P<nregs>\d+) - shmem (?P<shmem>\d+) - cuda stream id (?P<stream>\d+)( - ipoint_pre (?P<ipoint_pre>\d+))?$")
VALUES_START = re.compile(r"\* (R|C|UP|W|U|P)")
UREG_VALUE = re.compile(r"UReg(?P<reg>\d+): (?P<value>0x.+)$")
CONST_VALUE = re.compile(r"C(?P<size>\d+): (?P<value>0x.+)$")
REG_VALUE = re.compile(r"Reg(?P<reg>\d+)_T(?P<thread>\d+): (?P<value>0x[a-f0-9]+) ")
PRED_VALUE = re.compile(r"Pred: (?P<mask>0x[a-f0-9]+) (?P<value>0x[a-f0-9]+)")
UPRED_VALUE = re.compile(r"UPred: (?P<mask>0x[a-f0-9]+) (?P<value>0x[a-f0-9]+)")
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
        self.pred = None
        self.upred = None
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

    def set_upred(self, mask, value):
        self.upred = (mask, value)

    def get_upred(self, regnum):
        assert (self.upred[0] & (1 << regnum)) != 0
        return (self.upred[1] >> regnum) & 1

    def get_pred(self, regnum):
        if regnum == PR_NUM:
            return self.pred[1]

        assert (self.pred[0] & (1 << regnum)) != 0
        return (self.pred[1] >> regnum) & 1

    def set_pred(self, mask, value):
        self.pred = (mask, value)

    def __str__(self):
        return f"{self.op_idx} {self.insn}"

    __repr__ = __str__

class RawTrace:
    def __init__(self, trace, state_tracking = True):
        self.trace = trace
        self.state_tracking = state_tracking
        self._anno_cache = {}

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
                        assert insn_data is not None

                        if ty == 'UP':
                            val = UPRED_VALUE.match(l[2:])
                            insn_data.set_upred(int(val.group('mask'), base=16), int(val.group('value'), base=16))
                        elif ty == 'P':
                            val = PRED_VALUE.match(l[2:])
                            insn_data.set_pred(int(val.group('mask'), base=16),
                                               int(val.group('value'), base=16))
                        elif ty == 'U':
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
        if insn_data.insn in self._anno_cache:
            out = self._anno_cache[insn_data.insn]
        else:
            insn = self.make_insn(insn_data)

            # always regular only
            regs_written = len([r for r in insn.writes() if isinstance(r, SASSRegister) and r.is_regular()])

            out = []
            reg_ptr = 0
            ureg_ptr = 0
            for o in insn.operands():
                if isinstance(o.operand, SASSRegister):
                    r = o.operand
                    if r.is_regular():
                        if r.is_uniform():
                            out.append((o.access(), r,
                                        (lambda idx: lambda x: x.uregs[idx])(ureg_ptr)
                                        ))
                            ureg_ptr += 1

                            if o.access() == 'W' and regs_written < insn_data.width:
                               for r in o.operand.adjacent(insn_data.width-1):
                                   out.append((o.access(), r,
                                               (lambda idx: lambda x: x.uregs[idx])(ureg_ptr)
                                               ))
                                   ureg_ptr += 1
                        else:
                            out.append((o.access(), r,
                                        (lambda idx: lambda x: x.regs[idx])(reg_ptr)))
                            reg_ptr += 1

                            if o.access() == 'W' and regs_written < insn_data.width:
                               for r in o.operand.adjacent(insn_data.width-1):
                                   out.append((o.access(), r,
                                               (lambda idx: lambda x: x.regs[idx])(reg_ptr)
                                               ))
                                   reg_ptr += 1
                    elif r.is_predicate():
                        if r.is_uniform():
                            out.append((o.access(), r,
                                        (lambda num: lambda x: x.get_upred(num))(r.number())
                                        ))
                        else:
                            out.append((o.access(), r,
                                        (lambda num: lambda x: x.get_pred(num))(r.number())
                                        ))
                elif isinstance(o.operand, str):
                    if (o.operand.startswith('c') or o.operand.startswith('-c')):
                        if insn_data.constant is not None:
                            out.append((o.access(), o.operand, lambda x: x.constant))
                    else:
                        if not o.operand.startswith('['):
                            out.append((o.access(), o.operand, (lambda val: lambda x: val)(o.operand)))


            assert reg_ptr == len(insn_data.regs), insn_data.insn
            assert ureg_ptr == len(insn_data.uregs), insn_data.insn
            self._anno_cache[insn_data.insn] = out

        for o in out:
            yield (o[0], o[1], o[2](insn_data))

    def parse_io(self):
        def get_reg_or_str(op):
            if isinstance(op, SASSRegister):
                return op.n
            elif isinstance(op, str):
                return op
            else:
                raise NotImplementedError(op)

        state = {'RZ': 0}
        writer = {}
        for l in self.parse_kernel_order():
            yield l
            if isinstance(l, KernelData):
                state = {'RZ': 0, 'URZ': 0, 'PT': 1, 'UPT': 1}

            if isinstance(l, InsnData):
                writes = []
                for access, op, vals in self.annotate_insn_regs(l):
                    if access == 'W':
                        writes.append((access, op, vals))
                        continue
                    else:
                        if self.state_tracking and isinstance(op, SASSRegister):
                            if op.n != 'PR':
                                if op.n not in state:
                                    print(f"{op.n} not written to before reading for {l}")
                                    print(state)
                                    print(sorted([(k, v) for k, v in writer.items()]))
                                    vals = f"?uninit-{op.n}"
                                else:
                                    vals = state.get(op.n)

                    yield (access, get_reg_or_str(op), vals)

                for access, op, vals in writes:
                    yield (access, get_reg_or_str(op), vals)
                    if isinstance(op, SASSRegister) and not op.is_constant():
                        state[op.n] = vals
                        writer[op.n] = l.op_idx

                        # TODO
                        if l.insn.startswith("CS2R") and l.insn.endswith("SRZ"):
                            adj = op.adjacent(1)[0]
                            state[adj.n] = 0
                            writer[adj.n] = l.op_idx

def get_observations(trace):
    def process_insn_data_args(data):
        if len(data) <= 1: return
        insn = data[0]
        maxargs = max(len(x[2]) if isinstance(x[2], list) else 1 for x in data[1:])

        out = []
        params = []
        for args in data[1:]:
            val = args[2]

            if isinstance(val, list):
                if len(val[0]) == 3:
                    val = [x[2] for x in val]
            elif isinstance(val, (int, str)):
                val = [val] * maxargs
            elif isinstance(val, tuple) and len(val) == 2:
                val = [val[1]] * maxargs # Ureg

            out.append(val)
            params.append((args[0], args[1]))

        insn2 = trace.make_insn(insn)
        tests = {
            'insn': insn.insn,
            'opcode': insn2.opcode,
            'op_idx': insn.op_idx,
            'params': [list(p) for p in params],
            'args': []
        }

        #print(insn, maxargs)
        #print(params)
        argset = set()
        for args in zip(*out):
            argset.add(args)

        for args in argset:
            tests['args'].append(list(args))

        return tests


    prev_insn_data = []
    for l in trace.parse_io():
        if isinstance(l, KernelData):
            if len(prev_insn_data):
                yield process_insn_data_args(prev_insn_data)
                prev_insn_data = []

            yield l
        elif isinstance(l, InsnData):
            if len(prev_insn_data):
                yield process_insn_data_args(prev_insn_data)
            prev_insn_data = []
            prev_insn_data.append(l)
        else:
            prev_insn_data.append(l)

class TraceStorage:
    def __init__(self, dbname):
        self.dbname = dbname
        self.conn = sqlite3.connect(self.dbname)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        cur = self.conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS  Kernels (kernel_id INT PRIMARY KEY, name TEXT NOT NULL, grid_x INT, grid_y INT, grid_z INT, blockdim_x INT, blockdim_y INT, blockdim_z INT, nregs INT, shmem INT, stream INT);")
        cur.execute("CREATE TABLE IF NOT EXISTS Instructions  (instruction_id INTEGER PRIMARY KEY, opcode TEXT NOT NULL, insn TEXT NOT NULL, op_idx INT NOT NULL, cta_x INT, cta_y INT, cta_z INT, warp_id INT, params TEXT, kernel_id NOT NULL, FOREIGN KEY(kernel_id) REFERENCES kernels(kernel_id));")
        cur.execute("CREATE TABLE IF NOT EXISTS Arguments  (instruction_id INT, arguments TEXT,  FOREIGN KEY(instruction_id) REFERENCES Instructions(instruction_id));")
        cur.execute("CREATE INDEX IF NOT EXISTS OpcodeIndex ON Instructions(Opcode);")
        cur.execute("CREATE INDEX IF NOT EXISTS InsnIndex ON Instructions(Insn);")
        cur.execute("CREATE INDEX IF NOT EXISTS ArgIndex ON Arguments(instruction_id);")

    def insert_kernel(self, kernel_data):
        cur = self.conn.cursor()
        cur.execute('INSERT INTO Kernels (kernel_id, name, grid_x, grid_y, grid_z, blockdim_x, blockdim_y, blockdim_z, nregs, shmem, stream) VALUES (?,?,?,?,?,?,?,?,?,?,?);',
                    (kernel_data.kernel_idx, kernel_data.kernel,
                    kernel_data.grid[0], kernel_data.grid[1], kernel_data.grid[2],
                    kernel_data.blockdim[0], kernel_data.blockdim[1], kernel_data.blockdim[2],
                     kernel_data.nregs, kernel_data.shmem, kernel_data.stream))
        self.conn.commit()
        return kernel_data.kernel_idx

    def insert_instruction(self, kernel_id, instruction):
        cur = self.conn.cursor()

        insn = SASSInstruction.parse(instruction['insn'])
        cur.execute('INSERT INTO Instructions (kernel_id, opcode, insn, op_idx, cta_x, cta_y, cta_z, warp_id, params) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);',
                    (kernel_id,
                     instruction['opcode'],
                     instruction['insn'],
                     instruction['op_idx'],
                     0,0,0,0,
                     json.dumps(instruction['params'])))

        last_insn_id = cur.lastrowid

        for a in instruction['args']:
            cur.execute('INSERT INTO Arguments (instruction_id, arguments) VALUES (?,?);',
                        (last_insn_id, json.dumps(a)))

    def get_kernels(self):
        cur = self.conn.cursor()
        res = cur.execute(f'SELECT * from Kernels;')
        for k in res.fetchall():
            yield k

    def get_kernel(self, kernel_id):
        cur = self.conn.cursor()
        res = cur.execute(f'SELECT * FROM Kernels WHERE kernel_id = ?', (kernel_id,))
        r = res.fetchone()
        return r

    def get_kernel_trace(self, kernel_id):
        cur = self.conn.cursor()
        res = cur.execute(f'SELECT * FROM Instructions WHERE kernel_id = ? ORDER by instruction_id', (kernel_id,)) # TODO: trace ordering
        for r in res.fetchall():
            yield r

    def get_instructions_by_opcode(self, opcode, op_idx = None, kernel_id = None):

        cond = ['opcode=?']
        args = [opcode]

        if op_idx is not None:
            cond.append('op_idx=?')
            args.append(op_idx)

        if kernel_id is not None:
            cond.append('kernel_id=?')
            args.append(kernel_id)

        cur = self.conn.cursor()
        res = cur.execute(f'SELECT * FROM Instructions WHERE {" AND ".join(cond)};', tuple(args))
        for r in res.fetchall():
            yield r

    def get_instruction_args(self, instruction_id):
        cur = self.conn.cursor()
        res = cur.execute(f'SELECT * FROM Arguments WHERE instruction_id = ?',
                          (instruction_id,))

        for r in res.fetchall():
            yield r

    def complete(self):
        self.conn.commit()

def main():
    p = argparse.ArgumentParser(description="Parse a trace produced by NVBit tool record_reg_vals_thread")
    p.add_argument("tracefile")
    p.add_argument("--no-state", action="store_true", help="Don't track state to fix up read values")
    p.add_argument("-o", dest="obs_dbfile", help="Store observations in database")
    p.add_argument("command", nargs="?", default="observations", choices=['raw', 'kernel_order', 'io', 'observations'])
    args = p.parse_args()

    t = RawTrace(args.tracefile, state_tracking = not args.no_state)
    if args.command == 'observations':
        dbfile = None
        last_kernel_idx = None
        if args.obs_dbfile:
            dbfile = TraceStorage(args.obs_dbfile)

        for l in get_observations(t):
            if isinstance(l, dict):
                if not dbfile:
                    print(json.dumps(l))
                else:
                    dbfile.insert_instruction(last_kernel_idx, l)
            elif isinstance(l, KernelData):
                if not dbfile:
                    print(l)
                else:
                    last_kernel_idx = dbfile.insert_kernel(l)


        if dbfile:
            dbfile.complete()
    elif args.command == 'raw':
        for l in t.parse_raw():
            print(l)
    elif args.command == 'kernel_order':
        for l in t.parse_kernel_order():
            print(l)
    elif args.command == 'io':
        for l in t.parse_io():
            print(l)

if __name__ == "__main__":
    main()

