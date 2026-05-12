#!/usr/bin/env python3

import csv
import cudaocc
import json
import re

def print_device_attrs(r):
    keys = {
        "device__attribute_compute_capability_major" : "computeMajor",
        "device__attribute_compute_capability_minor" : "computeMinor",
        "device__attribute_max_threads_per_block" : "maxThreadsPerBlock",
        "device__attribute_max_threads_per_multiprocessor" : "maxThreadsPerMultiprocessor",
        "device__attribute_max_registers_per_block" : "regsPerBlock",
        "device__attribute_max_registers_per_multiprocessor" : "regsPerMultiprocessor",
        "device__attribute_warp_size" : "warpSize",
        "device__attribute_max_shared_memory_per_block" : "sharedMemPerBlock",
        "device__attribute_max_shared_memory_per_multiprocessor" : "sharedMemPerMultiprocessor",
        "device__attribute_multiprocessor_count" : "numSms",
        "device__attribute_max_shared_memory_per_block_optin" : "sharedMemPerBlockOptin",
        "device__attribute_reserved_shared_memory_per_block" : "reservedSharedMemPerBlock"}

    out = []
    for k in keys:
        #if k.startswith('device__attr'):
        out.append(f"{keys[k]}={r[k].replace(',','')}")

    print(", ".join(out))


def scale(v, unit):
    if unit == '':
        return v

    v = float(v)

    if unit[0] == "K":
        return v * 1000
    else:
        return v

def print_launch_attrs(r, units):
    for k in r:
        if k.startswith('launch_'):
            print(k, scale(r[k], units.get(k, '')), units.get(k, ''))

def parse_tuple(x):
    return tuple(int(xx) for xx in x[1:-1].split(","))

def print_occ(r, funcs, units):
    block = parse_tuple(r['Block Size'])
    grid = parse_tuple(r['Grid Size'])
    funcinfo = funcs[r['Kernel Name']]

    nthreads = block[0]*block[1]*block[2]
    nblocks = grid[0]*grid[1]*grid[2]

    dev = cudaocc.getDevicePropByCC(int(r['device__attribute_compute_capability_major']),
                                  int(r['device__attribute_compute_capability_minor']))

    oc = cudaocc.CUDAOccupancy(dev, cudaocc.DEFAULT_DEVICE_STATE)
    args = (nthreads,
            funcinfo['EIATTR_REGCOUNT'],
            int(scale(r['launch__shared_mem_per_block_static'],
                      units.get('launch__shared_mem_per_block_static', ''))),
            cudaocc.PARTITIONED_GC_OFF,
            cudaocc.FUNC_SHMEM_LIMIT_OPTIN,
            int(scale(r['launch__shared_mem_per_block_dynamic'],
                      units.get('launch__shared_mem_per_block_dynamic', ''))),
            int(r['launch__barrier_count']),
            0)

    f = cudaocc.cudaOccFuncAttributes(*args)

    res = oc.MaxActiveBlocksPerMultiprocessor(nthreads, f.maxDynamicSharedSizeBytes, f)
    return res

def main():
    import argparse

    p = argparse.ArgumentParser(description="Dump statistics from ncu-report.csv")
    p.add_argument("csv", help="CSV File from ncu (ncu -i file.ncu-rep --page raw --csv --print-kernel-base=mangled")
    p.add_argument("json", help="JSON File from hcubin")

    p.add_argument("--da", dest="device_attrs", action="store_true", help="Display device attributes suitable for incorporating into cudaocc")
    p.add_argument("--occ", dest="occ", action="store_true", help="Display occupancies")

    args = p.parse_args()

    with open(args.json, "r") as f:
        funcs = json.load(fp=f)

    with open(args.csv, "r") as f:
        c = csv.DictReader(f)
        units = {}

        for i, r in enumerate(c):
            if i == 0:
                units = r
                continue

            print(r['Kernel Name'], r['Block Size'], r['Grid Size'], r['CC'])
            if args.device_attrs:
                print_device_attrs(r)

            if args.occ:
                print_launch_attrs(r, units)
                v = print_occ(r, funcs, units)
                print('occ', v.activeBlocksPerMultiprocessor)
                print('reason', cudaocc.OCC_LIMIT_SET(v.limitingFactors))

if __name__ == "__main__":
    main()
