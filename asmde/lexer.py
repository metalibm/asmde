# -*- coding: utf-8 -*-

import re

class Lexem:
    PATTERN = "[\w\d]+"

    def __init__(self, value):
        self.value = value

    @classmethod
    def match(lexem_class, s):
        return re.match(lexem_class.PATTERN, s)

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self.value)

class Separator(Lexem):
    pass

class RegisterLexem(Lexem):
    PATTERN = "\$([ar][0-9]+){1,4}"

    def __repr__(self):
        return "RegisterLexem({})".format(self.value)

class ImmediateLexem(Lexem):
    PATTERN = "([+-]|)[0-9]+"

class OperatorLexem(Lexem):
    PATTERN = "[()\[\]\.]"

class LabelEndLexem(Lexem):
    PATTERN = ":"

class BundleSeparatorLexem(Lexem):
    PATTERN = ";;"


class MacroLexem(Lexem):
    PATTERN = "\/\/#"

class CommentHeadLexem(Lexem):
    PATTERN = "\/\/(?!#)"

# extended regular expression for seperator, including
# separators that will be included as valid lexems
SEP_PATTERN = "([ \t,=\[\]\.])+"

# DUMMY SEPARATOR (to be discarded during lexing)
DUMMY_SEP_PATTERN = "[ \t,=]+"

def generate_line_lexems(s):
    """ generate the list of lexems found in line @p s """
    lexem_list = []
    for sub_word in re.split(SEP_PATTERN, s):
        lexem_match = None
        for lexem_class in [CommentHeadLexem, LabelEndLexem, MacroLexem, ImmediateLexem, RegisterLexem, OperatorLexem, BundleSeparatorLexem, Lexem]:
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
                    lexem_list = lexem_list + generate_line_lexems(remainder)
                break

    return lexem_list

