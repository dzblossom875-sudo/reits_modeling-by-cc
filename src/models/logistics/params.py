"""
物流仓储REITs参数数据类

特点：高出租率、冷库vs普通仓差异、大客户集中度
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LogisticsProjectConfig:
    """
    物流仓储单项目配置。

    NOI公式（待确认）:
      仓储租金 = 租金单价 × 可租面积 × 出租率 × 12
      NOI = 仓储租金 + 其他收入 - 运营成本 - 税金 - Capex
    """
    name: str
    location: str = ""
    gla: float = 0.0                    # 可租赁面积（㎡）
    cold_storage_ratio: float = 0.0     # 冷库占比（冷库租金溢价显著）
    ambient_rent_per_sqm: float = 0.0   # 常温仓租金（元/㎡/月）
    cold_rent_per_sqm: float = 0.0      # 冷库租金（元/㎡/月）
    current_occupancy: float = 0.0
    remaining_years: float = 0.0
    capex_forecast: List[float] = field(default_factory=list)

    avg_lease_term_years: float = 3.0
    renewal_rate: float = 0.85
    rent_growth_rate: float = 0.03

    prospectus_noi: float = 0.0
    source_page: Optional[int] = None
    noi_source: str = "prospectus"

    @property
    def base_capex(self) -> float:
        return self.capex_forecast[0] if self.capex_forecast else 0.0


LOGISTICS_PITFALLS = {
    "cold_vs_ambient": {
        "rule": "冷库租金通常是常温仓的2-3倍，需分开计算",
        "check": "招募书中有冷库/常温仓面积分布，不可用统一平均租金",
    },
    "high_occupancy_assumption": {
        "rule": "物流仓储历史出租率高（90%+），但续约率假设需谨慎",
        "check": "大租户(>20%占比)到期不续的冲击测试",
    },
    "capex_cold_system": {
        "rule": "冷库制冷系统更换周期约10-15年，Capex峰值需体现",
        "check": "预测期内是否有制冷系统大修Capex",
    },
    "vat_rate": {
        "rule": "物流仓储租金增值税率9%（不动产）",
        "check": "确认收入是否含税",
    },
}
