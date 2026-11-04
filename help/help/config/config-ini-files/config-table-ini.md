# config-table-ini
## description
Configuration file containing table styling and layout definitions for the Henhouse parser system table rendering engine.
## summary
The table.ini file serves as the central configuration repository for all table styling and layout definitions used throughout the Henhouse parser architecture. It defines multiple table classes with styling parameters, border characters, layout options, and rendering specifications that provide consistent, customizable table output across all parser modules and data presentation contexts.
## full_text
The table.ini file is the central configuration repository for all table styling and layout definitions used throughout the Henhouse parser architecture. It defines a styling system with multiple table classes, configuration options, and rendering capabilities that provide consistent, customizable table output across all parser modules and data presentation contexts.

**Table Styling System Architecture:**
The table system uses a class-based approach where each table class is defined with specific styling parameters, layout options, and rendering characteristics. Table classes are loaded by the config system via `_read_flat_ini()` in `config.py` and made available through the TableBuilder integration using `conf_str()` and `conf_int()` functions. The system supports Unicode characters, ASCII compatibility, and display-width aware text processing.

**Configuration System:**
Each table class supports configuration including column definitions, padding settings, border characters, overflow handling, alignment options, margin specifications, and rule display. The system uses a consistent naming pattern: `t_<class>_<parameter>`, with parameters covering layout, styling, borders, text handling, and rendering behavior.

**Table Rendering:**
The table system provides table rendering with support for Unicode characters, ASCII compatibility, display-width aware text processing, word boundary wrapping, ellipsis truncation, and various styling options that work across different terminal environments and output formats.

**Configuration Access:**
Table configurations are accessed through the config system using `conf_str()` and `conf_int()` functions:
```python
from config import conf_str, conf_int

# Get table configuration values
has_header = conf_int('standard', 'has_header')  # Returns 1
columns = conf_str('standard', 'columns')        # Returns "label"
border_char = conf_str('standard', 'top_left')   # Returns "┌"
```

**Usage with TableBuilder:**
```python
from table import TableBuilder

# Create table with standard styling
tb = TableBuilder('standard')
tb.set_columns('label')
tb.row(keys=['label'], values=['Help: watercooler'])
result = tb.render()
```

**Integration with Parser System:**
Table definitions integrate with the TableBuilder system and parser modules through the config system, providing consistent table rendering throughout the parser architecture. The system supports dynamic table creation, field-based rendering, and customizable output formatting.

**Customization and Maintenance:**
Table styles can be customized and extended by modifying the table.ini file, with changes reflected throughout the system when configuration is reloaded. The system supports adding new table classes, modifying existing styles, and implementing specialized layout requirements.
---
# standard-table-classes
## description
Standard table classes with bordered appearance and consistent styling for general-purpose data display.
## summary
Table classes that provide standard styling with borders, headers, and consistent appearance suitable for most parser output and data display, including Unicode, ASCII, and enhanced border variants.
## full_text
Standard table classes provide the foundation for most table rendering throughout the parser system, offering clean styling with consistent borders, headers, and formatting options.

**Standard Table (t_standard):**
- Basic bordered table with Unicode characters
- Header support with rule separation (`t_standard_has_header = 1`)
- Single-column layout (`t_standard_columns = label`)
- Padding settings (`t_standard_padl = 1`, `t_standard_padr = 1`)
- Header rule display (`t_standard_rule_header = 1`)
- Unicode border characters: `┌`, `│`, `─`, `┐`, `└`, `┘`
- Junction characters: `┬`, `┼`, `┴`
- Header separators: `╞`, `╪`, `╡`

**Double Table (t_double):**
- Enhanced borders with double-line characters
- More prominent visual separation
- Single-column layout (`t_double_columns = label`)
- Double-line border characters: `╔`, `║`, `═`, `╗`, `╚`, `╝`
- Junction characters: `╦`, `╬`, `╩`
- Header separators: `╠`, `╬`, `╣`

**Heavy Table (t_heavy):**
- Bold borders with heavy character sets
- Strong visual emphasis and separation
- Single-column layout (`t_heavy_columns = label`)
- Heavy border characters: `┏`, `┃`, `━`, `┓`, `┗`, `┛`
- Junction characters: `┳`, `╋`, `┻`
- Header separators: `┣`, `╋`, `┫`

