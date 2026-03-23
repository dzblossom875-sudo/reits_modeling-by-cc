"""
酒店REITs参数提取模板（完整版）
定义所有需要从招募说明书中提取的字段，及其来源分类
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum

from ..core.config import SourceCategory


class FieldTier(str, Enum):
    TIER1_BASIC = "tier1_basic"
    TIER2_REVENUE = "tier2_revenue"
    TIER3_EXPENSE = "tier3_expense"
    TIER4_CAPEX = "tier4_capex"
    TIER5_VALUATION = "tier5_valuation"
    TIER6_HISTORICAL = "tier6_historical"


@dataclass
class TemplateField:
    """模板字段定义"""
    name: str
    display_name: str
    tier: FieldTier
    source_category: SourceCategory
    unit: str = ""
    required: bool = True
    per_project: bool = True
    regex_patterns: List[str] = field(default_factory=list)
    table_keywords: List[str] = field(default_factory=list)
    notes: str = ""


HOTEL_REIT_TEMPLATE: List[TemplateField] = [
    # === Tier 1: 基础信息 ===
    TemplateField("fund_name", "基金名称", FieldTier.TIER1_BASIC,
                  SourceCategory.PROSPECTUS, per_project=False,
                  regex_patterns=[r"基金名称[：:]\s*(.+?)(?:\n|$)"]),
    TemplateField("valuation_date", "评估基准日", FieldTier.TIER1_BASIC,
                  SourceCategory.PROSPECTUS, per_project=False,
                  regex_patterns=[r"评估基准日[：:]\s*(\d{4}年\d{1,2}月\d{1,2}日)",
                                  r"基准日[：:]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})"]),
    TemplateField("project_name", "项目名称", FieldTier.TIER1_BASIC,
                  SourceCategory.PROSPECTUS,
                  regex_patterns=[r"(广州|上海|北京|南京|深圳)\w*项目"]),
    TemplateField("brand", "酒店品牌", FieldTier.TIER1_BASIC,
                  SourceCategory.PROSPECTUS,
                  regex_patterns=[r"(美居|全季|汉庭|桔子水晶|桔子|CitiGO|城际)\w*酒店"]),
    TemplateField("total_rooms", "客房数", FieldTier.TIER1_BASIC,
                  SourceCategory.PROSPECTUS, unit="间",
                  regex_patterns=[r"客房数[量]*[：:]\s*(\d+)\s*间",
                                  r"(\d+)\s*间客房",
                                  r"房间数[量]*[：:]\s*(\d+)"],
                  table_keywords=["客房数", "房间数", "间"]),
    TemplateField("room_breakdown", "分品牌房间数", FieldTier.TIER1_BASIC,
                  SourceCategory.PROSPECTUS, unit="间", required=False),
    TemplateField("building_area", "建筑面积", FieldTier.TIER1_BASIC,
                  SourceCategory.PROSPECTUS, unit="㎡",
                  regex_patterns=[r"建筑面积[：:]\s*([\d,.]+)\s*平方米?",
                                  r"建筑面积[：:]\s*([\d,.]+)\s*㎡"]),
    TemplateField("land_area", "土地面积", FieldTier.TIER1_BASIC,
                  SourceCategory.PROSPECTUS, unit="㎡",
                  regex_patterns=[r"土地面积[：:]\s*([\d,.]+)\s*平方米?"]),
    TemplateField("remaining_years", "剩余年限", FieldTier.TIER1_BASIC,
                  SourceCategory.PROSPECTUS, unit="年",
                  regex_patterns=[r"剩余年限[：:]\s*([\d.]+)\s*年",
                                  r"剩余使用年限[：:]\s*([\d.]+)\s*年",
                                  r"土地使用权.*?([\d.]+)\s*年"],
                  table_keywords=["剩余年限", "剩余使用年限"]),
    TemplateField("location", "项目地址", FieldTier.TIER1_BASIC,
                  SourceCategory.PROSPECTUS, required=False),

    # === Tier 2: 收入数据 ===
    # 关键经营指标
    TemplateField("adr_2025", "ADR(2025预测)", FieldTier.TIER2_REVENUE,
                  SourceCategory.PROSPECTUS, unit="元/晚",
                  regex_patterns=[r"平均房价[：:]\s*([\d.]+)\s*元",
                                  r"ADR[：:]\s*([\d.]+)",
                                  r"日均房价[：:]\s*([\d.]+)"],
                  table_keywords=["平均房价", "ADR", "日均房价"]),
    TemplateField("occupancy_rate_2025", "OCC(2025预测)", FieldTier.TIER2_REVENUE,
                  SourceCategory.PROSPECTUS, unit="%",
                  regex_patterns=[r"入住率[：:]\s*([\d.]+)\s*%",
                                  r"出租率[：:]\s*([\d.]+)\s*%",
                                  r"OCC[：:]\s*([\d.]+)\s*%"],
                  table_keywords=["入住率", "出租率", "OCC"]),
    TemplateField("revpar_2025", "RevPAR(2025预测)", FieldTier.TIER2_REVENUE,
                  SourceCategory.PROSPECTUS, unit="元",
                  regex_patterns=[r"RevPAR[：:]\s*([\d.]+)",
                                  r"每间可售房收入[：:]\s*([\d.]+)"],
                  table_keywords=["RevPAR", "每间可售房收入"],
                  notes="RevPAR = ADR x OCC"),
    # 收入科目
    TemplateField("room_revenue", "客房收入", FieldTier.TIER2_REVENUE,
                  SourceCategory.PROSPECTUS, unit="万元",
                  regex_patterns=[r"客房收入[：:]\s*([\d,.]+)\s*万"],
                  table_keywords=["客房收入", "房间收入"]),
    TemplateField("ota_revenue", "OTA收入", FieldTier.TIER2_REVENUE,
                  SourceCategory.PROSPECTUS, unit="万元", required=False,
                  regex_patterns=[r"OTA收入[：:]\s*([\d,.]+)\s*万"],
                  table_keywords=["OTA收入", "在线旅游"]),
    TemplateField("fb_revenue", "餐饮收入", FieldTier.TIER2_REVENUE,
                  SourceCategory.PROSPECTUS, unit="万元",
                  regex_patterns=[r"餐饮收入[：:]\s*([\d,.]+)\s*万"],
                  table_keywords=["餐饮收入", "F&B"]),
    TemplateField("other_revenue", "其他收入", FieldTier.TIER2_REVENUE,
                  SourceCategory.PROSPECTUS, unit="万元",
                  regex_patterns=[r"其他收入[：:]\s*([\d,.]+)\s*万"],
                  table_keywords=["其他收入", "其他营业收入"]),
    TemplateField("commercial_rental", "商业租金收入", FieldTier.TIER2_REVENUE,
                  SourceCategory.PROSPECTUS, unit="万元", required=False,
                  regex_patterns=[r"商业租金[：:]\s*([\d,.]+)\s*万",
                                  r"租赁收入[：:]\s*([\d,.]+)\s*万"]),
    TemplateField("commercial_mgmt_fee", "商业物业费收入", FieldTier.TIER2_REVENUE,
                  SourceCategory.PROSPECTUS, unit="万元", required=False),
    TemplateField("total_revenue", "总收入", FieldTier.TIER2_REVENUE,
                  SourceCategory.PROSPECTUS, unit="万元",
                  regex_patterns=[r"营业收入[合计]*[：:]\s*([\d,.]+)\s*万"],
                  table_keywords=["营业收入", "收入合计"]),
    TemplateField("gop", "GOP(营业毛利)", FieldTier.TIER2_REVENUE,
                  SourceCategory.PROSPECTUS, unit="万元",
                  regex_patterns=[r"GOP[：:]\s*([\d,.]+)\s*万",
                                  r"营业毛利[：:]\s*([\d,.]+)\s*万",
                                  r"毛利润[：:]\s*([\d,.]+)\s*万"],
                  table_keywords=["GOP", "营业毛利", "毛利润"]),

    # === Tier 3: 支出数据 ===
    TemplateField("labor_cost", "人工成本", FieldTier.TIER3_EXPENSE,
                  SourceCategory.PROSPECTUS, unit="万元",
                  table_keywords=["人工成本", "人工费用", "人员费用"]),
    TemplateField("fb_cost", "餐饮成本", FieldTier.TIER3_EXPENSE,
                  SourceCategory.PROSPECTUS, unit="万元",
                  table_keywords=["餐饮成本"]),
    TemplateField("cleaning_supplies", "清洁用品", FieldTier.TIER3_EXPENSE,
                  SourceCategory.PROSPECTUS, unit="万元",
                  table_keywords=["清洁", "客房用品"]),
    TemplateField("consumables", "客用品/耗材", FieldTier.TIER3_EXPENSE,
                  SourceCategory.PROSPECTUS, unit="万元",
                  table_keywords=["客用品", "耗材", "一次性用品"]),
    TemplateField("utilities", "能源/水电", FieldTier.TIER3_EXPENSE,
                  SourceCategory.PROSPECTUS, unit="万元",
                  table_keywords=["能源", "水电", "水电气"]),
    TemplateField("maintenance", "维修保养", FieldTier.TIER3_EXPENSE,
                  SourceCategory.PROSPECTUS, unit="万元",
                  table_keywords=["维修", "维护", "保养"]),
    TemplateField("marketing", "市场营销", FieldTier.TIER3_EXPENSE,
                  SourceCategory.PROSPECTUS, unit="万元",
                  table_keywords=["营销", "推广", "市场"]),
    TemplateField("data_system", "数据系统", FieldTier.TIER3_EXPENSE,
                  SourceCategory.PROSPECTUS, unit="万元",
                  table_keywords=["数据", "系统", "IT"]),
    TemplateField("total_operating_expense", "运营费用合计", FieldTier.TIER3_EXPENSE,
                  SourceCategory.PROSPECTUS, unit="万元",
                  table_keywords=["运营费用", "营业成本"]),
    TemplateField("property_expense", "物业费用", FieldTier.TIER3_EXPENSE,
                  SourceCategory.PROSPECTUS, unit="万元",
                  table_keywords=["物业费", "物业管理费"]),
    TemplateField("insurance", "保险费", FieldTier.TIER3_EXPENSE,
                  SourceCategory.PROSPECTUS, unit="万元",
                  table_keywords=["保险"]),
    TemplateField("property_tax", "房产税", FieldTier.TIER3_EXPENSE,
                  SourceCategory.INDUSTRY, unit="万元",
                  table_keywords=["房产税"],
                  notes="从价计征1.2% x (1-30%) x 房产原值"),
    TemplateField("land_use_tax", "土地使用税", FieldTier.TIER3_EXPENSE,
                  SourceCategory.INDUSTRY, unit="万元",
                  table_keywords=["土地使用税"]),
    TemplateField("vat_rate_hotel", "酒店增值税率", FieldTier.TIER3_EXPENSE,
                  SourceCategory.INDUSTRY, unit="%",
                  notes="住宿业一般纳税人6%"),
    TemplateField("management_fee_rate", "管理费率", FieldTier.TIER3_EXPENSE,
                  SourceCategory.PROSPECTUS, unit="%",
                  regex_patterns=[r"管理费率[：:]\s*([\d.]+)\s*%"],
                  notes="酒店管理公司管理费，通常为GOP的2-5%"),

    # === Tier 4: 资本性支出 ===
    TemplateField("capex_year1", "首年Capex", FieldTier.TIER4_CAPEX,
                  SourceCategory.PROSPECTUS, unit="万元",
                  regex_patterns=[r"资本性支出[：:]\s*([\d,.]+)\s*万"],
                  table_keywords=["资本性支出", "Capex", "维修准备金"]),
    TemplateField("capex_forecast", "Capex预测(多年)", FieldTier.TIER4_CAPEX,
                  SourceCategory.PROSPECTUS, unit="万元"),
    TemplateField("renovation_cycle", "翻新周期", FieldTier.TIER4_CAPEX,
                  SourceCategory.INDUSTRY, unit="年", required=False,
                  notes="通常每5-7年一次大翻新"),

    # === Tier 5: 估值参数 ===
    TemplateField("discount_rate", "折现率/报酬率", FieldTier.TIER5_VALUATION,
                  SourceCategory.PROSPECTUS, unit="%", per_project=False,
                  regex_patterns=[r"折现率[：:]\s*([\d.]+)\s*%",
                                  r"报酬率[：:]\s*([\d.]+)\s*%",
                                  r"WACC[：:]\s*([\d.]+)\s*%"],
                  table_keywords=["折现率", "报酬率", "WACC"]),
    TemplateField("growth_year2", "第2年增长率", FieldTier.TIER5_VALUATION,
                  SourceCategory.PROSPECTUS, unit="%"),
    TemplateField("growth_year3", "第3年增长率", FieldTier.TIER5_VALUATION,
                  SourceCategory.PROSPECTUS, unit="%"),
    TemplateField("growth_year4_10", "第4-10年增长率", FieldTier.TIER5_VALUATION,
                  SourceCategory.PROSPECTUS, unit="%"),
    TemplateField("growth_year11_plus", "第11年及以后增长率", FieldTier.TIER5_VALUATION,
                  SourceCategory.PROSPECTUS, unit="%"),
    TemplateField("noicf_first_year", "首年NOI/CF", FieldTier.TIER5_VALUATION,
                  SourceCategory.PROSPECTUS, unit="万元",
                  regex_patterns=[r"年净收益[：:]\s*([\d,.]+)\s*万",
                                  r"NOI/CF[：:]\s*([\d,.]+)\s*万"],
                  table_keywords=["年净收益", "NOI/CF", "净收益"]),
    TemplateField("asset_valuation", "资产评估值", FieldTier.TIER5_VALUATION,
                  SourceCategory.PROSPECTUS, unit="亿元", per_project=False,
                  regex_patterns=[r"评估值[：:]\s*([\d.]+)\s*亿"],
                  table_keywords=["评估值", "资产评估"]),

    # === Tier 6: 历史数据 ===
    TemplateField("adr_2023", "ADR(2023历史)", FieldTier.TIER6_HISTORICAL,
                  SourceCategory.PROSPECTUS, unit="元/晚",
                  table_keywords=["2023", "平均房价"]),
    TemplateField("adr_2024", "ADR(2024历史)", FieldTier.TIER6_HISTORICAL,
                  SourceCategory.PROSPECTUS, unit="元/晚",
                  table_keywords=["2024", "平均房价"]),
    TemplateField("occ_2023", "OCC(2023历史)", FieldTier.TIER6_HISTORICAL,
                  SourceCategory.PROSPECTUS, unit="%",
                  table_keywords=["2023", "入住率"]),
    TemplateField("occ_2024", "OCC(2024历史)", FieldTier.TIER6_HISTORICAL,
                  SourceCategory.PROSPECTUS, unit="%",
                  table_keywords=["2024", "入住率"]),
    TemplateField("revenue_2023", "营业收入(2023)", FieldTier.TIER6_HISTORICAL,
                  SourceCategory.PROSPECTUS, unit="万元",
                  table_keywords=["2023", "营业收入"]),
    TemplateField("revenue_2024", "营业收入(2024)", FieldTier.TIER6_HISTORICAL,
                  SourceCategory.PROSPECTUS, unit="万元",
                  table_keywords=["2024", "营业收入"]),
    TemplateField("revenue_2025", "营业收入(2025)", FieldTier.TIER6_HISTORICAL,
                  SourceCategory.PROSPECTUS, unit="万元",
                  table_keywords=["2025", "营业收入"]),
    TemplateField("gop_2023", "GOP(2023)", FieldTier.TIER6_HISTORICAL,
                  SourceCategory.PROSPECTUS, unit="万元"),
    TemplateField("gop_2024", "GOP(2024)", FieldTier.TIER6_HISTORICAL,
                  SourceCategory.PROSPECTUS, unit="万元"),
    TemplateField("noi_2023", "NOI(2023)", FieldTier.TIER6_HISTORICAL,
                  SourceCategory.PROSPECTUS, unit="万元"),
    TemplateField("noi_2024", "NOI(2024)", FieldTier.TIER6_HISTORICAL,
                  SourceCategory.PROSPECTUS, unit="万元"),
]


def get_template_by_tier(tier: FieldTier) -> List[TemplateField]:
    return [f for f in HOTEL_REIT_TEMPLATE if f.tier == tier]


def get_template_by_source(source: SourceCategory) -> List[TemplateField]:
    return [f for f in HOTEL_REIT_TEMPLATE if f.source_category == source]


def get_required_fields() -> List[TemplateField]:
    return [f for f in HOTEL_REIT_TEMPLATE if f.required]


def generate_extraction_checklist() -> Dict[str, Any]:
    """生成提取检查清单"""
    checklist = {}
    for tier in FieldTier:
        fields = get_template_by_tier(tier)
        checklist[tier.value] = {
            "total_fields": len(fields),
            "required_fields": len([f for f in fields if f.required]),
            "fields": [
                {
                    "name": f.name,
                    "display_name": f.display_name,
                    "unit": f.unit,
                    "source_category": f.source_category.value,
                    "required": f.required,
                    "per_project": f.per_project,
                    "has_regex": len(f.regex_patterns) > 0,
                    "has_table_keywords": len(f.table_keywords) > 0,
                }
                for f in fields
            ],
        }
    return checklist


def get_all_regex_patterns() -> Dict[str, List[str]]:
    """获取所有正则匹配模式"""
    patterns = {}
    for f in HOTEL_REIT_TEMPLATE:
        if f.regex_patterns:
            patterns[f.name] = f.regex_patterns
    return patterns


def get_all_table_keywords() -> Dict[str, List[str]]:
    """获取所有表格关键词"""
    keywords = {}
    for f in HOTEL_REIT_TEMPLATE:
        if f.table_keywords:
            keywords[f.name] = f.table_keywords
    return keywords
