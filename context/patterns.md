# Henhouse System Patterns

This document describes the architectural patterns used throughout the Henhouse system, from simple action-list operations to complex multi-command subscription systems.

## Basic Patterns

- The basic patterns are demonstrated by simple action-parser pairs that show the core architectural components.
- **Action Functions** Action functions do something, often CRUD related to the db, and store their result as JSON thru the gateway response setters
- **Backend Functions** Backend functions transform action responses into formatted output for different interfaces. Parser backends produce CLI table output, HTTP backends produce HTML output. Other backend examples include mcp.

### Example 1: 

**basic_example.py**

```python
from hh.gateway.error.error_store import report_error, is_error

@register_action('basic_example')
@register_command('basic_example')
def basic_example() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    data = {
        "hen": "house",
        "fox": "house",
        "dog": "house"
    }
    result = process(data)
    if check_for_new_problems(result):
        warn("Something went wrong.")
        report_error("action", f"We have a new problem: {reason}")
        trace_out()
        return False
    gateway.set_action_response(success_payload(result))
    log("All done.")
    trace_out()
    return True
```

**render_basic_example.py**

```python
@register_http('basic_example')
@register_parser('basic_example')
def basic_example() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False    
    if not gateway.has_action_response():
        warn("No action response available")
        gateway.backend_error("No action response available")
        trace_out()
        return False    
    json_data = gateway.get_action_response()
    source_data = get_data(json_data)    
    result = process(data)
    if check_for_new_problems(result):
        warn("Something went wrong.")
        gateway.backend_error(f"We have a new problem: {reason}")
        trace_out()
        return False
    gateway.add_backend_response(result)
    log(f"Parser execution completed successfully with {len(result)} characters")
    trace_out()
    return True
```

### Example 2: 

**list_example.py**

```python
from hh.gateway.error.error_store import report_error, is_error

@register_action('list_example')
@register_command('list_example')
def list_example() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    try:
        items = get_available_items()
        log(f"Listing {len(items)} available items")
        data = {
            "type": "example",
            "count": len(items),
            "items": []
        }
        for item in sorted(items):
            item_info = get_item_info(item)
            data["items"].append({
                "name": item,
                "status": item_info.get('status', 'unknown')
            })
        log(f"Successfully created item list with {len(data['items'])} items")
        gateway.set_action_response(success_payload(data))
        trace_out()
        return True
    except Exception as e:
        warn("List action failed.")
        report_error("backend", f"Failed to list items: {str(e)}")
        trace_out()
        return False
```

**render_list_example.py**

```python
@register_http('list_example')
@register_parser('list_example')
def list_example() -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.has_action_response():
        warn("No action response available")
        gateway.backend_error("No action response available")
        trace_out()
        return False
    json_data = gateway.get_action_response()
    try:
        lines = []
        lines.append(render_header_block('l_list_example_header'))
        source_data = get_data(json_data)
        if not render_items_section(source_data, lines):
            warn("Failed to render items section")
            gateway.backend_error("Failed to render items section")
            trace_out()
            return False
        break_section(lines)
        result = finalize_output(lines)
        if len(result) == 0:
            warn("Backend response is empty")
        gateway.add_backend_response(result)
        log(f"Parser execution completed successfully with {len(result)} lines.")
        trace_out()
        return True
    except Exception as e:
        warn("Parser execution raised an exception.")
        gateway.backend_error(f"Parser execution raised an exception: {e}")
        trace_out()
        return False
```

## Key Pattern Elements

1. **Decorators**: `@register_action` and `@register_command` for actions; `@register_parser` and `@register_http` for backend handlers (typically both decorators on the same function)
2. **Tracing**: Always use `trace_in()` and `trace_out()` for debugging
3. **Gateway Checks**: Always verify gateway availability
4. **Error Handling**: Consistent try/catch with proper error responses
5. **Return Values**: Always return `bool` (True for success, False for failure)
6. **Response Handling**: Actions use `gateway.set_action_response()`; parsers use `gateway.add_backend_response()`

