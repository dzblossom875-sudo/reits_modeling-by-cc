"""
资产类型基类
定义各类REITs资产的特化接口
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

from ..dcf_model import DCFInputs
from ...core.types import ValuationResult
from ...core.config import AssetType


class AssetTypeHandler(ABC):
    """资产类型处理器基类"""

    ASSET_TYPE: AssetType = None

    @abstractmethod
    def get_required_params(self) -> List[str]:
        """获取该资产类型的必需参数"""
        pass

    @abstractmethod
    def get_optional_params(self) -> Dict[str, Any]:
        """获取该资产类型的可选参数及其默认值"""
        pass

    @abstractmethod
    def validate_params(self, inputs: DCFInputs) -> List[Dict[str, Any]]:
        """验证参数合理性"""
        pass

    @abstractmethod
    def calculate_kpi(self, result: ValuationResult) -> Dict[str, Any]:
        """计算该资产类型的特有KPI"""
        pass

    def get_industry_benchmarks(self) -> Dict[str, Any]:
        """获取行业基准值"""
        from ...core.config import INDUSTRY_BENCHMARKS
        return INDUSTRY_BENCHMARKS.get(self.ASSET_TYPE, {})
