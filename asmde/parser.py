# -*- coding: utf-8 -*-

import re
import sys
import argparse
import collections

import lexer

from lexer import (
    Lexem, RegisterLexem,
    LabelEndLexem, CommentHeadLexem,
    ImmediateLexem, OperatorLexem,
    BundleSeparatorLexem, MacroLexem,
)

from allocator import (
    Register, PhysicalRegister, ImmediateValue,
    VirtualRegister,
    DebugObject, Instruction, Bundle,
    RegFileDescription, RegFile, Architecture,
    BasicBlock, Program,
    even_indexed_register,
    odd_indexed_register,

    RegisterAssignator,
)


def NextLexem_OperatorPredicate(op_value):
    """ construct a predicate: lexem_list -> boolean
        which checks if the next lexem is an operator whose value macthes
        @p op_value (do not consume it) """
    def predicate(lexem_list):
        if len(lexem_list) == 0:
            return False
        head_lexem = lexem_list[0]
        return isinstance(head_lexem, OperatorLexem) and head_lexem.value == op_value
    return predicate

def MetaPopOperatorPredicate(op_value):
    """ construct a predicate: lexem_list -> boolean / lexem_list
        which checks if the next lexem is an operator whose value macthes
        @p op_value, consumes it if it macth and return the remaining lexem list,
        if it does not, the functions returns False (no lexem list) """
    def predicate(lexem_list):
        lexem = lexem_list[0]
        if not isinstance(lexem, OperatorLexem) or lexem.value != op_value:
            raise Exception(" expecting operator {}, got {}".format(op_value, lexem)) 
            return False
        return lexem_list[1:]
    return predicate


class Pattern:
    def __init__(self, tag):
        # pattern identifier used to distinguish between pattern instances
        self.tag = tag

    def parse(self, arch, lexem_list):
        """ parse @p lexem_list assuming it must match pattern.
            If it does not, returns None,
            Else return a tuple (match result, remaining lexems list) """
        raise NotImplementedError

class VirtualRegisterPattern(Pattern):
    VIRT_REG_DESCRIPTOR = "RDQOABCD"
    VIRT_REG_CLASS = {
            "R": Register.Std,
            "A": Register.Acc
    }
    @classmethod
    def parse(VRP_Class, arch, lexem_list):
        """ Try to parse a virtual register description for @p lexem_list
            return a pair with:
            - the list (most likely a single element) of virtual register
              encoded in lexem
            - a list of remaining lexems """
        if len(lexem_list) == 0:
            return None
        virtual_register_type_lexem = lexem_list[0]
        lexem_list = lexem_list[1:]
        reg_type = virtual_register_type_lexem.value

        if not isinstance(virtual_register_type_lexem, Lexem) or not reg_type in VRP_Class.VIRT_REG_DESCRIPTOR:#"RDQOABCD":
            # fail to match
            return None

        lexem_list = MetaPopOperatorPredicate("(")(lexem_list)

        reg_name_list = []
        while isinstance(lexem_list[0], Lexem) and lexem_list[0].value != ")":
            reg_name_list.append(lexem_list[0].value)
            lexem_list = lexem_list[1:]

        lexem_list = MetaPopOperatorPredicate(")")(lexem_list)

        reg_list = VRP_Class.get_reg_list_from_names(arch, reg_name_list, reg_type)
        return reg_list, lexem_list

    @classmethod
    def get_reg_list_from_names(VRP_Class, arch, reg_name_list, reg_type):
        raise NotImplementedError

class VirtualRegisterPattern_Any(VirtualRegisterPattern):
    @classmethod
    def get_reg_list_from_names(VRP_Class, arch, reg_name_list, reg_type):
        REG_CLASS_PATTERN_MAP = {
            "R": VirtualRegisterPattern_Std,
            "A": VirtualRegisterPattern_Acc,
            "D": VirtualRegisterPattern_DualStd,
        }
        if not reg_type in REG_CLASS_PATTERN_MAP:
            print("reg_type {} not found in REG_CLASS_PATTERN_MAP (name list: {})".format(reg_typ, reg_name_list))
            sys.exit(1)
        RegPatternClass = REG_CLASS_PATTERN_MAP[reg_type]
        reg_list = RegPatternClass.get_reg_list_from_names(arch, reg_name_list, reg_type)
        return reg_list


