# Smoke Check Examples

This document shows example output from running various Henhouse commands on different platforms. Use this as a reference to verify your installation is working correctly.

## Dependency List

### Windows PowerShell

```powershell
PS C:\Users\lee\Desktop\henhouse> hen dependency-list

  🏠 Henhouse:   Dependency List:

    ┌──────────────────────────┬────────────────┬──────────────────────────────┐
    │ 📦  Dependencies         │ 6 dependencies │ required by                  │
    ╞══════════════════════════╪════════════════╪══════════════════════════════╡
    │ ❌  Dependency Missing   │ grp            │ process_manager              │
    │ ❌  Dependency Missing   │ pillow         │ utils                        │
    │ ✅  Dependency Installed │ psutil         │ process_manager              │
    │ ❌  Dependency Missing   │ pwd            │ file_system, process_manager │
    │ ✅  Dependency Installed │ pygments       │ source_code_file_content     │
    │ ✅  Dependency Installed │ pymysql        │ connection                   │
    └──────────────────────────┴────────────────┴──────────────────────────────┘
```

**Note**: On Windows, some dependencies like `grp`, `pwd` are Unix-specific and will show as missing. This is expected.

### Unix (Ubuntu Server) with Debug Logging

```bash
lee@henhouse:/henhouse$ hen dependency-list -log

  🏠 Henhouse:   Dependency List:

    ┌──────────────────────────┬────────────────┬──────────────────────────────┐
    │ 📦  Dependencies         │ 6 dependencies │ required by                  │
    ╞══════════════════════════╪════════════════╪══════════════════════════════╡
    │ ✅  Dependency Installed │ grp            │ process_manager              │
    │ ✅  Dependency Installed │ pillow         │ utils                        │
    │ ✅  Dependency Installed │ psutil         │ process_manager              │
    │ ✅  Dependency Installed │ pwd            │ file_system, process_manager │
    │ ✅  Dependency Installed │ pygments       │ source_code_file_content     │
    │ ✅  Dependency Installed │ pymysql        │ connection                   │
    └──────────────────────────┴────────────────┴──────────────────────────────┘

  ┌──────────────┬───────────────────────────┬─────────────────────────────┬─────────────────────────────────┬────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │  label       │  folder                   │            file             │                       function  │  message                                                                                                                   │
  ╞══════════════╪═══════════════════════════╪═════════════════════════════╪═════════════════════════════════╪════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╡
  │  🔸  Log:    │  /hh/gateway/             │         gateway.py          │         _initialize_connection  │  Standard connection type selected                                                                                         │
  │  🔸  Log:    │  /hh/deploy/              │          utils.py           │         detect_project_context  │  Detecting project context                                                                                                 │
  │  🔸  Log:    │  /hh/deploy/              │          utils.py           │         detect_project_context  │  Found project: henhouse at /henhouse                                                                                      │
  │  🔸  Log:    │  /hh/gateway/connection/  │        connection.py        │                      _load_dsn  │  DSN loaded from config: /home/lee/.henhouse.cnf, host=localhost, database=henhouse                                        │
  │  🔸  Log:    │  /hh/gateway/connection/  │        connection.py        │        _detect_user_tier_level  │  Detected tier: root (index 3 → level 4)                                                                                   │
  │  🔸  Log:    │  /hh/gateway/connection/  │        connection.py        │        _detect_user_tier_level  │  User tier level: 4                                                                                                        │
  │  🔸  Log:    │  /hh/gateway/connection/  │        connection.py        │                      _load_dsn  │  DSN loaded from config: /home/lee/.henhouse.cnf, host=localhost, database=henhouse                                        │
  │  🔸  Log:    │  /hh/gateway/connection/  │        connection.py        │                     initialize  │  Main database connection opened: host=localhost, database=henhouse                                                        │
  │  🔸  Log:    │  /hh/gateway/connection/  │        connection.py        │                     initialize  │  Cache database connection opened: host=localhost, database=henhouse_cache                                                 │
  │  🔸  Log:    │  /hh/gateway/connection/  │        connection.py        │                     initialize  │  History database connection skipped (not yet implemented)                                                                 │
  │  🔸  Log:    │  /hh/gateway/connection/  │        connection.py        │                     initialize  │  All database connections initialized successfully                                                                         │
  │  🔸  Log:    │  /hh/gateway/response/    │         response.py         │                       __init__  │  Response initialized with empty buffer                                                                                    │
  │  🐛  Debug:  │  /hh/gateway/response/    │         response.py         │            set_user_tier_level  │  User tier level detected: 4 (root)                                                                                        │
  │  🔸  Log:    │  /hh/gateway/response/    │         response.py         │            set_user_tier_level  │  Set user tier level: 4                                                                                                    │
  │  🔸  Log:    │  /hh/gateway/             │         gateway.py          │           _initialize_response  │  Set user tier level 4 in response                                                                                         │
  │  🔸  Log:    │  /hh/gateway/             │         gateway.py          │           _initialize_response  │  Initialized parser response handler: hh.gateway.response.response_parser.ResponseParser                                   │
  │  🔸  Log:    │  /hh/gateway/system/      │       file_system.py        │                       __init__  │  FileSystem initialized (OS: ubuntu, dry_run=False)                                                                        │
  │  🔸  Log:    │  /hh/gateway/system/      │     process_manager.py      │                       __init__  │  ProcessManager initialized (OS: linux)                                                                                    │
  │  🔸  Log:    │  /hh/gateway/registry/    │          cache.py           │    discover_base_registrations  │  Found base cache with 5 backends and 103 commands                                                                         │
  │  🔸  Log:    │  /hh/gateway/registry/    │          cache.py           │           check_command_exists  │  Command 'dependency_list' exists: True                                                                                    │
  │  🔸  Log:    │  /hh/gateway/registry/    │          cache.py           │    discover_base_registrations  │  Found base cache with 5 backends and 103 commands                                                                         │
  │  🔸  Log:    │  /hh/gateway/registry/    │          cache.py           │           check_backend_exists  │  Backend 'parser' exists: True                                                                                             │
  │  🔸  Log:    │  /hh/gateway/registry/    │         registry.py         │                      decorator  │  register_command buffering 'dependency_list' from 'hh.gateway.system.dependency_list' (action_args=None)                  │
  │  🔸  Log:    │  /hh/gateway/registry/    │         registry.py         │                inner_decorator  │  Registered action: dependency_list -> hh.gateway.system.dependency_list.dependency_list                                   │
  │  🔸  Log:    │  /hh/gateway/registry/    │         registry.py         │                inner_decorator  │  Registered parser: dependency_list -> hh.gateway.system.dependency_list.dependency_list_parser                            │
  │  🔸  Log:    │  /hh/gateway/registry/    │          cache.py           │       check_command_in_backend  │  Found command 'dependency_list' in backend 'parser' cache                                                                 │
  │  🔸  Log:    │  /hh/gateway/registry/    │         registry.py         │                       __init__  │  Stored backend handler info for 'dependency_list': hh.gateway.system.dependency_list.dependency_list_parser               │
  │  🔸  Log:    │  /hh/gateway/registry/    │         registry.py         │                 select_backend  │  Found backend 'parser' with function: 'hh.gateway.registry.registry.backend_stub'                                         │
  │  🔸  Log:    │  /hh/gateway/registry/    │          cache.py           │       check_command_in_backend  │  Found command 'dependency_list' in backend 'action' cache                                                                 │
  │  🔸  Log:    │  /hh/gateway/registry/    │         registry.py         │                 select_command  │  Found command 'dependency_list' from action cache with function 'hh.gateway.system.dependency_list.dependency_list'       │
  │  🔸  Log:    │  /hh/gateway/             │         gateway.py          │        _configure_debug_module  │  Debug module configuration completed                                                                                      │
  │  🔸  Log:    │  /hh/gateway/             │         gateway.py          │                       dispatch  │  Gateway initialization completed, dispatching...                                                                          │
  │  🔸  Log:    │  /hh/gateway/registry/    │         registry.py         │             load_action_module  │  Action module loaded: 'hh.gateway.system.dependency_list' with function: 'dependency_list'                                │
  │  🔸  Log:    │  /hh/gateway/             │         gateway.py          │                       dispatch  │  Action module loaded: hh.gateway.system.dependency_list                                                                   │
  │  🔸  Log:    │  /hh/gateway/registry/    │         registry.py         │            load_backend_module  │  Backend module loaded: 'hh.gateway.system.dependency_list' with function: 'dependency_list_parser'                        │
  │  🔸  Log:    │  /hh/gateway/             │         gateway.py          │                       dispatch  │  Backend module loaded: hh.gateway.system.dependency_list                                                                  │
  │  🔸  Log:    │  /hh/gateway/             │         gateway.py          │                       dispatch  │  Starting action execution: hh.gateway.system.dependency_list.dependency_list                                              │
  │  🔸  Log:    │  /hh/gateway/system/      │     dependency_list.py      │  _scan_and_import_dependencies  │  Imported hh.gateway.connection.connection for dependency registration                                                     │
  │  🔸  Log:    │  /hh/gateway/system/      │     dependency_list.py      │  _scan_and_import_dependencies  │  Imported hh.gateway.system.process_manager for dependency registration                                                    │
  │  🔸  Log:    │  /hh/gateway/system/      │     dependency_list.py      │  _scan_and_import_dependencies  │  Imported hh.gateway.system.dependency_list for dependency registration                                                    │
  │  🔸  Log:    │  /hh/gateway/system/      │     dependency_list.py      │  _scan_and_import_dependencies  │  Imported hh.gateway.system.dependency for dependency registration                                                         │
  │  🔸  Log:    │  /hh/gateway/system/      │     dependency_list.py      │  _scan_and_import_dependencies  │  Imported hh.gateway.system.file_system for dependency registration                                                        │
  │  🔸  Log:    │  /hh/gateway/system/      │     dependency_list.py      │  _scan_and_import_dependencies  │  Imported hh.image.utils for dependency registration                                                                       │
  │  🔸  Log:    │  /hh/gateway/system/      │     dependency_list.py      │  _scan_and_import_dependencies  │  Imported hh.source_code_file.source_code_file_content for dependency registration                                         │
  │  🔸  Log:    │  /hh/gateway/system/      │     dependency_list.py      │                dependency_list  │  Checked 6 dependencies, all_available=True                                                                                │
  │  🔸  Log:    │  /hh/gateway/response/    │      json_standard.py       │                success_payload  │  Created success payload with 4 data keys                                                                                  │
  │  🔸  Log:    │  /hh/gateway/response/    │         response.py         │            set_action_response  │  Set action response: 676 characters                                                                                       │
  │  🔸  Log:    │  /hh/gateway/             │         gateway.py          │                       dispatch  │  Action execution completed successfully in 0.040s                                                                         │
  │  🔸  Log:    │  /hh/gateway/response/    │         response.py         │            has_action_response  │  Has action response: True                                                                                                 │
  │  🔸  Log:    │  /hh/gateway/             │         gateway.py          │                       dispatch  │  Starting backend execution: hh.gateway.system.dependency_list.dependency_list_parser                                      │
  │  🔸  Log:    │  /hh/gateway/response/    │         response.py         │            get_action_response  │  Retrieved action response: <class 'dict'>                                                                                 │
  │  🔸  Log:    │  /hh/render/              │      render_parser.py       │           render_parser_header  │  Parser backend detected - using CLI header renderer                                                                       │
  │  🔸  Log:    │  /hh/deploy/cache/        │  cache_cleanup_registry.py  │                      decorator  │  Registered cache cleanup: config_registry -> hh.render.config.config_registry.cleanup_config_registry_cache (cache_dir:   │
  │              │                           │                             │                                 │  hh/render/config/cache)                                                                                                   │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │                      get_label  │  Label 'l_main_header' not in hot cache, checking cold cache                                                               │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │  discover_config_registrations  │  Found config registry cache with 403 icons and 510 labels (last scan: 222.6s ago)                                         │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │                      get_label  │  Found label 'l_main_header' in cold cache from hh.render.config.config_labels, updated hot cache                          │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │                       get_icon  │  Icon 'tab' not in hot cache, checking cold cache                                                                          │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │  discover_config_registrations  │  Found config registry cache with 403 icons and 510 labels (last scan: 222.6s ago)                                         │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │                       get_icon  │  Found icon 'tab' in cold cache from hh.render.config.config_labels, updated hot cache                                     │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │                       get_icon  │  Icon 'blank_emoji' not in hot cache, checking cold cache                                                                  │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │  discover_config_registrations  │  Found config registry cache with 403 icons and 510 labels (last scan: 222.6s ago)                                         │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │                       get_icon  │  Found icon 'blank_emoji' in cold cache from hh.render.config.config_labels, updated hot cache                             │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │                      get_label  │  Label 'l_dependency_list' not in hot cache, checking cold cache                                                           │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │  discover_config_registrations  │  Found config registry cache with 403 icons and 510 labels (last scan: 222.6s ago)                                         │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │                      get_label  │  Found label 'l_dependency_list' in cold cache from hh.gateway.registry.config_labels, updated hot cache                   │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │                       get_icon  │  Found icon 'tab' in hot cache                                                                                             │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │                       get_icon  │  Found icon 'blank_emoji' in hot cache                                                                                     │
  │  🔸  Log:    │  /hh/render/              │      render_parser.py       │           render_parser_header  │  Added main header:   🏠 Henhouse:                                                                                         │
  │  🔸  Log:    │  /hh/render/              │      render_parser.py       │           render_parser_header  │  Added sub header:   Dependency List:                                                                                      │
  │  🔸  Log:    │  /hh/render/              │      render_parser.py       │           render_parser_header  │  Generated header with 2 parts (header_id= stored but not used)                                                            │
  │  🔸  Log:    │  /hh/render/              │          render.py          │                finalize_output  │  Finalized output: 3 input lines -> 3 output lines                                                                         │
  │  🔸  Log:    │  /hh/render/              │          render.py          │                   render_block  │  Rendering block: 7 rows, table_class=standard, block_type=list, table_id=                                                 │
  │  🔸  Log:    │  /hh/render/              │      render_parser.py       │          render_flexible_table  │  Rendering flexible table: 7 rows, table_class=standard                                                                    │
  │  🔸  Log:    │  /hh/render/              │      render_parser.py       │          render_flexible_table  │  Identified columns: ['label', 'info', 'col_b']                                                                            │
  │  🔸  Log:    │  /hh/render/              │      render_parser.py       │          render_flexible_table  │  Set final column 'col_b' width and overflow                                                                               │
  │  🔸  Log:    │  /hh/render/              │      render_parser.py       │          render_flexible_table  │  Applied table overrides: {'margin_l': 4}                                                                                  │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │                       get_icon  │  Icon 'dependency_header' not in hot cache, checking cold cache                                                            │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │  discover_config_registrations  │  Found config registry cache with 403 icons and 510 labels (last scan: 222.6s ago)                                         │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │                       get_icon  │  Found icon 'dependency_header' in cold cache from hh.gateway.registry.config_labels, updated hot cache                    │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │                      get_label  │  Label 'l_dependency_header' not in hot cache, checking cold cache                                                         │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │  discover_config_registrations  │  Found config registry cache with 403 icons and 510 labels (last scan: 222.6s ago)                                         │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │                      get_label  │  Found label 'l_dependency_header' in cold cache from hh.gateway.registry.config_labels, updated hot cache                 │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │                       get_icon  │  Found icon 'tab' in hot cache                                                                                             │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │                       get_icon  │  Found icon 'blank_emoji' in hot cache                                                                                     │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │  discover_config_registrations  │  Found config registry cache with 403 icons and 510 labels (last scan: 222.6s ago)                                         │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │                      get_label  │  Label 'l_dependency_available' not in hot cache, checking cold cache                                                      │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │  discover_config_registrations  │  Found config registry cache with 403 icons and 510 labels (last scan: 222.6s ago)                                         │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │                      get_label  │  Found label 'l_dependency_available' in cold cache from hh.gateway.registry.config_labels, updated hot cache              │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │                      get_label  │  Found label 'l_dependency_available' in hot cache                                                                         │
  │  🔸  Log:    │  /hh/render/config/       │     config_registry.py      │                      get_label  │  Found label 'l_dependency_available' in hot cache                                                                         │
  │  🔸  Log:    │  /hh/render/              │      render_parser.py       │          render_flexible_table  │  Rendered flexible table with 7 rows                                                                                       │
  │  🔸  Log:    │  /hh/render/              │          render.py          │                finalize_output  │  Finalized output: 2 input lines -> 2 output lines                                                                         │
  │  🔸  Log:    │  /hh/gateway/response/    │         response.py         │                     add_output  │  Added output:                                                                                                             │
  │              │                           │                             │                                 │    🏠 Henhouse:   Dependency List:                                                                                         │
  │              │                           │                             │                                 │                                                                                                                            │
  │              │                           │                             │                                 │      ┌──────────────────────────┬────────────────┬──────────────────────────────┐                                          │
  │              │                           │                             │                                 │      │ 📦  Dependencies         │ 6 dependencies │ required by                  │                                          │
  │              │                           │                             │                                 │      ╞══════════════════════════╪════════════════╪══════════════════════════════╡                                          │
  │              │                           │                             │                                 │      │ ✅  Dependency Installed │ grp            │ process_manager              │                                          │
  │              │                           │                             │                                 │      │ ✅  Dependency Installed │ pillow         │ utils                        │                                          │
  │              │                           │                             │                                 │      │ ✅  Dependency Installed │ psutil         │ process_manager              │                                          │
  │              │                           │                             │                                 │      │ ✅  Dependency Installed │ pwd            │ file_system, process_manager │                                          │
  │              │                           │                             │                                 │      │ ✅  Dependency Installed │ pygments       │ source_code_file_content     │                                          │
  │              │                           │                             │                                 │      │ ✅  Dependency Installed │ pymysql        │ connection                   │                                          │
  │              │                           │                             │                                 │      └──────────────────────────┴────────────────┴──────────────────────────────┘                                          │
  │  🔸  Log:    │  /hh/gateway/             │         gateway.py          │                       dispatch  │  Backend execution completed successfully in 0.040s                                                                        │
  │  🔸  Log:    │  /hh/gateway/             │         gateway.py          │                _process_errors  │  Error check result: False                                                                                                 │
  │  🔸  Log:    │  /hh/gateway/             │         gateway.py          │                _process_errors  │  No errors detected                                                                                                        │
  │  🔸  Log:    │  /hh/gateway/             │         gateway.py          │                        _commit  │  Starting commit process...                                                                                                │
  │  🔸  Log:    │  /hh/gateway/             │         gateway.py          │                        _commit  │  Committing file operations...                                                                                             │
  │  🔸  Log:    │  /hh/gateway/system/      │       file_system.py        │                         commit  │  FileSystem commit starting...                                                                                             │
  │  🔸  Log:    │  /hh/gateway/system/      │       file_system.py        │                         commit  │  No file operations to execute                                                                                             │
  │  🔸  Log:    │  /hh/gateway/             │         gateway.py          │                        _commit  │  Refreshing stale image caches...                                                                                          │
  │  🔸  Log:    │  /hh/image/               │      image_registry.py      │     refresh_stale_image_caches  │  No images in hot cache to refresh                                                                                         │
  │  🔸  Log:    │  /hh/gateway/             │         gateway.py          │                        _commit  │  Refreshing stale file caches...                                                                                           │
  │  🔸  Log:    │  /hh/file/                │      file_registry.py       │      refresh_stale_file_caches  │  No files in hot cache to refresh                                                                                          │
  │  🔸  Log:    │  /hh/gateway/             │         gateway.py          │                        _commit  │  Refreshing stale page caches...                                                                                           │
  │  🔸  Log:    │  /hh/page/                │      page_registry.py       │      refresh_stale_page_caches  │  No pages in hot cache to refresh                                                                                          │
  │  🔸  Log:    │  /hh/gateway/             │         gateway.py          │                        _commit  │  Committing database transactions...                                                                                       │
  │  🔸  Log:    │  /hh/gateway/connection/  │        connection.py        │                         commit  │  No transaction to commit                                                                                                  │
  │  🔸  Log:    │  /hh/gateway/             │         gateway.py          │                        _commit  │  Commit process completed                                                                                                  │
  │  🔸  Log:    │  /hh/gateway/             │         gateway.py          │                       dispatch  │  Closing database connections...                                                                                           │
  │  🔸  Log:    │  /hh/gateway/connection/  │        connection.py        │                          close  │  Starting connection cleanup...                                                                                            │
  │  🔸  Log:    │  /hh/gateway/connection/  │        connection.py        │                          close  │  Cache database connection closed                                                                                          │
  │  🔸  Log:    │  /hh/gateway/connection/  │        connection.py        │                          close  │  Main database connection closed                                                                                           │
  │  🔸  Log:    │  /hh/gateway/connection/  │        connection.py        │                          close  │  All database connections closed successfully                                                                              │
  └──────────────┴───────────────────────────┴─────────────────────────────┴─────────────────────────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Note**: The `-log` flag provides detailed debug output showing the Gateway execution flow, including connection initialization, registry lookups, action execution, and backend rendering.

## System Registry Commands

### Class List

```powershell
PS C:\Users\lee\Desktop\henhouse> hen class-list

  🏠 Henhouse:   Page Class Registry

    ┌──────────────────┬──────────────────┬───────────┬──────────────────────────────────────────┐
    │                  │ Class            │ Status    │ Module                                   │
    ╞══════════════════╪══════════════════╪═══════════╪══════════════════════════════════════════╡
    │ ✅  Loaded Class │ mcp_action       │ ✅ Loaded │ hh.mcp_action_request.mcp_action_request │
    │ ✅  Loaded Class │ mcp_request      │ ✅ Loaded │ hh.mcp_request.mcp_request               │
    │ ✅  Loaded Class │ page             │ ✅ Loaded │ hh.page.page                             │
    │ ✅  Loaded Class │ source_code_file │ ✅ Loaded │ hh.source_code_file.source_code_file     │
    │ ✅  Loaded Class │ work_docket      │ ✅ Loaded │ hh.work_docket.work_docket               │
    └──────────────────┴──────────────────┴───────────┴──────────────────────────────────────────┘
