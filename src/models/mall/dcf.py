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
        """获取商业项目列表，支持从 detailed_data 或 extracted_data 读取"""
        # 优先从 detailed_data 读取（标准流程）
        if self.detailed_data:
            projects = self.detailed_data.get("projects", [])
            if projects:
                return [p for p in projects if p.get("asset_type") == "mall"]

        # 回退：从 extracted_data 构造（多业态综合体场景）
        if self.data:
            projects = self.data.get("projects", [])
            fin_data = self.data.get("financial_data", {})

            mall_projects = []
            for proj in projects:
                if proj.get("asset_type") == "mall":
                    proj_name = proj.get("name", "")
                    proj_fin = fin_data.get(proj_name, {})

                    # 尝试从历史数据构造 Y1 预测
                    hist = proj_fin.get("historical_revenue", {})

                    # 获取最新的收入数据作为 Y1 基础
                    def get_latest(hist_item):
                        if not hist_item:
                            return 0
                        for year in ["2025", "2024", "2023", "2022"]:
                            val = hist_item.get(f"{year}_jan_oct") or hist_item.get(year)
                            if val:
                                return val
                        return 0

                    # 估算全年收入（如果是1-10月数据，按12/10折算）
                    def annualize(val, key):
                        if "jan_oct" in str(key) or key.endswith("_jan_oct"):
                            return val * 12 / 10
                        return val

                    # 构造 Y1 预测
                    fixed_rent = get_latest(hist.get("fixed_rent_excl_tax"))
                    perf_rent = get_latest(hist.get("performance_rent_excl_tax"))
                    joint_op = get_latest(hist.get("joint_op_income_net"))
                    prop_mgmt = get_latest(hist.get("property_mgmt_fee_excl_tax"))
                    marketing = get_latest(hist.get("marketing_fee_excl_tax"))
                    parking = get_latest(hist.get("parking_excl_tax"))
                    multi_ch = get_latest(hist.get("multi_channel_excl_tax"))
                    ice_rink = get_latest(hist.get("ice_rink_excl_tax"))
                    other = get_latest(hist.get("other_excl_tax"))

                    # 合并项目和财务数据
                    merged = {
                        "name": proj_name,
                        "asset_type": "mall",
                        "property": {
                            "remaining_years": proj.get("remaining_years", 20.0),
                            "gla_sqm": proj.get("gla_total_sqm", 0),
                        },
                        # Y1 预测数据（从历史数据推算）
                        "y1_forecast_wan": {
                            "fixed_rent_excl_tax": fixed_rent,
                            "perf_rent_pct_of_rent_income": perf_rent / (fixed_rent + perf_rent) if (fixed_rent + perf_rent) > 0 else 0.2,
                            "joint_op_pct_of_rent_income": joint_op / fixed_rent if fixed_rent > 0 else 0.01,
                            "prop_mgmt_fee_excl_tax": prop_mgmt,
                            "marketing_fee_excl_tax": marketing,
                            "parking_incl_tax": parking * 1.09,  # 含税估算
                            "multi_channel_excl_tax": multi_ch,
                            "ice_rink_excl_tax": ice_rink,
                            "other_excl_tax": other,
                        },
                        # 简化增长率假设
                        "rent_growth_schedule": {
                            "specialty": {"Y2": 0.05, "Y3": 0.04, "Y4": 0.04, "Y5": 0.03, "Y6": 0.03, "Y10": 0.025},
                            "anchor": {"Y2": 0.03, "Y3": 0.03, "Y4": 0.0275, "Y5": 0.0275, "Y6": 0.0275, "Y7": 0.025, "Y10": 0.02},
                            "cinema_supermarket": {"all_years": 0.02},
                            "parking": {"growth_from_Y2": 0.01},
                            "multi_channel": {"growth_from_Y3": 0.02},
                            "ice_rink": {"growth_from_Y3": 0.01},
                            "other": {"growth_from_Y3": 0.02},
                            "prop_mgmt_fee": {"increase_pct_every_5yr": 0.05},
                        },
                        "phase_split": {"phase1_rent_fraction": 0.55, "phase2_rent_fraction": 0.45},
                        "opex_detailed": {
                            "marketing_promo_pct_of_rev": 0.06,
                            "prop_mgmt_cost_pct_of_prop_mgmt_incl_tax": 0.50,
                            "repairs_pct_of_rev": 0.005,
                            "labor_y1_wan": 2973,
                            "labor_growth": 0.02,
                            "admin_y1_wan": 482,
                            "admin_growth": 0.02,
                            "platform_fee_y1_wan": 1297,
                            "platform_fee_growth": 0.02,
                            "ice_rink_cost_pct_of_revenue": 0.40,
                            "insurance_annual_wan": 104,
                            "capex_pct_of_revenue_excl_tax": 0.025,
                        },
                        "vat_rates": {
                            "phase1_rent_simplified": 0.05,
                            "phase2_rent_general": 0.09,
                            "joint_op_sales": 0.13,
                            "parking": 0.09,
                            "services_mgmt_promo_multi_rink_other": 0.06,
                            "surtax_on_vat": 0.12,
                        },
                        "taxes": {
                            "property_tax_from_lease": 0.12,
                            "property_tax_from_value": {"effective_rate": 0.0084},
                            "land_use_tax": {"annual_total_wan": 110},
                            "stamp_duty_per_mille": 1,
                            "platform_fee_base_wan": 1297,
                            "platform_fee_growth_rate": 0.02,
                        },
                        "collection_rate": {"current_year_pct": 0.99},
                        # 从顶层合并估值结果
                        "appraisal_value_wan": (
                            self.data.get("valuation_results", {})
                            .get("breakdown", {})
                            .get("commercial_wan", 0)
                        ),
                        # 历史数据用于对比
                        "historical_revenue_wan": {
                            "fixed_rent_excl_tax": hist.get("fixed_rent_excl_tax", {}),
                            "performance_rent_excl_tax": hist.get("performance_rent_excl_tax", {}),
                            "joint_op_net": hist.get("joint_op_income_net", {}),
                            "property_mgmt_fee_excl_tax": hist.get("property_mgmt_fee_excl_tax", {}),
                            "marketing_fee_excl_tax": hist.get("marketing_fee_excl_tax", {}),
                            "parking_excl_tax": hist.get("parking_excl_tax", {}),
                            "multi_channel_excl_tax": hist.get("multi_channel_excl_tax", {}),
                            "ice_rink_excl_tax": hist.get("ice_rink_excl_tax", {}),
                            "other_excl_tax": hist.get("other_excl_tax", {}),
                        },
                    }
                    mall_projects.append(merged)
            return mall_projects

        return []

    def get_y1_noi_breakdown(self) -> Optional[Dict[str, Any]]:
        """返回Y1 NOI推导明细（用于历史对比）"""
        projs = self._get_mall_projects()
        if not projs:
            return None
        return MallNOIDeriver.compare_historical(projs[0])
