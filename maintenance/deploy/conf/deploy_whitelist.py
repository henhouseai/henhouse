from typing import List

DEPLOY_WHITELIST: List[str] = [
    'maintenance/deploy/conf',
]

CLIENT_WHITELIST: List[str] = [
    'maintenance/maintenance_client.py',
]

APP_WHITELIST: List[tuple] = [
    ('maintenance', 'maintenance/deploy/apps/maintenance_worker.py'),
]