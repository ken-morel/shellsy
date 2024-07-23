"""
djamago is a python library which will help you create simple chatbots
the simple way. It uses regular expressions to match queries and
provide a response with the best match
"""

import difflib
import math
import random
import re

import collections

from functools import cached_property
from pyoload import *
from typing import Any
from typing import Callable
from typing import Generator
from typing import Iterable

try:
    import nltk
except Exception:
    USE_NLTK = False
else:
    USE_NLTK = True


TopicList = Iterable[str | tuple[int | float, str]]


class _Response:
    """\
    Simply a type for responses, may be synchronious or asynchronios
    is a base class for the return of functions
    """
    __slots__ = ()

    def __iter__(self):
        return self


@annotate
class SyncResponse(_Response):
    """\
    A synchronious response return from a callback
    receives a generator as arguments which is used to generate the response
    """

    # __slots__ = ("pending", "generator", "responses")
    pending: bool
    generator: Generator
    responses: list[Any]

    def __init__(self, generator: Generator):
        """
        :param generator: The generator to use for response
        """
        self.generator = generator
        self.pending = True
        self.responses = []

    @cached_property
    def text(self):
        """
        Loops through the generator and returns the catenated output
        """
        while self.pending:
            try:
                self.responses.append(next(self))
            except StopIteration:
                self.pending = False
        return "".join(self.responses)

    def get(self) -> list[Any]:
        """
        Loops through the generator and returns the output list
        """
        while self.pending:
            try:
                self.responses.append(next(self))
            except StopIteration:
                self.pending = False
        return self.responses

    def __next__(self) -> Any:
        return next(self.generator)


@annotate
class Response(_Response):
    """\
    A response return from a callback
    """

    __slots__ = ("value", "read")
    value: Any
    read: bool

    def __init__(self, value: Any):
        """
        :param generator: The generator to use for response
        """
        self.value = value
        self.read = False

    @property
    def text(self):
        """
        Loops through the generator and returns the catenated output
        """
        return str(self.value)

    def get(self) -> Any:
        """
        Loops through the generator and returns the output list
        """
        return self.value

    def __next__(self):
        print("read", self.read)
        if self.read:
            raise StopIteration()
        else:
            self.read = True
            return self.text


@annotate
class Pattern:
    """
    Base class for creating any pattern, all pattern support a
    `.check` method used to get the actual score and node data
    it can provide.
    You may subclass it but never instantiate it directly.
    """

    def __init__(*_, **__):
        raise NotImplementedError()


@annotate
class Evaluator(Pattern):
    """
    Evaluator is a pyoload pattern which simply provides a way to
    get the score for a state-1 node.
    It may be used as decorator and recieves as argument a function
    which will return
    """

    def __init__(
        self, func: "Callable[[Node], tuple[float | str, dict, dict]]"
    ):
        """
        initializes the evaluator
        :param func: the function to be used as check
        """
        self.__func__ = func

    def check(
        self, node: "Node"
    ) -> tuple[int | float, int, dict[str | re.Pattern, str]]:
        val, var = self.__func__(node)
        return (
            val,
            {
                "callback_pattern_evaluator": self,
            },
            var,
        )


@annotate
class RegEx(Pattern):
    """
    Provides the base for regex pattern matching
    """

    @multimethod
    def __init__(self: Pattern, regex: Iterable[tuple[float | int, str]]):
        scores, res = zip(*regexs)
        res = map(re.compile, res)
        self.regexs = tuple(zip(res, scores))

    @multimethod
    def __init__(self: Pattern, regex: str, score: int | float = 100.0):
        """
        @multimethod
        def __init__(self: Pattern, regex: list[tuple[float | int, str]])
        @multimethod
        def __init__(self: Pattern, regex: str, score: int | float = 100.0)

        Initializes a new Regular expression as Pattern
        :param regex: the regex
        which will be used to match
        or a list of tuples (score, regular expression)
        which will be used to match
        Initializes a new Regular expression as Pattern
        :param score: If A regex specifyed, then it's specific score
        """
        pattern = re.compile(regex)
        self.regexs = [(score, pattern)]

    def check(self: "RegEx", node: "Node") -> tuple[int | float, dict, dict]:
        """
        Compares all the RegEx's stored on initialization to the string
        and if matching, returns the score and match object associated

        :param node: The state-1 node to test
        :returns: A tuple (score, param, var)
        """
        ms = []
        for id, (score, regex) in enumerate(self.regexs):
            if m := regex.fullmatch(node.query):
                ms.append(
                    (
                        score,
                        {
                            "callback_pattern_regex_id": id,
                        },
                        {
                            "match": m,
                        },
                    )
                )
        if len(ms) > 0:
            ms.sort(key=lambda m: m[0], reverse=True)
            return ms[0]
        else:
            return [(0, {}, {})]


