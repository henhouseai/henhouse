# Page System Architecture Documentation

This document covers the core business logic modules for page, image, and text processing in the new Python Gateway-based system. For Gateway, Registry, Render, and other infrastructure details, see the respective documentation files.

## Table of Contents

1. [Page Module](#1-page-module)
2. [Image Module](#2-image-module)
3. [Text Processor Module](#3-text-processor-module)

## Agent Quick Reference

- **Core Modules**: `page/` (hierarchical content), `image/` (media management), `tp/` (markup parsing)
- **Mixin Architecture**: Page class uses 6 mixins with automatic connection management via wrapper system
- **Method Registration**: Mixins register methods with `@register_page_mixin_methods` decorator
- **Connection Management**: Wrapper system automatically routes to `@db_read`/`@db_write` or reuses existing connection
- **Markup Language**: `[[page_links]]`, `{{image_embeds}}`, decorator-based processing
- **Page Hierarchy**: Parent-child relationships with automatic breadcrumb generation
- **Image Instances**: Automatic multi-size generation and management
- **Text Processing**: Decorator-based parsing with configurable decorator registry

## Agent Training Notes

### Module Integration
- **Page Objects**: Actions create Page() instances for content operations
- **Image Objects**: Actions create Image() instances for media operations
- **Text Processing**: Page content parsed through TextProcessor with decorator registry
- **Mixin Pattern**: Pages and images use multiple mixins for functionality
- **Display Methods**: call _show_page() or _show_image() for formatted output data

### Common Usage Patterns
- **Page Creation**: `Page(page_id)` loads data and provides mixin methods
- **Image Management**: `Image(image_id)` handles multi-size instances automatically
- **Content Parsing**: TextProcessor decorators parse custom markup syntax
- **Data Retrieval**: All modules load from database via connection decorators

---

## 1. Page Module

**Files**: `hh/page/*.py`

The hierarchical page management system with CRUD operations, display logic, and content processing. Provides a clean object-oriented interface using mixins for functionality.

### Page Class

#### owned by:
- action handlers : *Created by page actions (add_page, show_page, etc.)*

#### owns:
- page data : *Page content, metadata, hierarchy information*
- validation logic : *Page validation and constraint checking*
- hierarchy logic : *Parent-child relationship management*
- content logic : *Text processing and parsing*
- image logic : *Image association management*
- display logic : *Output data preparation*

#### data managed:
- page metadata (source of truth) : *ID, name, link, parent, class, visibility*
- content data (source of truth) : *Text content and parsed HTML*
- hierarchy data (source of truth) : *Parent-child relationships*
- image associations (source of truth) : *Linked images*
- display data (source of truth) : *Rendered output data for backends*

#### calls:
- **Validation mixins** : *PageValidationMixin for constraints*
- **Hierarchy mixins** : *PageHierarchyMixin for tree operations*
- **Content mixins** : *PageContentMixin for content handling*
- **Image mixins** : *PageImagesMixin for image operations*
- **Display mixins** : *PageDisplayMixin for output preparation*
- **AJAX mixins** : *PageAjaxMixin for JSON payload assembly*

#### called by:
- action handlers : *Actions create Page instances and call methods*
- backend handlers : *Backends receive Page data for formatting*

#### retrieves from:
- database : *Gets page info from pages table via connection decorators*
- database : *Gets parent-child relationships for hierarchy*
- text processor : *Gets parsed content from TextProcessor*

#### provides to:
- action handlers : *Provides Page objects with methods*
- backend handlers : *Provides structured page data for rendering*

#### configuration dependencies:
- hh/page/*.py : *Page module implementation files*

#### agent training notes:
- **Page Creation**: Actions call `Page(page_id)` which loads from database
- **Data Loading**: Page constructor loads data automatically on init
- **Mixin Methods**: Page uses six mixins with automatic connection management via wrapper system
- **Method Registration**: Mixins register methods with `@register_page_mixin_methods` decorator
- **Connection Management**: Wrapper system automatically handles `@db_read`/`@db_write` decorators
- **Transaction Support**: Methods can share connections when `self.conn` is set
- **Display Data**: call `show_page()` (public wrapper) or `_show_page()` (mixin method) for formatted output data
- **Action Pattern**: Page actions use @register_action decorator

### Mixin Architecture

The Page class uses multiple inheritance with six specialized mixins, each providing focused functionality. The mixin system includes a sophisticated method registration and wrapper system that handles database connection management automatically.

#### The Six Mixins

1. **PageValidationMixin** (`page_validation.py`)
   - **Purpose**: Name validation, move validation, duplicate checking
   - **Key Methods**: `validate_name()`, `can_move_to_page()`, `check_children_recursive()`
   - **Class Methods**: `allow_null_names()`, `allow_duplicate_names()`, `auto_link_name()`, `allow_inside_of()`
   - **Instance Methods**: `allow_class_inside()`

2. **PageHierarchyMixin** (`page_hierarchy.py`)
   - **Purpose**: Parent-child relationships, breadcrumbs, move/copy operations
   - **Key Methods**: `get_path()`, `get_children_data()`, `get_child_page_ids()`, `move_page()`, `copy_page()`
   - **Static Methods**: `get_children_query()` - can be overridden by subclasses to customize child queries

3. **PageContentMixin** (`page_content.py`)
   - **Purpose**: CRUD operations, text processing, page data assembly
   - **Key Methods**: `modify_name()`, `modify_text()`, `add_page()`, `delete_page()`, `get_page_data()`, `flag_page_modification()`
   - **Class Hooks**: `add_page_class_information()` - called after page creation for class-specific setup
   - **Instance Hooks**: `delete_page_class_information()` - called before page deletion for cleanup

4. **PageImagesMixin** (`page_images.py`)
   - **Purpose**: Image association management, ranking, copying/moving images
   - **Key Methods**: `get_images_data()`, `add_image()`, `copy_images()`, `move_images()`, `set_image_rank()`, `remove_image()`
   - **Internal Methods**: `_create_image_record()`, `_add_image_to_group()`, `_reorder_images()`

5. **PageDisplayMixin** (`page_display.py`)
   - **Purpose**: Display data preparation, child grouping, badge headers
   - **Key Methods**: `show_page()`, `_get_children_by_class()`, `_get_children_for_class()`
   - **Hooks**: `add_upper_content()`, `add_lower_content()`, `add_badge_headers()`, `get_child_row_field_type()`

6. **PageAjaxMixin** (`page_ajax.py`)
   - **Purpose**: AJAX-friendly JSON payload assembly for MCP backend
   - **Key Methods**: `get_page()` - returns minimal JSON structure with available actions

#### Method Registration System

Each mixin registers its public methods using the `@register_page_mixin_methods` decorator:

```python
@register_page_mixin_methods
def _register_validation_methods():
    return {
        'validate_name': {'mixin_method': '_validate_name', 'decorator': 'read'},
        'can_move_to_page': {'mixin_method': '_can_move_to_page', 'decorator': 'read'},
    }
```

**Registration Pattern**:
- **Public Method Name**: The method name exposed to users (e.g., `validate_name`)
- **Mixin Method Name**: The private method in the mixin (e.g., `_validate_name`)
- **Decorator Type**: `'read'` = `@db_read`, `'write'` = `@db_write`

All registered methods are collected in `page_method_registry.py` and used by the wrapper system.

#### Wrapper Method System

The `_create_wrapper_methods` class decorator automatically creates wrapper methods that handle database connection management. For each registered method, it creates three methods:

1. **Decorated Version** (`page_dec_{method_name}`):
   - Uses `@db_read` or `@db_write` decorator
   - Creates and manages database connection automatically
   - Used when `self.conn is None`

2. **Connection Version** (`page_conn_{method_name}`):
   - Uses existing `self.conn` connection
   - No decorator (connection already established)
   - Used when `self.conn` exists (for transaction support)

3. **Public Wrapper** (`{method_name}`):
   - Routes to appropriate version based on connection state
   - Automatically resets connection after decorated version completes

**Connection Management Flow**:
```python
# When self.conn is None:
page.validate_name("test")
  → wrapper checks: self.conn is None?
  → calls page_dec_validate_name()
  → @db_read creates connection
  → calls _validate_name() (mixin method)
  → resets self.conn = None

# When self.conn exists (transaction):
page.conn = existing_connection
page.validate_name("test")
  → wrapper checks: self.conn exists?
  → calls page_conn_validate_name()
  → directly calls _validate_name() (reuses connection)
```

**Benefits**:
- **Automatic Connection Management**: Methods work with or without a connection
- **Transaction Support**: Multiple operations can share a connection/transaction
- **Clean API**: Public methods hide connection complexity
- **Mixin Isolation**: Each mixin focuses on business logic, not connection management

#### Mixin Method Implementation Pattern

Mixin methods follow a consistent pattern:

1. **Private Methods**: Mixin methods are prefixed with `_` (e.g., `_validate_name`)
2. **Public Wrappers**: Wrapper system creates public methods (e.g., `validate_name`)
3. **Error Handling**: Uses `is_error()` checks and `report_error()` for error coordination
4. **Debug Integration**: Uses `trace_in()`, `trace_out()`, `log()`, `debug()`, `warn()`
5. **Connection Usage**: Methods use `self.conn` directly (connection management handled by wrapper)

**Example Mixin Method**:
```python
def _validate_name(self, name: str, page_class: str, exclude_id: Optional[int] = None) -> bool:
    trace_in()
    # Uses self.conn directly (connection provided by wrapper)
    results = r_query(self.conn, "SELECT id FROM pages WHERE ...", ...)
    trace_out()
    return True
```

#### Extending the Mixin System

To add a new mixin:

1. **Create Mixin Class**: Create new mixin class with private methods
2. **Register Methods**: Use `@register_page_mixin_methods` to register public methods
3. **Add to Page Class**: Add mixin to Page class inheritance list
4. **Specify Decorator Type**: Choose `'read'` or `'write'` for each method

The wrapper system automatically handles the rest.

---

## 2. Image Module

**Files**: `hh/image/*.py`

The image management system with CRUD operations, multi-size instance management, and display logic. Handles automatic image processing and intelligent sizing.

### Image Class

#### owned by:
- action handlers : *Created by image actions (add_image, show_image, etc.)*

#### owns:
- image data : *Image metadata and instance information*
- validation logic : *Image validation and constraints*
- instance logic : *Multi-size image management*
- display logic : *Output data preparation*

#### data managed:
- image metadata (source of truth) : *ID, caption, parent, visibility*
- instance data (source of truth) : *Multiple sized versions*
- file paths (source of truth) : *Physical file locations*
- display data (source of truth) : *Rendered output data for backends*

#### calls:
- **ImageValidationMixin** : *Validation logic*
- **ImageInstancesMixin** : *Multi-size management*
- **ImageContentMixin** : *Content operations*
- **ImageDisplayMixin** : *Output preparation*

#### called by:
- action handlers : *Actions create Image instances and call methods*
- backend handlers : *Backends receive Image data for formatting*

#### retrieves from:
- database : *Gets image data from images table*
- database : *Gets instance data from imageinstances table*
- file system : *Gets physical image files from /srv/images/*

#### provides to:
- action handlers : *Provides Image objects with methods*
- backend handlers : *Provides structured image data for rendering*

#### configuration dependencies:
- hh/image/*.py : *Image module implementation files*

#### agent training notes:
- **Image Creation**: Actions call `Image(image_id)` which loads metadata
- **Instance Management**: Images automatically manage multiple size instances
- **Display Data**: call `_show_image()` to get formatted output data
- **Action Pattern**: Image actions use @register_action decorator

---

## 3. Text Processor Module

**Files**: `hh/tp/*.py` and `hh/tp/*.ini`

The custom markup parsing system for page content. Implements decorator-based processing with configurable decorator registry.

### TextProcessor Class

#### owned by:
- page system : *Created by Page class for content processing*

#### owns:
- parse state : *Current parsing position and context*
- decorator registry : *Registered decorators for processing*
- parse results : *Processed HTML content*

#### data managed:
- parse state (source of truth) : *Current parsing position in text*
- decorator registry (source of truth) : *Registered decorators and configuration*
- parse results (source of truth) : *Processed HTML content output*

#### calls:
- **process_text()** : *Main processing function*
- **decorator registry** : *Applies registered decorators*
- **parse syntax** : *Parses custom markup syntax*

#### called by:
- page system : *Pages call TextProcessor for content parsing*
- action handlers : *Actions may call for text rendering*

#### retrieves from:
- page content : *Gets page text data*
- decorator config files : *Gets decorator configuration from .ini files*

#### provides to:
- page system : *Provides parsed HTML content*
- backend handlers : *Provides processed text for rendering*

#### configuration dependencies:
- hh/tp/*.ini files : *Decorator configuration (icon.ini, label.ini)*
- hh/tp/decorators.py : *Decorator implementations*

#### agent training notes:
- **Text Processing**: Use TextProcessor for all content processing
- **Decorator Pattern**: Decorators are registered automatically and applied in order
- **Markup Syntax**: Supports [[links]], {{images}}, and other custom syntax
- **INI Configuration**: Decorators configured in .ini files in tp/ directory

---

## Integration with Other Systems

### With Gateway (see gateway.md)
- Actions create Page/Image instances and call mixin methods
- Actions return JSON via `gateway.set_action_response()`
- Backends receive Page/Image JSON data for formatting

### With Registry (see registry.md)
- Page/Image actions use @register_action decorator
- Backends use appropriate @register_parser/@register_http/@register_mcp decorators
- Handlers auto-discovered and registered

### With Render System (see render.md)
- Backends use render functions to format Page/Image data
- Page/Image display data structure compatible with render system
- FieldConfig used for table formatting

### Database Access Pattern
- All modules use @db_read/@db_write decorators
- Page/Image mixins call r_query()/u_query() for database operations
- Tier-based credentials loaded from ~/.project.cnf files

---

This document focuses specifically on the page, image, and text processor business logic modules. For infrastructure details (Gateway, Registry, Render), see the respective documentation files.
