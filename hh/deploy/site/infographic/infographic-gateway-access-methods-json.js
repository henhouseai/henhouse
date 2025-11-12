var infographicGatewayAccessMethodsData = {
  "infographics": [
    {
      "id": "gateway-access-methods",
      "title": "Gateway Access Methods",
      "nodes": [
        {
          "id": "gateway",
          "label": "gateway",
          "lowLevel": []
        },
        {
          "id": "cli-human-user",
          "label": "cli_human_user",
          "lowLevel": []
        },
        {
          "id": "guest-agent-spawn-daemon",
          "label": "guest_agent_spawn_daemon",
          "lowLevel": []
        },
        {
          "id": "verified-agent-spawn-daemon",
          "label": "verified_agent_spawn_daemon",
          "lowLevel": []
        },
        {
          "id": "admin-agent-spawn-daemon",
          "label": "admin_agent_spawn_daemon",
          "lowLevel": []
        },
        {
          "id": "root-agent-spawn-daemon",
          "label": "root_agent_spawn_daemon",
          "lowLevel": []
        },
        {
          "id": "guest-cli-agent",
          "label": "guest_cli_agent",
          "lowLevel": []
        },
        {
          "id": "verified-cli-agent",
          "label": "verified_cli_agent",
          "lowLevel": []
        },
        {
          "id": "admin-cli-agent",
          "label": "admin_cli_agent",
          "lowLevel": []
        },
        {
          "id": "root-cli-agent",
          "label": "root_cli_agent",
          "lowLevel": []
        },
        {
          "id": "web-user",
          "label": "web_user",
          "lowLevel": []
        },
        {
          "id": "guest-web-user",
          "label": "guest_web_user",
          "lowLevel": []
        },
        {
          "id": "verified-web-user",
          "label": "verified_web_user",
          "lowLevel": []
        },
        {
          "id": "admin-web-user",
          "label": "admin_web_user",
          "lowLevel": []
        },
        {
          "id": "root-web-user",
          "label": "root_web_user",
          "lowLevel": []
        },
        {
          "id": "external-agent",
          "label": "external_agent",
          "lowLevel": []
        }
      ],
      "connections": [
        {
          "from": "gateway",
          "to": "cli-human-user",
          "type": "bidirectional",
          "description": "direct_python_access",
          "lowLevel": []
        },
        {
          "from": "gateway",
          "to": "guest-cli-agent",
          "type": "bidirectional",
          "description": "mcp_protocol",
          "lowLevel": [
            {
              "term": "db_read_access",
              "display": "Limited"
            },
            {
              "term": "db_write_access",
              "display": "No"
            },
            {
              "term": "file_read_access",
              "display": "Limited"
            },
            {
              "term": "file_write_access",
              "display": "No"
            }
          ]
        },
        {
          "from": "gateway",
          "to": "verified-cli-agent",
          "type": "bidirectional",
          "description": "mcp_protocol",
          "lowLevel": [
            {
              "term": "db_read_access",
              "display": "Limited"
            },
            {
              "term": "db_write_access",
              "display": "Specific Tables"
            },
            {
              "term": "file_read_access",
              "display": "Limited"
            },
            {
              "term": "file_write_access",
              "display": "No"
            }
          ]
        },
        {
          "from": "gateway",
          "to": "admin-cli-agent",
          "type": "bidirectional",
          "description": "mcp_protocol",
          "lowLevel": [
            {
              "term": "db_read_access",
              "display": ""
            },
            {
              "term": "db_write_access",
              "display": "No Schema Changes"
            },
            {
              "term": "file_read_access",
              "display": "Broad"
            },
            {
              "term": "file_write_access",
              "display": "Specific Folders"
            }
          ]
        },
        {
          "from": "gateway",
          "to": "root-cli-agent",
          "type": "bidirectional",
          "description": "mcp_protocol",
          "lowLevel": [
            {
              "term": "db_read_access",
              "display": "Full"
            },
            {
              "term": "db_write_access",
              "display": "Full"
            },
            {
              "term": "db_write_access",
              "display": "Create Tables Modify Schema"
            },
            {
              "term": "file_read_access",
              "display": "Full"
            },
            {
              "term": "file_write_access",
              "display": "Full"
            }
          ]
        },
        {
          "from": "web-user",
          "to": "guest-web-user",
          "type": "bidirectional",
          "description": "routes_request",
          "lowLevel": []
        },
        {
          "from": "web-user",
          "to": "verified-web-user",
          "type": "bidirectional",
          "description": "routes_request",
          "lowLevel": []
        },
        {
          "from": "web-user",
          "to": "admin-web-user",
          "type": "bidirectional",
          "description": "routes_request",
          "lowLevel": []
        },
        {
          "from": "web-user",
          "to": "root-web-user",
          "type": "bidirectional",
          "description": "routes_request",
          "lowLevel": []
        },
        {
          "from": "gateway",
          "to": "guest-web-user",
          "type": "bidirectional",
          "description": "flask_daemon",
          "lowLevel": [
            "http_client",
            "mcp_client"
          ]
        },
        {
          "from": "gateway",
          "to": "verified-web-user",
          "type": "bidirectional",
          "description": "flask_daemon",
          "lowLevel": [
            "http_client",
            "mcp_client"
          ]
        },
        {
          "from": "gateway",
          "to": "admin-web-user",
          "type": "bidirectional",
          "description": "flask_daemon",
          "lowLevel": [
            "http_client",
            "mcp_client"
          ]
        },
        {
          "from": "gateway",
          "to": "root-web-user",
          "type": "bidirectional",
          "description": "flask_daemon",
          "lowLevel": [
            "http_client",
            "mcp_client"
          ]
        },
        {
          "from": "guest-web-user",
          "to": "guest-agent-spawn-daemon",
          "type": "bidirectional",
          "description": "routes_request",
          "lowLevel": []
        },
        {
          "from": "guest-agent-spawn-daemon",
          "to": "guest-cli-agent",
          "type": "bidirectional",
          "description": "routes_request",
          "lowLevel": []
        },
        {
          "from": "verified-web-user",
          "to": "verified-agent-spawn-daemon",
          "type": "bidirectional",
          "description": "routes_request",
          "lowLevel": []
        },
        {
          "from": "verified-agent-spawn-daemon",
          "to": "verified-cli-agent",
          "type": "bidirectional",
          "description": "routes_request",
          "lowLevel": []
        },
        {
          "from": "admin-web-user",
          "to": "admin-agent-spawn-daemon",
          "type": "bidirectional",
          "description": "routes_request",
          "lowLevel": []
        },
        {
          "from": "admin-agent-spawn-daemon",
          "to": "admin-cli-agent",
          "type": "bidirectional",
          "description": "routes_request",
          "lowLevel": []
        },
        {
          "from": "root-web-user",
          "to": "root-agent-spawn-daemon",
          "type": "bidirectional",
          "description": "routes_request",
          "lowLevel": []
        },
        {
          "from": "root-agent-spawn-daemon",
          "to": "root-cli-agent",
          "type": "bidirectional",
          "description": "routes_request",
          "lowLevel": []
        },
        {
          "from": "gateway",
          "to": "external-agent",
          "type": "bidirectional",
          "description": "mcp_protocol",
          "lowLevel": []
        }
      ]
    }
  ],
  "positions": {
    "gateway-access-methods": {
      "gateway": {
        "x": 1000,
        "y": 1004.5986404418945,
        "boxOffsetY": -4.500003814697266,
        "boxWidth": 83.93359375,
        "boxHeight": 47.00000762939453
      },
      "cli-human-user": {
        "x": 1600,
        "y": 1104.582967056357,
        "boxOffsetY": -4.499979621928333,
        "boxWidth": 137.76171875,
        "boxHeight": 46.99995924385689
      },
      "guest-cli-agent": {
        "x": 360.1341700638309,
        "y": 608.1772185245136,
        "boxOffsetY": -4.499986215381796,
        "boxWidth": 145.4609375,
        "boxHeight": 46.99997243076359
      },
      "verified-cli-agent": {
        "x": 765.3487782393661,
        "y": 607.7540606713537,
        "boxOffsetY": -4.499985657942489,
        "boxWidth": 168.80078125,
        "boxHeight": 46.99997131588498
      },
      "admin-cli-agent": {
        "x": 1310.0929910690143,
        "y": 619.113468484241,
        "boxOffsetY": -4.500002064386194,
        "boxWidth": 145.7109375,
        "boxHeight": 47.000004128772275
      },
      "root-cli-agent": {
        "x": 1676.264545643487,
        "y": 611.8289160718896,
        "boxOffsetY": -4.499998807429165,
        "boxWidth": 137.76171875,
        "boxHeight": 46.99999761485833
      },
      "web-user": {
        "x": 1000,
        "y": 4.248258412003821,
        "boxOffsetY": -4.4999999106527895,
        "boxWidth": 91.578125,
        "boxHeight": 46.99999982130558
      },
      "guest-web-user": {
        "x": 324.8723129572247,
        "y": 240.21933543980117,
        "boxOffsetY": -4.500002802908398,
        "boxWidth": 137.76171875,
        "boxHeight": 47.000005605816796
      },
      "verified-web-user": {
        "x": 818.3487782393661,
        "y": 244.24593932864627,
        "boxOffsetY": -4.499999083268449,
        "boxWidth": 161.10546875,
        "boxHeight": 46.9999981665369
      },
      "admin-web-user": {
        "x": 1243.1341700638309,
        "y": 247.82278147548652,
        "boxOffsetY": -4.499998525829199,
        "boxWidth": 138.01171875,
        "boxHeight": 46.9999970516584
      },
      "root-web-user": {
        "x": 1703.0161866827889,
        "y": 234.25403352658577,
        "boxOffsetY": -4.500002603136636,
        "boxWidth": 130.06640625,
        "boxHeight": 47.00000520627327
      },
      "external-agent": {
        "x": 400,
        "y": 1104.582964393451,
        "boxOffsetY": -4.499978290475383,
        "boxWidth": 137.76171875,
        "boxHeight": 46.99995658095099
      },
      "guest-agent-spawn-daemon": {
        "x": 200,
        "y": 404.2482433432022,
        "boxOffsetY": -4.500006681366756,
        "boxWidth": 214.734375,
        "boxHeight": 47.000013362733455
      },
      "verified-agent-spawn-daemon": {
        "x": 644.1708580912725,
        "y": 437.96988312782173,
        "boxOffsetY": -4.500001988715553,
        "boxWidth": 238.078125,
        "boxHeight": 47.000003977431106
      },
      "admin-agent-spawn-daemon": {
        "x": 1393.5,
        "y": 436,
        "boxOffsetY": -4.5,
        "boxWidth": 214.984375,
        "boxHeight": 47
      },
      "root-agent-spawn-daemon": {
        "x": 1800,
        "y": 404.2482538630101,
        "boxOffsetY": -4.499996682481594,
        "boxWidth": 207.0390625,
        "boxHeight": 46.999993364963245
      },
      "gateway->cli-human-user": {
        "x": 1320,
        "y": 1004.1322595838379,
        "boxOffsetY": -3.9999982001221497,
        "boxWidth": 136.95703125,
        "boxHeight": 27.999996400244186
      },
      "gateway->guest-cli-agent": {
        "x": 544.0199559075782,
        "y": 858.2558053382146,
        "boxOffsetY": 22.124996500814518,
        "boxWidth": 135.0703125,
        "boxHeight": 80.25000699837085
      },
      "gateway->verified-cli-agent": {
        "x": 854.7322387821671,
        "y": 755.3833832471713,
        "boxOffsetY": 22.124989284617527,
        "boxWidth": 169.70703125,
        "boxHeight": 80.25002143076506
      },
      "gateway->admin-cli-agent": {
        "x": 1223.1544522485913,
        "y": 743.1752129658674,
        "boxOffsetY": 22.12500948386321,
        "boxWidth": 184.55078125,
        "boxHeight": 80.2499810322737
      },
      "gateway->root-cli-agent": {
        "x": 1527.955547378544,
        "y": 846.8601818861763,
        "boxOffsetY": 28.374993285427422,
        "boxWidth": 200,
        "boxHeight": 92.75001342914504
      },
      "web-user->guest-web-user": {
        "x": 680.0684293003559,
        "y": 154.6952096839559,
        "boxOffsetY": -4.000001997739673,
        "boxWidth": 100.671875,
        "boxHeight": 28.000003995479346
      },
      "web-user->verified-web-user": {
        "x": 926.8066619414266,
        "y": 156.70851162837846,
        "boxOffsetY": -4.000000137919699,
        "boxWidth": 100.671875,
        "boxHeight": 28.000000275839398
      },
      "web-user->admin-web-user": {
        "x": 1139.199357853659,
        "y": 158.49693270179858,
        "boxOffsetY": -3.9999998592000736,
        "boxWidth": 100.671875,
        "boxHeight": 27.999999718400147
      },
      "web-user->root-web-user": {
        "x": 1369.140366163138,
        "y": 151.7125587273482,
        "boxOffsetY": -4.000001897853792,
        "boxWidth": 100.671875,
        "boxHeight": 28.000003795707585
      },
      "gateway->guest-web-user": {
        "x": 601.1105271258782,
        "y": 720.415572828905,
        "boxOffsetY": 9.625007775000654,
        "boxWidth": 100.43359375,
        "boxHeight": 55.249984449998806
      },
      "gateway->verified-web-user": {
        "x": 948.1270597682654,
        "y": 655.7542049394551,
        "boxOffsetY": 9.625003243163064,
        "boxWidth": 100.43359375,
        "boxHeight": 55.24999351367387
      },
      "gateway->admin-web-user": {
        "x": 1081.18119612901,
        "y": 454.8690262970267,
        "boxOffsetY": 9.62499612883039,
        "boxWidth": 100.43359375,
        "boxHeight": 55.25000774233922
      },
      "gateway->root-web-user": {
        "x": 1451.8919969594579,
        "y": 703.9590265733982,
        "boxOffsetY": 9.625009418379022,
        "boxWidth": 100.43359375,
        "boxHeight": 55.249981163241955
      },
      "guest-web-user->guest-agent-spawn-daemon": {
        "x": 247.07450412693083,
        "y": 339.49801536821906,
        "boxOffsetY": -3.9999995053985913,
        "boxWidth": 100.671875,
        "boxHeight": 27.999999010797183
      },
      "guest-agent-spawn-daemon->guest-cli-agent": {
        "x": 264.7054326802339,
        "y": 523.4769569105753,
        "boxOffsetY": -4.000014099818941,
        "boxWidth": 100.671875,
        "boxHeight": 28.000028199637768
      },
      "verified-web-user->verified-agent-spawn-daemon": {
        "x": 731.2598181653193,
        "y": 341.107911228234,
        "boxOffsetY": -4.000000535992001,
        "boxWidth": 100.671875,
        "boxHeight": 28.000001071984002
      },
      "verified-agent-spawn-daemon->verified-cli-agent": {
        "x": 704.7598181653193,
        "y": 522.8619718995877,
        "boxOffsetY": -3.9999861939344328,
        "boxWidth": 100.671875,
        "boxHeight": 27.99997238786898
      },
      "admin-web-user->admin-agent-spawn-daemon": {
        "x": 1318.3170850319154,
        "y": 341.91139073774326,
        "boxOffsetY": -4.000006892309159,
        "boxWidth": 100.671875,
        "boxHeight": 28.00001378461826
      },
      "admin-agent-spawn-daemon->admin-cli-agent": {
        "x": 1379.406040476465,
        "y": 528.3344679024573,
        "boxOffsetY": -3.9999976231036953,
        "boxWidth": 100.671875,
        "boxHeight": 27.999995246207277
      },
      "root-web-user->root-agent-spawn-daemon": {
        "x": 1792.9226642957583,
        "y": 332.61195832720375,
        "boxOffsetY": -3.9999946665315633,
        "boxWidth": 100.671875,
        "boxHeight": 27.999989333063127
      },
      "root-agent-spawn-daemon->root-cli-agent": {
        "x": 1779.5468437761074,
        "y": 521.3993995998557,
        "boxOffsetY": -3.999992768677771,
        "boxWidth": 100.671875,
        "boxHeight": 27.999985537355656
      },
      "gateway->external-agent": {
        "x": 700,
        "y": 1004.1322775826167,
        "boxOffsetY": -4.000007199511515,
        "boxWidth": 88.57421875,
        "boxHeight": 28.000014399022916
      }
    }
  }
};