class VirtualRegisterPattern_SingleReg(VirtualRegisterPattern):
    @classmethod
    def get_reg_list_from_names(VRP_Class, arch, reg_name_list, reg_type):
        assert reg_type in "RA"
        return [arch.get_unique_virt_reg_object(reg_name_list[0], reg_class=VRP_Class.VIRT_REG_CLASS)]

class VirtualRegisterPattern_DualReg(VirtualRegisterPattern):
    @classmethod
    def get_reg_list_from_names(VRP_Class, arch, reg_name_list, reg_type):
        assert reg_type in VRP_Class.VIRT_REG_DESCRIPTOR
        lo_reg = arch.get_unique_virt_reg_object(reg_name_list[0], reg_class=VRP_Class.VIRT_REG_CLASS, reg_constraint=even_indexed_register)
        hi_reg = arch.get_unique_virt_reg_object(reg_name_list[1], reg_class=VRP_Class.VIRT_REG_CLASS, reg_constraint=odd_indexed_register)
        lo_reg.add_linked_register(hi_reg, lambda color_map: [color_map[hi_reg] - 1])
        hi_reg.add_linked_register(lo_reg, lambda color_map: [color_map[lo_reg] + 1])
        return [lo_reg, hi_reg]

class VirtualRegisterPattern_Acc(VirtualRegisterPattern_SingleReg):
    VIRT_REG_CLASS = Register.Acc
    VIRT_REG_DESCRIPTOR = "A"
class VirtualRegisterPattern_Std(VirtualRegisterPattern_SingleReg):
    VIRT_REG_CLASS = Register.Std
    VIRT_REG_DESCRIPTOR = "R"
class VirtualRegisterPattern_DualStd(VirtualRegisterPattern_DualReg):
    VIRT_REG_CLASS = Register.Std
    VIRT_REG_DESCRIPTOR = "D"

class PhysicalRegisterPattern(Pattern):
    """ pattern for physical register """
    REG_PATTERN = None

    @staticmethod
    def get_unique_reg_obj(arch, index):
        raise NotImplementedError

    @classmethod
    def parse(PRP_Class, arch, lexem_list):
        if not len(lexem_list):
            return None
        elif isinstance(lexem_list[0], RegisterLexem):
            #raise Exception("RegisterLexem was expected, got: {}".format(lexem))
            reg_lexem = lexem_list[0]

            # STD_REG_PATTERN = "\$([r][0-9]+){1,4}"
            #ACC_REG_PATTERN = "\$([a][0-9]+){1,4}"

            index_range = [int(index) for index in re.split("\D+", reg_lexem.value) if index != ""]

            if re.fullmatch(PRP_Class.REG_PATTERN, reg_lexem.value):
                register_list = [PRP_Class.get_unique_reg_obj(arch, index) for index in index_range]
            #if re.fullmatch(STD_REG_PATTERN, reg_lexem.value):
            #    register_list = [arch.get_unique_phys_reg_object(index, PhysicalRegister.Std) for index in index_range]
            #elif re.fullmatch(ACC_REG_PATTERN, reg_lexem.value):
            #    register_list = [arch.get_unique_phys_reg_object(index, PhysicalRegister.Acc) for index in index_range]
            else:
                raise NotImplementedError

            return register_list, lexem_list[1:]
        else:
            # trying to parse a virtual register
            return None


class PhysicalRegisterPattern_Any(Pattern):
    """ pattern for physical register """
    REG_PATTERN = None

    @classmethod
    def parse(PRP_Class, arch, lexem_list):
        if isinstance(lexem_list[0], RegisterLexem):
            #raise Exception("RegisterLexem was expected, got: {}".format(lexem))
            reg_lexem = lexem_list[0]

            PATTERN_MAP = {
                "\$([r][0-9]+){1,4}": Register.Std,
                "\$([a][0-9]+){1,4}": Register.Acc,
            }

            index_range = [int(index) for index in re.split("\D+", reg_lexem.value) if index != ""]

            register_list = None

            for pattern in PATTERN_MAP:
                if re.fullmatch(pattern, reg_lexem.value):
                    register_list = [arch.get_unique_phys_reg_object(index, PATTERN_MAP[pattern]) for index in index_range]
                    break
            if register_list is None:
                return None

            return register_list, lexem_list[1:]
        else:
            # trying to parse a virtual register
            return None

class PhysicalRegisterPattern_Std(PhysicalRegisterPattern):
    REG_PATTERN = "\$([r][0-9]+)"#{1,4}"

    @staticmethod
    def get_unique_reg_obj(arch, index):
        return arch.get_unique_phys_reg_object(index, PhysicalRegister.Std)

