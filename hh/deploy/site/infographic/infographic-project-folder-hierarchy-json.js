var infographicProjectFolderHierarchyData = {
  "infographics": [
    {
      "id": "project-folder-hierarchy",
      "title": "Project Folder Hierarchy",
      "nodes": [
        {
          "id": "project-folder",
          "label": "project_folder",
          "lowLevel": []
        },
        {
          "id": "hh-folder",
          "label": "hh_folder",
          "lowLevel": []
        },
        {
          "id": "agents-folder",
          "label": "agents_folder",
          "lowLevel": []
        },
        {
          "id": "deploy-folder",
          "label": "deploy_folder",
          "lowLevel": [
            "cache_management",
            "deployment_configuration",
            "db_deployment",
            "flask_deployment",
            "git_deployment",
            "http_deployment",
            "srv_deployment",
            "users_deployment"
          ]
        },
        {
          "id": "gateway-folder",
          "label": "gateway_folder",
          "lowLevel": [
            "database_connection",
            "debug_system",
            "error_system",
            "command_registry_term",
            "request_object",
            "response_object"
          ]
        },
        {
          "id": "help-folder",
          "label": "help_folder",
          "lowLevel": [
            "help_command",
            "help_query",
            "help_registry",
            "help_markdown_parser",
            "help_markdown_files"
          ]
        },
        {
          "id": "image-folder",
          "label": "image_folder",
          "lowLevel": []
        },
        {
          "id": "page-folder",
          "label": "page_folder",
          "lowLevel": [
            "page_class",
            "page_mixins",
            "page_registry",
            "page_class_registry",
            "page_actions",
            "image_operations",
            "page_rendering",
            "page_utilities"
          ]
        },
        {
          "id": "render-folder",
          "label": "render_folder",
          "lowLevel": []
        },
        {
          "id": "tp-folder",
          "label": "tp_folder",
          "lowLevel": []
        },
        {
          "id": "custom-project-add-ins",
          "label": "custom_project_add_ins",
          "lowLevel": []
        },
        {
          "id": "context-folder",
          "label": "context_folder",
          "lowLevel": [
            {
              "term": "context",
              "display": "Henhouse System"
            },
            {
              "term": "context",
              "display": "Custom project add-ins"
            },
            {
              "term": "context",
              "display": "Other project files"
            }
          ]
        },
        {
          "id": "convenience-scripts",
          "label": "convenience_scripts",
          "lowLevel": [
            "hen_py",
            "hen_ps1",
            "stage_py",
            "stage_ps1"
          ]
        },
        {
          "id": "other-project-files",
          "label": "other_project_files",
          "lowLevel": []
        }
      ],
      "connections": [
        {
          "from": "project-folder",
          "to": "hh-folder",
          "type": "forward",
          "description": "contains",
          "lowLevel": []
        },
        {
          "from": "project-folder",
          "to": "context-folder",
          "type": "forward",
          "description": "contains",
          "lowLevel": []
        },
        {
          "from": "project-folder",
          "to": "convenience-scripts",
          "type": "forward",
          "description": "contains",
          "lowLevel": []
        },
        {
          "from": "project-folder",
          "to": "other-project-files",
          "type": "forward",
          "description": "contains",
          "lowLevel": []
        },
        {
          "from": "hh-folder",
          "to": "agents-folder",
          "type": "forward",
          "description": "contains",
          "lowLevel": []
        },
        {
          "from": "hh-folder",
          "to": "deploy-folder",
          "type": "forward",
          "description": "contains",
          "lowLevel": []
        },
        {
          "from": "hh-folder",
          "to": "gateway-folder",
          "type": "forward",
          "description": "contains",
          "lowLevel": []
        },
        {
          "from": "hh-folder",
          "to": "help-folder",
          "type": "forward",
          "description": "contains",
          "lowLevel": []
        },
        {
          "from": "hh-folder",
          "to": "image-folder",
          "type": "forward",
          "description": "contains",
          "lowLevel": []
        },
        {
          "from": "hh-folder",
          "to": "page-folder",
          "type": "forward",
          "description": "contains",
          "lowLevel": []
        },
        {
          "from": "hh-folder",
          "to": "render-folder",
          "type": "forward",
          "description": "contains",
          "lowLevel": []
        },
        {
          "from": "hh-folder",
          "to": "tp-folder",
          "type": "forward",
          "description": "contains",
          "lowLevel": []
        },
        {
          "from": "hh-folder",
          "to": "custom-project-add-ins",
          "type": "forward",
          "description": "contains",
          "lowLevel": []
        }
      ]
    }
  ],
  "positions": {
    "project-folder-hierarchy": {
      "project-folder": {
        "x": -300,
        "y": -500,
        "boxOffsetY": -4.30120849609375,
        "boxWidth": 137.73493194580078,
        "boxHeight": 46.6024169921875
      },
      "hh-folder": {
        "x": -200,
        "y": -195.7078978223726,
        "boxOffsetY": -4.301210085395752,
        "boxWidth": 99.2605209350586,
        "boxHeight": 46.602420170791476
      },
      "agents-folder": {
        "x": 260,
        "y": 200,
        "boxOffsetY": -4.301200866699219,
        "boxWidth": 130.7426986694336,
        "boxHeight": 46.60240173339844
      },
      "deploy-folder": {
        "x": -680,
        "y": 200,
        "boxOffsetY": 63.858771324157715,
        "boxWidth": 163.0588150024414,
        "boxHeight": 182.9223461151123
      },
      "gateway-folder": {
        "x": -885,
        "y": 200,
        "boxOffsetY": 47.256361961364746,
        "boxWidth": 174.9094696044922,
        "boxHeight": 149.71752738952637
      },
      "help-folder": {
        "x": -505,
        "y": 200,
        "boxOffsetY": -4.301200866699219,
        "boxWidth": 114.65055847167969,
        "boxHeight": 46.60240173339844
      },
      "image-folder": {
        "x": -200,
        "y": 200,
        "boxOffsetY": -4.301200866699219,
        "boxWidth": 122.34516143798828,
        "boxHeight": 46.60240173339844
      },
      "page-folder": {
        "x": -355,
        "y": 200,
        "boxOffsetY": -4.301200866699219,
        "boxWidth": 114.65055847167969,
        "boxHeight": 46.60240173339844
      },
      "render-folder": {
        "x": -40,
        "y": 200,
        "boxOffsetY": -4.301200866699219,
        "boxWidth": 130.04256439208984,
        "boxHeight": 46.60240173339844
      },
      "tp-folder": {
        "x": 110,
        "y": 200,
        "boxOffsetY": -4.301200866699219,
        "boxWidth": 99.2605209350586,
        "boxHeight": 46.60240173339844
      },
      "context-folder": {
        "x": -850,
        "y": -230,
        "boxOffsetY": 22.35273265838623,
        "boxWidth": 247.47178649902344,
        "boxHeight": 99.91032981872559
      },
      "convenience-scripts": {
        "x": -570,
        "y": -230,
        "boxOffsetY": 30.653937339782715,
        "boxWidth": 176.2076416015625,
        "boxHeight": 116.51273918151855
      },
      "other-project-files": {
        "x": 460,
        "y": -195.72952267735465,
        "boxOffsetY": -4.301208509955501,
        "boxWidth": 176.2076416015625,
        "boxHeight": 46.60241701991097
      },
      "custom-project-add-ins": {
        "x": 460,
        "y": 200,
        "boxOffsetY": -4.301200866699219,
        "boxWidth": 199.29017639160156,
        "boxHeight": 46.60240173339844
      },
      "project-folder->hh-folder": {
        "x": -200,
        "y": -350,
        "boxOffsetY": -3.90093994140625,
        "boxWidth": 80,
        "boxHeight": 27.8018798828125
      },
      "hh-folder->agents-folder": {
        "x": 260,
        "y": 50,
        "boxOffsetY": -3.9009361267089844,
        "boxWidth": 80,
        "boxHeight": 27.80187225341797
      },
      "hh-folder->deploy-folder": {
        "x": -680,
        "y": 50,
        "boxOffsetY": -3.9009361267089844,
        "boxWidth": 80,
        "boxHeight": 27.80187225341797
      },
      "hh-folder->gateway-folder": {
        "x": -885,
        "y": 50,
        "boxOffsetY": -3.9009361267089844,
        "boxWidth": 80,
        "boxHeight": 27.80187225341797
      },
      "hh-folder->help-folder": {
        "x": -505,
        "y": 50,
        "boxOffsetY": -3.9009361267089844,
        "boxWidth": 80,
        "boxHeight": 27.80187225341797
      },
      "hh-folder->image-folder": {
        "x": -200,
        "y": 50,
        "boxOffsetY": -3.9009361267089844,
        "boxWidth": 80,
        "boxHeight": 27.80187225341797
      },
      "hh-folder->page-folder": {
        "x": -355,
        "y": 50,
        "boxOffsetY": -3.9009361267089844,
        "boxWidth": 80,
        "boxHeight": 27.80187225341797
      },
      "hh-folder->render-folder": {
        "x": -40,
        "y": 50,
        "boxOffsetY": -3.9009361267089844,
        "boxWidth": 80,
        "boxHeight": 27.80187225341797
      },
      "hh-folder->tp-folder": {
        "x": 110,
        "y": 50,
        "boxOffsetY": -3.9009361267089844,
        "boxWidth": 80,
        "boxHeight": 27.80187225341797
      },
      "project-folder->context-folder": {
        "x": -850,
        "y": -350,
        "boxOffsetY": -3.90093994140625,
        "boxWidth": 80,
        "boxHeight": 27.8018798828125
      },
      "project-folder->convenience-scripts": {
        "x": -570,
        "y": -350,
        "boxOffsetY": -3.90093994140625,
        "boxWidth": 80,
        "boxHeight": 27.8018798828125
      },
      "project-folder->other-project-files": {
        "x": 460,
        "y": -340,
        "boxOffsetY": -3.90093994140625,
        "boxWidth": 80,
        "boxHeight": 27.8018798828125
      },
      "hh-folder->custom-project-add-ins": {
        "x": 460,
        "y": 50,
        "boxOffsetY": -3.9009361267089844,
        "boxWidth": 80,
        "boxHeight": 27.80187225341797
      }
    }
  }
};