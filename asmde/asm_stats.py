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


    def analyse_program(self, program, verbose=False):
        for bb in program.bb_list:
            for bundle in bb.bundle_list:
                for insn in bundle.insn_list:
                    insn_tag = insn.insn_object
                    if not insn.match_pattern is None:
                        insn_tag = insn_tag + "-" + insn.match_pattern.dump(verbose)
                    self.opc_map[insn_tag] += 1

    def dump(self, print_callback=print):
        print_callback("# Program statistics")
        for opc in self.opc_map:
            print_callback("{count:5} {opc:15}".format(opc=opc, count=self.opc_map[opc]))


if __name__ == "__main__":
    # command line options
    parser = argparse.ArgumentParser()
    parser.add_argument("--lexer-verbose", action="store_const", default=False, const=True, help="enable lexer verbosity")

    parser.add_argument("--output", action="store", default=None, help="select output file (default stdout)")
    parser.add_argument("--allow-error", action="store", default=0, type=int, help="set the number of accepted errors before stopping")
    parser.add_argument("--input", action="store", help="select input file")
    parser.add_argument("--objdump", action="store_const", default=False, const=True, help="indicate that assembly input is in objdump form")
    parser.add_argument("--arch", action="store", default=DummyArchitecture(), type=parse_architecture, help="select target architecture")
    parser.add_argument("--verbose-pattern", action="store_const", default=False, const=True, help="indicate that verbose match pattern must be use to distinguish insn")

    args = parser.parse_args()

    program = Program()
    asm_parser = AsmParser(args.arch, program)

    error_count = 0

    print("parsing input program")
    with open(args.input, "r") as input_stream:
        # TODO/FIXME: optimize file reading (line by line rather than full file at once)
        full_input_file = input_stream.read()
        for line_no, line in enumerate(full_input_file.split("\n")):
            if "file format" in line:
                # skipped line defining file format
                continue
            lexem_list = lexer.generate_line_lexems(line)
            if args.lexer_verbose:
                print(lexem_list)
            dbg_object = DebugObject(line_no)
            if args.allow_error:
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
            else:
                # if no arrow is allowed, we do not try/except to
                # be sure to catch the first error where it's raised
                # which simplify debug (e.g. though pdb)
                if args.objdump:
                    asm_parser.parse_objdump_line(lexem_list, dbg_object=dbg_object)
                else:
                    asm_parser.parse_asm_line(lexem_list, dbg_object=dbg_object)
        # finish program (e.g. connecting last BB to sink)
        asm_parser.program.end_program()

    stats = ProgramStatistics()
    stats.analyse_program(program, args.verbose_pattern)
    if not args.output is None:
        with open(args.output, "w") as out_stream:
            stats.dump(print_callback=(lambda s: out_stream.write(s+"\n")))
    else:
        stats.dump()

