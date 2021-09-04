import sys
import argparse

from asmde.allocator import Program, RegisterAssignator, DebugObject
from asmde.parser import AsmParser
from asmde_arch.dummy import DummyArchitecture
from asmde.arch_list import parse_architecture, ARCH_CTOR_MAP
import asmde.lexer as lexer


if __name__ == "__main__":
    # command line options
    parser = argparse.ArgumentParser()
    parser.add_argument("--lexer-verbose", action="store_const", default=False, const=True, help="enable lexer info/debug message display")
    parser.add_argument("--usedef-verbose", action="store_const", default=False, const=True, help="enable use-def evaluation info/message display")
    parser.add_argument("--parser-verbose", action="store_const", default=False, const=True, help="enable parser debug/info message display")
    parser.add_argument("--verbose", action="store_const", default=False, const=True, help="enable general debug/info message display")

    parser.add_argument("--output", action="store", default=None, help="select output file (default stdout)")
    parser.add_argument("-S", dest='asm_dump', action="store_const", default=False, const=True,
                        help="select assigned assembly output")
    parser.add_argument("input", help="input file")
    parser.add_argument("--arch", action="store", default=DummyArchitecture,
                                  type=parse_architecture, help="select target architecture")

    args = parser.parse_args()

    verbose = args.verbose
    # instantiating architecture
    arch = args.arch()

    program = Program()
    asm_parser = AsmParser(arch, program, args.parser_verbose)

    if verbose: print("parsing input program")
    with open(args.input, "r") as input_stream:
        # TODO/FIXME: optimize file reading (line by line rather than full file at once)
        full_input_file = input_stream.read()
        for line_no, line in enumerate(full_input_file.split("\n")):
            lexem_list = lexer.generate_line_lexems(line)
            if args.lexer_verbose:
                print(lexem_list)
            dbg_object = DebugObject(line_no)
            asm_parser.parse_asm_line(lexem_list, dbg_object=dbg_object, src_line=line)
        # finish program (e.g. connecting last BB to sink)
        asm_parser.program.end_program()
        if verbose:
            print(asm_parser.program.bb_list)
            for label in asm_parser.program.bb_label_map:
                print("label: {}".format(label))
                print(asm_parser.program.bb_label_map[label].bundle_list)
    # manage file I/O exception

    if verbose: print("Register Assignation")
    reg_assignator = RegisterAssignator(arch)

    empty_liverange_map = arch.get_empty_liverange_map()

    var_ins, var_out = reg_assignator.generate_use_def_lists(asm_parser.program, verbose=args.usedef_verbose)
    liverange_map = reg_assignator.generate_liverange_map(asm_parser.program, empty_liverange_map, var_ins, var_out)

    if verbose: print("Checking pre-defined register consistency")
    for reg in program.pre_defined_list:
        if not reg in var_out[program.source_bb]:
            print("{} is declared in pre-defined list but not alive at program source".format(reg))
            sys.exit(1)
    for reg in var_out[program.source_bb]:
        if not reg in program.pre_defined_list and not reg.const:
            print("{} is alive at program source but not declared in pre-defined list".format(reg))
            sys.exit(1)
    if verbose:
        print("Variable alive at source BB: {}".format([reg for reg in var_out[program.source_bb]]))
        print("Variable alive at sink BB: {}".format([reg for reg in var_ins[program.sink_bb]]))

    if verbose: print("Checking liveranges")
    liverange_status = reg_assignator.check_liverange_map(liverange_map)
    if verbose: print(liverange_status)
    if not liverange_status:
        pass

    if verbose: print("Graph coloring")
    conflict_map = reg_assignator.create_conflict_map(liverange_map)
    color_map = reg_assignator.create_color_map(conflict_map)
    for reg_class in conflict_map:
        conflict_graph = conflict_map[reg_class]
        class_color_map = color_map[reg_class]
        check_status = reg_assignator.check_color_map(conflict_graph, class_color_map)
        if not check_status:
            print("register assignation for class {} does is not valid")
            sys.exit(1)

    def dump_allocation(program, arch, color_map, output_callback):
        """ dump virtual register allocation mapping """
        if verbose: print("dumping allocation")
        for reg_class in color_map:
            for reg in color_map[reg_class]:
                if reg.is_virtual():
                    output_callback("#define {} {}\n".format(reg.name, color_map[reg_class][reg]))

    def dump_program(program, arch, color_map, dumpFunction):
        """ dump whole program with assigned registers """
        if verbose: print("dumping program")
        for elt in program.program_seq:
            dumpFunction(elt.dump(arch, color_map) + "\n")

    # selection of the output generation function
    if args.asm_dump:
        outGen = dump_program
    else:
        outGen = dump_allocation

    # setting dump function
    if args.output is None:
        # defaulting to stdout
        dumpFunction = lambda s: print(s, end="")
        outGen(program, arch, color_map, dumpFunction)
    else:
        with open(args.output, "w") as output_stream:
            outGen(program, arch, color_map, lambda s: output_stream.write(s))
