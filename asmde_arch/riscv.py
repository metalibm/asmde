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
    OptionalPattern,
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
            # None is the default spec
            isAlias = spec != "x" and spec != None
            ALIAS_RESOLUTION_MAP = {
                None: lambda xi: xi,
                "x": lambda xi: xi,
                "ra": lambda _: 1,
                "sp": lambda _: 2,
                "gp": lambda _: 3,
                "tp": lambda _: 4,
                "t": lambda ti: ti + 5 if ti <= 2 else ti + 25,
                "fp": lambda _: 8,
                "zero": lambda _: 0,
                "s": lambda si: dict([(0, 8), (1, 9)] + [(i, i+16) for i in range(2, 12)])[si],
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
            isAlias = spec != "f" and spec != None
            ALIAS_RESOLUTION_MAP = {
                None: lambda fi: fi,
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
    SPLITABLE_PATTERN = "(a|s|t|x)([0-9]+)"
    NON_SPLITABLE_PATTERN = "zero|ra|sp|gp|tp|fp" 
    REG_SPLIT_PATTERN = "(?P<spec>a|s|t|x)(?P<index>[0-9]*)"
    REG_CLASS = RVRegister.IntReg
    REG_LEXEM = Lexem

    @classmethod
    def splitSpecIndex(cls, s):
        """ split string @p s into specifier and index
            return a 3-uple (isAlias, spec, index) """
        if re.match(cls.SPLITABLE_PATTERN, s):
            match = re.match(cls.REG_SPLIT_PATTERN, s)
            spec = match.group("spec")
            idxStr = match.group("index")
            index = int(idxStr)
        else:
            assert re.match(cls.NON_SPLITABLE_PATTERN, s)
            spec = s 
            index = None
        return spec, index

class VirtualRegisterPattern_Fp(VirtualRegisterPattern_SingleReg):
    """ RISC-V Floating-Point Virtual register """
    VIRT_REG_CLASS = RVRegister.FPReg
    VIRT_REG_DESCRIPTOR = "F"
class PhysicalRegisterPattern_Fp(PhysicalRegisterPattern):
    """ RISC-V Floating-Pooint Physical register """
    REG_PATTERN = "(f|fs|ft|fa)[0-9]+"
    SUB_REG_PATTERN = "f[sta]{0,1}[0-9]+"
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

def std1opDumpPattern(parseResult):
    def dump(color_map, use_list, def_list):
        return "{} {}, {}".format(parseResult["opc"],
                                  def_list[0].instanciate(color_map),
                                  use_list[0].instanciate(color_map))
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

STD_1OP_PATTERN = SequentialPattern(
        [OpcodePattern("opc", match_predicate=True), RVRegisterPattern_Int("dst"),
         RVRegisterPattern_Int("op")],
        lambda result:
            Instruction(result["opc"],
                        use_list=(result["op"]),
                        def_list=result["dst"],
                        dump_pattern=std1opDumpPattern(result)))

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

STD_ZEROOP = SequentialPattern(
        [OpcodePattern("opc")],
        lambda result:
            Instruction(result["opc"],
                        use_list=[],
                        def_list=[],
                        dump_pattern=lambda color_map, use_list, def_list:
                            "{}".format(result["opc"])))

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
        lambda result: Instruction(result["opc"], is_cond_jump=True,
                                   use_list=(result["src1"] + result["src2"]),
                                   jump_label=result["dst"],
                                   dump_pattern=lambda color_map, use_list, def_list:
                                        "{} {}, {}, {}".format(result["opc"], use_list[0].instanciate(color_map), use_list[1].instanciate(color_map), result["dst"])
                                    ))

COND_BRANCH_1OP_PATTERN = SequentialPattern(
        [OpcodePattern("opc"), RVRegisterPattern_Int("src1"),
         LabelPattern("dst")],
        lambda result: Instruction(result["opc"], is_cond_jump=True,
                                   use_list=result["src1"],
                                   jump_label=result["dst"],
                                   dump_pattern=lambda color_map, use_list, def_list:
                                        "{} {}, {}".format(result["opc"], use_list[0].instanciate(color_map), result["dst"])
                                    ))
CALL_PATTERN = SequentialPattern(
        [OpcodePattern("opc"),
         LabelPattern("dst")],
        lambda result: Instruction(result["opc"],
                                   is_nocond_jump=True,
                                   jump_label=result["dst"],
                                   dump_pattern=lambda color_map, use_list, def_list:
                                        "{} {}".format(result["opc"], result["dst"])
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
    "li":  STD_ZEROOP_1IMM_PATTERN,
    "auipc":  STD_ZEROOP_1IMM_PATTERN,

    # arithmetic instructions
    "slt":  STD_2OP_PATTERN,
    "sltu":  STD_2OP_PATTERN,
    "slti":  STD_1OP_1IMM_PATTERN,
    "sltiu":  STD_1OP_1IMM_PATTERN,
    # alias
    "snez": STD_1OP_PATTERN,

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
    "ret": STD_ZEROOP,
    # alias
    "call":  CALL_PATTERN,
    "j":  CALL_PATTERN,

    # branch
    "beq": COND_BRANCH_PATTERN,
    "bne": COND_BRANCH_PATTERN,
    "blt": COND_BRANCH_PATTERN,
    "bge": COND_BRANCH_PATTERN,
    "bltu": COND_BRANCH_PATTERN,
    "bgeu": COND_BRANCH_PATTERN,
    # alias
    "bnez": COND_BRANCH_1OP_PATTERN,
    "beqz": COND_BRANCH_1OP_PATTERN,

}

def FP_OP_PATTERN(DstPattern, OpPatterns, match_predicate=True, optRounding=False):
    opNum = len(OpPatterns)
    def dumpPattern(parseResult):
        def dump(color_map, use_list, def_list):
            return "{} {}, ".format(parseResult["opc"],
                                   def_list[0].instanciate(color_map)) + \
                    ", ".join("{}".format(use_list[i].instanciate(color_map)) for i in range(opNum)) + \
                    (", {}".format(parseResult["rnd"]) if "rnd" in parseResult else "")
        return dump
    return SequentialPattern(
        [OpcodePattern("opc", match_predicate=match_predicate), DstPattern("dst")] +
        [OpPatterns[i]("op%d" % i) for i in range(opNum)]
        + ([OptionalPattern(LabelPattern("rnd"))] if optRounding else []),
        lambda result:
            Instruction(result["opc"],
                        use_list=sum([result["op%d" % i] for i in range(opNum)], []),
                        def_list=result["dst"],
                        dump_pattern=dumpPattern(result)))

FP_1OP_PATTERN = FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_FP])
FP_2OP_PATTERN = FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_FP]*2)
FP_3OP_PATTERN = FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_FP]*3)