**ASCII Table (t_ascii):**
- Plain ASCII characters for maximum compatibility
- Works across all terminal environments
- Single-column layout (`t_ascii_columns = label`)
- ASCII border characters: `+`, `|`, `-`
- Junction characters: `+` for all junctions
- Header separators: `+` for all separators

**Configuration Options:**
Each standard table class supports configuration including column definitions, padding settings, border characters, header rules, margin specifications, and text handling options.

**Integration:**
Standard table classes integrate with the TableBuilder system to provide consistent table rendering across all parser modules and output contexts.
---
# specialized-table-classes
## description
Specialized table classes for specific use cases, data types, and presentation requirements.
## summary
Table classes designed for specific purposes including metadata display, message formatting, compact layouts, text wrapping, divider elements, and specialized data presentation with optimized configurations for particular content types.
## full_text
Specialized table classes are designed for specific use cases and data types, providing optimized layouts and styling for particular kinds of content and presentation needs across the parser system.

**Key-Value Bare Table (t_kv_bare):**
- No borders or headers (`t_kv_bare_has_header = 0`)
- Two-column layout (`t_kv_bare_columns = label,value`)
- No padding (`t_kv_bare_padl = 0`, `t_kv_bare_padr = 0`)
- Suitable for simple key-value displays without visual clutter

**Plain Text Wrapping (t_plain_wrap_80):**
- Text wrapping at 80 characters (`t_plain_wrap_80_width_text = 80`)
- Single column layout (`t_plain_wrap_80_columns = text`)
- Wrap overflow handling (`t_plain_wrap_80_overflow_text = wrap`)
- Header rule display (`t_plain_wrap_80_rule_header = 1`)
- Mid-rule separator (`t_plain_wrap_80_h_mid = "─"`)

**Divider Tables (t_div, t_div_80, t_div_120):**
- No headers (`t_div_has_header = 0`)
- Single column layout (`t_div_columns = div`)
- Fixed widths: 80 chars (t_div_80), 120 chars (t_div_120)
- Used for visual separation and content division
- No padding or margins for clean separation

**Minimal Table (t_minimal):**
- Header support (`t_minimal_has_header = 1`)
- Two-column layout (`t_minimal_columns = label,div`)
- Padding settings (`t_minimal_padl = 2`, `t_minimal_padr = 2`)
- Header rule with separator (`t_minimal_rule_header = 1`)
- Used for help table outer display
- Border characters: `├`, `┼`, `┤`, `═`, `…`

**Metadata Tables (t_meta_main, t_meta_sub):**
- Main metadata table with header (`t_meta_main_has_header = 1`)
- Sub metadata table without header (`t_meta_sub_has_header = 0`)
- Two-column layout (`t_meta_main_columns = label,div`)
- Left margin (`t_meta_main_margin_l = 4`)
- Fixed width for sub tables (`t_meta_sub_width_div = 80`)
- Border characters: `├`, `┼`, `┤`, `─`

**Compact Metadata (t_meta_compact_wrap):**
- No header (`t_meta_compact_wrap_has_header = 0`)
- Two-column layout (`t_meta_compact_wrap_columns = key,value`)
- Fixed widths (`t_meta_compact_wrap_width_key = 20`, `t_meta_compact_wrap_width_value = 40`)
- Rule between rows (`t_meta_compact_wrap_rule_every = 1`)
- Padding settings (`t_meta_compact_wrap_padl = 1`, `t_meta_compact_wrap_padr = 1`)
- Vertical separator (`t_meta_compact_wrap_v_mid = "│"`)

**Embed Block (t_embed_block_fixed):**
- No header (`t_embed_block_fixed_has_header = 0`)
- Single column layout (`t_embed_block_fixed_columns = text`)
- Fixed width (`t_embed_block_fixed_width_text = 40`)
- Wrap overflow (`t_embed_block_fixed_overflow_text = wrap`)
- No margins for nesting (`t_embed_block_fixed_margin_l = 0`, `t_embed_block_fixed_margin_r = 0`)
- Padding settings (`t_embed_block_fixed_padl = 1`, `t_embed_block_fixed_padr = 1`)

