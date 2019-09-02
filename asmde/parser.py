# -*- coding: utf-8 -*-

import re

import lexer

from lexer import (
    Lexem, VirtualRegisterLexem, RegisterLexem,
    ImmediateLexem, OperatorLexem,
    BundleSeparatorLexem
)

class Register:
    class Std: pass
    class Acc: pass

class SubRegister:
    """ Elementary register object """
    def __init__(self, index, reg_class):
        self.index = index
        self.reg_class

class ArchRegister(Register):
    def __init__(self, index, reg_class=None):
        self.index = index
        self.reg_class = reg_class


    def __repr__(self):
        if self.reg_class is Register.Std:
            return "$r{}".format(self.index)
        elif self.reg_class is Register.Acc:
            return "$a{}".format(self.index)
        return "ArchRegister(index={}, class={})".format(self.index, self.reg_class)

class VirtualRegister(Register):
    def __init__(self, name, reg_class=None):
        self.name = name
        self.reg_class = reg_class

    def __repr__(self):
        if self.reg_class is Register.Std:
            return "$r<{}>".format(self.name)
        elif self.reg_class is Register.Acc:
            return "$a<{}>".format(self.name)
        return "VirtualRegister(name={}, class={})".format(self.name, self.reg_class)

class ImmediateValue:
    def __init__(self, value):
        self.value = value

class DebugObject:
    def __init__(self, src_line, src_file=None):
        self.src_file = src_file
        self.src_line = src_line

    def __repr__(self):
        return "Dbg(lineno={})".format(self.src_line)

class Instruction:
    def __init__(self, insn_object, def_list=None, use_list=None, dbg_object=None):
        self.insn_object = insn_object
        self.def_list = [] if def_list is None else def_list
        self.use_list = [] if use_list is None else use_list
        self.dbg_object = dbg_object

    def __repr__(self):
        return self.insn_object

class Bundle:
    def __init__(self, insn_list=None):
        self.insn_list = [] if insn_list is None else insn_list

    def add_insn(self, insn):
        self.insn_list.append(insn)

    def __repr__(self):
        return "Bundle({})".format(self.insn_list)

class Architecture:
    def __init__(self):
        pass

    def get_unique_reg_object(self, index, reg_class):
        raise NotImplementedError
    def get_unique_virt_reg_object(self, var_name, reg_class):
        raise NotImplementedError

class DummyArchitecture(Architecture):
    def __init__(self):
        self.physical_register_pool = {
            ArchRegister.Std:
                dict((i, ArchRegister(i, ArchRegister.Std)) for i in range(64)),
            ArchRegister.Acc:
                dict((i, ArchRegister(i, ArchRegister.Acc)) for i in range(48)),
        }
        self.virtual_register_pool = {
            ArchRegister.Std: {},
            ArchRegister.Acc: {},

        }

    def get_unique_reg_object(self, index, reg_class):
        return self.physical_register_pool[reg_class][index]

    def get_unique_virt_reg_object(self, var_name, reg_class):
        if not var_name in self.virtual_register_pool[reg_class]:
            self.virtual_register_pool[reg_class][var_name] = VirtualRegister(var_name, reg_class)
        return self.virtual_register_pool[reg_class][var_name]