# pattern with optionnal last argument rounding
FP_1OP_PATTERN_RND = FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_FP], optRounding=True)
FP_2OP_PATTERN_RND = FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_FP]*2, optRounding=True)
FP_3OP_PATTERN_RND = FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_FP]*3, optRounding=True)

LOAD_FP_PATTERN = LOAD_PATTERN(RVRegisterPattern_FP)
STORE_FP_PATTERN = STORE_PATTERN(RVRegisterPattern_FP)


RV32F_INSN_PATTERN_MATCH = {
    "fadd.s": FP_2OP_PATTERN_RND,
    "fsub.s": FP_2OP_PATTERN_RND,
    "fmul.s": FP_2OP_PATTERN_RND,
    "fdiv.s": FP_2OP_PATTERN_RND,
    "fmin.s": FP_2OP_PATTERN_RND,
    "fmax.s": FP_2OP_PATTERN_RND,

    "fsqrt.s": FP_1OP_PATTERN_RND,

    "fmadd.s" : FP_3OP_PATTERN_RND,
    "fnmadd.s": FP_3OP_PATTERN_RND,
    "fmsub.s" : FP_3OP_PATTERN_RND,
    "fnmsub.s": FP_3OP_PATTERN_RND,

    "flw": LOAD_FP_PATTERN,
    "fsw": STORE_FP_PATTERN,

    "fcvt.s.w": FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_Int], optRounding=True),
    "fcvt.s.wu": FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_Int], optRounding=True),
    "fcvt.w.s": FP_OP_PATTERN(RVRegisterPattern_Int, [RVRegisterPattern_FP], optRounding=True),
    "fcvt.wu.s": FP_OP_PATTERN(RVRegisterPattern_Int, [RVRegisterPattern_FP], optRounding=True),

    "fmv.x.s": FP_OP_PATTERN(RVRegisterPattern_Int, [RVRegisterPattern_FP]),
    "fmv.s.x": FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_Int]),
    "fmv.s": FP_1OP_PATTERN,

    "feq.s": FP_OP_PATTERN(RVRegisterPattern_Int, [RVRegisterPattern_FP]*2),
    "flt.s": FP_OP_PATTERN(RVRegisterPattern_Int, [RVRegisterPattern_FP]*2),
    "fle.s": FP_OP_PATTERN(RVRegisterPattern_Int, [RVRegisterPattern_FP]*2),

    "fsgnj.s": FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_FP]),
    "fsgnjn.s": FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_FP]),
    "fsgnjx.s": FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_FP]),

    "fclass.s": FP_OP_PATTERN(RVRegisterPattern_Int, [RVRegisterPattern_FP]),
}


