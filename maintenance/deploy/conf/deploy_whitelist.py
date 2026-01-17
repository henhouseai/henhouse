from typing import List

DEPLOY_WHITELIST: List[str] = [
    'maintenance/deploy/conf',
]

CLIENT_WHITELIST: List[str] = [
    'hh/deploy/maint/maintenance_client.py',
]

APP_WHITELIST: List[tuple] = [
    ('maintenance', 'hh/deploy/maintenance/worker.py'),
]