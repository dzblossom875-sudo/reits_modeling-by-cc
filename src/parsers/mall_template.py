"""
商业购物中心REITs参数提取模板（完整版）
基于成都万象城估价报告（2025-10-31）提炼，可复用于同类商业REIT项目。

字段分层:
  Tier1 基础信息  → 项目概览、物业参数
  Tier2 租户结构  → 出租率、租金结构、主次力店拆分
  Tier3 收入参数  → Y1预测各科目、增长率假设
  Tier4 成本税金  → 运营成本、税率、增值税处理
  Tier5 估值参数  → 折现率、Capex、报告估值
  Tier6 历史数据  → 近3年各科目历史数值

增值税处理原则（已验证）:
  收入按不含税口径列示，增值税为价外税（纯过路资金），不计入成本。
  仅增值税附加税（城建税+教育附加，VAT×12%）为真实税负，需计入税金。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

from ..core.config import SourceCategory


class FieldTier(str, Enum):
    TIER1_BASIC = "tier1_basic"
    TIER2_TENANCY = "tier2_tenancy"
    TIER3_REVENUE = "tier3_revenue"
    TIER4_COST_TAX = "tier4_cost_tax"
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


MALL_REIT_TEMPLATE: List[TemplateField] = [

    # =========================================================================
    # Tier 1: 基础信息
    # =========================================================================
    TemplateField("fund_name", "基金名称", FieldTier.TIER1_BASIC,
                  SourceCategory.PROSPECTUS, per_project=False,
                  regex_patterns=[r"基金名称[：:]\s*(.+?)(?:\n|$)"]),

    TemplateField("valuation_date", "评估基准日", FieldTier.TIER1_BASIC,
                  SourceCategory.PROSPECTUS, per_project=False,
                  regex_patterns=[r"评估基准日[：:]\s*(\d{4}年\d{1,2}月\d{1,2}日)",
                                  r"(\d{4}[-/]\d{2}[-/]\d{2})"]),

    TemplateField("project_name", "项目名称", FieldTier.TIER1_BASIC,
                  SourceCategory.PROSPECTUS,
                  regex_patterns=[r"(成都|上海|广州|北京|深圳|杭州)\w*[购物中心|广场|万象城|天地]"]),

    TemplateField("gla_sqm", "可租赁面积(GLA)", FieldTier.TIER1_BASIC,
                  SourceCategory.PROSPECTUS, unit="㎡",
                  regex_patterns=[r"可租赁面积[：:]\s*([\d,.]+)\s*平方米?",
                                  r"GLA[：:]\s*([\d,.]+)\s*(?:平方米|㎡)"],
                  table_keywords=["可租赁面积", "GLA"]),

    TemplateField("gla_temp_sqm", "临时展位面积", FieldTier.TIER1_BASIC,
                  SourceCategory.PROSPECTUS, unit="㎡", required=False,
                  notes="临时展位不计入正式GLA"),

    TemplateField("parking_spaces", "停车位数量", FieldTier.TIER1_BASIC,
                  SourceCategory.PROSPECTUS, unit="个",
                  regex_patterns=[r"停车位[：:]\s*(\d+)\s*个",
                                  r"车位数[：:]\s*(\d+)"],
                  table_keywords=["停车位", "车位"]),

    TemplateField("land_area_sqm", "土地面积", FieldTier.TIER1_BASIC,
                  SourceCategory.PROSPECTUS, unit="㎡",
                  regex_patterns=[r"土地面积[：:]\s*([\d,.]+)\s*平方米?"]),

    TemplateField("land_expiry", "土地使用权到期日", FieldTier.TIER1_BASIC,
                  SourceCategory.PROSPECTUS,
                  regex_patterns=[r"土地使用权.*?(\d{4}[-年]\d{1,2}[-月]\d{1,2}日?)",
                                  r"到期日[：:]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})"]),

    TemplateField("remaining_years", "剩余年限", FieldTier.TIER1_BASIC,
                  SourceCategory.PROSPECTUS, unit="年",
                  regex_patterns=[r"剩余.*?年限[：:]\s*([\d.]+)\s*年"],
                  notes="精确到小数点后2位，如20.10年"),

    TemplateField("open_phases", "开业期数说明", FieldTier.TIER1_BASIC,
                  SourceCategory.PROSPECTUS, required=False,
                  notes="如一期(2012)简易征收，二期(2020)一般计税；影响增值税率"),

    # =========================================================================
    # Tier 2: 租户结构
    # =========================================================================
    TemplateField("occupancy_rate", "出租率", FieldTier.TIER2_TENANCY,
                  SourceCategory.PROSPECTUS, unit="%",
                  regex_patterns=[r"出租率[：:]\s*([\d.]+)\s*%"],
                  table_keywords=["出租率", "入驻率"]),

    TemplateField("collection_rate_y1", "收缴率Y1", FieldTier.TIER2_TENANCY,
                  SourceCategory.PROSPECTUS, unit="%",
                  table_keywords=["收缴率", "收租率"],
                  notes="Y1通常98%（新资产），Y3+为99%；历史收缴率通常99-100%"),

    TemplateField("collection_rate_schedule", "收缴率年度计划", FieldTier.TIER2_TENANCY,
                  SourceCategory.PROSPECTUS, required=False,
                  notes="逐年列示：Y1=98%,Y2=98%,Y3-Y9=99%,Y6*=90%(翻新)"),

    TemplateField("fixed_rent_monthly_incl_tax", "月度固定租金(含税)", FieldTier.TIER2_TENANCY,
                  SourceCategory.PROSPECTUS, unit="万元/月",
                  table_keywords=["月租金", "固定租金"],
                  notes="含增值税，不含物业管理费，是计算基础"),

    TemplateField("avg_rent_per_sqm_incl_tax", "平均租金单价(含税)", FieldTier.TIER2_TENANCY,
                  SourceCategory.PROSPECTUS, unit="元/㎡/月",
                  table_keywords=["平均租金", "租金单价"],
                  notes="用于合理性验证"),

    TemplateField("tenant_type_split", "主次力店面积拆分", FieldTier.TIER2_TENANCY,
                  SourceCategory.PROSPECTUS, unit="㎡",
                  notes="影响增长率权重：专门店/主力店/超市影院/冰场"),

    TemplateField("phase_split_rent_fraction", "一二期租金分摊比例", FieldTier.TIER2_TENANCY,
                  SourceCategory.PROSPECTUS,
                  notes="影响增值税计算：一期简易5%，二期一般9%；典型分摊55%/45%"),

    TemplateField("top10_tenant_concentration", "前10大租户集中度", FieldTier.TIER2_TENANCY,
                  SourceCategory.PROSPECTUS, unit="%", required=False),

    TemplateField("lease_3yr_plus_ratio", "3年以上租约占比", FieldTier.TIER2_TENANCY,
                  SourceCategory.PROSPECTUS, unit="%", required=False),

    TemplateField("industry_breakdown", "业态拆分", FieldTier.TIER2_TENANCY,
                  SourceCategory.PROSPECTUS, required=False,
                  notes="餐饮/服装/生活方式/娱乐运动/儿童/个人护理/超市等"),

    # =========================================================================
    # Tier 3: 收入参数
    # =========================================================================
    TemplateField("fixed_rent_y1_excl_tax", "Y1固定租金(不含税)", FieldTier.TIER3_REVENUE,
                  SourceCategory.PROSPECTUS, unit="万元",
                  notes="由Capex反推：Capex=2.5%×总收入 → 固定租金作为最大分项"),

    TemplateField("perf_rent_pct_of_total_rent", "提成租金占比", FieldTier.TIER3_REVENUE,
                  SourceCategory.PROSPECTUS, unit="%",
                  notes="典型22%；公式：提成=22/78×固定；影响整体租金规模"),

    TemplateField("joint_op_pct_of_rent_income", "联营净收入占比", FieldTier.TIER3_REVENUE,
                  SourceCategory.PROSPECTUS, unit="%",
                  notes="典型1%×(固定+提成)；净额=销售额×扣点率-成本"),

    TemplateField("prop_mgmt_fee_y1_excl_tax", "Y1物业管理费(不含税)", FieldTier.TIER3_REVENUE,
                  SourceCategory.PROSPECTUS, unit="万元",
                  notes="由历史数据年化推算；参考110元/sqm/月标准"),

    TemplateField("marketing_fee_income_y1", "Y1推广费收入", FieldTier.TIER3_REVENUE,
                  SourceCategory.PROSPECTUS, unit="万元",
                  notes="不增长；由历史年化推算"),

    TemplateField("parking_y1_incl_tax", "Y1停车场收入(含税)", FieldTier.TIER3_REVENUE,
                  SourceCategory.PROSPECTUS, unit="万元",
                  notes="停车整租合同，含税金额；需÷(1+9%)转换为不含税"),

    TemplateField("multi_channel_y1_excl_tax", "Y1多经收入(不含税)", FieldTier.TIER3_REVENUE,
                  SourceCategory.PROSPECTUS, unit="万元",
                  notes="含临展、广告等多种经营收入；Y1-Y2持平，Y3起+2%/年"),

    TemplateField("ice_rink_revenue_y1", "Y1冰场收入(不含税)", FieldTier.TIER3_REVENUE,
                  SourceCategory.PROSPECTUS, unit="万元", required=False,
                  notes="有冰场时列示；Y1-Y2持平，Y3起+1%/年"),

    TemplateField("other_revenue_y1", "Y1其他收入(不含税)", FieldTier.TIER3_REVENUE,
                  SourceCategory.PROSPECTUS, unit="万元",
                  notes="Y1-Y2持平，Y3起+2%/年"),

    TemplateField("rent_growth_specialty", "专门店租金递增率", FieldTier.TIER3_REVENUE,
                  SourceCategory.PROSPECTUS, unit="%",
                  table_keywords=["专门店", "递增率"],
                  notes="Y2=5%,Y3=4%,Y4=4%,Y5-Y9=3%,Y10+=2.5%（典型）"),

    TemplateField("rent_growth_anchor", "主力店租金递增率", FieldTier.TIER3_REVENUE,
                  SourceCategory.PROSPECTUS, unit="%",
                  notes="Y2-Y3=3%,Y4-Y6=2.75%,Y7-Y9=2.5%,Y10+=2%（典型）"),

    TemplateField("rent_growth_cinema_supermarket", "超市影院递增率", FieldTier.TIER3_REVENUE,
                  SourceCategory.PROSPECTUS, unit="%",
                  notes="通常固定2%/年"),

    TemplateField("prop_mgmt_fee_growth", "物业管理费递增规则", FieldTier.TIER3_REVENUE,
                  SourceCategory.PROSPECTUS,
                  notes="每5年递增5%（Y6/Y11/Y16适用）"),

    TemplateField("parking_growth_rate", "停车场收入增长率", FieldTier.TIER3_REVENUE,
                  SourceCategory.PROSPECTUS, unit="%",
                  notes="Y2起+1%/年"),

    TemplateField("renovation_year", "翻新年份", FieldTier.TIER3_REVENUE,
                  SourceCategory.PROSPECTUS, required=False,
                  notes="大型翻新导致当年出租率降至90%；需在收缴率计划中体现"),

    # =========================================================================
    # Tier 4: 成本与税金
    # =========================================================================
    TemplateField("marketing_promo_cost_pct", "营销推广费率", FieldTier.TIER4_COST_TAX,
                  SourceCategory.PROSPECTUS, unit="%",
                  notes="6%×不含税收入（典型）"),

    TemplateField("prop_mgmt_cost_pct", "物业管理费成本占比", FieldTier.TIER4_COST_TAX,
                  SourceCategory.PROSPECTUS, unit="%",
                  notes="50%×物管收入含税额（用户已确认：50%是含税口径）"),

    TemplateField("repairs_pct", "房屋大修费率", FieldTier.TIER4_COST_TAX,
                  SourceCategory.PROSPECTUS, unit="%",
                  notes="0.5%×不含税收入"),

    TemplateField("labor_cost_y1", "Y1人工成本", FieldTier.TIER4_COST_TAX,
                  SourceCategory.PROSPECTUS, unit="万元",
                  table_keywords=["人工", "劳动力", "员工薪酬"],
                  notes="含所有员工薪资社保；+2%/年增长"),

    TemplateField("admin_cost_y1", "Y1行政管理费", FieldTier.TIER4_COST_TAX,
                  SourceCategory.PROSPECTUS, unit="万元",
                  notes="+2%/年增长"),

    TemplateField("platform_fee_y1", "Y1商业平台费", FieldTier.TIER4_COST_TAX,
                  SourceCategory.PROSPECTUS, unit="万元",
                  notes="店总管理费+商标使用费+物业酬金合计；+2%/年"),

    TemplateField("ice_rink_cost_pct", "冰场成本占冰场收入比", FieldTier.TIER4_COST_TAX,
                  SourceCategory.PROSPECTUS, unit="%", required=False,
                  notes="典型40%"),

    TemplateField("insurance_annual", "年度保险费", FieldTier.TIER4_COST_TAX,
                  SourceCategory.PROSPECTUS, unit="万元",
                  notes="固定，通常不增长"),

    TemplateField("capex_pct_of_revenue", "资本性支出率", FieldTier.TIER4_COST_TAX,
                  SourceCategory.PROSPECTUS, unit="%",
                  notes="2.5%×不含税收入（由报告披露的Y1 Capex绝对值反推验证）"),

    # ---- 税率参数 ----
    TemplateField("vat_phase1_rate", "一期增值税率(含税净率)", FieldTier.TIER4_COST_TAX,
                  SourceCategory.INDUSTRY, unit="%",
                  notes="简易计税：4.76%（含税口径）= 5%/(1+5%)；【仅用于附加税基数计算，不计入成本】"),

    TemplateField("vat_phase2_rate", "二期增值税率(含税净率)", FieldTier.TIER4_COST_TAX,
                  SourceCategory.INDUSTRY, unit="%",
                  notes="一般计税：8.26%（含税口径）= 9%/(1+9%)；【仅用于附加税基数计算，不计入成本】"),

    TemplateField("vat_services_rate", "服务类增值税率", FieldTier.TIER4_COST_TAX,
                  SourceCategory.INDUSTRY, unit="%",
                  notes="物管/推广/多经/冰场/其他：6%（不含税口径）；【仅用于附加税基数计算】"),

    TemplateField("vat_surtax_rate", "增值税附加税率", FieldTier.TIER4_COST_TAX,
                  SourceCategory.INDUSTRY, unit="%",
                  notes="城建税+教育费附加 = VAT×12%；此项为真实税负，计入税金"),

    TemplateField("property_tax_from_rent_rate", "房产税率(从租)", FieldTier.TIER4_COST_TAX,
                  SourceCategory.INDUSTRY, unit="%",
                  notes="12%×不含税租金（固定租金+停车场）；提成租金是否纳税需依据地方口径"),

    TemplateField("property_tax_from_value_rate", "房产税率(从价)", FieldTier.TIER4_COST_TAX,
                  SourceCategory.INDUSTRY, unit="%",
                  notes="有效税率0.84% = 扣除30%后×1.2%；适用于联营/空置面积"),

    TemplateField("land_use_tax_per_sqm", "土地使用税单价", FieldTier.TIER4_COST_TAX,
                  SourceCategory.PROSPECTUS, unit="元/㎡/年",
                  notes="核查：单价×土地面积=年总额"),

    TemplateField("stamp_duty_rate", "印花税率", FieldTier.TIER4_COST_TAX,
                  SourceCategory.INDUSTRY, unit="‰",
                  notes="1‰×固定租金（不含税）"),

    # =========================================================================
    # Tier 5: 估值参数
    # =========================================================================
    TemplateField("discount_rate", "折现率/报酬率", FieldTier.TIER5_VALUATION,
                  SourceCategory.PROSPECTUS, unit="%", per_project=False,
                  regex_patterns=[r"折现率[：:]\s*([\d.]+)\s*%",
                                  r"报酬率[：:]\s*([\d.]+)\s*%"],
                  table_keywords=["折现率", "报酬率"]),

    TemplateField("income_period_years", "收益期限", FieldTier.TIER5_VALUATION,
                  SourceCategory.PROSPECTUS, unit="年",
                  notes="精确到小数（剩余土地年限），如20.10年"),

    TemplateField("noicf_y1_appraised", "报告Y1 NOI/CF", FieldTier.TIER5_VALUATION,
                  SourceCategory.PROSPECTUS, unit="万元",
                  table_keywords=["年净收益", "NOI/CF", "净收益"],
                  notes="报告可能未明确披露，需从估值结论和折现率反推"),

    TemplateField("appraisal_value_wan", "报告估值结论", FieldTier.TIER5_VALUATION,
                  SourceCategory.PROSPECTUS, unit="万元",
                  regex_patterns=[r"评估价值[：:]\s*([\d,.]+)\s*万",
                                  r"市场价值[：:]\s*([\d,.]+)\s*万"],
                  table_keywords=["评估价值", "市场价值"]),

    TemplateField("capex_y1_absolute", "Y1 Capex绝对值(验证用)", FieldTier.TIER5_VALUATION,
                  SourceCategory.PROSPECTUS, unit="万元",
                  notes="报告明确披露Y1 Capex，用于反推总收入：总收入=Capex/2.5%"),

    # =========================================================================
    # Tier 6: 历史数据（近3年）
    # =========================================================================
    TemplateField("fixed_rent_excl_tax_2022", "固定租金(不含税)_2022", FieldTier.TIER6_HISTORICAL,
                  SourceCategory.PROSPECTUS, unit="万元", required=False),

    TemplateField("fixed_rent_excl_tax_2023", "固定租金(不含税)_2023", FieldTier.TIER6_HISTORICAL,
                  SourceCategory.PROSPECTUS, unit="万元"),

    TemplateField("fixed_rent_excl_tax_2024", "固定租金(不含税)_2024", FieldTier.TIER6_HISTORICAL,
                  SourceCategory.PROSPECTUS, unit="万元",
                  notes="用于验证Y1增长率假设合理性"),

    TemplateField("perf_rent_excl_tax_2024", "提成租金(不含税)_2024", FieldTier.TIER6_HISTORICAL,
                  SourceCategory.PROSPECTUS, unit="万元"),

    TemplateField("joint_op_net_2024", "联营净收入_2024", FieldTier.TIER6_HISTORICAL,
                  SourceCategory.PROSPECTUS, unit="万元"),

    TemplateField("prop_mgmt_fee_excl_tax_2024", "物业管理费(不含税)_2024", FieldTier.TIER6_HISTORICAL,
                  SourceCategory.PROSPECTUS, unit="万元"),

    TemplateField("parking_excl_tax_2024", "停车场收入(不含税)_2024", FieldTier.TIER6_HISTORICAL,
                  SourceCategory.PROSPECTUS, unit="万元"),

    TemplateField("multi_channel_excl_tax_2024", "多经收入(不含税)_2024", FieldTier.TIER6_HISTORICAL,
                  SourceCategory.PROSPECTUS, unit="万元"),

    TemplateField("ice_rink_excl_tax_2024", "冰场收入(不含税)_2024", FieldTier.TIER6_HISTORICAL,
                  SourceCategory.PROSPECTUS, unit="万元", required=False),

    TemplateField("other_excl_tax_2024", "其他收入(不含税)_2024", FieldTier.TIER6_HISTORICAL,
                  SourceCategory.PROSPECTUS, unit="万元"),

    TemplateField("fixed_rent_excl_tax_2025_ytd", "固定租金_2025年1-10月", FieldTier.TIER6_HISTORICAL,
                  SourceCategory.PROSPECTUS, unit="万元",
                  notes="用于年化推算Y1预测"),
]


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def get_template_by_tier(tier: FieldTier) -> List[TemplateField]:
    return [f for f in MALL_REIT_TEMPLATE if f.tier == tier]


def get_template_by_source(source: SourceCategory) -> List[TemplateField]:
    return [f for f in MALL_REIT_TEMPLATE if f.source_category == source]


def get_required_fields() -> List[TemplateField]:
    return [f for f in MALL_REIT_TEMPLATE if f.required]


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
                    "notes": f.notes,
                }
                for f in fields
            ],
        }
    return checklist