## Error Handling System

The system uses a **three-layer error handling approach** that ensures all errors are properly reported and bubbled up:

1. **Gateway Error Reporting** (Primary): All errors MUST be reported through the gateway if possible
2. **Warning System Logging** (Secondary): All errors MUST be logged through the warning system  
3. **Boolean Bubbling** (Tertiary): All errors MUST return `False` to bubble up the call stack

### Example 3: **Example Error Pattern for Actions:**

```python
from hh.gateway.error.error_store import report_error, is_error

def some_action():
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if error_condition:
        warn("Error description")
        report_error("action", "Error description")
        trace_out()
        return False
    trace_out()
    return True
```

### Example 4: **Example Error Pattern for Parsers:**
```python
def some_parser():
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not gateway.has_action_response():
        warn("No action response available for parsing")
        gateway.backend_error("No action response available")
        trace_out()
        return False
    if business_logic_fails:
        warn("Business logic validation failed")
        gateway.backend_error("Business logic validation failed")
        trace_out()
        return False
    log("All steps done.")
    trace_out()
    return True
```

### Example 5: **Example Error Pattern for Complex Chaining Logic:**

```python
from hh.gateway.error.error_store import report_error, is_error

def some_function():
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available.")
        trace_out()
        return False
	if not step1_done():
		warn("step 1 not done.")
        report_error("action", "step 1 not done.")
    if not is_error()
    	do_step2()
	if not step2_done():
		warn("step 2 not done.")
		report_error("action", "step 2 not done.")
    if not is_error()
    	do_step3()
	if not step3_done():
		warn("step 3 not done.")
		report_error("action", "step 3 not done.")
    if not is_error()
    	do_step4()
	if not step2_done():
		warn("step 4 not done.")
		report_error("action", "step 4 not done.")
    result = is_error()
	if result:
	    log("All steps done.")
	else
	    log("problems encountered.")
	do_some_cleanup()
    trace_out()
    return result
```

### Example 6: **Example Error Pattern with Try/Except Blocks:**

```python
from hh.gateway.error.error_store import report_error, is_error

def some_function():
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available")
        trace_out()
        return False
    if not step1_done():
        warn("step 1 not done")
        report_error("action", f"step 1 failed because {reason}")
        trace_out()
		return False
	try:
		result = do_step2()
		if not result:
			warn("step 2 failed")
            report_error("action", f"step 2 failed because {reason}")
		else
			log("All steps done.")
		trace_out()
		return result
	except Exception as e:
		warn("step 2 raised exception")
        report_error("backend", f"step 2 raised exception: {str(e)}")
        trace_out()
		return False    
```

## Common Error and Debug System Practices:

- Use gateway error system instead of raising custom exceptions
- Establish gateway at the top of functions for consistent access
- Always check both gateway and connection: `if not gateway or not gateway.conn:`
- Use warn() for simple messages to the user.
- Use report_error("action", message) for business logic errors inside methods decorated with @register_action or @register_command
- Use gateway.backend_error() for business logic errors inside methods decorated with @register_parser or @register_http
- Use if not is_error(): to protect any blocks of code from running if any previous error state has been logged
- Use trace_out() before returning False for proper cleanup
- The report_error() system is what triggers the code protection feature and should only be used when legitimate errors occur
- The global warn() system is what puts user friendly messages into the top of output stream.
- The boolean bubble-up system is what generates a list of errors at every level back up to the gateway, not just a single error message.
- Database operations use `gateway.conn.read()`, `gateway.conn.create()`, `gateway.conn.update()`, `gateway.conn.delete()`

## Medium Complexity Patterns

Medium complexity patterns extend the basic patterns by adding database operations, complex data processing, and enhanced error handling.

### Database Connection System

The system uses a gateway-managed connection system. All database operations go through `gateway.conn` methods:

