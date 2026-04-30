#!/usr/bin/env python3

class SASSCounter:
    def __init__(self):
        pass


    def is_warp_insn(self, insn):
        if insn.opcode.startswith('HMMA.'):
            return True
        else:
            return False

    def count_bb(self, bb):
        def add_count(count, insn, insn_count):
            if insn.opcode in count:
                for k, v in insn_count.items():
                    count[insn.opcode][k] = count[insn.opcode].get(k, 0) + v
            else:
                count[insn.opcode] = insn_count

        out = {}
        for insn in bb.code:
            if self.is_warp_insn(insn):
                add_count(out, insn, {'warp': 1})
            else:
                add_count(out, insn, {'thread': 1})

        return out

