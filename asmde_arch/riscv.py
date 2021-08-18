import re

from asmde.lexer import Lexem

from asmde.allocator import (
    Instruction, Architecture, RegFileDescription,
    Register, PhysicalRegister, VirtualRegister)

from asmde.parser import (
    SequentialPattern,
    OpcodePattern,
    VirtualRegisterPattern_SingleReg, ImmediatePattern,
    PhysicalRegisterPattern, RegisterPattern, GenericOffsetPattern, Pattern,
    MetaPopOperatorPredicate, AddrValue,
    LabelPattern
)


class RVRegister(Register):
    """ RISC-V Register family """
    class IntReg(Register.RegClass):
        """ Integer register """
        name = "Int"
        prefix = ""
        reg_prefix = "x"
        @classmethod
        def aliasResolution(cls, spec, index):
            isAlias = spec != "x"
            ALIAS_RESOLUTION_MAP = {
                "x": lambda xi: xi,
                "ra": lambda _: 1,
                "sp": lambda _: 2,
                "gp": lambda _: 3,
                "tp": lambda _: 4,
                "t": lambda ti: ti + 5 if ti <= 2 else ti + 25,
                "fp": lambda _: 8,
                "s": lambda si: {[(0, 8), (1, 9)] + [(i, i+16) for i in xrange(2, 12)]},
                "a": lambda ai: ai + 10,
            }
            return isAlias, ALIAS_RESOLUTION_MAP[spec](index)
    class FPReg(Register.RegClass):
        """ Floating-point register """
        name = "Fp"
        prefix = ""
        reg_prefix = "f"
        @classmethod
        def aliasResolution(cls, spec, index):
            isAlias = spec != "f"
            ALIAS_RESOLUTION_MAP = {
                "f": lambda fi: fi,
                "ft": lambda fti: fti if fti <= 7 else (fti + 20),
                "fs": lambda fsi: (fsi + 8) if fsi <= 1 else (fsi + 16),
                "fa": lambda fai: (fai + 10),
            }
            return isAlias, ALIAS_RESOLUTION_MAP[spec](index)


class VirtualRegisterPattern_Int(VirtualRegisterPattern_SingleReg):
    """ RISC-V Integer Virtual register """
    VIRT_REG_CLASS = RVRegister.IntReg
    VIRT_REG_DESCRIPTOR = "XAI"
class PhysicalRegisterPattern_Int(PhysicalRegisterPattern):
    """ RISC-V Integer Physical register """
    REG_PATTERN = "a[0-9]|zero|ra|sp|gp|tp|t[0-9]+|fp|s[0-9]+|x[0-9]+"
    SUB_REG_PATTERN = "a[0-9]|zero|ra|sp|gp|tp|t[0-9]+|fp|s[0-9]+|x[0-9]+"
    REG_SPLIT_PATTERN = "(?P<spec>a|s|t|x|zero|ra|sp|gp|tp|fp)(?P<index>[0-9]*)"
    REG_CLASS = RVRegister.IntReg
    REG_LEXEM = Lexem

    @classmethod
    def splitSpecIndex(cls, s):
        """ split string @p s into specifier and index
            return a 3-uple (isAlias, spec, index) """
        match = re.match(cls.REG_SPLIT_PATTERN, s)
        spec = match.group("spec")
        index = int(match.group("index"))
        return spec, index

class VirtualRegisterPattern_Fp(VirtualRegisterPattern_SingleReg):
    """ RISC-V Floating-Point Virtual register """
    VIRT_REG_CLASS = RVRegister.FPReg
    VIRT_REG_DESCRIPTOR = "F"
class PhysicalRegisterPattern_Fp(PhysicalRegisterPattern):
    """ RISC-V Floating-Pooint Physical register """
    REG_PATTERN = "(f|fs|ft|fa)[0-9]+"
    SUB_REG_PATTERN = "(f|fs|ft|fa)[0-9]+"
    REG_SPLIT_PATTERN = "(?P<spec>f|ft|fs|fa)(?P<index>[0-9]+)"
    REG_CLASS = RVRegister.FPReg
    REG_LEXEM = Lexem

class RVRegisterPattern_Int(RegisterPattern):
    VIRTUAL_PATTERN_CLASS = VirtualRegisterPattern_Int
    PHYSICAL_PATTERN_CLASS = PhysicalRegisterPattern_Int

class RVOffsetPattern_Std(GenericOffsetPattern):
    """ pattern for address offset """
    OffsetPhysicalRegisterClass = PhysicalRegisterPattern_Int
    OffsetVirtuallRegisterClass = VirtualRegisterPattern_Int

