// testing for basic RISC-V RV32I program
//#PREDEFINED(x0, x1)
flw f0, 16(x0)
flw f2, 0(x1)
fadd.s f2, f2, f0
fmul.s f2, f2, f2
fsub.s f2, f2, f0
fsub.s f2, f2, f0, rtz
fmadd.s f2, f2, f0, f0, rne
//#POSTUSED(f2)