class Expression(Pattern):
    r"""
    Expression class to create a new expression, in the expression syntax.

    Syntax:
        (name|"regex")(score)?( \(args\) )?

        - `"hello (.*)":100("world")`
        - `greetings("James":67)`
        - `hello:70("world":30)`
        - `greet(him:30, her:70)`

    the capture groups of the regex or of the expression name are passed
    for further matching by it's arguments

    in `"hello (.*)"("world")`, `(.*)` is passed to match "world"
    """

    ENTRIES: dict[str, list[tuple]] = {
        "-question": [
            (
                100,
                re.compile(
                    r"(?:please,?)?\s*(?:do you know|tell(?: me)?|may I ask)?"
                    r"\s*(.+)\??",
                ),
            ),
        ],
        "-whatis": [
            (100, re.compile(r"what\s*is\s*(.+)\?")),
            (50, re.compile(r".*what\s*is\s*(.+)\?")),
        ],
        "-whois": [
            (100, re.compile(r"who\s*is\s*(.+)\?")),
            (50, re.compile(r".*who\s*is\s*(.+)\?")),
        ],
        "-greetings": [
            (
                100,
                re.compile(
                    r"good\s*(?:morning|day|evening|night|afternoon)"
                    r"|greetings|hello"
                ),
            ),
            (
                30,
                re.compile(
                    r"(?:good\s*(?:morning|day|evening|night|afternoon)"
                    r"|greetings|hello)\s*.+"
                ),
            ),
        ],
        "-greetings-to": [
            (
                100,
                re.compile(
                    r"(?:good\s*(?:morning|day|evening|night|afternoon)"
                    r"|greetings|hello)\s*(.+)"
                ),
            ),
        ],
    }
    STRING_QUOTES = "'\""
    NAME_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_-@<>;"

    class ParsingError(ValueError):
        def __init__(self, begin, end, msg):
            self.params = (begin, end, msg)
            super().__init__(msg.format(begin, end))

        def moved(self, num: int):
            return self.__class__(
                self.params[0] + num, self.params[1] + num, self.params[2]
            )

    class AlreadyExists(ValueError):
        """
        Raised when an expression to `Expression.register`, already exists"""

    class DoesNotExist(ValueError):
        """
        Raised when an expression to `Expression.register`, already exists"""

    @classmethod
    @annotate
    def register(
        cls,
        name: str,
        vals: Iterable[tuple[float | int, str]],
    ) -> None:
        """
        Registers a new expression
        :param name: The name under which to register the expression
        could be a simple name as in `greetings` or a subclassing as
        `hello(a, b, ...)`
        :param vals: a list of tuples in the form (score, regex)
        to be used as match
        """
        parent_defs = []
        statement = name
        if "(" in name:
            begin = name.find("(")
            end = name.rfind(")")
            name, parents = name[:begin], name[begin + 1 : end]
            for parent in parents.split(","):
                parent = parent.strip()
                if not parent:
                    continue
                if parent not in cls.ENTRIES:
                    similar = []
                    for expr in cls.ENTRIES.keys():
                        similar.append(
                            (
                                difflib.SequenceMatcher(
                                    lambda *_: False, parent, expr
                                ).ratio(),
                                expr,
                            )
                        )
                    similar.sort(key=lambda k: -k[0])
                    add = ""
                    if len(similar) > 0 and similar[0][0]:
                        add = "Did you mean " + similar[0][1] + "?"
                    raise Expression.DoesNotExist(
                        f"Expression {name!r} subclasses {parent!r} in "
                        f"statement {statement!r} but expression {parent!r} "
                        "does not exist. " + add
                    )
                parent_defs.extend(cls.ENTRIES[parent])
        if name in cls.ENTRIES:
            raise Expression.AlreadyExists(
                f"Expression {name!r} already exists, may be you meant using "
                "Expression.override or Expression.extend"
            )
        cls.ENTRIES[name] = [
            (score, re.compile(txt)) for score, txt in vals
        ] + parent_defs

    @classmethod
    @annotate
    def override(
        cls,
        name: str,
        vals: Iterable[tuple[float | int, str]],
        _raise: bool = True,
    ) -> None:
        """
        Overrides an existing expression
        :param name: The expression name to override
        :param vals: new values
        :param _raise: Optional, if should raise `Expression.DoesNotExist` if
        does not exist
        """
        if name not in cls.ENTRIES and _raise:
            similar = []
            for expr in cls.ENTRIES.keys():
                similar.append(
                    (
                        difflib.SequenceMatcher(
                            lambda *_: False, parent, expr
                        ).ratio(),
                        expr,
                    )
                )
            similar.sort(key=lambda k: -k[0])
            add = ""
            if len(similar) > 0 and similar[0][0]:
                add = " or subclassing " + similar[0][1] + "?"
            raise Expression.DoesNotExist(
                f"you tried overriding {name!r}, which does not exist "
                f"may be you meant registering it" + add
            )
        cls.ENTRIES[name] = [(score, re.compile(txt)) for score, txt in vals]

    @classmethod
    @annotate
    def extend(
        cls,
        name: str,
        vals: Iterable[tuple[float | int, str]],
        _raise: bool = True,
    ) -> None:
        """
        Extends an existing expression
        :param name: The expression name to extend
        :param vals: new values to add
        :param _raise: Optional, if should raise `Expression.DoesNotExist` if
        does not exist
        """
        if name not in cls.ENTRIES and _raise:
            similar = []
            for expr in cls.ENTRIES.keys():
                similar.append(
                    (
                        difflib.SequenceMatcher(
                            lambda *_: False, parent, expr
                        ).ratio(),
                        expr,
                    )
                )
            similar.sort(key=lambda k: -k[0])
            add = ""
            if len(similar) > 0 and similar[0][0]:
                add = " or subclassing " + similar[0][1] + "?"
            raise Expression.DoesNotExist(
                f"you tried overriding {name!r}, which does not exist "
                f"may be you meant registering it" + add
            )
            raise Expression.DoesNotExist(
                f"you tried overriding {name!r}, which does not exist "
                f"may be you meant registering it"
            )
        cls.ENTRIES[name].extend(
            [(score, re.compile(txt)) for score, txt in vals],
        )

    @classmethod
    @annotate
    def alias(
        cls,
        alias: str,
        name: str,
        _raise: bool = True,
    ) -> None:
        """
        Extends an existing expression
        :param alias: The alias name
        :param name: The expression name to alias
        :param _raise: Optional, if should raise `Expression.DoesNotExist` if
        does not exist
        """
        if name not in cls.ENTRIES and _raise:
            similar = []
            for expr in cls.ENTRIES.keys():
                similar.append(
                    (
                        difflib.SequenceMatcher(
                            lambda *_: False, parent, expr
                        ).ratio(),
                        expr,
                    )
                )
            similar.sort(key=lambda k: -k[0])
            add = ""
            if len(similar) > 0 and similar[0][0]:
                add = similar[0][1] + "?"
            raise Expression.DoesNotExist(
                f"you tried aliassing {name!r}, which does not exist "
                f"may be you meant " + add
            )
        cls.ENTRIES[alias] = cls.ENTRIES[name]

    @staticmethod
    @annotate
    def parse(text: str) -> tuple[re.Pattern | str, list, str, int | float]:
        """
        Parses the passed expression string

        :param text: the string to parse

        :returns: a tuple (pattern or name, arguments, variablename, score)
        gotten from parsing the
        string.
        """
        score = 100
        pos = 0
        args = []
        name = ""

        intersection = set(Expression.STRING_QUOTES) & set(
            Expression.NAME_CHARS
        )
        if len(intersection) != 0:
            raise RuntimeError(
                f"found common characters {intersection} between "
                "djamago.Expression.STRING_QUOTES and "
                "djamago.Expression.NAME_CHARS"
            )

        text = text.strip()

        if text[pos] in Expression.STRING_QUOTES:  # Is a string liretal
            begin = pos + 1  # Index after quote
            end = (
                text[begin:].find(text[pos]) + begin
            )  # find quote after first, then add back index
            while text[end - 1] == "\\":
                text = text[end - 1 : end]
                begin2 = end + 1
                end = text[begin2:].find(text[pos]) + begin2

            if end - begin == -1:
                raise Expression.ParsingError(
                    begin,
                    end,
                    (
                        "Expression regex string literal began at {0}"
                        " but never closed"
                    ),
                )
            elif end - begin == 0:
                raise Expression.ParsingError(
                    begin, end, "empty expression string at {1}"
                )
            else:
                regex = re.compile(text[begin:end])
                pos = end + 1
        elif text[pos] in Expression.NAME_CHARS:
            end = begin = pos
            while len(text) > end and text[end] in Expression.NAME_CHARS:
                end += 1
            # regex = Expression.ENTRIES.get(text[begin:end])
            # if regex is None:
            #     raise Expression.ParsingError(
            #         begin,
            #         end,
            #         "expression '"
            #         + text[begin:end]
            #         + "' never registerred at {0} to {1}",
            #     )
            regex = text[begin:end]
            pos = end
        else:
            raise Expression.ParsingError(
                pos,
                pos,
                f"Primary name or regex expression missing in {text!r}[{pos}]",
            )
        if len(text) > pos and text[pos] == "(":  # arguments
            pos += 1
            still_args = True
            while len(text) > pos and still_args:  # a loop for each arg
                stack: list[int] = []  # the expression stack
                begin = pos
                if text[pos] == " ":
                    pos += 1
                    continue
                elif text[pos] == ")":
                    pos += 1
                    break
                for pos in range(begin, len(text)):
                    if text[pos] in "," and len(stack) == 0:
                        pos += 1
                        break
                    elif text[pos] in ")" and len(stack) == 0:
                        still_args = False
                        pos += 1
                        break
                    elif text[pos] == " " and len(stack) == 0:
                        continue
                    elif text[pos] == "(":
                        stack.append(pos)
                    elif text[pos] == ")":
                        stack.pop()
                if len(stack) > 0:
                    raise Expression.ParsingError(
                        stack[-1],
                        pos,
                        "brace opened at {0} never closed",
                    )
                try:
                    end = pos
                    parsed = Expression.parse(text[begin:end])
                except Expression.ParsingError as e:
                    raise e.moved(begin) from e
                else:
                    args.append(parsed)
        if len(text) > pos and text[pos] == "#":
            begin = pos = pos + 1
            while len(text) > pos and text[pos] in Expression.NAME_CHARS:
                pos += 1
            end = pos
            name = text[begin:end]
        if len(text) > pos and text[pos] == ":":
            begin = pos = pos + 1
            while (
                len(text) > pos and text[pos].isnumeric() or text[pos] == "."
            ):
                pos += 1
            end = pos
            score = int(text[begin:end])
        return (regex, args, name, score)

    @classmethod
    @annotate
    def _check(
        cls,
        name: str | re.Pattern,
        params: Iterable[tuple | re.Pattern],
        varname: str,
        string: str,
    ) -> tuple[int | float, dict, dict[str, str]]:
        """
        Performs the expressional check "name", with the specified args

        :param name: The name or re.Pattern to test
        :param nscore: The score to scale
        :param varname: the variable name to store the match
        :param params: The actual parameters for subchecking
        :param string: The string to evaluate

        :returns: a tuple: (score, param, var)
        """
        tests = []
        if isinstance(name, str):
            try:
                regexs = cls.ENTRIES[name]
            except KeyError:
                similar = []
                for expr in cls.ENTRIES.keys():
                    similar.append(
                        (
                            difflib.SequenceMatcher(
                                lambda *_: False, name, expr
                            ).ratio(),
                            expr,
                        )
                    )
                similar.sort(key=lambda k: -k[0])
                add = ""
                if len(similar) > 0 and similar[0][0] > 0.5:
                    add = " May be you meant " + similar[0][1] + "?"
                raise Expression.DoesNotExist(
                    f"Expression {name!r}, does not exist." + add
                )
        elif isinstance(name, re.Pattern):
            regexs = [(100, name)]
        for id, (score, regex) in enumerate(regexs):
            vars = {}
            mat = regex.fullmatch(string)
            if not mat:
                continue
            args = mat.groups()
            args = args[: len(params)]
            if len(params) != len(args):
                continue
            match_score = -1
            for param, arg in zip(params, args):
                if isinstance(param, tuple):
                    paramname, paramargs, paramvarname, paramscore = param
                    vars[paramvarname] = arg
                    pscore, _, pvars = Expression._check(
                        paramname,
                        paramargs,
                        paramvarname,
                        arg,
                    )
                    vars |= pvars
                    if pscore == -1:
                        continue
                    else:
                        match_score += pscore / 100 * paramscore
                elif isinstance(param, re.Pattern):
                    if param.fullmatch(arg):
                        match_score += 100
                    else:
                        return -1, {}, {}
                else:
                    raise Exception()
            if match_score > -1:
                match_score += 1
            if len(params) == 0:
                match_score = 100
            tests.append(
                (
                    match_score / 100 * score,
                    {
                        "sub_pattern_id": id,
                    },
                    vars,
                )
            )

        if len(tests) == 0:
            return (-1, {}, {})
        else:
            tests.sort(key=lambda k: k[0], reverse=True)
            return tests[0]

    @annotate
    def __init__(self, expr: str):
        """
        Initializes an expression with the passed string

        :param expr: The expression to be parsed
        """
        self.text = expr
        self.regex, self.params, self.name, self.score = Expression.parse(expr)

    def __str__(self):
        return f"<Expression({self.text!r})>"

    @annotate
    def check(self, node: "Node") -> _check.__annotations__.get("return"):
        """
        Performs the check of the passed node to find the match score
        and state-2 node data.

        :param node: The node to score

        :returns: a tuple (score, param, var)
        """
        score, param, var = Expression._check(
            self.regex, self.params, self.name, node.query
        )
        return (score / 100 * self.score, param, var)


