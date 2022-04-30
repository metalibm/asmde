# -*- coding: utf-8 -*-

import re

class ParentLexem:
    def __init__(self, value):
        self.value = value

    @classmethod
    def match(lexem_class, s):
        return re.match(lexem_class.PATTERN, s)

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self.value)

class Lexem(ParentLexem):
    PATTERN = "[\w\d_]+"


class Separator(ParentLexem):
    pass

class RegisterLexem(ParentLexem):
    PATTERN = "\$([ar][0-9]+){1,4}"

    def __repr__(self):
        return "RegisterLexem({})".format(self.value)

class SpecialRegisterLexem(ParentLexem):
    PATTERN = "\$([\w\d]+)"

    def __repr__(self):
        return "SpecialRegisterLexem({})".format(self.value)

class ImmediateLexem(ParentLexem):
    PATTERN = "([+-]|)[0-9]+"

class HexImmediateLexem(ParentLexem):
    PATTERN = "(\(|)([+-]|)0x[0-9a-fA-F_]+(\)|)"

class OperatorLexem(ParentLexem):
    PATTERN = "[()\[\]\.<>]"

class LabelEndLexem(ParentLexem):
    PATTERN = ":"

class BundleSeparatorLexem(ParentLexem):
    PATTERN = ";;"

class FunctionStartLexem(ParentLexem):
    PATTERN = "{{{"
class FunctionEndLexem(ParentLexem):
    PATTERN = "}}}"

class MacroLexem(ParentLexem):
    PATTERN = "\/\/#"

class CommentHeadLexem(ParentLexem):
    PATTERN = "\/\/(?!#)"

class TraceCommentHeadLexem(ParentLexem):
    PATTERN = "#"

class ObjdumpMacro(ParentLexem):
    PATTERN = "([\.]{3}|\*\*\*)"

class ObjdumpLabel(ParentLexem):
    PATTERN = "<[\w\d._+-]+>"

class DiscardedSymbol(ParentLexem):
    PATTERN = "[,]"

class UnmatchedLexem(ParentLexem):
    """ class for unmatched lexem """
    pass

class SymbolLexem(ParentLexem):
    PATTERN = "%(hi|lo)\([.\w\d]+\)"


# extended regular expression for seperator, including
# separators that will be included as valid lexems
SEP_PATTERN = "([ \t,=\?])+"

# DUMMY SEPARATOR (to be discarded during lexing)
DUMMY_SEP_PATTERN = "[ \t,=]+"

def generate_line_lexems(s, verbose=False):
    """ generate the list of lexems found in line @p s """
    lexem_list = []
    for sub_word in re.split(SEP_PATTERN, s):
        if sub_word in ['', ' ', '\t']: continue
        lexem_match = None
        for lexem_class in [ObjdumpMacro, ObjdumpLabel, FunctionStartLexem, FunctionEndLexem,
                            CommentHeadLexem, TraceCommentHeadLexem, LabelEndLexem, MacroLexem,
                            HexImmediateLexem, ImmediateLexem, RegisterLexem, OperatorLexem,
                            BundleSeparatorLexem, Lexem, SpecialRegisterLexem, SymbolLexem]:
            lexem_match = lexem_class.match(sub_word)
            if lexem_match is None:
                continue
            else:
                lexem_match_string = lexem_match.group(0)
                if not re.match(DUMMY_SEP_PATTERN, lexem_match_string) and lexem_match_string != "":
                    # only add lexem if it is a valid string (not empty nor a dont care seperator)
                    lexem_list.append(lexem_class(lexem_match_string))
                remainder = sub_word[lexem_match.end(0):]
                if remainder != "":
                    lexem_list = lexem_list + generate_line_lexems(remainder, verbose=verbose)
                break
        if lexem_match is None:
            if DiscardedSymbol.match(sub_word):
                # discard
                if verbose:
                    print("discarding '{}' ".format(sub_word))
                pass
            else:
                lexem_list.append(UnmatchedLexem(sub_word))
                if verbose:
                    print("could not match lexically '{}' ".format(sub_word))

    return lexem_list

