#!/usr/bin/env python3

import argparse
import re

TRACE_HDR = re.compile(r"^trace (?P<trace>\d+) id (?P<id>\d+)$")
TRACE_VAL = re.compile("\t" + r"\s+(?P<ser>\d+) (?P<target>[A-fa-f0-9]+) (?P<count>\d+)$")

class PathTrace:
    def __init__(self, tracefile):
        self.tracefile = tracefile
        self.data = {}
        self.data2trace = {}
        self.traces = {}

    def load(self):
        def process_trace(trace, trace_id, trace_data):
            if not len(trace_data): return

            trace_data = tuple(trace_data)
            if trace_data not in self.data:
                self.data[trace_data] = len(self.data) + 1

            self.traces[(trace, trace_id)] = self.data[trace_data]

        with open(self.tracefile, "r") as f:
            trace_data = []
            trace = None
            trace_id = None
            for l in f:
                m = TRACE_HDR.match(l)
                if m:
                    process_trace(trace, trace_id, trace_data)
                    trace_data = []
                    trace = int(m.group('trace'))
                    trace_id = m.group('id') # opaque?
                    continue
                else:
                    m = TRACE_VAL.match(l)
                    if m is not None:
                        trace_data.append((int(m.group('ser')),
                                           m.group('target'),
                                           int(m.group('count'))))

            if len(trace_data):
                process_trace(trace, trace_id, trace_data)

            for k, v in self.data.items():
                assert v not in self.data2trace
                self.data2trace[v] = k

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Load a path trace")

    p.add_argument("trace", help="Trace data")

    args = p.parse_args()

    pt = PathTrace(args.trace)
    pt.load()

    print(pt.traces, pt.data)
