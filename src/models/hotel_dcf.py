"""
酒店REITs DCF估值模型（统一版）
核心逻辑变更：
- 首年NOI由收入/支出明细推导（NOIEngine），而非直接用招募数值
- 招募noicf_2026仅用作验证基准（5%阈值）
- 通过验证后，用推导NOI驱动DCF全周期计算
"""

import json
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


@dataclass
class GrowthSchedule:
    """分段增长率配置"""
    year_ranges: List[Tuple[int, int]]
    rates: List[float]
    project_overrides: Dict[str, Dict[int, float]] = field(default_factory=dict)

    def get_rate(self, year: int, project_name: str = "") -> float:
        if project_name in self.project_overrides:
            overrides = self.project_overrides[project_name]
            if year in overrides:
                return overrides[year]
        for (start, end), rate in zip(self.year_ranges, self.rates):
            if start <= year <= end:
                return rate
        return self.rates[-1] if self.rates else 0.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GrowthSchedule":
        schedule = cls(year_ranges=[], rates=[])
        growth_config = data.get("valuation_parameters", {}).get("growth_rate", {})
        if not growth_config:
            schedule.year_ranges = [(1, 1), (2, 2), (3, 3), (4, 10), (11, 99)]
            schedule.rates = [0.0, 0.01, 0.02, 0.03, 0.0225]
            return schedule

        schedule.year_ranges = [(1, 1), (2, 2), (3, 3), (4, 10), (11, 99)]
        schedule.rates = [
            0.0,
            growth_config.get("year2_shanghai", 0.01),
            growth_config.get("year3", 0.02),
            growth_config.get("year4_10", 0.03),
            growth_config.get("year11_plus", 0.0225),
        ]
        gz_year2 = growth_config.get("year2_guangzhou", 0.02)
        schedule.project_overrides = {"广州": {2: gz_year2}}
        return schedule


@dataclass
class DerivedNOI:
    """NOI推导结果"""
    project_name: str
    total_revenue: float
    hotel_revenue: float
    commercial_revenue: float
    operating_expense: float
    property_expense: float
    insurance_expense: float
    tax_total: float
    management_fee: float
    total_expense: float
    capex: float
    noi: float  # = total_revenue - total_expense - capex
    prospectus_noicf: float
    diff_pct: float
    within_threshold: bool
    revenue_detail: Dict[str, Any] = field(default_factory=dict)
    expense_detail: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "total_revenue": round(self.total_revenue, 2),
            "hotel_revenue": round(self.hotel_revenue, 2),
            "commercial_revenue": round(self.commercial_revenue, 2),
            "operating_expense": round(self.operating_expense, 2),
            "property_expense": round(self.property_expense, 2),
            "insurance_expense": round(self.insurance_expense, 2),
            "tax_total": round(self.tax_total, 2),
            "management_fee": round(self.management_fee, 2),
            "total_expense": round(self.total_expense, 2),
            "capex": round(self.capex, 2),
            "noi": round(self.noi, 2),
            "prospectus_noicf": round(self.prospectus_noicf, 2),
            "diff_pct": round(self.diff_pct * 100, 2),
            "within_threshold": self.within_threshold,
            "revenue_detail": self.revenue_detail,
            "expense_detail": self.expense_detail,
        }


@dataclass
class HotelProjectConfig:
    """单个酒店项目配置"""
    name: str
    brand: str = ""
    location: str = ""
    total_rooms: int = 0
    remaining_years: float = 0.0
    base_noicf: float = 0.0  # 推导出的NOI/CF（= NOI - Capex）
    capex_forecast: List[float] = field(default_factory=list)
    adr_2023: float = 0.0
    adr_2025: float = 0.0
    source_page: Optional[int] = None
    noi_source: str = "prospectus"  # "derived" or "prospectus"

    @property
    def base_capex(self) -> float:
        return self.capex_forecast[0] if self.capex_forecast else 0.0

    @property
    def base_noi(self) -> float:
        return self.base_noicf + self.base_capex


