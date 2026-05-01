#!/usr/bin/env python3


import argparse
import trace
from functools import reduce
from gpucodeanalyzer.isa.loader import inject_loader_args, load_asmfile
from gpucodeanalyzer.generic_cfg import CFG
from collections import namedtuple
import csv

RENUMBER = namedtuple('RENUMBER', 'sm warp_id linblock linthread block_idx thread_idx')

class GPUConfig:
    numSms = None

    def __init__(self, numSms):
        self.numSms = numSms

class Config:
    grid = None
    block = None

    def __init__(self, grid_x, grid_y, grid_z, block_x, block_y, block_z, occupancy):
        self.grid = [grid_x, grid_y, grid_z]
        self.block = [block_x, block_y, block_z]
        self.block_threads = reduce(lambda x, y: x * y, self.block, 1)
        self.grid_blocks = reduce(lambda x, y: x * y, self.grid, 1)
        self.occupancy = occupancy

    def to_linear(self, thread):
        return thread[0] + thread[1] * self.block_dim[0] + self.thread[2] * self.block_dim[0] * self.block_dim[1]

    def from_linear(self, lin, xyz):
        z = lin // (xyz[0]*xyz[1])
        y = (lin % (xyz[0]*xyz[1])) // xyz[0]
        x = (lin % (xyz[0]*xyz[1])) % xyz[0]
        return (x, y, z)

    def linear2cta(self, linthread):
        lincta = linthread // self.block_threads
        return lincta, self.from_linear(lincta, self.grid)

    def linear2thread(self, linthread):
        ctathread = linthread % self.block_threads
        return ctathread, self.from_linear(ctathread, self.block)

    def renumber(self, trace_id, gpu_config):
        trace_id = int(trace_id)

        lincta, cta = self.linear2cta(trace_id)
        linthread, thread = self.linear2thread(trace_id)

        wave_size = self.occupancy * gpu_config.numSms
        warp_id = linthread // 32

        return RENUMBER((lincta % gpu_config.numSms) if lincta < wave_size else None,
                        warp_id,
                        lincta, linthread, cta, thread)


class Counter:
    def __init__(self, cfg, disp, trace, launch_config, gpu_config):
        self.cfg = cfg
        self.disp = disp
        self.trace = trace
        self.launch_config = launch_config
        self.gpu_config = gpu_config

        self.counter = disp.counter()()
        self.bb_counts = {}
        self.trace_counts = {}

    def count_bb(self):
        for bb in self.cfg.blocks:
            self.bb_counts[bb.target()] = self.counter.count_bb(bb)

    def _update_count(self, prev, cur, mul = 1):
        for ev in cur:
            if ev not in prev:
                prev[ev] = {}

            for ctr in cur[ev]:
                count = cur[ev][ctr] * mul
                prev[ev][ctr] = prev[ev].get(ctr, 0) + count

    def count_trace(self):
        trace = self.trace
        for tr in trace.traces:
            tdkey = trace.traces[tr]
            if tdkey in self.trace_counts: continue

            td = trace.data2trace[tdkey]

            trace_count = {}
            for _, bb, count in td:
                if len(bb) < 4:
                    bb = '0' * (4 - len(bb)) + bb

                bbc = self.bb_counts[bb]
                self._update_count(trace_count, bbc, count)

            self.trace_counts[tdkey] = trace_count

    def count_cta(self):
        trace = self.trace
        lc = self.launch_config

        cta_to_threads = {}
        for tr in trace.traces:
            n = lc.renumber(tr[1], self.gpu_config)

            if n.linblock not in cta_to_threads:
                cta_to_threads[n.linblock] = []

            cta_to_threads[n.linblock].append((tr, n))

        cta_counts = {}
        for cta in cta_to_threads:
            cta_count = {}
            trace_comp = {}
            for tr, _ in cta_to_threads[cta]:
                tdkey = self.trace.traces[tr]
                trace_comp[tdkey] = trace_comp.get(tdkey, 0) + 1

            for tdkey, count in trace_comp.items():
                self._update_count(cta_count, self.trace_counts[tdkey], count)

            cta_counts[cta] = cta_count

        self.cta_counts = cta_counts
        self.cta_to_threads = cta_to_threads

    def count_sm(self):
        sm_counts = dict([(k, {}) for k in range(self.gpu_config.numSms)])
        for cta in self.cta_to_threads:
            tinfo = self.cta_to_threads[cta]
            sm = tinfo[0][1].sm
            if sm is None: continue # past first wave

            self._update_count(sm_counts[sm], self.cta_counts[cta])
            self._update_count(sm_counts[sm], {'_BLOCK': {'block': 1}})

        self.sm_counts = sm_counts

    def dump_sm_counts(self):
        return self._dump_count('sm', self.sm_counts)

    def dump_cta_counts(self):
        return self._dump_count('cta', self.cta_counts)

    def _dump_count(self, count_src, counts):
        for src_id in counts:
            for ev in sorted(counts[src_id].keys()):
                out = {'src': count_src, 'src_id': src_id, 'ev': ev}
                for k in ['thread', 'warp', 'block']:
                    out[k] = counts[src_id][ev].get(k, 0)

                yield out

    def count_all(self):
        self.count_bb()
        self.count_trace()
        self.count_cta()
        self.count_sm()

    def write_csv(self, csvfile, cta = True, sm = True):
        with open(csvfile, "w", newline='') as f:
            ocsv = csv.DictWriter(f, ['src', 'src_id', 'ev', 'thread', 'warp', 'block'])
            ocsv.writeheader()
            if cta:
                for o in self.dump_cta_counts():
                    ocsv.writerow(o)

            if sm:
                for o in self.dump_sm_counts():
                    ocsv.writerow(o)

def main():
    p = argparse.ArgumentParser(description="Count")
    p.add_argument("trace")
    inject_loader_args(p)
    p.add_argument("num_sms", type=int)
    p.add_argument("occupancy", type=int)
    p.add_argument("--no-sm", action="store_true", help="Do not output per-SM first wave statistics")
    p.add_argument("--no-cta", action="store_true", help="Do not output per-CTA statistics")
    p.add_argument("-o", dest="output", help="Output CSV file")
    args = p.parse_args()

    metadata, disp, code = load_asmfile(args)
    cfg = CFG(code, args.fn)
    cfg.build()

    gc = GPUConfig(args.num_sms)

    t = trace.PathTrace(args.trace)
    t.load()
    assert t.metadata is not None, "Need a trace with metadata"

    # TODO: occupancy
    config = t.metadata + [args.occupancy]
    config = Config(*config)

    ctr = Counter(cfg, disp, t, config, gc)
    ctr.count_all()

    ctr.write_csv(args.output or "/dev/stdout")


if __name__ == "__main__":
    main()
