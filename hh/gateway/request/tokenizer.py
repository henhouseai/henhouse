from __future__ import annotations
import re
from typing import List, Sequence
from hh.gateway.request.token import Token, TokenKind, QuoteStyle, TokenizationError
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
            elif quote_style == QuoteStyle.BACKTICK and arg.startswith('`') and arg.endswith('`'):
                text = arg[1:-1]
                log(f"Extracted backtick-quoted text: '{text}'")
            else:
                error_msg = f"Unmatched quotes in argument: {arg}"
                warn(error_msg)
                report_error("request", error_msg)
                trace_out()
                raise TokenizationError(error_msg)
        else:
            text = arg
            debug(f"Using unquoted text: '{text}'")
        kind, processed_text = _classify_token_basic(text, quote_style)
        debug(f"Classified token as: {kind.value}")
        raw_tokens.append(Token(
            kind=kind,
            text=processed_text,
            origin_index=i,
            span=(i, i + 1),
            quote_style=quote_style
        ))
        debug(f"Added token: {kind.value}='{processed_text}' at position {i}")
    debug(f"Created {len(raw_tokens)} raw tokens")
    # No second pass needed - all classification happens in _classify_token_basic()
    debug(f"Tokenization complete: {len(raw_tokens)} final tokens")
    trace_out()
    return raw_tokens

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
    elif arg.startswith('`') and arg.endswith('`'):
        log("Detected backticks")
        trace_out()
        return QuoteStyle.BACKTICK
    else:
        log("No matching quotes detected")
        trace_out()
        return QuoteStyle.NONE

def _classify_token_basic(text: str, quote_style: QuoteStyle) -> tuple[TokenKind, str]:
    """
    Classify token by lexical form only (no context awareness).
    Returns (TokenKind, processed_text) where processed_text has prefixes stripped.
    
    Classification order:
    1. Quoted strings (already handled in tokenize, but check here for safety) → VALUE
    2. Strings with whitespace (quotes stripped by shell) → VALUE
    3. Numbers → NUMBER
    4. No-flags (--no- or --no_) → NO_FLAG (strip prefix)
    5. Regular flags (starts with -) → FLAG (strip dashes)
    6. Otherwise → COMMAND
    """
    trace_in()
    if not text:
        log("Empty text classified as VALUE")
        trace_out()
        return (TokenKind.VALUE, text)
    
    # If contains whitespace, it must be a string (quotes were stripped by shell)
    if ' ' in text or '\t' in text:
        debug(f"Text '{text}' contains whitespace, classified as VALUE (quotes stripped by shell)")
        trace_out()
        return (TokenKind.VALUE, text)
    
    # If quoted, it's already a string value (handled in tokenize, but double-check)
    if quote_style != QuoteStyle.NONE:
        debug(f"Quoted text '{text}' classified as VALUE")
        trace_out()
        return (TokenKind.VALUE, text)
    
    # Check for numbers first (before flags, since negative numbers start with -)
    if _is_number(text):
        debug(f"Text '{text}' classified as NUMBER")
        trace_out()
        return (TokenKind.NUMBER, text)
    
    # Check for no-flags (--no- or --no_)
    if text.startswith('--no-'):
        name = text[5:]  # Strip '--no-'
        debug(f"Text '{text}' classified as NO_FLAG, name='{name}'")
        trace_out()
        return (TokenKind.NO_FLAG, name)
    elif text.startswith('--no_'):
        name = text[5:]  # Strip '--no_'
        debug(f"Text '{text}' classified as NO_FLAG, name='{name}'")
        trace_out()
        return (TokenKind.NO_FLAG, name)
    
    # Check for regular flags (starts with -)
    if text.startswith('-'):
        # Strip all leading dashes
        name = text.lstrip('-')
        debug(f"Text '{text}' classified as FLAG, name='{name}'")
        trace_out()
        return (TokenKind.FLAG, name)
    
    # Otherwise it's a command
    debug(f"Text '{text}' classified as COMMAND")
    trace_out()
    return (TokenKind.COMMAND, text)


def _is_number(text: str) -> bool:
    """Check if text is a valid number (integer, decimal, or scientific notation, positive or negative)."""
    trace_in()
    if not text:
        log("Empty text is not a number")
        trace_out()
        return False
    # Pattern matches:
    # - Integers: 123, -456
    # - Decimals: 1.75, -0.5, .5, -.5
    # - Scientific: 1e5, -2.3e-4, 1E5, 1e+5
    # Optional sign, optional integer part, optional decimal point with digits, optional exponent
    pattern = r'^[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?$'
    is_number = re.match(pattern, text) is not None
    debug(f"Text '{text}' number check: {is_number}")
    trace_out()
    return is_number

def _is_negative_number(text: str) -> bool:
    """Legacy function - kept for backwards compatibility, but should use _is_number() instead."""
    trace_in()
    if not text or not text.startswith('-'):
        log(f"Text '{text}' is not a negative number (empty or no leading dash)")
        trace_out()
        return False
    is_negative = re.match(r'^-\d+$', text) is not None
    log(f"Text '{text}' negative number check: {is_negative}")
    trace_out()
    return is_negative