```

### Backend List

```powershell
PS C:\Users\lee\Desktop\henhouse> hen backend-list

  🏠 Henhouse:   Backend List:

    ┌─────────────┬─────────────┬─────────────────────────────────┐
    │ 5 commands  │ name        │ module                          │
    ╞═════════════╪═════════════╪═════════════════════════════════╡
    │ 🔲  Found:  │ action      │ hh.gateway.registry.action      │
    │ 🔲  Found:  │ http        │ hh.gateway.registry.http        │
    │ 🔲  Found:  │ maintenance │ hh.gateway.registry.maintenance │
    │ 🔲  Found:  │ mcp         │ hh.gateway.registry.mcp         │
    │ ✅  Loaded: │ parser      │ hh.gateway.registry.parser      │
    └─────────────┴─────────────┴─────────────────────────────────┘
```

### Action List

```powershell
PS C:\Users\lee\Desktop\henhouse> hen action-list

  🏠 Henhouse:   Action List:

    ┌─────────────┬──────────────────────────────┬─────────────────────────────────────────────────┐
    │ 88 commands │ name                         │ module                                          │
    ╞═════════════╪══════════════════════════════╪═════════════════════════════════════════════════╡
    │ ✅  Loaded: │ action_list                  │ hh.gateway.registry.utils                       │
    │ ✅  Loaded: │ backend_list                 │ hh.gateway.registry.utils                       │
    │ ✅  Loaded: │ command_list                 │ hh.gateway.registry.utils                       │
    │ ✅  Loaded: │ http_list                    │ hh.gateway.registry.utils                       │
    │ ✅  Loaded: │ maintenance_list             │ hh.gateway.registry.utils                       │
    │ ✅  Loaded: │ mcp_list                     │ hh.gateway.registry.utils                       │
    │ ✅  Loaded: │ parser_list                  │ hh.gateway.registry.utils                       │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ agent_list                   │ hh.agents.agent_list                            │
    │ 🔲  Found:  │ agent_purge                  │ hh.agents.agent_purge                           │
    │ 🔲  Found:  │ agent_tree                   │ hh.agents.agent_tree                            │
    │ 🔲  Found:  │ punch_in                     │ hh.agents.punch_in                              │
    │ 🔲  Found:  │ punch_out                    │ hh.agents.punch_out                             │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ gossip                       │ hh.agents.feed.gossip                           │
    │ 🔲  Found:  │ gulp                         │ hh.agents.feed.gulp                             │
    │ 🔲  Found:  │ peek                         │ hh.agents.feed.peek                             │
    │ 🔲  Found:  │ sip                          │ hh.agents.feed.sip                              │
    │ 🔲  Found:  │ subscription_runner          │ hh.agents.feed.subscription_runner              │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ answer                       │ hh.agents.onboarding.answer                     │
    │ 🔲  Found:  │ onboard                      │ hh.agents.onboarding.onboard                    │
    │ 🔲  Found:  │ promote                      │ hh.agents.onboarding.promote                    │
    │ 🔲  Found:  │ status                       │ hh.agents.onboarding.status                     │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ clear_cache                  │ hh.deploy.cache.clear_cache                     │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ add_db_users                 │ hh.deploy.db.add_db_users                       │
    │ 🔲  Found:  │ check_db                     │ hh.deploy.db.check_db                           │
    │ 🔲  Found:  │ clean_db                     │ hh.deploy.db.clean_db                           │
    │ 🔲  Found:  │ export_db                    │ hh.deploy.db.export_db                          │
    │ 🔲  Found:  │ import_db                    │ hh.deploy.db.import_db                          │
    │ 🔲  Found:  │ init_db                      │ hh.deploy.db.init_db                            │
    │ 🔲  Found:  │ init_homepage                │ hh.deploy.db.init_homepage                      │
    │ 🔲  Found:  │ remove_db_users              │ hh.deploy.db.remove_db_users                    │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ flask_start                  │ hh.deploy.flask.flask_start                     │
    │ 🔲  Found:  │ flask_status                 │ hh.deploy.flask.flask_status                    │
    │ 🔲  Found:  │ flask_stop                   │ hh.deploy.flask.flask_stop                      │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ pull_project                 │ hh.deploy.git.pull_project                      │
    │ 🔲  Found:  │ push_project                 │ hh.deploy.git.push_project                      │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ http_deploy                  │ hh.deploy.http.http_deploy                      │
    │ 🔲  Found:  │ http_deploy_ssl              │ hh.deploy.http.http_deploy_ssl                  │
    │ 🔲  Found:  │ http_remove                  │ hh.deploy.http.http_remove                      │
    │ 🔲  Found:  │ http_status                  │ hh.deploy.http.http_status                      │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ file_cache_refresh           │ hh.deploy.maint.file_cache_refresh              │
    │ 🔲  Found:  │ image_cache_refresh          │ hh.deploy.maint.image_cache_refresh             │
    │ 🔲  Found:  │ maintenance_jobs_status      │ hh.deploy.maint.maintenance_jobs_status         │
    │ 🔲  Found:  │ orphan_check                 │ hh.deploy.maint.orphan_checks                   │
    │ 🔲  Found:  │ page_cache_refresh           │ hh.deploy.maint.page_cache_refresh              │
    │ 🔲  Found:  │ regex_text                   │ hh.deploy.maint.regex_text                      │
    │ 🔲  Found:  │ update_maintenance_job       │ hh.deploy.maint.update_maintenance_job          │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ maintenance_start            │ hh.deploy.maintenance.maintenance_start         │
    │ 🔲  Found:  │ maintenance_status           │ hh.deploy.maintenance.maintenance_status        │
    │ 🔲  Found:  │ maintenance_stop             │ hh.deploy.maintenance.maintenance_stop          │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ deploy                       │ hh.deploy.srv.deploy                            │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ install                      │ hh.deploy.users.install                         │
    │ 🔲  Found:  │ install_cursor               │ hh.deploy.users.install_cursor                  │
    │ 🔲  Found:  │ uninstall                    │ hh.deploy.users.uninstall                       │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ upload_files                 │ hh.file.upload_file                             │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ dependency_list              │ hh.gateway.system.dependency_list               │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ help                         │ hh.help.help                                    │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ modify_caption               │ hh.image.modify_caption                         │
    │ 🔲  Found:  │ show_image                   │ hh.image.show_image                             │
    │ 🔲  Found:  │ upload_images                │ hh.image.upload_image                           │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ modify_mcp_action_request    │ hh.mcp_action_request.modify_mcp_action_request │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ modify_mcp_request           │ hh.mcp_request.modify_mcp_request               │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ add_image                    │ hh.page.add_image                               │
    │ 🔲  Found:  │ add_images                   │ hh.page.add_images                              │
    │ 🔲  Found:  │ add_page                     │ hh.page.add_page                                │
    │ 🔲  Found:  │ class_list                   │ hh.page.class_list                              │
    │ 🔲  Found:  │ copy_image                   │ hh.page.copy_image                              │
    │ 🔲  Found:  │ copy_images                  │ hh.page.copy_images                             │
    │ 🔲  Found:  │ copy_page                    │ hh.page.copy_page                               │
    │ 🔲  Found:  │ count_pages                  │ hh.page.count_pages                             │
    │ 🔲  Found:  │ delete_page                  │ hh.page.delete_page                             │
    │ 🔲  Found:  │ get_add_page_class_info      │ hh.page.get_add_page_class_info                 │
    │ 🔲  Found:  │ get_page                     │ hh.page.get_page                                │
    │ 🔲  Found:  │ get_text                     │ hh.page.get_text                                │
    │ 🔲  Found:  │ modify_name                  │ hh.page.modify_name                             │
    │ 🔲  Found:  │ modify_text                  │ hh.page.modify_text                             │
    │ 🔲  Found:  │ move_image                   │ hh.page.move_image                              │
    │ 🔲  Found:  │ move_images                  │ hh.page.move_images                             │
    │ 🔲  Found:  │ move_page                    │ hh.page.move_page                               │
    │ 🔲  Found:  │ remove_image                 │ hh.page.remove_image                            │
    │ 🔲  Found:  │ set_image_rank               │ hh.page.set_image_rank                          │
    │ 🔲  Found:  │ show_page                    │ hh.page.show_page                               │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ modify_file_path             │ hh.source_code_file.modify_file_path            │
    │ 🔲  Found:  │ modify_language              │ hh.source_code_file.modify_language             │
    ├─────────────┼──────────────────────────────┼─────────────────────────────────────────────────┤
    │ 🔲  Found:  │ modify_work_meta_remove_pair │ hh.work.modify_work_meta_remove_pair            │
    │ 🔲  Found:  │ modify_work_meta_set_all     │ hh.work.modify_work_meta_set_all                │
    │ 🔲  Found:  │ modify_work_meta_set_pair    │ hh.work.modify_work_meta_set_pair               │
    │ 🔲  Found:  │ modify_work_sort_order       │ hh.work.modify_work_sort_order                  │
    │ 🔲  Found:  │ modify_work_status           │ hh.work.modify_work_status                      │
    └─────────────┴──────────────────────────────┴─────────────────────────────────────────────────┘
