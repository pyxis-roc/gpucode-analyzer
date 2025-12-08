class SASSClassifier:
    def __init__(self):
        pass

    def classify(self, insn):
        if insn.opcode.startswith("IMAD") or insn.opcode.startswith("IADD"):
            return "int-arithmetic"
        elif insn.opcode.startswith('UIADD3.') or insn.opcode == 'UIADD3':
            return "int-arithmetic-uniform"
        elif insn.opcode.startswith("LDG."):
            if ".128." in insn.opcode:
                sz = '/16'
            else:
                sz = ''

            return f"memory-read/global{sz}"
        elif insn.opcode.startswith("STG."):
            if ".128." in insn.opcode:
                sz = '/16'
            else:
                sz = ''
            return f"memory-write/global{sz}"
        elif insn.opcode.startswith("ULDC.") or insn.opcode == 'ULDC':
            if insn.opcode.endswith('.64'):
                sz = '8'
            else:
                sz = '4'

            return f"memory-uniform/constant/{sz}"
        elif insn.opcode == "BRA" or insn.opcode == "EXIT" or insn.opcode.startswith("CALL."):
            return "control"
        elif insn.opcode.startswith("ISETP.") or insn.opcode.startswith("UISETP."):
            return "logical"
        elif insn.opcode.startswith("PLOP3.") or insn.opcode.startswith("ULOP3."):
            return "logical"
        elif insn.opcode.startswith("LOP3."):
            return "int-arithmetic"
        elif insn.opcode.startswith("MOV.") or insn.opcode == "SEL" or insn.opcode == "USEL" or insn.opcode.startswith("UMOV.") or insn.opcode == "MOV" or insn.opcode == "UMOV":
            return "register-to-register"
        elif insn.opcode == "CS2R" or insn.opcode == 'S2R':
            return "register-to-register"
        elif insn.opcode.startswith("SHF."):
            return "int-arithmetic"
        elif insn.opcode.startswith("USHF."):
            return "int-arithmetic-uniform"
        elif insn.opcode.startswith('LEA.'):
            return 'int-arithmetic'
        elif insn.opcode.startswith('ULEA.') or insn.opcode == 'ULEA':
            return "int-arithmetic-uniform"

        return "unknown"

    def intensity(self, cls):
        if cls == 'int-arithmetic': # not if uniform...
            return {'arithmetic': 32}
        elif cls.startswith('memory-read/global'):
            sz = int(cls[len('memory-read/global/')])
            return {'memory': sz * 32}
        elif cls.startswith('memory-write/global'):
            sz = int(cls[len('memory-write/global/')])
            return {'memory': sz * 32}
        elif cls == 'register-to-register':
            return {}
        elif cls == 'logical':
            return {}
        elif cls.startswith('memory-uniform'):
            return {} # TODO
        elif cls == 'int-arithmetic-uniform':
            return {'arithmetic': 1}
        elif cls == 'control':
            return {}
        else:
            print(cls)
            return {}
