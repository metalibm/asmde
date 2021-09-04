import collections

class Register:
    """ main class for Register objects """
    class RegClass:
        """ class of registers """
        @classmethod
        def build_multi_reg(reg_class, reg_list):
            """ build a multi-reg register from a list of physical registers """
            return MultiArchRegister(reg_list, reg_class)
        @classmethod
        def get_single_phy_reg_repr(reg_class, phys_reg):
            """ build a string representation for a single physical register """
            return reg_class.prefix + reg_class.reg_prefix + str(phys_reg.index)
        @classmethod
        def get_single_virt_reg_repr(reg_class, virt_reg):
            """ build a string representation for a single virtual register """
            return reg_class.prefix + reg_class.reg_prefix + "<{}>".format(virt_reg.name)
        @classmethod
        def get_alias_phy_reg_repr(reg_class, alias_reg):
            """ build a string representation for a single alias register """
            return reg_class.prefix + alias_reg.aliasSpec + str(alias_reg.aliasIndex)
        @classmethod
        def aliasResolution(cls, spec, index):
            """ return tuple (isAlias, physical_index) """
            return False, index
    class Std(RegClass):
        name = "Std"
        prefix = "$"
        reg_prefix = "r"
    class Acc(RegClass):
        name = "Acc"
        prefix = "$"
        reg_prefix = "a"
    class Special(RegClass):
        name = "Special"
        prefix = "$"
        reg_prefix = ""

    def is_virtual(self):
        """ predicate indicating if register is virtual (or physical) """
        return False
    def is_special(self):
        """ Predicate indicating if register belongs to a special/system
            register file """
        return False
    @property
    def baseReg(self):
        """ return the corresponding underlying base register.
             This is used to share a single register object between aliases """
        return self


class MultiArchRegister:
    """ register formed by concatening multiple regsiters """
    def __init__(self, reg_list, reg_class):
        self.reg_list = reg_list
        self.reg_class = reg_class

    def __repr__(self):
        return "{prefix}{reg_list}".format(
            prefix=self.reg_class.prefix,
            reg_list="".join("%s%d" % (self.reg_class.reg_prefix, reg.index) for reg in self.reg_list)
        )


class PhysicalRegister(Register):
    """ Physical register """
    def __init__(self, index, reg_class=None, const=False):
        self.index = index
        self.reg_class = reg_class
        # is the register constant ?
        self.const = const

    def __repr__(self):
        return self.reg_class.get_single_phy_reg_repr(self)

    def is_virtual(self):
        return False

    def instanciate(self, color_map):
        return self


class PhysicalRegisterAlias(PhysicalRegister):
    """ Alias / secundary name for a physical register """
    def __init__(self, physReg, aliasIndex, aliasSpec, reg_class):
        PhysicalRegister.__init__(self, physReg.index, reg_class)
        self.physReg = physReg
        self.aliasIndex = aliasIndex
        self.aliasSpec = aliasSpec

    def __repr__(self):
        return self.reg_class.get_alias_phy_reg_repr(self)


    @property
    def baseReg(self):
        return self.physReg

class SpecialRegister(Register):
    """ Physical register """
    def __init__(self, tag, reg_class=None):
        self.tag = tag
        self.reg_class = reg_class

    def __repr__(self):
        return self.reg_class.get_single_phy_reg_repr(self)

    def is_special(self):
        return True

    def instanciate(self, color_map):
        return self

# linked register
# register that must be assigned while enforcing a common constraint
# (e.g. contiguous)

def no_constraint(index):
    return True

def modulo_indexed_register(modulo, value):
    """ generate a predicate such a register <index>
        must match <index> % modulo == value """
    return lambda index: (index % modulo) == value
def odd_indexed_register(index):
    return (index % 2) == 1
def even_indexed_register(index):
    return (index % 2) == 0