class RVRegisterPattern_FP(RegisterPattern):
    VIRTUAL_PATTERN_CLASS = VirtualRegisterPattern_Fp
    PHYSICAL_PATTERN_CLASS = PhysicalRegisterPattern_Fp

class RVAddressPattern_Std(Pattern):
    @staticmethod
    def parse(arch, lexem_list):
        offset_match = RVOffsetPattern_Std.parse(arch, lexem_list)
        if offset_match is None: return None
        offset_value, lexem_list = offset_match
        lexem_list = MetaPopOperatorPredicate("(")(lexem_list)
        if lexem_list is None:
            # match failed
            return None
        base_match = RVRegisterPattern_Int.parse(arch, lexem_list)
        if base_match is None: return None
        base_value, lexem_list = base_match
        lexem_list = MetaPopOperatorPredicate(")")(lexem_list)
        if lexem_list is None:
            # match failed
            return None
        return AddrValue(base=base_value, offset=offset_value), lexem_list


def loadDumpPattern(parseResult):
    def dump(color_map, use_list, def_list):
        return "{} {}, {}({})".format(parseResult["opc"],
                                      def_list[0].instanciate(color_map),
                                      use_list[1].instanciate(color_map),
                                      use_list[0].instanciate(color_map))
    return dump

def storeDumpPattern(parseResult):
    def dump(color_map, use_list, def_list):
        return "{} {}, {}({})".format(parseResult["opc"],
                                      use_list[0].instanciate(color_map),
                                      use_list[2].instanciate(color_map),
                                      use_list[1].instanciate(color_map))
    return dump

def std2opDumpPattern(parseResult):
    def dump(color_map, use_list, def_list):
        return "{} {}, {}, {}".format(parseResult["opc"],
                                      def_list[0].instanciate(color_map),
                                      use_list[0].instanciate(color_map),
                                      use_list[1].instanciate(color_map))
    return dump

class RV_MatchPattern:
    def __init__(self, tag):
        self.tag = tag

    def dump(self, verbose=False):
        return self.tag

class RV_ImmediateMatchPattern(RV_MatchPattern):
    def __init__(self, value):
        RV_MatchPattern.__init__(self, "imm")
        self.value = value

    def dump(self, verbose=True):
        if verbose:
            return "%s %x" % (self.tag, self.value)
        else:
            return "%s" % self.tag


def LOAD_PATTERN(DstPattern):
    return SequentialPattern(
        [OpcodePattern("opc"), DstPattern("dst"),
         RVAddressPattern_Std("addr")],
        lambda result:
            Instruction(result["opc"],
                        use_list=(result["addr"].base + result["addr"].offset),
                        def_list=result["dst"],
                        dump_pattern=loadDumpPattern(result)))


def STORE_PATTERN(SrcPattern):
    return SequentialPattern(
        [OpcodePattern("opc"),
         SrcPattern("src"),
         RVAddressPattern_Std("addr")],
        lambda result:
            Instruction(result["opc"],
                        use_list=(result["src"] + result["addr"].base + result["addr"].offset),
                        dump_pattern=storeDumpPattern(result)))

LOAD_INT_PATTERN = LOAD_PATTERN(RVRegisterPattern_Int)
STORE_INT_PATTERN = STORE_PATTERN(RVRegisterPattern_Int)

STD_2OP_PATTERN = SequentialPattern(
        [OpcodePattern("opc"), RVRegisterPattern_Int("dst"),
         RVRegisterPattern_Int("lhs"), RVRegisterPattern_Int("rhs")],
        lambda result:
            Instruction(result["opc"],
                        use_list=(result["lhs"] + result["rhs"]),
                        def_list=result["dst"],
                        dump_pattern=std2opDumpPattern(result)))

STD_1OP_1IMM_PATTERN = SequentialPattern(
        [OpcodePattern("opc"), RVRegisterPattern_Int("dst"),
         RVRegisterPattern_Int("op"), ImmediatePattern("imm")],
        lambda result:
            Instruction(result["opc"],
                        match_pattern=RV_ImmediateMatchPattern(result["imm"].value),
                        use_list=(result["op"]),
                        def_list=result["dst"],
                        dump_pattern=lambda color_map, use_list, def_list:
                            "{} {}, {}, {}".format(result["opc"],
                                                    def_list[0].instanciate(color_map),
                                                    use_list[0].instanciate(color_map),
                                                    result["imm"])))