class PhysicalRegisterPattern_DualStd(PhysicalRegisterPattern):
    REG_PATTERN = "\$([r][0-9]+){2}"

    @staticmethod
    def get_unique_reg_obj(arch, index):
        return arch.get_unique_phys_reg_object(index, PhysicalRegister.Std)

class PhysicalRegisterPattern_Acc(PhysicalRegisterPattern):
    REG_PATTERN = "\$([a][0-9]+){1,4}"

    @staticmethod
    def get_unique_reg_obj(arch, index):
        return arch.get_unique_phys_reg_object(index, PhysicalRegister.Acc)


class RegisterPattern(Pattern):
    """ arbitrary (physical and virtual) register pattern """
    VIRTUAL_PATTERN_CLASS = None
    PHYSICAL_PATTERN_CLASS = None

    @classmethod
    def parse(RP_Class, arch, lexem_list):
        virtual_match = RP_Class.VIRTUAL_PATTERN_CLASS.parse(arch, lexem_list)
        if not virtual_match is None:
            # pair (register_list, remaining lexem list)
            return virtual_match
        physical_match = RP_Class.PHYSICAL_PATTERN_CLASS.parse(arch, lexem_list)
        if not physical_match is None:
            # pair (register_list, remaining lexem list)
            return physical_match
        # no match
        return None

class RegisterPattern_Std(RegisterPattern):
    VIRTUAL_PATTERN_CLASS = VirtualRegisterPattern_Std
    PHYSICAL_PATTERN_CLASS = PhysicalRegisterPattern_Std

class RegisterPattern_DualStd(RegisterPattern):
    VIRTUAL_PATTERN_CLASS = VirtualRegisterPattern_DualStd
    PHYSICAL_PATTERN_CLASS = PhysicalRegisterPattern_DualStd

class RegisterPattern_Acc(RegisterPattern):
    VIRTUAL_PATTERN_CLASS = VirtualRegisterPattern_Acc
    PHYSICAL_PATTERN_CLASS = PhysicalRegisterPattern_Acc


class OffsetPattern_Std(Pattern):
    """ pattern for address offset """
    @staticmethod
    def parse(arch, lexem_list):
        offset_lexem = lexem_list[0]
        if isinstance(offset_lexem, ImmediateLexem):
            offset = [ImmediateValue(int(offset_lexem.value))]
            lexem_list = lexem_list[1:]
        elif isinstance(offset_lexem, RegisterLexem):
            offset, lexem_list = PhysicalRegisterPattern_Std.parse(arch, lexem_list)
        elif isinstance(offset_lexem, Lexem):
            offset, lexem_list = VirtualRegisterPattern_Std.parse(arch, lexem_list)
        else:
            print("unrecognized lexem {} while parsing for offset".format(offset_lexem))
            raise NotImplementedError
        return offset, lexem_list

class AddrValue:
    def __init__(self, base=None, offset=None):
        self.base = base
        self.offset = offset

class AddressPattern_Std(Pattern):
    @staticmethod
    def parse(arch, lexem_list):
        offset_match = OffsetPattern_Std.parse(arch, lexem_list)
        if offset_match is None: return None
        offset_value, lexem_list = offset_match
        lexem_list = MetaPopOperatorPredicate("[")(lexem_list)
        base_match = RegisterPattern_Std.parse(arch, lexem_list)
        if base_match is None: return None
        base_value, lexem_list = base_match
        lexem_list = MetaPopOperatorPredicate("]")(lexem_list)
        return AddrValue(base=base_value, offset=offset_value), lexem_list

class OpcodePattern(Pattern):
    def __init__(self, tag="opcode"):
        Pattern.__init__(self, tag)

    def parse(self, arch, lexem_list):
        if len(lexem_list) == 0:
            return None
        else:
            head, lexem_list = lexem_list[0], lexem_list[1:]
            if (not isinstance(head, Lexem)):
                return None
            return head.value, lexem_list

class LabelPattern(Pattern):
    def __init__(self, tag="label"):
        Pattern.__init__(self, tag)

    def parse(self, arch, lexem_list):
        if len(lexem_list) == 0:
            return None
        else:
            head, lexem_list = lexem_list[0], lexem_list[1:]
            if (not isinstance(head, Lexem)):
                return None
            return head.value, lexem_list


