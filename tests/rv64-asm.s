	.text
	.attribute	4, 16
	.attribute	5, "rv64i2p0_m2p0_a2p0_f2p0_d2p0_c2p0"
	.file	"ml_exp.c"
	.globl	test_wrapper                    # -- Begin function test_wrapper
	.p2align	1
	.type	test_wrapper,@function
test_wrapper:                           # @test_wrapper
# %bb.0:
	addi	sp, sp, -64
	sd	ra, 56(sp)                      # 8-byte Folded Spill
	sd	s0, 48(sp)                      # 8-byte Folded Spill
	sd	s1, 40(sp)                      # 8-byte Folded Spill
	sd	s2, 32(sp)                      # 8-byte Folded Spill
	sd	s3, 24(sp)                      # 8-byte Folded Spill
	fsd	fs0, 16(sp)                     # 8-byte Folded Spill
	fsd	fs1, 8(sp)                      # 8-byte Folded Spill
	fsd	fs2, 0(sp)                      # 8-byte Folded Spill
	li	s2, 0
	lui	a0, %hi(ml_exp_input_table_arg0)
	addi	s1, a0, %lo(ml_exp_input_table_arg0)
	lui	a0, %hi(ml_exp_output_table+4)
	addi	s0, a0, %lo(ml_exp_output_table+4)
	li	s3, 10
.LBB0_1:                                # =>This Inner Loop Header: Depth=1
	flw	fs0, 0(s1)
	fmv.s	fa0, fs0
	call	ml_exp
	flw	fs1, -4(s0)
	flw	fs2, 0(s0)
	feq.s	a1, fs1, fs1
	feq.s	a0, fa0, fa0
	xori	a0, a0, 1
	bnez	a1, .LBB0_4
# %bb.2:                                #   in Loop: Header=BB0_1 Depth=1
	fle.s	a1, fs1, fa0
	bnez	a1, .LBB0_5
.LBB0_3:                                #   in Loop: Header=BB0_1 Depth=1
	beqz	a0, .LBB0_8
	j	.LBB0_6
.LBB0_4:                                #   in Loop: Header=BB0_1 Depth=1
	feq.s	a1, fs2, fs2
	xori	a1, a1, 1
	and	a0, a0, a1
	fle.s	a1, fs1, fa0
	beqz	a1, .LBB0_3
.LBB0_5:                                #   in Loop: Header=BB0_1 Depth=1
	fle.s	a1, fa0, fs2
	or	a0, a0, a1
	beqz	a0, .LBB0_8
.LBB0_6:                                #   in Loop: Header=BB0_1 Depth=1
	addi	s2, s2, 1
	addi	s0, s0, 8
	addi	s1, s1, 4
	bne	s2, s3, .LBB0_1
# %bb.7:
	lui	a0, %hi(.Lstr)
	addi	a0, a0, %lo(.Lstr)
	call	puts@plt
	li	a0, 0
	j	.LBB0_9
.LBB0_8:                                # %.thread
	fcvt.d.s	ft0, fs0
	fcvt.d.s	ft1, fa0
	lui	a0, %hi(.L.str)
	addi	a0, a0, %lo(.L.str)
	sext.w	a1, s2
	fmv.x.d	a2, ft0
	fmv.x.d	a3, ft1
	call	printf
	fcvt.d.s	ft0, fs1
	fcvt.d.s	ft1, fs2
	lui	a0, %hi(.L.str.1)
	addi	a0, a0, %lo(.L.str.1)
	fmv.x.d	a1, ft0
	fmv.x.d	a2, ft1
	call	printf
	li	a0, 1
.LBB0_9:
	ld	ra, 56(sp)                      # 8-byte Folded Reload
	ld	s0, 48(sp)                      # 8-byte Folded Reload
	ld	s1, 40(sp)                      # 8-byte Folded Reload
	ld	s2, 32(sp)                      # 8-byte Folded Reload
	ld	s3, 24(sp)                      # 8-byte Folded Reload
	fld	fs0, 16(sp)                     # 8-byte Folded Reload
	fld	fs1, 8(sp)                      # 8-byte Folded Reload
	fld	fs2, 0(sp)                      # 8-byte Folded Reload
	addi	sp, sp, 64
	ret
.Lfunc_end0:
	.size	test_wrapper, .Lfunc_end0-test_wrapper
                                        # -- End function
	.section	.sdata,"aw",@progbits
	.p2align	2                               # -- Begin function ml_exp
.LCPI1_0:
	.word	0x42b20000                      # float 89
.LCPI1_1:
	.word	0xc2d00000                      # float -104
.LCPI1_2:
	.word	0x3fb8aa3b                      # float 1.44269502
.LCPI1_3:
	.word	0xbf317000                      # float -0.693115234
.LCPI1_4:
	.word	0xb805fdf4                      # float -3.19461833E-5
.LCPI1_5:
	.word	0x3f000000                      # float 0.5
.LCPI1_6:
	.word	0x3e2aaa46                      # float 0.166665167
.LCPI1_7:
	.word	0x3d2aaa67                      # float 0.0416664146
.LCPI1_8:
	.word	0x3c091e81                      # float 0.0083690891