class Callback:
    """
    Creates a new callback expression to be used in a standard topic.
    It's instance is used as a decorator in a method definition in
    a Class definition of a subclass of `Topic`

    >>> class Topic(djamago.Topic)
    ...     @Callback(...)
    ...     def myfunc(Node):
    ...         pass
    """

    __func__: Callable
    patterns: list[tuple[int | float, Pattern]]

    @overload
    def __init__(self, pattern: str | Pattern):
        """
        Initializes the new callback with the specified arguments

        :param pattern: The Pattern to be used as check or a list of tuple
        mappings of (score, pattern)
        """
        if isinstance(pattern, str):
            pattern = Expression(pattern)
        self.patterns = [(100, pattern)]

    @overload
    def __init__(
        self,
        patterns: Iterable[tuple[int | float, Pattern | str] | Pattern | str],
    ):
        self.patterns = []
        for pattern in patterns:
            score = 100
            if isinstance(pattern, tuple):
                score, pattern = pattern
            if isinstance(pattern, str):
                if pattern.startswith("regex$"):
                    pattern = RegEx(pattern[6:])
                else:
                    pattern = Expression(pattern)
                self.patterns.append((score, pattern))

    @annotate
    def __call__(
        self,
        func: Callable | None = None,
        *,
        responses: Iterable[str] | str = (),
        topics=None,
        next=None,
    ):
        """
        Simple decorator over the callback the Callback object should call
        :param func: The callback to use

        :param responses: automatic responses if no func
        :param topics: automatic topics if no func
        :param next: automatic next if no func
        :returns: self
        """
        if isinstance(responses, str):
            responses = (responses,)
        if func is not None:
            self.__func__ = func
        else:
            def _func(node):
                import random

                if topics is not None:
                    node.set_topics(topics)
                if next is not None:
                    node.next = next
                return Response(random.choice(responses) % node.vars)
            self.__func__ = _func
        return self

    def __set_name__(self, obj: Type, name: str) -> None:
        obj.register(self)
        self.topic = obj
        self.name = name

    def __get__(self, obj: "Topic") -> "Callback":
        return self

    @annotate
    def respond(self, node: "Node") -> None:
        """
        Used the contained arguments to answer a state-2 node

        :param node: The state-2 node to answer
        :returns: None
        """
        if not hasattr(self, "__func__"):
            raise RuntimeError("Callable not decorated")
        node.response = self.__func__(node)

    @annotate
    def check(self, node: "Node") -> Iterable[tuple[int | float, dict, dict]]:
        """
        Performs the score evaluation on a state-1 node

        :param node: The state-1 node to evaluate
        :returns: a list of tuples (score, param, var)
        """
        matches = []
        for cpid, (pscore, pattern) in enumerate(self.patterns):
            score, param, var = pattern.check(node)
            if score >= 0:
                matches.append(
                    (
                        score / 100 * pscore,
                        param
                        | {
                            "callback_pattern_id": cpid,
                            "callback_pattern": (pscore, pattern),
                        },
                        var,
                    )
                )
        return matches


