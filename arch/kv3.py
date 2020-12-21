from asmde.lexer import SpecialRegisterLexem, Lexem

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
    Pattern,
    MetaPopOperatorPredicate,
    VirtualRegisterPattern,
    RegisterPattern,
)



from asmde.allocator import (
    Architecture, Instruction, RegFileDescription, Register,
    PhysicalRegister, VirtualRegister,
    SpecialRegister, SpecialRegFile,
    modulo_indexed_register,
)

class VirtualRegisterPattern_QuadReg(VirtualRegisterPattern):
    @classmethod
    def get_reg_list_from_names(VRP_Class, arch, reg_name_list, reg_type):
        assert reg_type in VRP_Class.VIRT_REG_DESCRIPTOR
        reg_list = []
        for i in range(4):
            reg = arch.get_unique_virt_reg_object(reg_name_list[i], reg_class=VRP_Class.VIRT_REG_CLASS, reg_constraint=modulo_indexed_register(4, i))
            reg_list.append(reg)
        for i in range(4):
            for j in range(3):
                linked_reg_id = (i + j) % 4
                delta_id = i - linked_reg_id
                reg_list[i].add_linked_register(reg_list[linked_reg_id], lambda color_map: [color_map[linked_reg_id] + delta_id])
        return reg_list
class VirtualRegisterPattern_QuadStd(VirtualRegisterPattern_QuadReg):
    VIRT_REG_CLASS = Register.Std
    VIRT_REG_DESCRIPTOR = "Q"

class PhysicalRegisterPattern_QuadStd(PhysicalRegisterPattern):
    REG_PATTERN = "\$([r][0-9]+){4}"

    @staticmethod
    def get_unique_reg_obj(arch, index):
        return arch.get_unique_phys_reg_object(index, PhysicalRegister.Std)

class RegisterPattern_QuadStd(RegisterPattern):
    VIRTUAL_PATTERN_CLASS = VirtualRegisterPattern_QuadStd
    PHYSICAL_PATTERN_CLASS = PhysicalRegisterPattern_QuadStd

class RegisterPattern_SubAcc(RegisterPattern_Acc):
    @classmethod
    def parse(PRP_Class, arch, lexem_list):
        acc_reg, lexem_list = RegisterPattern_Acc.parse(arch, lexem_list)
        if len(lexem_list) and isinstance(lexem_list[0], Lexem) and lexem_list[0].value in ["_lo", "_hi"]:
            # TODO/FIXME: wrongly generating a full acc register when only a sub-part
            # should be considered
            return acc_reg, lexem_list[1:]
        return None

class SpecialRegisterPattern(PhysicalRegisterPattern):
    REG_PATTERN = "\$([\w\d_]+)"
    REG_LEXEM = SpecialRegisterLexem

    @staticmethod
    def get_unique_reg_obj(arch, tag):
        return arch.get_special_reg_object(tag)

class Predicate:
    def __init__(self, specifier):
        self.specifier = specifier

class PredicatePattern(Pattern):
    """ pattern for address offset """
    @staticmethod
    def parse(arch, lexem_list):
        lexem_list = MetaPopOperatorPredicate(".")(lexem_list)
        if isinstance(lexem_list[0], Lexem):
            return Predicate(lexem_list[0].value), lexem_list[1:]
        return None

COMP_IMM_PATTERN = SequentialPattern(
    [OpcodePattern("opc"), PredicatePattern("pred"), RegisterPattern_Std("dst"), RegisterPattern_Std("lhs"), ImmediatePattern("imm")],
    lambda result:
        Instruction(result["opc"] + "." + result["pred"].specifier,
                    match_pattern="imm",
                    use_list=(result["lhs"]),
                    def_list=result["dst"],
                    dump_pattern=lambda color_map, use_list, def_list:
                        "{} {} = {}, {}".format(
                            result["opc"] + "." + result["pred"].specifier,
                            def_list[0].instanciate(color_map),
                            use_list[0].instanciate(color_map),
                            result["imm"])))

COMP_OP_PATTERN = SequentialPattern(
    [OpcodePattern("opc"), PredicatePattern("pred"), RegisterPattern_Std("dst"), RegisterPattern_Std("lhs"), RegisterPattern_Std("rhs")],
    lambda result:
        Instruction(result["opc"] + "." + result["pred"].specifier,
                    use_list=(result["lhs"] + result["rhs"]),
                    def_list=result["dst"],
                    dump_pattern=lambda color_map, use_list, def_list:
                        "{} {} = {}, {}".format(
                            result["opc"] + "." + result["pred"].specifier,
                            def_list[0].instanciate(color_map),
                            use_list[0].instanciate(color_map),
                            use_list[1].instanciate(color_map))))

