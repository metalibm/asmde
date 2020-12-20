import argparse
import collections

from asmde.allocator import Program, DebugObject
from asmde.parser import AsmParser
from arch.dummy import DummyArchitecture
from asmde. arch_list import parse_architecture
import asmde.lexer as lexer


class ProgramStatistics:
    def __init__(self):
        self.opc_map = collections.defaultdict(lambda: 0)


    def analyse_program(self, program):
        for bb in program.bb_list:
            for bundle in bb.bundle_list:
                for insn in bundle.insn_list:
                    self.opc_map[insn.insn_object] += 1

    def dump(self):
        print("Program statistics")
        for opc in self.opc_map:
            print("{opc:10} {count}".format(opc=opc, count=self.opc_map[opc]))


if __name__ == "__main__":
    # command line options
    parser = argparse.ArgumentParser()
    parser.add_argument("--lexer-verbose", action="store_const", default=False, const=True, help="enable lexer verbosity")

    parser.add_argument("--output", action="store", default=None, help="select output file (default stdout)")
    parser.add_argument("--allow-error", action="store", default=0, type=int, help="set the number of accepted errors before stopping")
    parser.add_argument("--input", action="store", help="select input file")
    parser.add_argument("--objdump", action="store_const", default=False, const=True, help="indicate that assembly input is in objdump form")
    parser.add_argument("--arch", action="store", default=DummyArchitecture(), type=parse_architecture, help="select target architecture")

    args = parser.parse_args()

    program = Program()
    asm_parser = AsmParser(args.arch, program)

    error_count = 0

    print("parsing input program")
    with open(args.input, "r") as input_stream:
        # TODO/FIXME: optimize file reading (line by line rather than full file at once)
        full_input_file = input_stream.read()
        for line_no, line in enumerate(full_input_file.split("\n")):
            lexem_list = lexer.generate_line_lexems(line)
            if args.lexer_verbose:
                print(lexem_list)
            dbg_object = DebugObject(line_no)
            try:
                if args.objdump:
                    asm_parser.parse_objdump_line(lexem_list, dbg_object=dbg_object)
                else:
                    asm_parser.parse_asm_line(lexem_list, dbg_object=dbg_object)
            except:
                print("error @line {}, {}".format(line_no, line))
                print(lexem_list)
                error_count += 1
                if error_count > args.allow_error:
                    raise
        # finish program (e.g. connecting last BB to sink)
        asm_parser.program.end_program()
        print(asm_parser.program.bb_list)
        for label in asm_parser.program.bb_label_map:
            print("label: {}".format(label))
            print(asm_parser.program.bb_label_map[label].bundle_list)

    stats = ProgramStatistics()
    stats.analyse_program(program)
    stats.dump()

