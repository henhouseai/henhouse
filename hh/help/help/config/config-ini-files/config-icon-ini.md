# config-icon-ini
## description
Configuration file containing emoji definitions for UI elements and status indicators.
## summary
The icon.ini file contains 45 emoji and symbol definitions used by the Henhouse parser system for UI elements, status indicators, and visual formatting. Icons are loaded on-demand by the config system and accessed through the ic() function with --no-icon flag support.
## full_text
The icon.ini file contains emoji and symbol definitions used throughout the Henhouse parser system. The file uses a simple key-value format where each icon is defined with a descriptive name and its corresponding emoji value.

**File Format:**
Icons are defined as key-value pairs in INI format: `key = "emoji"`. The file is loaded by `_read_flat_ini()` in config.py and stored in the `_cfg_icon` global variable. Icons are accessed through the `ic()` function which strips quotes and handles the --no-icon flag.

**Icon Categories:**
The file contains 45 icons organized into categories:
- Status indicators: active, inactive, todo, doing, review, done, success, error
- Content markers: message, channel, agent, help_topic, help_section, help_file
- Formatting elements: tab, blank_emoji, meta, pointer
- System elements: error, success, info, timestamp

**Integration with Config System:**
Icons integrate with the configuration routing system where non-prefixed keys are routed to icon.ini. The `ic()` function checks the --no-icon flag and returns empty string if disabled, otherwise returns the icon value from the configuration. The system includes comprehensive logging that tracks icon usage in `config.log.ic` files with timestamp and count data.

**Usage in Parser System:**
Icons are used in field configurations for table rendering, where they are referenced by key and rendered alongside labels. The system supports conditional display based on --no-* flags defined in parser configurations.
---
# status-indicators
## description
Status and state indicators for agents, tasks, and system elements.
## summary
Emoji indicators that show the current status or state of various system elements including agent status, task states, and operational conditions.
## full_text
Status indicators provide visual feedback about the current state of system elements through emoji symbols defined in icon.ini.

**Agent Status Icons:**
- `active = "🎯"` - Active agents currently operational
- `inactive = "💤"` - Agents not running
- `terminated = "🚫"` - Agents permanently deactivated
- `session = "⏰"` - Active work sessions and timeclock status

**Task and Work State Icons:**
- `todo = "🔲"` - Tasks not started
- `doing = "🔄"` - Tasks in progress
- `review = "🔍"` - Tasks under review
- `done = "✅"` - Completed tasks
- `task = "📌"` - General task indicator
- `step = "📍"` - Individual work steps

**System State Icons:**
- `success = "✅"` - Successful operations
- `error = "🚨"` - Error conditions and warnings
- `info = "📊"` - Information and status messages

**Usage:**
Status indicators are used in field configurations for table rendering, where they are referenced by key and displayed alongside labels. The `ic()` function handles conditional display based on the --no-icon flag.
---
# content-type-markers
## description
Emoji markers that identify different types of content and data elements.
## summary
Icons that categorize and identify different types of content including messages, channels, agents, files, and other data elements throughout the system.
## full_text
Content type markers provide visual categorization of different data elements through emoji symbols defined in icon.ini.

**Communication Icons:**
- `message = "📧"` - General message indicator
- `microlog = "🔔"` - Microlog messages
- `pointer = "👉"` - Pointer and direction indicators
- `channel = "📡"` - Communication channels
- `operator = "👨"` - Operator responses

**Data Element Icons:**
- `agent = "🤖"` - Agent identification
- `role = "🎭"` - Agent roles
- `help_topic = "❓"` - Help topics
- `help_section = "🔸"` - Help sections
- `help_file = "📄"` - Help files
- `help_child = "📁"` - Help categories
- `filing_cabinet = "📂"` - Filing cabinet
- `notes = "📄"` - Notes and documents

**Navigation Icons:**
- `sidecar_link = "🔗"` - Links and references
- `linked_items = "🔗"` - Linked items
- `activities = "📋"` - Activity lists
- `agent_tree = "🌳"` - Agent tree structure

**Usage:**
Content type markers are used in field configurations for table rendering, where they are referenced by key and displayed alongside labels to categorize different types of data.
---
# formatting-elements
## description
Spacing, alignment, and formatting symbols for visual layout.
## summary
Emoji and symbols used for text formatting, spacing, alignment, and visual layout throughout the parser system output.
## full_text
Formatting elements provide visual structure and spacing for parser output through emoji symbols defined in icon.ini.

**Spacing Icons:**
- `tab = "  "` - Tab characters for indentation
- `blank_emoji = "  "` - Blank emoji for consistent spacing
- `meta = "🔸"` - Meta information indicators

**Layout Elements:**
- `pointer = "👉"` - Direction and navigation indicators
- `sidecar_link = "🔗"` - Connection and linking symbols
- `sort_order = "#"` - Ordering and numbering

**Text Formatting:**
- `docket = "💼"` - Work docket indicators
- `ask = "🧩"` - Question and inquiry markers
- `subscription = "📡"` - Subscription indicators

**Usage:**
Formatting elements are used in field configurations for table rendering, where they provide visual structure and spacing alongside text content. The `tc()` function uses tab and blank_emoji for consistent indentation patterns with support for different modes and repeat counts.
---
# system-elements
## description
System-level icons for errors, success states, and operational feedback.
## summary
Icons that provide feedback about system operations, errors, success states, and other operational information throughout the Henhouse architecture.
## full_text
System elements provide feedback about system operations through emoji symbols defined in icon.ini.

**Success and Error Icons:**
- `success = "✅"` - Successful operations
- `error = "🚨"` - Error conditions and warnings
- `info = "📊"` - Information and status messages

**Operational Feedback:**
- `timestamp = "🕒"` - Time and date indicators
- `agent_state = "⚙️"` - Agent state information
- `runs = "🏃"` - Execution and run indicators

**User Guidance:**
- `help_topic = "❓"` - Help and assistance markers
- `help_section = "🔸"` - Section indicators
- `help_file = "📄"` - File indicators

**Usage:**
System elements are used in field configurations for table rendering, where they provide visual feedback about system operations and status. The `ic()` function handles conditional display based on the --no-icon flag.
---