CMOVE_OP_PATTERN = SequentialPattern(
    [OpcodePattern("opc"), PredicatePattern("pred"), RegisterPattern_Std("cond"), RegisterPattern_Std("dst"), RegisterPattern_Std("src")],
    lambda result:
        Instruction(result["opc"] + "." + result["pred"].specifier,
                    use_list=(result["cond"] + result["src"]),
                    def_list=result["dst"],
                    dump_pattern=lambda color_map, use_list, def_list:
                        "{} {} ? {} = {}".format(
                            result["opc"] + "." + result["pred"].specifier,
                            use_list[0].instanciate(color_map),
                            def_list[0].instanciate(color_map),
                            use_list[1].instanciate(color_map))))

CMOVE_IMM_PATTERN = SequentialPattern(
    [OpcodePattern("opc"), PredicatePattern("pred"), RegisterPattern_Std("cond"), RegisterPattern_Std("dst"), ImmediatePattern("imm")],
    lambda result:
        Instruction(result["opc"] + "." + result["pred"].specifier,
                    match_pattern="imm",
                    use_list=(result["cond"]),
                    def_list=result["dst"],
                    dump_pattern=lambda color_map, use_list, def_list:
                        "{} {} ? {} = {}".format(
                            result["opc"] + "." + result["pred"].specifier,
                            use_list[0].instanciate(color_map),
                            def_list[0].instanciate(color_map),
                            result["imm"])))
def LOAD_PATTERN_TEMPLATE(DstRegClass=RegisterPattern_Std):
    return SequentialPattern(
        [OpcodePattern("opc", match_predicate=True), DstRegClass("dst"), AddressPattern_Std("addr")],
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

LOAD_PATTERN = LOAD_PATTERN_TEMPLATE(RegisterPattern_Std)
LOAD_ACC_PATTERN = LOAD_PATTERN_TEMPLATE(RegisterPattern_Acc)
LOAD_DUAL_PATTERN = LOAD_PATTERN_TEMPLATE(RegisterPattern_DualStd)
LOAD_QUAD_PATTERN = LOAD_PATTERN_TEMPLATE(RegisterPattern_QuadStd)

def LOAD_COND_PATTERN_TEMPLATE(DstRegClass=RegisterPattern_Std):
    return SequentialPattern(
        [OpcodePattern("opc", match_predicate=True), RegisterPattern_Std("cond"), DstRegClass("dst"), AddressPattern_Std("addr")],
        lambda result:
            Instruction(result["opc"],
                        use_list=(result["cond"] + result["addr"].base + result["addr"].offset),
                        def_list=result["dst"],
                        dump_pattern=lambda color_map, use_list, def_list:
                            "{} {} ? {} = {}[{}]".format(
                                result["opc"],
                                use_list[0].instanciate(color_map),
                                def_list[0].instanciate(color_map),
                                use_list[2].instanciate(color_map),
                                use_list[1].instanciate(color_map))))

DINVALL_PATTERN = SequentialPattern(
    [OpcodePattern("opc", match_predicate=True), AddressPattern_Std("addr")],
    lambda result:
        Instruction(result["opc"],
                    use_list=(result["addr"].base + result["addr"].offset),
                    dump_pattern=lambda color_map, use_list, def_list:
                        "{} {}[{}]".format(
                            result["opc"],
                            use_list[1].instanciate(color_map),
                            use_list[0].instanciate(color_map))))



def STORE_PATTERN_TEMPLATE(SrcRegClass=RegisterPattern_Std):
    return SequentialPattern(
        [OpcodePattern("opc", match_predicate=True), AddressPattern_Std("dst_addr"), SrcRegClass("src")],
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

STORE_PATTERN = STORE_PATTERN_TEMPLATE(RegisterPattern_Std)
STORE_ACC_PATTERN = STORE_PATTERN_TEMPLATE(RegisterPattern_Acc)
STORE_DUAL_PATTERN = STORE_PATTERN_TEMPLATE(RegisterPattern_DualStd)
STORE_QUAD_PATTERN = STORE_PATTERN_TEMPLATE(RegisterPattern_QuadStd)

def STORE_COND_PATTERN_TEMPLATE(SrcRegClass=RegisterPattern_Std):
    return SequentialPattern(
        [OpcodePattern("opc", match_predicate=True), RegisterPattern_Std("cond"), AddressPattern_Std("dst_addr"), SrcRegClass("src")],
        lambda result:
            Instruction(result["opc"],
                        use_list=(result["cond"] + result["src"]),
                        def_list=(result["dst_addr"].base + result["dst_addr"].offset),
                        dump_pattern=lambda color_map, use_list, def_list:
                            "{} {} ? {}[{}] = {}".format(
                                result["opc"],
                                use_list[0].instanciate(color_map),
                                def_list[1].instanciate(color_map),
                                def_list[0].instanciate(color_map),
                                use_list[1].instanciate(color_map)
                                )))

STORE_COND_PATTERN = STORE_COND_PATTERN_TEMPLATE(RegisterPattern_Std)
STORE_COND_ACC_PATTERN = STORE_COND_PATTERN_TEMPLATE(RegisterPattern_Acc)
STORE_COND_DUAL_PATTERN = STORE_COND_PATTERN_TEMPLATE(RegisterPattern_DualStd)
STORE_COND_QUAD_PATTERN = STORE_COND_PATTERN_TEMPLATE(RegisterPattern_QuadStd)

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
                        dump_pattern=lambda color_map, use_list, def_list: "{} {}".format(result["opc"], use_list[0].instanciate(color_map)))
    )
