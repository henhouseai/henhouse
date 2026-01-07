from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import re
from typing import List, Optional, Union
from hh.gateway.request.token import Token, TokenKind, GrammarError
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.gateway.error.error_store import report_error

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
    as_value: Optional[Union[int, float]]  # Numeric value (int or float), None if not numeric
    origin_index: int

@dataclass
class ParsedCommand:
    name: str
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
    primary_command: Optional[ParsedCommand]  # Optional to support partial parsing on error
    additional_commands: List[ParsedCommand]
    flags: List[ParsedFlag]
    order: List[Union[ParsedCommand, ParsedFlag, ParsedValueMarker]]

def parse(tokens: List[Token]) -> ParsedCommandStream:
    trace_in()
    if not tokens:
        error_msg = "Empty token stream"
        warn(error_msg)
        report_error("request", error_msg)
        trace_out()
        raise GrammarError(error_msg)
    log(f"Parsing {len(tokens)} tokens")
    state = ParserState.EXPECT_COMMAND
    i = 0
    primary_command: Optional[ParsedCommand] = None
    additional_commands: list[ParsedCommand] = []
    flags: list[ParsedFlag] = []
    order: list[ParsedCommand | ParsedFlag | ParsedValueMarker] = []
    try:
        while i < len(tokens):
            token = tokens[i]
            log(f"Processing token {i}: {token.kind.value}='{token.text}' in state {state.value}")
            if state == ParserState.EXPECT_COMMAND:
                if token.kind != TokenKind.COMMAND:
                    error_msg = f"Missing leading command, got {token.kind.value}: '{token.text}' at position {token.origin_index}"
                    warn(error_msg)
                    report_error("request", error_msg)
                    trace_out()
                    raise GrammarError(error_msg)
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
                    # Context-aware: convert COMMAND to FLAG (not additional command)
                    # This happens after primary command - bare commands become flags
                    flag, next_i = _parse_command_as_flag(tokens, i)
                    flags.append(flag)
                    order.append(flag)
                    i = next_i
                    state = ParserState.EXPECT_FLAG_VALUE_OR_NEXT
                    log(f"Converted COMMAND '{flag.name}' to FLAG, now expecting value or next element")
                elif token.kind == TokenKind.VALUE:
                    error_msg = f"Value without owner: '{token.text}' at position {token.origin_index}"
                    warn(error_msg)
                    report_error("request", error_msg)
                    trace_out()
                    raise GrammarError(error_msg)
                elif token.kind == TokenKind.NUMBER:
                    error_msg = f"Number without owner: '{token.text}' at position {token.origin_index}"
                    warn(error_msg)
                    report_error("request", error_msg)
                    trace_out()
                    raise GrammarError(error_msg)
                else:
                    error_msg = f"Unexpected token type: {token.kind.value} at position {token.origin_index}"
                    warn(error_msg)
                    report_error("request", error_msg)
                    trace_out()
                    raise GrammarError(error_msg)
            elif state == ParserState.EXPECT_FLAG_VALUE_OR_NEXT:
                if token.kind == TokenKind.VALUE:
                    # Quoted string value
                    if flags:
                        value = _parse_value(token)
                        flags[-1].value = value
                        order.append(ParsedValueMarker(
                            command_name=None,
                            flag_name=flags[-1].name,
                            origin_index=token.origin_index
                        ))
                        log(f"Added string value '{value.raw}' to flag '{flags[-1].name}'")
                    else:
                        warn("Value token found but no flags available")
                    i += 1
                    state = ParserState.EXPECT_ELEMENT
                    log("Processed flag value, back to element state")
                elif token.kind == TokenKind.NUMBER:
                    # Number value (convert to ParsedValue with numeric conversion)
                    if flags:
                        value = _parse_number_value(token)
                        flags[-1].value = value
                        order.append(ParsedValueMarker(
                            command_name=None,
                            flag_name=flags[-1].name,
                            origin_index=token.origin_index
                        ))
                        log(f"Added number value '{value.raw}' (as_value={value.as_value}) to flag '{flags[-1].name}'")
                    else:
                        warn("Number token found but no flags available")
                    i += 1
                    state = ParserState.EXPECT_ELEMENT
                    log("Processed flag number value, back to element state")
                elif token.kind == TokenKind.COMMAND:
                    # Context-aware: convert COMMAND to VALUE (unquoted string value)
                    if flags:
                        value = _parse_command_as_value(token)
                        flags[-1].value = value
                        order.append(ParsedValueMarker(
                            command_name=None,
                            flag_name=flags[-1].name,
                            origin_index=token.origin_index
                        ))
                        log(f"Converted COMMAND '{token.text}' to VALUE for flag '{flags[-1].name}'")
                    else:
                        warn("Command token found as value but no flags available")
                    i += 1
                    state = ParserState.EXPECT_ELEMENT
                    log("Processed command as flag value, back to element state")
                else:
                    # No value provided - flag becomes boolean (truthy)
                    state = ParserState.EXPECT_ELEMENT
                    log("No value found, flag remains boolean, back to element state")
    except GrammarError as e:
        # Error encountered during token processing - return partial results
        # Everything parsed before the error is kept, error token and everything after discarded
        warn(f"Grammar error encountered during parsing, returning partial result: {e}")
        result = ParsedCommandStream(
            primary_command=primary_command,
            additional_commands=additional_commands,
            flags=flags,
            order=order
        )
        log(f"Returning partial parse: primary_command={primary_command is not None}, {len(flags)} flags")
        trace_out()
        return result
    
    # Parsing completed successfully - build final result
    if primary_command is None:
        error_msg = "No primary command found in token stream"
        warn(error_msg)
        report_error("request", error_msg)
        trace_out()
        raise GrammarError(error_msg)
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
    # Commands don't have default values - leave VALUE tokens in stream to be caught as orphaned
    result = ParsedCommand(
        name=command_token.text,
        origin_index=command_token.origin_index
    )
    log(f"Parsed command: '{result.name}'")
    trace_out()
    return result, i

