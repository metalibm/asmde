from asmde.lexer import SpecialRegisterLexem

from asmde.parser import (
    SequentialPattern, RegisterPattern_Std,
    AddressPattern_Std,
    OpcodePattern,
    RegisterPattern_DualStd,
    RegisterPattern_Acc,
    LabelPattern,
    PhysicalRegisterPattern,
    ImmediatePattern,
    DisjonctivePattern,
)



from asmde.allocator import (
    Architecture, Instruction, RegFileDescription, Register,
    PhysicalRegister, VirtualRegister,
    SpecialRegister,
)

class SpecialRegisterPattern(PhysicalRegisterPattern):
    REG_PATTERN = "\$([\w\d_]+)"
    REG_LEXEM = SpecialRegisterLexem

    @staticmethod
    def get_unique_reg_obj(arch, tag):
        return arch.get_special_reg_object(tag)

LOAD_PATTERN = SequentialPattern(
    [OpcodePattern("opc"), RegisterPattern_Std("dst"), AddressPattern_Std("addr")],
    lambda result:
        Instruction(result["opc"],
                    use_list=(result["addr"].base + result["addr"].offset),
                    def_list=result["dst"],
                    dump_pattern=lambda color_map, use_list, def_list:
                        "{} {} = {}[{}]".format(
                            result["opc"],
                            def_list[0].instanciate(color_map),
                            use_list[1].instanciate(color_map),
                            use_list[0].instanciate(color_map))))
STORE_PATTERN = SequentialPattern(
    [OpcodePattern("opc"), AddressPattern_Std("dst_addr"), RegisterPattern_Std("src")],
    lambda result:
        Instruction(result["opc"],
                    use_list=result["src"],
                    def_list=(result["dst_addr"].base + result["dst_addr"].offset),
                    dump_pattern=lambda color_map, use_list, def_list:
                        "{} {}[{}] = {}".format(
                            result["opc"],
                            def_list[1].instanciate(color_map),
                            def_list[0].instanciate(color_map),
                            use_list[0].instanciate(color_map)
                            )))
STORE_DUAL_PATTERN = SequentialPattern(
    [OpcodePattern("opc"), AddressPattern_Std("dst_addr"), RegisterPattern_DualStd("src")],
    lambda result:
        Instruction(result["opc"],
                    use_list=result["src"],
                    def_list=(result["dst_addr"].base + result["dst_addr"].offset),
                    dump_pattern=lambda color_map, use_list, def_list:
                        "{} {}[{}] = {}".format(
                            result["opc"],
                            def_list[1].instanciate(color_map),
                            def_list[0].instanciate(color_map),
                            use_list[0].instanciate(color_map)
                            )))
STD_1OP_PATTERN = SequentialPattern(
        [OpcodePattern("opc"), RegisterPattern_Std("dst"), RegisterPattern_Std("op")],
        lambda result:
            Instruction(result["opc"],
                        use_list=(result["op"]),
                        def_list=result["dst"],
                        dump_pattern=lambda color_map, use_list, def_list: "{} {} = {}, {}".format(result["opc"], def_list[0].instanciate(color_map), use_list[0].instanciate(color_map)))
    )
CALL_1OP_PATTERN = SequentialPattern(
        [OpcodePattern("opc"), RegisterPattern_Std("op")],
        lambda result:
            Instruction(result["opc"],
                        use_list=(result["op"]),
                        dump_pattern=lambda color_map, use_list, def_list: "{} {} = {}, {}".format(result["opc"], def_list[0].instanciate(color_map), use_list[0].instanciate(color_map)))
    )
STD_IMM_PATTERN = SequentialPattern(
        [OpcodePattern("opc"), RegisterPattern_Std("dst"), ImmediatePattern("op")],
        lambda result:
            Instruction(result["opc"],
                        def_list=result["dst"],
                        dump_pattern=lambda color_map, use_list, def_list: "{} {} = {}, {}".format(result["opc"], def_list[0].instanciate(color_map), use_list[0].instanciate(color_map)))
    )
STD_1OP_1IMM_PATTERN = SequentialPattern(
        [OpcodePattern("opc"), RegisterPattern_Std("dst"), RegisterPattern_Std("op"), ImmediatePattern("imm")],
        lambda result:
            Instruction(result["opc"],
                        use_list=(result["op"]),
                        def_list=result["dst"],
                        dump_pattern=lambda color_map, use_list, def_list:
                            "{} {} = {}, {}".format(result["opc"],
                                                    def_list[0].instanciate(color_map),
                                                    use_list[0].instanciate(color_map),
                                                    result["imm"])))
