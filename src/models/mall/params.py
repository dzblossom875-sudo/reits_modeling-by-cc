"""
商业地产REITs参数数据类（购物中心/商场）

待完善字段由用户后续填入。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MallProjectConfig:
    """
    单个商业项目配置。

    NOI公式（待确认）:
      客户租金收入 = 租金单价(元/㎡/月) × GLA(㎡) × 出租率 × 12
      物业管理收入 = 物业费单价 × 总面积 × 12
      NOI = 客户租金 + 物管收入 + 其他收入
            - 运营成本 - 税金 - 管理费 - Capex
    """
    name: str
    location: str = ""
    gla: float = 0.0               # 可租赁面积（㎡）
    gfa: float = 0.0               # 总建筑面积（㎡）
    occupancy_rate: float = 0.0    # 出租率
    base_rent_per_sqm: float = 0.0 # 基础租金（元/㎡/月）
    remaining_years: float = 0.0
    capex_forecast: List[float] = field(default_factory=list)

    # 租约结构
    anchor_tenant_ratio: float = 0.0     # 主力店占比（主力店租金通常有折扣）
    anchor_rent_discount: float = 0.75   # 主力店租金折扣系数
    lease_renewal_rate: float = 0.85     # 租约续约率假设
    vacancy_period_months: int = 3       # 空置期（月）

    # 收入增长
    rent_growth_rate: float = 0.03       # 年租金增长率
    prospectus_noi: float = 0.0          # 招募说明书基准NOI（用于验证）

    source_page: Optional[int] = None
    noi_source: str = "prospectus"

    @property
    def base_capex(self) -> float:
        return self.capex_forecast[0] if self.capex_forecast else 0.0


# 商业地产常见陷阱（新项目使用前必读）
MALL_PITFALLS = {
    "anchor_vs_inline": {
        "rule": "主力店（超市/影院）租金通常为内嵌店的40-60%，需分开计算",
        "check": "招募书中通常有各楼层/品牌租金分布表，避免用平均租金",
    },
    "effective_rent": {
        "rule": "有效租金 = 合同租金 × (1 - 空置率) × (1 - 租金减免期占比)",
        "check": "新项目开业期有租金优惠期（通常3-6个月），需扣除",
    },
    "property_management_income": {
        "rule": "物业管理费收入应单独列出，不可混入租金",
        "check": "物管费通常按总面积收取，与出租率无关",
    },
    "vat_on_rent": {
        "rule": "商业租金增值税率9%（不动产租赁），不同于酒店的6%",
        "check": "招募书收入若为含税收入，需/1.09换算",
    },
    "capex_renovation": {
        "rule": "商业地产每5-7年有大规模翻新Capex，需在预测期内体现",
        "check": "预测期超过5年时，应有一次Capex高峰",
    },
}
