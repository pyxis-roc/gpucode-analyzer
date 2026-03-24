#!/usr/bin/env python3

import re

try:
    from gpucodeanalyzer.isa.sass import SASSInstruction
except ImportError:
    SASSInstruction = None

SASS_WITH_PLR_INSN_RE = re.compile(r"^\s*/\*([0-9a-f]+)\*/\s+(.+) ;\s+// \|(?P<regs>.*)\|$")
PLR_FORMAT_NARROW = re.compile(r"\s+(?P<live>\d+) (?P<status>([v^x: ]*))  $")

def parse_reginfo(sass_insn_match, mw = None):
    insn = sass_insn_match.group(2)
    regs = sass_insn_match.group('regs')
    fields = regs.split("|")

    reg_prefixes = ['R', 'P', 'UR', 'UP']
    print(sass_insn_match.group(1), insn)
    for i, f in enumerate(fields):
        usage = PLR_FORMAT_NARROW.match(f)
        if usage is None:
            if len(f.strip()) == 0:
                # no register information
                continue

            assert usage is not None, (insn, i, f, len(f))

        live = int(usage.group('live'))
        regstatus = usage.group('status')
        read = list(reg_prefixes[i] + str(x) for x, u in enumerate(regstatus) if u in ('v',))
        reads = ",".join(read)
        if len(reads):
            reads = "reads " + reads
        else:
            reads = ""

        written = list(reg_prefixes[i] + str(x) + u  for x, u in enumerate(regstatus) if u in ('^', 'x'))
        writes = ",".join(written)
        if len(writes):
            writes = "writes " + writes
        else:
            writes = ""

        print("\t", reg_prefixes[i], "live", live, writes, reads)
        if mw is not None and len(written) > 1 and reg_prefixes[i] == "R" and SASSInstruction:
            opcode = insn.split()
            if opcode[0][0] == "@":
                opcode  = opcode[1]
            else:
                opcode = opcode[0]

            if (opcode not in SASSInstruction.MULTI_WRITER) and (opcode not in mw):
                print("MULTI_WRITER", opcode, len(written))
                mw[opcode] = {0: len(written)}

def get_instructions(textit):
    for i in textit:
        m = SASS_WITH_PLR_INSN_RE.match(i)
        if m is not None:
            yield m

if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Parse nvdisasm output to obtain instruction register information")
    p.add_argument("plrfile",  help="File to process (output of nvdisasm -plr -lrm narrow)")

    args = p.parse_args()

    mw = {}
    with open(args.plrfile, "r") as f:
        for i in get_instructions(f):
            parse_reginfo(i, mw)

    if(len(mw)):
        print(mw)