class VirtualRegister(Register):
    """ Virtual register """
    def __init__(self, name, reg_class=None, constraint=no_constraint, linked_registers=None):
        self.name = name
        self.reg_class = reg_class
        # predicate to be enforced when assigning a physical register index
        # to this virtual register: lambda index: bool
        self.constraint = constraint
        # list of pairs (register, index_generator)
        # where index_generator is lambda color_map: list which generates a iist of
        # possible valid indexes for self register
        self.linked_registers = {} if linked_registers is None else linked_registers

    def get_linked_map(self):
        return self.linked_registers

    def add_linked_register(self, reg, index_generator):
        self.linked_registers[reg] = index_generator

    def is_virtual(self):
        return True

    def __repr__(self):
        return self.reg_class.get_single_virt_reg_repr(self)

    def instanciate(self, color_map):
        return PhysicalRegister(color_map[self.reg_class][self], self.reg_class)


class ImmediateValue:
    """ Immediate (numerical) value """
    def __init__(self, value):
        self.value = value

    def instanciate(self, color_map):
        return self

    def __repr__(self):
        return "%d" % self.value

class DebugObject:
    """ Structure to store and forwared debug information """
    def __init__(self, src_line, src_file=None):
        self.src_file = src_file
        self.src_line = src_line

    def __repr__(self):
        return "Dbg(lineno={})".format(self.src_line)

    def __str__(self):
        return "line {}".format(self.src_line)

class Instruction:
    def __init__(self, insn_object, def_list=None, use_list=None, dbg_object=None, dump_pattern=None, is_jump=False, match_pattern=None, jump_label=None):
        self.insn_object = insn_object
        self.def_list = [] if def_list is None else def_list
        self.use_list = [] if use_list is None else use_list
        self.dbg_object = dbg_object
        # function (use_list, def_list) -> instruction string
        self.dump_pattern = dump_pattern
        self.is_jump = is_jump
        self.jump_label = jump_label
        # information on pattern used to match the instruction in the input
        # (if any)
        self.match_pattern = match_pattern

    def __repr__(self):
        return self.insn_object

class Bundle:
    def __init__(self, insn_list=None):
        self.insn_list = [] if insn_list is None else insn_list

    def add_insn(self, insn):
        self.insn_list.append(insn)

    def __len__(self):
        return len(self.insn_list)

    def __repr__(self):
        return "Bundle({})".format(self.insn_list)

    @property
    def use_list(self):
        return set(sum([insn.use_list for insn in self.insn_list], []))
    @property
    def def_list(self):
        return set(sum([insn.def_list for insn in self.insn_list], []))

    @property
    def has_jump(self):
        return any(insn.is_jump for insn in self.insn_list)



class RegFile:
    def __init__(self, description):
        self.description = description
        self.physical_pool = dict((i, self.description.reg_ctor(i, description.reg_class)) for i in range(self.description.num_phys_reg))
        self.virtual_pool = {}

    def get_phys_index(self, index, spec=None):
        """ translate an index and a specifier into an actual physical index
            (e.g. RV32I "t, 0 -> (x)5"""
        return index

    def get_unique_phys_reg_object(self, index, spec=None):
        isAlias, phys_index = self.description.reg_class.aliasResolution(spec, index)
        if phys_index > self.description.num_phys_reg:
            print("regfile for class {} contains only {} register(s), request for index: {}".format(self.description.reg_class.name, self.description.num_phys_reg, index))
            raise Exception()
        physReg = self.physical_pool[phys_index]
        if isAlias:
            return PhysicalRegisterAlias(physReg, index, spec, self.description.reg_class)
        else:
            return physReg

    def get_unique_virt_reg_object(self, var_name, reg_constraint=no_constraint):
        if not var_name in self.virtual_pool:
            self.virtual_pool[var_name] = VirtualRegister(var_name, self.description.reg_class, constraint=reg_constraint)
        return self.virtual_pool[var_name]

    def get_max_phys_register_index(self):
        return self.description.num_phys_reg - 1

class SpecialRegFile(RegFile):
    def __init__(self, description):
        self.description = description
        self.special_pool = {}
    def get_special_reg_object(self, tag):
        if not tag in self.special_pool:
            self.special_pool[tag] = PhysicalRegister(tag, self.description.reg_class)
        return self.special_pool[tag]
        