STD_1OP_2IMM_PATTERN = SequentialPattern(
        [OpcodePattern("opc"), RegisterPattern_Std("dst"), RegisterPattern_Std("op"), ImmediatePattern("imm0"), ImmediatePattern("imm1")],
        lambda result:
            Instruction(result["opc"],
                        use_list=(result["op"]),
                        def_list=result["dst"],
                        dump_pattern=lambda color_map, use_list, def_list:
                            "{} {} = {}, {}".format(result["opc"],
                                                    def_list[0].instanciate(color_map),
                                                    use_list[0].instanciate(color_map),
                                                    result["imm"])))
STD_1OP_SPEC2PHY_PATTERN = SequentialPattern(
        [OpcodePattern("opc"), RegisterPattern_Std("dst"), SpecialRegisterPattern("op")],
        lambda result:
            Instruction(result["opc"],
                        use_list=(result["op"]),
                        def_list=result["dst"],
                        dump_pattern=lambda color_map, use_list, def_list: "{} {} = {}, {}".format(result["opc"], def_list[0].instanciate(color_map), use_list[0].instanciate(color_map)))
    )
STD_1OP_PHY2SPEC_PATTERN = SequentialPattern(
        [OpcodePattern("opc"), SpecialRegisterPattern("dst"), RegisterPattern_Std("op")],
        lambda result:
            Instruction(result["opc"],
                        use_list=(result["op"]),
                        def_list=result["dst"],
                        dump_pattern=lambda color_map, use_list, def_list: "{} {} = {}, {}".format(result["opc"], def_list[0].instanciate(color_map), use_list[0].instanciate(color_map)))
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
                                   dump_pattern=lambda color_map, use_list, def_list: "{} {} = {}, {}".format(result["opc"], instanciate_dual_reg(color_map, Register.Std, def_list[0:2]), use_list[0].instanciate(color_map), use_list[1].instanciate(color_map)))
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
                                   use_list=(result["dst"]),
                                   dump_pattern=lambda color_map, use_list, def_list: "goto {}".format(use_list["dst"]))
    )

NOP_PATTERN = SequentialPattern([OpcodePattern("opc")], lambda result: Instruction(result["opc"]))

KV3_INSN_PATTERN_MATCH = {
    # TODO/FIXME, rswap should consider both src/dst as used and defined
    "rswap": STD_1OP_SPEC2PHY_PATTERN,
    "get": STD_1OP_SPEC2PHY_PATTERN,
    "wfxl": STD_1OP_PHY2SPEC_PATTERN,
    "set": STD_1OP_PHY2SPEC_PATTERN,

    "icall": CALL_1OP_PATTERN,

    "make": STD_IMM_PATTERN,

    "goto": GOTO_PATTERN,
    "ld":   LOAD_PATTERN,

    "sd":   STORE_PATTERN,
    "sq":   STORE_DUAL_PATTERN,

    "addw":  STD_2OP_PATTERN,
    "sbfw":  STD_2OP_PATTERN,

    "addd":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "sbfd":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),

    "srld":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "slld":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "srad":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),

    "sbmm8":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),

    "insf":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_2IMM_PATTERN]),
    "extfz":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_2IMM_PATTERN]),

    "notd": STD_1OP_PATTERN,
    "copyd": STD_1OP_PATTERN,

    "andd":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "ord":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "xord":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),

    "movefo": MOVEFO_PATTERN,
    "movefa": MOVEFA_PATTERN,

    "nop": NOP_PATTERN,
    "rfe": NOP_PATTERN,
}

class KV3Architecture(Architecture):
    def __init__(self, std_reg_num=64, acc_reg_num=48):
        Architecture.__init__(self,
            set([
                RegFileDescription(Register.Std, std_reg_num, PhysicalRegister, VirtualRegister),
                RegFileDescription(Register.Acc, acc_reg_num, PhysicalRegister, VirtualRegister),
                RegFileDescription(Register.Special, 0, PhysicalRegister, SpecialRegister)
            ]),
            KV3_INSN_PATTERN_MATCH
        )

