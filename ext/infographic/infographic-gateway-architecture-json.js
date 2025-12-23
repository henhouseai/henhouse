var infographicGatewayArchitectureData = {
  "infographics": [
    {
      "id": "gateway-architecture",
      "title": "Gateway System Architecture",
      "nodes": [
        {
          "id": "gateway",
          "label": "gateway",
          "lowLevel": [
            "dispatch",
            "get_gateway",
            "get_arg",
            "is_no",
            "set_action_response",
            "get_action_response"
          ]
        },
        {
          "id": "request-object",
          "label": "request_object",
          "lowLevel": [
            "request_grammar",
            "command_args",
            "no_flags",
            "string_args",
            "int_args",
            "flag_args"
          ]
        },
        {
          "id": "response-object",
          "label": "response_object",
          "lowLevel": [
            "response_assembly",
            "output_buffer",
            "action_response",
            "error_collections"
          ]
        },
        {
          "id": "registry",
          "label": "registry",
          "lowLevel": [
            "command_registry_term",
            "handler_discovery",
            "handler_resolution"
          ]
        },
        {
          "id": "error-system",
          "label": "error_system",
          "lowLevel": [
            "error_coordination",
            "error_state_tracking",
            "request_error",
            "action_error",
            "backend_error"
          ]
        },
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
        }
      ],
      "connections": [
        {
          "from": "gateway",
          "to": "request-object",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "creates_request",
            "argument_access",
            "get_arg_calls",
            "is_no_checks"
          ]
        },
        {
          "from": "gateway",
          "to": "response-object",
          "type": "bidirectional",
          "description": "response_management",
          "lowLevel": [
            "creates_response",
            "output_buffer",
            "error_collection",
            "final_assembly"
          ]
        },
        {
          "from": "gateway",
          "to": "registry",
          "type": "bidirectional",
          "description": "handler_discovery",
          "lowLevel": [
            "uses_registry",
            "loads_handlers",
            "supplies_handlers"
          ]
        },
        {
          "from": "gateway",
          "to": "error-system",
          "type": "bidirectional",
          "description": "error_coordination",
          "lowLevel": [
            "coordinates_errors",
            "reports_errors",
            "error_state_tracking"
          ]
        },
        {
          "from": "gateway",
          "to": "debug-system",
          "type": "bidirectional",
          "description": "debug_management",
          "lowLevel": [
            "initializes_debug",
            "captures_messages",
            "debug_output"
          ]
        },
        {
          "from": "registry",
          "to": "request-object",
          "type": "forward",
          "description": "handler_lookup",
          "lowLevel": [
            "uses_command",
            "locates_handlers"
          ]
        },
        {
          "from": "error-system",
          "to": "response-object",
          "type": "forward",
          "description": "error_output",
          "lowLevel": [
            "adds_errors",
            "error_collections"
          ]
        },
        {
          "from": "debug-system",
          "to": "response-object",
          "type": "forward",
          "description": "debug_output",
          "lowLevel": [
            "appends_debug",
            "debug_messages"
          ]
        }
      ]
    }
  ],
  "positions": {
    "gateway-architecture": {
      "gateway": {
        "x": 956.5,
        "y": 415.5
      },
      "request-object": {
        "x": 1577.5,
        "y": 171.0063509461097
      },
      "response-object": {
        "x": 207.5,
        "y": 829.0063509461097
      },
      "registry": {
        "x": 1549.5,
        "y": 962.5
      },
      "error-system": {
        "x": 642.4999999999999,
        "y": 1070.9936490538903
      },
      "debug-system": {
        "x": 198.5,
        "y": 142.99364905389035
      }
    }
  }
};