RV32D_INSN_PATTERN_MATCH = {
    "fadd.d": FP_2OP_PATTERN_RND,
    "fsub.d": FP_2OP_PATTERN_RND,
    "fmul.d": FP_2OP_PATTERN_RND,
    "fdiv.d": FP_2OP_PATTERN_RND,
    "fmin.d": FP_2OP_PATTERN_RND,
    "fmax.d": FP_2OP_PATTERN_RND,

    "fsqrt.d": FP_1OP_PATTERN_RND,

    "fcvt.s.d": FP_1OP_PATTERN_RND,
    "fcvt.d.s": FP_1OP_PATTERN_RND,

    "fmadd.d" : FP_3OP_PATTERN_RND,
    "fnmadd.d": FP_3OP_PATTERN_RND,
    "fmsub.d" : FP_3OP_PATTERN_RND,
    "fnmsub.d": FP_3OP_PATTERN_RND,

    "fld": LOAD_FP_PATTERN,
    "fsd": STORE_FP_PATTERN,

    "fcvt.d.w": FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_Int], optRounding=True),
    "fcvt.d.wu": FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_Int], optRounding=True),
    "fcvt.w.d": FP_OP_PATTERN(RVRegisterPattern_Int, [RVRegisterPattern_FP], optRounding=True),
    "fcvt.wu.d": FP_OP_PATTERN(RVRegisterPattern_Int, [RVRegisterPattern_FP], optRounding=True),

    "fmv.d": FP_1OP_PATTERN,

    "feq.d": FP_OP_PATTERN(RVRegisterPattern_Int, [RVRegisterPattern_Int]*2),
    "flt.d": FP_OP_PATTERN(RVRegisterPattern_Int, [RVRegisterPattern_Int]*2),
    "fle.d": FP_OP_PATTERN(RVRegisterPattern_Int, [RVRegisterPattern_Int]*2),

    "fsgnj.d": FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_FP]),
    "fsgnjn.d": FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_FP]),
    "fsgnjx.d": FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_FP]),

    "fclass.d": FP_OP_PATTERN(RVRegisterPattern_Int, [RVRegisterPattern_FP]),
}

def isRV32IRegAllocatable(regFile, index):
    """ default allocatable list for RV32 integer registers """
    return index in [6, 7, 10, 11, 12, 13, 14, 15, 16, 17, 28, 29, 30, 31]
def isRV32FRegAllocatable(regFile, index):
    """ default allocatable list for RV32 floating-point registers """
    return index in [0, 1, 2, 3, 4, 5, 6, 7, 10, 11, 12, 13, 14, 15, 16, 17, 28, 29, 30, 31]

def isRV64IRegAllocatable(regFile, index):
    """ default allocatable list for RV64 integer registers """
    # FIXME: copy of isRV63IRegAllocatable
    return index in [6, 7, 10, 11, 12, 13, 14, 15, 16, 17, 28, 29, 30, 31]
