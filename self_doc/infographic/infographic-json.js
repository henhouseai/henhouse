var infographicData = {
  "infographics": [
    {
      "id": "registry-discovery",
      "title": "Registry & Discovery System",
      "nodes": [
        {
          "id": "cache",
          "label": "cache",
          "lowLevel": [
            "json_cache_files",
            "decorator_scanning",
            "base_registrations",
            "backend_specific_registrations"
          ]
        },
        {
          "id": "command-registry",
          "label": "command_registry_term",
          "lowLevel": [
            "handler_resolution",
            "dynamic_module_loading",
            "module_validation"
          ]
        },
        {
          "id": "handler-discovery",
          "label": "handler_discovery",
          "lowLevel": [
            "decorator_scanning",
            "dynamic_module_loading"
          ]
        }
      ],
      "connections": [
        {
          "from": "handler-discovery",
          "to": "cache",
          "type": "bidirectional",
          "description": "cache_management",
          "lowLevel": [
            "writes_cache",
            "reads_cache",
            "validates_cache"
          ]
        },
        {
          "from": "cache",
          "to": "command-registry",
          "type": "bidirectional",
          "description": "registry_data",
          "lowLevel": [
            "provides_data",
            "reads_from_cache",
            "validates_data"
          ]
        },
        {
          "from": "handler-discovery",
          "to": "command-registry",
          "type": "bidirectional",
          "description": "handler_supply",
          "lowLevel": [
            "supplies_handlers_conn",
            "triggers_discovery"
          ]
        }
      ]
    },
    {
      "id": "backend-handler-execution",
      "title": "Backend Handler Execution Flow",
      "nodes": [
        {
          "id": "gateway",
          "label": "gateway",
          "lowLevel": [
            "dispatch",
            "get_action_response",
            "add_backend_response"
          ]
        },
        {
          "id": "action-handler",
          "label": "action_handler",
          "lowLevel": [
            "register_action_decorator",
            "register_command_decorator",
            "set_action_response",
            "success_payload"
          ]
        },
        {
          "id": "backend-handler",
          "label": "backend_handler",
          "lowLevel": [
            "register_parser_decorator",
            "register_http_decorator",
            "register_mcp_decorator",
            "add_backend_response",
            "get_action_response"
          ]
        },
        {
          "id": "backend-types",
          "label": "backend_types",
          "lowLevel": [
            "parser_backend",
            "http_backend",
            "mcp_backend",
            "action_backend"
          ]
        }
      ],
      "connections": [
        {
          "from": "gateway",
          "to": "action-handler",
          "type": "forward",
          "description": "dispatches_action",
          "lowLevel": []
        },
        {
          "from": "action-handler",
          "to": "gateway",
          "type": "forward",
          "description": "stores_results",
          "lowLevel": []
        },
        {
          "from": "gateway",
          "to": "backend-handler",
          "type": "forward",
          "description": "dispatches_backend",
          "lowLevel": []
        },
        {
          "from": "backend-handler",
          "to": "gateway",
          "type": "forward",
          "description": "adds_output",
          "lowLevel": []
        },
        {
          "from": "backend-handler",
          "to": "action-handler",
          "type": "forward",
          "description": "reads_results",
          "lowLevel": []
        },
        {
          "from": "backend-types",
          "to": "gateway",
          "type": "forward",
          "description": "defines_backends",
          "lowLevel": []
        },
        {
          "from": "gateway",
          "to": "backend-types",
          "type": "forward",
          "description": "selects_backend",
          "lowLevel": []
        },
        {
          "from": "backend-types",
          "to": "action-handler",
          "type": "forward",
          "description": "defines_backends",
          "lowLevel": []
        },
        {
          "from": "backend-types",
          "to": "backend-handler",
          "type": "forward",
          "description": "determines_handler",
          "lowLevel": []
        },
        {
          "from": "action-handler",
          "to": "backend-handler",
          "type": "forward",
          "description": "provides_data",
          "lowLevel": []
        }
      ]
    },
    {
      "id": "render-system-architecture",
      "title": "Render System Architecture",
      "nodes": [
        {
          "id": "render-system",
          "label": "render_system",
          "lowLevel": [
            "render_block",
            "render_header_block",
            "render_meta_table",
            "finalize_output",
            "break_section"
          ]
        },
        {
          "id": "table-builder",
          "label": "table_builder",
          "lowLevel": [
            "table_configuration",
            "table_layout",
            "table_borders",
            "table_cells",
            "field_configuration"
          ]
        },
        {
          "id": "text-tools",
          "label": "text_tools",
          "lowLevel": [
            "display_width",
            "wrap",
            "pad_left",
            "pad_right",
            "pad_center",
            "ellipsize",
            "slice"
          ]
        },
        {
          "id": "config-system",
          "label": "config_system",
          "lowLevel": [
            "icons",
            "label",
            "ini_files",
            "ic_icon_access",
            "dc_label_access",
            "mc_table_config_access",
            "tc_parse_config_access",
            "cc_config_access"
          ]
        }
      ],
      "connections": [
        {
          "from": "render-system",
          "to": "table-builder",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "creates_table_builder",
            "provides_rendered_output"
          ]
        },
        {
          "from": "render-system",
          "to": "text-tools",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "uses_text_tools",
            "provides_utilities"
          ]
        },
        {
          "from": "render-system",
          "to": "config-system",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "accesses_config",
            "supplies_config"
          ]
        },
        {
          "from": "table-builder",
          "to": "text-tools",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "uses_for_cells",
            "provides_width_calc"
          ]
        },
        {
          "from": "table-builder",
          "to": "config-system",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "reads_table_config",
            "supplies_table_settings"
          ]
        }
      ]
    },
    {
      "id": "debug-system-architecture",
      "title": "Debug System Architecture",
      "nodes": [
        {
          "id": "debug-system",
          "label": "debug_system",
          "lowLevel": [
            "debug_registry_term",
            "debug_levels",
            "trace_in",
            "trace_out",
            "log",
            "debug",
            "warn"
          ]
        },
        {
          "id": "debug-registry",
          "label": "debug_registry_term",
          "lowLevel": [
            "safe_mode_context",
            "debug_levels"
          ]
        },
        {
          "id": "debug-filters",
          "label": "debug_filters",
          "lowLevel": [
            "whitelist_filtering",
            "graylist_filtering",
            "blacklist_filtering",
            "debug_limit"
          ]
        }
      ],
      "connections": [
        {
          "from": "debug-system",
          "to": "debug-registry",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "captures_messages",
            "provides_filtered_data"
          ]
        },
        {
          "from": "debug-system",
          "to": "debug-filters",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "applies_filters",
            "filters_determine"
          ]
        },
        {
          "from": "debug-registry",
          "to": "debug-filters",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "applies_during_capture",
            "stores_filter_rules"
          ]
        }
      ]
    },
    {
      "id": "database-connection-system",
      "title": "Database Connection System",
      "nodes": [
        {
          "id": "db-connection-decoration",
          "label": "db_connection_decoration_system",
          "lowLevel": [
            "db_read_decorator",
            "db_write_decorator",
            "with_connection"
          ]
        },
        {
          "id": "database-lifecycle",
          "label": "database_connection_lifecycle",
          "lowLevel": [
            "dsn_configuration",
            "retry_logic",
            "error_classification"
          ]
        },
        {
          "id": "agent-validation",
          "label": "agent_validation",
          "lowLevel": [
            "agent_validation",
            "agent_id",
            "badge_ts"
          ]
        }
      ],
      "connections": [
        {
          "from": "db-connection-decoration",
          "to": "database-lifecycle",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "manages_connection",
            "provides_connections"
          ]
        },
        {
          "from": "db-connection-decoration",
          "to": "agent-validation",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "validates_agent",
            "gatekeeper_access"
          ]
        },
        {
          "from": "database-lifecycle",
          "to": "agent-validation",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "validates_during_setup",
            "validation_required"
          ]
        }
      ]
    },
    {
      "id": "text-processor-system",
      "title": "Text Processor System",
      "nodes": [
        {
          "id": "text-processor-pipeline",
          "label": "text_processor_pipeline",
          "lowLevel": [
            "decorator_pipeline",
            "register_tp_decorator"
          ]
        },
        {
          "id": "tp-grammar",
          "label": "tp_grammar",
          "lowLevel": [
            "link_tokens",
            "image_tokens",
            "image_link_tokens",
            "decorator_chain_tokens"
          ]
        },
        {
          "id": "page-resolution",
          "label": "page_resolution",
          "lowLevel": [
            "links_table",
            "page_id",
            "page_name"
          ]
        },
        {
          "id": "image-resolution",
          "label": "image_resolution",
          "lowLevel": [
            "imagelinks_table",
            "image_id",
            "image_instances"
          ]
        }
      ],
      "connections": [
        {
          "from": "tp-grammar",
          "to": "text-processor-pipeline",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "parsed_tokens_flow",
            "processes_grammar"
          ]
        },
        {
          "from": "text-processor-pipeline",
          "to": "page-resolution",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "resolves_page_links",
            "provides_page_data"
          ]
        },
        {
          "from": "text-processor-pipeline",
          "to": "image-resolution",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "resolves_images",
            "provides_image_data"
          ]
        },
        {
          "from": "tp-grammar",
          "to": "page-resolution",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "contains_page_refs",
            "results_populate_grammar"
          ]
        },
        {
          "from": "tp-grammar",
          "to": "image-resolution",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "contains_image_refs",
            "results_populate_grammar"
          ]
        },
        {
          "from": "page-resolution",
          "to": "image-resolution",
          "type": "undirected",
          "description": "both_use_database",
          "lowLevel": []
        }
      ]
    },
    {
      "id": "page-image-content-management",
      "title": "Page/Image Content Management",
      "nodes": [
        {
          "id": "pages",
          "label": "pages",
          "lowLevel": [
            "page_class",
            "page_hierarchy",
            "parent_child_relationships",
            "homepage_hierarchy"
          ]
        },
        {
          "id": "images",
          "label": "images",
          "lowLevel": [
            "image_class",
            "image_instances",
            "multi_size_management"
          ]
        },
        {
          "id": "page-class",
          "label": "page_class",
          "lowLevel": [
            "page_content",
            "page_images",
            "page_display",
            "page_validation"
          ]
        },
        {
          "id": "image-class",
          "label": "image_class",
          "lowLevel": [
            "image_display",
            "image_validation",
            "image_instances"
          ]
        }
      ],
      "connections": [
        {
          "from": "pages",
          "to": "page-class",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "creates_page_instances",
            "manages_page_data"
          ]
        },
        {
          "from": "images",
          "to": "image-class",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "creates_image_instances",
            "manages_image_data"
          ]
        },
        {
          "from": "pages",
          "to": "images",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "reference_images",
            "belong_to_pages"
          ]
        },
        {
          "from": "page-class",
          "to": "image-class",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "manages_page_images",
            "links_to_pages"
          ]
        }
      ]
    }
  ],
  "positions": {}
};