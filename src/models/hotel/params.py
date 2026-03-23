"""
酒店REITs参数数据类

包含:
  GrowthSchedule      - 分段增长率配置
  HotelProjectConfig  - 单项目配置
  DerivedNOI          - NOI推导结果（含审计字段）

⚠️ 华住项目特别注意事项（新项目运行前必读）:
  见本文件末尾 HOTEL_PITFALLS 字典，记录了实际踩坑的会计口径陷阱。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 增长率配置
# ---------------------------------------------------------------------------

@dataclass
class GrowthSchedule:
    """
    分段增长率配置（按年区间）。

    year_ranges: [(start, end), ...]  年份从1开始（1=首预测年）
    rates:       对应各区间的增长率
    project_overrides: 按项目名称的年份级别覆盖 {"广州": {2: 0.02}}
    """
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
        """从extracted_params JSON构造（标准化格式）

        支持动态项目覆盖，不再硬编码城市名称。
        期望数据格式:
        {
            "valuation_parameters": {
                "growth_rate": {
                    "rates": [0.0, 0.01, 0.02, 0.03, 0.0225],  // 默认分段增长率
                    "project_overrides": {                      // 可选：按项目覆盖
                        "项目A名称": {2: 0.02},
                        "项目B名称": {2: 0.01}
                    }
                }
            }
        }
        """
        growth_config = data.get("valuation_parameters", {}).get("growth_rate", {})

        # 使用配置的分段区间和默认增长率，不再硬编码
        year_ranges = growth_config.get("year_ranges", [(1, 1), (2, 2), (3, 3), (4, 10), (11, 99)])
        default_rates = growth_config.get("rates", [0.0, 0.01, 0.02, 0.03, 0.0225])

        schedule = cls(year_ranges=year_ranges, rates=default_rates)

        # 动态读取项目级覆盖（从数据文件而非硬编码）
        project_overrides = growth_config.get("project_overrides", {})
        schedule.project_overrides = project_overrides

        return schedule

    @classmethod
    def fixed(cls, rate: float) -> "GrowthSchedule":
        """所有年份使用固定增长率（敏感性分析专用）"""
        return cls(year_ranges=[(1, 1), (2, 99)], rates=[0.0, rate])


# ---------------------------------------------------------------------------
# 单项目配置
# ---------------------------------------------------------------------------

@dataclass
class HotelProjectConfig:
    """
    单个酒店底层项目的静态配置。

    从 extracted_params_detailed.json 的 projects[] 元素构造。
    所有数值单位：万元（除非注释说明）。
    """
    name: str
    brand: str = ""
    location: str = ""
    total_rooms: int = 0
    remaining_years: float = 0.0      # 土地使用权剩余年限（含小数）
    base_noicf: float = 0.0           # 首年NOI/CF（= NOI - Capex）
    capex_forecast: List[float] = field(default_factory=list)  # 逐年Capex预测（万元）
    adr_2023: float = 0.0             # 历史ADR（用于验证增长率）
    adr_2025: float = 0.0
    source_page: Optional[int] = None
    noi_source: str = "prospectus"    # "derived" | "prospectus" | "derived(差异+X.X%)"

    @property
    def base_capex(self) -> float:
        """获取首年Capex，处理列表或字典格式"""
        if not self.capex_forecast:
            return 0.0
        if isinstance(self.capex_forecast, dict):
            # 字典格式：取第一个值或0
            values = list(self.capex_forecast.values())
            return values[0] if values else 0.0
        # 列表格式
        return self.capex_forecast[0] if len(self.capex_forecast) > 0 else 0.0

    @property
    def base_noi(self) -> float:
        """NOI = NOI/CF + Capex（Capex是从NOI中扣除的，反推得NOI）"""
        return self.base_noicf + self.base_capex


# ---------------------------------------------------------------------------
# NOI推导结果（审计轨迹）
# ---------------------------------------------------------------------------

@dataclass
class DerivedNOI:
    """
    NOI推导的完整审计记录。

    所有金额单位：万元。
    diff_pct = (derived_noi - prospectus_noicf) / |prospectus_noicf|
    """
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
    noi: float
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


# ---------------------------------------------------------------------------
# ⚠️ 酒店REITs常见陷阱（新项目必读）
# ---------------------------------------------------------------------------

HOTEL_PITFALLS = {
    "VAT_double_deduction": {
        "rule": "营业收入(first_year_amount)已是不含税净额，禁止再扣增值税",
        "why": "中国GAAP营业收入不含增值税；ADR含税，但first_year_amount已完成价税分离",
        "vat_rate": "酒店住宿业一般纳税人统一用6%",
        "check": "adr * rooms * occ * 365 / 10000 / 1.06 ≈ first_year_amount（差异<5%即合理）",
    },
    "cost_caliber": {
        "rule": "运营成本用REITs后明细（人工+餐饮+物业+保险），不用历史利润表的营业成本",
        "why": "REITs后成本重分类：物业/保险签独立合同、折旧不计入、行政管理费由基金承担",
        "check": "运营明细合计 + 独立物业费 + 独立保险费 = 总运营成本（禁止混用历史利润表）",
    },
    "management_fee": {
        "rule": "管理费 = GOP × fee_rate（酒店运营管理费，付给酒店管理公司）",
        "why": "利润表'管理费用'含公司行政，REITs后由基金承担，不能用利润表数字",
        "fee_rate_typical": "华住收取GOP×3%",
        "check": "如招募书明确了管理费金额，应与GOP×3%交叉验证",
    },
    "tax_surcharge": {
        "rule": "税金及附加优先用实际缴纳值，推导值仅作对照",
        "why": "房产税从价计征有各地减免政策，推导值（原值×70%×1.2%）通常偏高",
        "deduction_rate": "标准扣除率30%（即按原值70%计征）",
        "check": "房产原值单位确认（万元，禁止/10000再除）",
    },
    "property_tax_unit": {
        "rule": "原始数据hotel_prop_base已是万元，计算时不要再除以10000",
        "why": "华住项目曾因单位错误导致房产税从934万元算成0.07万元",
        "check": "房产税结果量级：广州≈900万元，上海≈250万元为合理范围",
    },
    "capex_in_noi": {
        "rule": "NOI = GOP - 管理费；NOI/CF = NOI - Capex；DCF用NOI驱动，Capex单独列支",
        "why": "Capex是资本性支出，不在运营成本中，但需从现金流中扣除",
        "check": "base_noi = base_noicf + base_capex（反推关系）",
    },
    "remaining_years": {
        "rule": "土地使用权剩余年限含小数（如19.28年），partial_year现金流按比例折算",
        "why": "REITs持有到期无残值，最后一年需按实际月份比例计算",
        "check": "广州≈19.3年，上海≈30.7年；若数据明显偏离，核对土地证登记日期",
    },
    "adr_data_source": {
        "rule": "ADR优先用分品牌数据（如美居/全季分别计算），汇总比用统一ADR更准",
        "why": "多品牌项目统一ADR会抹平高低档差异，导致收入估算偏差",
        "check": "分品牌计算差异约1-2%，统一ADR差异约3-5%",
    },
    "historical_data_digit_error": {
        "rule": "从PDF提取大数字时必须交叉验证位序（如12,015 vs 13,215）",
        "why": "华住广州项目曾将12,015.67误提取为13,215.67，导致差异从-6%变+3%",
        "check": "提取值用ADR公式反算，差异应<5%；超过需重新核对原文",
    },
    "noi_always_derived": {
        "rule": "最终DCF始终用推导NOI，不因'差异大'而退回招募书数字",
        "why": "推导NOI基于真实成本口径，更准确；差异应记录并分析原因",
        "threshold": "5%以内视为合理；超过需在审计报告中说明原因",
    },
}
