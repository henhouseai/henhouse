# Page System Architecture Documentation

This document covers the core business logic modules for page, image, and text processing in the new Python Gateway-based system. For Gateway, Registry, Render, and other infrastructure details, see the respective documentation files.

## Table of Contents

1. [Page Module](#1-page-module)
2. [Image Module](#2-image-module)
3. [Text Processor Module](#3-text-processor-module)

## Agent Quick Reference

- **Core Modules**: `page/` (hierarchical content), `image/` (media management), `tp/` (markup parsing)
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
- **Mixin Methods**: Page uses multiple mixins for different functionality areas
- **Display Data**: call `_show_page()` to get formatted output data
- **Action Pattern**: Page actions use @register_action decorator

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