class RegFileDescription:
    """ descriptor of a register file object """
    def __init__(self, reg_class, num_phys_reg, reg_ctor, virtual_reg_ctor, reg_file_class=RegFile):
        self.reg_class = reg_class
        self.num_phys_reg = num_phys_reg
        self.reg_ctor = reg_ctor
        self.virtual_reg_ctor = virtual_reg_ctor
        self.reg_file_class = reg_file_class

class Architecture:
    """ Base class for architecture description """
    def __init__(self, reg_file_description_set, insn_patterns):
        self.reg_pool = dict((reg_desc.reg_class, reg_desc.reg_file_class(reg_desc)) for reg_desc in reg_file_description_set)
        # table (insn pattern) -> Pattern
        self.insn_patterns = insn_patterns

    def get_max_register_index_by_class(self, reg_class):
        return self.reg_pool[reg_class].get_max_phys_register_index()

    def get_unique_phys_reg_object(self, index, reg_class, spec=None):
        return self.reg_pool[reg_class].get_unique_phys_reg_object(index, spec=spec)

    def get_special_reg_object(self, tag, reg_class=Register.Special):
        assert reg_class is Register.Special
        return self.reg_pool[reg_class].get_special_reg_object(tag)

    def get_unique_virt_reg_object(self, var_name, reg_class, reg_constraint=no_constraint):
        return self.reg_pool[reg_class].get_unique_virt_reg_object(var_name, reg_constraint=reg_constraint)

    def get_empty_liverange_map(self):
        return LiveRangeMap(self.reg_pool.keys())

    def getPhyRegPatternList(self):
        return []

    def hasBundle(self):
        return False

class BasicBlock:
    index_count = 0
    per_index_map = {}

    def __init__(self, label="undef"):
        # list of predecessors
        self.preds = []
        # list of successors
        self.succs = []
        # index in program order
        self.index = BasicBlock.get_new_index()

        self.label = label

        # ensuring index unicity
        assert (not self.index in BasicBlock.per_index_map)
        # registering block into class map
        BasicBlock.per_index_map[self.index] = self

        self.bundle_list = []
        self.label_list = []


    def __repr__(self):
        return "BB {}".format(self.label)

    @staticmethod
    def get_new_index():
        """ Create a new (unique) index for a BB """
        new_index = BasicBlock.index_count
        BasicBlock.index_count += 1
        return new_index

    @property
    def empty(self):
        return len(self.bundle_list) == 0

    @property
    def fallback(self):
        """ basic block fall backs to the next one if it does not end with
            a jump """
        return not self.bundle_list[-1].has_jump

    def add_bundle(self, bundle):
        self.bundle_list.append(bundle)

    def add_label(self, label):
        self.label_list.append(label)

    def add_predecessor(self, pred):
        self.preds.append(pred)
    def add_successor(self, succ):
        self.succs.append(succ)

    def connect_to(self, succ):
        succ.add_predecessor(self)
        self.add_successor(succ)


    def merge_in(self, merged_bb):
        """ Merge self and merged_bb basic-block into self """
        self.preds += merged_bb.preds
        self.succs += merged_bb.succs
        assert (self.bundle_list == [] or merged_bb.bundle_list == [])
        self.bundle_list = self.bundle_list or merged_bb.bundle_list
        if not (self.index is None or merged_bb.index is None):
            print("[WARNING] duplicate index for bb {}/{} in BasicBlock.merge_in".format(self, merged_bb)) 
        self.index = self.index or merged_bb.index


