// testing for basic RISC-V RV32I program
//#PREDEFINED(a2, a0)
label:
bne a0, a2, label
beq a0, a2, label
lw a1, 0(a2)
add I(VAR), a0, a1
addi I(VAR), I(VAR), 7
sw I(VAR), -4(a2)
add a1, I(VAR), a1 
slti a0, a2, 7
slt a1, a1, I(VAR)
fence rw, rw
fence rwi, rwo
ebreak
ecall
lui a2, 17
auipc a4, 12
add a0, a0, a4
sw a1, 0(a1)
jalr a1, a0, 17
jal a0, 1337
//#POSTUSED(a1, a0, a2)
