"""
PolicySetu — Source Adapter Registry
====================================
Central registry mapping configured GovernmentSource entities to verified adapters.
"""

from typing import Dict, Type, Optional, Any
from app.adapters.base_adapter import BaseSourceAdapter
from app.adapters.pib_adapter import PIBSourceAdapter
from app.adapters.maharashtra_gr_adapter import MaharashtraGRAdapter
from app.adapters.india_code_adapter import IndiaCodeAdapter
from app.adapters.egazette_adapter import EGazetteAdapter
from app.adapters.mahadbt_adapter import MahaDBTAdapter

# Mapping by source identifier key
ADAPTER_MAP: Dict[str, Type[BaseSourceAdapter]] = {
    "pib": PIBSourceAdapter,
    "maharashtra_gr": MaharashtraGRAdapter,
    "india_code": IndiaCodeAdapter,
    "egazette": EGazetteAdapter,
    "mahadbt": MahaDBTAdapter,
}

# Name aliases for seamless lookup from GovernmentSource database records
ALIAS_MAP: Dict[str, str] = {
    "press information bureau": "pib",
    "pib": "pib",
    "maharashtra government resolutions": "maharashtra_gr",
    "maharashtra govt. resolutions": "maharashtra_gr",
    "maharashtra_gr": "maharashtra_gr",
    "india code legislative portal": "india_code",
    "india code": "india_code",
    "india_code": "india_code",
    "the gazette of india (e-gazette)": "egazette",
    "e-gazette of india": "egazette",
    "egazette": "egazette",
    "mahadbt scholarship portal": "mahadbt",
    "mahadbt portal": "mahadbt",
    "mahadbt": "mahadbt",
    "aaple sarkar dbt": "mahadbt",
}


def get_adapter_key(identifier: str) -> Optional[str]:
    """Resolve source name or code to registry key."""
    if not identifier:
        return None
    clean = identifier.strip().lower()
    return ALIAS_MAP.get(clean) or (clean if clean in ADAPTER_MAP else None)


def get_adapter(identifier: str) -> Optional[BaseSourceAdapter]:
    """Instantiate adapter for a given source name or code."""
    key = get_adapter_key(identifier)
    if key and key in ADAPTER_MAP:
        return ADAPTER_MAP[key]()
    return None


def get_all_registered_adapters() -> Dict[str, BaseSourceAdapter]:
    """Return dictionary of all registered adapter instances."""
    return {k: cls() for k, cls in ADAPTER_MAP.items()}
