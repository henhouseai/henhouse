# Henhouse deployment user account suffixes configuration
from typing import List

# Henhouse tier configuration - change these names to modify user tiers
HENHOUSE_TIERS: List[str] = [
    'guest',      # Lowest privilege tier
    'verified',   # Verified user tier  
    'admin',      # Admin tier
    'root'        # Highest level tier (highest privilege)
]

