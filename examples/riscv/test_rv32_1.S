// testing for basic RISC-V RV32I program
//#PREDEFINED(a2, a0, x14)
lw a1, 0(a2)
add a0, a0, a4
add I(var), a0, a1
add a2, I(var), a0
add a1, I(var), a1
add a6, x14, x10
add a1, a1, x16
//#POSTUSED(a1, a0, a2)
