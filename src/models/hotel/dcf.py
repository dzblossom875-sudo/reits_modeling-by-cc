"""
酒店REITs DCF建模模块

HotelProjectDCF  - 单个酒店项目的现金流计算
HotelDCFModel    - 多项目汇总DCF（实现 BaseDCF 接口）

设计原则:
  - 所有项目配置从 extracted_data / detailed_data 读取，无硬编码默认值
  - calculate() 返回 DCFResult（统一格式，可接入 SensitivityEngine）
  - adjust() 返回新实例（不修改原实例），供敏感性分析使用
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional

from ..base_dcf import BaseDCF
from ..dcf_result import CashFlowRow, DCFResult, ProjectResult
from .noi_engine import NOIDeriver
from .params import DerivedNOI, GrowthSchedule, HotelProjectConfig


# ---------------------------------------------------------------------------
# 单项目现金流计算
# ---------------------------------------------------------------------------

class HotelProjectDCF:
    """单个酒店项目的逐期现金流计算"""

    def __init__(self, config: HotelProjectConfig, discount_rate: float,
                 growth_schedule: Optional[GrowthSchedule] = None,
                 fixed_growth: Optional[float] = None,
                 noi_multiplier: float = 1.0):
        self.config = config
        self.discount_rate = discount_rate
        self.growth_schedule = growth_schedule
        self.fixed_growth = fixed_growth
        self.noi_multiplier = noi_multiplier
        self._cash_flows: Optional[List[CashFlowRow]] = None

    def _project_key(self) -> str:
        for key in ["广州", "上海"]:
            if key in self.config.name:
                return key
        return ""

    def _growth_rate(self, year: int) -> float:
        if self.fixed_growth is not None:
            return self.fixed_growth if year > 1 else 0.0
        if self.growth_schedule:
            return self.growth_schedule.get_rate(year, self._project_key())
        return 0.01

    def _get_capex_for_year(self, year: int) -> float:
        """获取指定年份的Capex，处理列表或字典格式"""
        cf = self.config.capex_forecast
        if not cf:
            return 0.0

        # 统一转为列表格式
        if isinstance(cf, dict):
            # 按年份排序取值（如 "2026", "2027"）
            values = []
            for k in sorted(cf.keys()):
                v = cf[k]
                if isinstance(v, (int, float)):
                    values.append(v)
            if not values:
                return 0.0
        else:
            values = cf

        if year <= len(values):
            return values[year - 1]
        else:
            base_cap = values[-1] if values else 0
            return base_cap * (1.02 ** (year - len(values)))

    def generate_cash_flows(self) -> List[CashFlowRow]:
        if self._cash_flows is not None:
            return self._cash_flows

        base_noi = self.config.base_noi * self.noi_multiplier
        full_years = int(self.config.remaining_years)
        partial = self.config.remaining_years - full_years
        cumulative = 1.0
        rows: List[CashFlowRow] = []

        for year in range(1, full_years + 1):
            g = self._growth_rate(year)
            if year > 1:
                cumulative *= (1 + g)

            noi = base_noi * cumulative
            capex = self._get_capex_for_year(year)

            fcf = noi - capex
            df = (1 + self.discount_rate) ** year
            rows.append(CashFlowRow(
                year=year, noi=round(noi, 2), capex=round(capex, 2),
                fcf=round(fcf, 2), growth_rate=g,
                cumulative_growth=round(cumulative, 4),
                discount_factor=round(df, 4), pv=round(fcf / df, 2),
            ))

        # 剩余不足一年的部分
        if partial > 0.01:
            ny = full_years + 1
            g = self._growth_rate(ny)
            cumulative *= (1 + g)
            noi = base_noi * cumulative
            capex_full = self._get_capex_for_year(ny)
            fcf = (noi - capex_full) * partial
            df = (1 + self.discount_rate) ** (full_years + partial)
            rows.append(CashFlowRow(
                year=ny, noi=round(noi * partial, 2), capex=round(capex_full * partial, 2),
                fcf=round(fcf, 2), growth_rate=g,
                cumulative_growth=round(cumulative, 4),
                discount_factor=round(df, 4), pv=round(fcf / df, 2),
            ))

        self._cash_flows = rows
        return rows

    def project_result(self, asset_type: str = "hotel") -> ProjectResult:
        cfs = self.generate_cash_flows()
        total_pv = sum(cf.pv for cf in cfs)
        cap_rate = self.config.base_noi / total_pv if total_pv > 0 else 0
        return ProjectResult(
            name=self.config.name,
            asset_type=asset_type,
            valuation=round(total_pv, 2),
            base_noi=round(self.config.base_noi * self.noi_multiplier, 2),
            base_capex=round(self.config.base_capex, 2),
            remaining_years=self.config.remaining_years,
            discount_rate=self.discount_rate,
            implied_cap_rate=round(cap_rate, 4),
            noi_source=self.config.noi_source,
            cash_flows=cfs,
        )


# ---------------------------------------------------------------------------
# 多项目汇总 DCF 模型（实现 BaseDCF）
# ---------------------------------------------------------------------------

class HotelDCFModel(BaseDCF):
    """
    酒店REITs多项目汇总DCF。

    实现 BaseDCF 接口：
      calculate() -> DCFResult
      adjust(discount_rate, growth_rate, noi_multiplier) -> HotelDCFModel
    """

    def __init__(self,
                 extracted_data: Dict[str, Any],
                 detailed_data: Optional[Dict[str, Any]] = None,
                 historical_data: Optional[Dict[str, Any]] = None,
                 growth_schedule: Optional[GrowthSchedule] = None,
                 fixed_growth: Optional[float] = None,
                 noi_multiplier: float = 1.0):
        self.data = extracted_data
        self.detailed_data = detailed_data
        self.historical_data = historical_data
        self.discount_rate = (
            extracted_data.get("valuation_parameters", {}).get("discount_rate", 0.0575)
        )
        self.growth_schedule = growth_schedule or GrowthSchedule.from_dict(extracted_data)
        self.fixed_growth = fixed_growth
        self.noi_multiplier = noi_multiplier

        self._derived_nois: List[DerivedNOI] = []
        self._project_configs: Optional[List[HotelProjectConfig]] = None
        self._result: Optional[DCFResult] = None

    # -----------------------------------------------------------------------
    # BaseDCF 接口实现
    # -----------------------------------------------------------------------

    def calculate(self) -> DCFResult:
        if self._result is not None:
            return self._result

        configs = self._get_configs()
        project_results: List[ProjectResult] = []

        for i, cfg in enumerate(configs):
            model = HotelProjectDCF(
                config=cfg,
                discount_rate=self.discount_rate,
                growth_schedule=self.growth_schedule,
                fixed_growth=self.fixed_growth,
                noi_multiplier=self.noi_multiplier,
            )
            pr = model.project_result(asset_type="hotel")

            # 挂上NOI推导审计轨迹
            if i < len(self._derived_nois):
                pr.noi_derivation = self._derived_nois[i].to_dict()
                pr.benchmark_noicf = self._derived_nois[i].prospectus_noicf
                pr.benchmark_diff_pct = self._derived_nois[i].diff_pct

            project_results.append(pr)

        total_val = sum(p.valuation for p in project_results)
        total_noi = sum(p.base_noi for p in project_results)
        cap_rate = total_noi / total_val if total_val > 0 else 0

        fund_info = self.data.get("fund_info", {})
        benchmark = self.data.get("comparison", {}).get("asset_valuation_wan", 0)

        self._result = DCFResult(
            fund_name=fund_info.get("name", ""),
            asset_type="hotel",
            projects=project_results,
            total_valuation=round(total_val, 2),
            total_noi_year1=round(total_noi, 2),
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

    def adjust(self,
               discount_rate: Optional[float] = None,
               growth_rate: Optional[float] = None,
               noi_multiplier: float = 1.0) -> "HotelDCFModel":
        """返回调参后的新实例（不修改 self）"""
        new = HotelDCFModel(
            extracted_data=self.data,
            detailed_data=self.detailed_data,
            historical_data=self.historical_data,
            growth_schedule=self.growth_schedule if growth_rate is None else None,
            fixed_growth=growth_rate if growth_rate is not None else self.fixed_growth,
            noi_multiplier=noi_multiplier,
        )
        if discount_rate is not None:
            new.discount_rate = discount_rate
        # 复用已推导的NOI（避免重复计算）
        new._derived_nois = self._derived_nois
        new._project_configs = self._get_configs()
        return new

    # -----------------------------------------------------------------------
    # 内部：从 extracted_data + detailed_data 构造项目配置
    # -----------------------------------------------------------------------

    def _get_configs(self) -> List[HotelProjectConfig]:
        if self._project_configs is not None:
            return self._project_configs

        fin_data = self.data.get("financial_data", {})
        projects = self.data.get("projects", [])
        detail_projects = (self.detailed_data or {}).get("projects", [])

        configs = []
        for i, proj_info in enumerate(projects):
            # 只处理酒店项目
            if proj_info.get("asset_type") != "hotel":
                continue

            key = proj_info.get("name", f"项目{i+1}")
            proj_fin = fin_data.get(key, {})

            prospectus_noicf = proj_fin.get("noicf_2026", 0)
            capex_list = proj_fin.get("capex_forecast", [])

            noi_source = "prospectus"
            base_noicf = prospectus_noicf

            # 如果有详细数据，用 NOIDeriver 推导
            if i < len(detail_projects):
                hist_proj = (self.historical_data or {}).get(key)
                derived = NOIDeriver.derive(detail_projects[i], prospectus_noicf, hist_proj)
                self._derived_nois.append(derived)
                base_noicf = derived.noi
                noi_source = "derived" if derived.within_threshold else f"derived(差异{derived.diff_pct*100:+.1f}%)"

            configs.append(HotelProjectConfig(
                name=key,
                brand=proj_info.get("brand", ""),
                location=proj_info.get("location", ""),
                total_rooms=proj_info.get("total_rooms", 0),
                remaining_years=proj_info.get("remaining_years", 0.0),
                base_noicf=base_noicf,
                capex_forecast=capex_list,
                adr_2023=proj_info.get("adr_2023", 0),
                adr_2025=proj_info.get("adr_2025", 0),
                noi_source=noi_source,
            ))

        self._project_configs = configs
        return configs

    # -----------------------------------------------------------------------
    # 辅助工具
    # -----------------------------------------------------------------------

    def get_historical_adr_cagr(self) -> float:
        """计算项目组合的历史ADR CAGR（2023→2025，2年）"""
        rates = []
        for cfg in self._get_configs():
            if cfg.adr_2023 > 0 and cfg.adr_2025 > 0:
                rates.append((cfg.adr_2025 / cfg.adr_2023) ** 0.5 - 1)
        return sum(rates) / len(rates) if rates else 0.0

    def recalculate(self) -> DCFResult:
        self._result = None
        self._project_configs = None
        self._derived_nois = []
        return self.calculate()