STD_ZEROOP_1IMM_PATTERN = SequentialPattern(
        [OpcodePattern("opc"), RVRegisterPattern_Int("dst"),
         ImmediatePattern("imm")],
        lambda result:
            Instruction(result["opc"],
                        match_pattern=RV_ImmediateMatchPattern(result["imm"].value),
                        use_list=[],
                        def_list=result["dst"],
                        dump_pattern=lambda color_map, use_list, def_list:
                            "{} {}, {}".format(result["opc"],
                                               def_list[0].instanciate(color_map),
                                               result["imm"])))
class FenceSpecifierPattern(Pattern):
    def __init__(self, tag="spec"):
        Pattern.__init__(self, tag)

    def parse(self, arch, lexem_list):
        if len(lexem_list) == 0:
            return None
        else:
            head, lexem_list = lexem_list[0], lexem_list[1:]
            if (not isinstance(head, Lexem)):
                return None
            opcode = head.value
            if re.fullmatch("[iorw]+", opcode):
                return opcode, lexem_list
            return None

FENCE_PATTERN = SequentialPattern([OpcodePattern("opc"),
                                   FenceSpecifierPattern("pred"),
                                   FenceSpecifierPattern("succ")],
                                   lambda result: Instruction(result["opc"], dump_pattern=lambda c,u,d: "{} {}, {}".format(result["opc"], result["pred"], result["succ"])))

ZEROOP_PATTERN = SequentialPattern([OpcodePattern("opc")],
                                   lambda result: Instruction(result["opc"], dump_pattern=lambda c,u,d: result["opc"]))

COND_BRANCH_PATTERN = SequentialPattern(
        [OpcodePattern("opc"), RVRegisterPattern_Int("src1"),
         RVRegisterPattern_Int("src2"), LabelPattern("dst")],
        lambda result: Instruction(result["opc"], is_jump=True,
                                   use_list=(result["src1"] + result["src2"]),
                                   jump_label=result["dst"],
                                   dump_pattern=lambda color_map, use_list, def_list:
                                        "{} {}, {}, {}".format(result["opc"], use_list[0].instanciate(color_map), use_list[1].instanciate(color_map), result["dst"])
                                    ))

RV32M_INSN_PATTERN_MATCH = {
    "mul":  STD_2OP_PATTERN,

    "mulh":  STD_2OP_PATTERN,
    "mulhu":  STD_2OP_PATTERN,
    "mulhsu":  STD_2OP_PATTERN,

    "div":  STD_2OP_PATTERN,
    "divu":  STD_2OP_PATTERN,
    "rem":  STD_2OP_PATTERN,
    "remu":  STD_2OP_PATTERN,
}

RV32I_INSN_PATTERN_MATCH = {
    # load and store instructions
    "lb":   LOAD_INT_PATTERN,
    "lh":   LOAD_INT_PATTERN,
    "lw":   LOAD_INT_PATTERN,
    "lbu":   LOAD_INT_PATTERN,
    "lhu":   LOAD_INT_PATTERN,
    "sb":   STORE_INT_PATTERN,
    "sh":   STORE_INT_PATTERN,
    "sw":   STORE_INT_PATTERN,

    # arithmetic instructions
    "add":  STD_2OP_PATTERN,
    "addi":  STD_1OP_1IMM_PATTERN,
    "sub":  STD_2OP_PATTERN,

    "lui":  STD_ZEROOP_1IMM_PATTERN,
    "auipc":  STD_ZEROOP_1IMM_PATTERN,

    # arithmetic instructions
    "slt":  STD_2OP_PATTERN,
    "sltu":  STD_2OP_PATTERN,
    "slti":  STD_1OP_1IMM_PATTERN,
    "sltiu":  STD_1OP_1IMM_PATTERN,

    # logic instructions
    "and":  STD_2OP_PATTERN,
    "andi":  STD_1OP_1IMM_PATTERN,
    "or":  STD_2OP_PATTERN,
    "ori":  STD_1OP_1IMM_PATTERN,
    "xor":  STD_2OP_PATTERN,
    "xori":  STD_1OP_1IMM_PATTERN,

    # shift instructions
    "sll":  STD_2OP_PATTERN,
    "slli":  STD_1OP_1IMM_PATTERN,
    "sra":  STD_2OP_PATTERN,
    "srai":  STD_1OP_1IMM_PATTERN,
    "srl":  STD_2OP_PATTERN,
    "srli":  STD_1OP_1IMM_PATTERN,

    "fence": FENCE_PATTERN,

    "ebreak": ZEROOP_PATTERN,
    "ecall": ZEROOP_PATTERN,

    # control flow
    "jalr":  STD_1OP_1IMM_PATTERN,
    "jal":  STD_ZEROOP_1IMM_PATTERN,
    # branch
    "beq": COND_BRANCH_PATTERN,
    "bne": COND_BRANCH_PATTERN,
    "blt": COND_BRANCH_PATTERN,
    "bge": COND_BRANCH_PATTERN,
    "bltu": COND_BRANCH_PATTERN,
    "bgeu": COND_BRANCH_PATTERN,
}

