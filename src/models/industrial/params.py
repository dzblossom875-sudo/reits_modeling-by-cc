"""
产业园REITs参数数据类

特点：分期开发、出租率爬坡、增值服务收入
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class IndustrialProjectConfig:
    """
    产业园单项目配置。

    NOI公式（待确认）:
      基础租金收入 = 租金单价 × 已开发面积 × 出租率 × 12
      增值服务收入 = 物业管理费 + 配套服务费
      NOI = 租金 + 增值服务 - 运营成本 - 税金 - 管理费 - Capex
    """
    name: str
    location: str = ""
    total_gfa: float = 0.0              # 总建筑面积（㎡）
    leasable_area: float = 0.0          # 可租赁面积（㎡）
    current_occupancy: float = 0.0      # 当前出租率
    stabilized_occupancy: float = 0.90  # 稳定出租率目标
    base_rent_per_sqm: float = 0.0      # 基础租金（元/㎡/月）
    remaining_years: float = 0.0
    capex_forecast: List[float] = field(default_factory=list)

    # 分期开发（可选）
    phase_schedule: List[Dict[str, Any]] = field(default_factory=list)
    # [{"year": 1, "area_added": 10000, "rent_per_sqm": 50}, ...]

    # 租户结构
    top_tenant_ratio: float = 0.0       # 最大单一租户占比（浓度风险）
    avg_lease_term_years: float = 3.0   # 平均租约年限
    rent_growth_rate: float = 0.025     # 年租金增长率

    prospectus_noi: float = 0.0
    source_page: Optional[int] = None
    noi_source: str = "prospectus"

    @property
    def base_capex(self) -> float:
        return self.capex_forecast[0] if self.capex_forecast else 0.0


INDUSTRIAL_PITFALLS = {
    "phased_development": {
        "rule": "分期开发项目现金流在建设期为负，需体现在DCF中",
        "check": "确认各期开发时间表和建设成本，不能只用稳定期收入",
    },
    "occupancy_ramp": {
        "rule": "新园区出租率通常需2-3年爬坡到稳定水平，不能直接用稳定率",
        "check": "招募书通常有逐年出租率预测，应与历史可比项目对比验证",
    },
    "vat_rate": {
        "rule": "工业/产业园租金增值税率9%（不动产）",
        "check": "确认收入口径是否含税",
    },
    "tenant_concentration": {
        "rule": "单一租户占比>30%为高风险，需在敏感性中体现",
        "check": "大租户到期不续约对NOI的冲击",
    },
}