@dataclass
class ProjectCashFlow:
    """单期项目现金流"""
    year: int
    noi: float
    capex: float
    fcf: float
    growth_rate: float
    cumulative_growth: float
    discount_factor: float
    pv: float


class HotelProjectDCF:
    """单个酒店项目DCF模型"""

    def __init__(self, config: HotelProjectConfig, discount_rate: float,
                 growth_schedule: Optional[GrowthSchedule] = None,
                 fixed_growth: Optional[float] = None):
        self.config = config
        self.discount_rate = discount_rate
        self.growth_schedule = growth_schedule
        self.fixed_growth = fixed_growth
        self._cash_flows: Optional[List[ProjectCashFlow]] = None

    def _get_project_key(self) -> str:
        for key in ["广州", "上海"]:
            if key in self.config.name:
                return key
        return ""

    def get_growth_rate(self, year: int) -> float:
        if self.fixed_growth is not None:
            return self.fixed_growth if year > 1 else 0.0
        if self.growth_schedule:
            return self.growth_schedule.get_rate(year, self._get_project_key())
        return 0.01

    def generate_cash_flows(self) -> List[ProjectCashFlow]:
        if self._cash_flows is not None:
            return self._cash_flows

        cash_flows = []
        full_years = int(self.config.remaining_years)
        partial = self.config.remaining_years - full_years
        cumulative_growth = 1.0

        for year in range(1, full_years + 1):
            growth_rate = self.get_growth_rate(year)
            if year == 1:
                cumulative_growth = 1.0
            else:
                cumulative_growth *= (1 + growth_rate)

            noi = self.config.base_noi * cumulative_growth

            if year <= len(self.config.capex_forecast):
                capex = self.config.capex_forecast[year - 1]
            else:
                base = self.config.capex_forecast[-1] if self.config.capex_forecast else 0
                capex = base * (1.02 ** (year - len(self.config.capex_forecast)))

            fcf = noi - capex
            discount_factor = (1 + self.discount_rate) ** year
            pv = fcf / discount_factor

            cash_flows.append(ProjectCashFlow(
                year=year,
                noi=round(noi, 2),
                capex=round(capex, 2),
                fcf=round(fcf, 2),
                growth_rate=growth_rate,
                cumulative_growth=round(cumulative_growth, 4),
                discount_factor=round(discount_factor, 4),
                pv=round(pv, 2),
            ))

        if partial > 0.01:
            next_year = full_years + 1
            growth_rate = self.get_growth_rate(next_year)
            cumulative_growth *= (1 + growth_rate)
            noi = self.config.base_noi * cumulative_growth
            base_capex = self.config.capex_forecast[-1] if self.config.capex_forecast else 0
            capex = base_capex * (1.02 ** (next_year - len(self.config.capex_forecast))) if next_year > len(self.config.capex_forecast) else self.config.capex_forecast[next_year - 1] if next_year <= len(self.config.capex_forecast) else 0
            fcf_full = noi - capex
            fcf = fcf_full * partial
            discount_factor = (1 + self.discount_rate) ** (full_years + partial)
            pv = fcf / discount_factor
            cash_flows.append(ProjectCashFlow(
                year=next_year,
                noi=round(noi * partial, 2),
                capex=round(capex * partial, 2),
                fcf=round(fcf, 2),
                growth_rate=growth_rate,
                cumulative_growth=round(cumulative_growth, 4),
                discount_factor=round(discount_factor, 4),
                pv=round(pv, 2),
            ))

        self._cash_flows = cash_flows
        return cash_flows

    def calculate(self) -> Dict[str, Any]:
        cash_flows = self.generate_cash_flows()
        total_pv = sum(cf.pv for cf in cash_flows)
        return {
            "name": self.config.name,
            "remaining_years": self.config.remaining_years,
            "base_noi": round(self.config.base_noi, 2),
            "base_capex": round(self.config.base_capex, 2),
            "base_fcf": round(self.config.base_noi - self.config.base_capex, 2),
            "rooms": self.config.total_rooms,
            "noi_source": self.config.noi_source,
            "valuation": round(total_pv, 2),
            "pv_cash_flows": round(total_pv, 2),
            "implied_cap_rate": round(self.config.base_noi / total_pv, 4) if total_pv > 0 else 0,
            "value_per_room": round(total_pv * 10000 / self.config.total_rooms, 2) if self.config.total_rooms > 0 else 0,
            "cash_flows": [
                {"year": cf.year, "noi": cf.noi, "capex": cf.capex,
                 "fcf": cf.fcf, "growth_rate": cf.growth_rate,
                 "cumulative_growth": cf.cumulative_growth,
                 "discount_factor": cf.discount_factor, "pv": cf.pv}
                for cf in cash_flows
            ],
        }


