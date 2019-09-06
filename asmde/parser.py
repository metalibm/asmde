# -*- coding: utf-8 -*-

import re
import sys

import lexer

from lexer import (
    Lexem, VirtualRegisterLexem, RegisterLexem,
    ImmediateLexem, OperatorLexem,
    BundleSeparatorLexem
)

class Register:
    class Std:
        name = "Std"
    class Acc:
        name = "Acc"

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
        elif isinstance(head, Lexem):
            INSN_PARSING_MAP = {
                "ld": self.parse_load_from_list,
                "add": self.parse_add_from_list,
                "movefa": self.parse_mofeva_from_list,
                "movefo": self.parse_mofevo_from_list,
            }
            if head.value in INSN_PARSING_MAP:
                parsing_method = INSN_PARSING_MAP[head.value]
                insn, lexem_list = parsing_method(lexem_list)
                insn.dbg_object = dbg_object
                self.ongoing_bundle.add_insn(insn)
            else:
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
        insn_object = Instruction("load", use_list=addr, def_list=dst_reg)
        return insn_object, lexem_list

    def parse_add_from_list(self, lexem_list):
        insn, lexem_list = self.parse_insn_from_list(lexem_list)
        dst_reg, lexem_list = self.parse_register_from_list(lexem_list)
        lhs, lexem_list = self.parse_register_from_list(lexem_list)
        rhs, lexem_list = self.parse_register_from_list(lexem_list)
        insn_object = Instruction("add", use_list=(lhs + rhs), def_list=dst_reg)
        return insn_object, lexem_list

    def parse_mofevo_from_list(self, lexem_list):
        insn, lexem_list = self.parse_insn_from_list(lexem_list)
        dst_reg, lexem_list = self.parse_register_from_list(lexem_list)
        lhs, lexem_list = self.parse_register_from_list(lexem_list)
        rhs, lexem_list = self.parse_register_from_list(lexem_list)
        insn_object = Instruction("movefo", use_list=(lhs + rhs), def_list=dst_reg)
        return insn_object, lexem_list

    def parse_mofeva_from_list(self, lexem_list):
        insn, lexem_list = self.parse_insn_from_list(lexem_list)
        dst_reg, lexem_list = self.parse_register_from_list(lexem_list)
        lhs, lexem_list = self.parse_register_from_list(lexem_list)
        insn_object = Instruction("movefa", use_list=(lhs), def_list=dst_reg)
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


class RegisterPool:
    def __init__(self, size):
        pass

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

class RegisterAssignator:
    def __init__(self, arch):
        self.arch = arch

    def process_program(self, bundle_list):
        pass

    def generate_liverange_map(self, bundle_list, liverange_map):
        """ generate a dict key -> list of disjoint live-ranges
            mapping each variable to its liverange """
        for index, bundle in enumerate(bundle_list):
            for insn in bundle.insn_list:
                for reg in insn.use_list:
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
                if isinstance(reg, ArchRegister):
                    color_map[reg] = reg.index

            while len(color_map) != len(graph):
                # looking for node with max degree
                max_reg = max([node for node in graph if not node in color_map], key=(lambda reg: len(list(node for node in graph[reg] if not node in color_map))))
                unavailable_color_list = sorted([color_map[neighbour] for neighbour in graph[max_reg] if neighbour in color_map])

                new_color = min(set(range(64)).difference(set(unavailable_color_list)))

                print("register {} of class {} has been assigned color {}".format(max_reg, reg_class.name, new_color))
                color_map[max_reg] = new_color

        return general_color_map

    def check_color_map(self, conflict_graph, color_map):
        for reg in conflict_graph:
            reg_color = color_map[reg]
            for neighbour in conflict_graph[reg]:
                if reg_color == color_map[neighbour]:
                    print("color conflict for {}({}) vs {}({})".format(reg, reg_color, neighbour, color_map[neighbour]))
                    return False
        return True




test_string = """\
add $r4 = $r5, $r5
ld $r4 = $r4[$r12]
;;
movefo A(acc) = $r4, $r2
;;
add R(add) = $r1, $r1
;;
movefa $r2 = A(acc)
;;
add $r3 = R(add), $r2
ld $r4 = $r2[$r12]
;;
add R(beta) = $r4, $r3
;;
add $r0 = R(beta), R(add)
;;
"""

if __name__ == "__main__":
    arch = DummyArchitecture()
    asm_parser = AsmParser(arch)

    print("parsing input program")
    for line_no, line in enumerate(test_string.split("\n")):
        lexem_list = lexer.generate_line_lexems(line)
        dbg_object = DebugObject(line_no)
        asm_parser.parse_asm_line(lexem_list, dbg_object=dbg_object)
    print(asm_parser.program)

    print("Register Assignation")
    reg_assignator = RegisterAssignator(arch)

    empty_liverange_map = LiveRangeMap([Register.Std, Register.Acc])
    print("Declaring pre-defined registers")
    for reg_index in [5, 1, 2, 12]:
        reg = arch.get_unique_reg_object(reg_index, reg_class=Register.Std)
        empty_liverange_map.declare_pre_defined_reg(reg)

    liverange_map = reg_assignator.generate_liverange_map(asm_parser.program, empty_liverange_map)

    print("Declaring post-used registers")
    for reg_index in [0]:
        reg = arch.get_unique_reg_object(reg_index, reg_class=Register.Std)
        liverange_map.declare_post_used_reg(reg)
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