def _parse_flag(tokens: List[Token], start_i: int) -> tuple[ParsedFlag, int]:
    trace_in()
    flag_token = tokens[start_i]
    # Tokenizer already stripped dashes, so name is just the text
    name = flag_token.text
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
    # Tokenizer already stripped --no- or --no_ prefix, so name is just the text
    name = no_flag_token.text
    log(f"Parsing no-flag: '{no_flag_token.text}' -> name='{name}' at position {start_i}")
    if start_i + 1 < len(tokens) and (tokens[start_i + 1].kind == TokenKind.VALUE or tokens[start_i + 1].kind == TokenKind.NUMBER or tokens[start_i + 1].kind == TokenKind.COMMAND):
        error_msg = f"No-flag cannot take value: '{no_flag_token.text}' followed by '{tokens[start_i + 1].text}'"
        warn(error_msg)
        report_error("request", error_msg)
        trace_out()
        raise GrammarError(error_msg)
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
    """Parse a VALUE token (quoted string) as ParsedValue."""
    trace_in()
    log(f"Parsing value: '{token.text}' at position {token.origin_index}")
    # Quoted strings are always strings, not numbers
    result = ParsedValue(
        raw=token.text,
        as_value=None,
        origin_index=token.origin_index
    )
    log(f"Parsed value: raw='{result.raw}', as_value={result.as_value}")
    trace_out()
    return result

def _parse_number_value(token: Token) -> ParsedValue:
    """Parse a NUMBER token as ParsedValue with numeric conversion."""
    trace_in()
    log(f"Parsing number value: '{token.text}' at position {token.origin_index}")
    as_value: Optional[Union[int, float]] = None
    try:
        # Try integer first
        if re.match(r'^-?\d+$', token.text):
            as_value = int(token.text)
            log(f"Number '{token.text}' converted to integer: {as_value}")
        else:
            # Try float
            float_value = float(token.text)
            # If it's a whole number, store as int
            if float_value.is_integer():
                as_value = int(float_value)
                log(f"Number '{token.text}' converted to integer: {as_value}")
            else:
                as_value = float_value
                log(f"Number '{token.text}' converted to float: {as_value}")
    except ValueError as e:
        log(f"Failed to convert '{token.text}' to number: {e}")
    result = ParsedValue(
        raw=token.text,
        as_value=as_value,
        origin_index=token.origin_index
    )
    log(f"Parsed number value: raw='{result.raw}', as_value={result.as_value}")
    trace_out()
    return result

def _parse_command_as_flag(tokens: List[Token], start_i: int) -> tuple[ParsedFlag, int]:
    """Convert a COMMAND token to a ParsedFlag (context-aware conversion)."""
    trace_in()
    command_token = tokens[start_i]
    log(f"Converting COMMAND '{command_token.text}' to FLAG at position {start_i}")
    result = ParsedFlag(
        name=command_token.text,
        value=None,
        origin_index=command_token.origin_index,
        is_no=False
    )
    log(f"Converted COMMAND to flag: '{result.name}'")
    trace_out()
    return result, start_i + 1

def _parse_command_as_value(token: Token) -> ParsedValue:
    """Convert a COMMAND token to a ParsedValue (unquoted string value)."""
    trace_in()
    log(f"Converting COMMAND '{token.text}' to VALUE at position {token.origin_index}")
    # Command becomes an unquoted string value
    result = ParsedValue(
        raw=token.text,
        as_value=None,
        origin_index=token.origin_index
    )
    log(f"Converted COMMAND to value: raw='{result.raw}'")
    trace_out()
    return result
