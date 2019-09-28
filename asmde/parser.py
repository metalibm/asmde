# -*- coding: utf-8 -*-

import re
import sys
import argparse

import lexer

from lexer import (
    Lexem, RegisterLexem,
    LabelEndLexem, CommentHeadLexem,
    ImmediateLexem, OperatorLexem,
    BundleSeparatorLexem, MacroLexem,
)

class Register:
    """ main class for Register objects """
    class RegClass:
        """ class of registers """
        @classmethod
        def build_multi_reg(reg_class, reg_list):
            """ build a multi-reg register from a list of physical registers """
            return MultiArchRegister(reg_list, reg_class)
        @classmethod
        def get_single_phy_reg_repr(reg_class, phys_reg):
            """ build a string representation for a single physical register """
            return reg_class.prefix + reg_class.reg_prefix + str(phys_reg.index)
        @classmethod
        def get_single_virt_reg_repr(reg_class, virt_reg):
            """ build a string representation for a single virtual register """
            return reg_class.prefix + reg_class.reg_prefix + "<%s>".format(virt_reg.name)
    class Std(RegClass):
        name = "Std"
        prefix = "$"
        reg_prefix = "r"
    class Acc(RegClass):
        name = "Acc"
        prefix = "$"
        reg_prefix = "a"

    def is_virtual(self):
        """ predicate indicating if register is virtual (or physical) """
        raise NotImplementedError


class MultiArchRegister:
    """ register formed by concatening multiple regsiters """
    def __init__(self, reg_list, reg_class):
        self.reg_list = reg_list
        self.reg_class = reg_class

    def __repr__(self):
        return "{prefix}{reg_list}".format(
            prefix=self.reg_class.prefix,
            reg_list="".join("%s%d" % (self.reg_class.reg_prefix, reg.index) for reg in self.reg_list)
        )


class PhysicalRegister(Register):
    """ Physical register """
    def __init__(self, index, reg_class=None):
        self.index = index
        self.reg_class = reg_class

    def __repr__(self):
        return self.reg_class.get_single_phy_reg_repr(self)

    def is_virtual(self):
        return False

    def instanciate(self, color_map):
        return self

# linked register
# register that must be assigned while enforcing a common constraint
# (e.g. contiguous)

def no_constraint(index):
    return True

def odd_indexed_register(index):
    return (index % 2) == 1
def even_indexed_register(index):
    return (index % 2) == 0

class VirtualRegister(Register):
    """ Virtual register """
    def __init__(self, name, reg_class=None, constraint=no_constraint, linked_registers=None):
        self.name = name
        self.reg_class = reg_class
        # predicate to be enforced when assigning a physical register index
        # to this virtual register: lambda index: bool
        self.constraint = constraint
        # list of pairs (register, index_generator)
        # where index_generator is lambda color_map: list which generates a iist of
        # possible valid indexes for self register
        self.linked_registers = {} if linked_registers is None else linked_registers

    def get_linked_map(self):
        return self.linked_registers

    def add_linked_register(self, reg, index_generator):
        self.linked_registers[reg] = index_generator

    def is_virtual(self):
        return True

    def __repr__(self):
        return self.reg_class.get_single_virt_reg_repr(self)

    def instanciate(self, color_map):
        return PhysicalRegister(color_map[self.reg_class][self], self.reg_class)


class ImmediateValue:
    """ Immediate (numerical) value """
    def __init__(self, value):
        self.value = value

    def instanciate(self, color_map):
        return self

    def __repr__(self):
        return "%d" % self.value

class DebugObject:
    """ Structure to store and forwared debug information """
    def __init__(self, src_line, src_file=None):
        self.src_file = src_file
        self.src_line = src_line

    def __repr__(self):
        return "Dbg(lineno={})".format(self.src_line)

class Instruction:
    def __init__(self, insn_object, def_list=None, use_list=None, dbg_object=None, dump_pattern=None):
        self.insn_object = insn_object
        self.def_list = [] if def_list is None else def_list
        self.use_list = [] if use_list is None else use_list
        self.dbg_object = dbg_object
        # function (use_list, def_list) -> instruction string
        self.dump_pattern = dump_pattern

    def __repr__(self):
        return self.insn_object

class Bundle:
    def __init__(self, insn_list=None):
        self.insn_list = [] if insn_list is None else insn_list

    def add_insn(self, insn):
        self.insn_list.append(insn)

    def __len__(self):
        return len(self.insn_list)

    def __repr__(self):
        return "Bundle({})".format(self.insn_list)