class Topic:
    """
    A topic to be used to group several callbacks together
    """

    _callbacks: list[Callback]
    name: str = None

    @classmethod
    @annotate
    def register(cls, callback: Callback) -> None:
        """
        Registers a new callback in the Topic

        :param callback: the callback to register
        :returns: None
        """
        if not hasattr(cls, "_callbacks"):
            cls._callbacks = []
        cls._callbacks.append(callback)

    @classmethod
    @annotate
    def get_callback(cls, name: str) -> Callback:
        for callback in cls._callbacks:
            if callback.name == name:
                return callback
        else:
            matches = []
            for callback in cl._callbacks:
                matches.append(
                    (
                        difflib.SequenceMatcher(
                            lambda *_: False, name, callback.name
                        ).ratio(),
                        callback.name,
                    )
                )
            matches.sort(key=lambda k: -k[0])
            add = ""
            if len(matches) > 0 and matches[0][0] > 0.5:
                add = " May be you meant " + matches[0][1]
            raise KeyError(f"callback {name!r} not in topic {cls!r}." + add)

    @classmethod
    @annotate
    def matches(cls, node: "Node") -> Iterable[tuple[float | int, dict, dict]]:
        """
        Gets all the callback matches for a specific state-1 node

        :param node: The node to evaluate

        :returns: a list of tuples (score, param, var)
        """
        matches = []
        for callback in cls._callbacks:
            for score, params, var in callback.check(node):
                matches.append(
                    (
                        score,
                        params
                        | {
                            "callback": callback,
                            "topic": cls,
                        },
                        var,
                    )
                )
        return matches

    @classmethod
    @annotate
    def respond(cls, node: "Node") -> None:
        """
        Responds to a state-2 node with the contained data

        :param node: The node to respond

        :returns: None
        """
        node.params["callback"].respond(node)

    def __init__(*_, **__):
        raise NotImplementedError("Topic classes are not to be instantiated")