class Program:
    def __init__(self, pre_defined_list=None, post_used_list=None, empty=False):
        self.pre_defined_list = [] if pre_defined_list is None else pre_defined_list
        self.post_used_list = [] if post_used_list is None else post_used_list
        self.bb_list = []
        self.bb_label_map = {}
        self.source_bb = self.add_bb("source")
        self.sink_bb = self.add_bb("sink")
        if not empty:
            self.current_bb = self.add_bb()
            self.source_bb.connect_to(self.current_bb)
        else:
            self.current_bb = None

        # dict <label_name> : program offset (in bundles)
        #self.label_map = {}


    def add_bundle(self, bundle):
        self.current_bb.add_bundle(bundle)
        # self.bundle_list.append(bundle)

    def add_bb(self, label="undef"):
        """ add a new BasicBlock without modifying self.current_bb reference """
        new_bb = BasicBlock(label)
        self.bb_list.append(new_bb)
        return new_bb

    def add_new_current_bb(self, label="undef"):
        self.current_bb = self.add_bb(label)
        return self.current_bb

    def end_program(self):
        """ end current program, check if last BB is a fallback and connect it to sink if required """
        if self.current_bb != self.sink_bb and self.current_bb.fallback:
            self.current_bb.connect_to(self.sink_bb)

    def get_bb_by_label(self, label):
        """ search if label is already linked to a BasicBlock,
            if so returns it, else create one """
        if not label in self.bb_label_map:
            self.bb_label_map[label] = self.add_bb(label)
        return self.bb_label_map[label]

    def add_label(self, label, offset=None):
        """ Declare a new label @p label, if offset is None
            the offset associated with the label is the current program index
            (end of program) else @p offset value is used directly """
        if not self.current_bb.empty:
            # finishing previous BB and opening a new one
            previous_bb = self.current_bb
            self.current_bb = self.add_bb(label)
            if previous_bb.fallback:
                previous_bb.connect_to(self.current_bb)
        if label in self.bb_label_map:
            # merging several basic-blocks
            self.current_bb.merge_in(self.bb_label_map[label])
            for bb_label in self.current_bb.label_list:
                self.bb_label_map[bb_label] = self.current_bb
        else:
            self.current_bb.label = label
            self.bb_label_map[label] = self.current_bb

        #if offset is None:
        #    offset = len(self.bundle_list)
        #self.label_map[label] = offset


class LiveRangeMap:
    """ Structure to store and manipulate register live ranges """
    def __init__(self, reg_class_list):
        self.liverange_map = dict((reg_class, collections.defaultdict(list)) for reg_class in reg_class_list)

    def __contains__(self, key):
        return key in self.liverange_map[key.reg_class]

    def __getitem__(self, key):
        return self.liverange_map[key.reg_class][key]

    def __setitem__(self, key, value):
        self.liverange_map[key.reg_class][key] = value

    def get_class_list(self):
        """ return the list of register classes """
        return list(self.liverange_map.keys())

    def get_class_map(self, reg_class):
        """ return the sub-dict of liveranges of registers of class @p reg_class """
        return self.liverange_map[reg_class]

    def get_all_registers(self):
        return sum([list(self.liverange_map[reg_class].keys()) for reg_class in self.liverange_map], [])

    def declare_pre_defined_reg(self, reg):
        """ declare a register which is alive before program starts """
        if not reg in self.liverange_map[reg.reg_class]:
            self.liverange_map[reg.reg_class][reg] = [LiveRange()]
        self.liverange_map[reg.reg_class][reg][-1].update_start(-1, DebugObject("before program starts"))
    def declare_post_used_reg(self, reg):
        if not reg in self.liverange_map[reg.reg_class]:
            self.liverange_map[reg.reg_class][reg] = [LiveRange()]
        self.liverange_map[reg.reg_class][reg][-1].update_stop(PostProgram(), DebugObject("after program ends"))

    def populate_pre_defined_list(self, program):
        for reg in program.pre_defined_list:
            self.declare_pre_defined_reg(reg)

    def populate_post_used_list(self, program):
        for reg in program.post_used_list:
            self.declare_post_used_reg(reg)

class VarUseDef:
    def __init__(self, loc, var, dbg_object=None):
        self.loc = loc
        self.var = var
        self.dbg_object = dbg_object

class VarDef(VarUseDef):
    """ Variable definition """
    pass
class VarUse(VarUseDef):
    """ Variable use """
    pass

