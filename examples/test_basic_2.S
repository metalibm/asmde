// testing for static acc registers
//#PREDEFINED($r5, $r2, $r1, $r12)
add R(p) = $r5, $r5
;;
ld R(p) = R(p)[$r12]
;;
movefo $a0 = R(p), $r2
;;
add R(add) = $r1, $r1
;;
start_label:
addd D(d_lo,d_hi) = $r1, $r1
;;
addd $r6r7 = R(d_hi), R(d_lo)
;;
movefa $r2 = $a0
;;
add $r3 = R(add), $r6
ld R(p) = $r2[$r12]
;;
add R(beta) = R(p), $r3
;;
end_label:
add $r0 = R(beta), R(add)
;;
//#POSTUSED($r0, $r7)
