import sys
import argparse

from asmde.allocator import Program, RegisterAssignator, DebugObject
from asmde.parser import AsmParser
from asmde_arch.dummy import DummyArchitecture
from asmde.arch_list import parse_architecture
import asmde.lexer as lexer


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

            if asm_parser.arch.hasBundle():
                print(";;")


    if args.output is None:
        dump_allocation(color_map, lambda s: print(s, end=""))
    else:
        with open(args.output, "w") as output_stream:
            dump_allocation(color_map, lambda s: output_stream.write(s))

    print("dumping program")
    dump_program(asm_parser.program.bb_list, color_map)