class SequentialPattern:
    def __init__(self, elt_pattern_list, result_builder):
        self.elt_pattern_list = elt_pattern_list
        # callback to build the object result from a match
        self.result_builder = result_builder

    def match(self, arch, lexem_list):
        match_result = {}
        for pattern in self.elt_pattern_list:
            result = pattern.parse(arch, lexem_list)
            if result is None:
                print("could not match {} with {}".format(lexem_list, pattern))
                return None
            # retieving parse result and updating remaining list of lexems
            value, lexem_list = result
            if not value is None:
                match_result[pattern.tag] = value

        return self.result_builder(match_result), lexem_list


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


class AsmParser:
    def __init__(self, arch, program):
        self.ongoing_bundle = Bundle()
        self.program = program
        self.arch = arch

    def parse_asm_line(self, lexem_list, dbg_object):
        if not len(lexem_list): return
        head = lexem_list[0]
        if isinstance(head, BundleSeparatorLexem):
            self.program.add_bundle(self.ongoing_bundle)
            self.ongoing_bundle = Bundle()
        elif isinstance(head, MacroLexem):
            self.parse_macro(lexem_list[1:], dbg_object)
        elif isinstance(head, CommentHeadLexem):
            pass
        elif isinstance(head, Lexem):
            if isinstance(lexem_list[1], LabelEndLexem):
                if len(self.ongoing_bundle) != 0:
                    print("Error: label can not be inserted in the middle of a bundle @ {}".format(dbg_object))
                    sys.exit(1)
                self.program.add_label(head.value)

            else:
                if head.value in self.arch.insn_patterns:
                    insn_pattern = self.arch.insn_patterns[head.value]
                    insn_match = insn_pattern.match(self.arch, lexem_list)
                    if insn_match is None:
                        print("failed to match {} in {}".format(head.value, lexem_list))
                        sys.exit(1)
                    else:
                        insn_object, lexem_list = insn_match

                else:
                    print("unable to parse {} @ {}".format(lexem_list, dbg_object))
                    raise NotImplementedError
                # adding meta information
                insn_object.dbg_object = dbg_object
                # registering instruction
                self.ongoing_bundle.add_insn(insn_object)
                if insn_object.is_jump:
                    # succ = self.program.bb_label_map[insn_object.use_list[0]]
                    # TODO/FIXME jump bb label should be extract with method
                    #            and not directly from index 0 of use_list
                    succ = self.program.get_bb_by_label(insn_object.use_list[0])
                    self.program.current_bb.add_successor(succ)
                    succ.add_predecessor(self.program.current_bb)

        else:
            raise NotImplementedError

    def parse_macro(self, lexem_list, dbg_object):
        """ parse macro line once '//#' has been consumed """
        macro_name = lexem_list[0]
        lexem_list = lexem_list[1:]

        # consuming "("
        lexem_list = MetaPopOperatorPredicate("(")(lexem_list)

        register_list = []
        while len(lexem_list) and not NextLexem_OperatorPredicate(")")(lexem_list):
            sub_reg_list, lexem_list = self.parse_register_from_list(lexem_list)
            register_list = register_list + sub_reg_list

        lexem_list = MetaPopOperatorPredicate(")")(lexem_list)

        if macro_name.value == "PREDEFINED":
            print("adding {} to list of pre-defined registers".format(register_list))
            self.program.pre_defined_list += register_list

        elif macro_name.value == "POSTUSED":
            print("adding {} to list of post-used registers".format(register_list))
            self.program.post_used_list += register_list

        else:
            print("unknown macro {} @ {} ".format(macro_name.value, dbg_object))
            #Error
            sys.exit(1)

    def parse_insn_from_list(self, lexem_list):
        insn = lexem_list[0]
        lexem_list = lexem_list[1:]
        return insn, lexem_list

    def parse_register_from_list(self, lexem_list):
        return self.parse_register(lexem_list)

    def parse_virtual_register(self, lexem_list):
        """ Try to parse a virtual register description for @p lexem_list
            return a pair with:
            - the list (most likely a single element) of virtual register
              encoded in lexem
            - a list of remaining lexems """
        reg_list, lexem_list = VirtualRegisterPattern_Any.parse(self.arch, lexem_list)
        return reg_list, lexem_list

    def parse_register(self, lexem_list):
        """ extract the lexem register representing a list of registers
            return the list of register object and the remaining
            list of lexems """
        if isinstance(lexem_list[0], RegisterLexem):
            register_match = PhysicalRegisterPattern_Any.parse(self.arch, lexem_list)
            if register_match is None:
                print("unable to parse register from {}".format(lexem_list))
                sys.exit(1)
            reg_list, lexem_list = register_match
            return reg_list, lexem_list
        else:
            # trying to parse a virtual register
            return self.parse_virtual_register(lexem_list)




