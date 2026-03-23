"""
统一DCF结果对象 + 通用敏感性分析引擎

所有业态(hotel/mall/industrial/logistics)的calculate()均返回DCFResult。
SensitivityEngine在DCFResult层面运行，不感知业态差异。
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .base_dcf import BaseDCF


# ---------------------------------------------------------------------------
# 基础数据类
# ---------------------------------------------------------------------------

@dataclass
class CashFlowRow:
    """单期现金流（所有业态通用格式）"""
    year: int
    noi: float
    capex: float
    fcf: float
    growth_rate: float
    cumulative_growth: float
    discount_factor: float
    pv: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "year": self.year,
            "noi": self.noi,
            "capex": self.capex,
            "fcf": self.fcf,
            "growth_rate": round(self.growth_rate, 4),
            "cumulative_growth": round(self.cumulative_growth, 4),
            "discount_factor": round(self.discount_factor, 4),
            "pv": self.pv,
        }


@dataclass
class ProjectResult:
    """单个底层项目的DCF结果"""
    name: str
    asset_type: str
    valuation: float           # DCF估值（万元）
    base_noi: float            # 首年NOI（万元）
    base_capex: float          # 首年Capex（万元）
    remaining_years: float     # 剩余年限
    discount_rate: float
    implied_cap_rate: float    # 隐含资本化率
    noi_source: str            # "derived" / "prospectus"
    cash_flows: List[CashFlowRow] = field(default_factory=list)
    noi_derivation: Dict[str, Any] = field(default_factory=dict)   # NOI推导审计轨迹
    benchmark_noicf: float = 0.0    # 招募说明书基准NOI/CF
    benchmark_diff_pct: float = 0.0 # 推导值 vs 招募值差异%

    @property
    def base_fcf(self) -> float:
        return self.base_noi - self.base_capex

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "asset_type": self.asset_type,
            "valuation": round(self.valuation, 2),
            "base_noi": round(self.base_noi, 2),
            "base_capex": round(self.base_capex, 2),
            "base_fcf": round(self.base_fcf, 2),
            "remaining_years": self.remaining_years,
            "discount_rate": round(self.discount_rate, 4),
            "implied_cap_rate": round(self.implied_cap_rate, 4),
            "noi_source": self.noi_source,
            "benchmark_noicf": round(self.benchmark_noicf, 2),
            "benchmark_diff_pct": round(self.benchmark_diff_pct * 100, 2),
            "cash_flows": [cf.to_dict() for cf in self.cash_flows],
            "noi_derivation": self.noi_derivation,
        }


@dataclass
class DCFResult:
    """
    所有业态DCF计算的统一出口。

    下游（压力测试 / 输出）只与 DCFResult 交互，
    不需要知道是 hotel / mall / industrial / logistics。
    """
    fund_name: str
    asset_type: str
    projects: List[ProjectResult]

    # 汇总估值
    total_valuation: float        # 万元
    total_noi_year1: float        # 万元
    discount_rate: float
    implied_cap_rate: float

    # 与招募说明书对比
    benchmark_valuation: float = 0.0    # 招募说明书披露估值（万元）
    benchmark_diff_pct: float = 0.0     # (dcf - benchmark) / benchmark

    # 用于敏感性重算的参数快照
    params: Dict[str, Any] = field(default_factory=dict)

    run_timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))

    # -----------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "fund_name": self.fund_name,
            "asset_type": self.asset_type,
            "total_valuation": round(self.total_valuation, 2),
            "total_valuation_billion": round(self.total_valuation / 10000, 2),
            "total_noi_year1": round(self.total_noi_year1, 2),
            "discount_rate": round(self.discount_rate, 4),
            "implied_cap_rate": round(self.implied_cap_rate, 4),
            "benchmark_valuation": round(self.benchmark_valuation, 2),
            "benchmark_diff_pct": round(self.benchmark_diff_pct * 100, 2),
            "run_timestamp": self.run_timestamp,
            "projects": [p.to_dict() for p in self.projects],
        }

    def summary(self) -> str:
        lines = [
            f"=== DCF结果: {self.fund_name} ({self.asset_type}) ===",
            f"  总估值:   {self.total_valuation:>10,.2f} 万元  ({self.total_valuation/10000:.2f} 亿元)",
            f"  总NOI:    {self.total_noi_year1:>10,.2f} 万元",
            f"  折现率:   {self.discount_rate:.2%}",
            f"  隐含Cap Rate: {self.implied_cap_rate:.2%}",
        ]
        if self.benchmark_valuation:
            lines.append(f"  vs 招募书: {self.benchmark_diff_pct*100:+.1f}%")
        for p in self.projects:
            lines.append(f"  [{p.name}] {p.valuation:,.2f}万 | NOI {p.base_noi:,.2f}万 | {p.remaining_years:.1f}年")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 通用敏感性分析引擎（在DCFResult层面运行）
# ---------------------------------------------------------------------------

class SensitivityEngine:
    """
    通用敏感性/压力测试引擎。

    接受任意 BaseDCF 子类实例，通过 model.adjust() 产生变体，
    所有分析方法均在此集中，不再分散到各业态模块。

    标准可扰动参数（所有业态通用）:
        discount_rate   折现率
        growth_rate     固定增长率覆盖（None = 使用分段增长率）
        noi_multiplier  首年NOI的乘数（1.0 = 不变）
    """

    STANDARD_PARAMS = {
        "discount_rate": {"label": "折现率", "format": "pct"},
        "growth_rate":   {"label": "增长率", "format": "pct"},
        "noi_multiplier": {"label": "NOI调整", "format": "mult"},
    }

    def __init__(self, model: "BaseDCF"):
        self.model = model
        self.base: DCFResult = model.calculate()

    # -----------------------------------------------------------------------
    # 单变量敏感性
    # -----------------------------------------------------------------------
    def single_variable(self, param: str, values: List[float]) -> Dict[str, Any]:
        """对单个参数做敏感性扫描"""
        base_val = self._get_base_value(param)
        results = []
        for v in values:
            r = self.model.adjust(**{param: v}).calculate()
            val = r.total_valuation
            results.append({
                "value": v,
                "valuation": round(val, 2),
                "vs_base": round(val - self.base.total_valuation, 2),
                "vs_base_pct": round((val - self.base.total_valuation) / self.base.total_valuation * 100, 2),
            })
        return {
            "parameter": param,
            "label": self.STANDARD_PARAMS.get(param, {}).get("label", param),
            "base_value": base_val,
            "base_valuation": round(self.base.total_valuation, 2),
            "results": results,
        }

    # -----------------------------------------------------------------------
    # Tornado 图
    # -----------------------------------------------------------------------
    def tornado(self, variation_pct: float = 0.10) -> List[Dict[str, Any]]:
        """各参数 ±variation_pct 变动对估值的影响（用于Tornado图）"""
        rows = []
        for param in self.STANDARD_PARAMS:
            base_val = self._get_base_value(param)
            if base_val is None or base_val == 0:
                continue
            up_val = base_val * (1 + variation_pct)
            dn_val = base_val * (1 - variation_pct)
            up_result = self.model.adjust(**{param: up_val}).calculate().total_valuation
            dn_result = self.model.adjust(**{param: dn_val}).calculate().total_valuation
            impact = abs(up_result - dn_result)
            rows.append({
                "parameter": param,
                "label": self.STANDARD_PARAMS[param]["label"],
                "base_value": base_val,
                "up_value": round(up_val, 4),
                "dn_value": round(dn_val, 4),
                "up_valuation": round(up_result, 2),
                "dn_valuation": round(dn_result, 2),
                "impact_range": round(impact, 2),
                "impact_pct": round(impact / self.base.total_valuation * 100, 2),
            })
        rows.sort(key=lambda x: x["impact_range"], reverse=True)
        return rows

    # -----------------------------------------------------------------------
    # 双变量热力图
    # -----------------------------------------------------------------------
    def two_way(self, param_x: str, values_x: List[float],
                param_y: str, values_y: List[float]) -> Dict[str, Any]:
        """双参数敏感性矩阵"""
        matrix = []
        for vy in values_y:
            row = []
            for vx in values_x:
                r = self.model.adjust(**{param_x: vx, param_y: vy}).calculate()
                row.append(round(r.total_valuation, 2))
            matrix.append(row)
        return {
            "param_x": param_x,
            "param_y": param_y,
            "values_x": values_x,
            "values_y": values_y,
            "matrix": matrix,
            "base_valuation": round(self.base.total_valuation, 2),
        }

    # -----------------------------------------------------------------------
    # 压力测试
    # -----------------------------------------------------------------------
    def stress_test(self, scenarios: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        多情景压力测试。

        scenarios格式:
            [{"name": "衰退", "discount_rate": 0.08, "growth_rate": 0.005, "noi_multiplier": 0.85}, ...]

        若不传scenarios，使用内置标准情景。
        """
        if scenarios is None:
            scenarios = self._default_scenarios()

        results = []
        for sc in scenarios:
            name = sc.pop("name", "unnamed")
            desc = sc.pop("description", "")
            r = self.model.adjust(**sc).calculate()
            val = r.total_valuation
            results.append({
                "scenario": name,
                "description": desc,
                "adjustments": sc,
                "valuation": round(val, 2),
                "vs_base": round(val - self.base.total_valuation, 2),
                "vs_base_pct": round((val - self.base.total_valuation) / self.base.total_valuation * 100, 2),
            })
        return results

    # -----------------------------------------------------------------------
    # 内部工具
    # -----------------------------------------------------------------------
    def _get_base_value(self, param: str) -> Optional[float]:
        mapping = {
            "discount_rate": self.base.discount_rate,
            "growth_rate": self.base.params.get("growth_rate"),
            "noi_multiplier": 1.0,
        }
        return mapping.get(param)

    @staticmethod
    def _default_scenarios() -> List[Dict[str, Any]]:
        return [
            {"name": "乐观", "description": "低折现率+高增长",
             "discount_rate": None, "growth_rate": 0.04, "noi_multiplier": 1.05},
            {"name": "悲观", "description": "高折现率+低增长",
             "discount_rate": None, "growth_rate": 0.005, "noi_multiplier": 0.92},
            {"name": "压力", "description": "衰退情景",
             "discount_rate": None, "growth_rate": 0.0, "noi_multiplier": 0.80},
        ]
