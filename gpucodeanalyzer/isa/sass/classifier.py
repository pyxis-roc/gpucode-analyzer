class SASSClassifier:
    def __init__(self):
        pass

    def classify(self, insn):
        if insn.predicate and insn.predicate == '!PT':
            return "nop"

        if insn.opcode.startswith("IMAD") or insn.opcode.startswith("IADD"):
            return "int-arithmetic"
        elif insn.opcode.startswith("IMNMX"):
            return "int-arithmetic" # logical?
        elif insn.opcode.startswith("IABS"): # or insn.opcode.startswith("IADD"):
            return "int-arithmetic"
        elif insn.opcode.startswith("MUFU."): # or insn.opcode.startswith("IADD"):
            return "fp-arithmetic"
        elif insn.opcode.startswith("FMUL.") or insn.opcode == 'FMUL': # or insn.opcode.startswith("IADD"):
            return "fp-arithmetic"
        elif insn.opcode.startswith('UIADD3.') or insn.opcode == 'UIADD3':
            return "int-arithmetic-uniform"
        elif insn.opcode.startswith('UIMAD'):
            return "int-arithmetic-uniform"
        elif insn.opcode.startswith("LD."):
            return f"memory-read/global/32"
        elif insn.opcode.startswith("LDG."):
            if ".128." in insn.opcode or insn.opcode.endswith('.128'):
                sz = '/16'
            elif insn.opcode == 'LDG.E.CONSTANT':
                sz = '/32'
            elif insn.opcode == 'LDG.E.64':
                sz = '/64'
            elif insn.opcode == 'LDG.E':
                sz = '/32'
            else:
                assert False, insn.opcode # NotImplemented

            return f"memory-read/global{sz}"
        elif insn.opcode.startswith("STG."):
            if ".128." in insn.opcode or insn.opcode.endswith('.128'):
                sz = '/16'
            elif insn.opcode == 'STG.E':
                sz = '/32'
            else:
                assert False, insn.opcode
            return f"memory-write/global{sz}"
        elif insn.opcode.startswith("STS"):
            if ".128." in insn.opcode:
                sz = '/16'
            else:
                sz = ''

            return f"memory-write/shared{sz}"
        elif insn.opcode.startswith("LDS.") or insn.opcode == 'LDS':
            if insn.opcode.endswith('.64'):
                sz = '/8'
            elif insn.opcode.endswith('.128'):
                sz = '/16'
            else:
                sz = ''

            return f"memory-read/shared{sz}"
        elif insn.opcode.startswith('BAR.') or insn.opcode.startswith('DEPBAR.'):
            return f"barrier"
        elif insn.opcode == 'LDGDEPBAR':
            return f"barrier/memory-read/global"
        elif insn.opcode.startswith("STL"):
            if ".128." in insn.opcode:
                sz = '/16'
            else:
                sz = ''

            return f"memory-write/local{sz}"
        elif insn.opcode.startswith("LDL.") or insn.opcode == 'LDL':
            if insn.opcode.endswith('.64'):
                sz = '/8'
            else:
                sz = '/4'

            return f"memory-read/local{sz}"

        elif insn.opcode.startswith("ULDC.") or insn.opcode == 'ULDC':
            if insn.opcode.endswith('.64'):
                sz = '8'
            else:
                sz = '4'
                #assert False, insn.opcode

            return f"memory-uniform/constant/{sz}"
        elif insn.opcode.startswith("LDSM."):
            return f"matrix-read/global"
        elif insn.opcode.startswith("LDGSTS."):
            if insn.opcode.endswith('.128'):
                sz = '16'
            else:
                assert False, insn.opcode

            return [f"memory-read/global/{sz}", f"memory-write/shared/{sz}"]
        elif insn.opcode == "BRA" or insn.opcode == "EXIT" or insn.opcode.startswith("CALL."):
            return "control"
        elif insn.opcode.startswith("ISETP.") or insn.opcode.startswith("UISETP."):
            return "logical"
        elif insn.opcode.startswith("FSETP."):
            return "logical/float"
        elif insn.opcode.startswith("PLOP3.") or insn.opcode.startswith("ULOP3."):
            return "logical"
        elif insn.opcode.startswith("LOP3."):
            return "int-arithmetic"
        elif insn.opcode.startswith("MOV.") or insn.opcode == "SEL" or insn.opcode == "USEL" or insn.opcode.startswith("UMOV.") or insn.opcode == "MOV" or insn.opcode == "UMOV" or insn.opcode == "P2R":
            return "register-to-register"
        elif insn.opcode in {'CS2R','S2R','R2P','S2UR','R2UR'}:
            return "register-to-register"
        elif insn.opcode.startswith("SHFL."):
            return 'warp'
        elif insn.opcode.startswith("SHF."):
            return "int-arithmetic"
        elif insn.opcode.startswith("USHF."):
            return "int-arithmetic-uniform"
        elif insn.opcode.startswith('LEA.') or insn.opcode == 'LEA':
            return 'int-arithmetic'
        elif insn.opcode.startswith('ULEA.') or insn.opcode == 'ULEA':
            return "int-arithmetic-uniform"
        elif insn.opcode.startswith('HMMA.'):
            return 'tc-arithmetic/fp16' # tensor-code
        elif insn.opcode.startswith('FFMA'):
            return 'fp-arithmetic' # tensor-code
        elif insn.opcode.startswith('F2FP.'):
            return 'conversion/float-to-float'
        elif insn.opcode.startswith('F2I.'):
            return 'conversion/float-to-int'
        elif insn.opcode.startswith('I2F.'):
            return 'conversion/int-to-float'
        elif insn.opcode.startswith('I2FP.'):
            return 'conversion/int-to-float'

        return "unknown"

    def intensity(self, cls):
        if cls == 'int-arithmetic': # not if uniform...
            return {'int-arithmetic': 32}
        elif cls.startswith('memory-read/global'):
            sz = int(cls[len('memory-read/global/'):])
            return {'memory': sz * 32}
        elif cls.startswith('memory-write/global'):
            sz = int(cls[len('memory-write/global/'):])
            return {'memory': sz * 32}
        elif cls.startswith('memory-read/shared'):
            sz = int(cls[len('memory-read/shared/'):] or '4')
            return {'shared-memory': sz * 32}
        elif cls.startswith('memory-write/shared'):
            sz = int(cls[len('memory-write/shared/'):] or '4')
            return {'shared-memory': sz * 32}
        elif cls.startswith('memory-read/local'):
            sz = int(cls[len('memory-read/local/'):] or '4')
            return {'local-memory': sz * 32}
        elif cls.startswith('memory-write/local'):
            sz = int(cls[len('memory-write/local/'):] or '4')
            return {'local-memory': sz * 32}
        elif cls.startswith('matrix-read/global'):
            return {'matrix-read-ops': 32} # TODO: translate into bytes
        elif cls == 'register-to-register':
            return {}
        elif cls == 'logical':
            return {}
        elif cls == 'logical/float':
            return {}
        elif cls.startswith('memory-uniform'):
            return {} # TODO
        elif cls == 'int-arithmetic-uniform':
            return {'int-arithmetic': 1}
        elif cls == 'control' or cls == 'barrier' or cls.startswith('barrier'):
            return {}
        elif cls == 'conversion/float-to-int':
            return {'conversion': 32} # for now
        elif cls == 'conversion/int-to-float':
            return {'conversion': 32} # for now
        elif cls == 'conversion/float-to-float':
            return {'conversion': 32}
        elif cls == 'fp-arithmetic':
            return {'fp-arithmetic': 32}
        elif cls == 'tc-arithmetic/fp16':
            return {'fp16-arithmetic': (7*32)} # TODO: actual count
        elif cls == 'warp':
            return {'warp': 1}
        else:
            print("Unhandled in intensity", cls)
            return {}
