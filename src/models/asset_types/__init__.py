"""
各类REITs资产的特化处理
"""

from .industrial import IndustrialREIT
from .logistics import LogisticsREIT
from .housing import HousingREIT
from .infrastructure import InfrastructureREIT
from .hotel import HotelREIT

__all__ = [
    "IndustrialREIT",
    "LogisticsREIT",
    "HousingREIT",
    "InfrastructureREIT",
    "HotelREIT",
]
