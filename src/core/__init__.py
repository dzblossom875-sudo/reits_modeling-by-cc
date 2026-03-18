"""
REITs Modeling Agent - Core Module
核心模块，包含配置、数据类型和异常定义
"""

from .config import (
    AssetType,
    ParamCategory,
    DEFAULT_DISCOUNT_RATES,
    DEFAULT_GROWTH_RATES,
    FORECAST_YEARS,
    INDUSTRY_BENCHMARKS,
)
from .types import (
    ExtractedParam,
    ExtractedParams,
    ParsedDocument,
    ValuationResult,
    ScenarioResult,
    RiskItem,
    ValidationIssue,
    Table,
    ProjectInfo,
)
from .exceptions import (
    REITsModelingError,
    DocumentParseError,
    ParameterExtractionError,
    ValidationError,
    CalculationError,
)

__all__ = [
    # Config
    "AssetType",
    "ParamCategory",
    "DEFAULT_DISCOUNT_RATES",
    "DEFAULT_GROWTH_RATES",
    "FORECAST_YEARS",
    "INDUSTRY_BENCHMARKS",
    # Types
    "ExtractedParam",
    "ExtractedParams",
    "ParsedDocument",
    "ValuationResult",
    "ScenarioResult",
    "RiskItem",
    "ValidationIssue",
    "Table",
    "ProjectInfo",
    # Exceptions
    "REITsModelingError",
    "DocumentParseError",
    "ParameterExtractionError",
    "ValidationError",
    "CalculationError",
]