"""
基础设施（高速/能源）REITs特化处理
"""

from typing import Dict, List, Any

from .base import AssetTypeHandler
from ..dcf_model import DCFInputs
from ...core.types import ValuationResult
from ...core.config import AssetType


class InfrastructureREIT(AssetTypeHandler):
    """基础设施REITs处理器"""

    ASSET_TYPE = AssetType.INFRASTRUCTURE

    def get_required_params(self) -> List[str]:
        return [
            "traffic_volume",      # 车流量/发电量
            "toll_rate",           # 收费标准
            "traffic_growth",      # 增长预测
            "operating_expense",
            "discount_rate",
            "remaining_years"      # 基础设施通常有明确期限
        ]

    def get_optional_params(self) -> Dict[str, Any]:
        return {
            "management_fee_ratio": 0.02,
            "maintenance_cost": 0,
            "capex": 0,
        }

    def validate_params(self, inputs: DCFInputs) -> List[Dict[str, Any]]:
        """验证基础设施参数合理性"""
        issues = []
        benchmarks = self.get_industry_benchmarks()

        # 剩余年限检查（基础设施REITs期限很重要）
        remaining_years = inputs.remaining_years
        if remaining_years < 5:
            issues.append({
                "level": "high",
                "param": "remaining_years",
                "message": f"剩余年限仅 {remaining_years} 年，需要特别关注资产处置安排",
                "suggestion": "建议明确特许经营期结束后的资产处置方案"
            })

        # 车流量增长检查
        growth_range = benchmarks.get("traffic_growth_range", (0.02, 0.06))
        if inputs.traffic_growth > growth_range[1]:
            issues.append({
                "level": "warning",
                "param": "traffic_growth",
                "message": f"车流量增长率 {inputs.traffic_growth:.2%} 偏高",
                "suggestion": f"行业常见范围为 {growth_range[0]:.1%}-{growth_range[1]:.1%}"
            })

        # 运营费用率检查（基础设施运营成本较高）
        opex_range = benchmarks.get("opex_ratio", (0.30, 0.50))
        if inputs.operating_expense_ratio < opex_range[0]:
            issues.append({
                "level": "warning",
                "param": "operating_expense_ratio",
                "message": f"运营费用率 {inputs.operating_expense_ratio:.1%} 偏低",
                "suggestion": f"基础设施运营成本通常为收入的 {opex_range[0]:.0%}-{opex_range[1]:.0%}"
            })

        return issues

    def calculate_kpi(self, result: ValuationResult) -> Dict[str, Any]:
        """计算基础设施特有KPI"""
        kpi = {
            "asset_type": "基础设施",
            "valuation_per_year_remaining": 0,  # 每年剩余期限的估值
            "dscr_estimate": 0,  # 偿债覆盖率估算
        }

        remaining_years = result.project_info.remaining_years
        if remaining_years > 0:
            kpi["valuation_per_year_remaining"] = round(result.npv / remaining_years, 2)

        # 估算偿债覆盖率（如果有现金流数据）
        if result.cash_flows:
            total_noi = sum(cf.calculate_noi() for cf in result.cash_flows)
            avg_annual_noi = total_noi / len(result.cash_flows) if result.cash_flows else 0
            # 假设债务成本为NOI的60%
            if avg_annual_noi > 0:
                kpi["dscr_estimate"] = round(avg_annual_noi / (avg_annual_noi * 0.6), 2)

        return kpi
