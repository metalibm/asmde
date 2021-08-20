// testing for basic RISC-V RV32I program
//#PREDEFINED(a2, a0, x14)
mul a3, a2, x14
mulh X(M), a3, a0
div X(M), X(M), a0
divu X(M), X(M), a0
rem X(M), X(M), a0
remu X(M), X(M), a0
mulhu a1, X(M), a3
mulhsu a0, X(M), a1
//#POSTUSED(a1, a0, a2)
