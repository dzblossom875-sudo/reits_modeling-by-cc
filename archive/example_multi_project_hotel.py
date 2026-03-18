#!/usr/bin/env python3
"""
华住REIT多项目分算示例
基于招募说明书关键数据，分项目计算后汇总

计算逻辑：
1. 酒店部分：
   - 客房收益 = ADR * 入住率 * 365 * 客房数 / 10000 (万元)
   - 总收益 = 客房收入 + OTA收入 + 餐饮收入 + 其他收入
   - GOP = 总收益 - 运营费用

2. 商业部分：
   - 商业净收益 = 租金收入 + 物业费 - 商业运营费用

3. 汇总：
   - 年净收益 = 酒店GOP + 商业净收益 - 其他总费用 - 资本性支出
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dataclasses import dataclass, field
from typing import List, Dict
from src.core.config import AssetType
from src.models.dcf_model import DCFModel, DCFInputs
from src.models.scenarios import ScenarioManager
from src.exporters import ExcelGenerator, JSONExporter, Visualizer


@dataclass
class HotelProject:
    """单个酒店项目"""
    name: str

    # 基础信息
    adr: float                      # 平均房价（元/晚）
    occupancy_rate: float           # 入住率
    room_count: int                 # 客房数
    adr_growth: float = 0.03        # ADR年增长率

    # 收入明细（万元）
    room_revenue: float = 0.0       # 客房收入
    ota_revenue: float = 0.0        # OTA收入
    fb_revenue: float = 0.0         # 餐饮收入
    other_revenue: float = 0.0      # 其他收入

    # 运营费用（万元）
    operating_expenses: Dict[str, float] = field(default_factory=dict)
    total_operating_expense: float = 0.0

    # 商业部分（万元）
    commercial_rent: float = 0.0
    commercial_mgmt_fee: float = 0.0
    commercial_opex: float = 0.0

    # 其他费用（万元）
    property_fee: float = 0.0
    insurance: float = 0.0
    property_tax: float = 0.0
    land_use_tax: float = 0.0
    management_fee: float = 0.0

    # 资本性支出（万元）
    capex: float = 0.0

    def calculate_hotel_revenue(self) -> float:
        """计算酒店总收入（万元）"""
        return self.room_revenue + self.ota_revenue + self.fb_revenue + self.other_revenue

    def calculate_gop(self) -> float:
        """计算酒店GOP（营业毛利）"""
        return self.calculate_hotel_revenue() - self.total_operating_expense

    def calculate_commercial_net(self) -> float:
        """计算商业部分净收益"""
        return self.commercial_rent + self.commercial_mgmt_fee - self.commercial_opex

    def calculate_other_expenses(self) -> float:
        """计算其他总费用"""
        return (self.property_fee + self.insurance + self.property_tax +
                self.land_use_tax + self.management_fee)

    def calculate_annual_noicf(self) -> float:
        """
        计算年净收益（NOI/CF）
        公式：酒店GOP + 商业净收益 - 其他费用 - 资本性支出
        """
        return (self.calculate_gop() + self.calculate_commercial_net() -
                self.calculate_other_expenses() - self.capex)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "name": self.name,
            "adr": self.adr,
            "occupancy_rate": self.occupancy_rate,
            "room_count": self.room_count,
            "hotel_revenue": self.calculate_hotel_revenue(),
            "gop": self.calculate_gop(),
            "commercial_net": self.calculate_commercial_net(),
            "other_expenses": self.calculate_other_expenses(),
            "capex": self.capex,
            "annual_noicf": self.calculate_annual_noicf(),
        }


def create_huazhu_projects() -> List[HotelProject]:
    """
    创建华住REIT的各项目数据
    基于招募说明书披露的关键信息
    """
    projects = []

    # 项目1: 南京汉庭酒店（示例数据）
    projects.append(HotelProject(
        name="南京汉庭酒店",
        adr=350.0,                          # 平均房价350元/晚
        occupancy_rate=0.78,                # 入住率78%
        room_count=150,                     # 150间客房
        adr_growth=0.025,
        # 收入（万元）
        room_revenue=1496.0,                # 客房收入
        ota_revenue=280.0,                  # OTA收入
        fb_revenue=120.0,                   # 餐饮收入
        other_revenue=45.0,                 # 其他收入
        # 运营费用（万元）
        total_operating_expense=1100.0,     # 总运营费用
        operating_expenses={
            "personnel": 500.0,             # 人工
            "fb_cost": 60.0,                # 餐饮成本
            "cleaning": 80.0,               # 清洁物料
            "utilities": 150.0,             # 能源
            "maintenance": 100.0,           # 维护费
            "marketing": 80.0,              # 营销推广
            "system": 50.0,                 # 数据系统
            "other": 80.0,                  # 其他
        },
        # 商业部分（万元）
        commercial_rent=80.0,
        commercial_mgmt_fee=20.0,
        commercial_opex=30.0,
        # 其他费用（万元）
        property_fee=45.0,
        insurance=15.0,
        property_tax=25.0,
        land_use_tax=5.0,
        management_fee=60.0,
        # 资本性支出
        capex=80.0,
    ))

    # 项目2: 南京全季酒店（示例数据）
    projects.append(HotelProject(
        name="南京全季酒店",
        adr=520.0,                          # 平均房价520元/晚
        occupancy_rate=0.82,                # 入住率82%
        room_count=180,                     # 180间客房
        adr_growth=0.03,
        # 收入（万元）
        room_revenue=2800.0,                # 客房收入
        ota_revenue=450.0,                  # OTA收入
        fb_revenue=280.0,                   # 餐饮收入
        other_revenue=85.0,                 # 其他收入
        # 运营费用（万元）
        total_operating_expense=2200.0,     # 总运营费用
        operating_expenses={
            "personnel": 950.0,
            "fb_cost": 150.0,
            "cleaning": 140.0,
            "utilities": 280.0,
            "maintenance": 200.0,
            "marketing": 180.0,
            "system": 100.0,
            "other": 200.0,
        },
        # 商业部分（万元）
        commercial_rent=120.0,
        commercial_mgmt_fee=35.0,
        commercial_opex=50.0,
        # 其他费用（万元）
        property_fee=80.0,
        insurance=25.0,
        property_tax=45.0,
        land_use_tax=8.0,
        management_fee=120.0,
        # 资本性支出
        capex=150.0,
    ))

    # 项目3: 南京桔子酒店（示例数据）
    projects.append(HotelProject(
        name="南京桔子酒店",
        adr=450.0,                          # 平均房价450元/晚
        occupancy_rate=0.75,                # 入住率75%
        room_count=165,                     # 165间客房
        adr_growth=0.028,
        # 收入（万元）
        room_revenue=2030.0,                # 客房收入
        ota_revenue=380.0,                  # OTA收入
        fb_revenue=200.0,                   # 餐饮收入
        other_revenue=65.0,                 # 其他收入
        # 运营费用（万元）
        total_operating_expense=1650.0,     # 总运营费用
        operating_expenses={
            "personnel": 750.0,
            "fb_cost": 110.0,
            "cleaning": 115.0,
            "utilities": 220.0,
            "maintenance": 160.0,
            "marketing": 140.0,
            "system": 80.0,
            "other": 75.0,
        },
        # 商业部分（万元）
        commercial_rent=100.0,
        commercial_mgmt_fee=28.0,
        commercial_opex=40.0,
        # 其他费用（万元）
        property_fee=65.0,
        insurance=20.0,
        property_tax=35.0,
        land_use_tax=6.0,
        management_fee=95.0,
        # 资本性支出
        capex=120.0,
    ))

    return projects


def print_project_details(projects: List[HotelProject]):
    """打印各项目详细信息"""
    print("\n" + "=" * 70)
    print("  各项目详细计算")
    print("=" * 70)

    for i, proj in enumerate(projects, 1):
        print(f"\n【项目{i}】{proj.name}")
        print("-" * 60)

        print(f"  [基础信息]")
        print(f"    ADR: {proj.adr:.0f} 元/晚")
        print(f"    入住率: {proj.occupancy_rate:.0%}")
        print(f"    客房数: {proj.room_count} 间")
        print(f"    ADR增长率: {proj.adr_growth:.1%}")

        print(f"\n  [酒店部分收入]")
        print(f"    客房收入: {proj.room_revenue:,.2f} 万元")
        print(f"    OTA收入: {proj.ota_revenue:,.2f} 万元")
        print(f"    餐饮收入: {proj.fb_revenue:,.2f} 万元")
        print(f"    其他收入: {proj.other_revenue:,.2f} 万元")
        print(f"    酒店总收入: {proj.calculate_hotel_revenue():,.2f} 万元")

        print(f"\n  [酒店运营成本]")
        for item, amount in proj.operating_expenses.items():
            print(f"    {item}: {amount:,.2f} 万元")
        print(f"    运营费用合计: {proj.total_operating_expense:,.2f} 万元")
        print(f"    GOP: {proj.calculate_gop():,.2f} 万元")

        print(f"\n  [商业部分]")
        print(f"    商业租金: {proj.commercial_rent:,.2f} 万元")
        print(f"    商业物业费: {proj.commercial_mgmt_fee:,.2f} 万元")
        print(f"    商业运营费: {proj.commercial_opex:,.2f} 万元")
        print(f"    商业净收益: {proj.calculate_commercial_net():,.2f} 万元")

        print(f"\n  [其他费用]")
        print(f"    物业费: {proj.property_fee:,.2f} 万元")
        print(f"    保险费: {proj.insurance:,.2f} 万元")
        print(f"    房产税: {proj.property_tax:,.2f} 万元")
        print(f"    土地使用税: {proj.land_use_tax:,.2f} 万元")
        print(f"    酒店管理费: {proj.management_fee:,.2f} 万元")
        print(f"    其他费用合计: {proj.calculate_other_expenses():,.2f} 万元")

        print(f"\n  [资本性支出]")
        print(f"    年资本性支出: {proj.capex:,.2f} 万元")

        print(f"\n  [年净收益]")
        print(f"    >>> {proj.calculate_annual_noicf():,.2f} 万元 <<<")


def print_summary(projects: List[HotelProject]):
    """打印汇总数据"""
    print("\n" + "=" * 70)
    print("  汇总数据")
    print("=" * 70)

    total_room_revenue = sum(p.room_revenue for p in projects)
    total_ota = sum(p.ota_revenue for p in projects)
    total_fb = sum(p.fb_revenue for p in projects)
    total_other = sum(p.other_revenue for p in projects)
    total_opex = sum(p.total_operating_expense for p in projects)
    total_gop = sum(p.calculate_gop() for p in projects)
    total_commercial = sum(p.calculate_commercial_net() for p in projects)
    total_other_exp = sum(p.calculate_other_expenses() for p in projects)
    total_capex = sum(p.capex for p in projects)
    total_noicf = sum(p.calculate_annual_noicf() for p in projects)

    print(f"\n  [收入汇总] (万元)")
    print(f"    项目数量: {len(projects)} 个")
    print(f"    客房收入合计: {total_room_revenue:,.2f}")
    print(f"    OTA收入合计: {total_ota:,.2f}")
    print(f"    餐饮收入合计: {total_fb:,.2f}")
    print(f"    其他收入合计: {total_other:,.2f}")

    print(f"\n  [成本费用汇总] (万元)")
    print(f"    运营费用合计: {total_opex:,.2f}")
    print(f"    GOP合计: {total_gop:,.2f}")
    print(f"    商业净收益合计: {total_commercial:,.2f}")
    print(f"    其他费用合计: {total_other_exp:,.2f}")
    print(f"    资本性支出合计: {total_capex:,.2f}")

    print(f"\n  [关键指标]")
    weighted_adr = sum(p.adr * p.room_count for p in projects) / sum(p.room_count for p in projects)
    weighted_occ = sum(p.occupancy_rate * p.room_count for p in projects) / sum(p.room_count for p in projects)
    print(f"    总客房数: {sum(p.room_count for p in projects)} 间")
    print(f"    加权平均ADR: {weighted_adr:.0f} 元")
    print(f"    加权平均入住率: {weighted_occ:.1%}")

    print(f"\n  [年净收益汇总]")
    print(f"    >>> 年净收益合计: {total_noicf:,.2f} 万元 <<<")

    return total_noicf


def run_valuation(projects: List[HotelProject], output_dir: str):
    """运行DCF估值"""
    print("\n" + "=" * 70)
    print("  DCF估值计算")
    print("=" * 70)

    # 计算年净收益
    annual_noicf = sum(p.calculate_annual_noicf() for p in projects)

    # 构建DCF输入
    inputs = DCFInputs(
        asset_type=AssetType.HOTEL,
        project_name="华泰紫金南京华住酒店REIT",
        remaining_years=19,                 # 剩余年限19年
        total_area=sum(p.room_count for p in projects) * 35,  # 估算总面积

        # 使用年净收益作为基础（简化处理）
        current_rent=0,                     # 酒店不使用租金模式
        rent_growth_rate=0.03,              # 年增长率3%
        occupancy_rate=0.78,                # 平均入住率

        # 酒店特有
        adr=400.0,                          # 加权平均ADR
        room_count=sum(p.room_count for p in projects),
        fb_revenue_ratio=0.28,              # 餐饮收入占比

        # 成本（已包含在NOI计算中）
        operating_expense=0,                # 已单独计算
        operating_expense_ratio=0.0,

        # 资本端
        discount_rate=0.0575,               # 折现率5.75%
        capex=0,                            # 已单独计算
    )

    # 创建自定义DCF模型（使用项目NOI）
    from src.core.types import CashFlowItem

    cash_flows = []
    for year in range(1, inputs.remaining_years + 1):
        # 考虑增长
        growth_factor = (1 + inputs.rent_growth_rate) ** (year - 1)
        year_noicf = annual_noicf * growth_factor

        cf = CashFlowItem(
            year=year,
            total_income=year_noicf,
            operating_expense=0,
            management_fee=0,
        )
        cash_flows.append(cf)

    # 手动计算NPV
    npv = 0.0
    for cf in cash_flows:
        discount_factor = (1 + inputs.discount_rate) ** cf.year
        npv += cf.total_income / discount_factor

    # 终值（第19年末）
    terminal_growth = 0.02
    terminal_value = cash_flows[-1].total_income * (1 + terminal_growth) / (inputs.discount_rate - terminal_growth)
    terminal_pv = terminal_value / ((1 + inputs.discount_rate) ** inputs.remaining_years)
    total_npv = npv + terminal_pv

    print(f"\n  [估值假设]")
    print(f"    首年净收益: {annual_noicf:,.2f} 万元")
    print(f"    年增长率: {inputs.rent_growth_rate:.2%}")
    print(f"    折现率: {inputs.discount_rate:.2%}")
    print(f"    预测年限: {inputs.remaining_years} 年")

    print(f"\n  [估值结果]")
    print(f"    现金流现值: {npv:,.2f} 万元")
    print(f"    终值现值: {terminal_pv:,.2f} 万元")
    print(f"    >>> DCF估值: {total_npv:,.2f} 万元 <<<")

    # 多情景分析
    print(f"\n  [情景分析]")
    scenarios = {
        "Base": total_npv,
        "Optimistic (+20%)": total_npv * 1.2,
        "Pessimistic (-20%)": total_npv * 0.8,
        "Stress Test (-30%)": total_npv * 0.7,
    }
    for name, value in scenarios.items():
        print(f"    {name}: {value:,.0f} 万元")

    # 生成输出
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 保存项目数据JSON
    import json
    projects_data = {
        "projects": [p.to_dict() for p in projects],
        "summary": {
            "total_noicf": annual_noicf,
            "dcf_valuation": total_npv,
            "total_room_count": sum(p.room_count for p in projects),
        }
    }
    with open(output_path / "multi_project_analysis.json", 'w', encoding='utf-8') as f:
        json.dump(projects_data, f, ensure_ascii=False, indent=2)

    print(f"\n  [输出文件]")
    print(f"    项目分析JSON: {output_path / 'multi_project_analysis.json'}")

    return total_npv


def main():
    print("=" * 70)
    print("  华住REIT多项目分算示例")
    print("=" * 70)
    print("\n  计算逻辑:")
    print("    1. 分项目计算酒店部分GOP")
    print("    2. 分项目计算商业部分净收益")
    print("    3. 扣除其他费用和资本性支出")
    print("    4. 汇总年净收益进行DCF估值")

    # 创建项目
    projects = create_huazhu_projects()

    # 打印项目详情
    print_project_details(projects)

    # 打印汇总
    print_summary(projects)

    # 运行估值
    valuation = run_valuation(projects, "./output/huazhu_multi_project")

    print("\n" + "=" * 70)
    print("  计算完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
