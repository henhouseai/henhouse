from typing import List

DEPLOY_WHITELIST: List[str] = [
    'nginx_flask/deploy/conf',
]

CLIENT_WHITELIST: List[str] = [
    'hh/deploy/flask/http_client.py',
    'hh/deploy/flask/mcp_client.py',
    'hh/deploy/flask/api_client.py',
    'hh/deploy/flask/download_client.py',
]

APP_WHITELIST: List[tuple] = [
    ('flask', 'hh/deploy/flask/app.py'),
    ('media', 'hh/deploy/flask/media_server.py'),
]