class RegFileDescription:
    def __init__(self, reg_class, num_phys_reg, reg_ctor, virtual_reg_ctor):
        self.reg_class = reg_class
        self.num_phys_reg = num_phys_reg
        self.reg_ctor = reg_ctor
        self.virtual_reg_ctor = virtual_reg_ctor

class RegFile:
    def __init__(self, description):
        self.description = description
        self.physical_pool = dict((i, self.description.reg_ctor(i, description.reg_class)) for i in range(self.description.num_phys_reg))
        self.virtual_pool = {}

    def get_unique_phys_reg_object(self, index):
        if index > self.description.num_phys_reg:
            print("regfile for class {} contains only {} register(s), request for index: {}".format(self.description.reg_class.name, self.description.num_phys_reg, index))
            sys.exit(1)
        return self.physical_pool[index]

    def get_unique_virt_reg_object(self, var_name, reg_constraint=no_constraint):
        if not var_name in self.virtual_pool:
            self.virtual_pool[var_name] = VirtualRegister(var_name, self.description.reg_class, constraint=reg_constraint)
        return self.virtual_pool[var_name]

    def get_max_phys_register_index(self):
        return self.description.num_phys_reg - 1

class Architecture:
    """ Base class for architecture description """
    def __init__(self, reg_file_description_set, insn_patterns):
        self.reg_pool = dict((reg_desc.reg_class, RegFile(reg_desc)) for reg_desc in reg_file_description_set)
        # table (insn pattern) -> Pattern 
        self.insn_patterns = insn_patterns

    def get_max_register_index_by_class(self, reg_class):
        return self.reg_pool[reg_class].get_max_phys_register_index()

    def get_unique_phys_reg_object(self, index, reg_class):
        return self.reg_pool[reg_class].get_unique_phys_reg_object(index)

    def get_unique_virt_reg_object(self, var_name, reg_class, reg_constraint=no_constraint):
        return self.reg_pool[reg_class].get_unique_virt_reg_object(var_name, reg_constraint=reg_constraint)

    def get_empty_liverange_map(self):
        return LiveRangeMap(self.reg_pool.keys())


class Program:
    def __init__(self, pre_defined_list=None, post_used_list=None):
        self.pre_defined_list = [] if pre_defined_list is None else pre_defined_list
        self.post_used_list = [] if post_used_list is None else post_used_list
        self.bundle_list = []
        # dict <label_name> : program offset (in bundles)
        self.label_map = {}

    def add_bundle(self, bundle):
        self.bundle_list.append(bundle)

    def add_label(self, label, offset=None):
        """ Declare a new label @p label, if offset is None
            the offset associated with the label is the current program index
            (end of program) else @p offset value is used directly """
        if offset is None:
            offset = len(self.bundle_list)
        self.label_map[label] = offset

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


class LiveRange:
    def __init__(self, start=None, stop=None, start_dbg_object=None, stop_dbg_object=None):
        self.start = start
        self.stop = stop
        self.start_dbg_object = start_dbg_object
        self.stop_dbg_object = stop_dbg_object

    def update_stop(self, new_stop, dbg_object=None):
        if self.stop is None or new_stop > self.stop:
            self.stop = new_stop
            self.stop_dbg_object = dbg_object
    def update_start(self, new_start, dbg_object=None):
        if self.start is None or new_start < self.start:
            self.start = new_start
            self.start_dbg_object = dbg_object

    def __repr__(self):
        return "[{}; {}]".format(self.start, self.stop)

    def intersect(self, liverange):
        """ Check intersection between @p self range and @p liverange """
        #if liverange_bound_compare_lt(self.stop, liverange.start) or liverange_bound_compare_gt(self.start, liverange.stop):
        if self.stop <= liverange.start or self.start >= liverange.stop:
            return False
        return True

    @staticmethod
    def intersect_list(lr_list0, lr_list1):
        """ test if any of the live range of list @p lr_list0
            intersects any of the live range of list @p lr_list1 """
        for liverange0 in lr_list0:
            for liverange1 in lr_list1:
                if liverange0.intersect(liverange1):
                    return True
        return False


def liverange_bound_compare_gt(lhs, rhs):
    if isinstance(lhs, PostProgram):
        # PostProgram > all
        return True
    elif isinstance(rhs, PostProgram):
        return False
    else:
        return lhs < rhs

def liverange_bound_compare_lt(lhs, rhs):
    return liverange_bound_compare_gt(rhs, lhs)