class AsmParser:
    def __init__(self, arch):
        self.ongoing_bundle = Bundle()
        self.program = []
        self.arch = arch

    def parse_asm_line(self, lexem_list, dbg_object):
        if not len(lexem_list): return
        head = lexem_list[0]
        if isinstance(head, BundleSeparatorLexem):
            self.program.append(self.ongoing_bundle)
            self.ongoing_bundle = Bundle()
            print("End of bundle")
        elif isinstance(head, Lexem):
            INSN_PARSING_MAP = {
                "ld": self.parse_load_from_list,
                "add": self.parse_add_from_list
            }
            if head.value in INSN_PARSING_MAP:
                parsing_method = INSN_PARSING_MAP[head.value]
                insn, lexem_list = parsing_method(lexem_list)
                insn.dbg_object = dbg_object
                self.ongoing_bundle.add_insn(insn)
            else:
                print(lexem_list)
                raise NotImplementedError
        else:
            raise NotImplementedError


    def parse_insn_from_list(self, lexem_list):
        insn = lexem_list[0]
        lexem_list = lexem_list[1:]
        return insn, lexem_list

    def parse_register_from_list(self, lexem_list):
        head, lexem_list = lexem_list[0], lexem_list[1:]
        return self.parse_register(head), lexem_list

    def parse_virtual_register(self, lexem):
        """ return the list (most likely a single element) of virtual
            register encoded in lexem """
        assert isinstance(lexem, VirtualRegisterLexem)

        VIRTUAL_REG_PATTERN = "(?P<var_type>[RDQOABCD])\((?P<var_name>\w+)\)"
        reg_match = re.match(VIRTUAL_REG_PATTERN, lexem.value)
        reg_type = reg_match.group("var_type")
        reg_name = reg_match.group("var_name")

        reg_class = {
            "R": Register.Std,
            "A": Register.Acc
        }[reg_type]
        return [self.arch.get_unique_virt_reg_object(reg_name, reg_class=reg_class)]


    def parse_register(self, lexem):
        """ extract the lexem register representing a list of registers
            return the list of register object and the remaining
            list of lexems """
        if isinstance(lexem, VirtualRegisterLexem):
            return self.parse_virtual_register(lexem)


        if not isinstance(lexem, RegisterLexem):
            raise Exception("RegisterLexem was expected, got: {}".format(lexem))

        STD_REG_PATTERN = "\$([r][0-9]+){1,4}"
        ACC_REG_PATTERN = "\$([a][0-9]+){1,4}"

        index_range = [int(index) for index in re.split("\D+", lexem.value) if index != ""]
        sub_reg_num = len(index_range)

        if re.fullmatch(STD_REG_PATTERN, lexem.value):
            register_list = [self.arch.get_unique_reg_object(index, ArchRegister.Std) for index in index_range]
        elif re.fullmatch(ACC_REG_PATTERN, lexem.value):
            register_list = [self.arch.get_unique_reg_object(index, ArchRegister.Acc) for index in index_range]
        else:
            raise NotImplementedError

        return register_list

    def parse_offset_from_list(self, lexem_list):
        offset = lexem_list[0]
        lexem_list = lexem_list[1:]
        if isinstance(offset, ImmediateLexem):
            offset = ImmediateValue(int(offset.value))
        elif isinstance(offset, RegisterLexem):
            offset = self.parse_register(offset)
        return offset, lexem_list

    def parse_base_addr_from_list(self, lexem_list):
        def MetaPopOperatorPredicate(op_value):
            def predicate(lexem_list):
                lexem = lexem_list[0]
                if not isinstance(lexem, OperatorLexem) or lexem.value != op_value:
                    raise Exception(" expecting operator {}, got {}".format(op_value, lexem)) 
                    return False
                return lexem_list[1:]
            return predicate

        lexem_list = MetaPopOperatorPredicate("[")(lexem_list)
        base_addr, lexem_list = self.parse_register_from_list(lexem_list)
        lexem_list = MetaPopOperatorPredicate("]")(lexem_list)

        return base_addr, lexem_list

    def parse_addr_from_list(self, lexem_list):
        offset, lexem_list = self.parse_offset_from_list(lexem_list)
        base_addr, lexem_list = self.parse_base_addr_from_list(lexem_list)

        return (base_addr + offset), lexem_list

    def parse_load_from_list(self, lexem_list):
        insn, lexem_list = self.parse_insn_from_list(lexem_list)
        dst_reg, lexem_list = self.parse_register_from_list(lexem_list)
        addr, lexem_list = self.parse_addr_from_list(lexem_list)
        print("LOAD INSN")
        print("   defs: {}".format(dst_reg))
        print("   uses: {}".format(addr))
        insn_object = Instruction("load", use_list=addr, def_list=dst_reg)
        return insn_object, lexem_list

    def parse_add_from_list(self, lexem_list):
        insn, lexem_list = self.parse_insn_from_list(lexem_list)
        dst_reg, lexem_list = self.parse_register_from_list(lexem_list)
        lhs, lexem_list = self.parse_register_from_list(lexem_list)
        rhs, lexem_list = self.parse_register_from_list(lexem_list)
        print("ADD INSN")
        print("   defs: {}".format(dst_reg))
        print("   uses: {}".format(lhs + rhs))
        insn_object = Instruction("add", use_list=(lhs + rhs), def_list=dst_reg)
        return insn_object, lexem_list

