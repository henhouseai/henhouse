from __future__ import annotations
import re
from typing import List, Sequence
from hh.gateway.request.token import Token, TokenKind, QuoteStyle, TokenizationError
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

def tokenize(argv: Sequence[str]) -> List[Token]:
    trace_in()
    if not argv:
        log("Empty argv provided, returning empty token list")
        trace_out()
        return []
    log(f"Tokenizing {len(argv)} arguments: {argv}")
    raw_tokens = []
    for i, arg in enumerate(argv):
        log(f"Processing argument {i}: '{arg}'")
        if arg == "":
            raw_tokens.append(Token(
                kind=TokenKind.VALUE,
                text="",
                origin_index=i,
                span=(i, i + 1),
                quote_style=QuoteStyle.NONE
            ))
            log(f"Added empty value token at position {i}")
            continue
        quote_style = _detect_quote_style(arg)
        log(f"Detected quote style: {quote_style.value}")
        if quote_style != QuoteStyle.NONE:
            if quote_style == QuoteStyle.DOUBLE and arg.startswith('"') and arg.endswith('"'):
                text = arg[1:-1]
                log(f"Extracted double-quoted text: '{text}'")
            elif quote_style == QuoteStyle.SINGLE and arg.startswith("'") and arg.endswith("'"):
                text = arg[1:-1]
                log(f"Extracted single-quoted text: '{text}'")
            else:
                warn(f"Unmatched quotes in argument: {arg}")
                trace_out()
                raise TokenizationError(f"Unmatched quotes in argument: {arg}")
        else:
            text = arg
            log(f"Using unquoted text: '{text}'")
        kind = _classify_token_basic(text)
        log(f"Classified token as: {kind.value}")
        raw_tokens.append(Token(
            kind=kind,
            text=text,
            origin_index=i,
            span=(i, i + 1),
            quote_style=quote_style
        ))
        log(f"Added token: {kind.value}='{text}' at position {i}")
    log(f"Created {len(raw_tokens)} raw tokens, now classifying")
    result = _classify_tokens(raw_tokens)
    log(f"Tokenization complete: {len(result)} final tokens")
    trace_out()
    return result

def _detect_quote_style(arg: str) -> QuoteStyle:
    trace_in()
    if len(arg) < 2:
        log("Argument too short for quotes, returning NONE")
        trace_out()
        return QuoteStyle.NONE
    if arg.startswith('"') and arg.endswith('"'):
        log("Detected double quotes")
        trace_out()
        return QuoteStyle.DOUBLE
    elif arg.startswith("'") and arg.endswith("'"):
        log("Detected single quotes")
        trace_out()
        return QuoteStyle.SINGLE
    else:
        log("No matching quotes detected")
        trace_out()
        return QuoteStyle.NONE

def _classify_token_basic(text: str) -> TokenKind:
    trace_in()
    if not text:
        log("Empty text classified as VALUE")
        trace_out()
        return TokenKind.VALUE
    if text.startswith('-'):
        if text.startswith('--no-') or text.startswith('--no_'):
            log(f"Text '{text}' classified as NO_FLAG")
            trace_out()
            return TokenKind.NO_FLAG
        else:
            log(f"Text '{text}' classified as FLAG")
            trace_out()
            return TokenKind.FLAG
    log(f"Text '{text}' classified as COMMAND")
    trace_out()
    return TokenKind.COMMAND

def _classify_tokens(raw_tokens: List[Token]) -> List[Token]:
    trace_in()
    if not raw_tokens:
        log("No raw tokens to classify")
        trace_out()
        return raw_tokens
    log(f"Classifying {len(raw_tokens)} raw tokens")
    tokens = []
    expecting_value = False
    for i, token in enumerate(raw_tokens):
        log(f"Processing token {i}: {token.kind.value}='{token.text}'")
        if i == 0:
            if token.kind == TokenKind.FLAG or token.kind == TokenKind.NO_FLAG:
                new_token = Token(
                    kind=TokenKind.COMMAND,
                    text=token.text,
                    origin_index=token.origin_index,
                    span=token.span,
                    quote_style=token.quote_style
                )
                tokens.append(new_token)
                log(f"Converted first token to COMMAND: '{token.text}'")
            else:
                tokens.append(token)
                log(f"Kept first token as-is: {token.kind.value}")
            continue
        if _is_negative_number(token.text):
            new_token = Token(
                kind=TokenKind.FLAG,
                text=token.text,
                origin_index=token.origin_index,
                span=token.span,
                quote_style=token.quote_style
            )
            tokens.append(new_token)
            expecting_value = True
            log(f"Negative number detected, converted to FLAG: '{token.text}', now expecting value")
            continue
        if expecting_value:
            if token.kind == TokenKind.FLAG or token.kind == TokenKind.NO_FLAG:
                expecting_value = False
                log("Flag encountered while expecting value, stopping value expectation")
            else:
                new_token = Token(
                    kind=TokenKind.VALUE,
                    text=token.text,
                    origin_index=token.origin_index,
                    span=token.span,
                    quote_style=token.quote_style
                )
                tokens.append(new_token)
                expecting_value = False
                log(f"Value token added: '{token.text}', stopped expecting value")
                continue
        if token.kind == TokenKind.FLAG:
            tokens.append(token)
            expecting_value = True
            log(f"Flag token added: '{token.text}', now expecting value")
            continue
        if token.kind == TokenKind.NO_FLAG:
            tokens.append(token)
            expecting_value = False
            log(f"No-flag token added: '{token.text}', not expecting value")
            continue
        new_token = Token(
            kind=TokenKind.COMMAND,
            text=token.text,
            origin_index=token.origin_index,
            span=token.span,
            quote_style=token.quote_style
        )
        tokens.append(new_token)
        expecting_value = False
        log(f"Command token added: '{token.text}'")
    log(f"Token classification complete: {len(tokens)} final tokens")
    trace_out()
    return tokens

def _is_negative_number(text: str) -> bool:
    trace_in()
    if not text or not text.startswith('-'):
        log(f"Text '{text}' is not a negative number (empty or no leading dash)")
        trace_out()
        return False
    is_negative = re.match(r'^-\d+$', text) is not None
    log(f"Text '{text}' negative number check: {is_negative}")
    trace_out()
    return is_negative
