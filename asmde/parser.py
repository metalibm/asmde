# -*- coding: utf-8 -*-

import re
import sys
import collections

import asmde.lexer

from asmde.lexer import (
    Lexem, RegisterLexem,
    LabelEndLexem, CommentHeadLexem,
    ImmediateLexem, OperatorLexem,
    BundleSeparatorLexem, MacroLexem,
    HexImmediateLexem,
    ObjdumpLabel,
    ObjdumpMacro
)

from asmde.allocator import (
    Register, PhysicalRegister, ImmediateValue,
    VirtualRegister,
    DebugObject, Instruction, Bundle,
    RegFileDescription, RegFile, Architecture,
    BasicBlock,
    even_indexed_register,
    odd_indexed_register,
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
            # raise Exception(" expecting operator {}, got {}".format(op_value, lexem)) 
            return None
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

        if not isinstance(virtual_register_type_lexem, Lexem) or not reg_type in VRP_Class.VIRT_REG_DESCRIPTOR:
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
        
       # REG_CLASS_PATTERN_MAP = {
       #     "R": VirtualRegisterPattern_Std,
       #     "A": VirtualRegisterPattern_Acc,
       #     "D": VirtualRegisterPattern_DualStd,
       # }
       REG_CLASS_PATTERN_MAP = arch.getVirtualRegClassPatternMap()
       if not reg_type in REG_CLASS_PATTERN_MAP:
           print("reg_type {} not found in REG_CLASS_PATTERN_MAP (name list: {})".format(reg_typ, reg_name_list))
           sys.exit(1)
       RegPatternClass = REG_CLASS_PATTERN_MAP[reg_type]
       reg_list = RegPatternClass.get_reg_list_from_names(arch, reg_name_list, reg_type)
       return reg_list


class VirtualRegisterPattern_SingleReg(VirtualRegisterPattern):
    @classmethod
    def get_reg_list_from_names(VRP_Class, arch, reg_name_list, reg_type):
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
    REG_LEXEM = RegisterLexem
    REG_CLASS = None

    @classmethod
    def get_unique_reg_obj(cls, arch, index, spec=None):
        return arch.get_unique_phys_reg_object(index, cls.REG_CLASS, spec=spec)

    @classmethod
    def splitSpecIndex(cls, s):
        """ split string @p s into specifier and index
            return a 3-uple (isAlias, spec, index) """
        try:
            match = re.match("(?P<spec>\D+)(?P<index>\d+)", s)
            spec = match.group("spec")
            index = int(match.group("index"))
        except:
            print("failed to match regsiter pattern {} with {}".format(s, cls))
            raise
        return spec, index

    @classmethod
    def parse(PRP_Class, arch, lexem_list):
        if not len(lexem_list):
            return None
        elif isinstance(lexem_list[0], PRP_Class.REG_LEXEM):
            #raise Exception("RegisterLexem was expected, got: {}".format(lexem))
            reg_lexem = lexem_list[0]

            # STD_REG_PATTERN = "\$([r][0-9]+){1,4}"
            #ACC_REG_PATTERN = "\$([a][0-9]+){1,4}"


            if re.fullmatch(PRP_Class.REG_PATTERN, reg_lexem.value):
                # extracting specifier and index
                spec_index_list = [PRP_Class.splitSpecIndex(subreg) for subreg in re.findall(PRP_Class.SUB_REG_PATTERN, reg_lexem.value)]
                print(reg_lexem.value, spec_index_list)
                #index_range = [PRP_Class.aliasResolution(arch, spec_index(1), spec_index(2)) for spec_index in spec_index_list]
                # index_range = [int(index) for index in re.split("\D+", reg_lexem.value) if index != ""]
                register_list = [PRP_Class.get_unique_reg_obj(arch, index, spec) for (spec, index) in spec_index_list]
            #if re.fullmatch(STD_REG_PATTERN, reg_lexem.value):
            #    register_list = [arch.get_unique_phys_reg_object(index, PhysicalRegister.Std) for index in index_range]
            #elif re.fullmatch(ACC_REG_PATTERN, reg_lexem.value):
            #    register_list = [arch.get_unique_phys_reg_object(index, PhysicalRegister.Acc) for index in index_range]
            else:
                return None
                print(PRP_Class, lexem_list)
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
        for RegPatternClass in arch.getPhyRegPatternList():
            result = RegPatternClass.parse(arch, lexem_list)
            if result is not None:
                register_list, new_lexem_list = result
                return register_list, new_lexem_list
        return None

class PhysicalRegisterPattern_Std(PhysicalRegisterPattern):
    REG_PATTERN = "\$([r][0-9]+)"
    SUB_REG_PATTERN = "([r][0-9]+)"
    REG_CLASS = PhysicalRegister.Std


class PhysicalRegisterPattern_DualStd(PhysicalRegisterPattern):
    REG_PATTERN = "\$([r][0-9]+){2}"
    SUB_REG_PATTERN = "([r][0-9]+)"
    REG_CLASS = PhysicalRegister.Std


class PhysicalRegisterPattern_Acc(PhysicalRegisterPattern):
    REG_PATTERN = "\$([a][0-9]+){1,4}"
    SUB_REG_PATTERN = "([a][0-9]+)"
    REG_CLASS = PhysicalRegister.Acc


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


class ImmediatePattern(Pattern):
    @staticmethod
    def parse(arch, lexem_list):
        imm_lexem = lexem_list[0]
        if isinstance(imm_lexem, ImmediateLexem):
            value = ImmediateValue(int(imm_lexem.value))
            # if there is a post-fix HexImmediateLexem (as in objdump file
            # we consume it also
            if len(lexem_list) > 1 and isinstance(lexem_list[1], HexImmediateLexem):
                lexem_list = lexem_list[2:]
            else:
                lexem_list = lexem_list[1:]
            return value, lexem_list
        else:
            print("unrecognized lexem {} while parsing for immediate".format(offset_lexem))
            raise NotImplementedError

class GenericOffsetPattern(Pattern):
    OffsetPhysicalRegisterClass = None
    OffsetVirtuallRegisterClass = None

    @classmethod
    def parse(cls, arch, lexem_list):
        offset_lexem = lexem_list[0]
        if isinstance(offset_lexem, ImmediateLexem):
            offset_imm, lexem_list = ImmediatePattern.parse(arch, lexem_list)
            offset = [offset_imm]
        elif isinstance(offset_lexem, RegisterLexem):
            offset, lexem_list = cls.OffsetPhysicalRegisterClass.parse(arch, lexem_list)
        elif isinstance(offset_lexem, Lexem):
            offset, lexem_list = cls.OffsetVirtuallRegisterClass.parse(arch, lexem_list)
        else:
            print("unrecognized lexem {} while parsing for offset".format(offset_lexem))
            raise NotImplementedError
        return offset, lexem_list
    

class OffsetPattern_Std(GenericOffsetPattern):
    """ pattern for address offset """
    OffsetPhysicalRegisterClass = PhysicalRegisterPattern_Std
    OffsetVirtuallRegisterClass = VirtualRegisterPattern_Std

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
        if lexem_list is None:
            # match failed
            return None
        base_match = RegisterPattern_Std.parse(arch, lexem_list)
        if base_match is None: return None
        base_value, lexem_list = base_match
        lexem_list = MetaPopOperatorPredicate("]")(lexem_list)
        if lexem_list is None:
            # match failed
            return None
        return AddrValue(base=base_value, offset=offset_value), lexem_list

class OpcodePattern(Pattern):
    def __init__(self, tag="opcode", match_predicate=False):
        Pattern.__init__(self, tag)
        self.match_predicate = match_predicate

    def parse(self, arch, lexem_list):
        if len(lexem_list) == 0:
            return None
        else:
            head, lexem_list = lexem_list[0], lexem_list[1:]
            if (not isinstance(head, Lexem)):
                return None
            opcode = head.value
            while self.match_predicate and isinstance(lexem_list[0], OperatorLexem) and lexem_list[0].value == ".":
                assert isinstance(lexem_list[1], Lexem)
                predicate = lexem_list[1].value
                opcode = "{}.{}".format(opcode, predicate)
                lexem_list = lexem_list[2:]
            
            return opcode, lexem_list

class LabelPattern(Pattern):
    def __init__(self, tag="label"):
        Pattern.__init__(self, tag)

    def parse(self, arch, lexem_list):
        if len(lexem_list) == 0:
            return None
        else:
            head, lexem_list = lexem_list[0], lexem_list[1:]
            if (not isinstance(head, (Lexem, ObjdumpLabel))) and (isinstance(head, OperatorLexem) and head.value != "<"):
                return None
            if isinstance(head, OperatorLexem) and head.value == "<":
                label = head.value
                head, lexem_list = lexem_list[0], lexem_list[1:]
                while not isinstance(head, OperatorLexem) or head.value != ">":
                    label = label + head.value
                    if not len(lexem_list):
                        # no match
                        return None
                    head, lexem_list = lexem_list[0], lexem_list[1:]
                # adding final ">"
                label = label + head.value
            return head.value, lexem_list


class SequentialPattern:
    def __init__(self, elt_pattern_list, result_builder, tag=""):
        self.elt_pattern_list = elt_pattern_list
        # callback to build the object result from a match
        self.result_builder = result_builder
        self.tag = tag

    def match(self, arch, lexem_list):
        match_result = {}
        for pattern in self.elt_pattern_list:
            result = pattern.parse(arch, lexem_list)
            if result is None:
                return None
            # retieving parse result and updating remaining list of lexems
            value, lexem_list = result
            if not value is None:
                match_result[pattern.tag] = value

        return self.result_builder(match_result), lexem_list


class DisjonctivePattern:
    """ match one of the element in the list """
    def __init__(self, elt_pattern_list, tag_list=None):
        self.elt_pattern_list = elt_pattern_list
        self.tag_list = tag_list if not tag_list is None else []

    def match(self, arch, lexem_list):
        for pattern in self.elt_pattern_list:
            result = pattern.match(arch, lexem_list)
            if not result is None:
                # should be tuple Result, lexem_list
                return result
        return None


class AsmParser:
    def __init__(self, arch, program):
        self.ongoing_bundle = Bundle()
        self.program = program
        self.arch = arch
        # information used to distinguish bundles when parsing
        # assembly traces
        self.last_timestamp = None
        self.last_program_counter = None

    def parse_asm_line(self, lexem_list, dbg_object):
        if not len(lexem_list): return
        head = lexem_list[0]
        if isinstance(head, BundleSeparatorLexem):
            assert self.arch.hasBundle()
            self.program.add_bundle(self.ongoing_bundle)
            self.ongoing_bundle = Bundle()
        elif isinstance(head, MacroLexem):
            self.parse_macro(lexem_list[1:], dbg_object)
        elif isinstance(head, CommentHeadLexem):
            pass
        elif isinstance(head, Lexem):
            if len(lexem_list) > 1 and isinstance(lexem_list[1], LabelEndLexem):
                if len(self.ongoing_bundle) != 0:
                    print("Error: label can not be inserted in the middle of a bundle @ {}".format(dbg_object))
                    sys.exit(1)
                self.program.add_label(head.value)

            else:
                mnemonic = head.value
                if mnemonic in self.arch.insn_patterns:
                    insn_pattern = self.arch.insn_patterns[mnemonic]
                else:
                    # looking for compound instruction with specified
                    sub_lexem_list = lexem_list[1:]
                    while isinstance(sub_lexem_list[0], OperatorLexem) and sub_lexem_list[0].value == ".":
                        assert isinstance(sub_lexem_list[1], Lexem)
                        predicate = sub_lexem_list[1].value
                        mnemonic = "{}.{}".format(mnemonic, predicate)
                        sub_lexem_list = sub_lexem_list[2:]

                    if mnemonic in self.arch.insn_patterns:
                        insn_pattern = self.arch.insn_patterns[mnemonic]
                    else:
                        print("unable to parse {} @ {}".format(lexem_list, dbg_object))
                        raise NotImplementedError

                insn_match = insn_pattern.match(self.arch, lexem_list)
                if insn_match is None:
                    print("failed to match {} in {}".format(mnemonic, lexem_list))
                    sys.exit(1)
                else:
                    insn_object, lexem_list = insn_match

                # adding meta information
                insn_object.dbg_object = dbg_object
                # registering instruction
                self.ongoing_bundle.add_insn(insn_object)
                if insn_object.is_jump:
                    # succ = self.program.bb_label_map[insn_object.use_list[0]]
                    # TODO/FIXME jump bb label should be extract with method
                    #            and not directly from index 0 of use_list
                    succ = self.program.get_bb_by_label(insn_object.jump_label)
                    self.program.current_bb.add_successor(succ)
                    succ.add_predecessor(self.program.current_bb)
                if not self.arch.hasBundle():
                    # if the architecture does not bundle multiple instructions
                    # (e.g. VLIW), we only emit one instruction per bundle
                    self.program.add_bundle(self.ongoing_bundle)
                    self.ongoing_bundle = Bundle()

        else:
            raise NotImplementedError

    def parse_objdump_line(self, lexem_list, dbg_object):
        if not len(lexem_list): return
        head = lexem_list[0]
        if isinstance(head, BundleSeparatorLexem):
            self.program.add_bundle(self.ongoing_bundle)
            self.ongoing_bundle = Bundle()
        elif isinstance(head, MacroLexem):
            self.parse_macro(lexem_list[1:], dbg_object)
        elif isinstance(head, CommentHeadLexem):
            pass
        elif isinstance(head, ObjdumpMacro):
            pass
        elif isinstance(head, OperatorLexem) and head.value == "<":
            # label
            label = head.value
            while not isinstance(lexem_list[0], OperatorLexem) or lexem_list[0].value != ">":
                label = label + lexem_list.pop(0).value
            assert isinstance(lexem_list[1], LabelEndLexem)
            self.program.add_label(label)

        elif isinstance(head, ObjdumpLabel):
            assert isinstance(lexem_list[1], LabelEndLexem)
            if len(lexem_list) > 1 and isinstance(lexem_list[1], LabelEndLexem):
                if len(self.ongoing_bundle) != 0:
                    print("Error: label can not be inserted in the middle of a bundle @ {}".format(dbg_object))
                    sys.exit(1)
                self.program.add_label(head.value)

        elif isinstance(head, Lexem):
            if head.value == "Disassembly":
                # skipping "Dissasembly of section ..."
                pass
            elif len(lexem_list) > 1 and isinstance(lexem_list[1], LabelEndLexem):
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
                    print("unable to parse {} @ {}, head={}".format(lexem_list, dbg_object, head))
                    raise NotImplementedError
                # adding meta information
                insn_object.dbg_object = dbg_object
                # registering instruction
                self.ongoing_bundle.add_insn(insn_object)
                if insn_object.is_jump:
                    # succ = self.program.bb_label_map[insn_object.use_list[0]]
                    # TODO/FIXME jump bb label should be extract with method
                    #            and not directly from index 0 of use_list
                    succ = self.program.get_bb_by_label(insn_object.jump_label)
                    self.program.current_bb.add_successor(succ)
                    succ.add_predecessor(self.program.current_bb)
                # in objdump file, a instruction line may be ended by a bundle separator
                #   goto label;;
                if len(lexem_list) and isinstance(lexem_list[-1], BundleSeparatorLexem):
                    self.program.add_bundle(self.ongoing_bundle)
                    self.ongoing_bundle = Bundle()

        else:
            print(head, lexem_list, dbg_object)
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

        # register alias disambiguation
        register_list = [reg.baseReg for reg in register_list]

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

    def parse_trace_line(self, lexem_list, dbg_object):
        """ parse assembly trace """
        if not len(lexem_list): return

        head = lexem_list[0]

        if isinstance(head, asmde.lexer.TraceCommentHeadLexem):
            return
        elif isinstance(head, MacroLexem):
            self.parse_macro(lexem_list[1:], dbg_object)
            return
        elif isinstance(head, (asmde.lexer.FunctionStartLexem, asmde.lexer.FunctionEndLexem)):
            # ignoring function start and end
            return


        def match_field_sep(lexem_list):
            """ in ASM trace timestamp and PC field ends with ':' """
            head = lexem_list[0]
            if isinstance(head, LabelEndLexem):
                return lexem_list[1:]
            return None

        # trace is
        # <timestamp>':' <PC as hex>':'  <operation>
        timestamp = lexem_list[0]
        lexem_list = match_field_sep(lexem_list[1:])
        assert not lexem_list is None
        program_counter = lexem_list[0]
        lexem_list = match_field_sep(lexem_list[1:])
        assert not lexem_list is None

        # if the timestamp has changed (should be increase)
        # we commit the previous bundle and open a new one
        if self.last_timestamp != timestamp:
            self.program.add_bundle(self.ongoing_bundle)
            self.ongoing_bundle = Bundle()
        # updating timestamp
        self.last_timestamp = timestamp
        self.last_program_counter = program_counter

        # strip HexImmediateLexem from lexem_list as they corresponds to register value dump
        # in traces
        lexem_list = list(filter(lambda v: not isinstance(v, HexImmediateLexem), lexem_list))
        head = lexem_list[0]

        if isinstance(head, OperatorLexem) and head.value == "<":
            # label
            label = head.value
            while not isinstance(lexem_list[0], OperatorLexem) or lexem_list[0].value != ">":
                label = label + lexem_list.pop(0).value
            assert isinstance(lexem_list[1], LabelEndLexem)
            self.program.add_label(label)

        elif isinstance(head, ObjdumpLabel):
            assert isinstance(lexem_list[1], LabelEndLexem)
            if len(lexem_list) > 1 and isinstance(lexem_list[1], LabelEndLexem):
                if len(self.ongoing_bundle) != 0:
                    print("Error: label can not be inserted in the middle of a bundle @ {}".format(dbg_object))
                    sys.exit(1)
                self.program.add_label(head.value)

        elif isinstance(head, Lexem):
            if head.value in self.arch.insn_patterns:
                insn_pattern = self.arch.insn_patterns[head.value]
                insn_match = insn_pattern.match(self.arch, lexem_list)
                if insn_match is None:
                    print("failed to match {} in {}".format(head.value, lexem_list))
                    sys.exit(1)
                else:
                    insn_object, lexem_list = insn_match

            else:
                print("unable to parse {} @ {}, head={}".format(lexem_list, dbg_object, head))
                raise NotImplementedError
            # adding meta information
            insn_object.dbg_object = dbg_object
            # registering instruction
            self.ongoing_bundle.add_insn(insn_object)
            if insn_object.is_jump:
                # succ = self.program.bb_label_map[insn_object.use_list[0]]
                # TODO/FIXME jump bb label should be extract with method
                #            and not directly from index 0 of use_list
                succ = self.program.get_bb_by_label(insn_object.jump_label)
                self.program.current_bb.add_successor(succ)
                succ.add_predecessor(self.program.current_bb)
            # in objdump file, a instruction line may be ended by a bundle separator
            #   goto label;;
            if len(lexem_list) and isinstance(lexem_list[-1], BundleSeparatorLexem):
                self.program.add_bundle(self.ongoing_bundle)
                self.ongoing_bundle = Bundle()
        else:
            print(head, lexem_list, dbg_object)
            raise NotImplementedError

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
        match = VirtualRegisterPattern_Any.parse(self.arch, lexem_list)
        if match is None:
            return match
        reg_list, lexem_list = match
        return reg_list, lexem_list

    def parse_register(self, lexem_list):
        """ extract the lexem register representing a list of registers
            return the list of register object and the remaining
            list of lexems """
        register_match = PhysicalRegisterPattern_Any.parse(self.arch, lexem_list)
        if not register_match is None:
            reg_list, lexem_list = register_match
            return reg_list, lexem_list
        else:
            # trying to parse a virtual register
            register_match = self.parse_virtual_register(lexem_list)
            if register_match is None:
                print("unable to parse register from {}".format(lexem_list))
                sys.exit(1)
            reg_list, lexem_list = register_match
            return reg_list, lexem_list