.LCPI1_9:
	.word	0x3ab6b3a4                      # float 0.00139390351
.LCPI1_10:
	.word	0x3f800000                      # float 1
.LCPI1_11:
	.word	0x28800000                      # float 1.42108547E-14
.LCPI1_12:
	.word	0x79000000                      # float 4.15383749E+34
.LCPI1_13:
	.word	0x7f800000                      # float +Inf
.LCPI1_14:
	.word	0x7fc00000                      # float NaN
	.text
	.globl	ml_exp
	.p2align	1
	.type	ml_exp,@function
ml_exp:                                 # @ml_exp
# %bb.0:
	addi	sp, sp, -16
	sd	ra, 8(sp)                       # 8-byte Folded Spill
	fsd	fs0, 0(sp)                      # 8-byte Folded Spill
	fmv.x.w	a0, fa0
	lui	a1, 522240
	and	a2, a0, a1
	beq	a2, a1, .LBB1_6
# %bb.1:
	lui	a0, %hi(.LCPI1_0)
	flw	ft0, %lo(.LCPI1_0)(a0)
	flt.s	a0, ft0, fa0
	bnez	a0, .LBB1_9
# %bb.2:
	lui	a0, %hi(.LCPI1_1)
	flw	ft0, %lo(.LCPI1_1)(a0)
	flt.s	a0, fa0, ft0
	bnez	a0, .LBB1_12
# %bb.3:
	lui	a0, %hi(.LCPI1_2)
	flw	ft0, %lo(.LCPI1_2)(a0)
	fmul.s	ft0, fa0, ft0
	#APP
	fcvt.w.s	a1, ft0, rne
	#NO_APP
	sext.w	a0, a1
	slti	a2, a0, 128
	#APP
	fcvt.w.s	a3, ft0, rne
	#NO_APP
	lui	a4, %hi(.LCPI1_3)
	flw	ft0, %lo(.LCPI1_3)(a4)
	lui	a4, %hi(.LCPI1_4)
	flw	ft1, %lo(.LCPI1_4)(a4)
	sext.w	a4, a3
	fcvt.s.w	ft2, a3
	fmul.s	ft0, ft2, ft0
	fadd.s	ft0, fa0, ft0
	fmul.s	ft1, ft2, ft1
	fadd.s	ft2, ft1, ft0
	lui	a3, %hi(.LCPI1_5)
	flw	ft3, %lo(.LCPI1_5)(a3)
	fmul.s	ft4, ft2, ft2
	lui	a3, %hi(.LCPI1_6)
	flw	ft5, %lo(.LCPI1_6)(a3)
	fmul.s	ft3, ft4, ft3
	lui	a3, %hi(.LCPI1_7)
	flw	ft6, %lo(.LCPI1_7)(a3)
	fmul.s	ft5, ft4, ft5
	fmul.s	ft5, ft2, ft5
	fadd.s	ft3, ft3, ft5
	fmul.s	ft5, ft4, ft6
	fmul.s	ft5, ft4, ft5
	fadd.s	ft3, ft5, ft3
	lui	a3, %hi(.LCPI1_8)
	flw	ft5, %lo(.LCPI1_8)(a3)
	lui	a3, %hi(.LCPI1_9)
	flw	ft6, %lo(.LCPI1_9)(a3)
	li	a3, -126
	slt	a3, a3, a4
	and	a2, a2, a3
	fmul.s	ft5, ft4, ft5
	fmul.s	ft6, ft4, ft6
	fmul.s	ft6, ft2, ft6
	fadd.s	ft5, ft5, ft6
	fmul.s	ft2, ft2, ft4
	fmul.s	ft2, ft2, ft5
	lui	a3, %hi(.LCPI1_10)
	flw	ft4, %lo(.LCPI1_10)(a3)
	fadd.s	ft2, ft3, ft2
	fadd.s	ft1, ft1, ft2
	fadd.s	ft0, ft0, ft1
	fadd.s	ft0, ft0, ft4
	slliw	a1, a1, 23
	beqz	a2, .LBB1_13
# %bb.4:
	lui	a0, 260096
	add	a0, a0, a1
	lui	a1, 522240
	and	a0, a0, a1
	fmv.w.x	ft1, a0
	fmul.s	fs0, ft0, ft1
.LBB1_5:                                # %.critedge364
	fmv.s	fa0, fs0
	ld	ra, 8(sp)                       # 8-byte Folded Reload
	fld	fs0, 0(sp)                      # 8-byte Folded Reload
	addi	sp, sp, 16
	ret
.LBB1_6:
	lui	a1, 2048
	addiw	a1, a1, -1
	and	a1, a1, a0
	beqz	a1, .LBB1_17
# %bb.7:
	lui	a1, %hi(.LCPI1_14)
	flw	fs0, %lo(.LCPI1_14)(a1)
	lui	a1, 1024
	and	a0, a0, a1
	bnez	a0, .LBB1_5
# %bb.8:
	li	a0, 16
	j	.LBB1_16
.LBB1_9:
	li	a0, 1
	call	feraiseexcept
.LBB1_10:
	li	a0, 4
	call	feraiseexcept
