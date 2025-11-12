from __future__ import annotations
from enum import Enum
from typing import NamedTuple

class TokenKind(Enum):
    COMMAND = "COMMAND"
    FLAG = "FLAG"
    NO_FLAG = "NO_FLAG"
    VALUE = "VALUE"
    UNKNOWN = "UNKNOWN"

class QuoteStyle(Enum):
    NONE = "none"
    SINGLE = "single"
    DOUBLE = "double"

class Token(NamedTuple):
    kind: TokenKind
    text: str
    origin_index: int
    span: tuple[int, int]
    quote_style: QuoteStyle

class TokenizationError(Exception):
    pass

class GrammarError(Exception):
    pass
