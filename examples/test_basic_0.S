// testing for static acc registers
//#PREDEFINED($r2, $r0)
add $r1 = $r0, $r2
;;
movefo $a0 = $r1, $r1
;;
//#POSTUSED($a0)