.LBB1_11:                               # %.critedge
	lui	a0, %hi(.LCPI1_13)
	flw	fs0, %lo(.LCPI1_13)(a0)
	j	.LBB1_5
.LBB1_12:
	li	a0, 1
	call	feraiseexcept
	li	a0, 2
	call	feraiseexcept
	fmv.w.x	fs0, zero
	j	.LBB1_5
.LBB1_13:
	li	a2, 128
	bge	a0, a2, .LBB1_18
# %bb.14:
	lui	a0, 354304
	add	a0, a0, a1
	lui	a1, %hi(.LCPI1_11)
	flw	ft1, %lo(.LCPI1_11)(a1)
	lui	a1, 522240
	and	a0, a0, a1
	fmv.w.x	ft2, a0
	fmul.s	ft0, ft0, ft2
	fmul.s	fs0, ft0, ft1
	fmv.x.w	a0, fs0
	and	a0, a0, a1
	bnez	a0, .LBB1_5
# %bb.15:
	li	a0, 2
.LBB1_16:                               # %.critedge364
	call	feraiseexcept
	j	.LBB1_5
.LBB1_17:                               # %.critedge
	fmv.w.x	fs0, zero
	fle.s	a0, fs0, fa0
	beqz	a0, .LBB1_5
	j	.LBB1_11
.LBB1_18:
	lui	a0, 24576
	add	a0, a0, a1
	lui	a1, 522240
	lui	a2, %hi(.LCPI1_12)
	flw	ft1, %lo(.LCPI1_12)(a2)
	and	a0, a0, a1
	fmv.w.x	ft2, a0
	fmul.s	ft0, ft0, ft2
	fmul.s	fs0, ft0, ft1
	fmv.x.w	a0, fs0
	lui	a2, 524288
	addiw	a2, a2, -1
	and	a0, a0, a2
	bne	a0, a1, .LBB1_5
	j	.LBB1_10
.Lfunc_end1:
	.size	ml_exp, .Lfunc_end1-ml_exp
                                        # -- End function
	.globl	main                            # -- Begin function main
	.p2align	1
	.type	main,@function
main:                                   # @main
# %bb.0:
	addi	sp, sp, -16
	sd	ra, 8(sp)                       # 8-byte Folded Spill
	call	test_wrapper
	snez	a0, a0
	ld	ra, 8(sp)                       # 8-byte Folded Reload
	addi	sp, sp, 16
	ret
.Lfunc_end2:
	.size	main, .Lfunc_end2-main
                                        # -- End function
	.type	ml_exp_output_table,@object     # @ml_exp_output_table
	.data
	.globl	ml_exp_output_table
	.p2align	2
ml_exp_output_table:
	.word	0x3f800000                      # float 1
	.word	0x3f800000                      # float 1
	.word	0x3f800000                      # float 1
	.word	0x3f800000                      # float 1
	.word	0x3f800000                      # float 1
	.word	0x3f800001                      # float 1.00000012
	.word	0x3f800000                      # float 1
	.word	0x3f800000                      # float 1
	.word	0x3f800000                      # float 1
	.word	0x3f800000                      # float 1
	.word	0x3f800000                      # float 1
	.word	0x3f800000                      # float 1
	.word	0x3f800002                      # float 1.00000024
	.word	0x3f800003                      # float 1.00000036
	.word	0x3f800000                      # float 1
	.word	0x3f800000                      # float 1
	.word	0x3f800000                      # float 1
	.word	0x3f800001                      # float 1.00000012
	.word	0x3f800000                      # float 1
	.word	0x3f800000                      # float 1
	.size	ml_exp_output_table, 80

	.type	ml_exp_input_table_arg0,@object # @ml_exp_input_table_arg0
	.section	.rodata,"a",@progbits
	.p2align	2
ml_exp_input_table_arg0:
	.word	0x00000000                      # float 0
	.word	0x00000000                      # float 0
	.word	0x2e4eff56                      # float 4.7065761E-11
	.word	0x00000000                      # float 0
	.word	0x00000000                      # float 0
	.word	0x00000000                      # float 0
	.word	0x3499cebd                      # float 2.86488927E-7
	.word	0x00000000                      # float 0
	.word	0x106bbdea                      # float 4.64918827E-29
	.word	0x00000000                      # float 0
	.size	ml_exp_input_table_arg0, 40

	.type	.L.str,@object                  # @.str
	.section	.rodata.str1.1,"aMS",@progbits,1
.L.str:
	.asciz	"error[%d]: ml_exp(%a), result is %a vs expected "
	.size	.L.str, 49

	.type	.L.str.1,@object                # @.str.1
.L.str.1:
	.asciz	"[%a;%a]\n"
	.size	.L.str.1, 9

	.type	.Lstr,@object                   # @str
.Lstr:
	.asciz	"test successful ml_exp"
	.size	.Lstr, 23

	.ident	"clang version 14.0.0 (https://github.com/llvm/llvm-project.git 5c27740238007d22f2d0cd0ebe2aaffa90a9c92b)"
	.section	".note.GNU-stack","",@progbits
	.addrsig
