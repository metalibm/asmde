Build status: [![Python package](https://github.com/metalibm/asmde/actions/workflows/python-package.yml/badge.svg)](https://github.com/metalibm/asmde/actions/workflows/python-package.yml)

# Assembly Development Editor

asmde is a small set of utilities to help analyse and developp assembly programs.

## Install

```
pip3 install git+https://github.com/metalibm/asmde.git
```

# Assembly statistics

The command `python3 -m asm_stats` parses an input file and generates an histogram of encountered assembly instructions.
It supports source assembly (`--mode asm`), trace (`--mode trace`), objdump parsing (`--mode objdump`).
```
python3 asmde/asm_stats.py --arch <binary-arch> [--mode asm|objdump|trace] <input-file>
```

To objdump a file compatible with the `--mode objdump` you shoud use the following options: `objdump -d --no-addresses --no-show-raw-insn`.

To output an histogram displaying all the architecture instructions (and not just the one encountered in the parsed input) you can add `--display-all-opcodes`.


# Register Assignator
The register assignator is another asmde tools (called directly with `asmde.py`) which perform basic register assignation on an input assembly file with extended syntax.
The extended syntax consists in assembly syntax aumented with Variable and post-process the program to perform register allocation.

### Basic example
The following example parse the assembly template in `test_rv32_0.S` and generates an assembly output with assigned registers.
```
python3 asmde.py -S --arch rv32 examples/riscv/test_rv32_0.S
```

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

# Supported architecture(s)

- RISC-V RV32I, RV32M, RV32F (work in progress)
- Kalray's KV3 VLIW ISA
- Dummy architecture

# Extending asmde