class PostProgram:
    """" After program ends timestamp """
    def __gt__(self, int_value):
        """ PostProgram is equals to +infty, so is always greater than any integer """
        assert isinstance(int_value, int)
        return True

    def __ge__(self, int_value):
        assert isinstance(int_value, int)
        return True

    def __lt__(self, int_value):
        """ PostProgram is equals to +infty, so is always greater than any integer """
        assert isinstance(int_value, int)
        return False

    def __le__(self, int_value):
        assert isinstance(int_value, int)
        return False

    def __repr__(self):
        return "PostProgram"

class LiveRangeMap(object):
    """ Structure to store and manipulate register live ranges """
    def __init__(self, reg_class_list):
        self.liverange_map = dict((reg_class, {}) for reg_class in reg_class_list)

    def __contains__(self, key):
        return key in self.liverange_map[key.reg_class]

    def __getitem__(self, key):
        return self.liverange_map[key.reg_class][key]

    def __setitem__(self, key, value):
        self.liverange_map[key.reg_class][key] = value

    def get_class_list(self):
        """ return the list of register classes """
        return list(self.liverange_map.keys())

    def get_class_map(self, reg_class):
        """ return the sub-dict of liveranges of registers of class @p reg_class """
        return self.liverange_map[reg_class]

    def get_all_registers(self):
        return sum([list(self.liverange_map[reg_class].keys()) for reg_class in self.liverange_map], [])

    def declare_pre_defined_reg(self, reg):
        """ declare a register which is alive before program starts """
        if not reg in self.liverange_map[reg.reg_class]:
            self.liverange_map[reg.reg_class][reg] = [LiveRange()]
        self.liverange_map[reg.reg_class][reg][-1].update_start(-1, DebugObject("before program starts"))
    def declare_post_used_reg(self, reg):
        if not reg in self.liverange_map[reg.reg_class]:
            self.liverange_map[reg.reg_class][reg] = [LiveRange()]
        self.liverange_map[reg.reg_class][reg][-1].update_stop(PostProgram(), DebugObject("after program ends"))

    def populate_pre_defined_list(self, program):
        for reg in program.pre_defined_list:
            self.declare_pre_defined_reg(reg)

    def populate_post_used_list(self, program):
        for reg in program.post_used_list:
            self.declare_post_used_reg(reg)