- **Read Operations**: `gateway.conn.read(sql, params)` - Returns list of dict rows
- **Create Operations**: `gateway.conn.create(sql, params)` - Returns lastrowid
- **Update Operations**: `gateway.conn.update(sql, params)` - Returns rowcount
- **Delete Operations**: `gateway.conn.delete(sql, params)` - Returns rowcount

**Cache Database Operations** (for cache database):
- `gateway.conn.read_cache(sql, params)` - Read from cache database
- `gateway.conn.create_cache(sql, params)` - Insert into cache database
- `gateway.conn.update_cache(sql, params)` - Update cache database

**Key Points**:
- Database access is through gateway.conn methods
- Connection is automatically initialized by gateway
- Transactions are automatically started on first write operation
- Always check `if not gateway or not gateway.conn:` before database operations

### Example 7: **Simple Database Read Operations**

**some_db_read_action.py**

```python
from hh.gateway.error.error_store import report_error, is_error

@register_action('some_db_read_action')
@register_command('some_db_read_action')
def some_db_read_action(conn) -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        report_error("action", "No gateway or connection available")
        trace_out()
        return False
    try:
        query = "SELECT id, name, status FROM table_1 WHERE active = 1"
        results = gateway.conn.read(query, [])
        data = {
            "count": len(results),
            "items": results
        }
        gateway.set_action_response(success_payload(data))
        log(f"database returned {len(results)} items.")
        trace_out()
        return True
    except Exception as e:
        warn(f"Database read failed: {str(e)}")
        report_error("action", f"Database read failed: {str(e)}")
        trace_out()
        return False
```

### Example 8: **Simple Database Write Operations**

**some_db_write_action.py**

```python
from hh.gateway.error.error_store import report_error, is_error

@register_action('some_db_write_action')
@register_command('some_db_write_action')
def some_db_write_action(conn) -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        report_error("action", "No gateway or connection available")
        trace_out()
        return False
    try:
        name = gateway.get_arg('name')
        status = gateway.get_arg('status')
        lastrowid = gateway.conn.create(
            "INSERT INTO table_1 (name, status) VALUES (%s, %s)",
            [name, status]
        )
        data = {
            "success": True,
            "message": "Record created successfully",
            "id": lastrowid
        }
        gateway.set_action_response(success_payload(data))
        log("Hello, Database!")
        trace_out()
        return True
    except Exception as e:
        warn(f"Database write failed: {str(e)}")
        report_error("action", f"Database write failed: {str(e)}")
        trace_out()
        return False
```

### Example 9: **Complex Read + Write Operations**

**some_complex_action.py**

```python
from hh.gateway.error.error_store import report_error, is_error

@register_action('some_complex_action')
@register_command('some_complex_action')
def some_complex_action(conn) -> bool:
    trace_in()
    gateway = get_gateway()
    if not gateway or not gateway.conn:
        warn("No gateway or connection available")
        report_error("action", "No gateway or connection available")
        trace_out()
        return False
    try:
        query = """
            SELECT t1.id, t1.name, t1.key, t2.value, t2.category
            FROM table_1 t1
            JOIN table_2 t2 ON t1.key = t2.key
            WHERE t1.active = 1
        """
        results = gateway.conn.read(query, [])
        processed_data = []
        for row in results:
            processed = black_box(row)
            processed_data.append(processed)
        for item in processed_data:
            gateway.conn.create(
                "INSERT INTO table_3 (processed_id, result, timestamp) VALUES (%s, %s, %s)",
                [item['id'], item['result'], item['timestamp']]
            )
        data = {
            "count": len(processed_data),
            "processed_items": processed_data
        }
        gateway.set_action_response(success_payload(data))
        log("complex data mutation successful.")
        trace_out()
        return True
    except Exception as e:
        warn(f"Complex operation failed: {str(e)}")
        report_error("backend", f"Complex operation failed: {str(e)}")
        trace_out()
        return False
```

## Table Rendering in Backend 

Powerful generalized system for formatting CLI table output with rich control over formatting with tons of customizable features and overrides