def parse_architecture(arch_str_desc):
    ARCH_CTOR_MAP = {
        "dummy": DummyArchitecture
    }

    return ARCH_CTOR_MAP[arch_str_desc]()


if __name__ == "__main__":
    # command line options
    parser = argparse.ArgumentParser()
    parser.add_argument("--lexer-verbose", action="store_const", default=False, const=True, help="enable lexer verbosity")

    parser.add_argument("--output", action="store", default=None, help="select output file (default stdout)")
    parser.add_argument("--input", action="store", help="select input file")
    parser.add_argument("--arch", action="store", default=DummyArchitecture(), type=parse_architecture, help="select target architecture")

    args = parser.parse_args()

    program = Program()
    asm_parser = AsmParser(args.arch, program)

    print("parsing input program")
    with open(args.input, "r") as input_stream:
        # TODO/FIXME: optimize file reading (line by line rather than full file at once)
        full_input_file = input_stream.read()
        for line_no, line in enumerate(full_input_file.split("\n")):
            lexem_list = lexer.generate_line_lexems(line)
            if args.lexer_verbose:
                print(lexem_list)
            dbg_object = DebugObject(line_no)
            asm_parser.parse_asm_line(lexem_list, dbg_object=dbg_object)
        # finish program (e.g. connecting last BB to sink)
        asm_parser.program.end_program()
        print(asm_parser.program.bb_list)
        for label in asm_parser.program.bb_label_map:
            print("label: {}".format(label))
            print(asm_parser.program.bb_label_map[label].bundle_list)
        #print(asm_parser.program.label_map)
    # manage file I/O exception

    print("Register Assignation")
    reg_assignator = RegisterAssignator(args.arch)

    empty_liverange_map = args.arch.get_empty_liverange_map()

    #print("Declaring pre-defined registers")
    #empty_liverange_map.populate_pre_defined_list(program)

    var_ins, var_out = reg_assignator.generate_use_def_lists(asm_parser.program)
    liverange_map = reg_assignator.generate_liverange_map(asm_parser.program, empty_liverange_map, var_ins, var_out)

    print("Checking pre-defined register consistency")
    for reg in program.pre_defined_list:
        if not reg in var_out[program.source_bb]:
            print("{} is declared in pre-defined list but not alive at program source".format(reg))
            sys.exit(1)
    for reg in var_out[program.source_bb]:
        if not reg in program.pre_defined_list:
            print("{} is alive at program source but not declared in pre-defined list".format(reg))
            sys.exit(1)
    print("Variable alive at source BB: {}".format([reg for reg in var_out[program.source_bb]]))
    print("Variable alive at sink BB: {}".format([reg for reg in var_ins[program.sink_bb]]))

    print("Checking liveranges")
    liverange_status = reg_assignator.check_liverange_map(liverange_map)
    print(liverange_status)
    if not liverange_status:
        # sys.exit(1)
        pass

    print("Graph coloring")
    conflict_map = reg_assignator.create_conflict_map(liverange_map)
    color_map = reg_assignator.create_color_map(conflict_map)
    for reg_class in conflict_map:
        conflict_graph = conflict_map[reg_class]
        class_color_map = color_map[reg_class]
        check_status = reg_assignator.check_color_map(conflict_graph, class_color_map)
        if not check_status:
            print("register assignation for class {} does is not valid")
            sys.exit(1)

    def dump_allocation(color_map, output_callback):
        """ dump virtual register allocation mapping """
        for reg_class in color_map:
            for reg in color_map[reg_class]:
                if reg.is_virtual():
                    output_callback("#define {} {}\n".format(reg.name, color_map[reg_class][reg]))

    def dump_program(bb_list, color_map):
        for bb in bb_list:
            for bundle in bb.bundle_list:
                for insn in bundle.insn_list:
                    if not insn.dump_pattern is None:
                        # use_list = [reg.instanciate(color_map) for reg in insn.use_list]
                        # def_list = [reg.instanciate(color_map) for reg in insn.def_list]

                        print(insn.dump_pattern(color_map, insn.use_list, insn.def_list))

            print(";;")


    if args.output is None:
        dump_allocation(color_map, lambda s: print(s, end=""))
    else:
        with open(args.output, "w") as output_stream:
            dump_allocation(color_map, lambda s: output_stream.write(s))

    print("dumping program")
    dump_program(asm_parser.program.bb_list, color_map)

