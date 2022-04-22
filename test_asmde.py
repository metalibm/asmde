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
        test_ret = subprocess.check_call("python3 asmde.py {}".format(test).split(" "))
        print("{} test_ret={}".format(test, test_ret))
        assert test_ret == 0

    # testing writing output file
    test_ret = subprocess.check_call("python3 asmde.py --output {outFile} {inFile}".format(
        inFile="examples/test_basic_2.S",
        outFile="test_basic_2.regalloc.h").split(" "))
    assert test_ret == 0

def test_trace_parsing():
    # broken because asmde module is not available in default PYTHONPATH
    return
    test_list = [
        ("tests/asm_trace_test.trc", "tests/asmde_trace_test-count.expected"),
    ]

    for test, golden in test_list:
        print("executing {}".format(test))
        test_ret = subprocess.check_call("python3 asmde/asm_stats.py --arch kv3 --input {} --mode trace --output /tmp/asm_test.count".format(test).split(" "))
        print("{} test_ret={}".format(test, test_ret))
        assert test_ret == 0
        test_ret = subprocess.check_call("diff /tmp/asm_test.count {}".format(golden).split(" "))
        print("{} test_ret={}".format(test, test_ret))
        assert test_ret == 0


if __name__ == "__main__":
    test_basic()
    # broken because asmde module is not available in default PYTHONPATH
    # test_trace_parsing()