```

### Command List

```powershell
PS C:\Users\lee\Desktop\henhouse> hen command-list

  🏠 Henhouse:   Command List:

    ┌──────────────┬──────────────────────────────┬─────────────────────────────────────────────────┬───────────────────────┐
    │ 103 commands │ name                         │ module                                          │ action_args           │
    ╞══════════════╪══════════════════════════════╪═════════════════════════════════════════════════╪═══════════════════════╡
    │ ✅  Loaded:  │ action_list                  │ hh.gateway.registry.utils                       │                       │
    │ ✅  Loaded:  │ backend_list                 │ hh.gateway.registry.utils                       │                       │
    │ ✅  Loaded:  │ command_list                 │ hh.gateway.registry.utils                       │                       │
    │ ✅  Loaded:  │ http_list                    │ hh.gateway.registry.utils                       │                       │
    │ ✅  Loaded:  │ maintenance_list             │ hh.gateway.registry.utils                       │                       │
    │ ✅  Loaded:  │ mcp_list                     │ hh.gateway.registry.utils                       │                       │
    │ ✅  Loaded:  │ parser_list                  │ hh.gateway.registry.utils                       │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ agent_list                   │ hh.agents.agent_list                            │                       │
    │ 🔲  Found:   │ agent_purge                  │ hh.agents.agent_purge                           │                       │
    │ 🔲  Found:   │ agent_tree                   │ hh.agents.agent_tree                            │                       │
    │ 🔲  Found:   │ punch_in                     │ hh.agents.punch_in                              │                       │
    │ 🔲  Found:   │ punch_out                    │ hh.agents.punch_out                             │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ gossip                       │ hh.agents.feed.gossip                           │                       │
    │ 🔲  Found:   │ gulp                         │ hh.agents.feed.gulp                             │                       │
    │ 🔲  Found:   │ peek                         │ hh.agents.feed.peek                             │                       │
    │ 🔲  Found:   │ sip                          │ hh.agents.feed.sip                              │                       │
    │ 🔲  Found:   │ subscribe_agent              │ hh.agents.feed.subscription_runner              │ agent, subscribe      │
    │ 🔲  Found:   │ subscribe_ask                │ hh.agents.feed.subscription_runner              │ ask, subscribe        │
    │ 🔲  Found:   │ subscribe_docket             │ hh.agents.feed.subscription_runner              │ docket, subscribe     │
    │ 🔲  Found:   │ subscribe_keyword            │ hh.agents.feed.subscription_runner              │ keyword, subscribe    │
    │ 🔲  Found:   │ subscribe_operator           │ hh.agents.feed.subscription_runner              │ operator, subscribe   │
    │ 🔲  Found:   │ subscribe_sidecar            │ hh.agents.feed.subscription_runner              │ sidecar, subscribe    │
    │ 🔲  Found:   │ subscribe_step               │ hh.agents.feed.subscription_runner              │ step, subscribe       │
    │ 🔲  Found:   │ subscribe_task               │ hh.agents.feed.subscription_runner              │ task, subscribe       │
    │ 🔲  Found:   │ unsubscribe_agent            │ hh.agents.feed.subscription_runner              │ agent, unsubscribe    │
    │ 🔲  Found:   │ unsubscribe_ask              │ hh.agents.feed.subscription_runner              │ ask, unsubscribe      │
    │ 🔲  Found:   │ unsubscribe_docket           │ hh.agents.feed.subscription_runner              │ docket, unsubscribe   │
    │ 🔲  Found:   │ unsubscribe_keyword          │ hh.agents.feed.subscription_runner              │ keyword, unsubscribe  │
    │ 🔲  Found:   │ unsubscribe_operator         │ hh.agents.feed.subscription_runner              │ operator, unsubscribe │
    │ 🔲  Found:   │ unsubscribe_sidecar          │ hh.agents.feed.subscription_runner              │ sidecar, unsubscribe  │
    │ 🔲  Found:   │ unsubscribe_step             │ hh.agents.feed.subscription_runner              │ step, unsubscribe     │
    │ 🔲  Found:   │ unsubscribe_task             │ hh.agents.feed.subscription_runner              │ task, unsubscribe     │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ answer                       │ hh.agents.onboarding.answer                     │                       │
    │ 🔲  Found:   │ onboard                      │ hh.agents.onboarding.onboard                    │                       │
    │ 🔲  Found:   │ promote                      │ hh.agents.onboarding.promote                    │                       │
    │ 🔲  Found:   │ status                       │ hh.agents.onboarding.status                     │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ clear_cache                  │ hh.deploy.cache.clear_cache                     │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ add_db_users                 │ hh.deploy.db.add_db_users                       │                       │
    │ 🔲  Found:   │ check_db                     │ hh.deploy.db.check_db                           │                       │
    │ 🔲  Found:   │ clean_db                     │ hh.deploy.db.clean_db                           │                       │
    │ 🔲  Found:   │ export_db                    │ hh.deploy.db.export_db                          │                       │
    │ 🔲  Found:   │ import_db                    │ hh.deploy.db.import_db                          │                       │
    │ 🔲  Found:   │ init_db                      │ hh.deploy.db.init_db                            │                       │
    │ 🔲  Found:   │ init_homepage                │ hh.deploy.db.init_homepage                      │                       │
    │ 🔲  Found:   │ remove_db_users              │ hh.deploy.db.remove_db_users                    │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ flask_start                  │ hh.deploy.flask.flask_start                     │                       │
    │ 🔲  Found:   │ flask_status                 │ hh.deploy.flask.flask_status                    │                       │
    │ 🔲  Found:   │ flask_stop                   │ hh.deploy.flask.flask_stop                      │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ pull_project                 │ hh.deploy.git.pull_project                      │                       │
    │ 🔲  Found:   │ push_project                 │ hh.deploy.git.push_project                      │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ http_deploy                  │ hh.deploy.http.http_deploy                      │                       │
    │ 🔲  Found:   │ http_deploy_ssl              │ hh.deploy.http.http_deploy_ssl                  │                       │
    │ 🔲  Found:   │ http_remove                  │ hh.deploy.http.http_remove                      │                       │
    │ 🔲  Found:   │ http_status                  │ hh.deploy.http.http_status                      │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ file_cache_refresh           │ hh.deploy.maint.file_cache_refresh              │                       │
    │ 🔲  Found:   │ image_cache_refresh          │ hh.deploy.maint.image_cache_refresh             │                       │
    │ 🔲  Found:   │ maintenance_jobs_status      │ hh.deploy.maint.maintenance_jobs_status         │                       │
    │ 🔲  Found:   │ orphan_check                 │ hh.deploy.maint.orphan_checks                   │                       │
    │ 🔲  Found:   │ page_cache_refresh           │ hh.deploy.maint.page_cache_refresh              │                       │
    │ 🔲  Found:   │ regex_text                   │ hh.deploy.maint.regex_text                      │                       │
    │ 🔲  Found:   │ update_maintenance_job       │ hh.deploy.maint.update_maintenance_job          │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ maintenance_start            │ hh.deploy.maintenance.maintenance_start         │                       │
    │ 🔲  Found:   │ maintenance_status           │ hh.deploy.maintenance.maintenance_status        │                       │
    │ 🔲  Found:   │ maintenance_stop             │ hh.deploy.maintenance.maintenance_stop          │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ deploy                       │ hh.deploy.srv.deploy                            │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ install                      │ hh.deploy.users.install                         │                       │
    │ 🔲  Found:   │ install_cursor               │ hh.deploy.users.install_cursor                  │                       │
    │ 🔲  Found:   │ uninstall                    │ hh.deploy.users.uninstall                       │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ upload_files                 │ hh.file.upload_file                             │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ dependency_list              │ hh.gateway.system.dependency_list               │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ help                         │ hh.help.help                                    │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ modify_caption               │ hh.image.modify_caption                         │                       │
    │ 🔲  Found:   │ show_image                   │ hh.image.show_image                             │                       │
    │ 🔲  Found:   │ upload_images                │ hh.image.upload_image                           │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ modify_mcp_action_request    │ hh.mcp_action_request.modify_mcp_action_request │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ modify_mcp_request           │ hh.mcp_request.modify_mcp_request               │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ add_image                    │ hh.page.add_image                               │                       │
    │ 🔲  Found:   │ add_images                   │ hh.page.add_images                              │                       │
    │ 🔲  Found:   │ add_page                     │ hh.page.add_page                                │                       │
    │ 🔲  Found:   │ class_list                   │ hh.page.class_list                              │                       │
    │ 🔲  Found:   │ copy_image                   │ hh.page.copy_image                              │                       │
    │ 🔲  Found:   │ copy_images                  │ hh.page.copy_images                             │                       │
    │ 🔲  Found:   │ copy_page                    │ hh.page.copy_page                               │                       │
    │ 🔲  Found:   │ count_pages                  │ hh.page.count_pages                             │                       │
    │ 🔲  Found:   │ delete_page                  │ hh.page.delete_page                             │                       │
    │ 🔲  Found:   │ get_add_page_class_info      │ hh.page.get_add_page_class_info                 │                       │
    │ 🔲  Found:   │ get_page                     │ hh.page.get_page                                │                       │
    │ 🔲  Found:   │ get_text                     │ hh.page.get_text                                │                       │
    │ 🔲  Found:   │ modify_name                  │ hh.page.modify_name                             │                       │
    │ 🔲  Found:   │ modify_text                  │ hh.page.modify_text                             │                       │
    │ 🔲  Found:   │ move_image                   │ hh.page.move_image                              │                       │
    │ 🔲  Found:   │ move_images                  │ hh.page.move_images                             │                       │
    │ 🔲  Found:   │ move_page                    │ hh.page.move_page                               │                       │
    │ 🔲  Found:   │ remove_image                 │ hh.page.remove_image                            │                       │
    │ 🔲  Found:   │ set_image_rank               │ hh.page.set_image_rank                          │                       │
    │ 🔲  Found:   │ show_page                    │ hh.page.show_page                               │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ modify_file_path             │ hh.source_code_file.modify_file_path            │                       │
    │ 🔲  Found:   │ modify_language              │ hh.source_code_file.modify_language             │                       │
    ├──────────────┼──────────────────────────────┼─────────────────────────────────────────────────┼───────────────────────┤
    │ 🔲  Found:   │ modify_work_meta_remove_pair │ hh.work.modify_work_meta_remove_pair            │                       │
    │ 🔲  Found:   │ modify_work_meta_set_all     │ hh.work.modify_work_meta_set_all                │                       │
    │ 🔲  Found:   │ modify_work_meta_set_pair    │ hh.work.modify_work_meta_set_pair               │                       │
    │ 🔲  Found:   │ modify_work_sort_order       │ hh.work.modify_work_sort_order                  │                       │
    │ 🔲  Found:   │ modify_work_status           │ hh.work.modify_work_status                      │                       │
    └──────────────┴──────────────────────────────┴─────────────────────────────────────────────────┴───────────────────────┘