class LiveRange:
    def __init__(self, start=None, stop=None, start_dbg_object=None, stop_dbg_object=None):
        self.start = start
        self.stop = stop
        self.start_dbg_object = start_dbg_object
        self.stop_dbg_object = stop_dbg_object

    def update_stop(self, new_stop, dbg_object=None):
        if self.stop is None or new_stop > self.stop:
            self.stop = new_stop
            self.stop_dbg_object = dbg_object
    def update_start(self, new_start, dbg_object=None):
        if self.start is None or new_start < self.start:
            self.start = new_start
            self.start_dbg_object = dbg_object

    def __repr__(self):
        return "[{}; {}]".format(self.start, self.stop)

    @property
    def is_valid(self):
        return not (self.start is None or self.stop is None)

    def intersect(self, liverange):
        """ Check intersection between @p self range and @p liverange """
        #if liverange_bound_compare_lt(self.stop, liverange.start) or liverange_bound_compare_gt(self.start, liverange.stop):
        assert not (self.stop is None or self.start is None)
        assert not (liverange.start is None or liverange.stop is None)
        if self.stop <= liverange.start or self.start >= liverange.stop:
            return False
        return True

    @staticmethod
    def intersect_list(lr_list0, lr_list1):
        """ test if any of the live range of list @p lr_list0
            intersects any of the live range of list @p lr_list1 """
        for liverange0 in lr_list0:
            for liverange1 in lr_list1:
                if liverange0.intersect(liverange1):
                    return True
        return False


def liverange_bound_compare_gt(lhs, rhs):
    if isinstance(lhs, PostProgram):
        # PostProgram > all
        return True
    elif isinstance(rhs, PostProgram):
        return False
    else:
        return lhs < rhs

def liverange_bound_compare_lt(lhs, rhs):
    return liverange_bound_compare_gt(rhs, lhs)

class PostProgram:
    """" After program ends timestamp """
    def __gt__(self, int_value):
        """ PostProgram is equals to +infty, so is always greater than any integer """
        assert isinstance(int_value, int)
        return True

    def __ge__(self, int_value):
        assert isinstance(int_value, int)
        return True

    def __lt__(self, int_value):
        """ PostProgram is equals to +infty, so is always greater than any integer """
        assert isinstance(int_value, int)
        return False

    def __le__(self, int_value):
        assert isinstance(int_value, int)
        return False

    def __repr__(self):
        return "PostProgram"

