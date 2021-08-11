// testing for basic RISC-V RV32I program
//#PREDEFINED(a2, a0)
lw a1, 0(a2)
add I(VAR), a0, a1
add a1, I(VAR), a1 
//#POSTUSED(a1, a0, a2)
