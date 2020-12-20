Build status: [![Build Status](https://travis-ci.org/nibrunie/asmde.svg?branch=master)](https://travis-ci.org/nibrunie/asmde)

# Assembly Development Editor

asmde is a small set of utilities to help analyse and developp assembly programs.

# Assembly statistics

The command `asm_stats.py` parses an input file and generate an histogram of encountered assembly instructions.
It supports both source assembly or objdump generation (with `--objdump` option).
```
python3 asmde/asm_stats.py --arch <binary-arch> [--objdump] -input <input-file>
```

To objdump a file compatible with the `--objdump` you shoud use the following options: ` -d --no-addresses --no-show-raw-insn`.


# Register Assignator
The register assignator is another asmde tools (called directly with `asmde.py`) which perform basic register assignation on an input assembly file with extended syntax.
The extended syntax consists in assembly syntax aumented with Variable and post-process the program to perform register allocation.

### Command line options

--lexer-verbose: enable display of lexer information messages

## Assembly language extension

### Variables

A variable corresponds virtual register.

Current version support `R(<varname>)` and `A(<varname>)` targetting two distinct register files.

### Macros

A macro starts with `//#`

List of supported macros:
- PREDEFINED <list or registers>   add the registers in the list to the list of registers defined before program starts (e.g. function arguments)
- POSTUSED   <list of registers>   add the registers in the list to the list of registers usedafter program ends (e.g. function results)

# Extending asmde
