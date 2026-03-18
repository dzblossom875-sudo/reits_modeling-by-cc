"""
全局配置和常量定义
"""

from enum import Enum
from typing import Dict, Any


class AssetType(str, Enum):
    """REITs资产类型"""
    INDUSTRIAL = "industrial"          # 产业园
    LOGISTICS = "logistics"            # 物流仓储
    HOUSING = "housing"                # 保障性租赁住房
    INFRASTRUCTURE = "infrastructure"  # 高速/能源特许经营权
    HOTEL = "hotel"                    # 酒店基础设施


class ParamCategory(str, Enum):
    """参数类别"""
    BASIC = "basic"           # 基础信息
    REVENUE = "revenue"       # 收入端
    COST = "cost"             # 成本端
    CAPITAL = "capital"       # 资本端


# 预测年限
FORECAST_YEARS = 10

# 默认折现率参考值 (基于资产类型)
DEFAULT_DISCOUNT_RATES: Dict[AssetType, float] = {
    AssetType.INDUSTRIAL: 0.075,      # 产业园: 7.5%
    AssetType.LOGISTICS: 0.070,       # 物流: 7.0%
    AssetType.HOUSING: 0.065,         # 保障房: 6.5%
    AssetType.INFRASTRUCTURE: 0.080,  # 基础设施: 8.0%
    AssetType.HOTEL: 0.085,           # 酒店: 8.5%
}

# 默认增长率参考值
DEFAULT_GROWTH_RATES: Dict[AssetType, Dict[str, float]] = {
    AssetType.INDUSTRIAL: {
        "rent_growth": 0.025,      # 租金年增长 2.5%
        "occupancy": 0.90,         # 目标出租率 90%
    },
    AssetType.LOGISTICS: {
        "rent_growth": 0.030,      # 租金年增长 3.0%
        "occupancy": 0.95,         # 目标出租率 95%
    },
    AssetType.HOUSING: {
        "rent_growth": 0.020,      # 租金年增长 2.0%
        "occupancy": 0.95,         # 目标入住率 95%
    },
    AssetType.INFRASTRUCTURE: {
        "traffic_growth": 0.030,   # 车流量/发电量增长 3.0%
        "toll_growth": 0.025,      # 收费增长 2.5%
    },
    AssetType.HOTEL: {
        "adr_growth": 0.030,       # 平均房价增长 3.0%
        "occupancy": 0.70,         # 目标入住率 70%
        "revpar_growth": 0.035,    # RevPAR增长 3.5%
    },
}

# 行业基准值（用于风险提示）
INDUSTRY_BENCHMARKS: Dict[AssetType, Dict[str, Any]] = {
    AssetType.INDUSTRIAL: {
        "rent_range": (50, 150),           # 元/㎡/月
        "occupancy_range": (0.75, 0.95),
        "opex_ratio": (0.15, 0.25),        # 运营费用占收入比
        "tenant_concentration_warning": 0.30,  # 单一租户占比警告线
    },
    AssetType.LOGISTICS: {
        "rent_range": (30, 80),            # 元/㎡/月
        "occupancy_range": (0.85, 0.98),
        "opex_ratio": (0.10, 0.20),
        "tenant_concentration_warning": 0.25,
    },
    AssetType.HOUSING: {
        "rent_range": (40, 100),           # 元/㎡/月
        "occupancy_range": (0.90, 0.98),
        "opex_ratio": (0.20, 0.30),
        "tenant_concentration_warning": None,  # 保障房通常不集中
    },
    AssetType.INFRASTRUCTURE: {
        "traffic_growth_range": (0.02, 0.06),
        "opex_ratio": (0.30, 0.50),
        "remaining_years_warning": 5,      # 剩余年限警告线
    },
    AssetType.HOTEL: {
        "adr_range": (300, 800),           # 平均房价 元/晚
        "occupancy_range": (0.60, 0.80),
        "revpar_range": (180, 500),
        "opex_ratio": (0.60, 0.75),        # 酒店运营费用较高
    },
}

# 参数名称映射（从常见表述到标准字段）
PARAM_NAME_MAPPINGS: Dict[str, str] = {
    # 基础信息
    "项目类型": "asset_type",
    "资产规模": "asset_scale",
    "建筑面积": "gross_area",
    "可租赁面积": "leasable_area",
    "剩余年限": "remaining_years",

    # 收入端
    "当前租金": "current_rent",
    "平均租金": "avg_rent",
    "租金单价": "rent_per_sqm",
    "租金增长率": "rent_growth_rate",
    "年租金增长": "annual_rent_growth",
    "出租率": "occupancy_rate",
    "入住率": "occupancy_rate",
    "满租率": "occupancy_rate",
    "出租率假设": "occupancy_rate",

    # 酒店特有
    "平均房价": "adr",
    "ADR": "adr",
    "RevPAR": "revpar",
    "客房收入": "room_revenue",
    "餐饮收入": "fb_revenue",
    "其他收入": "other_revenue",
    "餐饮收入占比": "fb_revenue_ratio",

    # 成本端
    "运营成本": "operating_expense",
    "运营费用": "operating_expense",
    "管理费用": "management_fee",
    "物业管理费": "property_management_fee",
    "维护费用": "maintenance_cost",
    "维修费用": "maintenance_cost",
    "税费": "tax",

    # 资本端
    "折现率": "discount_rate",
    "资本化率": "cap_rate",
    "资本性支出": "capex",
    "重置成本": "replacement_cost",
    "残值": "residual_value",
}

# 风险阈值配置
RISK_THRESHOLDS = {
    "param_deviation": 0.20,       # 参数偏离行业均值20%触发警告
    "growth_rate_ceiling": 0.10,   # 增长率上限（超过需特别说明）
    "short_remaining_years": 5,    # 剩余年限短于5年需特别关注
    "high_tenant_concentration": 0.30,  # 单一租户占比过高
    "cap_rate_discount_spread": 0.005,  # 资本化率与折现率倒挂阈值
}

# Excel模板配置
EXCEL_TEMPLATE_CONFIG = {
    "sheets": [
        "Dashboard",
        "Assumptions",
        "DCF",
        "Scenarios",
        "Sensitivity",
        "Data",
    ],
    "forecast_years": FORECAST_YEARS,
    "currency_format": '#,##0.00',
    "percentage_format": '0.00%',
}