CALL_IMM_PATTERN = SequentialPattern(
        [OpcodePattern("opc"), ImmediatePattern("imm")],
        lambda result:
            Instruction(result["opc"],
                        match_pattern="imm",
                        dump_pattern=lambda color_map, use_list, def_list: "{} {}".format(result["opc"], result["imm"])))
    
STD_IMM_PATTERN = SequentialPattern(
        [OpcodePattern("opc"), RegisterPattern_Std("dst"), ImmediatePattern("op")],
        lambda result:
            Instruction(result["opc"],
                        match_pattern="imm",
                        def_list=result["dst"],
                        dump_pattern=lambda color_map, use_list, def_list: "{} {} = {}, {}".format(result["opc"], def_list[0].instanciate(color_map), use_list[0].instanciate(color_map)))
    )
STD_1OP_1IMM_PATTERN = SequentialPattern(
        [OpcodePattern("opc"), RegisterPattern_Std("dst"), RegisterPattern_Std("op"), ImmediatePattern("imm")],
        lambda result:
            Instruction(result["opc"],
                        match_pattern="imm",
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

# TODO/FIXME: acc must be the same register for input and output
STD_2OP_ACC_PATTERN = SequentialPattern(
        [OpcodePattern("opc"), RegisterPattern_Std("acc"), RegisterPattern_Std("lhs"), RegisterPattern_Std("rhs")],
        lambda result:
            Instruction(result["opc"],
                        use_list=(result["acc"], result["lhs"] + result["rhs"]),
                        def_list=result["acc"],
                        dump_pattern=lambda color_map, use_list, def_list: "{} {} = {}, {}".format(result["opc"], def_list[0].instanciate(color_map), use_list[0].instanciate(color_map), use_list[1].instanciate(color_map)))
    )

STD_2OP_DUAL_RESULT_PATTERN = SequentialPattern(
        [OpcodePattern("opc"), RegisterPattern_DualStd("dst"), RegisterPattern_Std("lhs"), RegisterPattern_Std("rhs")],
        lambda result:
            Instruction(result["opc"],
                        use_list=(result["lhs"] + result["rhs"]),
                        def_list=result["dst"],
                        dump_pattern=lambda color_map, use_list, def_list:
                            "{} {} = {}, {}".format(
                                result["opc"],
                                def_list[0].instanciate(color_map),
                                use_list[0].instanciate(color_map),
                                use_list[1].instanciate(color_map))))


DUAL_2OP_PATTERN = SequentialPattern(
        [OpcodePattern("opc"), RegisterPattern_DualStd("dst"), RegisterPattern_DualStd("lhs"), RegisterPattern_DualStd("rhs")],
        lambda result: Instruction(result["opc"], use_list=(result["lhs"] + result["rhs"]), def_list=result["dst"], 
                                   dump_pattern=lambda color_map, use_list, def_list: "{} {} = {}, {}".format(result["opc"], instanciate_dual_reg(color_map, Register.Std, def_list[0:2]), use_list[0].instanciate(color_map), use_list[1].instanciate(color_map)))
    )

# FIXME: add support for sub-register part selector
MOVETQ_PATTERN = SequentialPattern(
        [OpcodePattern("opc"), RegisterPattern_SubAcc("dst"), RegisterPattern_Std("lhs"), RegisterPattern_Std("rhs")],
        lambda result: Instruction(
                            result["opc"],
                            use_list=(result["lhs"] + result["rhs"]),
                            def_list=result["dst"],
                            dump_pattern=lambda color_map, use_list, def_list:
                                "{} {} = {}, {}".format(
                                    result["opc"],
                                    def_list[0].instanciate(color_map),
                                    use_list[0].instanciate(color_map), use_list[1].instanciate(color_map))))

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

BRANCH_PATTERN = SequentialPattern(
        [OpcodePattern("opc", match_predicate=True), RegisterPattern_Std("cond"), LabelPattern("dst")],
        lambda result: Instruction(result["opc"], is_jump=True,
                                   use_list=(result["cond"]),
                                   dump_pattern=lambda color_map, use_list, def_list:
                                        "{} {} ? {}".format(result["opc"], use_list[0].instanciate(color_map), use_list["dst"])
                                    ))

NOP_PATTERN = SequentialPattern([OpcodePattern("opc")], lambda result: Instruction(result["opc"]))

STD_2OP_OR_1OP1IMM_PATTERN = DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN])
COMP_PATTERN = DisjonctivePattern([COMP_OP_PATTERN, COMP_IMM_PATTERN])

