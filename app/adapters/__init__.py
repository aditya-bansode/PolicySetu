"""
PolicySetu — Adapters Package
=============================
"""

from app.adapters.base_adapter import BaseSourceAdapter
from app.adapters.pib_adapter import PIBSourceAdapter
from app.adapters.maharashtra_gr_adapter import MaharashtraGRAdapter
from app.adapters.india_code_adapter import IndiaCodeAdapter
from app.adapters.egazette_adapter import EGazetteAdapter
from app.adapters.registry import get_adapter, get_all_registered_adapters

__all__ = [
    "BaseSourceAdapter",
    "PIBSourceAdapter",
    "MaharashtraGRAdapter",
    "IndiaCodeAdapter",
    "EGazetteAdapter",
    "get_adapter",
    "get_all_registered_adapters",
]
