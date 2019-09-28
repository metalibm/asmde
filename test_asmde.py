import subprocess


def test_basic():
    test_list = [
        "examples/test_basic.S",
        "examples/test_basic_0.S",
        "examples/test_basic_2.S",
        "examples/test_dual_split_regs.S",
        "examples/test_immediate.S",
        "examples/test_extended.S",
    ]
    # testing all available examples
    for test in test_list:
        print("executing {}".format(test))
        test_ret = subprocess.check_call("python3 asmde/parser.py --input {}".format(test).split(" "))
        print("{} test_ret={}".format(test, test_ret))
        assert test_ret == 0

    # testing writing output file
    test_ret = subprocess.check_call("python3 asmde/parser.py --input {} --output {}".format(
        "examples/test_basic_2.S",
        "test_basic_2.regalloc.h").split(" "))
    assert test_ret == 0


if __name__ == "__main__":
    test_basic()
