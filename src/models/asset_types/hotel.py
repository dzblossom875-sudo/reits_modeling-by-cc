"""
酒店基础设施REITs特化处理
"""

from typing import Dict, List, Any

from .base import AssetTypeHandler
from ..dcf_model import DCFInputs
from ...core.types import ValuationResult
from ...core.config import AssetType


class HotelREIT(AssetTypeHandler):
    """酒店REITs处理器"""

    ASSET_TYPE = AssetType.HOTEL

    def get_required_params(self) -> List[str]:
        return [
            "adr",                    # 平均房价
            "occupancy_rate",         # 入住率
            "room_count",             # 房间数
            "operating_expense",      # 运营费用
            "discount_rate"
        ]

    def get_optional_params(self) -> Dict[str, Any]:
        return {
            "fb_revenue_ratio": 0.30,     # 餐饮收入占比
            "rent_growth_rate": 0.03,     # ADR增长率
            "management_fee_ratio": 0.03,
            "capex": 0,
            "cap_rate": 0.07
        }

    def validate_params(self, inputs: DCFInputs) -> List[Dict[str, Any]]:
        """验证酒店参数合理性"""
        issues = []
        benchmarks = self.get_industry_benchmarks()

        # ADR范围检查
        adr_range = benchmarks.get("adr_range", (300, 800))
        if inputs.adr < adr_range[0] or inputs.adr > adr_range[1]:
            issues.append({
                "level": "warning",
                "param": "adr",
                "message": f"平均房价 {inputs.adr} 元/晚 超出常见范围 {adr_range}",
                "suggestion": "请确认酒店定位和星级"
            })

        # 入住率检查
        occ_range = benchmarks.get("occupancy_range", (0.60, 0.80))
        if inputs.occupancy_rate > 0.85:
            issues.append({
                "level": "warning",
                "param": "occupancy_rate",
                "message": f"入住率 {inputs.occupancy_rate:.1%} 偏高",
                "suggestion": "酒店入住率通常受季节性影响，建议分淡旺季分别建模"
            })

        # 运营费用率检查（酒店运营成本很高）
        opex_range = benchmarks.get("opex_ratio", (0.60, 0.75))
        if inputs.operating_expense_ratio < opex_range[0]:
            issues.append({
                "level": "warning",
                "param": "operating_expense_ratio",
                "message": f"运营费用率 {inputs.operating_expense_ratio:.1%} 偏低",
                "suggestion": f"酒店运营费用通常为收入的 {opex_range[0]:.0%}-{opex_range[1]:.0%}（含人力、能耗、物料等）"
            })

        # RevPAR计算和检查
        if inputs.adr > 0 and inputs.occupancy_rate > 0:
            revpar = inputs.adr * inputs.occupancy_rate
            revpar_range = benchmarks.get("revpar_range", (180, 500))
            if revpar < revpar_range[0] or revpar > revpar_range[1]:
                issues.append({
                    "level": "info",
                    "param": "revpar",
                    "message": f"RevPAR {revpar:.0f} 元，超出常见范围 {revpar_range}",
                })

        return issues

    def calculate_kpi(self, result: ValuationResult) -> Dict[str, Any]:
        """计算酒店特有KPI"""
        kpi = {
            "asset_type": "酒店",
            "valuation_per_room": 0,      # 每间房估值
            "revpar_calculated": 0,       # 计算RevPAR
            "adr_calculated": 0,          # 计算ADR
        }

        # 从现金流反推ADR和RevPAR
        if result.cash_flows:
            first_cf = result.cash_flows[0]
            if first_cf.available_room_nights > 0:
                kpi["adr_calculated"] = round(first_cf.adr, 2)
                kpi["revpar_calculated"] = round(
                    first_cf.room_revenue * 10000 / first_cf.available_room_nights, 2
                )

        # 每间房估值
        # 这里假设平均每间房35㎡，用总面积估算房间数
        total_area = result.project_info.total_area
        if total_area > 0:
            avg_room_size = 35
            estimated_rooms = total_area / avg_room_size
            if estimated_rooms > 0:
                kpi["valuation_per_room"] = round(result.npv * 10000 / estimated_rooms, 2)

        return kpi
