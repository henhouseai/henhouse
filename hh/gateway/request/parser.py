from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import re
from typing import List, Optional, Union
from hh.gateway.request.token import Token, TokenKind, GrammarError
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init

trace_in = lambda message=None: None
trace_out = lambda message=None: None
log = lambda message: None
debug = lambda message: None
warn = lambda message: None

@register_debug_init
def _initialize_debug():
    global trace_in, trace_out, log, debug, warn
    trace_in = get_trace_in(True)
    trace_out = get_trace_out(True)
    log = get_log(True)
    debug = get_debug(True)
    warn = get_warn(True)

class ParserState(Enum):
    EXPECT_COMMAND = "EXPECT_COMMAND"
    EXPECT_ELEMENT = "EXPECT_ELEMENT"
    EXPECT_FLAG_VALUE_OR_NEXT = "EXPECT_FLAG_VALUE_OR_NEXT"

@dataclass
class ParsedValue:
    raw: str
    as_int: Optional[int]
    origin_index: int

@dataclass
class ParsedCommand:
    name: str
    default_value: Optional[ParsedValue]
    origin_index: int

@dataclass
class ParsedFlag:
    name: str
    value: Optional[ParsedValue]
    origin_index: int
    is_no: bool

@dataclass
class ParsedValueMarker:
    command_name: Optional[str]
    flag_name: Optional[str]
    origin_index: int

@dataclass
class ParsedCommandStream:
    primary_command: ParsedCommand
    additional_commands: List[ParsedCommand]
    flags: List[ParsedFlag]
    order: List[Union[ParsedCommand, ParsedFlag, ParsedValueMarker]]

def parse(tokens: List[Token]) -> ParsedCommandStream:
    trace_in()
    if not tokens:
        warn("Empty token stream provided to parser")
        trace_out()
        raise GrammarError("Empty token stream")
    log(f"Parsing {len(tokens)} tokens")
    state = ParserState.EXPECT_COMMAND
    i = 0
    primary_command: Optional[ParsedCommand] = None
    additional_commands: list[ParsedCommand] = []
    flags: list[ParsedFlag] = []
    order: list[ParsedCommand | ParsedFlag | ParsedValueMarker] = []
    while i < len(tokens):
        token = tokens[i]
        log(f"Processing token {i}: {token.kind.value}='{token.text}' in state {state.value}")
        if state == ParserState.EXPECT_COMMAND:
            if token.kind != TokenKind.COMMAND:
                warn(f"Missing leading command, got {token.kind.value}: '{token.text}' at position {token.origin_index}")
                trace_out()
                raise GrammarError(f"Missing leading command, got {token.kind.value}: '{token.text}' at position {token.origin_index}")
            command, next_i = _parse_command(tokens, i)
            primary_command = command
            order.append(command)
            i = next_i
            state = ParserState.EXPECT_ELEMENT
            log(f"Parsed primary command: '{command.name}', now expecting element")
        elif state == ParserState.EXPECT_ELEMENT:
            if token.kind == TokenKind.FLAG:
                flag, next_i = _parse_flag(tokens, i)
                flags.append(flag)
                order.append(flag)
                i = next_i
                state = ParserState.EXPECT_FLAG_VALUE_OR_NEXT
                log(f"Parsed flag: '{flag.name}', now expecting value or next element")
            elif token.kind == TokenKind.NO_FLAG:
                flag, next_i = _parse_no_flag(tokens, i)
                flags.append(flag)
                order.append(flag)
                i = next_i
                log(f"Parsed no-flag: '{flag.name}', staying in element state")
            elif token.kind == TokenKind.COMMAND:
                command, next_i = _parse_command(tokens, i)
                additional_commands.append(command)
                order.append(command)
                i = next_i
                log(f"Parsed additional command: '{command.name}'")
            elif token.kind == TokenKind.VALUE:
                warn(f"Value without owner: '{token.text}' at position {token.origin_index}")
                trace_out()
                raise GrammarError(f"Value without owner: '{token.text}' at position {token.origin_index}")
            else:
                warn(f"Unexpected token type: {token.kind.value} at position {token.origin_index}")
                trace_out()
                raise GrammarError(f"Unexpected token type: {token.kind.value} at position {token.origin_index}")
        elif state == ParserState.EXPECT_FLAG_VALUE_OR_NEXT:
            if token.kind == TokenKind.VALUE:
                if flags:
                    value = _parse_value(token)
                    flags[-1].value = value
                    order.append(ParsedValueMarker(
                        command_name=None,
                        flag_name=flags[-1].name,
                        origin_index=token.origin_index
                    ))
                    log(f"Added value '{value.raw}' to flag '{flags[-1].name}'")
                else:
                    warn("Value token found but no flags available")
                i += 1
                state = ParserState.EXPECT_ELEMENT
                log("Processed flag value, back to element state")
            else:
                state = ParserState.EXPECT_ELEMENT
                log("No value found, back to element state")
    if primary_command is None:
        warn("No primary command found in token stream")
        trace_out()
        raise GrammarError("No primary command found")
    result = ParsedCommandStream(
        primary_command=primary_command,
        additional_commands=additional_commands,
        flags=flags,
        order=order
    )
    log(f"Parse complete: {len(additional_commands)} additional commands, {len(flags)} flags")
    trace_out()
    return result

