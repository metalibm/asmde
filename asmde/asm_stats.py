import argparse
import collections

from asmde.allocator import Program, DebugObject
from asmde.parser import AsmParser
from asmde_arch.dummy import DummyArchitecture
from asmde.arch_list import parse_architecture
import asmde.lexer as lexer


class ProgramStatistics:
    def __init__(self, arch, program_name):
        self.opc_map = collections.defaultdict(lambda: 0)
        self.arch = arch
        self.program_name = program_name


    def analyse_program(self, program, verbose=False):
        for bb in program.bb_list:
            for bundle in bb.bundle_list:
                for insn in bundle.insn_list:
                    insn_tag = insn.insn_object
                    if not insn.match_pattern is None:
                        insn_tag = insn_tag + "-" + insn.match_pattern.dump(verbose)
                    self.opc_map[insn_tag] += 1

    def dump(self, print_callback=print, exhaustive_display=True, csv_format=False):
        """ if <exhaustive_display> is set we display all architecture instructions (even
            those not appearing in the program) are display (with count 0) """
        print_callback("# Program statistics")

        opc_map = set(self.opc_map.keys())
        if exhaustive_display:
            opc_map = opc_map.union(self.arch.get_all_opc())

        for opc in sorted(opc_map, key=lambda k: opc_map[k]):
            if csv_format:
                out_format = "{opc}, {count}"
            else:
                out_format = "{count:5} {opc:15}"
            print_callback(out_format.format(opc=opc, count=self.opc_map[opc]))

    def fuse_in(self, global_map, exhaustive_opc=True):
        """ fuse result of this statistic map into <global_map> """
        opc_map = set(self.opc_map.keys())
        if exhaustive_opc:
            opc_map = opc_map.union(self.arch.get_all_opc())
        for opc in opc_map:
            global_map[opc][self.program_name] = self.opc_map[opc]



if __name__ == "__main__":
    # command line options
    parser = argparse.ArgumentParser()
    parser.add_argument("--lexer-verbose", action="store_const", default=False, const=True, help="enable lexer verbosity")

    parser.add_argument("--output", action="store", default=None, help="select output file (default stdout)")
    parser.add_argument("--allow-error", action="store", default=0, type=int, help="set the number of accepted errors before stopping")
    parser.add_argument("input", action="store", nargs="+", help="list of input files")
    parser.add_argument("--mode", action="store", default="objdump", choices=["objdump", "trace", "asm"], help="indicate assembly parsing mode")
    parser.add_argument("--arch", action="store", default=DummyArchitecture(), type=parse_architecture, help="select target architecture")
    parser.add_argument("--verbose-lexing", action="store_const", default=False, const=True, help="enable verbose lexing (more debug/info/warning messages)")
    parser.add_argument("--verbose-pattern", action="store_const", default=False, const=True, help="indicate that verbose match pattern must be use to distinguish insn")
    parser.add_argument("--display-all-opcodes", action="store_const", default=False, const=True, help="also display zero value count for absent opcodes")
    parser.add_argument("--csv", action="store_const", default=False, const=True, help="output in csv format")

    args = parser.parse_args()


    error_count = 0

    stats = collections.defaultdict(lambda: collections.defaultdict(lambda: 0))

    for input_name in args.input:
        print("parsing input program {}".format(input_name))
        program = Program()
        arch = args.arch()
        asm_parser = AsmParser(arch, program)
        with open(input_name, "r") as input_stream:
            # TODO/FIXME: optimize file reading (line by line rather than full file at once)
            full_input_file = input_stream.read()
            for line_no, line in enumerate(full_input_file.split("\n")):
                if "file format" in line:
                    # skipped line defining file format
                    continue
                lexem_list = lexer.generate_line_lexems(line, verbose=args.verbose_lexing)
                if args.lexer_verbose:
                    print(lexem_list)
                dbg_object = DebugObject(line_no + 1)
                if args.allow_error:
                    try:
                        if args.mode == "objdump":
                            asm_parser.parse_objdump_line(lexem_list, dbg_object=dbg_object)
                        elif args.mode == "trace":
                            asm_parser.parse_trace_line(lexem_list, dbg_object=dbg_object)
                        else:
                            asm_parser.parse_asm_line(lexem_list, dbg_object=dbg_object)
                    except:
                        print("error @line {}, {}".format(line_no, line))
                        print(lexem_list)
                        error_count += 1
                        if error_count > args.allow_error:
                            raise
                else:
                    # if no error is allowed, we do not try/except to
                    # be sure to catch the first error where it's raised
                    # which simplify debug (e.g. through pdb)
                    if args.mode == "objdump":
                        asm_parser.parse_objdump_line(lexem_list, dbg_object=dbg_object)
                    elif args.mode == "trace":
                        asm_parser.parse_trace_line(lexem_list, dbg_object=dbg_object)
                    else:
                        asm_parser.parse_asm_line(lexem_list, dbg_object=dbg_object)
            # finish program (e.g. connecting last BB to sink)
            asm_parser.program.end_program()

        program_stats = ProgramStatistics(arch, input_name)
        program_stats.analyse_program(program, args.verbose_pattern)
        program_stats.fuse_in(stats, exhaustive_opc=args.display_all_opcodes)

    def display_title(print_callback):
        print_callback("# " + ", ".join(args.input))
    def display_opc(print_callback, opc, stats):
        print_callback(opc + " " + ", ".join(str(stats[opc][input_name]) for input_name in args.input))
    def dump_stats(print_callback):
        display_title(print_callback)
        for opc in sorted(stats):
            display_opc(print_callback, opc, stats)

    if not args.output is None:
        with open(args.output, "w") as out_stream:
            dump_stats(lambda s: out_stream.write(s+"\n"))
            #stats.dump(print_callback=(lambda s: out_stream.write(s+"\n")), exhaustive_display=args.display_all_opcodes, csv_format=args.csv)
    else:
        dump_stats(print)
        #stats.dump(exhaustive_display=args.display_all_opcodes, csv_format=args.csv)

