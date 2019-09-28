//#PREDEFINED($r0)
addd D(d_lo,d_hi) = $r0, $r0
;;
addd $r6r7 = R(d_hi), R(d_lo)
;;
sbf $r6 = $r6, $r7
;;
sbfd $r6r7 = $r6, $r0
;;
//#POSTUSED($r6, $r7)