```

### HTTP List

```powershell
PS C:\Users\lee\Desktop\henhouse> hen http-list

  🏠 Henhouse:   HTTP List:

    ┌────────────┬────────────┬────────────────────────────┐
    │ 3 commands │ name       │ module                     │
    ╞════════════╪════════════╪════════════════════════════╡
    │ 🔲  Found: │ http_error │ hh.gateway.error.error     │
    ├────────────┼────────────┼────────────────────────────┤
    │ 🔲  Found: │ show_image │ hh.image.render_show_image │
    ├────────────┼────────────┼────────────────────────────┤
    │ 🔲  Found: │ show_page  │ hh.page.render_show_page   │
    └────────────┴────────────┴────────────────────────────┘
```

### Parser List

```powershell
PS C:\Users\lee\Desktop\henhouse> hen parser-list

  🏠 Henhouse:   Parser List:

    ┌──────────────┬──────────────────────────────┬──────────────────────────────────────────────────────┐
    │ 101 commands │ name                         │ module                                               │
    ╞══════════════╪══════════════════════════════╪══════════════════════════════════════════════════════╡
    │ ✅  Loaded:  │ backend_list                 │ hh.gateway.registry.render_command_list              │
    │ ✅  Loaded:  │ command_list                 │ hh.gateway.registry.render_command_list              │
    │ ✅  Loaded:  │ action_list                  │ hh.gateway.registry.utils                            │
    │ ✅  Loaded:  │ http_list                    │ hh.gateway.registry.utils                            │
    │ ✅  Loaded:  │ maintenance_list             │ hh.gateway.registry.utils                            │
    │ ✅  Loaded:  │ mcp_list                     │ hh.gateway.registry.utils                            │
    │ ✅  Loaded:  │ parser_list                  │ hh.gateway.registry.utils                            │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ agent_purge                  │ hh.agents.render_agent_purge                         │
    │ 🔲  Found:   │ agent_list                   │ hh.agents.render_agents                              │
    │ 🔲  Found:   │ agent_tree                   │ hh.agents.render_agents                              │
    │ 🔲  Found:   │ punch_in                     │ hh.agents.render_timeclock_punch                     │
    │ 🔲  Found:   │ punch_out                    │ hh.agents.render_timeclock_punch                     │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ gulp                         │ hh.agents.feed.render_gulp                           │
    │ 🔲  Found:   │ gossip                       │ hh.agents.feed.render_sip                            │
    │ 🔲  Found:   │ peek                         │ hh.agents.feed.render_sip                            │
    │ 🔲  Found:   │ sip                          │ hh.agents.feed.render_sip                            │
    │ 🔲  Found:   │ subscribe_agent              │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ subscribe_ask                │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ subscribe_docket             │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ subscribe_keyword            │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ subscribe_operator           │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ subscribe_sidecar            │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ subscribe_step               │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ subscribe_task               │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ unsubscribe_agent            │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ unsubscribe_ask              │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ unsubscribe_docket           │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ unsubscribe_keyword          │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ unsubscribe_operator         │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ unsubscribe_sidecar          │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ unsubscribe_step             │ hh.agents.feed.render_subscription                   │
    │ 🔲  Found:   │ unsubscribe_task             │ hh.agents.feed.render_subscription                   │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ answer                       │ hh.agents.onboarding.render_answer                   │
    │ 🔲  Found:   │ onboard                      │ hh.agents.onboarding.render_onboard                  │
    │ 🔲  Found:   │ promote                      │ hh.agents.onboarding.render_promote                  │
    │ 🔲  Found:   │ status                       │ hh.agents.onboarding.render_status                   │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ clear_cache                  │ hh.deploy.cache.render_clear_cache                   │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ add_db_users                 │ hh.deploy.db.render_add_db_users                     │
    │ 🔲  Found:   │ check_db                     │ hh.deploy.db.render_check_db                         │
    │ 🔲  Found:   │ clean_db                     │ hh.deploy.db.render_clean_db                         │
    │ 🔲  Found:   │ export_db                    │ hh.deploy.db.render_export_db                        │
    │ 🔲  Found:   │ import_db                    │ hh.deploy.db.render_import_db                        │
    │ 🔲  Found:   │ init_db                      │ hh.deploy.db.render_init_db                          │
    │ 🔲  Found:   │ init_homepage                │ hh.deploy.db.render_init_homepage                    │
    │ 🔲  Found:   │ remove_db_users              │ hh.deploy.db.render_remove_db_users                  │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ flask_start                  │ hh.deploy.flask.render_flask_start                   │
    │ 🔲  Found:   │ flask_status                 │ hh.deploy.flask.render_flask_status                  │
    │ 🔲  Found:   │ flask_stop                   │ hh.deploy.flask.render_flask_stop                    │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ pull_project                 │ hh.deploy.git.render_pull_project                    │
    │ 🔲  Found:   │ push_project                 │ hh.deploy.git.render_push_project                    │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ http_deploy                  │ hh.deploy.http.render_http_deploy                    │
    │ 🔲  Found:   │ http_deploy_ssl              │ hh.deploy.http.render_http_deploy_ssl                │
    │ 🔲  Found:   │ http_remove                  │ hh.deploy.http.render_http_remove                    │
    │ 🔲  Found:   │ http_status                  │ hh.deploy.http.render_http_status                    │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ file_cache_refresh           │ hh.deploy.maint.file_cache_refresh                   │
    │ 🔲  Found:   │ image_cache_refresh          │ hh.deploy.maint.image_cache_refresh                  │
    │ 🔲  Found:   │ maintenance_jobs_status      │ hh.deploy.maint.maintenance_jobs_status              │
    │ 🔲  Found:   │ orphan_check                 │ hh.deploy.maint.orphan_checks                        │
    │ 🔲  Found:   │ page_cache_refresh           │ hh.deploy.maint.page_cache_refresh                   │
    │ 🔲  Found:   │ regex_text                   │ hh.deploy.maint.regex_text                           │
    │ 🔲  Found:   │ update_maintenance_job       │ hh.deploy.maint.update_maintenance_job               │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ maintenance_start            │ hh.deploy.maintenance.render_maintenance_start       │
    │ 🔲  Found:   │ maintenance_status           │ hh.deploy.maintenance.render_maintenance_status      │
    │ 🔲  Found:   │ maintenance_stop             │ hh.deploy.maintenance.render_maintenance_stop        │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ deploy                       │ hh.deploy.srv.render_deploy                          │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ install                      │ hh.deploy.users.render_install                       │
    │ 🔲  Found:   │ install_cursor               │ hh.deploy.users.render_install_cursor                │
    │ 🔲  Found:   │ uninstall                    │ hh.deploy.users.render_uninstall                     │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ parser_error                 │ hh.gateway.error.error                               │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ dependency_list              │ hh.gateway.system.dependency_list                    │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ help                         │ hh.help.render_help                                  │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ modify_caption               │ hh.image.render_show_image                           │
    │ 🔲  Found:   │ show_image                   │ hh.image.render_show_image                           │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ modify_mcp_action_request    │ hh.mcp_action_request.render_show_mcp_action_request │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ modify_mcp_request           │ hh.mcp_request.render_show_mcp_request               │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ class_list                   │ hh.page.class_list                                   │
    │ 🔲  Found:   │ count_pages                  │ hh.page.render_count_pages                           │
    │ 🔲  Found:   │ delete_page                  │ hh.page.render_delete_page                           │
    │ 🔲  Found:   │ get_add_page_class_info      │ hh.page.render_get_add_page_class_info               │
    │ 🔲  Found:   │ get_page                     │ hh.page.render_get_page                              │
    │ 🔲  Found:   │ add_image                    │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ add_images                   │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ add_page                     │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ copy_image                   │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ copy_images                  │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ copy_page                    │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ modify_name                  │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ modify_text                  │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ move_image                   │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ move_images                  │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ move_page                    │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ remove_image                 │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ set_image_rank               │ hh.page.render_show_page                             │
    │ 🔲  Found:   │ show_page                    │ hh.page.render_show_page                             │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ modify_file_path             │ hh.source_code_file.render_show_source_code_file     │
    │ 🔲  Found:   │ modify_language              │ hh.source_code_file.render_show_source_code_file     │
    ├──────────────┼──────────────────────────────┼──────────────────────────────────────────────────────┤
    │ 🔲  Found:   │ modify_work_meta_remove_pair │ hh.work.render_show_work_page                        │
    │ 🔲  Found:   │ modify_work_meta_set_all     │ hh.work.render_show_work_page                        │
    │ 🔲  Found:   │ modify_work_meta_set_pair    │ hh.work.render_show_work_page                        │
    │ 🔲  Found:   │ modify_work_sort_order       │ hh.work.render_show_work_page                        │
    │ 🔲  Found:   │ modify_work_status           │ hh.work.render_show_work_page                        │
    └──────────────┴──────────────────────────────┴──────────────────────────────────────────────────────┘