class RegisterAssignator:
    def __init__(self, arch):
        self.arch = arch

    def process_program(self, bundle_list):
        pass

    def generate_use_def_lists(self, program, verbose=False):
        """ List variable use and defs in program """
        use_list, def_list = {}, {}
        var_gens = collections.defaultdict(set)
        var_kills = collections.defaultdict(set)
        for bb in program.bb_list:
            # set of already defined variables
            already_def_set = set()
            for index, bundle in enumerate(bb.bundle_list):
                for regObj in bundle.use_list:
                    # discard non register element (e.g. ImmediateValue)
                    if not isinstance(regObj, Register): continue
                    # register alias disambiguation
                    reg = regObj.baseReg
                    if not reg in use_list: use_list[reg] = []
                    use_list[reg].append(VarUse((bb, index), reg, ))
                    if not reg in already_def_set:
                        # variable is used without being previously
                        # defined in the BB, it must be alive at BB entry
                        var_gens[bb].add(reg)

                for regObj in bundle.def_list:
                    # discard non register element (e.g. ImmediateValue)
                    if not isinstance(regObj, Register): continue
                    # register alias disambiguation
                    reg = regObj.baseReg
                    if not reg in def_list: def_list[reg] = []
                    var_def = VarDef((bb, index), reg)
                    def_list[reg].append(var_def)
                    var_kills[bb].add(reg)
                    already_def_set.add(reg)


        var_ins = collections.defaultdict(set)
        var_out = collections.defaultdict(set)

        if verbose:
            for reg in use_list:
                print("use_list {}: {}".format(reg, use_list[reg]))
            for reg in def_list:
                print("def_list {}: {}".format(reg, def_list[reg]))
            print("post_used_list: {}".format(program.post_used_list))
        # adding post used list into sink BB
        for reg in program.post_used_list:
            var_ins[program.sink_bb].add(reg)
            var_out[program.sink_bb].add(reg)

        # TODO(OPT): topological order for worklist (starting from sink)
        worklist = [bb for bb in program.sink_bb.preds] + [bb for bb in program.bb_list] + [program.source_bb]
        while worklist != []:
            bb = worklist.pop(0)
            if verbose: print("processing bb: {}, succs: {}".format(bb, bb.succs))
            if bb is program.sink_bb:
                # discard sink_bb which has no successor
                continue
            # out leaving variables is the union of leaving variable
            # at the entry of all successors
            var_out[bb] = set().union(*tuple(var_ins[succ] for succ in bb.succs))
            ins_bb = var_out[bb].difference(var_kills[bb]).union(var_gens[bb])
            if len(ins_bb.difference(var_ins[bb])) != 0:
                # var_ins[bb] is modified by current iteration
                for pred in bb.preds:
                    worklist.append(pred)
            var_ins[bb] = ins_bb
        if verbose:
            for bb in var_gens:
                print("var_gens for {}: ".format(bb, var_gens[bb]))
            for bb in var_ins:
                print("var_ins for {}: ".format(bb, var_ins[bb]))
            for bb in var_out:
                print("var_out for {}: ".format(bb, var_out[bb]))

        return var_ins, var_out


    def generate_liverange_map(self, program, liverange_map, var_ins, var_out):
        """ generate a dict key -> list of disjoint live-ranges
            mapping each variable to its liverange """
        # each range only covers a single BB
        # complete range is the accumulation of this sub-range segment
        for bb_index, bb in enumerate(program.bb_list):
            # initializing BB's LiveRange by iterating over var_ins
            for reg in var_ins[bb]:
                liverange_map[reg].append(LiveRange(start=(bb_index, -1)))
            # iterating over bundle in BB (in program order)
            for index, bundle in enumerate(bb.bundle_list):
                for insn in bundle.insn_list:
                    for regObj in insn.use_list:
                        if not isinstance(regObj, Register):
                            # discard non register element (e.g. ImmediateValue)
                            continue
                        # alias disambiguation
                        reg = regObj.baseReg
                        if not reg in liverange_map:
                            liverange_map[reg] = [LiveRange()]
                        # we update the last inserted LiveRange object in reg's list
                        liverange_map[reg][-1].update_stop((bb_index, index), dbg_object=insn.dbg_object)
                    for regObj in insn.def_list:
                        # alias disambiguation
                        reg = regObj.baseReg
                        if not reg in liverange_map:
                            liverange_map[reg] = []
                        if not(len(liverange_map[reg]) and liverange_map[reg][-1].start == (bb_index, index)): 
                            # only register a liverange once per index value
                            liverange_map[reg].append(LiveRange(start=(bb_index, index), start_dbg_object=insn.dbg_object))
            # closing BB's LiveRange by iterating over var_out
            final_bb_index = len(bb.bundle_list)
            for reg in var_out[bb]:
                if not reg in liverange_map:
                    print("reg must be alive at end of BB {} and is not !".format(bb_index))
                    raise Exception()
                elif liverange_map[reg][-1].start[0] != bb_index:
                    print("latest liverange for reg {}, {} does not match expected BB's index{}, {}".format(reg, liverange_map[reg][-1], bb_index, liverange_map[reg][-1].start[0]))
                    raise Exception()
                liverange_map[reg][-1].update_stop((bb_index, final_bb_index))
        return liverange_map

    def check_liverange_map(self, liverange_map):
        error_count = 0
        for reg in liverange_map.get_all_registers():
            for liverange in liverange_map[reg]:
                if liverange.start == None and liverange.stop != None:
                    print("value {} is used @ {} without being defined!".format(reg, liverange.stop_dbg_object))
                    error_count += 1
                if liverange.stop == None and liverange.start != None:
                    print("value {} is defined @ {} without being used!".format(reg, liverange.start_dbg_object))
                    error_count += 1
        return error_count == 0

    def create_conflict_map(self, liverange_map):
        """ Build the graph of liverange intersection from the
            liverange_map """
        conflict_map = {}
        for reg_class in liverange_map.get_class_list():
            sub_liverange_map = liverange_map.get_class_map(reg_class)
            conflict_map[reg_class] = {}
            # check if any liverange is still undefined
            for reg in sub_liverange_map:
                for liverange in sub_liverange_map[reg]:
                    if liverange.start is None or liverange.stop is None:
                        print("sub liverange for reg {} contains undefined bound(s) ({})".format(reg, sub_liverange_map[reg]))
                        raise Exception()

            # building actual conflict map
            for reg in sub_liverange_map:
                conflict_map[reg_class][reg] = set()
                for reg2 in sub_liverange_map:
                    if reg2 != reg and LiveRange.intersect_list(sub_liverange_map[reg], sub_liverange_map[reg2]):
                        conflict_map[reg_class][reg].add(reg2)
        return conflict_map

    def create_color_map(self, conflict_map, verbose=False):
        max_color_num = 0
        max_degree = 0
        max_degree_node = None

        general_color_map = {}

        # start by pre-assigning colors to corresponding physical registers
        for reg_class in conflict_map:
            graph = conflict_map[reg_class]
            color_map = {}
            general_color_map[reg_class] = color_map
            for reg in graph:
                if isinstance(reg, PhysicalRegister):
                    color_map[reg] = reg.index

            while len(color_map) != len(graph):
                # looking for node with max degree
                max_reg = max([node for node in graph if not node in color_map], key=(lambda reg: len(list(node for node in graph[reg] if not node in color_map))))

                def allocate_reg_list(reg_list, graph, color_map):
                    """ Allocate each register in reg_list assuming dependencies
                        are stored in graph and color_map indicates previously performed
                        allocation """
                    if len(reg_list) == 0:
                        # empty list returns empty allocation (valid)
                        return {}
                    else:
                        # select head of list as current register for allocation
                        head_reg = reg_list[0]
                        remaining_reg_list = reg_list[1:]
                        unavailable_color_set = set([color_map[neighbour] for neighbour in graph[head_reg] if neighbour in color_map])

                        valid_color_set = [color for color in range(self.arch.reg_pool[reg_class].description.num_phys_reg) if head_reg.constraint(color)]
                        if not len(valid_color_set):
                            # no color available in valid set
                            return None
                        available_color_set = set(valid_color_set).difference(set(unavailable_color_set))

                        if not len(available_color_set):
                            # no color available in available color set
                            return None

                        # enforcing link constraints
                        linked_map = head_reg.get_linked_map()
                        for linked_reg in linked_map:
                            if not linked_reg in color_map:
                                # discard linked registers which have not been allocated yet
                                continue
                            else:
                                available_color_set.intersection_update(set(linked_map[linked_reg](color_map)))
                        for possible_color in available_color_set:
                            # FIXME: bad performance: copying full local dict each time
                            local_color_map = {head_reg: possible_color}
                            local_color_map.update(color_map)
                            sub_allocation = allocate_reg_list(remaining_reg_list, graph, local_color_map)
                            if sub_allocation != None:
                                # valid sub allocation
                                sub_allocation.update({head_reg: possible_color})
                                # return first valid sub-alloc
                                return sub_allocation

                        return None
                # FIXME/TODO: build full set of linked registers (recursively)

                # if selected register is linked, we must allocated all the
                # register at once to ensure link constraints are met
                linked_allocation = allocate_reg_list([max_reg] + list(max_reg.get_linked_map().keys()), graph, color_map)
                if linked_allocation is None:
                    print("no feasible allocation for {} and linked map {}".format(max_reg, max_reg.get_linked_map()))
                    raise Exception()

                num_reg_in_class = self.arch.get_max_register_index_by_class(reg_class)
                for linked_reg in linked_allocation:
                    linked_color =  linked_allocation[linked_reg]
                    color_map[linked_reg] = linked_color
                    # check on colour bound
                    if linked_color >= num_reg_in_class:
                        print("Error while assigning register of class {}, requesting index {}, only {} register(s) available".format(reg_class.name, linked_color, num_reg_in_class)) 
                        raise Exception()

                    if verbose: print("register {} of class {} has been assigned color {}".format(linked_reg, reg_class.name, linked_color))

        return general_color_map

    def check_color_map(self, conflict_graph, color_map):
        for reg in conflict_graph:
            reg_color = color_map[reg]
            for neighbour in conflict_graph[reg]:
                if reg_color == color_map[neighbour]:
                    print("color conflict for {}({}) vs {}({})".format(reg, reg_color, neighbour, color_map[neighbour]))
                    return False
        return True
