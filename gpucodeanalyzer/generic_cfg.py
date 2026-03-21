#!/usr/bin/env python3

class Instruction:
    label = None
    opcode = None

    def targets(self):
        if self.is_control():
            raise NotImplementedError

    def is_control(self):
        return isinstance(self, ControlInsn)

    def reads(self):
        raise NotImplementedError

    def writes(self):
        raise NotImplementedError

    def code(self):
        raise NotImplementedError

class ControlInsn(Instruction):
    indirect_targets = None

    def targets(self):
        """Return multiple target pcs"""
        raise NotImplementedError

    def target(self):
        """Returns pc of target"""
        raise NotImplementedError

    def is_conditional(self):
        raise NotImplementedError

class Operand:
    def __init__(self, operand, read = False, write = False, implicit = False):
        self.operand = operand
        self.read = read
        self.write = write
        self.implicit = implicit # does not appear in the instruction

    def is_read(self):
        return self.read

    def is_write(self):
        return self.write

    def access(self):
        a = ""

        if self.is_read():
            a += "R"

        if self.is_write():
            a += "W"

        return a

    def is_implicit(self):
        return self.implicit

class Register:
    def __init__(self, n):
        self.n = n

    def __str__(self):
        return f"Register({self.n})"

    def is_constant(self):
        return False

    __repr__ = __str__

class Memory:
    pass


class BasicBlock:
    def __init__(self, name, code):
        self.name = name
        self.code = code
        self.successors = {}
        self.predecessors = {}

    def reverse(self):
        succ = {}
        pred = {}

        for s in self.successors.values():
            pred[s.name] = s

        for p in self.predecessors.values():
            succ[p.name] = p

        self.successors = succ
        self.predecessors = pred

    def add_successor(self, label, bb):
        # TODO: prevent duplicate adding?
        assert label not in self.successors, f"Duplicate successor label {label}"
        self.successors[label] = bb

    def add_predecessor(self, bb):
        self.predecessors[bb.name] = bb

    def remove_successor(self, label):
        self.successors[label].remove_predecessor(self)
        del self.successors[label]

    def remove_predecessor(self, bb):
        del self.predecessors[bb.name]

    def _mark_as_predecessor(self):
        # must be called once all successors have been added

        for s in self.successors:
            self.successors[s].add_predecessor(self)

    def __str__(self):
        return f"{self.name}: {self.successors}\n" + "\n".join([f"  {c}" for c in self.code])

    def __repr__(self):
        return f"BasicBlock({self.name}, ...)"

    def copy(self):
        o = BasicBlock(self.name, self.code)
        o.successors = dict(self.successors.items())
        o.predecessors = dict(self.predecessors.items())

        return o

    def target(self):
        if hasattr(self, '_target'):
            return self._target
        elif len(self.code) > 0:
            return self.code[0].label
        elif self.name in ("_start", "_exit"):
            return self.name
        else:
            raise ValueError