class NOIDeriver:
    """
    从REITs后收支明细推导NOI，并与招募说明书数值对比验证

    公式:
      运营成本 = 运营明细 + 物业费 + 保险（REITs后独立列支，不用历史利润表）
      GOP = 营业收入(不含税) - 运营成本 - 税金及附加(实际缴纳)
      NOI = GOP - 管理费(GOP × 3%, 付给华住)
      NOI/CF = NOI - Capex

    关键会计处理:
    1. 收入(ADR): ADR为含税报价, first_year_amount已完成价税分离(不含税)
    2. 运营成本: 使用REITs后明细(人工+餐饮+物业+保险等), 非历史利润表
       （REITs后成本重分类, 物业/保险独立合同, 不含折旧）
    3. 税金及附加: 使用实际缴纳值, 同时记录推导值供对比
       （推导值因房产原值基数/减免政策等原因偏高）
    4. 管理费: GOP × fee_rate (付给酒店管理公司华住的运营管理费)
    """
    THRESHOLD = 0.05

    @classmethod
    def derive_project_noi(cls, project_detail: Dict[str, Any],
                           prospectus_noicf: float,
                           historical_data: Optional[Dict[str, Any]] = None) -> DerivedNOI:
        rev = project_detail.get("revenue", {})
        exp = project_detail.get("expenses", {})
        capex_data = project_detail.get("capex", {})

        hotel = rev.get("hotel", {})
        commercial = rev.get("commercial", {})

        # --- 收入: first_year_amount已是不含增值税的净额 ---
        room_data = hotel.get("room_revenue", {})
        room_rev = room_data.get("first_year_amount", 0)
        fb_rev = hotel.get("fb_revenue", {}).get("first_year_amount", 0)
        other_rev = hotel.get("other_revenue", {}).get("first_year_amount", 0)
        ota_rev = hotel.get("ota_revenue", {}).get("first_year_amount", 0)
        hotel_total = room_rev + fb_rev + other_rev + ota_rev

        comm_rent = commercial.get("rental_income", 0)
        comm_mgmt = commercial.get("mgmt_fee_income", 0)
        commercial_total = comm_rent + comm_mgmt

        total_revenue = hotel_total + commercial_total

        # ADR含税→不含税: 统一6%增值税率(酒店住宿业一般纳税人)
        HOTEL_VAT_RATE = 0.06
        adr = room_data.get("adr", 0)
        rooms = room_data.get("room_count", 0)
        occ = room_data.get("occupancy_rate", 0)
        adr_incl_tax = adr * rooms * occ * 365 / 10000 if (adr and rooms and occ) else 0
        adr_excl_tax = adr_incl_tax / (1 + HOTEL_VAT_RATE)
        adr_excl_diff = room_rev - adr_excl_tax
        adr_excl_diff_pct = (adr_excl_diff / adr_excl_tax * 100) if adr_excl_tax > 0 else 0

        # --- 运营成本: REITs后明细(含物业+保险, 独立列支) ---
        op = exp.get("operating", {})
        op_keys = ["labor_cost", "fb_cost", "cleaning_supplies", "consumables",
                    "utilities", "maintenance", "marketing", "data_system", "other"]
        operating_items = {k: op.get(k, 0) for k in op_keys}
        operating_subtotal = sum(operating_items.values())
        prop_exp = exp.get("property_expense", {}).get("annual_total", 0) / 10000
        insurance = exp.get("insurance", {}).get("annual_amount", 0)

        cost_excl_dep = operating_subtotal + prop_exp + insurance
        cost_source = "REITs明细"

        # 历史利润表对照
        hist_cost_2025 = 0
        if historical_data and "运营成本(不含折旧)" in historical_data:
            hist_cost_2025 = historical_data["运营成本(不含折旧)"].get("2025", 0)

        # --- 税金及附加: 实际缴纳值, 同时记录推导值 ---
        derived_tax = cls._calc_tax_from_detail(exp, comm_rent)
        hist_tax_2025 = 0
        if historical_data and "税金及附加" in historical_data:
            hist_tax_2025 = historical_data["税金及附加"].get("2025", 0)

        if hist_tax_2025 > 0:
            tax_total = hist_tax_2025
            tax_source = "实际缴纳2025"
        else:
            tax_total = derived_tax
            tax_source = "从原值推导"

        tax_diff = derived_tax - tax_total
        tax_diff_pct = (tax_diff / tax_total * 100) if tax_total > 0 else 0

        # --- GOP ---
        gop = total_revenue - cost_excl_dep - tax_total

        # --- 管理费: GOP × 酒店管理公司费率 ---
        mgmt_rate = exp.get("management_fee", {}).get("fee_rate", 0.03)
        mgmt_fee = gop * mgmt_rate
        mgmt_source = f"GOP×{mgmt_rate:.0%}"

        total_expense = cost_excl_dep + tax_total + mgmt_fee

        capex = capex_data.get("annual_capex", 0)

        noi = total_revenue - total_expense - capex

        diff_pct = (noi - prospectus_noicf) / abs(prospectus_noicf) if prospectus_noicf != 0 else 0
        within = abs(diff_pct) <= cls.THRESHOLD

        return DerivedNOI(
            project_name=project_detail.get("name", ""),
            total_revenue=total_revenue,
            hotel_revenue=hotel_total,
            commercial_revenue=commercial_total,
            operating_expense=cost_excl_dep,
            property_expense=prop_exp,
            insurance_expense=insurance,
            tax_total=tax_total,
            management_fee=mgmt_fee,
            total_expense=total_expense,
            capex=capex,
            noi=noi,
            prospectus_noicf=prospectus_noicf,
            diff_pct=diff_pct,
            within_threshold=within,
            revenue_detail={
                "room_revenue_excl_tax": round(room_rev, 2),
                "adr_incl_tax": round(adr_incl_tax, 2),
                "adr_excl_tax_6pct": round(adr_excl_tax, 2),
                "adr_vs_actual_diff": round(adr_excl_diff, 2),
                "adr_vs_actual_diff_pct": round(adr_excl_diff_pct, 1),
                "vat_rate": HOTEL_VAT_RATE,
                "ota_revenue": round(ota_rev, 2),
                "fb_revenue": round(fb_rev, 2),
                "other_revenue": round(other_rev, 2),
                "commercial_rent": round(comm_rent, 2),
                "commercial_mgmt": round(comm_mgmt, 2),
            },
            expense_detail={
                "cost_excl_dep": round(cost_excl_dep, 2),
                "cost_source": cost_source,
                "operating_items": {k: round(v, 2) for k, v in operating_items.items()},
                "operating_subtotal": round(operating_subtotal, 2),
                "property_expense": round(prop_exp, 2),
                "insurance": round(insurance, 2),
                "hist_cost_2025": round(hist_cost_2025, 2),
                "cost_vs_hist": round(cost_excl_dep - hist_cost_2025, 2) if hist_cost_2025 else None,
                "cost_vs_hist_pct": round((cost_excl_dep / hist_cost_2025 - 1) * 100, 1) if hist_cost_2025 else None,
                "gop": round(gop, 2),
                "gop_margin": round(gop / total_revenue * 100, 1) if total_revenue else 0,
                "tax_total": round(tax_total, 2),
                "tax_source": tax_source,
                "tax_derived": round(derived_tax, 2),
                "tax_derived_diff": round(tax_diff, 2),
                "tax_derived_diff_pct": round(tax_diff_pct, 1),
                "management_fee": round(mgmt_fee, 2),
                "mgmt_source": mgmt_source,
            },
        )

    @staticmethod
    def _calc_tax_from_detail(exp: Dict, comm_rent: float) -> float:
        """从明细推导税金及附加（房产税+土地使用税，不含增值税）"""
        tax = exp.get("tax", {})
        prop_tax_data = tax.get("property_tax", {})
        hotel_pt = prop_tax_data.get("hotel", {})
        deduction_rate = hotel_pt.get("deduction_rate", 0.30)
        hotel_pt_amt = hotel_pt.get("original_value", 0) * (1 - deduction_rate) * hotel_pt.get("rate", 0.012)
        comm_pt = prop_tax_data.get("commercial", {})
        comm_pt_amt = comm_pt.get("rental_base", comm_rent) * comm_pt.get("rate", 0.12)
        land = tax.get("land_use_tax", {})
        land_tax = land.get("unit_rate", 0) * land.get("land_area", 0) / 10000
        return hotel_pt_amt + comm_pt_amt + land_tax