```

### MCP List

```powershell
PS C:\Users\lee\Desktop\henhouse> hen mcp-list

  🏠 Henhouse:   MCP List:

    ┌─────────────┬──────────────────────────────┬─────────────────────────┐
    │ 66 commands │ name                         │ module                  │
    ╞═════════════╪══════════════════════════════╪═════════════════════════╡
    │ 🔲  Found:  │ mcp_error                    │ hh.gateway.error.error  │
    ├─────────────┼──────────────────────────────┼─────────────────────────┤
    │ 🔲  Found:  │ action_list                  │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ add_page                     │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ agent_list                   │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ agent_purge                  │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ agent_tree                   │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ answer                       │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ backend_list                 │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ command_list                 │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ copy_image                   │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ copy_images                  │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ copy_page                    │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ count_pages                  │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ delete_page                  │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ get_add_page_class_info      │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ get_page                     │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ get_text                     │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ gossip                       │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ gulp                         │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ help                         │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ http_list                    │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ mcp_list                     │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ modify_caption               │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ modify_file_path             │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ modify_language              │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ modify_mcp_action_request    │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ modify_mcp_request           │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ modify_name                  │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ modify_text                  │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ modify_work_meta_remove_pair │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ modify_work_meta_set_all     │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ modify_work_meta_set_pair    │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ modify_work_sort_order       │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ modify_work_status           │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ move_image                   │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ move_images                  │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ move_page                    │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ onboard                      │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ parser_list                  │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ peek                         │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ promote                      │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ punch_in                     │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ punch_out                    │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ remove_image                 │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ set_image_rank               │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ show_image                   │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ show_page                    │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ sip                          │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ status                       │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ subscribe_agent              │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ subscribe_ask                │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ subscribe_docket             │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ subscribe_keyword            │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ subscribe_operator           │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ subscribe_sidecar            │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ subscribe_step               │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ subscribe_task               │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ unsubscribe_agent            │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ unsubscribe_ask              │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ unsubscribe_docket           │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ unsubscribe_keyword          │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ unsubscribe_operator         │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ unsubscribe_sidecar          │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ unsubscribe_step             │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ unsubscribe_task             │ hh.gateway.registry.mcp │
    │ 🔲  Found:  │ upload_images                │ hh.gateway.registry.mcp │
    └─────────────┴──────────────────────────────┴─────────────────────────┘
