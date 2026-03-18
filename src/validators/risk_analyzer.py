"""
风险分析器
分析估值模型中的风险点
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from ..core.types import ValuationResult, RiskItem
from ..models.dcf_model import DCFInputs
from ..core.config import AssetType, INDUSTRY_BENCHMARKS, RISK_THRESHOLDS


class RiskAnalyzer:
    """风险分析器"""

    def __init__(self):
        self.risks: List[RiskItem] = []

    def analyze(self, valuation: ValuationResult) -> List[RiskItem]:
        """
        执行全面风险分析

        Args:
            valuation: 估值结果

        Returns:
            风险项列表
        """
        self.risks = []

        # 参数假设风险
        self._analyze_parameter_risks(valuation)

        # 模型结构风险
        self._analyze_model_risks(valuation)

        # 资产特有风险
        self._analyze_asset_specific_risks(valuation)

        # 市场风险
        self._analyze_market_risks(valuation)

        # 按风险等级排序
        severity_order = {"high": 0, "medium": 1, "low": 2}
        self.risks.sort(key=lambda x: severity_order.get(x.level, 3))

        return self.risks

    def _analyze_parameter_risks(self, valuation: ValuationResult):
        """分析参数假设风险"""
        assumptions = valuation.assumptions
        asset_type = valuation.asset_type
        benchmarks = INDUSTRY_BENCHMARKS.get(asset_type, {})

        # 折现率风险
        discount_rate = self._parse_rate(assumptions.get("discount_rate"))
        if discount_rate:
            default_rate = {
                AssetType.INDUSTRIAL: 0.075,
                AssetType.LOGISTICS: 0.070,
                AssetType.HOUSING: 0.065,
                AssetType.INFRASTRUCTURE: 0.080,
                AssetType.HOTEL: 0.085,
            }.get(asset_type, 0.075)

            if abs(discount_rate - default_rate) / default_rate > 0.20:
                self.risks.append(RiskItem(
                    level="medium",
                    category="参数假设",
                    description=f"折现率 {discount_rate:.2%} 与行业基准 {default_rate:.2%} 差异较大",
                    param_name="discount_rate",
                    param_value=discount_rate,
                    benchmark=f"{default_rate:.2%}",
                    suggestion="请确认折现率假设的合理性，考虑风险溢价是否充分"
                ))

        # 增长率风险
        growth_rate = self._parse_rate(assumptions.get("rent_growth_rate"))
        if growth_rate and growth_rate > 0.05:
            self.risks.append(RiskItem(
                level="medium",
                category="参数假设",
                description=f"租金增长率 {growth_rate:.2%} 较高，可能过于乐观",
                param_name="rent_growth_rate",
                param_value=growth_rate,
                benchmark="2%-3%",
                suggestion="建议进行敏感度分析，评估增长率下行对估值的影响"
            ))

        # 出租率风险
        occupancy = self._parse_rate(assumptions.get("occupancy_rate"))
        if occupancy and occupancy > 0.95:
            self.risks.append(RiskItem(
                level="low",
                category="参数假设",
                description=f"出租率假设 {occupancy:.1%} 接近满租，未考虑空置风险",
                param_name="occupancy_rate",
                param_value=occupancy,
                benchmark="90%-95%",
                suggestion="考虑设置合理的空置率缓冲（如5%-10%）"
            ))

    def _analyze_model_risks(self, valuation: ValuationResult):
        """分析模型结构风险"""
        # 剩余年限风险
        remaining_years = valuation.project_info.remaining_years
        if remaining_years and remaining_years < 5:
            self.risks.append(RiskItem(
                level="high",
                category="模型结构",
                description=f"剩余年限仅 {remaining_years} 年，模型接近到期",
                param_name="remaining_years",
                param_value=remaining_years,
                suggestion="需明确特许经营期结束后的资产处置或续约安排"
            ))

        # 终值计算风险
        if valuation.cash_flows and len(valuation.cash_flows) > 0:
            final_noi = valuation.cash_flows[-1].calculate_noi()
            first_noi = valuation.cash_flows[0].calculate_noi()
            if first_noi > 0 and final_noi / first_noi > 2:
                self.risks.append(RiskItem(
                    level="medium",
                    category="模型结构",
                    description="终期NOI较初期增长超过100%，永续增长假设可能过于乐观",
                    param_name="terminal_growth",
                    suggestion="考虑限制永续增长率或使用退出倍数法计算终值"
                ))

    def _analyze_asset_specific_risks(self, valuation: ValuationResult):
        """分析资产特有风险"""
        asset_type = valuation.asset_type

        if asset_type == AssetType.HOTEL:
            self.risks.append(RiskItem(
                level="medium",
                category="资产特定",
                description="酒店资产受季节性波动影响较大，当前模型可能未充分考虑",
                suggestion="建议分淡旺季分别建模，或使用更保守的全年平均假设"
            ))

        elif asset_type == AssetType.INFRASTRUCTURE:
            self.risks.append(RiskItem(
                level="medium",
                category="资产特定",
                description="基础设施资产依赖特许经营权，存在政策风险和到期风险",
                suggestion="关注特许经营协议条款，评估续约可能性和成本"
            ))

        elif asset_type == AssetType.LOGISTICS:
            self.risks.append(RiskItem(
                level="low",
                category="资产特定",
                description="物流仓储租户集中度可能较高，存在大客户流失风险",
                suggestion="了解前五大租户占比，评估租户稳定性"
            ))

        elif asset_type == AssetType.HOUSING:
            self.risks.append(RiskItem(
                level="low",
                category="资产特定",
                description="保障房受政府定价政策约束，租金增长空间有限",
                suggestion="确认当地租金涨幅限制政策，确保增长假设合规"
            ))

    def _analyze_market_risks(self, valuation: ValuationResult):
        """分析市场风险"""
        # 利率风险（折现率敏感性）
        discount_rate = self._parse_rate(valuation.assumptions.get("discount_rate"))
        if discount_rate:
            # 模拟利率上升1%的影响
            higher_rate = discount_rate + 0.01
            if valuation.npv > 0:
                # 简化估算：NPV对折现率的敏感度
                rate_sensitivity = -valuation.npv / (1 + discount_rate) * 0.01
                if abs(rate_sensitivity) / valuation.npv > 0.10:
                    self.risks.append(RiskItem(
                        level="medium",
                        category="市场风险",
                        description=f"估值对利率敏感，折现率上升1%可能导致NPV下降约 {abs(rate_sensitivity)/valuation.npv*100:.1f}%",
                        param_name="discount_rate",
                        param_value=discount_rate,
                        suggestion="考虑进行利率压力测试，评估加息环境下的估值安全边际"
                    ))

    def _parse_rate(self, value: Any) -> Optional[float]:
        """解析比率值"""
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return value if value < 1 else value / 100

        if isinstance(value, str):
            value = value.replace('%', '').strip()
            try:
                v = float(value)
                return v if v < 1 else v / 100
            except ValueError:
                return None

        return None

    def generate_risk_report(self, risks: List[RiskItem]) -> str:
        """
        生成风险报告文本

        Args:
            risks: 风险项列表

        Returns:
            格式化的风险报告
        """
        if not risks:
            return "未发现明显风险点。"

        lines = ["# 风险评估报告\n"]

        # 按等级分组
        high_risks = [r for r in risks if r.level == "high"]
        medium_risks = [r for r in risks if r.level == "medium"]
        low_risks = [r for r in risks if r.level == "low"]

        if high_risks:
            lines.append("## 高风险\n")
            for i, risk in enumerate(high_risks, 1):
                lines.append(f"{i}. **{risk.category}**: {risk.description}")
                if risk.suggestion:
                    lines.append(f"   - 建议: {risk.suggestion}")
                lines.append("")

        if medium_risks:
            lines.append("## 中风险\n")
            for i, risk in enumerate(medium_risks, 1):
                lines.append(f"{i}. **{risk.category}**: {risk.description}")
                if risk.suggestion:
                    lines.append(f"   - 建议: {risk.suggestion}")
                lines.append("")

        if low_risks:
            lines.append("## 低风险\n")
            for i, risk in enumerate(low_risks, 1):
                lines.append(f"{i}. **{risk.category}**: {risk.description}")
                if risk.suggestion:
                    lines.append(f"   - 建议: {risk.suggestion}")
                lines.append("")

        return "\n".join(lines)