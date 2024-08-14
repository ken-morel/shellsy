"""
Shellsy: An extensible shell program designed for ease of use and flexibility.

This module serves as the entry point for the Shellsy application, allowing
users
to define commands and interact with the shell environment.

Copyright (C) 2024  Ken Morel

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import re
import keyword
from pygments import unistring as uni
from pygments.lexer import (
    RegexLexer,
    # do_insertions,
    include,
    default,
    this,
    using,
    words,
    # line_re,
    bygroups,
    combined,
)
from pygments.token import (
    Punctuation,
    Whitespace,
    Text,
    Comment,
    Operator,
    Keyword,
    Name,
    String,
    Number,
    Generic,
    Error,
    Literal,
    # Other,
)


class ShellsyLexer(RegexLexer):
    def innerstring_rules(ttype):
        return [
            # the old style '%s' % (...) string formatting (still valid in Py3)
            (
                r"%(\(\w+\))?[-#0 +]*([0-9]+|[*])?(\.([0-9]+|[*]))?"
                "[hlL]?[E-GXc-giorsaux%]",
                String.Interpol,
            ),
            # the new style '{}'.format(...) string formatting
            (
                r"\{"
                r"((\w+)((\.\w+)|(\[[^\]]+\]))*)?"  # field name
                r"(\![sra])?"  # conversion
                r"(\:(.?[<>=\^])?[-+ ]?#?0?(\d+)?,?(\.\d+)?[E-GXb-gnosx%]?)?"
                r"\}",
                String.Interpol,
            ),
            # backslashes, quotes and formatting signs must be parsed one at
            # a time
            (r'[^\\\'"%{\n]+', ttype),
            (r'[\'"\\]', ttype),
            # unhandled string formatting sign
            (r"%|(\{{1,2})", ttype),
            # newlines are an error (use "nl" state)
        ]

    def fstring_rules(ttype):
        return [
            # Assuming that a '}' is the closing brace after format specifier.
            # Sadly, this means that we won't detect syntax error. But it's
            # more important to parse correct syntax correctly, than to
            # highlight invalid syntax.
            (r"\}", String.Interpol),
            (r"\{", String.Interpol, "py-expr-inside-fstring"),
            # backslashes, quotes and formatting signs must be parsed one at
            # a time
            (r'[^\\\'"{}\n]+', ttype),
            (r'[\'"\\]', ttype),
            # newlines are an error (use "nl" state)
        ]

    aliases = [""]
    filenames = ["*.shellsy"]
    mimetypes = ["text/x-shellsy"]
    url = "https://github.com/ken-morel/shellsy"
    version_added = "1.0.0"
    flags = re.DOTALL | re.IGNORECASE | re.MULTILINE
    operators = []
    verbs = [""]
    aliases_ = []
    uni_name = f"[{uni.xid_start}][{uni.xid_continue}]*"
    commenthelp = ["help"]
    tokens = {
        "root": [
            (r"!", Punctuation, "bash"),
            (r"#.+", Comment.Single),
            include("shellsy-statement"),
        ],
        "single-string": [
            include("string-escapes"),
            ("'", Punctuation, "#pop"),
            (r".", String.Single),
        ],
        "double-string": [
            include("string-escapes"),
            (r'"', Punctuation, "#pop"),
            (r".", String.Double),
        ],
        "string-escapes": [
            (
                r"\\(N\{.*?\}|u[a-fA-F0-9]{4}|U[a-fA-F0-9]{8})",
                String.Escape,
            ),
            (
                r'\\([\\abfnrtv"\']|\n|x[a-fA-F0-9]{2}|[0-7]{1,3})',
                String.Escape,
            ),
        ],
        "pathcontent": [
            (r"\w\:", Name.Namespace),
            (
                r"(%)([\w_]+)(%)",
                bygroups(Punctuation, Name.Constant, Punctuation),
            ),
            (
                r"(\$)([\w_]+)",
                bygroups(Punctuation, Name.Constant),
            ),
            (r"(?:/|\\)(?=\w|\d|_|\-)", Operator),
            (r"[\w\d_\-\s]+", Generic),
            (r"\.[\w_\-]+(?=/)", Name.Namespace),
            (r"/(?=\s|\b|$)", Punctuation, "#pop"),
        ],
        "commandblock": [
            (r"\}", Punctuation, "#pop"),
            (r";", Punctuation),
            include("shellsy-statement"),
        ],
        "bash": [
            include("bash-basic"),
            (r"`", String.Backtick, "bash-backticks"),
            include("bash-data"),
            include("bash-interp"),
        ],
        "bash-interp": [
            (r"\$\(\(", Keyword, "bash-math"),
            (r"\$\(", Keyword, "bash-paren"),
            (r"\$\{#?", String.Interpol, "bash-curly"),
            (r"\$[a-zA-Z_]\w*", Name.Variable),  # user variable
            (r"\$(?:\d+|[#$?!_*@-])", Name.Variable),  # builtin
            (r"\$", Text),
        ],
        "bash-basic": [
            (
                r"\b(if|fi|else|while|in|do|done|for|then|return|function|case|"
                r"select|break|continue|until|esac|elif)(\s*)\b",
                bygroups(Keyword, Whitespace),
            ),
            (
                r"\b(alias|bg|bind|builtin|caller|cd|command|compgen|"
                r"complete|declare|dirs|disown|echo|enable|eval|exec|exit|"
                r"export|false|fc|fg|getopts|hash|help|history|jobs|kill|let|"
                r"local|logout|popd|printf|pushd|pwd|read|readonly|set|shift|"
                r"shopt|source|suspend|test|time|times|trap|true|type|typeset|"
                r"ulimit|umask|unalias|unset|wait)(?=[\s)`])",
                Name.Builtin,
            ),
            (r"\A#!.+\n", Comment.Hashbang),
            (r"#.*\n", Comment.Single),
            (r"\\[\w\W]", String.Escape),
            (
                r"(\b\w+)(\s*)(\+?=)",
                bygroups(Name.Variable, Whitespace, Operator),
            ),
            (r"[\[\]{}()=]", Operator),
            (r"<<<", Operator),  # here-string
            (r"<<-?\s*(\'?)\\?(\w+)[\w\W]+?\2", String),
            (r"&&|\|\|", Operator),
        ],
        "bash-data": [
            (r'(?s)\$?"(\\.|[^"\\$])*"', String.Double),
            (r'"', String.Double, "bash-string"),
            (r"(?s)\$'(\\\\|\\[0-7]+|\\.|[^'\\])*'", String.Single),
            (r"(?s)'.*?'", String.Single),
            (r";", Punctuation),
            (r"&", Punctuation),
            (r"\|", Punctuation),
            (r"\s+", Whitespace),
            (r"\d+\b", Number),
            (r'[^=\s\[\]{}()$"\'`\\<&|;]+', Text),
            (r"<", Text),
        ],
        "bash-string": [
            (r'"', String.Double, "#pop"),
            (r'(?s)(\\\\|\\[0-7]+|\\.|[^"\\$])+', String.Double),
            include("bash-interp"),
        ],
        "bash-curly": [
            (r"\}", String.Interpol, "#pop"),
            (r":-", Keyword),
            (r"\w+", Name.Variable),
            (r'[^}:"\'`$\\]+', Punctuation),
            (r":", Punctuation),
            include("bash"),
        ],
        "bash-paren": [
            (r"\)", Keyword, "#pop"),
            include("bash"),
        ],
        "bash-math": [
            (r"\)\)", Keyword, "#pop"),
            (r"\*\*|\|\||<<|>>|[-+*/%^|&<>]", Operator),
            (r"\d+#[\da-zA-Z]+", Number),
            (r"\d+#(?! )", Number),
            (r"0[xX][\da-fA-F]+", Number),
            (r"\d+", Number),
            (r"[a-zA-Z_]\w*", Name.Variable),  # user variable
            include("bash"),
        ],
        "bash-backticks": [
            (r"`", String.Backtick, "#pop"),
            include("bash"),
        ],
        "python-expression": [
            # (r'[^\(]+', Punctuation),
            (r"\)\)?", Punctuation, "#pop"),  # End of inline Python
            include("py-root"),
        ],
        "py-root": [
            (r"\n", Whitespace),
            (
                r'^(\s*)([rRuUbB]{,2})("""(?:.|\n)*?""")',
                bygroups(Whitespace, String.Affix, String.Doc),
            ),
            (
                r"^(\s*)([rRuUbB]{,2})('''(?:.|\n)*?''')",
                bygroups(Whitespace, String.Affix, String.Doc),
            ),
            (r"\A#!.+$", Comment.Hashbang),
            (r"#.*$", Comment.Single),
            (r"\\\n", Text),
            (r"\\", Text),
            include("py-keywords"),
            include("py-soft-keywords"),
            include("py-expr"),
        ],
        "py-expr": [
            # raw f-strings
            (
                '(?i)(rf|fr)(""")',
                bygroups(String.Affix, String.Double),
                combined("py-rfstringescape", "py-tdqf"),
            ),
            (
                "(?i)(rf|fr)(''')",
                bygroups(String.Affix, String.Single),
                combined("py-rfstringescape", "py-tsqf"),
            ),
            (
                '(?i)(rf|fr)(")',
                bygroups(String.Affix, String.Double),
                combined("py-rfstringescape", "py-dqf"),
            ),
            (
                "(?i)(rf|fr)(')",
                bygroups(String.Affix, String.Single),
                combined("py-rfstringescape", "py-sqf"),
            ),
            # non-raw f-strings
            (
                '([fF])(""")',
                bygroups(String.Affix, String.Double),
                combined("py-fstringescape", "py-tdqf"),
            ),
            (
                "([fF])(''')",
                bygroups(String.Affix, String.Single),
                combined("py-fstringescape", "py-tsqf"),
            ),
            (
                '([fF])(")',
                bygroups(String.Affix, String.Double),
                combined("py-fstringescape", "py-dqf"),
            ),
            (
                "([fF])(')",
                bygroups(String.Affix, String.Single),
                combined("py-fstringescape", "py-sqf"),
            ),
            # raw bytes and strings
            (
                '(?i)(rb|br|r)(""")',
                bygroups(String.Affix, String.Double),
                "py-tdqs",
            ),
            (
                "(?i)(rb|br|r)(''')",
                bygroups(String.Affix, String.Single),
                "py-tsqs",
            ),
            (
                '(?i)(rb|br|r)(")',
                bygroups(String.Affix, String.Double),
                "py-dqs",
            ),
            (
                "(?i)(rb|br|r)(')",
                bygroups(String.Affix, String.Single),
                "py-sqs",
            ),
            # non-raw strings
            (
                '([uU]?)(""")',
                bygroups(String.Affix, String.Double),
                combined("py-stringescape", "py-tdqs"),
            ),
            (
                "([uU]?)(''')",
                bygroups(String.Affix, String.Single),
                combined("py-stringescape", "py-tsqs"),
            ),
            (
                '([uU]?)(")',
                bygroups(String.Affix, String.Double),
                combined("py-stringescape", "py-dqs"),
            ),
            (
                "([uU]?)(')",
                bygroups(String.Affix, String.Single),
                combined("py-stringescape", "py-sqs"),
            ),
            # non-raw bytes
            (
                '([bB])(""")',
                bygroups(String.Affix, String.Double),
                combined("py-bytesescape", "py-tdqs"),
            ),
            (
                "([bB])(''')",
                bygroups(String.Affix, String.Single),
                combined("py-bytesescape", "py-tsqs"),
            ),
            (
                '([bB])(")',
                bygroups(String.Affix, String.Double),
                combined("py-bytesescape", "py-dqs"),
            ),
            (
                "([bB])(')",
                bygroups(String.Affix, String.Single),
                combined("py-bytesescape", "py-sqs"),
            ),
            (r"[^\S\n]+", Text),
            include("py-numbers"),
            (r"!=|==|<<|>>|:=|[-~+/*%=<>&^|.]", Operator),
            (r"[]{}:(),;[]", Punctuation),
            (r"(in|is|and|or|not)\b", Operator.Word),
            include("py-expr-keywords"),
            include("py-builtins"),
            include("py-magicfuncs"),
            include("py-magicvars"),
            include("py-name"),
        ],
        "py-expr-inside-fstring": [
            (r"[{([]", Punctuation, "py-expr-inside-fstring-inner"),
            # without format specifier
            (
                r"(=\s*)?"  # debug (https://bugs.python.org/issue36817)
                r"(\![sraf])?"  # conversion
                r"\}",
                String.Interpol,
                "#pop",
            ),
            # with format specifier
            # we'll catch the remaining '}' in the outer scope
            (
                r"(=\s*)?"  # debug (https://bugs.python.org/issue36817)
                r"(\![sraf])?"  # conversion
                r":",
                String.Interpol,
                "#pop",
            ),
            (r"\s+", Whitespace),  # allow new lines
            include("py-expr"),
        ],
        "py-expr-inside-fstring-inner": [
            (r"[{([]", Punctuation, "py-expr-inside-fstring-inner"),
            (r"[])}]", Punctuation, "#pop"),
            (r"\s+", Whitespace),  # allow new lines
            include("py-expr"),
        ],
        "py-expr-keywords": [
            # Based on https://docs.python.org/3/reference/expressions.html
            (
                words(
                    (
                        "async for",
                        "await",
                        "else",
                        "for",
                        "if",
                        "lambda",
                        "yield",
                        "yield from",
                    ),
                    suffix=r"\b",
                ),
                Keyword,
            ),
            (
                words(("True", "False", "None", "Nil"), suffix=r"\b"),
                Keyword.Constant,
            ),
        ],
        "py-keywords": [
            (
                words(
                    (
                        "await",
                        "del",
                        "else",
                        "for",
                        "if",
                        "lambda",
                        "raise",
                        "return",
                        "as",
                    ),
                    suffix=r"\b",
                ),
                Keyword,
            ),
            (
                words(("True", "False", "None"), suffix=r"\b"),
                Keyword.Constant,
            ),
        ],
        "py-soft-keywords": [
            # `match`, `case` and `_` soft keywords
            (
                r"(^[ \t]*)"  # at beginning of line + possible indentation
                r"(match|case)\b"  # a possible keyword
                r"(?![ \t]*(?:"  # not followed by...
                r"[:,;=^&|@~)\]}]|(?:"  # characters and keywords
                + r"|".join(k for k in keyword.kwlist if k[0].islower())
                + r")\b))",
                bygroups(Text, Keyword),
                "py-soft-keywords-inner",
            ),
        ],
        "py-soft-keywords-inner": [
            # optional `_` keyword
            (
                r"(\s+)([^\n_]*)(_\b)",
                bygroups(Whitespace, using(this), Keyword),
            ),
            default("#pop"),
        ],
        "py-builtins": [
            (
                words(
                    (
                        "__import__",
                        "abs",
                        "aiter",
                        "all",
                        "any",
                        "bin",
                        "bool",
                        "bytearray",
                        "breakpoint",
                        "bytes",
                        "callable",
                        "chr",
                        "classmethod",
                        "compile",
                        "complex",
                        "delattr",
                        "dict",
                        "dir",
                        "divmod",
                        "enumerate",
                        "eval",
                        "filter",
                        "float",
                        "format",
                        "frozenset",
                        "getattr",
                        "globals",
                        "hasattr",
                        "hash",
                        "hex",
                        "id",
                        "input",
                        "int",
                        "isinstance",
                        "issubclass",
                        "iter",
                        "len",
                        "list",
                        "locals",
                        "map",
                        "max",
                        "memoryview",
                        "min",
                        "next",
                        "object",
                        "oct",
                        "open",
                        "ord",
                        "pow",
                        "print",
                        "property",
                        "range",
                        "repr",
                        "reversed",
                        "round",
                        "set",
                        "setattr",
                        "slice",
                        "sorted",
                        "staticmethod",
                        "str",
                        "sum",
                        "super",
                        "tuple",
                        "type",
                        "vars",
                        "zip",
                        "shell",
                    ),
                    prefix=r"(?<!\.)",
                    suffix=r"\b",
                ),
                Name.Builtin,
            ),
            (
                r"(?<!\.)(Ellipsis|NotImplemented|cls)\b",
                Name.Builtin.Pseudo,
            ),
            (
                words(
                    (
                        "ArithmeticError",
                        "AssertionError",
                        "AttributeError",
                        "BaseException",
                        "BufferError",
                        "BytesWarning",
                        "DeprecationWarning",
                        "EOFError",
                        "EnvironmentError",
                        "Exception",
                        "FloatingPointError",
                        "FutureWarning",
                        "GeneratorExit",
                        "IOError",
                        "ImportError",
                        "ImportWarning",
                        "IndentationError",
                        "IndexError",
                        "KeyError",
                        "KeyboardInterrupt",
                        "LookupError",
                        "MemoryError",
                        "NameError",
                        "NotImplementedError",
                        "OSError",
                        "OverflowError",
                        "PendingDeprecationWarning",
                        "ReferenceError",
                        "ResourceWarning",
                        "RuntimeError",
                        "RuntimeWarning",
                        "StopIteration",
                        "SyntaxError",
                        "SyntaxWarning",
                        "SystemError",
                        "SystemExit",
                        "TabError",
                        "TypeError",
                        "UnboundLocalError",
                        "UnicodeDecodeError",
                        "UnicodeEncodeError",
                        "UnicodeError",
                        "UnicodeTranslateError",
                        "UnicodeWarning",
                        "UserWarning",
                        "ValueError",
                        "VMSError",
                        "Warning",
                        "WindowsError",
                        "ZeroDivisionError",
                        # new builtin exceptions from PEP 3151
                        "BlockingIOError",
                        "ChildProcessError",
                        "ConnectionError",
                        "BrokenPipeError",
                        "ConnectionAbortedError",
                        "ConnectionRefusedError",
                        "ConnectionResetError",
                        "FileExistsError",
                        "FileNotFoundError",
                        "InterruptedError",
                        "IsADirectoryError",
                        "NotADirectoryError",
                        "PermissionError",
                        "ProcessLookupError",
                        "TimeoutError",
                        # others new in Python 3
                        "StopAsyncIteration",
                        "ModuleNotFoundError",
                        "RecursionError",
                        "EncodingWarning",
                        "ShellsyNtaxError",
                    ),
                    prefix=r"(?<!\.)",
                    suffix=r"\b",
                ),
                Name.Exception,
            ),
        ],
        "py-magicfuncs": [
            (
                words(
                    (
                        "__abs__",
                        "__add__",
                        "__aenter__",
                        "__aexit__",
                        "__aiter__",
                        "__and__",
                        "__anext__",
                        "__await__",
                        "__bool__",
                        "__bytes__",
                        "__call__",
                        "__complex__",
                        "__contains__",
                        "__del__",
                        "__delattr__",
                        "__delete__",
                        "__delitem__",
                        "__dir__",
                        "__divmod__",
                        "__enter__",
                        "__eq__",
                        "__exit__",
                        "__float__",
                        "__floordiv__",
                        "__format__",
                        "__ge__",
                        "__get__",
                        "__getattr__",
                        "__getattribute__",
                        "__getitem__",
                        "__gt__",
                        "__hash__",
                        "__iadd__",
                        "__iand__",
                        "__ifloordiv__",
                        "__ilshift__",
                        "__imatmul__",
                        "__imod__",
                        "__imul__",
                        "__index__",
                        "__init__",
                        "__instancecheck__",
                        "__int__",
                        "__invert__",
                        "__ior__",
                        "__ipow__",
                        "__irshift__",
                        "__isub__",
                        "__iter__",
                        "__itruediv__",
                        "__ixor__",
                        "__le__",
                        "__len__",
                        "__length_hint__",
                        "__lshift__",
                        "__lt__",
                        "__matmul__",
                        "__missing__",
                        "__mod__",
                        "__mul__",
                        "__ne__",
                        "__neg__",
                        "__new__",
                        "__next__",
                        "__or__",
                        "__pos__",
                        "__pow__",
                        "__prepare__",
                        "__radd__",
                        "__rand__",
                        "__rdivmod__",
                        "__repr__",
                        "__reversed__",
                        "__rfloordiv__",
                        "__rlshift__",
                        "__rmatmul__",
                        "__rmod__",
                        "__rmul__",
                        "__ror__",
                        "__round__",
                        "__rpow__",
                        "__rrshift__",
                        "__rshift__",
                        "__rsub__",
                        "__rtruediv__",
                        "__rxor__",
                        "__set__",
                        "__setattr__",
                        "__setitem__",
                        "__str__",
                        "__sub__",
                        "__subclasscheck__",
                        "__truediv__",
                        "__xor__",
                    ),
                    suffix=r"\b",
                ),
                Name.Function.Magic,
            ),
        ],
        "py-magicvars": [
            (
                words(
                    (
                        "__annotations__",
                        "__bases__",
                        "__class__",
                        "__closure__",
                        "__code__",
                        "__defaults__",
                        "__dict__",
                        "__doc__",
                        "__file__",
                        "__func__",
                        "__globals__",
                        "__kwdefaults__",
                        "__module__",
                        "__mro__",
                        "__name__",
                        "__objclass__",
                        "__qualname__",
                        "__self__",
                        "__slots__",
                        "__weakref__",
                    ),
                    suffix=r"\b",
                ),
                Name.Variable.Magic,
            ),
        ],
        "py-numbers": [
            (
                (r"(\d(?:_?\d)*\.(?:\d(?:_?\d)*)?|" r"(?:\d(?:_?\d)*)?\.\d(?:_?\d)*)"),
                # r"([eE][+-]?\d(?:_?\d)*)?",),
                Number.Float,
            ),
            (r"\d(?:_?\d)*[eE][+-]?\d(?:_?\d)*j?", Number.Float),
            (r"0[oO](?:_?[0-7])+", Number.Oct),
            (r"0[bB](?:_?[01])+", Number.Bin),
            (r"0[xX](?:_?[a-fA-F0-9])+", Number.Hex),
            (r"\d(?:_?\d)*", Number.Integer),
        ],
        "py-name": [
            (r"@" + uni_name, Name.Decorator),
            (r"@", Operator),  # new matrix multiplication operator
            (uni_name, Name),
        ],
        "py-funcname": [
            include("py-magicfuncs"),
            (uni_name, Name.Function, "#pop"),
            default("#pop"),
        ],
        "py-classname": [
            (uni_name, Name.Class, "#pop"),
        ],
        "py-fromimport": [
            (
                r"(\s+)(import)\b",
                bygroups(Text, Keyword.Namespace),
                "#pop",
            ),
            (r"\.", Name.Namespace),
            # if None occurs here, it's "raise x from None", since None can
            # never be a module name
            (r"None\b", Keyword.Constant, "#pop"),
            (uni_name, Name.Namespace),
            default("#pop"),
        ],
        "py-rfstringescape": [
            (r"\{\{", String.Escape),
            (r"\}\}", String.Escape),
        ],
        "py-fstringescape": [
            include("py-rfstringescape"),
            include("py-stringescape"),
        ],
        "py-bytesescape": [
            (
                r'\\([\\abfnrtv"\']|\n|x[a-fA-F0-9]{2}|[0-7]{1,3})',
                String.Escape,
            )
        ],
        "py-stringescape": [
            (
                r"\\(N\{.*?\}|u[a-fA-F0-9]{4}|U[a-fA-F0-9]{8})",
                String.Escape,
            ),
            include("py-bytesescape"),
        ],
        "py-fstrings-single": fstring_rules(String.Single),
        "py-fstrings-double": fstring_rules(String.Double),
        "py-strings-single": innerstring_rules(String.Single),
        "py-strings-double": innerstring_rules(String.Double),
        "py-dqf": [
            (r'"', String.Double, "#pop"),
            (
                r'\\\\|\\"|\\\n',
                String.Escape,
            ),  # included here for raw strings
            include("py-fstrings-double"),
        ],
        "py-sqf": [
            (r"'", String.Single, "#pop"),
            (
                r"\\\\|\\'|\\\n",
                String.Escape,
            ),  # included here for raw strings
            include("py-fstrings-single"),
        ],
        "py-dqs": [
            (r'"', String.Double, "#pop"),
            (
                r'\\\\|\\"|\\\n',
                String.Escape,
            ),  # included here for raw strings
            include("py-strings-double"),
        ],
        "py-sqs": [
            (r"'", String.Single, "#pop"),
            (
                r"\\\\|\\'|\\\n",
                String.Escape,
            ),  # included here for raw strings
            include("py-strings-single"),
        ],
        "py-tdqf": [
            (r'"""', String.Double, "#pop"),
            include("py-fstrings-double"),
            (r"\n", String.Double),
        ],
        "py-tsqf": [
            (r"'''", String.Single, "#pop"),
            include("py-fstrings-single"),
            (r"\n", String.Single),
        ],
        "py-tdqs": [
            (r'"""', String.Double, "#pop"),
            include("py-strings-double"),
            (r"\n", String.Double),
        ],
        "py-tsqs": [
            (r"'''", String.Single, "#pop"),
            include("py-strings-single"),
            (r"\n", String.Single),
        ],
        "shellsy-arguments": [
            (r"\{", Punctuation, "commandblock"),
            (r"(True|False|Nil|None)", Keyword),
            (
                r"(\()(\w+)#(.*)(\))",
                bygroups(Punctuation, Keyword, String.Single, Punctuation),
            ),
            (
                r"\(\(?",
                Punctuation,
                "python-expression",
            ),
            (
                r"(\[)(-)(\])",
                bygroups(Punctuation, Keyword, Punctuation),
            ),
            (
                r"\[",
                Punctuation,
                "shellsy-array",
            ),
            (
                r"(?<!^)(\$)([\w_]+)",
                bygroups(Punctuation, Name.Variable),
            ),
            # Double quoted strings (e.g., "arg1 string")
            (
                r"(')([^']*)(')",
                bygroups(Punctuation, String.Single, Punctuation),
            ),
            (r'"', Punctuation, "double-string"),
            (r"'", Punctuation, "single-string"),
            (
                r"(-?[\d.]+)(\:)(-?[\d.]+)(\:)(-?[\d.]+)",
                bygroups(
                    Literal.Number,
                    Punctuation,
                    Literal.Number,
                    Punctuation,
                    Literal.Number,
                ),
            ),
            (
                r"(-?[\d.]+)(\:)(-?[\d.]+)",
                bygroups(Literal.Number, Punctuation, Literal.Number),
            ),
            (r"-?[\d.]+(?:,-?[\d.]+)+", Literal.Number),
            (r"-?\d+", Number),
            (r"-?[\d.]+", Literal.Number.Float),
            (r"(-)(\w+)", bygroups(Punctuation, Name.Label)),
            (r"/", Punctuation, "pathcontent"),
            (r"(?<!\s)\s(?!\s)", Generic),
        ],
        "shellsy-statement": [
            (
                r"^[\w\._]+",
                Name.Function,
            ),
            (r"\\b\w+\\b", Keyword),
            (
                r"^(\$)([\w_]+)\s*(\:?)",
                bygroups(Punctuation, Name.Variable, Keyword),
            ),
            (r"^([\w._]+)", Error),
            include("shellsy-arguments"),
        ],
        "shellsy-array": [
            (r"\]", Punctuation, "#pop"),
            include("shellsy-arguments"),
        ],
    }


lexer = ShellsyLexer()
