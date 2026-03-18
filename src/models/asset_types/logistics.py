"""
物流仓储REITs特化处理
"""

from typing import Dict, List, Any

from .base import AssetTypeHandler
from ..dcf_model import DCFInputs
from ...core.types import ValuationResult
from ...core.config import AssetType


class LogisticsREIT(AssetTypeHandler):
    """物流仓储REITs处理器"""

    ASSET_TYPE = AssetType.LOGISTICS

    def get_required_params(self) -> List[str]:
        return [
            "current_rent",
            "rent_growth_rate",
            "occupancy_rate",
            "total_area",
            "operating_expense",
            "discount_rate"
        ]

    def get_optional_params(self) -> Dict[str, Any]:
        return {
            "other_income_ratio": 0.01,
            "management_fee_ratio": 0.025,
            "maintenance_cost": 0,
            "capex": 0,
            "cap_rate": 0.055
        }

    def validate_params(self, inputs: DCFInputs) -> List[Dict[str, Any]]:
        """验证物流仓储参数合理性"""
        issues = []
        benchmarks = self.get_industry_benchmarks()

        # 租金范围检查（物流租金通常低于产业园）
        rent_range = benchmarks.get("rent_range", (30, 80))
        if inputs.current_rent < rent_range[0] or inputs.current_rent > rent_range[1]:
            issues.append({
                "level": "warning",
                "param": "current_rent",
                "message": f"当前租金 {inputs.current_rent} 元/㎡/月 超出物流仓储常见范围 {rent_range}",
            })

        # 出租率检查（物流出租率通常较高）
        occ_range = benchmarks.get("occupancy_range", (0.85, 0.98))
        if inputs.occupancy_rate < 0.80:
            issues.append({
                "level": "warning",
                "param": "occupancy_rate",
                "message": f"出租率 {inputs.occupancy_rate:.1%} 偏低",
            })

        return issues

    def calculate_kpi(self, result: ValuationResult) -> Dict[str, Any]:
        """计算物流仓储特有KPI"""
        kpi = {
            "asset_type": "物流仓储",
            "valuation_per_sqm": 0,
            "noi_yield": 0,  # NOI收益率
        }

        total_area = result.project_info.total_area
        if total_area > 0:
            kpi["valuation_per_sqm"] = round(result.npv * 10000 / total_area, 2)

        if result.cash_flows:
            first_year_noi = result.cash_flows[0].calculate_noi()
            if result.npv > 0:
                kpi["noi_yield"] = round(first_year_noi / result.npv, 4)

        return kpi
