"""
商业购物中心REITs DCF模型（成都万象城版本）

实现 BaseDCF 接口：
  calculate() -> DCFResult   （20.10年逐期折现）
  adjust(...)  -> MallDCFModel（返回新实例，供敏感性分析使用）

折现约定：各期现金流在期末折现（年末时点），与酒店模型保持一致。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..base_dcf import BaseDCF
from ..dcf_result import CashFlowRow, DCFResult, ProjectResult
from .noi_engine import MallNOIDeriver, MallYearNOI


class MallProjectDCF:
    """单个商业项目现金流计算"""

    def __init__(self, proj_detail: Dict[str, Any], discount_rate: float,
                 noi_multiplier: float = 1.0,
                 fixed_growth: Optional[float] = None):
        self.proj = proj_detail
        self.discount_rate = discount_rate
        self.noi_multiplier = noi_multiplier
        self.fixed_growth = fixed_growth     # 非None时覆盖schedule（用于敏感性测试）

    def generate_cash_flows(self) -> List[CashFlowRow]:
        remaining = self.proj.get("property", {}).get("remaining_years", 20.10)
        year_nois: List[MallYearNOI] = MallNOIDeriver.derive_all_years(self.proj, remaining)

        rows: List[CashFlowRow] = []
        for yn in year_nois:
            noi = yn.noi * self.noi_multiplier
            capex = yn.capex * self.noi_multiplier

            if self.fixed_growth is not None and yn.year_idx > 1:
                # 覆盖增长率：以Y1 FCF为基准，按fixed_growth复利增长
                pass  # 暂不支持override模式（通过adjust传入y1_forecast倍数实现）

            fcf = noi - capex
            df = (1 + self.discount_rate) ** yn.year_idx
            rows.append(CashFlowRow(
                year=yn.year_idx,
                noi=round(noi, 2),
                capex=round(capex, 2),
                fcf=round(fcf, 2),
                growth_rate=0.0,
                cumulative_growth=1.0,
                discount_factor=round(df, 4),
                pv=round(fcf / df, 2),
            ))
        return rows

    def project_result(self) -> ProjectResult:
        cfs = self.generate_cash_flows()
        total_pv = sum(cf.pv for cf in cfs)
        base_fcf = cfs[0].fcf if cfs else 0
        cap_rate = base_fcf / total_pv if total_pv > 0 else 0

        name = self.proj.get("name", "商业项目")
        remaining = self.proj.get("property", {}).get("remaining_years", 20.10)
        return ProjectResult(
            name=name,
            asset_type="mall",
            valuation=round(total_pv, 2),
            base_noi=round(base_fcf, 2),
            base_capex=round(cfs[0].capex if cfs else 0, 2),
            remaining_years=remaining,
            discount_rate=self.discount_rate,
            implied_cap_rate=round(cap_rate, 4),
            noi_source="derived_from_params",
            cash_flows=cfs,
        )


class MallDCFModel(BaseDCF):
    """
    商业购物中心REITs DCF模型。

    数据流：
      extracted_data: extracted_params.json（项目概览、估值结论）
      detailed_data:  extracted_params_detailed.json（逐项参数）
    """

    def __init__(self, extracted_data: Dict[str, Any],
                 detailed_data: Optional[Dict[str, Any]] = None,
                 fixed_growth: Optional[float] = None,
                 noi_multiplier: float = 1.0):
        self.data = extracted_data
        self.detailed_data = detailed_data
        self.discount_rate = extracted_data.get("valuation_parameters", {}).get("discount_rate", 0.065)
        self.fixed_growth = fixed_growth
        self.noi_multiplier = noi_multiplier
        self._result: Optional[DCFResult] = None

    def calculate(self) -> DCFResult:
        if self._result is not None:
            return self._result

        mall_projects = self._get_mall_projects()
        project_results: List[ProjectResult] = []

        for proj_detail in mall_projects:
            model = MallProjectDCF(
                proj_detail=proj_detail,
                discount_rate=self.discount_rate,
                noi_multiplier=self.noi_multiplier,
                fixed_growth=self.fixed_growth,
            )
            pr = model.project_result()

            # 挂上历史对比审计
            comparison = MallNOIDeriver.compare_historical(proj_detail)
            pr.noi_derivation = comparison

            # 与报告估值对比
            appraised = proj_detail.get("appraisal_value_wan", 0)
            if appraised:
                pr.benchmark_noicf = appraised
                pr.benchmark_diff_pct = (pr.valuation - appraised) / appraised

            project_results.append(pr)

        total_val = sum(p.valuation for p in project_results)
        total_fcf_y1 = sum(p.base_noi for p in project_results)
        cap_rate = total_fcf_y1 / total_val if total_val > 0 else 0

        fund_info = self.data.get("fund_info", {})
        benchmark = self.data.get("valuation_results", {}).get("breakdown", {}).get("commercial_wan", 0)

        self._result = DCFResult(
            fund_name=fund_info.get("name", ""),
            asset_type="mall",
            projects=project_results,
            total_valuation=round(total_val, 2),
            total_noi_year1=round(total_fcf_y1, 2),
            discount_rate=self.discount_rate,
            implied_cap_rate=round(cap_rate, 4),
            benchmark_valuation=benchmark,
            benchmark_diff_pct=(total_val - benchmark) / benchmark if benchmark else 0,
            params={
                "discount_rate": self.discount_rate,
                "growth_rate": self.fixed_growth,
                "noi_multiplier": self.noi_multiplier,
            },
        )
        return self._result

    def adjust(self, discount_rate: Optional[float] = None,
               growth_rate: Optional[float] = None,
               noi_multiplier: float = 1.0) -> "MallDCFModel":
        new = MallDCFModel(
            extracted_data=self.data,
            detailed_data=self.detailed_data,
            fixed_growth=growth_rate if growth_rate is not None else self.fixed_growth,
            noi_multiplier=noi_multiplier,
        )
        if discount_rate is not None:
            new.discount_rate = discount_rate
        return new

    def _get_mall_projects(self) -> List[Dict[str, Any]]:
        if not self.detailed_data:
            return []
        return [
            p for p in self.detailed_data.get("projects", [])
            if p.get("asset_type") == "mall"
        ]

    def get_y1_noi_breakdown(self) -> Optional[Dict[str, Any]]:
        """返回Y1 NOI推导明细（用于历史对比）"""
        projs = self._get_mall_projects()
        if not projs:
            return None
        return MallNOIDeriver.compare_historical(projs[0])