@annotate
def use_nltk(val: bool | type(None) = None) -> bool:
    """
    With args: tells djamago if it should use nltk, if true
    makes sure the required plugins are installed at first
    Without args: returns if djamago uses nltk

    :param val: If djamago should use nltk

    :returns: USE_NLTK
    """
    global USE_NLTK
    if val:
        nltk.download("punkt")
        nltk.download("wordnet")
        nltk.download("stopwords")
    if val is not None:
        USE_NLTK = val
    return USE_NLTK


Token = list[str]


class QA(Topic):
    """
    Base topic subclass to register QA list to be used as fallback topic
    or as integral part of djamago instance
    """

    jaccard_score: float = 0.5
    cosine_score: float = 1.5
    difflib_score: float = 1
    min_score: float | int = 70.0

    @staticmethod
    @annotate
    def tokenize(text: str) -> Token:
        """
        Normalizes the passed string into List of strings, removing junk
        :param text: the text to normalize

        :returns: a list of strings
        """
        if use_nltk():
            from nltk.corpus import stopwords
            from nltk.stem import WordNetLemmatizer
            from nltk.tokenize import word_tokenize

            tokens = word_tokenize(text.lower())
            stop_words = set(stopwords.words("english"))
            tokens = [t for t in tokens if t not in stop_words]  # junk
            lemmatizer = WordNetLemmatizer()
            tokens = [lemmatizer.lemmatize(t) for t in tokens]  # singular
            return tokens
        else:
            return text.split(" ")

    @annotate
    def jaccard_similarity(a: Token, b: Token) -> float:
        """
        Calculates the jaccard similarity per cent of two list of strings

        Jaccard = len(union) / len(intersection) * 100
        """
        intersection = set(a) & set(b)
        union = set(a) | set(b)
        le = len(union)
        if le == 0:
            return 0.0
        else:
            return len(intersection) / le * 100

    @annotate
    def cosine_similarity(a: Token, b: Token) -> float:
        """
        Computes the cosine similarity per cent between two list of strings
        """
        a = list(collections.Counter(a).values())
        b = list(collections.Counter(b).values())
        dot_product = sum(av * bv for av, bv in zip(a, b))
        magnitude_a = math.sqrt(sum(av**2 for av in a))
        magnitude_b = math.sqrt(sum(bv**2 for bv in b))
        mag = magnitude_a * magnitude_b
        if mag == 0:
            return 0.0
        else:
            return dot_product / mag * 100

    @annotate
    def difflib_similarity(a: Token, b: Token) -> float:
        """
        Uses difflib.SequenceMatcher to compare the reconstitutions of
        two list of strings returning the percent ratio
        """
        import difflib

        return (
            difflib.SequenceMatcher(
                lambda x: x == " -._",
                " ".join(a),
                " ".join(b),
            ).ratio()
            * 100.0
        )

    @annotate
    def levenshtein_distance(a: Token, b: Token) -> int:
        """
        Finds the levenshtein distance between two list of strings
        """
        m, n = len(a), len(b)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                cost = 0 if a[i - 1] == b[j - 1] else 1
                dp[i][j] = min(
                    dp[i - 1][j] + 1,
                    dp[i][j - 1] + 1,
                    dp[i - 1][j - 1] + cost,
                )
        return dp[m][n]

    @staticmethod
    @overload
    def similarity(a: str, b: str) -> float:
        return QA.similarity(QA.tokenize(a), QA.tokenize(b))

    @staticmethod
    @overload
    def similarity(a: Token, b: Token) -> float:
        """
        Uses the `QA.jaccard_similarity`, `QA.cosine_similarity`,
        `QA.difflib_similarity` to find the similarity between the two strings
        or tokens and returns the result

        It scales the ratios according to `QA.jaccard_score`,
        `QA.cosine_score` and `QA.difflib_score`.
        """
        return sum(
            (
                QA.jaccard_similarity(a, b) * QA.jaccard_score,
                QA.cosine_similarity(a, b) * QA.cosine_score,
                QA.difflib_similarity(a, b) * QA.difflib_score,
            )
        ) / sum((QA.jaccard_score, QA.cosine_score, QA.difflib_score))

    class QA:
        """
        A quetion and answer instance of QA, it represents A question list
        and corresponding answers
        """

        questions: list[float, str]
        answers: list[str]
        tokens: Iterable[tuple[int | float, list[str]]]

        def check(
            self, node: "Node"
        ) -> Iterable[tuple[int | float, dict, dict]]:
            """
            Compares all the questions tokens to that of the node query
            and returns the matches score and parameters with the question
            in variables.

            :param node: THe node to check

            :returns: A list of tuples (score, param, var)
            """
            matches = []
            qtoken = QA.tokenize(node.query)
            for id, (score, question, token) in enumerate(self.questions):
                m = (
                    QA.similarity(qtoken, token) / 100 * score,
                    {
                        "qa_qa_question_id": id,
                        "qa_qa": self,
                        "qa_qa_question_question": question,
                    },
                    {
                        "question": question,
                    },
                )
                if m[0] > self.qa.min_score:
                    matches.append(m)
            return matches

        @annotate
        def respond(self, node: "Node"):
            """
            Responds to a Node with one of the contained answers

            :param node: The node to answer
            """
            node.response = random.choice(self.answers)

        def __init__(self, questions, answers, qa=None):
            """
            Initializes the QA.QA with the passed list of questions and answers

            :param questions: a list of strings or mappings (score, string)
            :param answers: The answers to use
            :param qa: The parent `djamago.QA` object
            """
            if qa is not None:
                self.qa = qa
            else:
                self.qa = QA
            if isinstance(questions, str):
                questions = [questions]
            if isinstance(answers, str):
                answers = [answers]
            self.questions = []
            self.answers = tuple(answers)
            for question in questions:
                if isinstance(question, tuple):
                    score, question = question
                else:
                    score = 100
                self.questions.append((score, question, QA.tokenize(question)))

    questions: list[int]

    @classmethod
    @annotate
    def matches(cls, node: "Node") -> Iterable[tuple[int | float, dict, dict]]:
        f"""{Topic.matches.__doc__}"""
        matches = []
        for qa in cls.QAs:
            for score, param, var in qa.check(node):
                matches.append(
                    (
                        score,
                        param
                        | {
                            "qa": cls,
                            "topic": cls,
                        },
                        var,
                    )
                )
        return matches

    def __init_subclass__(cls):
        if hasattr(cls, "QAs"):
            return
        else:
            cls.QAs = []
        if hasattr(cls, "data"):
            data = cls.data
        elif hasattr(cls, "source_json"):
            import json

            with open(cls.source_json) as f:
                data = json.loads(f.read())
        elif hasattr(cls, "source_yaml"):
            import yaml

            with open(cls.source_yaml) as f:
                data = yaml.safe_load(f.read())
        else:
            data = []
        for questions, answers in data:
            cls.QAs.append(QA.QA(questions, answers))

    @annotate
    @classmethod
    def respond(cls, node: "Node"):
        """
        respond to a state-2 node

        :param node: The node to respond
        """
        node.params["qa_qa"].respond(node)
        cls.format_response(node)

    @staticmethod
    def format_response(node: "Node") -> None:
        """
        A callback to override in QA subclass, which receives the node before
        it is returned back.
        :param node: The node to format
        """


