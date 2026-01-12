var infographicHttpDeploymentArchitectureData = {
  "infographics": [
    {
      "id": "http-deployment-architecture",
      "title": "HTTP Deployment Architecture",
      "nodes": [
        {
          "id": "http-deployment",
          "label": "http_deployment",
          "lowLevel": [
            "flask_daemon_deployment",
            "subprocess_isolation",
            "url_to_argv_mapping"
          ]
        },
        {
          "id": "nginx-integration",
          "label": "nginx_integration",
          "lowLevel": [
            "static_asset_serving",
            "health_check_endpoint",
            "basic_auth"
          ]
        },
        {
          "id": "flask-daemon",
          "label": "flask_daemon_deployment",
          "lowLevel": [
            "tier_specific_flask_apps",
            "tier_specific_ports",
            "concurrency_limits",
            "timeout_handling"
          ]
        },
        {
          "id": "ubuntu-tiers",
          "label": "ubuntu_user_tiers",
          "lowLevel": [
            "guest_tier",
            "admin_tier",
            "root_tier",
            "tier_specific_credentials",
            "tier_specific_log_files"
          ]
        },
        {
          "id": "http-client",
          "label": "http_client",
          "lowLevel": [
            "subprocess_isolation",
            "url_to_argv_mapping"
          ]
        }
      ],
      "connections": [
        {
          "from": "nginx-integration",
          "to": "flask-daemon",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "proxies_requests",
            "listens_on_ports"
          ]
        },
        {
          "from": "http-deployment",
          "to": "flask-daemon",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "orchestrates_deployment",
            "deployed_via"
          ]
        },
        {
          "from": "ubuntu-tiers",
          "to": "flask-daemon",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "runs_separate_instance",
            "apps_run_as_users"
          ]
        },
        {
          "from": "http-client",
          "to": "flask-daemon",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "spawned_by_flask",
            "creates_subprocess"
          ]
        },
        {
          "from": "nginx-integration",
          "to": "http-deployment",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "configured_by_deployment",
            "sets_up_nginx"
          ]
        },
        {
          "from": "nginx-integration",
          "to": "ubuntu-tiers",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "routes_to_subdomains",
            "determines_routing"
          ]
        },
        {
          "from": "http-client",
          "to": "http-deployment",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "executes_requests",
            "uses_for_execution"
          ]
        },
        {
          "from": "http-deployment",
          "to": "ubuntu-tiers",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "sets_up_tiers",
            "configured_by_deployment_tiers"
          ]
        },
        {
          "from": "nginx-integration",
          "to": "http-client",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "triggers_subprocess",
            "returns_through_nginx"
          ]
        },
        {
          "from": "ubuntu-tiers",
          "to": "http-client",
          "type": "bidirectional",
          "description": "data_flow",
          "lowLevel": [
            "determines_permissions",
            "runs_with_credentials"
          ]
        }
      ]
    }
  ],
  "positions": {
    "http-deployment-architecture": {
      "http-deployment": {
        "x": 1775,
        "y": 481
      },
      "nginx-integration": {
        "x": 1724.254248593737,
        "y": 962.7641290737884
      },
      "flask-daemon": {
        "x": 672.7457514062631,
        "y": 1426.9463130731183
      },
      "ubuntu-tiers": {
        "x": 576.7457514062631,
        "y": 448.0536869268817
      },
      "http-client": {
        "x": 1213.2542485937367,
        "y": 224.23587092621165
      }
    }
  }
};