```

### Maintenance List

```powershell
PS C:\Users\lee\Desktop\henhouse> hen maintenance-list

  🏠 Henhouse:   Maintenance List:

    ┌────────────┬─────────────────────────┬─────────────────────────────────┐
    │ 9 commands │ name                    │ module                          │
    ╞════════════╪═════════════════════════╪═════════════════════════════════╡
    │ 🔲  Found: │ maintenance_error       │ hh.gateway.error.error          │
    ├────────────┼─────────────────────────┼─────────────────────────────────┤
    │ 🔲  Found: │ file_cache_refresh      │ hh.gateway.registry.maintenance │
    │ 🔲  Found: │ image_cache_refresh     │ hh.gateway.registry.maintenance │
    │ 🔲  Found: │ maintenance_jobs_status │ hh.gateway.registry.maintenance │
    │ 🔲  Found: │ orphan_check            │ hh.gateway.registry.maintenance │
    │ 🔲  Found: │ page_cache_refresh      │ hh.gateway.registry.maintenance │
    │ 🔲  Found: │ regex_text              │ hh.gateway.registry.maintenance │
    │ 🔲  Found: │ tool_name               │ hh.gateway.registry.maintenance │
    │ 🔲  Found: │ update_maintenance_job  │ hh.gateway.registry.maintenance │
    └────────────┴─────────────────────────┴─────────────────────────────────┘

PS C:\Users\lee\Desktop\henhouse> 