**Messages Compact (t_messages_compact):**
- No header (`t_messages_compact_has_header = 0`)
- Eight-column layout: `msg_id,chan,queued,occurred,from,kind,content_block,meta_block`
- Fixed column widths for message data
- Border characters: `┌`, `│`, `─`, `┐`, `└`, `┘`, `┬`, `┴`
- Auto-width for content and meta blocks (`t_messages_compact_width_content_block = 0`, `t_messages_compact_width_meta_block = 0`)


**Configuration Flexibility:**
Specialized table classes support customization to meet specific requirements while maintaining consistency with the overall table system. Each class can be modified through parameter adjustments in table.ini.

**Integration:**
Specialized table classes integrate with parser modules to provide presentation for specific data types and use cases, supporting the overall parser architecture's flexibility and consistency.
---
# layout-configuration
## description
Layout and formatting configuration options for table rendering and presentation.
## summary
Layout configuration system providing control over table appearance, spacing, alignment, text handling, borders, and formatting to ensure readable and consistent output across all table classes with customization options.
## full_text
Layout configuration provides control over table appearance, spacing, alignment, and formatting to ensure readable and consistent output across all table classes with customization options.

**Column Configuration:**
- Column definitions and ordering (`t_<class>_columns`)
- Width specifications (`t_<class>_width_<column>`)
- Alignment options (`t_<class>_align_<column>`: left, right, center)
- Vertical alignment (`t_<class>_valign_<column>`: top, center, bottom)
- Column-specific padding (`t_<class>_padl_<column>`, `t_<class>_padr_<column>`)

**Padding and Spacing:**
- Cell padding (`t_<class>_padl`, `t_<class>_padr`)
- Per-column padding overrides (`t_<class>_padl_<column>`, `t_<class>_padr_<column>`)
- Margin settings (`t_<class>_margin_l`, `t_<class>_margin_r`, `t_<class>_margin_t`, `t_<class>_margin_b`)
- Default padding when not specified: 0
- Default margins when not specified: 0

**Border and Separator Configuration:**
- Border character definitions (`t_<class>_top_left`, `t_<class>_v_left`, `t_<class>_h_top`)
- Junction characters (`t_<class>_top_mid`, `t_<class>_mid_mid`, `t_<class>_bot_mid`)
- Vertical separators (`t_<class>_v_left`, `t_<class>_v_mid`, `t_<class>_v_right`)
- Horizontal separators (`t_<class>_h_top`, `t_<class>_h_mid`, `t_<class>_h_bot`)
- Header-specific separators (`t_<class>_header_left`, `t_<class>_header_mid`, `t_<class>_header_right`)
- Bottom-specific separators (`t_<class>_bot_left`, `t_<class>_bot_mid`, `t_<class>_bot_right`)

**Text Handling:**
- Overflow handling (`t_<class>_overflow_<column>`: wrap, ellipsis, clip)
- Text wrapping with word boundaries and display-width awareness
- Display-width aware text processing using wcwidth library
- Special character handling for emoji and East Asian characters
- Word boundary wrapping with hyphenation for long tokens

**Rule Configuration:**
- Header rule display (`t_<class>_rule_header`)
- Data row rules (`t_<class>_rule_every`)
- Rule patterns (`t_<class>_hsep_top`, `t_<class>_hsep_mid`, `t_<class>_hsep_bottom`)
- Fallback rule patterns (`t_<class>_hsep`)
- Rule rendering only when triggered and band has separators or junctions

**Width and Sizing:**
- Auto-sizing when width not specified (0 = auto width)
- Fixed width specifications for consistent layouts
- Display-width calculation for proper alignment
- Column width normalization across vertical separators

**Integration:**
Layout configuration integrates with the TableBuilder system to provide consistent table rendering with customization options, supporting the parser system's flexible output requirements.
---
# rendering-options
## description
Rendering options and display specifications for table output across different environments and requirements.
## summary
Configuration options that control how tables are rendered including display modes, character sets, text processing, debug logging, and output formatting for different environments and terminal requirements.
## full_text
Rendering options provide control over how tables are displayed, ensuring consistent appearance across different environments and meeting various output requirements.