### Example 10: **Table Rendering Functions**

**render_list_example.py** 

```python
from typing import List, TypedDict
from hh.gateway import get_gateway, trace_in, trace_out, log, debug, warn
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import break_section
from hh.json.json_standard import get_data
from hh.text.text import safe_str

def render_items_section(source_data, lines):
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_items_section")
        trace_out()
        return False
    block = 'rows'
    if not gateway.is_no(block):                                    # render a table using the field configs
        items = source_data.get('items', [])
        count = len(items)
        log(f"Rendering {count} items")
        if not items:
            log("No items to render")
            trace_out()
            return True
        table_data = TableData()
        table_data.add_row(
            'items_header',
            name='name',
            status='status'
        )
        for item in items:
            table_data.add_row(
                'item_row',
                name=safe_str(item.get('name', 'Unknown')),
                status=safe_str(item.get('status', 'unknown'))
            )
        rendered_block = render_block(
            table_data,
            FieldConfig()
                .add_header('items_header')
                .add_simple(['item_row']),
            table_overrides={'margin_l': 4},
            block_type=block
        )
        lines.append(rendered_block)
        break_section(lines)
        log(f"Rendered items table with {table_data.num_rows()} rows")
    if not gateway.is_no('meta'):                                  # render a recursive metadata parsing table
        log("Rendering meta data")
        lines.append(render_block(data, block_type='meta'))
        break_section(lines)
	log("All done.")
    trace_out()
    return True
```

### Example 11: **Advanced Table Rendering with Dynamic Field Types**

**render_list_example.py** (enhanced version)

This example extends Example 10 to show how field types can be selected dynamically based on data values. The field type (first parameter to `add_row()`) is an identifier that maps to styling rules in FieldConfig. Most field types use default styling via `.add_simple()`, and colors are optional.

```python
from typing import List, TypedDict
from hh.gateway import get_gateway, trace_in, trace_out, log, debug, warn
from hh.render.render import render_header_block, render_block, finalize_output, FieldConfig, TableData
from hh.render.config.config import break_section
from hh.json.json_standard import get_data
from hh.text.text import safe_str

def render_items_section(source_data, lines):
    trace_in()
    gateway = get_gateway()
    if not gateway:
        warn("No gateway available in render_items_section")
        trace_out()
        return False
    block = 'rows'
    if not gateway.is_no(block):
        items = source_data.get('items', [])
        count = len(items)
        log(f"Rendering {count} items")
        if not items:
            log("No items to render")
            trace_out()
            return True
        table_data = TableData()
        table_data.add_row(
            'items_header',
            name='Name',
            status='Status'
        )
        for item in items:
            status = item.get('status', 'unknown')
            # Select field type based on data value
            if status == 'active':
                field_type = 'active_item'
            elif status == 'error':
                field_type = 'error_item'
            else:
                field_type = 'item_row'
            table_data.add_row(
                field_type,
                name=safe_str(item.get('name', 'Unknown')),
                status=safe_str(status)
            )
        rendered_block = render_block(
            table_data,
            FieldConfig()
                .add_header('items_header')
                .add_simple(['item_row', 'active_item', 'error_item'])
                .add_simple_color('error_item', 'red'),
            table_overrides={'margin_l': 4},
            block_type=block
        )
        lines.append(rendered_block)
        break_section(lines)
        log(f"Rendered items table with {table_data.num_rows()} rows")
    if not gateway.is_no('meta'):
        log("Rendering meta data")
        lines.append(render_block(data, block_type='meta'))
        break_section(lines)
	log("All done.")
    trace_out()
    return True
```

**Key Points:**
- The first parameter to `add_row()` is the field type identifier (e.g., `'item_row'`, `'active_item'`, `'error_item'`)
- Field types are selected dynamically based on data values (status in this example)
- `.add_simple()` applies default styling to field types (no color)
- `.add_simple_color()` is optional and only used when you want color styling
- Most field types will use `.add_simple()` without colors