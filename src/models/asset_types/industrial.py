"""
产业园REITs特化处理
"""

from typing import Dict, List, Any

from .base import AssetTypeHandler
from ..dcf_model import DCFInputs
from ...core.types import ValuationResult
from ...core.config import AssetType


class IndustrialREIT(AssetTypeHandler):
    """产业园REITs处理器"""

    ASSET_TYPE = AssetType.INDUSTRIAL

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
            "other_income_ratio": 0.02,        # 其他收入占2%
            "management_fee_ratio": 0.03,      # 管理费率3%
            "maintenance_cost": 0,             # 维护费用
            "capex": 0,                        # 资本性支出
            "cap_rate": 0.065                  # 资本化率6.5%
        }

    def validate_params(self, inputs: DCFInputs) -> List[Dict[str, Any]]:
        """验证产业园参数合理性"""
        issues = []
        benchmarks = self.get_industry_benchmarks()

        # 租金范围检查
        rent_range = benchmarks.get("rent_range", (50, 150))
        if inputs.current_rent < rent_range[0] or inputs.current_rent > rent_range[1]:
            issues.append({
                "level": "warning",
                "param": "current_rent",
                "message": f"当前租金 {inputs.current_rent} 元/㎡/月 超出行业常见范围 {rent_range}",
                "suggestion": "请确认租金单位是否正确（应为元/㎡/月）"
            })

        # 出租率检查
        occ_range = benchmarks.get("occupancy_range", (0.75, 0.95))
        if inputs.occupancy_rate < occ_range[0]:
            issues.append({
                "level": "warning",
                "param": "occupancy_rate",
                "message": f"出租率 {inputs.occupancy_rate:.1%} 低于行业平均水平",
                "suggestion": "该项目可能存在空置风险"
            })

        # 运营费用率检查
        opex_range = benchmarks.get("opex_ratio", (0.15, 0.25))
        if inputs.operating_expense_ratio < opex_range[0]:
            issues.append({
                "level": "info",
                "param": "operating_expense_ratio",
                "message": "运营费用率偏低，可能低估了实际运营成本"
            })

        return issues

    def calculate_kpi(self, result: ValuationResult) -> Dict[str, Any]:
        """计算产业园特有KPI"""
        kpi = {
            "asset_type": "产业园",
            "valuation_per_sqm": 0,  # 每平米估值
            "cap_rate_implied": 0,   # 隐含资本化率
        }

        # 计算每平米估值
        total_area = result.project_info.total_area
        if total_area > 0:
            kpi["valuation_per_sqm"] = round(result.npv * 10000 / total_area, 2)

        # 计算隐含资本化率
        if result.cash_flows:
            first_year_noi = result.cash_flows[0].calculate_noi()
            if result.npv > 0:
                kpi["cap_rate_implied"] = round(first_year_noi / result.npv, 4)

        return kpi
