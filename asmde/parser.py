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

class ArchRegister(Register):
    def __init__(self, index_range, reg_class=None):
        self.index_range = index_range
        self.reg_class = reg_class

    def __repr__(self):
        return "ArchRegister(index_range={}, class={})".format(self.index_range, self.reg_class)

class VirtualRegister(Register):
    def __init__(self, name, reg_class=None):
        self.name = name
        self.reg_class = reg_class

    def __repr__(self):
        return "VirtualRegister(name={}, class={})".format(self.name, self.reg_class)

class ImmediateValue:
    def __init__(self, value):
        self.value = value


class Architecture:
    def parse_asm_line(self, lexem_list):
        if not len(lexem_list): return
        head = lexem_list[0]
        if isinstance(head, BundleSeparatorLexem):
            print("End of bundle")
        elif isinstance(head, Lexem):
            INSN_PARSING_MAP = {
                "ld": self.parse_load_from_list,
                "add": self.parse_add_from_list
            }
            if head.value in INSN_PARSING_MAP:
                parsing_method = INSN_PARSING_MAP[head.value]
                insn, lexem_list = parsing_method(lexem_list)
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
        assert isinstance(lexem, VirtualRegisterLexem)

        VIRTUAL_REG_PATTERN = "(?P<var_type>[RDQOABCD])\((?P<var_name>\w+)\)"
        reg_match = re.match(VIRTUAL_REG_PATTERN, lexem.value)
        reg_type = reg_match.group("var_type")
        reg_name = reg_match.group("var_name")

        reg_class = {
            "R": Register.Std,
            "A": Register.Acc
        }[reg_type]
        return VirtualRegister(reg_name, reg_class=reg_class)


    def parse_register(self, lexem):
        """ extract the lexem register representing a
            register, return the register object and the remaining
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
            register = ArchRegister(index_range, ArchRegister.Std)
        elif re.fullmatch(ACC_REG_PATTERN, lexem.value):
            register = ArchRegister(index_range, ArchRegister.Acc)
        else:
            raise NotImplementedError

        return register

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

        return (base_addr, offset), lexem_list

    def parse_load_from_list(self, lexem_list):
        insn, lexem_list = self.parse_insn_from_list(lexem_list)
        dst_reg, lexem_list = self.parse_register_from_list(lexem_list)
        addr, lexem_list = self.parse_addr_from_list(lexem_list)
        print("LOAD INSN")
        print("   defs: {}".format(dst_reg))
        print("   uses: {}".format(addr))
        return (insn, dst_reg, addr), lexem_list

    def parse_add_from_list(self, lexem_list):
        insn, lexem_list = self.parse_insn_from_list(lexem_list)
        dst_reg, lexem_list = self.parse_register_from_list(lexem_list)
        lhs, lexem_list = self.parse_register_from_list(lexem_list)
        rhs, lexem_list = self.parse_register_from_list(lexem_list)
        print("ADD INSN")
        print("   defs: {}".format(dst_reg))
        print("   uses: {}".format((lhs, rhs)))
        return (insn, dst_reg, (lhs, rhs)), lexem_list

test_string = """\
ld $r4 = $r2[$r12]
;;
add $r3 = $r2, $r1
;;
add $r3 = R(add), $r1
;;
"""

if __name__ == "__main__":
    print(lexer.RegisterLexem.match("$r12"))
    print(lexer.RegisterLexem.match("$r12[$r2]"))
    print(lexer.OperatorLexem.match("["))
    print(lexer.OperatorLexem.match("]"))
    print(lexer.BundleSeparatorLexem.match(";;"))
    print(lexer.generate_line_lexems(";;"))

    arch = Architecture()

    for line in test_string.split("\n"):
        lexem_list = lexer.generate_line_lexems(line)
        print("lexem_list: ", lexem_list)
        arch.parse_asm_line(lexem_list)