def FP_OP_PATTERN(DstPattern, OpPatterns):
    opNum = len(OpPatterns)
    def dumpPattern(parseResult):
        def dump(color_map, use_list, def_list):
            return "{} {}, ".format(parseResult["opc"],
                                   def_list[0].instanciate(color_map)) + \
                    ", ".join("{}".format(use_list[i].instanciate(color_map)) for i in xrange(opNum))
        return dump
    return SequentialPattern(
        [OpcodePattern("opc"), RVRegisterPattern_FP("dst")] +
        [OpPatterns[i]("op%d" % i) for i in range(opNum)],
        lambda result:
            Instruction(result["opc"],
                        use_list=([result["op%d" % i] for i in range(opNum)]),
                        def_list=result["dst"],
                        dump_pattern=dumpPattern(result)))

FP_1OP_PATTERN = FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_FP])
FP_2OP_PATTERN = FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_FP]*2)
FP_3OP_PATTERN = FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_FP]*3)

LOAD_FP_PATTERN = LOAD_PATTERN(RVRegisterPattern_FP)
STORE_FP_PATTERN = STORE_PATTERN(RVRegisterPattern_FP)



RV32F_INSN_PATTERN_MATCH = {
    "fadd.s": FP_2OP_PATTERN,
    "fsub.s": FP_2OP_PATTERN,
    "fmul.s": FP_2OP_PATTERN,
    "fdiv.s": FP_2OP_PATTERN,
    "fmin.s": FP_2OP_PATTERN,
    "fmax.s": FP_2OP_PATTERN,

    "fsqrt.s": FP_1OP_PATTERN,
    "fcvt.s.d": FP_1OP_PATTERN,
    "fcvt.d.s": FP_1OP_PATTERN,

    "fmadd.s" : FP_3OP_PATTERN,
    "fnmadd.s": FP_3OP_PATTERN,
    "fmsub.s" : FP_3OP_PATTERN,
    "fnmsub.s": FP_3OP_PATTERN,

    "flw": LOAD_FP_PATTERN,
    "fsw": STORE_PATTERN,

    "fcvt.s.w": FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_Int]),
    "fcvt.s.wu": FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_Int]),
    "fcvt.w.s": FP_OP_PATTERN(RVRegisterPattern_Int, [RVRegisterPattern_FP]),
    "fcvt.wu.s": FP_OP_PATTERN(RVRegisterPattern_Int, [RVRegisterPattern_FP]),

    "fmv.x.s": FP_OP_PATTERN(RVRegisterPattern_Int, [RVRegisterPattern_FP]),
    "fmc.s.x": FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_Int]),

    "feq.s": FP_OP_PATTERN(RVRegisterPattern_Int, [RVRegisterPattern_Int]*2),
    "flt.s": FP_OP_PATTERN(RVRegisterPattern_Int, [RVRegisterPattern_Int]*2),
    "fle.s": FP_OP_PATTERN(RVRegisterPattern_Int, [RVRegisterPattern_Int]*2),

    "fsgnj.s": FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_FP]),
    "fsgnjn.s": FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_FP]),
    "fsgnjx.s": FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_FP]),

    "fclass.s": FP_OP_PATTERN(RVRegisterPattern_Int, [RVRegisterPattern_FP]),
}


class RV32(Architecture):
    def __init__(self):
        Architecture.__init__(self,
            set([
                RegFileDescription(RVRegister.IntReg, 32, PhysicalRegister, VirtualRegister),
                RegFileDescription(RVRegister.FPReg, 32, PhysicalRegister, VirtualRegister)
            ]),
            dict(list(RV32I_INSN_PATTERN_MATCH.items()) +
                 list(RV32M_INSN_PATTERN_MATCH.items()) +
                 list(RV32F_INSN_PATTERN_MATCH.items()))
        )

    def getPhyRegPatternList(self):
        return [PhysicalRegisterPattern_Int]

    def getVirtualRegClassPatternMap(self):
       REG_CLASS_PATTERN_MAP = {
           "X": VirtualRegisterPattern_Int,
           "A": VirtualRegisterPattern_Int,
           "F": VirtualRegisterPattern_Fp,
       }
       return REG_CLASS_PATTERN_MAP
