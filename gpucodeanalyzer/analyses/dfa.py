
class DFA:
    def __init__(self, cfg):
        self.cfg = cfg
        self.IN = {}
        self.OUT = {}

    def initialize(self, block):
        raise NotImplementedError

    def xfer(self, block, flowfact):
        raise NotImplementedError

    def merge(self, flowblocks):
        raise NotImplementedError

    def forward(self):
        blocks = []

        # TODO: change order to "optimal"
        for b in self.cfg.blocks:
            self.initialize(b)
            blocks.append(b)

        changed = True
        while changed:
            changed = False

            for b in blocks:
                n = b.name
                self.IN[n] = self.merge(b.predecessors)
                out = self.xfer(b, self.IN[n])
                changed = changed or (out != self.OUT[n])
                self.OUT[n] = out

    def backward(self):
        raise NotImplementedError
