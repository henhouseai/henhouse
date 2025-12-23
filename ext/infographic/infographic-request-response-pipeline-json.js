var infographicRequestResponsePipelineData = {
  "infographics": [
    {
      "id": "request-response-pipeline",
      "title": "Request/Response Pipeline",
      "nodes": [
        {
          "id": "request-object",
          "label": "request_object",
          "lowLevel": [
            "command_args",
            "string_args",
            "int_args",
            "flag_args",
            "no_flags",
            "get_arg",
            "is_no"
          ]
        },
        {
          "id": "tokenizer",
          "label": "tokenizer",
          "lowLevel": [
            "token_classification",
            "quote_detection"
          ]
        },
        {
          "id": "grammar-parser",
          "label": "grammar_parser",
          "lowLevel": [
            "request_parsing_pipeline"
          ]
        },
        {
          "id": "semantics",
          "label": "semantics",
          "lowLevel": [
            "request_object_construction"
          ]
        },
        {
          "id": "response-object",
          "label": "response_object",
          "lowLevel": [
            "output_buffer",
            "action_response",
            "error_collections",
            "response_assembly"
          ]
        }
      ],
      "connections": [
        {
          "from": "tokenizer",
          "to": "grammar-parser",
          "type": "forward",
          "description": "tokenization",
          "lowLevel": [
            "provides_tokens",
            "parsing_input"
          ]
        },
        {
          "from": "grammar-parser",
          "to": "semantics",
          "type": "forward",
          "description": "grammar_structure",
          "lowLevel": [
            "parsed_grammar",
            "structured_data"
          ]
        },
        {
          "from": "semantics",
          "to": "request-object",
          "type": "forward",
          "description": "request_construction",
          "lowLevel": [
            "builds_request",
            "populates_data"
          ]
        },
        {
          "from": "request-object",
          "to": "response-object",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "influences_structure",
            "uses_request_data"
          ]
        },
        {
          "from": "tokenizer",
          "to": "request-object",
          "type": "forward",
          "description": "token_data",
          "lowLevel": [
            "tokens_to_data"
          ]
        },
        {
          "from": "semantics",
          "to": "response-object",
          "type": "forward",
          "description": "assembly_guide",
          "lowLevel": [
            "structure_guide",
            "response_format"
          ]
        }
      ]
    }
  ],
  "positions": {
    "request-response-pipeline": {
      "request-object": {
        "x": 1525,
        "y": 813
      },
      "tokenizer": {
        "x": 1260.254248593737,
        "y": 1143.7641290737884
      },
      "grammar-parser": {
        "x": 690.7457514062631,
        "y": 1063.9463130731183
      },
      "semantics": {
        "x": 789.7457514062631,
        "y": 615.0536869268817
      },
      "response-object": {
        "x": 1232.2542485937367,
        "y": 386.23587092621165
      }
    }
  }
};