@annotate
class Node:
    __slots__ = (
        "topics",
        "parent",
        "response",
        "query",
        "score",
        "vars",
        "params",
        "raw_query",
        "candidates",
        "next",
        "response",
    )

    topics: Iterable[tuple[float | int, str]]
    parent: "Node | type(None)"
    response: str
    query: str
    score: int | float
    vars: dict
    params: dict
    candidates: Iterable[tuple[int | float, dict, dict]]
    next: (
        str
        | Callback
        | Iterable[str | Callback]
        | Iterable[tuple[float | int, str | Callback]]
    )
    response: _Response

    @annotate
    def __init__(
        self,
        query: str,
        raw_query: str,
        topics: list | tuple = (),
        parent: "Node | type(None)" = None,
        response: Response = None,
    ):
        """
        Creates a new node with the passes parameters

        :param query: The query
        :param raw_query: The unprocessed query
        :param topics: The primary list of topics
        :param parent: The parent of the node
        :param response: An optional response
        """
        self.set_topics(topics)
        self.parent = parent
        if response is not None:
            self.response = response
        else:
            self.response = Response("")
        self.query = query
        self.raw_query = raw_query
        self.score = 0
        self.params = {}
        self.vars = {}
        self.candidates = ()
        self.next = ()

    def __str__(self):
        return (
            f"<djamado.Node({self.query!r}) ->{self.score}"
            f":{self.topics}:{self.response!r}:>"
        )

    @annotate
    def hierarchy(self):
        obj = self
        while obj is not None:
            yield obj
            obj = obj.parent
        raise StopIteration()

    def set_topics(self, topics):
        if isinstance(topics, str):
            self.topics = ((100, topics),)
        else:
            self.topics = tuple(
                [
                    topic if isinstance(topic, tuple) else (100, topic)
                    for topic in topics
                ]
            )

    def add_topic(self, topic):
        self.set_topics(self.topics + (topic,))


