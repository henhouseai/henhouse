var infographicGlossaryData = {
  "glossary": {
    "gateway": {
      "title": "Gateway",
      "description": "The central orchestrator and state manager for the entire Henhouse system. It manages request/response objects, coordinates execution, handles errors, manages debugging, and provides consistent APIs for all subsystems.",
      "page_id": 238
    },
    "dispatch": {
      "title": "Dispatch",
      "description": "Main execution flow method that orchestrates the action-backend execution sequence through the gateway.",
      "page_id": 30
    },
    "response_object": {
      "title": "Response Object",
      "description": "The output assembly and error coordination system that collects, manages, and formats all response data from the system. Buffers output, stores action results, and manages error collections.",
      "page_id": 264
    },
    "request_object": {
      "title": "Request Object",
      "description": "The command-line argument parsing and validation system that converts raw input into structured, typed data. Provides parsed arguments, flags, and command information to the rest of the system.",
      "page_id": 263
    },
    "debug_system": {
      "title": "Debug System",
      "description": "The comprehensive debug system that provides sophisticated debugging capabilities, error handling, and system introspection through multiple specialized debug modules and filtering mechanisms.",
      "page_id": 260
    },
    "command_registry_term": {
      "title": "Command Registry",
      "description": "The registry system that manages command and backend handler discovery, validation, and dynamic loading.",
      "page_id": 262
    },
    "pages": {
      "title": "Pages",
      "description": "Hierarchical content pages that form the main content structure, with parent-child relationships.",
      "page_id": 241
    },
    "images": {
      "title": "Images",
      "description": "Image assets with multi-size instance management, linked to pages and stored with metadata.",
      "page_id": 240
    },
    "action_handler": {
      "title": "Action Handler",
      "description": "Business logic execution function registered with @register_action that implements command functionality.",
      "page_id": 37
    },
    "backend_handler": {
      "title": "Backend Handler",
      "description": "Presentation logic function registered with @register_parser, @register_http, or @register_mcp that formats action output.",
      "page_id": 38
    },
    "error_handler": {
      "title": "Error Handler",
      "description": "Error processing function that formats and displays error information for specific backend types.",
      "page_id": 39
    },
    "connection_decorators": {
      "title": "Connection Decorators",
      "description": "Database access decorators (@db_read, @db_write) that manage connection lifecycle and provide retry logic.",
      "page_id": 40
    },
    "register_action_decorator": {
      "title": "Register Action Decorator",
      "description": "@register_action decorator that registers business logic functions for command execution.",
      "page_id": 41
    },
    "register_command_decorator": {
      "title": "Register Command Decorator",
      "description": "@register_command decorator that registers command functions for CLI invocation.",
      "page_id": 42
    },
    "backend_registration_decorators": {
      "title": "Backend Registration Decorators",
      "description": "Decorator system for registering backend handlers: @register_parser for CLI, @register_http for HTTP, and @register_mcp for MCP backends.",
      "page_id": 43
    },
    "request_grammar": {
      "title": "Request Grammar",
      "description": "The grammar structure that defines how command-line arguments are parsed and organized into structured data.",
      "page_id": 44
    },
    "tp_grammar": {
      "title": "TP Grammar",
      "description": "Text processor grammar syntax for links, images, and decorators: [[links]], {{images}}, @decorators.",
      "page_id": 45
    },
    "parser_backend": {
      "title": "Parser Backend",
      "description": "Backend type for CLI output formatting, registered with @register_parser decorator.",
      "page_id": 46
    },
    "http_backend": {
      "title": "HTTP Backend",
      "description": "Backend type for web HTML output formatting, registered with @register_http decorator.",
      "page_id": 47
    },
    "mcp_backend": {
      "title": "MCP Backend",
      "description": "Backend type for Model Context Protocol AI agent integration, registered with @register_mcp decorator.",
      "page_id": 48
    },
    "flask_daemon": {
      "title": "Flask Daemon",
      "description": "Tier-specific Flask application instances that run as daemons, each bound to different ports and running as different Unix users for HTTP deployment.",
      "page_id": 49
    },
    "spawner_daemons": {
      "title": "Spawner Daemons",
      "description": "Four tier-specific daemon processes that spawn and manage agent worker processes.",
      "page_id": 50
    },
    "project_folders": {
      "title": "Project Folders",
      "description": "Directory structure and organization of project files, code, and assets in the deployment environment.",
      "page_id": 51
    },
    "server_deployment": {
      "title": "Server Deployment",
      "description": "Overall server deployment architecture and configuration for hosting Henhouse applications in production environments.",
      "page_id": 52
    },
    "database_server_setup": {
      "title": "Database Server Setup",
      "description": "Configuration and setup of database server infrastructure for Henhouse data persistence and management.",
      "page_id": 53
    },
    "http_server_setup": {
      "title": "HTTP Server Setup",
      "description": "Configuration and setup of HTTP server infrastructure including Nginx, TLS termination, and web-facing deployment.",
      "page_id": 54
    },
    "flask_daemon_deployment": {
      "title": "Flask Daemon Deployment",
      "description": "Tier-specific Flask application instances that run as daemons, each bound to different ports and running as different Unix users.",
      "page_id": 55
    },
    "web_user": {
      "title": "Web User",
      "description": "A user accessing the system via web browser interface.",
      "page_id": 56
    },
    "guest_web_user": {
      "title": "Guest Web User",
      "description": "An unauthenticated web user with minimal access permissions.",
      "page_id": 57
    },
    "verified_web_user": {
      "title": "Verified Web User",
      "description": "A web user that has been authenticated and verified with standard user permissions.",
      "page_id": 58
    },
    "admin_web_user": {
      "title": "Admin Web User",
      "description": "A web user with administrative privileges and elevated access permissions.",
      "page_id": 59
    },
    "root_web_user": {
      "title": "Root Web User",
      "description": "A web user with root-level privileges and full system access.",
      "page_id": 60
    },
    "guest_agent_spawn_daemon": {
      "title": "Guest Agent Spawn Daemon",
      "description": "Daemon process that spawns guest-level CLI agents with minimal access permissions for automated operations.",
      "page_id": 61
    },
    "verified_agent_spawn_daemon": {
      "title": "Verified Agent Spawn Daemon",
      "description": "Daemon process that spawns verified CLI agents with standard user permissions for automated operations.",
      "page_id": 62
    },
    "admin_agent_spawn_daemon": {
      "title": "Admin Agent Spawn Daemon",
      "description": "Daemon process that spawns admin-level CLI agents with elevated permissions for automated operations.",
      "page_id": 63
    },
    "root_agent_spawn_daemon": {
      "title": "Root Agent Spawn Daemon",
      "description": "Daemon process that spawns root-level CLI agents with full system access for automated operations.",
      "page_id": 64
    },
    "cli_agent": {
      "title": "CLI Agent",
      "description": "An automated agent accessing the system via command-line interface without human intervention.",
      "page_id": 65
    },
    "guest_cli_agent": {
      "title": "Guest CLI Agent",
      "description": "An unauthenticated CLI agent with minimal access permissions.",
      "page_id": 66
    },
    "verified_cli_agent": {
      "title": "Verified CLI Agent",
      "description": "A CLI agent that has been authenticated and verified with standard user permissions.",
      "page_id": 67
    },
    "admin_cli_agent": {
      "title": "Admin CLI Agent",
      "description": "A CLI agent with administrative privileges and elevated access permissions.",
      "page_id": 68
    },
    "root_cli_agent": {
      "title": "Root CLI Agent",
      "description": "A CLI agent with root-level privileges and full system access.",
      "page_id": 69
    },
    "database_connection": {
      "title": "Database Connection",
      "description": "Overall system for managing database access permissions and control across different user tiers and agent types.",
      "page_id": 70
    },
    "filesystem_access": {
      "title": "Filesystem Access",
      "description": "Overall system for managing filesystem access permissions and control across different user tiers and agent types.",
      "page_id": 71
    },
    "db_read_access": {
      "title": "DB Read",
      "description": "The level of permission granted for reading data from the database. Can range from limited (specific tables/columns) to full (all tables and schemas).",
      "page_id": 72
    },
    "db_write_access": {
      "title": "DB Write",
      "description": "The level of permission granted for writing, modifying, or deleting data in the database. May include restrictions on which tables can be modified, or limitations on schema changes.",
      "page_id": 73
    },
    "file_read_access": {
      "title": "File Read",
      "description": "The level of permission granted for reading files from the filesystem. Can range from limited (specific directories) to broad or full access across the project.",
      "page_id": 74
    },
    "file_write_access": {
      "title": "File Write",
      "description": "The level of permission granted for creating, modifying, or deleting files on the filesystem. May be restricted to specific folders or directories.",
      "page_id": 75
    },
    "deployment_system": {
      "title": "Deployment System",
      "description": "System for deploying Henhouse applications to production environments with tier-based isolation.",
      "page_id": 76
    },
    "commands": {
      "title": "Commands",
      "description": "User-invokable command functions registered with @register_command that execute business logic.",
      "page_id": 77
    },
    "actions": {
      "title": "Actions",
      "description": "Business logic execution functions that implement command functionality and return structured JSON data.",
      "page_id": 78
    },
    "backends": {
      "title": "Backends",
      "description": "Presentation layer handlers that format action response data for different output formats (CLI, HTTP, MCP).",
      "page_id": 79
    },
    "page_names": {
      "title": "Page Names",
      "description": "Unique name identifiers for pages used for navigation, linking, and reference in the page system.",
      "page_id": 80
    },
    "links": {
      "title": "Links",
      "description": "Page-to-page references parsed from page content and stored in the links database table.",
      "page_id": 81
    },
    "http_client": {
      "title": "HTTP Client",
      "description": "Subprocess entry point that executes gateway requests for HTTP deployment, spawned by Flask apps per request.",
      "page_id": 82
    },
    "mcp_client": {
      "title": "MCP Client",
      "description": "MCP protocol client for AI agent communication and integration.",
      "page_id": 83
    },
    "trace_in": {
      "title": "Trace In",
      "description": "Debug function that logs function entry, used for call stack tracing and execution flow analysis.",
      "page_id": 84
    },
    "trace_out": {
      "title": "Trace Out",
      "description": "Debug function that logs function exit, used for call stack tracing and execution flow analysis.",
      "page_id": 85
    },
    "log": {
      "title": "Log",
      "description": "Debug function for general operational messages at level 3.",
      "page_id": 86
    },
    "debug": {
      "title": "Debug",
      "description": "Debug function for detailed debugging information at level 4.",
      "page_id": 87
    },
    "warn": {
      "title": "Warn",
      "description": "Debug function for warning messages at level 5, always recorded regardless of debug level settings.",
      "page_id": 88
    },
    "debug_limit": {
      "title": "Debug Limit",
      "description": "Maximum number of debug messages shown per unique module/file/function combination before suppression.",
      "page_id": 89
    },
    "whitelist_filtering": {
      "title": "Whitelist Filtering",
      "description": "Debug filter that includes only modules matching specified folder/module patterns.",
      "page_id": 90
    },
    "graylist_filtering": {
      "title": "Graylist Filtering",
      "description": "Debug filter that includes only files matching specified filename patterns.",
      "page_id": 91
    },
    "blacklist_filtering": {
      "title": "Blacklist Filtering",
      "description": "Debug filter that excludes functions matching specified function name patterns.",
      "page_id": 92
    },
    "get_arg": {
      "title": "Get Arg",
      "description": "Gateway method to retrieve command argument values by name (string or integer arguments).",
      "page_id": 93
    },
    "is_no": {
      "title": "Is No",
      "description": "Gateway method to check if a flag is disabled via no-flags or no-groups.",
      "page_id": 94
    },
    "action_response": {
      "title": "Action Response",
      "description": "JSON data structure containing action execution results, stored in the response object.",
      "page_id": 95
    },
    "backend_response": {
      "title": "Backend Response",
      "description": "Formatted output from backend handlers that gets added to the response buffer for final output assembly.",
      "page_id": 96
    },
    "seed_data": {
      "title": "Seed Data",
      "description": "Arbitrary client seed payload emitted to HTML/clients by backends for client-side initialization and configuration.",
      "page_id": 97
    },
    "css_links": {
      "title": "CSS Links",
      "description": "Custom header CSS links added by decorators/modules to include stylesheets in the HTML response header.",
      "page_id": 98
    },
    "js_links": {
      "title": "JS Links",
      "description": "Custom header JavaScript script links added by decorators/modules to include scripts in the HTML response header.",
      "page_id": 99
    },
    "upper_content": {
      "title": "Upper Content",
      "description": "Explicit HTML layout field for legacy-structure compatibility, containing content displayed in the upper section of the page.",
      "page_id": 100
    },
    "lower_content": {
      "title": "Lower Content",
      "description": "Explicit HTML layout field for legacy-structure compatibility, containing content displayed in the lower section of the page.",
      "page_id": 101
    },
    "page_text": {
      "title": "Page Text",
      "description": "Explicit HTML layout field for legacy-structure compatibility, containing the main page text content.",
      "page_id": 102
    },
    "error_system": {
      "title": "Error System",
      "description": "The comprehensive error handling and rendering system that provides structured error display with field configurations and backend-specific error parsers. Coordinates error collection across all system layers.",
      "page_id": 103
    },
    "security": {
      "title": "Security",
      "description": "Security system and access control mechanisms for the Henhouse platform, including authentication, authorization, and privilege management.",
      "page_id": 104
    },
    "user_accounts": {
      "title": "User Accounts",
      "description": "User account management system for the Henhouse platform, including account creation, authentication, and user profile management.",
      "page_id": 105
    },
    "server": {
      "title": "Server",
      "description": "Server infrastructure and deployment environment for hosting Henhouse applications in production.",
      "page_id": 106
    },
    "project": {
      "title": "Project",
      "description": "Henhouse project structure and organization, including local development and server deployment repositories.",
      "page_id": 107
    },
    "local_project_repository": {
      "title": "Local Project Repository",
      "description": "Local development repository containing project source code, configuration, and assets for development work.",
      "page_id": 108
    },
    "server_project_repository": {
      "title": "Server Project Repository",
      "description": "Server-side repository containing project source code and configuration for deployment and production use.",
      "page_id": 109
    },
    "server_git_remote": {
      "title": "Server Git Remote",
      "description": "Git remote repository configuration on the server for synchronizing project code between local and server environments.",
      "page_id": 110
    },
    "server_deployed_project": {
      "title": "Server Deployed Project",
      "description": "Production-deployed project instance on the server, including configured services, databases, and runtime environment.",
      "page_id": 111
    },
    "server_push_pull_project": {
      "title": "Server Push/Pull Project",
      "description": "Process of pushing project changes from local development to server repository or pulling updates from server to local.",
      "page_id": 112
    },
    "local_push_pull_project": {
      "title": "Local Push/Pull Project",
      "description": "Process of pushing project changes from local development to remote repositories or pulling updates to local environment.",
      "page_id": 113
    },
    "project_guest_user": {
      "title": "Project Guest User",
      "description": "User account type with guest-level access permissions for a specific project, with minimal read-only access.",
      "page_id": 114
    },
    "project_verified_user": {
      "title": "Project Verified User",
      "description": "User account type with verified-level access permissions for a specific project, with standard user access and content management capabilities.",
      "page_id": 115
    },
    "project_admin_user": {
      "title": "Project Admin User",
      "description": "User account type with admin-level access permissions for a specific project, with elevated privileges for project management.",
      "page_id": 116
    },
    "project_root_user": {
      "title": "Project Root User",
      "description": "User account type with root-level access permissions for a specific project, with full system access and control.",
      "page_id": 117
    },
    "user_account_suffixes": {
      "title": "User Account Suffixes",
      "description": "Naming convention suffixes applied to user accounts to distinguish user types and access levels (e.g., guest, verified, admin, root).",
      "page_id": 118
    },
    "database_connection_credentials": {
      "title": "Database Connection Credentials",
      "description": "Authentication credentials and configuration parameters used to establish database connections, including username, password, host, and database name.",
      "page_id": 119
    },
    "http_access": {
      "title": "HTTP Access",
      "description": "HTTP access control and permission management system for web-based interactions and API endpoints in the Henhouse platform.",
      "page_id": 120
    },
    "respawing": {
      "title": "Respawing",
      "description": "Process of restarting agent worker processes by spawner daemons when they terminate or fail, ensuring continuous operation.",
      "page_id": 121
    },
    "watchdog_system": {
      "title": "Watchdog System",
      "description": "Monitoring system that ensures agent processes remain healthy and restarts them if needed.",
      "page_id": 122
    },
    "files": {
      "title": "Files",
      "description": "File storage and management system for project files stored in /srv/files/project folder. Users can upload files similar to image uploads for project assets and resources.",
      "page_id": 123
    },
    "context": {
      "title": "Context",
      "description": "Textual information that gets given to an LLM agent so that they understand how to use the Henhouse system and other parts of the project being worked on.",
      "page_id": 124
    },
    "watercooler_system": {
      "title": "Watercooler System",
      "description": "Informal communication and context sharing system for agents to exchange information, messages, and updates through watercooler channels.",
      "page_id": 125
    },
    "watercooler_messages": {
      "title": "Watercooler Messages",
      "description": "Informal communication channel for agents to share information and updates.",
      "page_id": 126
    },
    "watercooler_micrologs": {
      "title": "Watercooler Micrologs",
      "description": "Brief log entries in watercooler system with links to related agents, operators, keywords, dockets, tasks, and steps for context tracking.",
      "page_id": 127
    },
    "watercooler_microlog_agent_links": {
      "title": "Watercooler Microlog Agent Links",
      "description": "Links within watercooler micrologs that reference specific agents involved in operations or tasks.",
      "page_id": 128
    },
    "watercooler_microlog_operator_links": {
      "title": "Watercooler Microlog Operator Links",
      "description": "Links within watercooler micrologs that reference operators responsible for executing operations or tasks.",
      "page_id": 129
    },
    "watercooler_microlog_sidecar_links": {
      "title": "Watercooler Microlog Sidecar Links",
      "description": "Links within watercooler micrologs that reference sidecar processes or services associated with operations.",
      "page_id": 130
    },
    "watercooler_microlog_keyword_links": {
      "title": "Watercooler Microlog Keyword Links",
      "description": "Links within watercooler micrologs that reference keywords for categorizing and organizing context information.",
      "page_id": 131
    },
    "watercooler_microlog_docket_links": {
      "title": "Watercooler Microlog Docket Links",
      "description": "Links within watercooler micrologs that reference work dockets for organizing and tracking related tasks.",
      "page_id": 132
    },
    "watercooler_microlog_ask_links": {
      "title": "Watercooler Microlog Ask Links",
      "description": "Links within watercooler micrologs that reference ask operations or requests for information or actions.",
      "page_id": 133
    },
    "watercooler_microlog_task_links": {
      "title": "Watercooler Microlog Task Links",
      "description": "Links within watercooler micrologs that reference specific tasks within work dockets.",
      "page_id": 134
    },
    "watercooler_microlog_step_links": {
      "title": "Watercooler Microlog Step Links",
      "description": "Links within watercooler micrologs that reference individual steps within tasks.",
      "page_id": 135
    },
    "watercooler_queues": {
      "title": "Watercooler Queues",
      "description": "Queue system within watercooler for managing and delivering messages and context updates organized by entity type (agents, operators, sidecars, keywords, dockets, asks, tasks, steps).",
      "page_id": 136
    },
    "watercooler_agent_queue": {
      "title": "Watercooler Agent Queue",
      "description": "Queue within watercooler system for managing messages and updates related to specific agents.",
      "page_id": 137
    },
    "watercooler_operator_queue": {
      "title": "Watercooler Operator Queue",
      "description": "Queue within watercooler system for managing messages and updates related to specific operators.",
      "page_id": 138
    },
    "watercooler_sidecar_queue": {
      "title": "Watercooler Sidecar Queue",
      "description": "Queue within watercooler system for managing messages and updates related to sidecar processes or services.",
      "page_id": 139
    },
    "watercooler_keyword_queue": {
      "title": "Watercooler Keyword Queue",
      "description": "Queue within watercooler system for managing messages and updates organized by keywords.",
      "page_id": 140
    },
    "watercooler_docket_queue": {
      "title": "Watercooler Docket Queue",
      "description": "Queue within watercooler system for managing messages and updates related to work dockets.",
      "page_id": 141
    },
    "watercooler_ask_queue": {
      "title": "Watercooler Ask Queue",
      "description": "Queue within watercooler system for managing messages and updates related to ask operations or requests.",
      "page_id": 142
    },
    "watercooler_task_queue": {
      "title": "Watercooler Task Queue",
      "description": "Queue within watercooler system for managing messages and updates related to specific tasks.",
      "page_id": 143
    },
    "watercooler_step_queue": {
      "title": "Watercooler Step Queue",
      "description": "Queue within watercooler system for managing messages and updates related to individual steps within tasks.",
      "page_id": 144
    },
    "sipping": {
      "title": "Sipping",
      "description": "Process in watercooler system where agents consume or read messages and context updates from queues without removing them.",
      "page_id": 145
    },
    "onboarding": {
      "title": "Onboarding",
      "description": "Process of registering and configuring new agents in the system.",
      "page_id": 146
    },
    "bootstrap": {
      "title": "Bootstrap",
      "description": "Initial setup and configuration process for new agents during onboarding, providing essential system information and capabilities.",
      "page_id": 147
    },
    "required_reading": {
      "title": "Required Reading",
      "description": "Essential documentation and information that new agents must review during onboarding to understand system capabilities and workflows.",
      "page_id": 148
    },
    "onboarding_exams": {
      "title": "Onboarding Exams",
      "description": "Assessment tests or evaluations that new agents complete during onboarding to verify understanding of system operations and requirements.",
      "page_id": 149
    },
    "bootstrap_version_tracking": {
      "title": "Bootstrap Version Tracking",
      "description": "System for tracking and managing versions of bootstrap data and configurations used during agent onboarding to ensure consistency and updates.",
      "page_id": 150
    },
    "deployment_file_filtering_lists": {
      "title": "Deployment File Filtering Lists",
      "description": "Whitelist and blacklist configuration files that control which files are included or excluded during deployment to server environments.",
      "page_id": 151
    },
    "deploy_whitelist": {
      "title": "Deploy Whitelist",
      "description": "Configuration file specifying which files and directories are allowed to be deployed to the server during deployment operations.",
      "page_id": 152
    },
    "js_whitelist": {
      "title": "JS Whitelist",
      "description": "Configuration file specifying which JavaScript files are allowed to be deployed and served in the deployment environment.",
      "page_id": 153
    },
    "css_whitelist": {
      "title": "CSS Whitelist",
      "description": "Configuration file specifying which CSS stylesheet files are allowed to be deployed and served in the deployment environment.",
      "page_id": 154
    },
    "py_whitelist": {
      "title": "PY Whitelist",
      "description": "Configuration file specifying which Python files are allowed to be deployed to the server during deployment operations.",
      "page_id": 155
    },
    "misc_whitelist": {
      "title": "Misc Whitelist",
      "description": "Configuration file specifying which miscellaneous files are allowed to be deployed to the server during deployment operations.",
      "page_id": 156
    },
    "context_whitelist": {
      "title": "Context Whitelist",
      "description": "Configuration file specifying which context-related files or content are allowed in the context system and watercooler.",
      "page_id": 157
    },
    "context_blacklist": {
      "title": "Context Blacklist",
      "description": "Configuration file specifying which context-related files or content are excluded or blocked from the context system and watercooler.",
      "page_id": 158
    },
    "image_files": {
      "title": "Image Files",
      "description": "Image file assets stored in the files system, including multi-size instances managed with metadata and linked to pages.",
      "page_id": 159
    },
    "context_files": {
      "title": "Context Files",
      "description": "Files related to context system and watercooler messaging, including context data and communication artifacts.",
      "page_id": 160
    },
    "project_source_files": {
      "title": "Project Source Files",
      "description": "Source code and development files for the project, including Python modules, JavaScript, CSS, and other source assets.",
      "page_id": 161
    },
    "other_files": {
      "title": "Other Files",
      "description": "Miscellaneous files in the project that don't fall into specific categories like images, context, or source code.",
      "page_id": 162
    },
    "page_link_syntax": {
      "title": "Page Link Syntax",
      "description": "TP grammar syntax for creating page-to-page links using double square brackets: [[page_name]] or [[page_name|display text]].",
      "page_id": 163
    },
    "image_link_syntax": {
      "title": "Image Link Syntax",
      "description": "TP grammar syntax for creating image links using double curly braces: {{image_name}} or {{image_name|display text}}.",
      "page_id": 164
    },
    "image_syntax": {
      "title": "Image Syntax",
      "description": "TP grammar syntax for embedding images using double curly braces: {{image_name}}.",
      "page_id": 165
    },
    "decorator_syntax": {
      "title": "Decorator Syntax",
      "description": "TP grammar syntax for applying decorators using @ symbol: @decorator_name or @decorator_name{content}.",
      "page_id": 166
    },
    "page_link_override_syntax": {
      "title": "Page Link Override Syntax",
      "description": "TP grammar syntax for overriding default page link behavior with custom display text or formatting.",
      "page_id": 167
    },
    "image_link_override_syntax": {
      "title": "Image Link Override Syntax",
      "description": "TP grammar syntax for overriding default image link behavior with custom display text or formatting.",
      "page_id": 168
    },
    "image_id_syntax": {
      "title": "Image ID Syntax",
      "description": "TP grammar syntax for referencing images by their ID rather than name in image links and embeds.",
      "page_id": 169
    },
    "image_caption_override_syntax": {
      "title": "Image Caption Override Syntax",
      "description": "TP grammar syntax for overriding default image captions with custom text in image embeds and links.",
      "page_id": 170
    },
    "decorator_chaining": {
      "title": "Decorator Chaining",
      "description": "TP grammar feature allowing multiple decorators to be applied sequentially to the same content using @decorator1@decorator2{content} syntax.",
      "page_id": 171
    },
    "rendering_system": {
      "title": "Rendering System",
      "description": "System for rendering content in different formats including CLI tables, HTML tables, text processing, and configuration-driven display.",
      "page_id": 172
    },
    "cli_tables": {
      "title": "CLI Tables",
      "description": "Rendering system for generating formatted tables in command-line interface output with columns, rows, and borders.",
      "page_id": 173
    },
    "html_tables": {
      "title": "HTML Tables",
      "description": "Rendering system for generating HTML table elements with structure, styling, and formatting for web display.",
      "page_id": 174
    },
    "text_processing": {
      "title": "Text Processing",
      "description": "Rendering system for processing and transforming text content including TP grammar parsing, decorators, and formatting.",
      "page_id": 175
    },
    "config_system": {
      "title": "Config System",
      "description": "Centralized configuration management system providing access to icons, labels, table settings, and parse configuration.",
      "page_id": 176
    },
    "ic": {
      "title": "IC",
      "description": "Icon configuration setting or parameter in the config system for managing icon display and mappings.",
      "page_id": 177
    },
    "dc": {
      "title": "DC",
      "description": "Description configuration setting or parameter in the config system for managing description text display.",
      "page_id": 178
    },
    "icon_ini": {
      "title": "icon.ini",
      "description": "INI configuration file storing icon definitions and mappings for visual display elements.",
      "page_id": 179
    },
    "label_ini": {
      "title": "label.ini",
      "description": "INI configuration file storing label text definitions for headers, buttons, and display elements.",
      "page_id": 180
    },
    "no_icon": {
      "title": "No Icon",
      "description": "Configuration option or flag indicating that icons should not be displayed for specific elements or contexts.",
      "page_id": 181
    },
    "no_desc": {
      "title": "No Desc",
      "description": "Configuration option or flag indicating that descriptions should not be displayed for specific elements or contexts.",
      "page_id": 182
    },
    "no_label": {
      "title": "No Label",
      "description": "Configuration option or flag indicating that labels should not be displayed for specific elements or contexts.",
      "page_id": 183
    },
    "table_ini": {
      "title": "table.ini",
      "description": "INI configuration file storing table formatting settings including margins, padding, borders, and column configurations.",
      "page_id": 184
    },
    "error_types": {
      "title": "Error Types",
      "description": "Categories of errors in the error system: request, registry, action, backend, debug, connection, JSON, syntax, and link resolution errors.",
      "page_id": 185
    },
    "request_errors": {
      "title": "Request Errors",
      "description": "Error type for request parsing, validation, and command-line argument processing failures.",
      "page_id": 186
    },
    "registry_errors": {
      "title": "Registry Errors",
      "description": "Error type for handler discovery, validation, and loading failures in the registry system.",
      "page_id": 187
    },
    "action_errors": {
      "title": "Action Errors",
      "description": "Error type for business logic execution failures in action handlers.",
      "page_id": 188
    },
    "backend_errors": {
      "title": "Backend Errors",
      "description": "Error type for presentation logic failures in backend handlers (parser, HTTP, MCP).",
      "page_id": 189
    },
    "debug_errors": {
      "title": "Debug Errors",
      "description": "Error type for debug system failures and debug output generation issues.",
      "page_id": 190
    },
    "connection_errors": {
      "title": "Connection Errors",
      "description": "Error type for database connection failures, query execution errors, and connection lifecycle issues.",
      "page_id": 191
    },
    "json_errors": {
      "title": "JSON Errors",
      "description": "Error type for JSON parsing, serialization, and validation failures.",
      "page_id": 192
    },
    "syntax_errors": {
      "title": "Syntax Errors",
      "description": "Error type for syntax parsing failures in text processor, command parsing, or other syntax-based processing.",
      "page_id": 193
    },
    "link_resolution_errors": {
      "title": "Link Resolution Errors",
      "description": "Error type for failures in resolving page links, image links, or other reference links in the system.",
      "page_id": 194
    },
    "error_reporting": {
      "title": "Error Reporting",
      "description": "System for reporting errors by category to the error system, including methods for each error type (request_error, action_error, backend_error, etc.).",
      "page_id": 195
    },
    "error_logging": {
      "title": "Error Logging",
      "description": "System for logging errors to persistent storage and tracking error history, including error store management and error collection.",
      "page_id": 196
    },
    "error_rendering": {
      "title": "Error Rendering",
      "description": "System for formatting and displaying errors to users through backend-specific error handlers and parsers, with structured error display.",
      "page_id": 197
    },
    "agents": {
      "title": "Agents",
      "description": "Automated agent system for the Henhouse platform, including agent registration, onboarding, management, and context sharing through watercooler and context feeds.",
      "page_id": 198
    },
    "local_agents": {
      "title": "Local Agents",
      "description": "Agents running in the local development environment, as opposed to server-deployed agents or remote agents.",
      "page_id": 199
    },
    "debug_safe": {
      "title": "Debug Safe",
      "description": "Base debug rendering system providing filtering, color management, and safe rendering capabilities.",
      "page_id": 200
    },
    "debug_table": {
      "title": "Debug Table",
      "description": "Tabular debug rendering system that formats debug information as structured tables with safe mode context.",
      "page_id": 201
    },
    "debug_trace": {
      "title": "Debug Trace",
      "description": "Call stack tracing system that builds and renders hierarchical call stack trees from debug trace data.",
      "page_id": 202
    },
    "render_block": {
      "title": "Render Block",
      "description": "Main table rendering function with field configuration support for formatting structured data into tables.",
      "page_id": 203
    },
    "field_configs": {
      "title": "Field Configs",
      "description": "Field configuration system for defining table column structures, headers, formatting, and display options in table rendering.",
      "page_id": 204
    },
    "table_data": {
      "title": "Table Data",
      "description": "Structured data formatted for table rendering, including rows, columns, and metadata used by table rendering systems.",
      "page_id": 205
    },
    "render_flex_table": {
      "title": "Render Flex Table",
      "description": "Flexible table rendering function for CLI output that handles dynamic column widths and content alignment.",
      "page_id": 206
    },
    "hh_folder": {
      "title": "HH Folder",
      "description": "Main source code folder containing the core Henhouse system modules and components.",
      "page_id": 207
    },
    "help_folder": {
      "title": "Help Folder",
      "description": "Folder containing help documentation and assistance resources for the Henhouse system.",
      "page_id": 208
    },
    "help_command": {
      "title": "Help Command",
      "description": "Main help command entry point that registers as an action/command, retrieves topic and section from gateway, creates HelpQuery instances, and returns JSON-formatted help data."
    },
    "help_query": {
      "title": "Help Query",
      "description": "Query system that retrieves help content by topic and section, uses the help registry to look up files, handles special vs regular files, finds related child directories and sibling files, and formats help content as JSON output."
    },
    "help_registry": {
      "title": "Help Registry",
      "description": "Registry system that maintains an index of help topics and their sections, loads/saves from TSV cache files, rebuilds by scanning markdown files, and distinguishes between special (title matches directory) and regular help files."
    },
    "help_markdown_parser": {
      "title": "Markdown Parser",
      "description": "Parses markdown help files to extract sections and subsections, mapping headers to content buckets (summary, description, full_text) and returning section keys with line ranges for indexing."
    },
    "help_markdown_files": {
      "title": "Markdown File",
      "description": "Subfolder containing markdown help documentation files organized by topic, with sections and subsections for help content retrieval."
    },
    "agents_folder": {
      "title": "Agents Folder",
      "description": "Folder containing agent management system modules and agent-related functionality.",
      "page_id": 210
    },
    "config_folder": {
      "title": "Config Folder",
      "description": "Folder containing configuration system modules and configuration management functionality.",
      "page_id": 211
    },
    "deploy_folder": {
      "title": "Deploy Folder",
      "description": "Folder containing deployment system modules and deployment-related functionality.",
      "page_id": 212
    },
    "gateway_folder": {
      "title": "Gateway Folder",
      "description": "Folder containing gateway system modules and gateway orchestration functionality.",
      "page_id": 213
    },
    "image_folder": {
      "title": "Image Folder",
      "description": "Folder containing image management system modules and image-related functionality.",
      "page_id": 214
    },
    "page_folder": {
      "title": "Page Folder",
      "description": "Folder containing page management system modules and page-related functionality.",
      "page_id": 241
    },
    "render_system": {
      "title": "Render System",
      "description": "Comprehensive output formatting system that transforms structured data into formatted tables and text output.",
      "page_id": 216
    },
    "tp_folder": {
      "title": "TP Folder",
      "description": "Folder containing text processor system modules and text processing functionality.",
      "page_id": 217
    },
    "git_repositories": {
      "title": "Git Repositories",
      "description": "Git version control repositories used for managing project source code, including local development repositories and server-side repositories for deployment and synchronization.",
      "page_id": 220
    },
    "context_folder": {
      "title": "Context Folder",
      "description": "Folder containing context files that provide agents with information to understand how to use the Henhouse system and the project they're working on. Contains general purpose context for all agents and role-specific context files that serve as on-the-job training.",
      "page_id": 221
    },
    "convenience_scripts": {
      "title": "Convenience Scripts",
      "description": "Wrappers which allow the user to execute Henhouse command line functions with minimal keystrokes.",
      "page_id": 222
    },
    "other_project_files": {
      "title": "Other Project Files",
      "description": "Miscellaneous files in the project that don't fall into specific categories like images, context, or source code.",
      "page_id": 223
    },
    "custom_project_add_ins": {
      "title": "Custom Project Add-ins",
      "description": "Folder containing custom project-specific add-ins and extensions for the Henhouse system.",
      "page_id": 224
    },
    "registry": {
      "title": "Registry",
      "description": "The command registry that manages command and backend information with dynamic handler loading and validation. Provides handler discovery and resolution capabilities."
    },
    "get_gateway": {
      "title": "Get Gateway",
      "description": "Function to access the singleton gateway instance for system state and argument access."
    },
    "set_action_response": {
      "title": "Set Action Response",
      "description": "Gateway method to store structured JSON response data from action execution."
    },
    "get_action_response": {
      "title": "Get Action Response",
      "description": "Gateway method to retrieve action execution results for backend formatting."
    },
    "command_args": {
      "title": "Command Args",
      "description": "Parsed command-line arguments including strings, integers, flags, and no-flags."
    },
    "no_flags": {
      "title": "No Flags",
      "description": "System for disabling flags via --no- prefix or flag groups, allowing selective disabling of features."
    },
    "string_args": {
      "title": "String Args",
      "description": "Collection of string-type arguments parsed from command line input."
    },
    "int_args": {
      "title": "Int Args",
      "description": "Collection of integer-type arguments parsed from command line input."
    },
    "flag_args": {
      "title": "Flag Args",
      "description": "Collection of boolean flag arguments parsed from command line input."
    },
    "response_assembly": {
      "title": "Response Assembly",
      "description": "Process of combining backend output with error information and debug data into final formatted response."
    },
    "output_buffer": {
      "title": "Output Buffer",
      "description": "List of output strings collected from backend handlers for final response assembly."
    },
    "error_collections": {
      "title": "Error Collections",
      "description": "Separate error lists maintained for each system layer (request, registry, action, backend, debug, connection, JSON, syntax)."
    },
    "handler_discovery": {
      "title": "Handler Discovery",
      "description": "Process of discovering and registering action and backend handlers through decorator scanning and module loading."
    },
    "handler_resolution": {
      "title": "Handler Resolution",
      "description": "Process of locating and validating appropriate handlers for a given command and backend combination."
    },
    "error_coordination": {
      "title": "Error Coordination",
      "description": "Centralized management of errors across all system layers with proper categorization and reporting."
    },
    "error_state_tracking": {
      "title": "Error State Tracking",
      "description": "System for maintaining error state across different system layers and coordinating error reporting."
    },
    "request_error": {
      "title": "Request Error",
      "description": "Error type for request parsing and validation failures."
    },
    "action_error": {
      "title": "Action Error",
      "description": "Error type for business logic execution failures in action handlers."
    },
    "backend_error": {
      "title": "Backend Error",
      "description": "Error type for presentation logic failures in backend handlers."
    },
    "debug_registry_term": {
      "title": "Debug Registry",
      "description": "Centralized debug data collection and management system that captures, stores, and filters debug information."
    },
    "debug_levels": {
      "title": "Debug Levels",
      "description": "Multiple activation levels for debug output: trace, log, debug, and warn. Can be combined via CLI flags."
    },
    "tokenizer": {
      "title": "Tokenizer",
      "description": "The tokenization system that breaks down raw command-line strings into categorized tokens, detecting quote styles and classifying token types."
    },
    "token_classification": {
      "title": "Token Classification",
      "description": "Process of categorizing tokens as commands, flags, values, or special cases based on context and syntax rules."
    },
    "quote_detection": {
      "title": "Quote Detection",
      "description": "System for detecting and handling various quote styles (single, double) in command-line arguments."
    },
    "grammar_parser": {
      "title": "Grammar Parser",
      "description": "The orchestrator that coordinates the parsing pipeline, managing the flow from tokens to parsed grammar structure."
    },
    "request_parsing_pipeline": {
      "title": "Request Parsing Pipeline",
      "description": "The four-stage parsing process: tokenization, grammar parsing, semantic analysis, and request object construction."
    },
    "semantics": {
      "title": "Semantics",
      "description": "The semantic analysis stage that constructs the final Request object from parsed grammar, populating argument collections and applying defaults."
    },
    "request_object_construction": {
      "title": "Request Object Construction",
      "description": "Process of building the structured Request object with proper data types from parsed grammar structure."
    },
    "cache": {
      "title": "Cache",
      "description": "The sophisticated caching and discovery system that provides performance optimization by avoiding repeated file system scans and module imports. Stores discovered registrations in JSON files."
    },
    "json_cache_files": {
      "title": "JSON Cache Files",
      "description": "Cached discovery results stored in JSON format to avoid repeated scanning of decorators and module imports."
    },
    "decorator_scanning": {
      "title": "Decorator Scanning",
      "description": "Process of scanning the filesystem for decorator usage patterns to discover registered handlers."
    },
    "base_registrations": {
      "title": "Base Registrations",
      "description": "Cached base command and backend registration lists from initial discovery operations."
    },
    "backend_specific_registrations": {
      "title": "Backend Specific Registrations",
      "description": "Cached handler registrations for specific backend types discovered during scanning."
    },
    "dynamic_module_loading": {
      "title": "Dynamic Module Loading",
      "description": "Runtime loading of handler modules with validation, triggered when handlers are needed."
    },
    "module_validation": {
      "title": "Module Validation",
      "description": "Process of validating that cached module paths are still importable and handler functions exist."
    },
    "data_flow": {
      "title": "Data Flow",
      "description": "The bidirectional exchange of data between components, typically involving argument access and response building."
    },
    "creates_request": {
      "title": "Creates Request",
      "description": "Process of creating and initializing request objects from raw input data."
    },
    "argument_access": {
      "title": "Argument Access",
      "description": "Mechanism for accessing parsed command arguments through gateway methods like get_arg and is_no."
    },
    "get_arg_calls": {
      "title": "Get Arg Calls",
      "description": "Specific calls to gateway.get_arg() method to retrieve argument values by name."
    },
    "is_no_checks": {
      "title": "Is No Checks",
      "description": "Specific calls to gateway.is_no() method to check if flags are disabled."
    },
    "creates_response": {
      "title": "Creates Response",
      "description": "Process of creating and initializing response objects for output assembly."
    },
    "error_collection": {
      "title": "Error Collection",
      "description": "Process of gathering and organizing error information from different system layers."
    },
    "final_assembly": {
      "title": "Final Assembly",
      "description": "Process of combining all output components (backend output, errors, debug) into the final formatted response."
    },
    "uses_registry": {
      "title": "Uses Registry",
      "description": "Gateway operation of accessing the registry to discover and load appropriate handlers."
    },
    "loads_handlers": {
      "title": "Loads Handlers",
      "description": "Process of dynamically loading action and backend handler modules when needed."
    },
    "supplies_handlers": {
      "title": "Supplies Handlers",
      "description": "Registry operation of providing validated handler functions to the gateway on demand."
    },
    "coordinates_errors": {
      "title": "Coordinates Errors",
      "description": "Centralized error management that coordinates error collection and reporting across all system layers."
    },
    "reports_errors": {
      "title": "Reports Errors",
      "description": "Process of reporting errors through gateway error methods to the error system."
    },
    "initializes_debug": {
      "title": "Initializes Debug",
      "description": "Process of setting up and configuring the debug system based on request flags and configuration."
    },
    "captures_messages": {
      "title": "Captures Messages",
      "description": "Debug system operation of capturing messages through debug registry."
    },
    "debug_output": {
      "title": "Debug Output",
      "description": "Formatted debug information appended to the response, showing system execution details."
    },
    "uses_command": {
      "title": "Uses Command",
      "description": "Registry operation of using the request command name to locate appropriate handlers."
    },
    "locates_handlers": {
      "title": "Locates Handlers",
      "description": "Process of finding the correct handler modules for a given command and backend combination."
    },
    "adds_errors": {
      "title": "Adds Errors",
      "description": "Error system operation of adding error information to the response error collections."
    },
    "appends_debug": {
      "title": "Appends Debug",
      "description": "Debug system operation of adding debug output to the response for user inspection."
    },
    "debug_messages": {
      "title": "Debug Messages",
      "description": "Individual debug log entries captured by the debug system showing system execution details."
    },
    "raw_input_processing": {
      "title": "Raw Input Processing",
      "description": "Initial processing of raw command-line input before parsing and validation."
    },
    "request_parsing": {
      "title": "Request Parsing",
      "description": "Process of parsing raw command-line input into structured, validated data through the parsing pipeline."
    },
    "argument_extraction": {
      "title": "Argument Extraction",
      "description": "Process of extracting and categorizing arguments from parsed command-line input."
    },
    "provides_tokens": {
      "title": "Provides Tokens",
      "description": "Tokenizer operation of providing categorized tokens to the grammar parser for parsing."
    },
    "parsing_input": {
      "title": "Parsing Input",
      "description": "Grammar parser operation of processing tokenized input to build structured grammar representation."
    },
    "parsed_grammar": {
      "title": "Parsed Grammar",
      "description": "Structured grammar representation built from tokens, organized into commands, flags, and values."
    },
    "structured_data": {
      "title": "Structured Data",
      "description": "Data organized into structured formats (parsed grammar, request objects) for system consumption."
    },
    "builds_request": {
      "title": "Builds Request",
      "description": "Semantics operation of constructing the final Request object from parsed grammar structure."
    },
    "populates_data": {
      "title": "Populates Data",
      "description": "Process of filling request object collections with parsed argument data and metadata."
    },
    "influences_structure": {
      "title": "Influences Structure",
      "description": "How request data influences the structure and format of response object assembly."
    },
    "uses_request_data": {
      "title": "Uses Request Data",
      "description": "Response object operation of using request data for formatting and response building."
    },
    "tokens_to_data": {
      "title": "Tokens to Data",
      "description": "Transformation of tokenized input into structured data that populates request objects."
    },
    "structure_guide": {
      "title": "Structure Guide",
      "description": "Semantic structure that guides how response objects are assembled and formatted."
    },
    "response_format": {
      "title": "Response Format",
      "description": "The format and structure of response output, informed by parsed grammar and semantic analysis."
    },
    "writes_cache": {
      "title": "Writes Cache",
      "description": "Handler discovery operation of writing discovered registrations to JSON cache files."
    },
    "reads_cache": {
      "title": "Reads Cache",
      "description": "Cache operation of reading cached handler data for registry operations."
    },
    "validates_cache": {
      "title": "Validates Cache",
      "description": "Process of validating that cached data is still current and module paths are still importable."
    },
    "provides_data": {
      "title": "Provides Data",
      "description": "Action handler operation of providing data that backend handler formats for presentation."
    },
    "reads_from_cache": {
      "title": "Reads From Cache",
      "description": "Command registry operation of reading handler information from cache files."
    },
    "validates_data": {
      "title": "Validates Data",
      "description": "Command registry operation of validating cached handler data before use."
    },
    "supplies_handlers_conn": {
      "title": "Supplies Handlers",
      "description": "Handler discovery operation of providing discovered handler information to the command registry."
    },
    "triggers_discovery": {
      "title": "Triggers Discovery",
      "description": "Command registry operation of triggering handler discovery when cache misses occur."
    },
    "response_management": {
      "title": "Response Management",
      "description": "Gateway operation of managing response object lifecycle, including creation, output buffering, error collection, and final assembly."
    },
    "handler_lookup": {
      "title": "Handler Lookup",
      "description": "Process of using command information from the request object to locate appropriate handler modules through the registry."
    },
    "error_output": {
      "title": "Error Output",
      "description": "Process of adding error information collected from system layers to the response object for user display."
    },
    "debug_management": {
      "title": "Debug Management",
      "description": "Gateway operation of initializing, coordinating, and managing debug system operations throughout request processing."
    },
    "cache_management": {
      "title": "Cache Management",
      "description": "Bidirectional process of writing discovered handlers to cache files and reading cached data during handler discovery and registry operations."
    },
    "registry_data": {
      "title": "Registry Data",
      "description": "Bidirectional exchange of handler registration data between cache and command registry for performance optimization."
    },
    "handler_supply": {
      "title": "Handler Supply",
      "description": "Bidirectional process of handler discovery providing discovered handler information to the command registry, and registry triggering discovery when needed."
    },
    "tokenization": {
      "title": "Tokenization",
      "description": "Process of breaking down raw command-line input into categorized tokens for grammar parsing."
    },
    "grammar_structure": {
      "title": "Grammar Structure",
      "description": "Process of building structured grammar representation from tokenized input for semantic analysis."
    },
    "request_construction": {
      "title": "Request Construction",
      "description": "Process of building the final Request object from parsed grammar structure, populating all argument collections."
    },
    "token_data": {
      "title": "Token Data",
      "description": "Direct transfer of token information from tokenizer to request object for initial data population."
    },
    "assembly_guide": {
      "title": "Assembly Guide",
      "description": "How semantic structure guides the assembly and formatting of response objects."
    },
    "parser": {
      "title": "Parser",
      "description": "CLI backend type that formats output as command-line tables and text."
    },
    "mcp": {
      "title": "MCP",
      "description": "Model Context Protocol backend type for AI agent integration."
    },
    "hen_py": {
      "title": "hen.py",
      "description": "Main command-line entry point script for the Henhouse system, used by human users on the local machine (Cursor app PowerShell terminal) or on the server via SSH connection as the human user's account. Agents and project users use gateway.py instead, which is created from hen.py."
    },
    "hen_ps1": {
      "title": "hen.ps1",
      "description": "PowerShell wrapper script that lets you run hen.py without having to type 'python'."
    },
    "global_gateway_singleton_object": {
      "title": "Global Gateway Singleton Object",
      "description": "Single gateway instance managed globally, accessed via get_gateway() function for system-wide coordination."
    },
    "db_connection_decoration_system": {
      "title": "DB Connection Decoration System",
      "description": "Decorator-based database access system providing @db_read and @db_write decorators for safe database operations."
    },
    "db_credential_storage_location": {
      "title": "DB Credential Storage Location",
      "description": "Database connection credentials stored in ~/.{project}.cnf files, loaded per-tier with appropriate privilege levels."
    },
    "ubuntu_user_tiers": {
      "title": "Ubuntu User Tiers",
      "description": "Unix user-based permission tiers (guest, admin, root, verified) that provide isolated execution contexts."
    },
    "srv_deployment": {
      "title": "SRV Deployment",
      "description": "Deployment layout under /srv/{project}/ directory containing code, static assets, logs, and tier-specific Flask apps."
    },
    "push_pull_system": {
      "title": "Push/Pull System",
      "description": "Deployment workflow for pushing code changes and pulling updates to deployment environments."
    },
    "stage_py": {
      "title": "stage.py",
      "description": "Script that allows edits done on the server to be staged back into the Git repository through the Cursor app interface, providing a graphical user interface for staging as opposed to command line."
    },
    "stage_ps1": {
      "title": "stage.ps1",
      "description": "PowerShell wrapper script that lets you run stage.py without having to type 'python'."
    },
    "http_deployment": {
      "title": "HTTP Deployment",
      "description": "HTTP-facing deployment architecture with Nginx terminating TLS and proxying to Flask apps, which spawn Gateway subprocesses."
    },
    "cache_management": {
      "title": "Cache Management",
      "description": "Deployment system for managing cache cleanup and registry operations in the deployment environment."
    },
    "deployment_configuration": {
      "title": "Deployment Config",
      "description": "Deployment configuration files including whitelists and blacklists that control which files are included or excluded during deployment."
    },
    "db_deployment": {
      "title": "DB Deployment",
      "description": "Database deployment system for setting up, configuring, and managing database infrastructure in the deployment environment."
    },
    "flask_deployment": {
      "title": "Flask Deployment",
      "description": "Flask application deployment system for managing tier-specific Flask daemon instances and HTTP/MCP clients."
    },
    "git_deployment": {
      "title": "Git Deployment",
      "description": "Git repository deployment system for managing code synchronization between local development and server repositories."
    },
    "users_deployment": {
      "title": "Users Deployment",
      "description": "User account deployment system for managing user accounts, authentication, and access control in the deployment environment."
    },
    "mysql_deployment": {
      "title": "MySQL Deployment",
      "description": "MySQL database deployment and configuration for Henhouse data persistence."
    },
    "db_homepage_init": {
      "title": "DB Homepage Init",
      "description": "Database initialization process that creates the homepage hierarchy structure."
    },
    "agent_management_system": {
      "title": "Agent Management System",
      "description": "System for managing AI agents including registration, onboarding, timeclock tracking, and context subscriptions."
    },
    "context_subscriptions": {
      "title": "Context Subscriptions",
      "description": "System for agents to subscribe to and receive context feed updates."
    },
    "context_feed_queues": {
      "title": "Context Feed Queues",
      "description": "Queue system for managing and delivering context updates to subscribed agents."
    },
    "respawning_system": {
      "title": "Respawning System",
      "description": "System for automatically restarting failed or terminated agent processes."
    },
    "work_module": {
      "title": "Work Module",
      "description": "Module for managing work assignments, dockets, tasks, and steps."
    },
    "work_dockets": {
      "title": "Work Dockets",
      "description": "Organizational containers for grouping related work tasks and assignments."
    },
    "asks": {
      "title": "Asks",
      "description": "Requests or requirements that need to be addressed as part of work items."
    },
    "task": {
      "title": "Task",
      "description": "Individual work unit within a docket that may contain multiple steps."
    },
    "steps": {
      "title": "Steps",
      "description": "Individual actions or operations within a task that must be completed sequentially."
    },
    "sidecar_files": {
      "title": "Sidecar Files",
      "description": "Supporting files associated with main content files, providing additional metadata or configuration."
    },
    "filing_cabinet_documents": {
      "title": "Filing Cabinet Documents",
      "description": "Organized document storage system for categorizing and retrieving documents by keywords and metadata."
    },
    "keywords": {
      "title": "Keywords",
      "description": "Tags or labels used for categorizing and searching documents and content."
    },
    "homepage_hierarchy": {
      "title": "Homepage Hierarchy",
      "description": "Tree structure of pages starting from the root homepage, with parent-child relationships forming a navigation hierarchy."
    },
    "tp_decorators": {
      "title": "TP Decorators",
      "description": "Decorator functions registered with @register_tp_decorator that transform text in the text processor pipeline."
    },
    "filesystem_crud_per_user": {
      "title": "Filesystem CRUD Per User",
      "description": "File system operations (Create, Read, Update, Delete) scoped to individual user directories."
    },
    "db_crud_per_user": {
      "title": "DB CRUD Per User",
      "description": "Database operations (Create, Read, Update, Delete) with tier-based access control and permissions."
    },
    "cli_table_system": {
      "title": "CLI Table System",
      "description": "Command-line interface table formatting system for displaying structured data in terminal output."
    },
    "html_table_system": {
      "title": "HTML Table System",
      "description": "HTML table formatting system for displaying structured data in web browser output."
    },
    "icons": {
      "title": "Icons",
      "description": "Visual icon symbols defined in icon.ini files for use in table headers and display elements."
    },
    "label": {
      "title": "Label",
      "description": "Text labels defined in label.ini files for use in headers, buttons, and display elements."
    },
    "flag_groups": {
      "title": "Flag Groups",
      "description": "Logical groupings of related flags that can be disabled together via no-flag groups."
    },
    "extra_commands": {
      "title": "Extra Commands",
      "description": "Additional command names that can be recognized beyond the primary command name, with optional default values."
    },
    "kebab_case_to_snake_case_conversion": {
      "title": "Kebab-Case to Snake_Case Conversion",
      "description": "Automatic conversion between command naming conventions (e.g., command-list ↔ command_list) for handler matching."
    },
    "backend_types": {
      "title": "Backend Types",
      "description": "Four main backend categories: action (business logic), parser (CLI), http (web), and mcp (AI agent protocol)."
    },
    "action_backend": {
      "title": "Action Backend",
      "description": "Backend type for business logic execution, registered with @register_action and @register_command decorators."
    },
    "register_parser_decorator": {
      "title": "Register Parser Decorator",
      "description": "@register_parser decorator that registers CLI formatting functions for parser backend."
    },
    "register_http_decorator": {
      "title": "Register HTTP Decorator",
      "description": "@register_http decorator that registers HTML formatting functions for HTTP backend."
    },
    "register_mcp_decorator": {
      "title": "Register MCP Decorator",
      "description": "@register_mcp decorator that registers MCP protocol functions for MCP backend."
    },
    "error_reporting_methods": {
      "title": "Error Reporting Methods",
      "description": "Gateway methods for reporting errors by category: request_error, action_error, backend_error, etc."
    },
    "debug_filters": {
      "title": "Debug Filters",
      "description": "Filtering system providing precise control over debug output via whitelist, graylist, and blacklist rules."
    },
    "safe_mode_context": {
      "title": "Safe Mode Context",
      "description": "Context manager that prevents recursive debug rendering during table construction and debug output generation."
    },
    "debug_function_factory": {
      "title": "Debug Function Factory",
      "description": "System that provides debug function implementations (trace_in, log, debug, warn) based on configured debug backend."
    },
    "render_flexible_table": {
      "title": "Render Flexible Table",
      "description": "Flexible table rendering function with automatic column detection and formatting."
    },
    "render_meta_table": {
      "title": "Render Meta Table",
      "description": "Recursive metadata table rendering for complex nested data structures with automatic width calculation."
    },
    "field_configuration": {
      "title": "Field Configuration",
      "description": "FieldConfig class and field type definitions that control how table fields are displayed and formatted."
    },
    "field_config": {
      "title": "FieldConfig",
      "description": "Configuration class with methods like add_header(), add_simple(), add_group() for building table field configurations."
    },
    "table_builder": {
      "title": "Table Builder",
      "description": "Table formatting system that transforms structured data into formatted tables through coordinated modules."
    },
    "table_configuration": {
      "title": "Table Configuration",
      "description": "Configuration management system that loads table settings from INI files for margins, padding, borders, and column settings."
    },
    "table_layout": {
      "title": "Table Layout",
      "description": "Layout calculation system that determines optimal column layouts and dimensions based on content and configuration."
    },
    "table_borders": {
      "title": "Table Borders",
      "description": "Border rendering system that creates table borders and separators using normalized glyphs and layout calculations."
    },
    "table_cells": {
      "title": "Table Cells",
      "description": "Cell processing system that handles individual cell content with text shaping, wrapping, and alignment."
    },
    "column_layout": {
      "title": "Column Layout",
      "description": "Calculated column dimensions and properties including width, alignment, overflow handling, and vertical alignment."
    },
    "rendered_row": {
      "title": "Rendered Row",
      "description": "Data structure representing a fully rendered table row with formatted lines and type information."
    },
    "text_tools": {
      "title": "Text Tools",
      "description": "Comprehensive text processing utility system providing Unicode-aware text manipulation and formatting capabilities."
    },
    "justify": {
      "title": "Justify",
      "description": "Text justification function that distributes spaces evenly across lines for aligned text blocks."
    },
    "text_processor_pipeline": {
      "title": "Text Processor Pipeline",
      "description": "Decorator-based processing pipeline that transforms structured markup into formatted output through sequential decorators."
    },
    "decorator_pipeline": {
      "title": "Decorator Pipeline",
      "description": "Sequential decorator execution where text flows through decorators in left-to-right order for transformation."
    },
    "register_tp_decorator": {
      "title": "Register TP Decorator",
      "description": "@register_tp_decorator decorator that registers text processor decorator functions for markup transformation."
    },
    "link_tokens": {
      "title": "Link Tokens",
      "description": "Page link syntax tokens: [[page_id]], [[page_name]], [[page_name][display_text]] parsed by text processor."
    },
    "image_tokens": {
      "title": "Image Tokens",
      "description": "Image embed syntax tokens: {{page_id}}, {{page_name}}, {{{image_id}}} parsed by text processor."
    },
    "image_link_tokens": {
      "title": "Image-Link Tokens",
      "description": "Combined image-link syntax tokens: [[page][{{image}}]] that create clickable image links parsed by text processor."
    },
    "decorator_chain_tokens": {
      "title": "Decorator Chain Tokens",
      "description": "Decorator syntax tokens: @decorator_name, @decorator(arg1, arg2) parsed by text processor."
    },
    "page_resolution": {
      "title": "Page Resolution",
      "description": "Process of resolving page references (by ID or name) to actual page data from the database."
    },
    "image_resolution": {
      "title": "Image Resolution",
      "description": "Process of resolving image references (by page or direct ID) to actual image data and instances from the database."
    },
    "links_table": {
      "title": "Links Table",
      "description": "Database table storing page-to-page references parsed from page content and managed by text processor."
    },
    "imagelinks_table": {
      "title": "ImageLinks Table",
      "description": "Database table storing page-to-image references parsed from page content and managed by text processor."
    },
    "db_read_decorator": {
      "title": "DB Read Decorator",
      "description": "@db_read decorator for database read operations (SELECT queries) with no retry logic."
    },
    "db_write_decorator": {
      "title": "DB Write Decorator",
      "description": "@db_write decorator for database write operations (INSERT/UPDATE/DELETE) with retry logic and transactions."
    },
    "with_connection": {
      "title": "With Connection",
      "description": "Core connection management decorator that handles connection creation, lifecycle, and cleanup with error handling."
    },
    "error_classification": {
      "title": "Error Classification",
      "description": "System for categorizing database exceptions to determine appropriate retry decisions and error handling strategies."
    },
    "retry_logic": {
      "title": "Retry Logic",
      "description": "Automatic retry mechanism for database operations with exponential backoff and configurable retry limits."
    },
    "exponential_backoff": {
      "title": "Exponential Backoff",
      "description": "Retry strategy that increases delay between retry attempts exponentially to reduce database load during failures."
    },
    "agent_validation": {
      "title": "Agent Validation",
      "description": "Process of validating agent identity (agent_id, badge_ts) before allowing database access for security."
    },
    "r_query": {
      "title": "R Query",
      "description": "Function for executing SELECT queries with parameter binding, returning result rows."
    },
    "u_query": {
      "title": "U Query",
      "description": "Function for executing UPDATE queries with parameter binding, returning affected row count."
    },
    "c_query": {
      "title": "C Query",
      "description": "Function for executing INSERT queries with parameter binding, returning inserted row ID."
    },
    "d_query": {
      "title": "D Query",
      "description": "Function for executing DELETE queries with parameter binding, returning deleted row count."
    },
    "dsn_configuration": {
      "title": "DSN Configuration",
      "description": "Database connection configuration loaded from ~/.{project}.cnf files containing host, user, password, database settings."
    },
    "database_connection_lifecycle": {
      "title": "Database Connection Lifecycle",
      "description": "Complete lifecycle management of database connections from creation, usage, transaction handling, to cleanup and error recovery."
    },
    "config_access_functions": {
      "title": "Config Access Functions",
      "description": "Unified API functions (ic, dc, mc, tc, cc) for accessing configuration data from INI files."
    },
    "ic_icon_access": {
      "title": "IC (Icon Access)",
      "description": "ic() function for accessing icon values from icon.ini configuration files."
    },
    "dc_label_access": {
      "title": "DC (Label Access)",
      "description": "dc() function for accessing label values from label.ini configuration files."
    },
    "mc_table_config_access": {
      "title": "MC (Table Config Access)",
      "description": "mc() function for accessing table configuration values from table.ini configuration files."
    },
    "tc_parse_config_access": {
      "title": "TC (Parse Config Access)",
      "description": "tc() function for accessing parse configuration values from parse.ini configuration files."
    },
    "cc_config_access": {
      "title": "CC (Config Access)",
      "description": "cc() function for accessing general configuration values from configuration files."
    },
    "ini_files": {
      "title": "INI Files",
      "description": "Configuration files in INI format (icon.ini, label.ini, table.ini, parse.ini) storing system configuration data."
    },
    "parse_ini": {
      "title": "parse.ini",
      "description": "INI configuration file storing text parsing configuration settings."
    },
    "cached_config_data": {
      "title": "Cached Config Data",
      "description": "Configuration data cached in memory after initial load for performance optimization."
    },
    "page_class": {
      "title": "Page Class",
      "description": "Object-oriented page management class with mixins for hierarchy, validation, content, images, and display functionality."
    },
    "page_hierarchy": {
      "title": "Page Hierarchy",
      "description": "Parent-child relationship system for organizing pages into tree structures with breadcrumb generation."
    },
    "page_validation": {
      "title": "Page Validation",
      "description": "Validation system for page constraints including name uniqueness, parent validity, and business rule enforcement."
    },
    "page_content": {
      "title": "Page Content",
      "description": "Page text content management with text processor integration for parsing markup and generating HTML output."
    },
    "page_images": {
      "title": "Page Images",
      "description": "Image association management for linking images to pages and managing image ordering and visibility."
    },
    "page_display": {
      "title": "Page Display",
      "description": "Output data preparation system for formatting page information for backend rendering (CLI tables, HTML, MCP)."
    },
    "page_mixins": {
      "title": "Page Mixins",
      "description": "Mixin modules providing functionality to the Page class: validation, hierarchy, content, images, display, and AJAX mixins."
    },
    "page_registry": {
      "title": "Page Registry",
      "description": "Page loading and lookup system that provides functions for retrieving page objects by ID, name, or link from the database."
    },
    "page_class_registry": {
      "title": "Page Class Registry",
      "description": "Dynamic page class discovery and registration system that scans for and caches custom page class definitions with caching support."
    },
    "page_actions": {
      "title": "Page Actions",
      "description": "Action handler files that implement CRUD and modification operations for pages: add, delete, show, modify, move, and copy operations."
    },
    "image_operations": {
      "title": "Image Operations",
      "description": "Action handler files for managing image associations with pages: add, remove, copy, move, and reorder image operations."
    },
    "page_rendering": {
      "title": "Page Rendering",
      "description": "Backend handler files that format page data for display in different output formats (CLI tables, HTML) using render_block and field configurations."
    },
    "page_utilities": {
      "title": "Page Utilities",
      "description": "Utility functions for page operations including page counting, page lookup, and helper functions for page management."
    },
    "parent_child_relationships": {
      "title": "Parent-Child Relationships",
      "description": "Database and object relationships between parent and child pages forming hierarchical page structures."
    },
    "breadcrumb_generation": {
      "title": "Breadcrumb Generation",
      "description": "Automatic generation of breadcrumb navigation paths from page hierarchy for display in UI."
    },
    "image_class": {
      "title": "Image Class",
      "description": "Object-oriented image management class with mixins for validation, instances, content, and display functionality."
    },
    "image_instances": {
      "title": "Image Instances",
      "description": "Multi-size image version management system that automatically generates and manages different sized versions of images."
    },
    "multi_size_management": {
      "title": "Multi-Size Management",
      "description": "Automatic system for creating and managing multiple sized versions (thumb, small, large, original) of image files."
    },
    "image_validation": {
      "title": "Image Validation",
      "description": "Validation system for image constraints including file format, size limits, and metadata validation."
    },
    "image_display": {
      "title": "Image Display",
      "description": "Output data preparation system for formatting image information for backend rendering (CLI tables, HTML, MCP)."
    },
    "image_instances_table": {
      "title": "Image Instances Table",
      "description": "Database table storing multiple sized versions of images with width, height, file paths, and file sizes."
    },
    "nginx_integration": {
      "title": "Nginx Integration",
      "description": "Nginx web server configuration for TLS termination, static asset serving, and proxying to Flask applications."
    },
    "tier_specific_flask_apps": {
      "title": "Tier-Specific Flask Apps",
      "description": "Separate Flask application instances per Unix tier user (guest, admin, root) running on different ports."
    },
    "tier_specific_ports": {
      "title": "Tier-Specific Ports",
      "description": "Different local ports assigned to each tier's Flask app instance for Nginx routing."
    },
    "tier_specific_credentials": {
      "title": "Tier-Specific Credentials",
      "description": "Database credentials loaded from tier-specific ~/.{project}.cnf files providing appropriate DB privilege levels."
    },
    "subprocess_isolation": {
      "title": "Subprocess Isolation",
      "description": "Isolation mechanism where each HTTP request spawns a fresh Gateway subprocess, preventing shared-state issues."
    },
    "concurrency_limits": {
      "title": "Concurrency Limits",
      "description": "Semaphore-based limits on in-flight Gateway subprocesses per Flask app instance to prevent resource exhaustion."
    },
    "timeout_handling": {
      "title": "Timeout Handling",
      "description": "Timeout mechanism (10s default) for Gateway subprocess execution with clear timeout error messages."
    },
    "input_caps": {
      "title": "Input Caps",
      "description": "Limits on number and size of argv tokens derived from URL/query string to prevent abuse and resource exhaustion."
    },
    "url_to_argv_mapping": {
      "title": "URL to argv Mapping",
      "description": "Mapping system that converts URL path segments to positional tokens and query parameters to flags for Gateway execution."
    },
    "path_segments": {
      "title": "Path Segments",
      "description": "URL path segments (e.g., /page/123) that become positional command arguments: ['page', '123']."
    },
    "query_parameters": {
      "title": "Query Parameters",
      "description": "URL query parameters (e.g., ?id=123&no_header=1) that become flag arguments: ['--id', '123', '--no_header', '1']."
    },
    "static_asset_serving": {
      "title": "Static Asset Serving",
      "description": "Direct serving of static files (CSS, JS, images) from /srv/{project}/site by Nginx without passing to Flask."
    },
    "health_check_endpoint": {
      "title": "Health Check Endpoint",
      "description": "/status endpoint that returns JSON payload indicating Flask app health and availability."
    },
    "basic_auth": {
      "title": "Basic Auth",
      "description": "HTTP Basic Authentication using htpasswd files to gate admin and root tier subdomains at Nginx level."
    },
    "htpasswd": {
      "title": "htpasswd",
      "description": "Password file format used by Nginx for HTTP Basic Authentication of admin and root tier access."
    },
    "has_action_response": {
      "title": "Has Action Response",
      "description": "Gateway method to check if action execution has completed and produced response data."
    },
    "add_backend_response": {
      "title": "Add Backend Response",
      "description": "Gateway method to add formatted output from backend handlers to the response buffer."
    },
    "get_output": {
      "title": "Get Output",
      "description": "Response object method that assembles and returns the final formatted output string combining all components."
    },
    "get_data": {
      "title": "Get Data",
      "description": "Utility function to extract data object from JSON response structure, accessing the 'data' field."
    },
    "safe_str": {
      "title": "Safe Str",
      "description": "Utility function to safely convert values to strings, handling None and other edge cases gracefully."
    },
    "ensure_iso_timestamps": {
      "title": "Ensure ISO Timestamps",
      "description": "Utility function to convert datetime objects to ISO format strings for JSON serialization."
    },
    "iso_now": {
      "title": "ISO Now",
      "description": "Utility function that returns current timestamp in ISO format string."
    },
    "json_success": {
      "title": "JSON Success",
      "description": "Utility function that creates standardized JSON success response structure."
    },
    "json_error": {
      "title": "JSON Error",
      "description": "Utility function that creates standardized JSON error response structure."
    },
    "guest_tier": {
      "title": "Guest Tier",
      "description": "Lowest privilege tier with read-only database access, no write permissions, for public-facing content viewing."
    },
    "admin_tier": {
      "title": "Admin Tier",
      "description": "Administrative tier with full CRUD database access, gated by HTTP Basic Auth, for content management."
    },
    "root_tier": {
      "title": "Root Tier",
      "description": "Highest privilege tier with full system access, gated by HTTP Basic Auth, for system administration."
    },
    "verified_tier": {
      "title": "Verified Tier",
      "description": "Verified user tier with elevated permissions, accessed via magic-link verification (not yet fully implemented)."
    },
    "magic_link_verification": {
      "title": "Magic-Link Verification",
      "description": "Authentication mechanism using magic links sent via email for verified tier access (pending implementation)."
    },
    "session_based_tier_tracking": {
      "title": "Session-Based Tier Tracking",
      "description": "Session management system for tracking user tier across requests (pending implementation)."
    },
    "tier_specific_subdomains": {
      "title": "Tier-Specific Subdomains",
      "description": "Different subdomains (e.g., admin.{domain}, root.{domain}) that route to tier-specific Flask apps via Nginx."
    },
    "tier_specific_log_files": {
      "title": "Tier-Specific Log Files",
      "description": "Separate log files maintained per tier under /srv/{project}/logs/ for audit and debugging."
    },
    "mixin_pattern": {
      "title": "Mixin Pattern",
      "description": "Design pattern where functionality is added to classes via mixin classes (e.g., PageValidationMixin, PageHierarchyMixin)."
    },
    "singleton_pattern": {
      "title": "Singleton Pattern",
      "description": "Design pattern ensuring only one gateway instance exists globally, accessed via get_gateway() function."
    },
    "decorator_pattern": {
      "title": "Decorator Pattern",
      "description": "Design pattern using Python decorators for registering handlers, database access, and text processor transformations."
    },
    "builder_pattern": {
      "title": "Builder Pattern",
      "description": "Design pattern for constructing complex objects (tables, requests) through fluent method chaining."
    },
    "registry_pattern": {
      "title": "Registry Pattern",
      "description": "Design pattern for dynamic registration and discovery of handlers through decorators and module scanning."
    },
    "gateway_system_architecture": {
      "title": "Gateway System Architecture",
      "description": "High-level overview of the Gateway system showing how the central orchestrator manages request/response objects, coordinates execution through the registry, handles errors, and manages debugging across all subsystems."
    },
    "request_response_pipeline": {
      "title": "Request/Response Pipeline",
      "description": "High-level overview of the four-stage parsing pipeline (tokenizer → grammar parser → semantics → request object) and how request data flows to influence response assembly and formatting."
    },
    "registry_discovery_system": {
      "title": "Registry & Discovery System",
      "description": "High-level overview of the registry and discovery system showing how handler discovery, cache management, and command registry work together to provide dynamic handler loading and validation."
    },
    "backend_handler_execution_flow": {
      "title": "Backend Handler Execution Flow",
      "description": "High-level overview of the backend handler execution flow showing how gateway dispatches action handlers, stores results, dispatches backend handlers, and how backend types define handler patterns."
    },
    "render_system_architecture": {
      "title": "Render System Architecture",
      "description": "High-level overview of the render system architecture showing how render system, table builder, text tools, and config system work together to format structured data into tables and text output."
    },
    "debug_system_architecture": {
      "title": "Debug System Architecture",
      "description": "High-level overview of the debug system architecture showing how debug system, debug registry, and debug filters work together to capture, filter, and display debug information."
    },
    "database_connection_system": {
      "title": "Database Connection System",
      "description": "High-level overview of the database connection system showing how DB connection decorators, database connection lifecycle, and agent validation work together for safe database operations."
    },
    "http_deployment_architecture": {
      "title": "HTTP Deployment Architecture",
      "description": "High-level overview of the HTTP deployment architecture showing how HTTP deployment, nginx integration, Flask daemon deployment, Ubuntu user tiers, and HTTP client work together for web-facing deployment."
    },
    "text_processor_system": {
      "title": "Text Processor System",
      "description": "High-level overview of the text processor system showing how text processor pipeline, TP grammar, page resolution, and image resolution work together to parse markup and resolve references."
    },
    "page_image_content_management": {
      "title": "Page/Image Content Management",
      "description": "High-level overview of the page and image content management system showing how pages, images, page class, and image class work together for hierarchical content and media management."
    },
    "render_header_block": {
      "title": "Render Header Block",
      "description": "Header block rendering function with no-flag support for conditional header display."
    },
    "finalize_output": {
      "title": "Finalize Output",
      "description": "Output finalization and line filtering function that assembles final formatted output."
    },
    "break_section": {
      "title": "Break Section",
      "description": "Function that adds section breaks between content blocks in rendered output."
    },
    "display_width": {
      "title": "Display Width",
      "description": "Text tool function that calculates accurate display width for Unicode text with ANSI filtering."
    },
    "wrap": {
      "title": "Wrap",
      "description": "Advanced text wrapping function with color preservation and intelligent word breaking."
    },
    "pad_left": {
      "title": "Pad Left",
      "description": "Text padding function that pads text on the left side with display width awareness."
    },
    "pad_right": {
      "title": "Pad Right",
      "description": "Text padding function that pads text on the right side with display width awareness."
    },
    "pad_center": {
      "title": "Pad Center",
      "description": "Text padding function that centers text with display width awareness."
    },
    "ellipsize": {
      "title": "Ellipsize",
      "description": "Text ellipsizing function with display width awareness for truncating long text."
    },
    "slice": {
      "title": "Slice",
      "description": "Text slicing function with display width calculation for safe text truncation."
    },
    "dispatches_action": {
      "title": "Dispatches Action",
      "description": "Gateway operation of dispatching action handler execution for business logic."
    },
    "stores_results": {
      "title": "Stores Results",
      "description": "Action handler operation of storing execution results via set_action_response."
    },
    "dispatches_backend": {
      "title": "Dispatches Backend",
      "description": "Gateway operation of dispatching backend handler execution for presentation formatting."
    },
    "adds_output": {
      "title": "Adds Output",
      "description": "Backend handler operation of adding formatted output via add_backend_response."
    },
    "reads_results": {
      "title": "Reads Results",
      "description": "Backend handler operation of reading action results via get_action_response."
    },
    "defines_backends": {
      "title": "Defines Backends",
      "description": "Backend types operation of defining which backend handler to use for a request."
    },
    "selects_backend": {
      "title": "Selects Backend",
      "description": "Gateway operation of selecting appropriate backend type for request processing."
    },
    "determines_handler": {
      "title": "Determines Handler",
      "description": "Backend types operation of determining handler registration pattern for different backends."
    },
    "creates_table_builder": {
      "title": "Creates Table Builder",
      "description": "Render system operation of creating table builder instances for formatting structured data."
    },
    "provides_rendered_output": {
      "title": "Provides Rendered Output",
      "description": "Table builder operation of providing rendered table output to render system."
    },
    "uses_text_tools": {
      "title": "Uses Text Tools",
      "description": "Render system operation of using text tools for width calculation and formatting."
    },
    "provides_utilities": {
      "title": "Provides Utilities",
      "description": "Text tools operation of providing text processing utilities to render system."
    },
    "accesses_config": {
      "title": "Accesses Config",
      "description": "Render system operation of accessing config for icons, labels, and table settings."
    },
    "supplies_config": {
      "title": "Supplies Config",
      "description": "Config system operation of supplying configuration data to render system."
    },
    "uses_for_cells": {
      "title": "Uses For Cells",
      "description": "Table builder operation of using text tools for cell content processing."
    },
    "provides_width_calc": {
      "title": "Provides Width Calc",
      "description": "Text tools operation of providing width calculations for column layout."
    },
    "reads_table_config": {
      "title": "Reads Table Config",
      "description": "Table builder operation of reading table configuration from config system."
    },
    "supplies_table_settings": {
      "title": "Supplies Table Settings",
      "description": "Config system operation of supplying table formatting settings to table builder."
    },
    "provides_filtered_data": {
      "title": "Provides Filtered Data",
      "description": "Debug registry operation of providing filtered debug data for output."
    },
    "applies_filters": {
      "title": "Applies Filters",
      "description": "Debug system operation of applying filter rules to control output."
    },
    "filters_determine": {
      "title": "Filters Determine",
      "description": "Debug filters operation of determining which messages appear in debug output."
    },
    "applies_during_capture": {
      "title": "Applies During Capture",
      "description": "Debug registry operation of applying filters during message capture."
    },
    "stores_filter_rules": {
      "title": "Stores Filter Rules",
      "description": "Debug filters operation of storing filter rules in registry state."
    },
    "manages_connection": {
      "title": "Manages Connection",
      "description": "DB connection decoration system operation of managing connection through lifecycle."
    },
    "provides_connections": {
      "title": "Provides Connections",
      "description": "Database connection lifecycle operation of providing connection instances to decorators."
    },
    "validates_agent": {
      "title": "Validates Agent",
      "description": "DB connection decoration system operation of validating agent before database access."
    },
    "gatekeeper_access": {
      "title": "Gatekeeper Access",
      "description": "Agent validation operation of serving as gatekeeper for connection access."
    },
    "validates_during_setup": {
      "title": "Validates During Setup",
      "description": "Database connection lifecycle operation of validating agent during connection setup."
    },
    "validation_required": {
      "title": "Validation Required",
      "description": "Agent validation requirement before connection creation in database lifecycle."
    },
    "proxies_requests": {
      "title": "Proxies Requests",
      "description": "Nginx integration operation of proxying requests to Flask apps."
    },
    "listens_on_ports": {
      "title": "Listens On Ports",
      "description": "Flask daemon deployment operation of Flask apps listening on ports nginx proxies to."
    },
    "orchestrates_deployment": {
      "title": "Orchestrates Deployment",
      "description": "HTTP deployment operation of orchestrating Flask deployment process."
    },
    "deployed_via": {
      "title": "Deployed Via",
      "description": "Flask daemon deployment being deployed via HTTP deployment system."
    },
    "runs_separate_instance": {
      "title": "Runs Separate Instance",
      "description": "Ubuntu user tiers operation where each tier runs separate Flask instance."
    },
    "apps_run_as_users": {
      "title": "Apps Run As Users",
      "description": "Flask daemon deployment operation of Flask apps running as tier-specific users."
    },
    "spawned_by_flask": {
      "title": "Spawned By Flask",
      "description": "HTTP client being spawned by Flask apps as subprocess per request."
    },
    "creates_subprocess": {
      "title": "Creates Subprocess",
      "description": "Flask daemon deployment operation of creating HTTP client subprocess per request."
    },
    "configured_by_deployment": {
      "title": "Configured By Deployment",
      "description": "Nginx integration being configured by deployment system."
    },
    "sets_up_nginx": {
      "title": "Sets Up Nginx",
      "description": "HTTP deployment operation of setting up nginx configuration."
    },
    "routes_to_subdomains": {
      "title": "Routes To Subdomains",
      "description": "Nginx integration operation of routing to tier-specific subdomains."
    },
    "determines_routing": {
      "title": "Determines Routing",
      "description": "Ubuntu user tiers structure determining nginx routing configuration."
    },
    "executes_requests": {
      "title": "Executes Requests",
      "description": "HTTP client operation of executing deployment requests."
    },
    "uses_for_execution": {
      "title": "Uses For Execution",
      "description": "HTTP deployment system operation of using HTTP client for execution."
    },
    "sets_up_tiers": {
      "title": "Sets Up Tiers",
      "description": "HTTP deployment operation of setting up tier structure."
    },
    "configured_by_deployment_tiers": {
      "title": "Configured By Deployment",
      "description": "Ubuntu user tiers structure being configured by deployment system."
    },
    "triggers_subprocess": {
      "title": "Triggers Subprocess",
      "description": "Nginx integration operation of triggering HTTP client subprocess via requests."
    },
    "returns_through_nginx": {
      "title": "Returns Through Nginx",
      "description": "HTTP client operation of returning responses through nginx."
    },
    "determines_permissions": {
      "title": "Determines Permissions",
      "description": "Ubuntu user tiers operation of determining HTTP client permissions."
    },
    "runs_with_credentials": {
      "title": "Runs With Credentials",
      "description": "HTTP client operation of running with tier credentials."
    },
    "parsed_tokens_flow": {
      "title": "Parsed Tokens Flow",
      "description": "TP grammar operation where parsed tokens flow into text processor pipeline."
    },
    "processes_grammar": {
      "title": "Processes Grammar",
      "description": "Text processor pipeline operation of processing grammar tokens."
    },
    "resolves_page_links": {
      "title": "Resolves Page Links",
      "description": "Text processor pipeline operation of resolving page links."
    },
    "provides_page_data": {
      "title": "Provides Page Data",
      "description": "Page resolution operation of providing resolved page data to text processor."
    },
    "resolves_images": {
      "title": "Resolves Images",
      "description": "Text processor pipeline operation of resolving image references."
    },
    "provides_image_data": {
      "title": "Provides Image Data",
      "description": "Image resolution operation of providing resolved image data to text processor."
    },
    "contains_page_refs": {
      "title": "Contains Page Refs",
      "description": "TP grammar tokens containing page references for resolution."
    },
    "results_populate_grammar": {
      "title": "Results Populate Grammar",
      "description": "Page resolution results populating grammar structure with resolved data."
    },
    "contains_image_refs": {
      "title": "Contains Image Refs",
      "description": "TP grammar tokens containing image references for resolution."
    },
    "both_use_database": {
      "title": "Both Use Database",
      "description": "Both page and image resolution systems using database tables for lookup."
    },
    "creates_page_instances": {
      "title": "Creates Page Instances",
      "description": "Pages operation of creating page class instances for content management."
    },
    "manages_page_data": {
      "title": "Manages Page Data",
      "description": "Page class operation of managing page data and hierarchy."
    },
    "creates_image_instances": {
      "title": "Creates Image Instances",
      "description": "Images operation of creating image class instances for media management."
    },
    "manages_image_data": {
      "title": "Manages Image Data",
      "description": "Image class operation of managing image data and instances."
    },
    "reference_images": {
      "title": "Reference Images",
      "description": "Pages operation of referencing associated images."
    },
    "belong_to_pages": {
      "title": "Belong To Pages",
      "description": "Images operation of belonging to pages in content structure."
    },
    "manages_page_images": {
      "title": "Manages Page Images",
      "description": "Page class operation of managing page images and associations."
    },
    "links_to_pages": {
      "title": "Links To Pages",
      "description": "Image class operation of linking to parent pages."
    },
    "cli_human_user": {
      "title": "CLI Human User",
      "description": "A human user accessing the system via command-line interface with direct terminal interaction."
    },
    "external_agent": {
      "title": "External Agent",
      "description": "An external automated system or service accessing the gateway through programmatic interfaces."
    },
    "provides_access": {
      "title": "Provides Access",
      "description": "Gateway method that grants access to system resources based on user type and permissions."
    },
    "routes_request": {
      "title": "Routes Request",
      "description": "Gateway process of directing incoming requests to appropriate handlers based on command and backend type."
    },
    "authenticates": {
      "title": "Authenticates",
      "description": "Gateway authentication process that verifies user identity and determines access level."
    },
    "manages_session": {
      "title": "Manages Session",
      "description": "Gateway session management for maintaining user state and permissions across requests."
    },
    "mcp_protocol": {
      "title": "MCP Protocol",
      "description": "Model Context Protocol for AI agent communication and integration, providing structured access methods to the gateway system."
    }
  }
};