from asmde_arch.dummy import DummyArchitecture
from asmde_arch.kv3 import KV3Architecture

ARCH_CTOR_MAP = {
    "dummy": DummyArchitecture,
    "kv3": KV3Architecture,
}

def parse_architecture(arch_str_desc):
    return ARCH_CTOR_MAP[arch_str_desc]()