def _parse_command(tokens: List[Token], start_i: int) -> tuple[ParsedCommand, int]:
    trace_in()
    command_token = tokens[start_i]
    log(f"Parsing command: '{command_token.text}' at position {start_i}")
    i = start_i + 1
    default_value = None
    if i < len(tokens) and tokens[i].kind == TokenKind.VALUE:
        default_value = _parse_value(tokens[i])
        i += 1
        log(f"Command has default value: '{default_value.raw}'")
    else:
        log("Command has no default value")
    result = ParsedCommand(
        name=command_token.text,
        default_value=default_value,
        origin_index=command_token.origin_index
    )
    log(f"Parsed command: '{result.name}' with default_value={default_value is not None}")
    trace_out()
    return result, i

def _parse_flag(tokens: List[Token], start_i: int) -> tuple[ParsedFlag, int]:
    trace_in()
    flag_token = tokens[start_i]
    name = flag_token.text.lstrip('-')
    log(f"Parsing flag: '{flag_token.text}' -> name='{name}'")
    result = ParsedFlag(
        name=name,
        value=None,
        origin_index=flag_token.origin_index,
        is_no=False
    )
    log(f"Parsed flag: '{result.name}' (is_no={result.is_no})")
    trace_out()
    return result, start_i + 1

def _parse_no_flag(tokens: List[Token], start_i: int) -> tuple[ParsedFlag, int]:
    trace_in()
    no_flag_token = tokens[start_i]
    log(f"Parsing no-flag: '{no_flag_token.text}' at position {start_i}")
    if no_flag_token.text.startswith('--no-'):
        name = no_flag_token.text[5:]
        log(f"Detected --no- format, name='{name}'")
    elif no_flag_token.text.startswith('--no_'):
        name = no_flag_token.text[5:]
        log(f"Detected --no_ format, name='{name}'")
    else:
        warn(f"Invalid no-flag format: {no_flag_token.text}")
        trace_out()
        raise GrammarError(f"Invalid no-flag format: {no_flag_token.text}")
    if start_i + 1 < len(tokens) and tokens[start_i + 1].kind == TokenKind.VALUE:
        warn(f"No-flag cannot take value: '{no_flag_token.text}' followed by '{tokens[start_i + 1].text}'")
        trace_out()
        raise GrammarError(f"No-flag cannot take value: '{no_flag_token.text}' followed by '{tokens[start_i + 1].text}'")
    result = ParsedFlag(
        name=name,
        value=None,
        origin_index=no_flag_token.origin_index,
        is_no=True
    )
    log(f"Parsed no-flag: '{result.name}' (is_no={result.is_no})")
    trace_out()
    return result, start_i + 1

def _parse_value(token: Token) -> ParsedValue:
    trace_in()
    log(f"Parsing value: '{token.text}' at position {token.origin_index}")
    as_int = None
    if re.match(r'^\d+$', token.text):
        try:
            as_int = int(token.text)
            log(f"Value '{token.text}' converted to integer: {as_int}")
        except ValueError as e:
            log(f"Failed to convert '{token.text}' to integer: {e}")
    else:
        log(f"Value '{token.text}' is not numeric")
    result = ParsedValue(
        raw=token.text,
        as_int=as_int,
        origin_index=token.origin_index
    )
    log(f"Parsed value: raw='{result.raw}', as_int={result.as_int}")
    trace_out()
    return result