KV3_INSN_PATTERN_MATCH = {
    # TODO/FIXME, rswap should consider both src/dst as used and defined
    "rswap": STD_1OP_SPEC2PHY_PATTERN,
    "get": STD_1OP_SPEC2PHY_PATTERN,
    "wfxl": STD_1OP_PHY2SPEC_PATTERN,
    "wfxm": STD_1OP_PHY2SPEC_PATTERN,
    "set": STD_1OP_PHY2SPEC_PATTERN,

    "iget": CALL_1OP_PATTERN,
    "icall": CALL_1OP_PATTERN,
    "scall": DisjonctivePattern([CALL_1OP_PATTERN, CALL_IMM_PATTERN]),
    "igoto": CALL_1OP_PATTERN,
    "call": GOTO_PATTERN,

    "make": STD_IMM_PATTERN,
    "pcrel": STD_IMM_PATTERN,

    "goto": GOTO_PATTERN,
    "cb": BRANCH_PATTERN,
    "loopdo": BRANCH_PATTERN,

    "lbz":   DisjonctivePattern([LOAD_PATTERN, LOAD_COND_PATTERN_TEMPLATE(RegisterPattern_Std)]),
    "lbs":   DisjonctivePattern([LOAD_PATTERN, LOAD_COND_PATTERN_TEMPLATE(RegisterPattern_Std)]),
    "lhz":   DisjonctivePattern([LOAD_PATTERN, LOAD_COND_PATTERN_TEMPLATE(RegisterPattern_Std)]),
    "lhs":   DisjonctivePattern([LOAD_PATTERN, LOAD_COND_PATTERN_TEMPLATE(RegisterPattern_Std)]),
    "lwz":   DisjonctivePattern([LOAD_PATTERN, LOAD_COND_PATTERN_TEMPLATE(RegisterPattern_Std)]),
    "lws":   DisjonctivePattern([LOAD_PATTERN, LOAD_COND_PATTERN_TEMPLATE(RegisterPattern_Std)]),
    "ld":    DisjonctivePattern([LOAD_PATTERN, LOAD_COND_PATTERN_TEMPLATE(RegisterPattern_Std)]),
    "lq":   DisjonctivePattern([LOAD_DUAL_PATTERN, LOAD_COND_PATTERN_TEMPLATE(RegisterPattern_DualStd)]),
    "lo":   DisjonctivePattern([LOAD_QUAD_PATTERN, LOAD_COND_PATTERN_TEMPLATE(RegisterPattern_QuadStd)]),

    "sb":   DisjonctivePattern([STORE_PATTERN, STORE_COND_PATTERN]),
    "sh":   DisjonctivePattern([STORE_PATTERN, STORE_COND_PATTERN]),
    "sw":   DisjonctivePattern([STORE_PATTERN, STORE_COND_PATTERN]),
    "sd":   DisjonctivePattern([STORE_PATTERN, STORE_COND_PATTERN]),
    "sq":   DisjonctivePattern([STORE_DUAL_PATTERN, STORE_COND_DUAL_PATTERN]),
    "so":   DisjonctivePattern([STORE_QUAD_PATTERN, STORE_COND_QUAD_PATTERN]),

    "lv":   DisjonctivePattern([LOAD_ACC_PATTERN, LOAD_COND_PATTERN_TEMPLATE(RegisterPattern_Acc)]),
    "sv":   DisjonctivePattern([STORE_ACC_PATTERN, STORE_COND_ACC_PATTERN]),

    "acswapd":   STORE_DUAL_PATTERN,
    "acswapw":   STORE_DUAL_PATTERN,
    "aladdd":   STORE_PATTERN,
    "alclrd": LOAD_PATTERN,
    "alclrw": LOAD_PATTERN,

    "compd": DisjonctivePattern([COMP_OP_PATTERN, COMP_IMM_PATTERN]),
    "compw": DisjonctivePattern([COMP_OP_PATTERN, COMP_IMM_PATTERN]),

    "cmoved": DisjonctivePattern([CMOVE_OP_PATTERN, CMOVE_IMM_PATTERN]),

    "maxw":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "minw":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "maxd":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "mind":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),

    "maxud":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "minud":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),

    "maxuw":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "minuw":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),

    "addw":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "sbfw":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "addwd":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "sbfwd":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "sbfuwd":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "adduwd":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "negw": STD_1OP_PATTERN,

    "addwp":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "sbfwp":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),

    "fabsw": STD_1OP_PATTERN,
    "fabsd": STD_1OP_PATTERN,
    "fabswp": STD_1OP_PATTERN,

    "fwidenlwd": STD_1OP_PATTERN,
    "fwidenmwd": STD_1OP_PATTERN,
    "fnarrowdw": STD_1OP_PATTERN,
    "fwidenlwd": STD_1OP_PATTERN,

    "floatw": COMP_PATTERN,
    "floatuw": COMP_PATTERN,
    "fixedw": COMP_PATTERN,
    "fixeduw": COMP_PATTERN,

    "floatd": COMP_PATTERN,
    "floatud": COMP_PATTERN,
    "fixedd": COMP_PATTERN,
    "fixedud": COMP_PATTERN,

    "fnegw": STD_1OP_PATTERN,
    "fnegwp": STD_1OP_PATTERN,
    "fnegd": STD_1OP_PATTERN,

    "fmaxw": STD_2OP_PATTERN,
    "fminw": STD_2OP_PATTERN,
    "fmaxwp": STD_2OP_PATTERN,
    "fminwp": STD_2OP_PATTERN,

    "fsbfw": STD_2OP_PATTERN,
    "faddw": STD_2OP_PATTERN,
    "fmulw": STD_2OP_PATTERN,
    "fmulwc": STD_2OP_PATTERN,
    "fmulcwc": STD_2OP_PATTERN,

    "fsbfwd": STD_2OP_PATTERN,
    "faddwd": STD_2OP_PATTERN,
    "fmulwd": STD_2OP_PATTERN,

    "fsbfwp": STD_2OP_PATTERN,
    "faddwp": STD_2OP_PATTERN,
    "fmulwp": STD_2OP_PATTERN,

    "fsbfd": STD_2OP_PATTERN,
    "faddd": STD_2OP_PATTERN,
    "fmuld": STD_2OP_PATTERN,

    "fsbfdp": DUAL_2OP_PATTERN,
    "fadddp": DUAL_2OP_PATTERN,

    "ffmaw": STD_2OP_ACC_PATTERN,
    "ffmawd": STD_2OP_ACC_PATTERN,
    "ffmad": STD_2OP_ACC_PATTERN,

    "ffmsw": STD_2OP_ACC_PATTERN,
    "ffmswd": STD_2OP_ACC_PATTERN,
    "ffmsd": STD_2OP_ACC_PATTERN,

    "ffmawp": STD_2OP_ACC_PATTERN,
    "ffmswp": STD_2OP_ACC_PATTERN,

    "fmulwq": DUAL_2OP_PATTERN,
    "faddwq": DUAL_2OP_PATTERN,
    "fsbfwq": DUAL_2OP_PATTERN,

    "frecw": STD_1OP_PATTERN,
    "frecwp": STD_1OP_PATTERN,

    "fcompw": DisjonctivePattern([COMP_OP_PATTERN, COMP_IMM_PATTERN]),
    "fcompd": DisjonctivePattern([COMP_OP_PATTERN, COMP_IMM_PATTERN]),

    "srlw":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "srsw":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "sllw":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "sraw":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "rorw":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "rolw":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),

    "srlwps":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "srswps":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "sllwps":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "srawps":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "rorwps":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "rolwps":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),

    "absw": STD_1OP_PATTERN,
    "abswp": STD_1OP_PATTERN,
    "absd": STD_1OP_PATTERN,

    "abdw": STD_2OP_PATTERN,
    "abdd": STD_2OP_PATTERN,

    "negd": STD_1OP_PATTERN,
    "addd":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "sbfd":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),

    "stsud": STD_2OP_PATTERN,

    "addx2d":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "addx4d":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "addx8d":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "addx16d":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),

    "addx2w":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "addx4w":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "addx8w":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "addx16w":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),

    "sbfx2d":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "sbfx4d":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "sbfx8d":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "sbfx16d":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),

    "sbfx2w":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "sbfx4w":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "sbfx8w":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "sbfx16w":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),

    "muld":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "mulwd":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "muluwd":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "mulw":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),

    "mulw":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "mulsuwd":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),

    "maddw": STD_2OP_ACC_PATTERN,
    "madduw": STD_2OP_ACC_PATTERN,
    "msbfw": STD_2OP_ACC_PATTERN,

    "madduwd": STD_2OP_ACC_PATTERN,
    "maddwd": STD_2OP_ACC_PATTERN,
    "msbfwd": STD_2OP_ACC_PATTERN,
    "msbfuwd": STD_2OP_ACC_PATTERN,

    "maddd": STD_2OP_ACC_PATTERN,
    "msbfd": STD_2OP_ACC_PATTERN,

    "muludt": STD_2OP_DUAL_RESULT_PATTERN,
    "muldt": STD_2OP_DUAL_RESULT_PATTERN,

    "srld":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "srsd":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "slld":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "srad":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "rord":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "rold":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),

    "sbmm8":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "sbmmt8":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),

    "insf":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_2IMM_PATTERN]),
    "extfz":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_2IMM_PATTERN]),
    "extfs":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_2IMM_PATTERN]),

    "ctzd": STD_1OP_PATTERN,
    "ctzw": STD_1OP_PATTERN,
    "clzd": STD_1OP_PATTERN,
    "clzw": STD_1OP_PATTERN,

    "cbsd": STD_1OP_PATTERN,
    "cbsw": STD_1OP_PATTERN,

    "zxbd": STD_1OP_PATTERN,
    "zxhd": STD_1OP_PATTERN,
    "zxwd": STD_1OP_PATTERN,
    "sxbd": STD_1OP_PATTERN,
    "sxhd": STD_1OP_PATTERN,
    "sxwd": STD_1OP_PATTERN,

    "notd": STD_1OP_PATTERN,
    "copyd": STD_1OP_PATTERN,

    "notw": STD_1OP_PATTERN,
    "copyw": STD_1OP_PATTERN,

    "copyq": STD_2OP_DUAL_RESULT_PATTERN,

    "andd":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "andnd":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "ord":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "nord":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "ornd":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "xord":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "nandd":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),

    "lnandd":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "landd":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),

    "lnorw":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "lorw":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "ornw":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),

    "andw":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "nandw":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "andnw":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "orw":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "norw":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "xorw":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),
    "nxorw":  DisjonctivePattern([STD_2OP_PATTERN, STD_1OP_1IMM_PATTERN]),

    "movetq": MOVETQ_PATTERN,
    "movefa": MOVEFA_PATTERN,

    "nop": NOP_PATTERN,
    "fence": NOP_PATTERN,
    "await": NOP_PATTERN,
    "dinval": NOP_PATTERN,
    "dinvall": DINVALL_PATTERN,
    "dzerol": DINVALL_PATTERN,
    "iinval": NOP_PATTERN,
    "barrier": NOP_PATTERN,
    "stop": NOP_PATTERN,
    "errop": NOP_PATTERN,
    "tlbwrite": NOP_PATTERN,
    "tlbprobe": NOP_PATTERN,

    "rfe": NOP_PATTERN,
    "ret": NOP_PATTERN,

    "dtouchl": DINVALL_PATTERN,
    "iinvals": DINVALL_PATTERN,
}

class KV3Architecture(Architecture):
    def __init__(self, std_reg_num=64, acc_reg_num=48):
        Architecture.__init__(self,
            set([
                RegFileDescription(Register.Std, std_reg_num, PhysicalRegister, VirtualRegister),
                RegFileDescription(Register.Acc, acc_reg_num, PhysicalRegister, VirtualRegister),
                RegFileDescription(Register.Special, 0, PhysicalRegister, SpecialRegister, reg_file_class=SpecialRegFile)
            ]),
            KV3_INSN_PATTERN_MATCH
        )

