import subprocess


def test_basic():
    test_list = [
        "examples/test_basic.S",
        "examples/test_basic_0.S",
        "examples/test_basic_2.S",
        "examples/test_dual_split_regs.S",
    ]
    for test in test_list:
        print("executing {}".format(test))
        test_ret = subprocess.check_call("python3 asmde/parser.py --input {}".format(test).split(" "))
        print("{} test_ret={}".format(test, test_ret))
        assert test_ret == 0