def isRV64FRegAllocatable(regFile, index):
    """ default allocatable list for RV64 floating-point registers """
    # FIXME: copy of isRV32FRegAllocatable
    return index in [0, 1, 2, 3, 4, 5, 6, 7, 10, 11, 12, 13, 14, 15, 16, 17, 28, 29, 30, 31]

class RV_Common(Architecture):
    """ common architecture class for RISC-V """
    def getPhyRegPatternList(self):
        return [PhysicalRegisterPattern_Int, PhysicalRegisterPattern_Fp]

    def getVirtualRegClassPatternMap(self):
       REG_CLASS_PATTERN_MAP = {
           "X": VirtualRegisterPattern_Int,
           "I": VirtualRegisterPattern_Int,
           "A": VirtualRegisterPattern_Int,
           "F": VirtualRegisterPattern_Fp,
       }
       return REG_CLASS_PATTERN_MAP

class RV32(RV_Common):
    def __init__(self):
        Architecture.__init__(self,
            set([
                RegFileDescription(RVRegister.IntReg, 32, PhysicalRegister, VirtualRegister, isAllocatable=isRV32IRegAllocatable),
                RegFileDescription(RVRegister.FPReg, 32, PhysicalRegister, VirtualRegister, isAllocatable=isRV32FRegAllocatable)
            ]),
            dict(list(RV32I_INSN_PATTERN_MATCH.items()) +
                 list(RV32M_INSN_PATTERN_MATCH.items()) +
                 list(RV32F_INSN_PATTERN_MATCH.items()) +
                 list(RV32D_INSN_PATTERN_MATCH.items())
                 )
        )
        # declaring x0 as constant (=0)
        zeroReg = self.get_unique_phys_reg_object(0, RVRegister.IntReg)
        zeroReg.const = True


RV64I_EXTRA_INSN_PATTERN_MATCH = {
    # 64-bit load and store instructions
    "ld":   LOAD_INT_PATTERN,
    "sd":   STORE_INT_PATTERN,

    "slliw":  STD_1OP_1IMM_PATTERN,
    "srliw":  STD_1OP_1IMM_PATTERN,
    "sraiw":  STD_1OP_1IMM_PATTERN,

    "sllw":  STD_2OP_PATTERN,
    "srlw":  STD_2OP_PATTERN,
    "sraw":  STD_2OP_PATTERN,

    "addw":  STD_2OP_PATTERN,
    "addiw":  STD_1OP_1IMM_PATTERN,
    # alias
    "sext.w": STD_1OP_PATTERN,
}

RV64D_EXTRA_INSN_PATTERN_MATCH = {
    # FIXME: RV64D-only
    "fmv.x.d": FP_OP_PATTERN(RVRegisterPattern_Int, [RVRegisterPattern_FP]),
    "fmv.x.w": FP_OP_PATTERN(RVRegisterPattern_Int, [RVRegisterPattern_FP]),
    "fmv.w.x": FP_OP_PATTERN(RVRegisterPattern_FP, [RVRegisterPattern_Int]),
}

class RV64(RV_Common):
    def __init__(self):
        Architecture.__init__(self,
            set([
                RegFileDescription(RVRegister.IntReg, 64, PhysicalRegister, VirtualRegister, isAllocatable=isRV64IRegAllocatable),
                RegFileDescription(RVRegister.FPReg, 64, PhysicalRegister, VirtualRegister, isAllocatable=isRV64FRegAllocatable)
            ]),
            dict(list(RV32I_INSN_PATTERN_MATCH.items()) +
                 list(RV32M_INSN_PATTERN_MATCH.items()) +
                 list(RV32F_INSN_PATTERN_MATCH.items()) +
                 list(RV32D_INSN_PATTERN_MATCH.items()) +
                 list(RV64I_EXTRA_INSN_PATTERN_MATCH.items()) +
                 list(RV64D_EXTRA_INSN_PATTERN_MATCH.items())
                 )
        )
        # declaring x0 as constant (=0)
        zeroReg = self.get_unique_phys_reg_object(0, RVRegister.IntReg)
        zeroReg.const = True

if __name__ == "__main__":
    _ = RV32()