class LiveRange:
    def __init__(self, start=None, stop=None, start_dbg_object=None, stop_dbg_object=None):
        self.start = start
        self.stop = stop
        self.start_dbg_object = start_dbg_object
        self.stop_dbg_object = stop_dbg_object

    def update_stop(self, new_stop, dbg_object=None):
        if self.stop is None or new_stop > self.stop:
            self.stop = new_stop
            self.dbg_object = dbg_object
    def update_start(self, new_start, dbg_object=None):
        if self.start is None or new_start < self.start:
            self.start = new_start
            self.dbg_object = dbg_object

    def __repr__(self):
        return "[{}; {}]".format(self.start, self.stop)

class RegisterPool:
    def __init__(self, size):
        pass


class RegisterAssignator:
    def __init__(self, arch):
        self.arch = arch

    def process_program(self, bundle_list):
        pass

    def generate_liverange_map(self, bundle_list):
        """ generate a dict key -> live_range mapping each variable
            to its liverange """
        liverange_map = {}
        for index, bundle in enumerate(bundle_list):
            print(index, bundle)
            for insn in bundle.insn_list:
                print("uses in {}".format(insn.use_list))
                for reg in insn.use_list:
                    print(reg)
                    if not reg in liverange_map:
                        liverange_map[reg] = LiveRange(stop=index, stop_dbg_object=insn.dbg_object)
                    else:
                        liverange_map[reg].update_stop(index, dbg_object=insn.dbg_object)
                print("defs in {}".format(insn.def_list))
                for reg in insn.def_list:
                    print(reg)
                    if not reg in liverange_map:
                        liverange_map[reg] = LiveRange(start=index, start_dbg_object=insn.dbg_object)
                    else:
                        liverange_map[reg].update_start(index, dbg_object=insn.dbg_object)
        return liverange_map

    def check_liverange_map(self, liverange_map):
        error_count = 0
        for reg in liverange_map:
            liverange = liverange_map[reg]
            if liverange.start == None and liverange.stop != None:
                print("value {} is used @ {} without being defined!".format(reg, liverange.stop_dbg_object))
                error_count += 1
            if liverange.stop == None and liverange.start != None:
                print("value {} is defined @ {} without being used!".format(reg, liverange.start_dbg_object))
                error_count += 1
        return error_count == 0



test_string = """\
ld $r4 = $r2[$r12]
add $r3 = $r2, $r1
;;
add $r3 = $r2, $r1
;;
add $r3 = R(add), $r1
ld $r4 = $r2[$r12]
;;
"""

if __name__ == "__main__":
    print(lexer.RegisterLexem.match("$r12"))
    print(lexer.RegisterLexem.match("$r12[$r2]"))
    print(lexer.OperatorLexem.match("["))
    print(lexer.OperatorLexem.match("]"))
    print(lexer.BundleSeparatorLexem.match(";;"))
    print(lexer.generate_line_lexems(";;"))

    arch = DummyArchitecture()
    asm_parser = AsmParser(arch)

    for line_no, line in enumerate(test_string.split("\n")):
        lexem_list = lexer.generate_line_lexems(line)
        dbg_object = DebugObject(line_no)
        print("lexem_list: ", lexem_list)
        asm_parser.parse_asm_line(lexem_list, dbg_object=dbg_object)

    print(asm_parser.program)

    print("Register Assignation")
    reg_assignator = RegisterAssignator(arch)
    liverange_map = reg_assignator.generate_liverange_map(asm_parser.program)
    print(liverange_map)

    print(reg_assignator.check_liverange_map(liverange_map))

