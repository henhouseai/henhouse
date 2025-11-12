from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Union, Callable, Any
from hh.gateway.connection.types import DatabaseConnection
from hh.gateway.error.error_store import report_error, is_error
from hh.gateway.registry.debug import get_trace_in, get_trace_out, get_log, get_debug, get_warn, register_debug_init
from hh.tp.tp_decorator_registry import get_tp_decorator
from hh.page.page_registry import get_page, find_page
from hh.image.image_registry import get_image_conn
from hh.gateway.connection.connection import get_connection, r_query, c_query, d_query

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

class TextProcessor:

    def __init__(self, first_decorator: Optional[str] = None, final_decorator: Optional[str] = None) -> None:
        trace_in()
        self.first_decorator = first_decorator
        self.final_decorator = final_decorator  # Will default to 'mcp' in _apply_final_decorator if None
        self._text: str = ""
        self._len: int = 0
        self._pos: int = 0
        self._parse_errors: List[str] = []
        self._parsed_elements: List[Dict[str, Any]] = []
        log(f"TextProcessor initialized with first_decorator: {first_decorator} and final_decorator: {final_decorator}")
        trace_out()


    def process(self, content: str) -> Optional[str]:
        trace_in()
        if not content:
            log("Empty content provided, returning empty string")
            trace_out()
            return ""
        log(f"Processing content: {repr(content[:500])}{'...' if len(content) > 500 else ''}")
        self._text = content
        self._len = len(content)
        self._pos = 0
        # Reset error tracking and parsed elements
        self._parse_errors = []
        self._parsed_elements = []
        elements = self._parse_unparsed_text()
        log(f"Parsed {len(elements)} elements")
        # Store parsed elements for potential links table update
        self._parsed_elements = elements
        # Check for parse errors - report each one separately
        if self._parse_errors:
            for error_msg in self._parse_errors:
                warn(error_msg)
                report_error("link_resolution", error_msg)
            trace_out()
            return None
        result_parts: List[str] = []
        for i, element in enumerate(elements):
            log(f"Processing element {i}: {element.get('type', 'unknown')}")
            result_parts.append(self._process_element(element))
        result = "".join(result_parts)
        log(f"Final result: {repr(result[:500])}{'...' if len(result) > 500 else ''}")
        trace_out()
        return result

    # ============ Parsing (recursive-descent) ============

    def _parse_unparsed_text(self) -> List[Dict[str, Any]]:
        trace_in()
        elements: List[Dict[str, Any]] = []
        while not self._at_end():
            if self._peek_is("@"):
                log(f"Found decorator at position {self._pos}")
                elements.append(self._parse_decorated_element())
            elif self._peek_is("[["):
                log(f"Found link at position {self._pos}")
                base = self._parse_link_syntax()
                elements.append({"type": "link", **base, "decorators": []})
            elif self._peek_is("{{"):
                log(f"Found image at position {self._pos}")
                base = self._parse_image_syntax()
                elements.append({"type": "image", **base, "decorators": []})
            else:
                text_content = self._parse_text_until_control()
                if text_content:
                    log(f"Found text content: {repr(text_content[:20])}{'...' if len(text_content) > 20 else ''}")
                    elements.append({"type": "text", "content": text_content, "decorators": []})
        log(f"Parsed {len(elements)} elements from unparsed text")
        trace_out()
        return elements


    def _parse_decorated_element(self) -> Dict[str, Any]:
        trace_in()
        chain: List[Tuple[str, Dict[str, Any]]] = self._parse_decorator_chain()
        log(f"Parsed decorator chain: {[name for name, _ in chain]}")
        # Base element may follow; if not, treat as empty base string
        if self._peek_is("[["):
            log("Found link as base element")
            base = {"type": "link", **self._parse_link_syntax()}
        elif self._peek_is("{{"):
            log("Found image as base element")
            base = {"type": "image", **self._parse_image_syntax()}
        else:
            log("No base element found, using empty base")
            base = {"type": "empty", "content": ""}
        base["decorators"] = chain
        trace_out()
        return base


    def _parse_decorator_chain(self) -> List[Tuple[str, Dict[str, Any]]]:
        trace_in()
        chain: List[Tuple[str, Dict[str, Any]]] = []
        while self._peek_is("@"):
            name, args = self._parse_decorator_token()
            log(f"Parsed decorator: {name} with args: {args}")
            chain.append((name, args))
            # Look ahead for exactly one whitespace followed by decorator or base element
            if self._has_chaining_whitespace():
                log("Found chaining whitespace, consuming it")
                self._consume_whitespace()
            else:
                log("No chaining whitespace found, stopping decorator chain")
                break
        log(f"Parsed decorator chain with {len(chain)} decorators")
        trace_out()
        return chain


    def _parse_decorator_token(self) -> Tuple[str, Dict[str, Any]]:
        trace_in()
        # '@' already ensured
        self._expect("@")
        name = self._parse_decorator_name()
        log(f"Parsed decorator name: '{name}'")
        args: Dict = {}
        if self._peek_is("("):
            log(f"Found arguments for decorator '{name}'")
            args = self._parse_decorator_args()
            log(f"Parsed arguments: {args}")
        else:
            log(f"No arguments for decorator '{name}'")
        trace_out()
        return name, args


    def _parse_decorator_name(self) -> str:
        trace_in()
        if self._at_end():
            log("At end of text, returning empty decorator name")
            trace_out()
            return ""
        start = self._pos
        ch = self._peek()
        if not ch.isalpha():
            log(f"First character '{ch}' is not alphabetic, returning empty name")
            trace_out()
            return ""
        self._pos += 1
        while not self._at_end():
            ch = self._peek()
            if ch.isalnum() or ch in "-_":
                self._pos += 1
            else:
                break
        name = self._text[start:self._pos]
        log(f"Parsed decorator name: '{name}' (length: {len(name)})")
        trace_out()
        return name


    def _parse_decorator_args(self) -> Dict[str, Any]:
        trace_in()
        args: Dict[str, Any] = {}
        self._expect("(")
        log("Starting argument parsing")
        part_index = 0
        current = []
        in_string = False
        string_char: Optional[str] = None
        while not self._at_end():
            ch = self._peek()
            log(f"Processing character '{ch}' (in_string={in_string}, part_index={part_index})")
            if in_string:
                current.append(ch)
                self._pos += 1
                if ch == string_char:
                    in_string = False
                    string_char = None
                    log(f"End of string, current buffer: '{''.join(current)}'")
                continue
            if ch in ("'", '"'):
                in_string = True
                string_char = ch
                current.append(ch)
                self._pos += 1
                log(f"Start of string with '{ch}', current buffer: '{''.join(current)}'")
                continue
            if ch == ',':
                token = "".join(current).strip()
                if token:
                    coerced = self._coerce_arg(token)
                    args[f"arg{part_index}"] = coerced
                    log(f"Added argument {part_index}: '{token}' -> {coerced} (type: {type(coerced).__name__})")
                    part_index += 1
                else:
                    log("Empty token, skipping")
                current = []
                self._pos += 1
                continue
            if ch == ')':
                token = "".join(current).strip()
                if token:
                    coerced = self._coerce_arg(token)
                    args[f"arg{part_index}"] = coerced
                    log(f"Final argument {part_index}: '{token}' -> {coerced} (type: {type(coerced).__name__})")
                else:
                    log("No final argument")
                self._pos += 1
                break
            current.append(ch)
            self._pos += 1
        log(f"Finished parsing arguments: {args}")
        trace_out()
        return args


    def _coerce_arg(self, token: str) -> Union[str, int, float]:
        trace_in()
        original_token = token
        token = token.strip()
        log(f"Coercing argument: '{original_token}' -> '{token}'")
        if (len(token) >= 2) and ((token[0] == token[-1]) and token[0] in ("'", '"')):
            result = token[1:-1]
            log(f"String literal: '{token}' -> '{result}'")
            trace_out()
            return result
        if token.isdigit():
            result = int(token)
            log(f"Integer: '{token}' -> {result}")
            trace_out()
            return result
        try:
            if token.replace('.', '', 1).isdigit() and token.count('.') <= 1:
                result = float(token)
                log(f"Float: '{token}' -> {result}")
                trace_out()
                return result
        except Exception as e:
            log(f"Float conversion failed for '{token}': {e}")
        log(f"String (no coercion): '{token}'")
        trace_out()
        return token


    def _parse_link_syntax(self) -> Dict[str, Any]:
        trace_in()
        self._expect("[[")
        identifier, display = self._parse_link_contents()
        self._expect("]]")
        # Log what link was found
        if identifier["type"] == "page_id":
            log(f"Found page ID link: {identifier['value']}")
        else:
            log(f"Found page link: '{identifier['value']}'")
        if display:
            if isinstance(display, dict):
                log(f"Link has nested image display")
            else:
                log(f"Link has text display: '{display}'")
        else:
            log(f"Link has no custom display text")
        trace_out()
        return {"identifier": identifier, "display": display}


    def _parse_link_contents(self) -> Tuple[Dict[str, Any], Optional[Union[str, Dict[str, Any]]]]:
        trace_in()
        identifier = self._parse_link_identifier()
        log(f"Parsed link identifier: {identifier}")
        display: Optional[Union[str, Dict[str, Any]]] = None
        if self._peek_is("]["):
            log("Found display separator ']['")
            self._expect("][")
            if self._peek_is("{{"):
                log("Found nested image in link display")
                image = self._parse_image_syntax(parent_link_identifier=identifier)
                result = {"type": "image", **image}
                log(f"Created nested image display: {result}")
                trace_out()
                return identifier, result
            else:
                display = self._parse_text_until_control()
                log(f"Parsed text display: '{display}'")
        else:
            log("No display text found")
        trace_out()
        return identifier, display


    def _parse_link_identifier(self) -> Dict[str, Any]:
        trace_in()
        num = self._parse_number_token()
        if num is not None:
            log(f"Found page ID: {num}")
            result = {"type": "page_id", "value": num}
            trace_out()
            return result
        text = self._parse_text_until_control()
        log(f"Found page link text: '{text}'")
        result = {"type": "page_link", "value": text}
        trace_out()
        return result


    def _parse_image_syntax(self, parent_link_identifier: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        log(f"Parsing image syntax at position {self._pos}, text: {repr(self._text[self._pos:self._pos+10])}")
        if self._peek_is("{{{"):
            log("Found {{{ - entering explicit image ID mode")
            # Explicit image ID mode: {{{id}}} or {{{id}{caption}}}
            self._expect("{{{")
            identifier, caption = self._parse_explicit_image_contents()
            # Expect closing }} (one } was already consumed in _parse_explicit_image_contents)
            self._expect("}}")
        else:
            log("Found {{ - entering page name/image mode")
            # Page name/image mode: {{name}} or {{name}{caption}}
            self._expect("{{")
            identifier, caption = self._parse_image_contents(parent_link_identifier)
            self._expect("}}")
        log(f"Image syntax parsed: {identifier}, caption: {caption}")
        return {"identifier": identifier, "caption": caption}


    def _parse_explicit_image_contents(self) -> Tuple[Dict[str, Any], Optional[str]]:
        # Parse image ID
        num = self._parse_number_token()
        if num is None:
            self._parse_errors.append("Expected image ID after {{{")
            return {"type": "image_id", "value": 0}, None
        identifier = {"type": "image_id", "value": num}
        log(f"Parsed explicit image ID: {num}, now at position {self._pos}, text: {repr(self._text[self._pos:self._pos+10])}")
        caption: Optional[str] = None
        # Expect } to close the ID portion: {{{id} ...
        self._expect("}")
        log(f"Consumed closing }} for ID, now at position {self._pos}, text: {repr(self._text[self._pos:self._pos+10])}")
        # Check for caption bridge: }{ or just close: }}
        if self._peek_is("}{"):
            log("Found }}{{ bridge separator for caption")
            self._expect("}{")
            caption = self._parse_text_until_control()
            log(f"Parsed caption: {repr(caption)}")
        else:
            log("No caption found, expecting closing }}}}")
        return identifier, caption


    def _parse_image_contents(self, parent_link_identifier: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], Optional[str]]:
        log(f"Parsing image contents at position {self._pos}, text: {repr(self._text[self._pos:self._pos+10])}")
        identifier = self._parse_image_identifier(parent_link_identifier)
        log(f"Image contents got identifier: {identifier}")
        caption: Optional[str] = None
        if self._peek_is("}{"):
            log("Found }{ - parsing caption")
            self._expect("}{")
            caption = self._parse_text_until_control()
            log(f"Parsed caption: {repr(caption)}")
        else:
            log("No }{ found - no caption")
        log(f"Image contents returning: {identifier}, caption: {caption}")
        return identifier, caption


    def _parse_image_identifier(self, parent_link_identifier: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        log(f"Parsing image identifier at position {self._pos}, text: {repr(self._text[self._pos:self._pos+10])}")
        if self._peek_is("{{"):
            log("Found {{ in _parse_image_identifier - parsing nested image")
            self._expect("{{")
            num = self._parse_number_token()
            self._expect("}}")
            result = {"type": "image_id", "value": num}
            log(f"Image identifier returning nested image: {result}")
            return result
        else:
            log("No {{ found - calling _parse_link_identifier")
            result = self._parse_link_identifier()
            # Handle {{}} shorthand - if empty and we have parent context, use parent page name
            if (result["type"] == "page_link" and 
                result["value"] == "" and 
                parent_link_identifier and 
                parent_link_identifier["type"] == "page_link"):
                log(f"Found empty {{}} shorthand, using parent page name: {parent_link_identifier['value']}")
                result["value"] = parent_link_identifier["value"]
            log(f"Image identifier returning link identifier: {result}")
            return result

    # ============ Generation ============

    def _process_element(self, element: Dict[str, Any]) -> str:
        # Generate base JSON from element
        base_json = self._generate_element_json(element)
        # Apply global first decorator
        if self.first_decorator:
            base_json = self._apply_decorator(self.first_decorator, base_json, {})
        # Apply decorators in reverse order (right-to-left chaining)
        decorators = element.get("decorators", [])
        for i, (name, args) in enumerate(reversed(decorators)):
            base_json = self._apply_decorator(name, base_json, args)
            args_str = f"({','.join(str(v) for v in args.values())})" if args else ""
            log(f"[{i+1}/{len(decorators)}] @{name}{args_str}: {type(base_json).__name__}")
        if decorators:
            base_type = element.get("type", "unknown")
            if base_type == "empty":
                log(f"Chain complete: {len(decorators)} decorators applied to empty input")
            else:
                log(f"Chain complete: {len(decorators)} decorators applied to {base_type} base element")
        # Apply global final decorator (may be None)
        result = self._apply_final_decorator(self.final_decorator, base_json)
        log(f"Element processing complete: {element.get('type', 'unknown')} -> {type(result).__name__}")
        return result


    def _generate_element_json(self, element: Dict[str, Any]) -> Dict[str, Any]:
        etype = element["type"]
        if etype == "text":
            return {"type": "text", "content": element.get("content", "")}
        elif etype == "link":
            return self._generate_link_json(element)
        elif etype == "image":
            return self._generate_image_json(element)
        elif etype == "empty":
            return {"type": "empty", "content": ""}
        else:
            return {"type": "unknown", "content": ""}


    def _generate_link_json(self, element: Dict[str, Any]) -> Dict[str, Any]:
        trace_in()
        identifier = element["identifier"]
        display = element["display"]
        # Resolve page information
        resolved_page = self._resolve_page_info(identifier)
        log(f"Resolving page identifier {identifier['type']}: '{identifier['value']}' -> page_id={resolved_page['id']}, name='{resolved_page['name']}'")
        log(f"Display value: {display}")
        # Handle name override
        name_override = None
        if isinstance(display, str) and display:
            name_override = display
        # Build JSON structure
        result = {
            "type": "page_link",
            "resolved_page": {
                "id": resolved_page["id"],
                "parent": resolved_page.get("parent", 1),
                "name": resolved_page["name"]
            }
        }
        if name_override:
            result["resolved_page"]["name_override"] = name_override
        # Handle nested image display
        if isinstance(display, dict) and display.get("type") == "image":
            image_json = self._generate_image_json(display)
            if image_json is not None:
                result["type"] = "image_link"
                result["resolved_page"]["resolved_image"] = image_json
        log(f"Generated {result['type']} JSON: page_id={result['resolved_page']['id']}, name='{result['resolved_page']['name']}'")
        trace_out()
        return result


    def _resolve_page_info(self, identifier: Dict[str, Any]) -> Dict[str, Any]:
        if identifier["type"] == "page_id":
            page_id = identifier["value"]
            try:
                page = get_page(page_id=page_id)
                if page:
                    return {
                        "id": page.id,
                        "parent": getattr(page, 'parent', 1),
                        "name": page.name
                    }
                else:
                    self._parse_errors.append(f"Page ID {page_id} not found")
                    return {"id": page_id, "parent": 1, "name": f"Page {page_id} (not found)"}
            except Exception as e:
                self._parse_errors.append(f"Error looking up page ID {page_id}: {e}")
                return {"id": page_id, "parent": 1, "name": f"Page {page_id} (error)"}
        else:
            page_name = identifier["value"]
            try:
                page = find_page(link=page_name)
                if page and hasattr(page, 'id'):
                    return {
                        "id": page.id,
                        "parent": getattr(page, 'parent', 1),
                        "name": page.name
                    }
                else:
                    self._parse_errors.append(f"Page name '{page_name}' not found")
                    return {"id": 0, "parent": 1, "name": page_name}
            except Exception as e:
                self._parse_errors.append(f"Error looking up page name '{page_name}': {e}")
                return {"id": 0, "parent": 1, "name": page_name}


    def _generate_image_json(self, element: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        trace_in()
        identifier = element["identifier"]
        caption = element.get("caption")
        # Resolve image information using actual Image class
        resolved_image = self._resolve_image_info(identifier)
        # If no image found, return None instead of fake data
        if resolved_image is None:
            log(f"Resolving image {identifier['type']}: '{identifier['value']}' -> no image found")
            trace_out()
            return None
        log(f"Resolving image {identifier['type']}: '{identifier['value']}' -> image_id={resolved_image['id']}, instances={len(resolved_image['instances'])}")
        log(f"Caption: {caption}")
        # Build JSON structure
        result = {
            "type": "image",
            "resolved_image": {
                "id": resolved_image["id"],
                "filename": resolved_image["filename"],
                "path": resolved_image["path"],
                "caption": resolved_image["caption"],
                "instances": resolved_image["instances"]
            }
        }
        if caption:
            result["resolved_image"]["caption_override"] = caption
        
        log(f"Generated {result['type']} JSON: image_id={result['resolved_image']['id']}, instances={len(result['resolved_image']['instances'])}")
        trace_out()
        return result


    def _resolve_image_info(self, identifier: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        trace_in()
        log(f"Resolving image info for {identifier['type']}: '{identifier['value']}'")
        if identifier["type"] == "image_id":
            # Direct image ID lookup using Image class
            image_id = identifier["value"]
            try:
                conn = get_connection()
                image = get_image_conn(conn, image_id)
                if image:
                    log(f"Found image ID {image_id} directly")
                    # Load instances on-demand
                    instances = image.get_instances()
                    log(f"Loaded {len(instances)} instances for image {image_id}")
                    result = {
                        "id": image.id,
                        "filename": self._extract_filename_from_instances(instances),
                        "path": "/images/",
                        "caption": image.caption or "",
                        "instances": instances
                    }
                    trace_out()
                    return result
                else:
                    log(f"No image found for ID {image_id}")
                    trace_out()
                    return None
            except Exception as e:
                log(f"Error looking up image ID {image_id}: {e}")
                self._parse_errors.append(f"Error looking up image ID {image_id}: {e}")
                trace_out()
                return None
        elif identifier["type"] == "page_id":
            # Primary image of page by ID - find image with imageRank=1 in image_groups
            page_id = identifier["value"]
            try:
                conn = get_connection()
                # Find primary image (image_rank=1) for this page using image_groups
                query = """
                    SELECT i.id FROM images i 
                    JOIN image_groups ig ON i.id = ig.image_id 
                    WHERE ig.page_id = %s AND ig.image_rank = 1
                """
                log(f"Querying for primary image on page {page_id}")
                results = r_query(conn, query, [page_id])
                if results:
                    primary_image_id = results[0]['id']
                    log(f"Found primary image ID {primary_image_id} for page {page_id}")
                    result = self._resolve_image_info({"type": "image_id", "value": primary_image_id})
                    trace_out()
                    return result
                else:
                    log(f"No primary image found for page {page_id}")
                    trace_out()
                    return None
            except Exception as e:
                log(f"Error looking up primary image for page {page_id}: {e}")
                self._parse_errors.append(f"Error looking up primary image for page {page_id}: {e}")
                trace_out()
                return None
        else:
            # Primary image of page by name
            page_name = identifier["value"]
            try:
                log(f"Looking up page by name '{page_name}'")
                page = find_page(link=page_name)
                if page and hasattr(page, 'id'):
                    log(f"Found page '{page_name}' with ID {page.id}")
                    result = self._resolve_image_info({"type": "page_id", "value": page.id})
                    trace_out()
                    return result
                else:
                    log(f"No page found with name '{page_name}'")
                    trace_out()
                    return None
            except Exception as e:
                log(f"Error looking up primary image for page '{page_name}': {e}")
                self._parse_errors.append(f"Error looking up primary image for page '{page_name}': {e}")
                trace_out()
                return None


    def _extract_filename_from_instances(self, instances: List[Dict[str, Any]]) -> str:
        if not instances:
            return "unknown.jpg"
        # Use the largest instance as the base filename
        largest = max(instances, key=lambda x: x['width'])
        src = largest['src']
        # Extract just the filename from the path
        if '/' in src:
            return src.split('/')[-1]
        return src

    # ============ Decorators ============

    def _apply_decorator(self, name: str, json_data: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
        trace_in()
        log(f"Applying decorator '{name}' to JSON data")
        func = get_tp_decorator(name)
        if not func:
            warn(f"Decorator '{name}' not found")
            trace_out()
            return json_data
        try:
            result = func(json_data, **args)
            log(f"Decorator '{name}' result: {type(result).__name__}")
            trace_out()
            return result
        except Exception as e:
            warn(f"Error applying decorator '{name}': {e}")
            report_error("textprocessor", f"Error applying decorator '{name}': {e}")
            trace_out()
            return json_data


    def _apply_final_decorator(self, name: Optional[str], json_data: Dict[str, Any]) -> str:
        trace_in()
        # Use 'mcp' as default if no final decorator specified
        if not name:
            name = 'mcp'
            log("No final decorator specified, using default @mcp decorator")
        else:
            log(f"Applying final decorator '{name}' to JSON data")
        func = get_tp_decorator(name)
        if not func:
            warn(f"Final decorator '{name}' not found")
            trace_out()
            return json_data
        try:
            result = func(json_data)
            log(f"Final decorator '{name}' result: {repr(result[:500])}{'...' if len(result) > 500 else ''}")
            trace_out()
            return result
        except Exception as e:
            warn(f"Error applying final decorator '{name}': {e}")
            report_error("textprocessor", f"Error applying final decorator '{name}': {e}")
            trace_out()
            return json_data


    def _extract_display_text(self, json_data: Dict[str, Any]) -> str:
        if json_data.get("type") == "text":
            result = json_data.get("content", "")
        elif json_data.get("type") == "page_link":
            page = json_data.get("resolved_page", {})
            result = page.get("name_override") or page.get("name", "Unknown Page")
        elif json_data.get("type") == "image":
            image = json_data.get("resolved_image", {})
            result = image.get("caption_override") or image.get("caption", "Image")
        elif json_data.get("type") == "custom":
            result = json_data.get("value", "")
        else:
            result = str(json_data)
        log(f"Extracted display text: {json_data.get('type', 'unknown')} -> '{result}'")
        return result

    # ============ Links Table Management ============

    def update_links_table(self, conn: DatabaseConnection, page_id: int) -> bool:
        trace_in()
        log(f"Updating links table for page {page_id}")
        log(f"TextProcessor.update_links_table called for page {page_id}")
        log(f"Parsed elements count: {len(self._parsed_elements)}")
        if not self._parsed_elements:
            log("No parsed elements available for links table update")
            log("No parsed elements - returning True")
            trace_out()
            return True
        try:
            # Delete existing links for this page
            deleted_links = d_query(conn, "DELETE FROM links WHERE id = %s", (page_id,))
            log(f"Deleted {deleted_links} existing links for page {page_id}")
            deleted_image_links = d_query(conn, "DELETE FROM image_links WHERE id = %s", (page_id,))
            log(f"Deleted {deleted_image_links} existing image links for page {page_id}")
            # Process each parsed element to extract link information
            log(f"Processing {len(self._parsed_elements)} parsed elements")
            for i, element in enumerate(self._parsed_elements):
                log(f"Element {i}: type={element.get('type')}, identifier={element.get('identifier')}")
                if element.get('type') == 'link':
                    log(f"Processing link element {i}")
                    self._update_links_table_from_link(conn, element, page_id)
                elif element.get('type') == 'image':
                    log(f"Processing image element {i}")
                    self._update_links_table_from_image(conn, element, page_id)
                else:
                    log(f"Skipping element {i} of type {element.get('type')}")
            log(f"Successfully updated links table for page {page_id}")
            trace_out()
            return True
        except Exception as e:
            error_msg = f"Error updating links table for page {page_id}: {e}"
            warn(error_msg)
            report_error("link_resolution", error_msg)
            trace_out()
            return False


    def _update_links_table_from_link(self, conn: DatabaseConnection, element: Dict[str, Any], page_id: int) -> None:
        trace_in()
        identifier = element.get('identifier', {})
        identifier_type = identifier.get('type')
        identifier_value = identifier.get('value')
        log(f"Updating links table from link - type: {identifier_type}, value: {identifier_value}")
        if identifier_type == 'page_id':
            # Direct page ID link: [[123456]]
            target_page_id = identifier_value
            link_text = str(target_page_id)
            log(f"Adding page ID link: {link_text} -> {target_page_id}")
        elif identifier_type == 'page_link':
            # Page name link: [[Home]]
            page_name = identifier_value
            try:
                target_page = find_page(link=page_name)
                if target_page and hasattr(target_page, 'id'):
                    target_page_id = target_page.id
                    link_text = page_name
                    log(f"Adding page name link: {link_text} -> {target_page_id}")
                else:
                    log(f"Could not resolve page name '{page_name}' to page ID, skipping")
                    trace_out()
                    return
            except Exception as e:
                log(f"Error resolving page name '{page_name}': {e}, skipping")
                trace_out()
                return
        else:
            log(f"Unknown link identifier type: {identifier_type}, skipping")
            trace_out()
            return
        # Insert into links table
        try:
            insert_query = "INSERT INTO links (id, link, resolution_id) VALUES (%s, %s, %s)"
            log(f"Inserting into links table: page_id={page_id}, link_text='{link_text}', target_page_id={target_page_id}")
            link_id = c_query(conn, insert_query, (page_id, link_text, target_page_id))
            if link_id is None:
                warn(f"Failed to insert link: page {page_id} -> {link_text} -> {target_page_id}")
                trace_out()
                return False
            log(f"Inserted link: page {page_id} -> {link_text} -> {target_page_id}")
            log(f"Successfully inserted link into database")
        except Exception as e:
            log(f"Error inserting link: {e}")
        
        # Check for nested image display with explicit ID
        display = element.get('display')
        if isinstance(display, dict) and display.get('type') == 'image':
            nested_identifier = display.get('identifier', {})
            if nested_identifier.get('type') == 'image_id':
                # Direct image ID in nested context -> image_links table
                target_image_id = nested_identifier['value']
                log(f"Found nested explicit image ID {target_image_id} in link display")
                try:
                    insert_query = "INSERT INTO image_links (id, resolution_id) VALUES (%s, %s)"
                    image_link_id = c_query(conn, insert_query, (page_id, target_image_id))
                    if image_link_id is None:
                        warn(f"Failed to insert nested image reference: page {page_id} -> image {target_image_id}")
                    else:
                        log(f"Inserted nested image reference: page {page_id} -> image {target_image_id}")
                except Exception as e:
                    log(f"Error inserting nested image reference: {e}")
        
        trace_out()


    def _update_links_table_from_image(self, conn: DatabaseConnection, element: Dict[str, Any], page_id: int) -> None:
        trace_in()
        identifier = element.get('identifier', {})
        identifier_type = identifier.get('type')
        identifier_value = identifier.get('value')
        log(f"Updating links table from image - type: {identifier_type}, value: {identifier_value}")
        if identifier_type == 'page_id':
            # Page ID reference for image: {{123456}} -> links table
            target_page_id = identifier_value
            link_text = str(target_page_id)
            log(f"Adding page ID image reference: {link_text} -> {target_page_id}")
            # Insert into links table (page reference for image display)
            try:
                insert_query = "INSERT INTO links (id, link, resolution_id) VALUES (%s, %s, %s)"
                link_id = c_query(conn, insert_query, (page_id, link_text, target_page_id))
                if link_id is None:
                    warn(f"Failed to insert page image reference: page {page_id} -> {link_text} -> {target_page_id}")
                else:
                    log(f"Inserted page image reference: page {page_id} -> {link_text} -> {target_page_id}")
            except Exception as e:
                log(f"Error inserting page image reference: {e}")
        elif identifier_type == 'page_link':
            # Page name reference for image: {{Home}} -> links table
            page_name = identifier_value
            try:
                target_page = find_page(link=page_name)
                if target_page and hasattr(target_page, 'id'):
                    target_page_id = target_page.id
                    link_text = page_name
                    log(f"Adding page name image reference: {link_text} -> {target_page_id}")
                    # Insert into links table (page reference for image display)
                    try:
                        insert_query = "INSERT INTO links (id, link, resolution_id) VALUES (%s, %s, %s)"
                        link_id = c_query(conn, insert_query, (page_id, link_text, target_page_id))
                        if link_id is None:
                            warn(f"Failed to insert page image reference: page {page_id} -> {link_text} -> {target_page_id}")
                        else:
                            log(f"Inserted page image reference: page {page_id} -> {link_text} -> {target_page_id}")
                    except Exception as e:
                        log(f"Error inserting page image reference: {e}")
                else:
                    log(f"Could not resolve page name '{page_name}' to page ID, skipping")
                    trace_out()
                    return
            except Exception as e:
                log(f"Error resolving page name '{page_name}': {e}, skipping")
                trace_out()
                return
        elif identifier_type == 'image_id':
            # Direct image ID reference: {{{123456}}} -> image_links table
            target_image_id = identifier_value
            log(f"Adding direct image ID reference: page {page_id} -> image {target_image_id}")
            # Insert into image_links table (direct image reference)
            try:
                insert_query = "INSERT INTO image_links (id, resolution_id) VALUES (%s, %s)"
                log(f"Inserting into image_links table: page_id={page_id}, target_image_id={target_image_id}")
                image_link_id = c_query(conn, insert_query, (page_id, target_image_id))
                if image_link_id is None:
                    warn(f"Failed to insert direct image reference: page {page_id} -> image {target_image_id}")
                    trace_out()
                    return False
                log(f"Inserted direct image reference: page {page_id} -> image {target_image_id}")
                log(f"Successfully inserted image reference into database")
            except Exception as e:
                log(f"Error inserting direct image reference: {e}")
        else:
            log(f"Unknown image identifier type: {identifier_type}, skipping")
        trace_out()

    # ============ Low-level helpers ============

    def _peek(self) -> str:
        return self._text[self._pos]


    def _peek_is(self, s: str) -> bool:
        return self._text.startswith(s, self._pos)


    def _expect(self, s: str) -> None:
        if not self._peek_is(s):
            raise ValueError(f"Expected '{s}' at position {self._pos}")
        self._pos += len(s)


    def _consume_whitespace(self) -> None:
        while not self._at_end() and self._peek().isspace():
            self._pos += 1


    def _has_chaining_whitespace(self) -> bool:
        if self._at_end():
            return False
        # Check if current position is whitespace
        if not self._peek().isspace():
            return False
        # Look ahead to see if there's exactly one whitespace followed by @, [[, or {{
        temp_pos = self._pos
        whitespace_count = 0
        # Count consecutive whitespace characters
        while temp_pos < self._len and self._text[temp_pos].isspace():
            whitespace_count += 1
            temp_pos += 1
        # Must have exactly one whitespace character
        if whitespace_count != 1:
            return False
        # Check if the next character is a decorator or base element
        if temp_pos >= self._len:
            return False
        next_char = self._text[temp_pos]
        return next_char == '@' or (temp_pos + 1 < self._len and 
                                  (self._text[temp_pos:temp_pos+2] == '[[' or 
                                   self._text[temp_pos:temp_pos+2] == '{{'))


    def _parse_text_until_control(self) -> str:
        start = self._pos
        while not self._at_end():
            if self._peek_is("@") or self._peek_is("[[") or self._peek_is("{{"):
                break
            if self._peek_is("]]") or self._peek_is("]["):
                break
            if self._peek_is("}}") or self._peek_is("}{"):
                break
            if self._peek_is("::"):
                break
            self._pos += 1
        result = self._text[start:self._pos]
        log(f"Parsed text until control: {repr(result)}")
        return result


    def _parse_number_token(self) -> Optional[int]:
        start = self._pos
        while not self._at_end() and self._peek().isdigit():
            self._pos += 1
        if self._pos > start:
            return int(self._text[start:self._pos])
        return None


    def _at_end(self) -> bool:
        return self._pos >= self._len

