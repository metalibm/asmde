from arch.dummy import DummyArchitecture

ARCH_CTOR_MAP = {
    "dummy": DummyArchitecture,
}

def parse_architecture(arch_str_desc):
    return ARCH_CTOR_MAP[arch_str_desc]()
