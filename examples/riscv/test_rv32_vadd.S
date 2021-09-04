// testing for basic RISC-V RV32I program
// void vector_add(float* dst, float* src0, float* src1, unsigned n)
//#PREDEFINED(a0, a1, a2, a3)
        .file   "test_vadd.c"
        .option nopic
        .attribute arch, "rv64i2p0_m2p0_a2p0_f2p0_d2p0_c2p0"
        .attribute unaligned_access, 0
        .attribute stack_align, 16
        .text
        .align  1
        .globl  my_vadd
        .type   my_vadd, @function
my_vadd:
		// check for early exit condition n == 0
		beq a3, x0, end
loop:
		// load inputs
		flw F(LHS), 0(a1)
		flw F(RHS), 0(a2)
		// operation
		fadd.s F(ACC), F(LHS), F(RHS)
		// store result
		fsw F(ACC), 0(a0)
		// update addresses
		addi a1, a1, 4
		addi a2, a2, 4
		addi a0, a0, 4
		// update loop count
		addi a3, a3, -1
		// branch if not finished
		bne x0, a3, loop
end:
        ret
        .size   my_vadd, .-my_vadd
        .section        .rodata.str1.8,"aMS",@progbits,1