class CFG:
    def __init__(self, codefile, fn_name = None):
        self.codefile = codefile
        self.fn_name = fn_name
        self.blocks = [BasicBlock('_start', []), BasicBlock('_exit', [])]
        self.labels_to_blocks = {'_start': self.blocks[0],
                                 '_exit': self.blocks[1]}
        self.names_to_blocks = {'_start': self.labels_to_blocks['_start'],
                                '_exit': self.labels_to_blocks['_exit'],
                                }

    def build(self):
        def add_bb(bbcode, ndx, last_bb):
            bb = BasicBlock(f"BB{ndx}", bbcode)
            self.blocks.append(bb)

            self.names_to_blocks[bb.name] = bb
            self.labels_to_blocks[bb.code[0].label] = bb

            if last_bb:
                if len(last_bb.code) and last_bb.code[-1].is_control():
                    # true targets patched up later by other code
                    if last_bb.code[-1].is_conditional():
                        last_bb.add_successor('false', bb)
                else:
                    last_bb.add_successor('next', bb)

            return [], ndx + 1, bb

        starts = set()
        ends = set()
        next_is_start = False
        indirects = set()

        if self.fn_name:
            code = self.codefile.codes[self.fn_name]
        else:
            code = self.codefile.code

        for i in code:
            if next_is_start:
                starts.add(i.label)
                next_is_start = False

            if i.is_control():
                ends.add(i.label)
                for tgt in i.targets():
                    starts.add(tgt)

                if i.is_indirect():
                    indirects.add(i.label)

                next_is_start = True

        bbndx = 0
        last_bb = self.labels_to_blocks['_start']
        current = []
        for i in code:
            if i.label in starts:
                if len(current):
                    current, bbndx, last_bb = add_bb(current, bbndx, last_bb)
            elif i.label in ends:
                current.append(i)
                current, bbndx, last_bb = add_bb(current, bbndx, last_bb)
                continue

            current.append(i)

        if len(current):
            current, bbndx, last_bb = add_bb(current, bbndx, last_bb)

        # fix up branch targets to bb; could be avoided
        for bb in self.blocks:
            #print(bb)
            if len(bb.code) == 0: continue
            last_insn = bb.code[-1]
            if last_insn.is_control():
                targets = last_insn.targets()
                succlabel = 'true' if last_insn.is_conditional() else 'next'
                for tgt, tgtndx in zip(targets, [""] + list(range(1, len(targets)))):
                    bb.add_successor(f'{succlabel}{tgtndx}',
                                     self.labels_to_blocks[tgt])

        # populate predecessors
        for bb in self.blocks:
            bb._mark_as_predecessor()

        if len(indirects):
            self.codefile.resolve_indirects(self, indirects)

        self.check_consistency()

    def update_indirects(self, indirects):
        for label, addr in indirects.items():
            for a in addr:
                if a not in self.labels_to_blocks:
                    print(f"Address {a} not found as a basic block. NotYetImplemented, splitting blocks")
                    raise NotImplementedError

        changed = False
        for bb in self.blocks:
            if len(bb.code) == 0: continue
            last_insn = bb.code[-1]
            if last_insn.is_control() and last_insn.is_indirect():
                if last_insn.label in indirects:
                    cur_targets = set(last_insn.targets())
                    res_targets = set(indirects[last_insn.label])
                    new_targets = res_targets - cur_targets
                    if len(new_targets):
                        changed = True
                        k = len(cur_targets)
                        for r in new_targets:
                            bb.add_successor(f'indirect{k}', self.labels_to_blocks[r])
                            k = k + 1

                        bb._mark_as_predecessor()

                        if last_insn.indirect_targets is None:
                            last_insn.indirect_targets = new_targets
                        else:
                            last_insn.indirect_targets.extend(new_targets)

                        current_targets = set(last_insn.indirect_targets)
                        remove = []
                        for s in bb.successors:
                            if bb.successors[s].target() not in current_targets:
                                remove.append(s)

                        for rs in remove:
                            bb.remove_successor(rs)



    def check_consistency(self):
        for b in self.blocks:
            if len(b.predecessors) == 0 and b.name != "_start" and b.target() != "0000": #TODO: fix the 0000
                print(f"WARNING:generic_cfg:no predecessors: {b.target()}")

            if len(b.successors) == 0 and b.name != "_exit":
                print(f"WARNING:generic_cfg: no successors: {b.target()}")

    def dump(self):
        for b in self.blocks:
            print(b)

    def dump_code(self, output):
        for b in self.blocks:
            print(f">>> {b.target()}", file=output)
            for i in b.code:
                print(i.code(), file=output)

    def dump_dot(self, output, code=True, xinsn=lambda i: i.insn, count=False):
        print("digraph {", file=output)
        for b in self.blocks:
            if count:
                count = str(len(b.code)) + "\\n"
            else:
                count = ""

            bbcode = f'"{count}' + b.target() + "\\n" + "\\n".join([str(xinsn(s)) for s in b.code]) + '"'
            if not code:
                bbcode = f'"{count}"'

            print(b.name + f" [label={bbcode},shape=rect];", file=output)
            print("\n".join(f"{b.name} -> {succ.name} [label=\"{lbl if lbl != 'next' else ''}\"];" for lbl, succ in b.successors.items()), file=output)
        print("}", file=output)

    def copy(self):
        x = CFG(self.codefile, self.fn_name)
        x.blocks = list([b.copy() for b in self.blocks])

        l2b = {}
        l2b['_start'] = self.labels_to_blocks['_start'].copy()
        l2b['_exit'] = self.labels_to_blocks['_exit'].copy()

        l2b.update(dict((b.code[0].label, b) for b in x.blocks if len(b.code)))

        # note, doesn't deep copy instructions
        for l in self.labels_to_blocks:
            x.labels_to_blocks[l] = l2b[l]

        # note, doesn't deep copy instructions
        x.names_to_blocks = dict([(b.name, b) for b in x.blocks])

        return x

    def convert(self, converter, func_name = None):
        assert (func_name or self.fn_name) is not None, f'Needs a function name'
        converter.init_cfg(self, func_name or self.fn_name)
        block_order = converter.output_block_order()

        for b in block_order:
            converter.convert_block(self.labels_to_blocks[b])

        converter.finish_cfg()

    def reverse(self):
        for b in self.blocks:
            b.reverse()

    def all_instructions(self):
        for b in self.blocks:
            for i in b.code:
                yield i
