"""
保障性租赁住房REITs特化处理
"""

from typing import Dict, List, Any

from .base import AssetTypeHandler
from ..dcf_model import DCFInputs
from ...core.types import ValuationResult
from ...core.config import AssetType


class HousingREIT(AssetTypeHandler):
    """保障性租赁住房REITs处理器"""

    ASSET_TYPE = AssetType.HOUSING

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
            "management_fee_ratio": 0.03,
            "maintenance_cost": 0,
            "capex": 0,
            "cap_rate": 0.05
        }

    def validate_params(self, inputs: DCFInputs) -> List[Dict[str, Any]]:
        """验证保障房参数合理性"""
        issues = []
        benchmarks = self.get_industry_benchmarks()

        # 租金增长限制（保障房通常有租金涨幅限制）
        if inputs.rent_growth_rate > 0.03:
            issues.append({
                "level": "warning",
                "param": "rent_growth_rate",
                "message": f"租金增长率 {inputs.rent_growth_rate:.2%} 偏高",
                "suggestion": "保障房通常有租金涨幅限制（如每年不超过5%）"
            })

        # 出租率检查（保障房出租率通常很高）
        if inputs.occupancy_rate < 0.90:
            issues.append({
                "level": "warning",
                "param": "occupancy_rate",
                "message": f"入住率 {inputs.occupancy_rate:.1%} 偏低",
                "suggestion": "保障房通常需求稳定，入住率应在90%以上"
            })

        # 运营费用率检查（保障房运营成本相对较高）
        if inputs.operating_expense_ratio < 0.15:
            issues.append({
                "level": "info",
                "param": "operating_expense_ratio",
                "message": "保障房运营费用率偏低，可能低估了社区服务、维修等成本"
            })

        return issues

    def calculate_kpi(self, result: ValuationResult) -> Dict[str, Any]:
        """计算保障房特有KPI"""
        kpi = {
            "asset_type": "保障性租赁住房",
            "valuation_per_sqm": 0,
            "rent_per_room_monthly": 0,  # 估算每间房月租金
        }

        total_area = result.project_info.total_area
        if total_area > 0:
            kpi["valuation_per_sqm"] = round(result.npv * 10000 / total_area, 2)

            # 估算每间房月租金（假设每间35㎡）
            avg_room_size = 35
            estimated_rooms = total_area / avg_room_size
            if result.cash_flows and estimated_rooms > 0:
                monthly_rent = result.cash_flows[0].rental_income * 10000 / 12 / estimated_rooms
                kpi["rent_per_room_monthly"] = round(monthly_rent, 2)

        return kpi