**Character Set Options:**
- Unicode characters for enhanced appearance (standard, double, heavy tables)
- ASCII characters for maximum compatibility (t_ascii)
- Custom character sets defined in table.ini
- Fallback options for different terminal environments
- Character width normalization across vertical separators

**Display Modes:**
- Header display control (`t_<class>_has_header`)
- Rule display control (`t_<class>_rule_header`, `t_<class>_rule_every`)
- Column visibility through column definitions
- Content overflow handling (`t_<class>_overflow_<column>`)
- Band-specific rendering with junction and separator support

**Output Formatting:**
- Fixed width settings (`t_<class>_width_<column>`)
- Auto-sizing when width not specified (0 = auto width)
- Text wrapping and overflow handling
- Margin and positioning control
- Column width normalization and alignment

**Text Processing:**
- Display-width aware text processing using wcwidth library
- Word boundary wrapping with hyphenation for long tokens
- Ellipsis truncation (`t_<class>_overflow_<column> = ellipsis`)
- Character clipping (`t_<class>_overflow_<column> = clip`)
- Special character handling for emoji and East Asian characters

**Environment Adaptation:**
- Character encoding handling
- Display width calculation using wcwidth library
- Cross-platform compatibility
- Terminal environment considerations
- Unicode character width calculation

**Debug Logging:**
- Debug log file configuration (`t_debug_log_file = table.render.log`)
- Table rendering debug information
- Performance monitoring and troubleshooting
- Development and maintenance support

**Integration:**
Rendering options integrate with the parser system to provide consistent table display across all supported environments and output formats, supporting the overall parser architecture's flexibility and reliability.
---
# customization-and-maintenance
## description
Table customization options and maintenance procedures for the styling system.
## summary
Guidelines for customizing table styles, adding new table classes, maintaining the table styling system for performance and consistency, and integrating with the overall parser architecture.
## full_text
The table styling system provides customization options and maintenance procedures to ensure performance, consistency, and adaptability to changing requirements across the parser architecture.

**Customization Options:**
- Adding new table classes for specific needs
- Modifying existing table styles and parameters
- Creating custom character sets and borders
- Implementing specialized layout requirements
- Extending text handling and overflow options

**Table Class Creation:**
- Define new table classes with unique styling
- Configure column layouts and specifications (`t_<class>_columns`)
- Set border and separator characters (`t_<class>_top_left`, `t_<class>_v_left`, etc.)
- Implement custom rendering behavior
- Use consistent naming pattern: `t_<class>_<parameter>`
- Follow existing parameter conventions for compatibility

**Parameter Configuration:**
- Adjust padding, margins, and spacing (`t_<class>_padl`, `t_<class>_margin_l`)
- Configure alignment and text handling (`t_<class>_align_<column>`, `t_<class>_overflow_<column>`)
- Set overflow and wrapping options (wrap, ellipsis, clip)
- Customize visual appearance and hierarchy
- Configure rule display (`t_<class>_rule_header`, `t_<class>_rule_every`)

**Configuration Loading:**
- Table classes are loaded via `_read_flat_ini()` in config.py
- Parameters accessed through `conf_str()` and `conf_int()` functions
- Changes require configuration reload to take effect
- No code changes needed for parameter modifications
- Configuration system supports dynamic loading

**Maintenance Procedures:**
- Review table styling consistency across all classes
- Test character set and encoding validation
- Verify cross-platform compatibility
- Check parameter naming conventions
- Validate display-width calculations
- Test overflow handling and text wrapping

**Best Practices:**
- Consistent naming conventions for table classes
- Document custom configurations and their purposes
- Test across different environments and terminal types
- Follow existing parameter patterns for compatibility
- Use display-width aware text processing
- Implement proper error handling for edge cases

**Debug and Troubleshooting:**
- Enable debug logging (`t_debug_log_file = table.render.log`)
- Monitor table rendering performance
- Test with various data types and sizes
- Validate character width calculations
- Check border and separator rendering

**Integration:**
Customization and maintenance procedures integrate with the overall parser system to ensure that table styling remains consistent, maintainable, and performant across all modules and use cases, supporting the parser architecture's flexibility and reliability.
---
