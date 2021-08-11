from asmde.allocator import Instruction, Architecture, RegFileDescription, Register, PhysicalRegister, VirtualRegister

from asmde.parser import (
    SequentialPattern,
    OpcodePattern, RegisterPattern_Std, AddressPattern_Std,
    RegisterPattern_DualStd, RegisterPattern_Acc,
    LabelPattern
)

def instanciate_dual_reg(color_map, reg_class, reg_list):
    """ Instanciate a pair of registers formed by the registers in reg_list """
    instanciated_list = [reg.instanciate(color_map) for reg in reg_list]
    return reg_class.build_multi_reg(instanciated_list)


LOAD_PATTERN = SequentialPattern(
    [OpcodePattern("opc"), RegisterPattern_Std("dst"), AddressPattern_Std("addr")],
    lambda result:
        Instruction(result["opc"],
                    use_list=(result["addr"].base + result["addr"].offset),
                    def_list=result["dst"],
                    dump_pattern=lambda color_map, use_list, def_list: "ld {} = {}[{}]".format(def_list[0].instanciate(color_map), use_list[1].instanciate(color_map), use_list[0].instanciate(color_map)))
)
STD_2OP_PATTERN = SequentialPattern(
        [OpcodePattern("opc"), RegisterPattern_Std("dst"), RegisterPattern_Std("lhs"), RegisterPattern_Std("rhs")],
        lambda result:
            Instruction(result["opc"],
                        use_list=(result["lhs"] + result["rhs"]),
                        def_list=result["dst"],
                        dump_pattern=lambda color_map, use_list, def_list: "add {} = {}, {}".format(def_list[0].instanciate(color_map), use_list[0].instanciate(color_map), use_list[1].instanciate(color_map)))
    )
DUAL_2OP_PATTERN = SequentialPattern(
        [OpcodePattern("opc"), RegisterPattern_DualStd("dst"), RegisterPattern_Std("lhs"), RegisterPattern_Std("rhs")],
        lambda result: Instruction(result["opc"], use_list=(result["lhs"] + result["rhs"]), def_list=result["dst"], 
                                   dump_pattern=lambda color_map, use_list, def_list: "addd {} = {}, {}".format(instanciate_dual_reg(color_map, Register.Std, def_list[0:2]), use_list[0].instanciate(color_map), use_list[1].instanciate(color_map)))
    )
MOVEFO_PATTERN = SequentialPattern(
        [OpcodePattern("opc"), RegisterPattern_Acc("dst"), RegisterPattern_Std("lhs"), RegisterPattern_Std("rhs")],
        lambda result: Instruction(result["opc"], use_list=(result["lhs"] + result["rhs"]), def_list=result["dst"],
                                   dump_pattern=lambda color_map, use_list, def_list: "movefo {} = {}, {}".format(def_list[0].instanciate(color_map), use_list[0].instanciate(color_map), use_list[1].instanciate(color_map)))
    )
MOVEFA_PATTERN = SequentialPattern(
        [OpcodePattern("movefa"), RegisterPattern_Std("dst"), RegisterPattern_Acc("src")],
        lambda result: Instruction("movefo", use_list=(result["src"]), def_list=result["dst"],
                                   dump_pattern=lambda color_map, use_list, def_list: "movefa {} = {}".format(def_list[0].instanciate(color_map), use_list[0].instanciate(color_map)))
    )

GOTO_PATTERN = SequentialPattern(
        [OpcodePattern("opc"), LabelPattern("dst")],
        lambda result: Instruction(result["opc"], is_jump=True,
                                   dump_pattern=lambda color_map, use_list, def_list: "goto {}".format(use_list["dst"]))
    )

INSN_PATTERN_MATCH = {
    "ld":   LOAD_PATTERN,

    "add":  STD_2OP_PATTERN,
    "sbf":  STD_2OP_PATTERN,

    "addd":  DUAL_2OP_PATTERN,
    "sbfd":  DUAL_2OP_PATTERN,

    "movefo": MOVEFO_PATTERN,
    "movefa": MOVEFA_PATTERN,
}

class DummyArchitecture(Architecture):
    def __init__(self, std_reg_num=16, acc_reg_num=16):
        Architecture.__init__(self,
            set([
                RegFileDescription(Register.Std, std_reg_num, PhysicalRegister, VirtualRegister),
                RegFileDescription(Register.Acc, acc_reg_num, PhysicalRegister, VirtualRegister)
            ]),
            INSN_PATTERN_MATCH
        )

    def hasBundle(self):
        return True

