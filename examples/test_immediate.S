//#PREDEFINED($r0)
ld R(val) = 0[$r0]
;;
ld R(val2) = 17[R(val)]
addd $r6r7 = $r0, R(val)
;;
add R(res) = $r6, $r7
add $r0 = R(val2), $r0
;;
add $r0 = R(res), $r0
;;
//#POSTUSED($r0)