class RegisterAssignator:
    def __init__(self, arch):
        self.arch = arch

    def process_program(self, bundle_list):
        pass

    def generate_liverange_map(self, program, liverange_map):
        """ generate a dict key -> list of disjoint live-ranges
            mapping each variable to its liverange """
        for index, bundle in enumerate(program.bundle_list):
            for insn in bundle.insn_list:
                for reg in insn.use_list:
                    if not isinstance(reg, Register):
                        # discard non register element (e.g. ImmediateValue)
                        continue
                    if not reg in liverange_map:
                        liverange_map[reg] = [LiveRange()]
                    # we update the last inserted LiveRange object in reg's list
                    liverange_map[reg][-1].update_stop(index, dbg_object=insn.dbg_object)
                for reg in insn.def_list:
                    if not reg in liverange_map:
                        liverange_map[reg] = []
                    if not(len(liverange_map[reg]) and liverange_map[reg][-1].start == index): 
                        # only register a liverange once per index value
                        liverange_map[reg].append(LiveRange(start=index, start_dbg_object=insn.dbg_object))
        return liverange_map

    def check_liverange_map(self, liverange_map):
        error_count = 0
        for reg in liverange_map.get_all_registers():
            for liverange in liverange_map[reg]:
                if liverange.start == None and liverange.stop != None:
                    if liverange.stop_dbg_object is None:
                        print("value {} is used @ {} without being defined!".format(reg, liverange.stop_dbg_object))
                    else:
                        print("value {} is used line {} without being defined!".format(reg, liverange.stop_dbg_object.src_line))
                    error_count += 1
                if liverange.stop == None and liverange.start != None:
                    if liverange.start_dbg_object is None:
                        print("value {} is defined @ {} without being used!".format(reg, liverange.stop_dbg_object))
                    else:
                        print("value {} is defined line {} without being used!".format(reg, liverange.start_dbg_object.src_line))
                    error_count += 1
        return error_count == 0

    def create_conflict_map(self, liverange_map):
        """ Build the graph of liverange intersection from the
            liverange_map """
        conflict_map = {}
        for reg_class in liverange_map.get_class_list():
            sub_liverange_map = liverange_map.get_class_map(reg_class)
            conflict_map[reg_class] = {}
            for reg in sub_liverange_map:
                conflict_map[reg_class][reg] = set()
                for reg2 in sub_liverange_map:
                    if reg2 != reg and LiveRange.intersect_list(sub_liverange_map[reg], sub_liverange_map[reg2]):
                        conflict_map[reg_class][reg].add(reg2)
        return conflict_map

    def create_color_map(self, conflict_map):
        max_color_num = 0
        max_degree = 0
        max_degree_node = None

        general_color_map = {}

        # start by pre-assigning colors to corresponding physical registers
        for reg_class in conflict_map:
            graph = conflict_map[reg_class]
            color_map = {}
            general_color_map[reg_class] = color_map
            for reg in graph:
                if isinstance(reg, PhysicalRegister):
                    color_map[reg] = reg.index

            while len(color_map) != len(graph):
                # looking for node with max degree
                max_reg = max([node for node in graph if not node in color_map], key=(lambda reg: len(list(node for node in graph[reg] if not node in color_map))))

                def allocate_reg_list(reg_list, graph, color_map):
                    """ Allocate each register in reg_list assuming dependencies
                        are stored in graph and color_map indicates previously performed
                        allocation """
                    if len(reg_list) == 0:
                        # empty list returns empty allocation (valid)
                        return {}
                    else:
                        # select head of list as current register for allocation
                        head_reg = reg_list[0]
                        remaining_reg_list = reg_list[1:]
                        unavailable_color_set = set([color_map[neighbour] for neighbour in graph[head_reg] if neighbour in color_map])

                        valid_color_set = [color for color in range(self.arch.reg_pool[reg_class].description.num_phys_reg) if head_reg.constraint(color)]
                        if not len(valid_color_set):
                            # no color available in valid set
                            return None
                        available_color_set = set(valid_color_set).difference(set(unavailable_color_set))

                        if not len(available_color_set):
                            # no color available in available color set
                            return None

                        # enforcing link constraints
                        linked_map = head_reg.get_linked_map()
                        for linked_reg in linked_map:
                            if not linked_reg in color_map:
                                # discard linked registers which have not been allocated yet
                                continue
                            else:
                                available_color_set.intersection_update(set(linked_map[linked_reg](color_map)))
                        for possible_color in available_color_set:
                            # FIXME: bad performance: copying full local dict each time
                            local_color_map = {head_reg: possible_color}
                            local_color_map.update(color_map)
                            sub_allocation = allocate_reg_list(remaining_reg_list, graph, local_color_map)
                            if sub_allocation != None:
                                # valid sub allocation
                                sub_allocation.update({head_reg: possible_color})
                                # return first valid sub-alloc
                                return sub_allocation

                        return None
                # FIXME/TODO: build full set of linked registers (recursively)

                # if selected register is linked, we must allocated all the
                # register at once to ensure link constraints are met
                linked_allocation = allocate_reg_list([max_reg] + list(max_reg.get_linked_map().keys()), graph, color_map)
                if linked_allocation is None:
                    print("no feasible allocation for {} and linked map {}".format(max_reg, max_reg.get_linked_map()))
                    sys.exit(1)

                num_reg_in_class = self.arch.get_max_register_index_by_class(reg_class)
                for linked_reg in linked_allocation:
                    linked_color =  linked_allocation[linked_reg]
                    color_map[linked_reg] = linked_color
                    # check on colour bound
                    if linked_color >= num_reg_in_class:
                        print("Error while assigning register of class {}, requesting index {}, only {} register(s) available".format(reg_class.name, linked_color, num_reg_in_class)) 
                        sys.exit(1)

                    print("register {} of class {} has been assigned color {}".format(linked_reg, reg_class.name, linked_color))

        return general_color_map

    def check_color_map(self, conflict_graph, color_map):
        for reg in conflict_graph:
            reg_color = color_map[reg]
            for neighbour in conflict_graph[reg]:
                if reg_color == color_map[neighbour]:
                    print("color conflict for {}({}) vs {}({})".format(reg, reg_color, neighbour, color_map[neighbour]))
                    return False
        return True


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
        print(asm_parser.program.bundle_list)
        print(asm_parser.program.label_map)
    # manage file I/O exception

    print("Register Assignation")
    reg_assignator = RegisterAssignator(args.arch)

    empty_liverange_map = args.arch.get_empty_liverange_map()

    print("Declaring pre-defined registers")
    empty_liverange_map.populate_pre_defined_list(program)

    liverange_map = reg_assignator.generate_liverange_map(asm_parser.program, empty_liverange_map)

    print("Declaring post-used registers")
    liverange_map.populate_post_used_list(program)
    print(liverange_map)

    print("Checking liveranges")
    liverange_status = reg_assignator.check_liverange_map(liverange_map)
    print(liverange_status)
    if not liverange_status:
        sys.exit(1)

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

    def dump_program(program, color_map):
        for bundle in program:
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
    dump_program(asm_parser.program.bundle_list, color_map)