@annotate
class Djamago:
    topics: dict[str, Topic]
    nodes: list[Node]
    name: str
    initial_node: Node

    def __init_subclass__(cls):
        cls.topics = {}

    @classmethod
    def get_topic(cls, name: str):
        """
        Queries a topic from the topic name
        """
        return cls.topics[name]

    def __init__(self, name: str = "", initial_node=None, topics=None):
        """
        Initializes the djamago object

        :param name: The name of the chatbot
        :param initial_node: An optional initial node
        :param topics: THe topics for the inital node
        """
        self.name = name
        node = initial_node or Node(
            topics=tuple(self.topics.keys()),
            parent=None,
            query="",
            raw_query="",
            response=Response(""),
        )
        if topics is not None:
            node.set_topics(topics)
        self.nodes = [node]

    @unannotable
    @overload
    def respond(self, query: str) -> Node:
        """
        Returns the response node to a string query
        """
        node = Node(
            parent=self.nodes[-1],
            raw_query=query,
            query=query.lower(),
            topics=self.nodes[-1].topics,
        )
        self.respond_node(node)
        self.nodes.append(node)
        return node

    @unannotable
    @respond.overload
    def respond_node(self, node: Node) -> None:
        """
        Responds to a state-1 node
        """
        matches = []
        usedNext = False
        if hasattr(node.parent, "next") and node.parent.next:
            usedNext = True
            next = node.parent.next
            if isinstance(next, tuple):
                for callback in next:
                    score = 100
                    if isinstance(callback, tuple):
                        score, callback = callback
                    if isinstance(callback, str):
                        ct, cn = callback.split(".")
                        callback = self.get_topic(ct).get_callback(cn)
                    matches.extend(
                        (s / 100 * score, p, v)
                        for s, p, v in callback.check(node)
                    )
            else:
                matches.extend(next.check(node))
        else:
            for topic in node.parent.topics:
                if isinstance(topic, tuple):
                    score, topic = topic
                else:
                    score = 100
                matches.extend(
                    [
                        (sscore / 100 * score, param, var)
                        for (sscore, param, var) in self.get_topic(
                            topic
                        ).matches(node)
                    ]
                )
        while True:
            matches.sort(key=lambda m: m[0], reverse=True)
            node.candidates = tuple(matches)
            for idx, (score, param, var) in enumerate(tuple(matches)):
                node.params = param
                node.vars = var
                node.score = score
                try:
                    return param["topic"].respond(node)
                except ScoreChange as scorechange:
                    matches[idx] = (
                        scorechange.score,
                        param | scorechange.param,
                        var | scorechange.var,
                    )
                    break
            else:
                raise ValueError(
                    "Node did not find any match"
                    + (
                        ". Note, The parent node had a .next attribute"
                        if usedNext
                        else ""
                    )
                )

    @classmethod
    def topic(cls, topic: type):
        """
        Registers a new Topic to the djamago subclass
        """
        name = topic.name or topic.__name__.lower()
        cls.topics[name] = topic
        return topic


class ScoreChange(ValueError):
    """
    ScoreChange, to raise in a callback to update the score,

    raise ScoreChange(-1)

    """

    score: int | float
    param: dict
    var: dict

    @annotate
    def __init__(
        self,
        score: int | float = -1,
        param: dict = {},
        var: dict = {},
    ):
        """
        :param score: The new score for the callback
        """
        self.score = score
        self.param = param
        self.var = var
        super().__init__(
            f"Score changed to {score}. Should normally be caught by djamago."
            ", if you see this please report at "
            "https://github.com/ken-norel/djamago/issues/new"
        )


__version__ = "0.1.0"