class HotelDCFModel:
    """
    酒店REITs统一DCF模型

    核心流程：
    1. 用NOIDeriver从收支明细推导首年NOI
    2. 与招募noicf_2026对比 (5%阈值)
    3. 通过验证 → 用推导NOI作为DCF基础
    4. 分段增长率驱动全周期现金流
    """

    def __init__(self, extracted_data: Dict[str, Any],
                 detailed_data: Optional[Dict[str, Any]] = None,
                 historical_data: Optional[Dict[str, Any]] = None,
                 growth_schedule: Optional[GrowthSchedule] = None,
                 fixed_growth: Optional[float] = None):
        self.data = extracted_data
        self.detailed_data = detailed_data
        self.historical_data = historical_data
        self.discount_rate = extracted_data.get("valuation_parameters", {}).get("discount_rate", 0.0575)
        self.growth_schedule = growth_schedule or GrowthSchedule.from_dict(extracted_data)
        self.fixed_growth = fixed_growth

        self.derived_nois: List[DerivedNOI] = []
        self.project_configs = self._build_project_configs()
        self.project_models = self._build_project_models()
        self._results: Optional[Dict[str, Any]] = None

    def _build_project_configs(self) -> List[HotelProjectConfig]:
        configs = []
        fin_data = self.data.get("financial_data", {})
        projects = self.data.get("projects", [])
        detail_projects = (self.detailed_data or {}).get("projects", [])

        # 从数据文件中动态构建项目映射，而非硬编码
        for i, proj_info in enumerate(projects):
            proj_name = proj_info.get("name", f"项目{i+1}")
            proj_fin = fin_data.get(proj_name, {})

            # 从数据文件中获取默认值，若不存在则使用0值（强制要求数据完整性）
            default_noicf = proj_fin.get("noicf_2026", 0)
            default_remaining = proj_info.get("remaining_years", 0)
            default_capex = proj_fin.get("capex_forecast", [0, 0, 0])

            prospectus_noicf = proj_fin.get("noicf_2026", default_noicf)
            capex_list = proj_fin.get("capex_forecast", default_capex)

            noi_source = "prospectus"
            base_noicf = prospectus_noicf

            # 如果有详细项目数据，尝试推导NOI
            if i < len(detail_projects):
                hist_proj = (self.historical_data or {}).get(proj_name)
                derived = NOIDeriver.derive_project_noi(
                    detail_projects[i], prospectus_noicf, hist_proj)
                self.derived_nois.append(derived)

                base_noicf = derived.noi
                noi_source = "derived" if derived.within_threshold else f"derived(差异{derived.diff_pct*100:+.1f}%)"

            configs.append(HotelProjectConfig(
                name=proj_info.get("name", proj_name),
                brand=proj_info.get("brand", ""),
                total_rooms=proj_info.get("total_rooms", 0),
                remaining_years=proj_info.get("remaining_years", default_remaining),
                base_noicf=base_noicf,
                capex_forecast=capex_list,
                adr_2023=proj_info.get("adr_2023", 0),
                adr_2025=proj_info.get("adr_2025", 0),
                noi_source=noi_source,
            ))

        return configs

    def _build_project_models(self) -> List[HotelProjectDCF]:
        return [
            HotelProjectDCF(
                config=cfg,
                discount_rate=self.discount_rate,
                growth_schedule=self.growth_schedule,
                fixed_growth=self.fixed_growth,
            )
            for cfg in self.project_configs
        ]

    def calculate(self) -> Dict[str, Any]:
        if self._results is not None:
            return self._results

        project_results = [m.calculate() for m in self.project_models]
        total_valuation = sum(p["valuation"] for p in project_results)
        total_base_noi = sum(p["base_noi"] for p in project_results)
        total_rooms = sum(p["rooms"] for p in project_results)

        self._results = {
            "projects": project_results,
            "total_valuation": round(total_valuation, 2),
            "total_pv_cash_flows": round(total_valuation, 2),
            "noi_derivation": [d.to_dict() for d in self.derived_nois],
            "kpis": {
                "total_rooms": total_rooms,
                "total_base_noi": round(total_base_noi, 2),
                "implied_cap_rate": round(total_base_noi / total_valuation, 4) if total_valuation > 0 else 0,
                "projects": [
                    {"name": p["name"], "rooms": p["rooms"],
                     "value_per_room": p["value_per_room"],
                     "implied_cap_rate": p["implied_cap_rate"],
                     "base_noi": p["base_noi"],
                     "noi_source": p["noi_source"]}
                    for p in project_results
                ],
            },
            "comparison": {
                "dcf_valuation_billion": round(total_valuation / 10000, 2),
                "asset_valuation_billion": 15.91,
                "vs_asset_valuation": round(total_valuation / 10000 - 15.91, 2),
                "fund_raise_billion": 13.2,
            },
        }
        return self._results

    def recalculate(self) -> Dict[str, Any]:
        self._results = None
        for m in self.project_models:
            m._cash_flows = None
        return self.calculate()

    def get_historical_adr_growth(self) -> float:
        rates = []
        for cfg in self.project_configs:
            if cfg.adr_2023 > 0 and cfg.adr_2025 > 0:
                cagr = (cfg.adr_2025 / cfg.adr_2023) ** 0.5 - 1
                rates.append(cagr)
        return sum(rates) / len(rates) if rates else -0.028

    def export_to_dict(self) -> Dict[str, Any]:
        results = self.calculate()
        return {
            "fund_info": self.data.get("fund_info", {}),
            "dcf_inputs": {
                "discount_rate": self.discount_rate,
                "discount_rate_percent": f"{self.discount_rate:.2%}",
                "growth_mode": "fixed" if self.fixed_growth is not None else "segmented",
                "historical_growth": self.get_historical_adr_growth(),
                "valuation_method": "报酬率全周期DCF法（持有到期，残值归零）",
            },
            "dcf_results": results,
            "extraction_source": self.data.get("source_pages", {}),
        }

    def adjust_discount_rate(self, new_rate: float):
        self.discount_rate = new_rate
        for m in self.project_models:
            m.discount_rate = new_rate
        self._results = None
        for m in self.project_models:
            m._cash_flows = None

    def adjust_growth(self, fixed_growth: Optional[float] = None,
                      schedule: Optional[GrowthSchedule] = None):
        self.fixed_growth = fixed_growth
        if schedule:
            self.growth_schedule = schedule
        for m in self.project_models:
            m.fixed_growth = fixed_growth
            if schedule:
                m.growth_schedule = schedule
        self._results = None
        for m in self.project_models:
            m._cash_flows = None
