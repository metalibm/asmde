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
        reg_prefix = "a"
    class FPReg(Register.RegClass):
        """ Floating-point register """
        name = "Fp"
        prefix = ""
        reg_prefix = "f"


class VirtualRegisterPattern_Int(VirtualRegisterPattern_SingleReg):
    """ RISC-V Integer Virtual register """
    VIRT_REG_CLASS = RVRegister.IntReg
    VIRT_REG_DESCRIPTOR = "I"
class PhysicalRegisterPattern_Int(PhysicalRegisterPattern):
    """ RISC-V Integer Physical register """
    REG_PATTERN = "(a[0-9]+)"#{1,4}"
    REG_CLASS = RVRegister.IntReg
    REG_LEXEM = Lexem

class VirtualRegisterPattern_Fp(VirtualRegisterPattern_SingleReg):
    """ RISC-V Floating-Point Virtual register """
    VIRT_REG_CLASS = RVRegister.FPReg
    VIRT_REG_DESCRIPTOR = "F"
class PhysicalRegisterPattern_Fp(PhysicalRegisterPattern):
    """ RISC-V Floating-Pooint Physical register """
    REG_PATTERN = "(f[0-9]+)"#{1,4}"
    REG_CLASS = RVRegister.FPReg
    REG_LEXEM = Lexem

class RVRegisterPattern_Int(RegisterPattern):
    VIRTUAL_PATTERN_CLASS = VirtualRegisterPattern_Int
    PHYSICAL_PATTERN_CLASS = PhysicalRegisterPattern_Int

class RVOffsetPattern_Std(GenericOffsetPattern):
    """ pattern for address offset """
    OffsetPhysicalRegisterClass = PhysicalRegisterPattern_Int
    OffsetVirtuallRegisterClass = VirtualRegisterPattern_Int

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
        return "{} {}, {}({})".format(parseResult["opc"],
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


LOAD_PATTERN = SequentialPattern(
    [OpcodePattern("opc"), RVRegisterPattern_Int("dst"),
     RVAddressPattern_Std("addr")],
    lambda result:
        Instruction(result["opc"],
                    use_list=(result["addr"].base + result["addr"].offset),
                    def_list=result["dst"],
                    dump_pattern=loadDumpPattern(result)))

STORE_PATTERN = SequentialPattern(
    [OpcodePattern("opc"),
     RVRegisterPattern_Int("src"),
     RVAddressPattern_Std("addr")],
    lambda result:
        Instruction(result["opc"],
                    use_list=(result["src"] + result["addr"].base + result["addr"].offset),
                    dump_pattern=storeDumpPattern(result)))

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

GOTO_PATTERN = SequentialPattern(
        [OpcodePattern("opc"), LabelPattern("dst")],
        lambda result: Instruction(result["opc"], is_jump=True,
                                   dump_pattern=lambda color_map, use_list, def_list: "goto {}".format(use_list["dst"]))
    )

RV32_INSN_PATTERN_MATCH = {
    # load and store instructions
    "lb":   LOAD_PATTERN,
    "lh":   LOAD_PATTERN,
    "lw":   LOAD_PATTERN,
    "lbu":   LOAD_PATTERN,
    "lhu":   LOAD_PATTERN,
    "sb":   STORE_PATTERN,
    "sh":   STORE_PATTERN,
    "sw":   STORE_PATTERN,

    # arithmetic instructions
    "add":  STD_2OP_PATTERN,
    "addi":  STD_1OP_1IMM_PATTERN,
    "sub":  STD_2OP_PATTERN,

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
}

class RV32(Architecture):
    def __init__(self):
        Architecture.__init__(self,
            set([
                RegFileDescription(RVRegister.IntReg, 32, PhysicalRegister, VirtualRegister),
                RegFileDescription(RVRegister.FPReg, 32, PhysicalRegister, VirtualRegister)
            ]),
            RV32_INSN_PATTERN_MATCH
        )

    def getPhyRegPatternList(self):
        return [PhysicalRegisterPattern_Int]

    def getVirtualRegClassPatternMap(self):
       REG_CLASS_PATTERN_MAP = {
           "X": VirtualRegisterPattern_Int,
           "A": VirtualRegisterPattern_Int,
           "F": VirtualRegisterPattern_Fp,
       }
       REG_CLASS_PATTERN_MAP = arch.getVirtualRegClassPatternMap()
