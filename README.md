# Assembly Development Editor

asmde is a small utility to help developp assembly programs.
It extends assembly syntax with Variable and post-process the program to perform register allocation.

## Tool usage

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
