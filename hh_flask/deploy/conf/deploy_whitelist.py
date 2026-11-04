from typing import List

DEPLOY_WHITELIST: List[str] = [
    'hh_flask/deploy/conf',
]

CLIENT_WHITELIST: List[str] = [
    'hh_flask/deploy/clients/http_client.py',
    'hh_flask/deploy/clients/mcp_client.py',
    'hh_flask/deploy/clients/api_client.py',
    'hh_flask/deploy/clients/download_client.py',
]

APP_WHITELIST: List[tuple] = [
    ('flask', 'hh_flask/deploy/apps/app.py'),
    ('media', 'hh_flask/deploy/apps/media_server.py'),
]