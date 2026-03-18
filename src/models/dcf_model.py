"""
DCF估值模型核心
支持各类REITs资产的现金流预测和估值计算
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from ..core.types import (
    ProjectInfo, CashFlowItem, ValuationResult,
    ExtractedParam, ExtractedParams
)
from ..core.config import (
    AssetType, FORECAST_YEARS, DEFAULT_DISCOUNT_RATES,
    DEFAULT_GROWTH_RATES
)
from ..core.exceptions import CalculationError


@dataclass
class DCFInputs:
    """DCF模型输入参数"""
    # 基础信息
    asset_type: AssetType
    project_name: str = ""
    remaining_years: int = FORECAST_YEARS

    # 收入端
    current_rent: float = 0.0              # 当前租金（元/㎡/月）
    rent_growth_rate: float = 0.025        # 租金年增长率
    occupancy_rate: float = 0.90           # 出租率/入住率
    total_area: float = 0.0                # 总面积（㎡）
    other_income_ratio: float = 0.0        # 其他收入占比

    # 酒店特有
    adr: float = 0.0                       # 平均房价
    room_count: int = 0                    # 房间数
    fb_revenue_ratio: float = 0.30         # 餐饮收入占比

    # 基础设施特有
    traffic_volume: float = 0.0            # 日均车流量（万辆）
    toll_rate: float = 0.0                 # 收费标准
    traffic_growth: float = 0.03           # 车流量增长

    # 成本端
    operating_expense: float = 0.0         # 年运营费用（万元）
    operating_expense_ratio: float = 0.20  # 运营费用率
    management_fee_ratio: float = 0.05     # 管理费率
    maintenance_cost: float = 0.0          # 维护费用（万元）

    # 资本端
    discount_rate: float = 0.075           # 折现率
    cap_rate: Optional[float] = None       # 资本化率
    capex: float = 0.0                     # 资本性支出（万元）
    residual_value: float = 0.0            # 残值

    @classmethod
    def from_extracted_params(cls, params: ExtractedParams) -> "DCFInputs":
        """从提取的参数构建输入"""
        inputs = cls(asset_type=params.asset_type or AssetType.INDUSTRIAL)

        # 基础信息
        inputs.project_name = params.get_param_value("project_name", "")
        inputs.remaining_years = params.get_param_value("remaining_years", FORECAST_YEARS)
        inputs.total_area = float(params.get_param_value("leasable_area", 0) or 0)

        # 确保remaining_years是数字
        remaining_years = params.get_param_value("remaining_years", 10)
        try:
            inputs.remaining_years = int(float(remaining_years))
        except (ValueError, TypeError):
            inputs.remaining_years = 10

        # 收入端
        inputs.current_rent = params.get_param_value("current_rent", 0)
        inputs.rent_growth_rate = params.get_param_value("rent_growth_rate", 0.025)
        if inputs.rent_growth_rate > 1:  # 如果是百分比数值
            inputs.rent_growth_rate /= 100
        inputs.occupancy_rate = params.get_param_value("occupancy_rate", 0.90)
        if inputs.occupancy_rate > 1:
            inputs.occupancy_rate /= 100

        # 酒店特有
        inputs.adr = params.get_param_value("adr", 0)
        inputs.room_count = int(params.get_param_value("room_count", 0))
        inputs.fb_revenue_ratio = params.get_param_value("fb_revenue_ratio", 0.30)
        if inputs.fb_revenue_ratio > 1:
            inputs.fb_revenue_ratio /= 100

        # 基础设施特有
        inputs.traffic_volume = params.get_param_value("traffic_volume", 0)
        inputs.toll_rate = params.get_param_value("toll_rate", 0)
        inputs.traffic_growth = params.get_param_value("traffic_growth", 0.03)
        if inputs.traffic_growth > 1:
            inputs.traffic_growth /= 100

        # 成本端
        inputs.operating_expense = params.get_param_value("operating_expense", 0)
        inputs.operating_expense_ratio = params.get_param_value("operating_expense_ratio", 0.20)
        if inputs.operating_expense_ratio > 1:
            inputs.operating_expense_ratio /= 100
        inputs.maintenance_cost = params.get_param_value("maintenance_cost", 0)

        # 资本端
        inputs.discount_rate = params.get_param_value("discount_rate", 0.075)
        if inputs.discount_rate > 1:
            inputs.discount_rate /= 100
        inputs.cap_rate = params.get_param_value("cap_rate")
        if inputs.cap_rate and inputs.cap_rate > 1:
            inputs.cap_rate /= 100
        inputs.capex = params.get_param_value("capex", 0)

        return inputs


class DCFModel:
    """DCF估值模型"""

    def __init__(self, inputs: DCFInputs):
        self.inputs = inputs
        self.cash_flows: List[CashFlowItem] = []

    def calculate(self, scenario_name: str = "Base Case") -> ValuationResult:
        """
        执行DCF计算

        Returns:
            ValuationResult: 估值结果
        """
        try:
            # 生成现金流预测
            self.cash_flows = self._generate_cash_flows()

            # 计算NPV
            npv = self._calculate_npv()

            # 计算IRR
            irr = self._calculate_irr()

            # 计算资本化率估值（如有）
            cap_value = self._calculate_cap_value()

            # 构建项目信息
            project_info = ProjectInfo(
                name=self.inputs.project_name,
                asset_type=self.inputs.asset_type,
                total_area=self.inputs.total_area,
                remaining_years=self.inputs.remaining_years
            )

            # 构建假设清单
            assumptions = self._build_assumptions()

            return ValuationResult(
                project_info=project_info,
                asset_type=self.inputs.asset_type,
                npv=npv,
                irr=irr,
                cap_rate=cap_value,
                dcf_value=npv,
                scenario_name=scenario_name,
                cash_flows=self.cash_flows,
                assumptions=assumptions
            )

        except Exception as e:
            raise CalculationError(f"DCF计算失败: {str(e)}")

    def _generate_cash_flows(self) -> List[CashFlowItem]:
        """生成现金流预测"""
        cash_flows = []

        if self.inputs.asset_type == AssetType.HOTEL:
            return self._generate_hotel_cash_flows()
        elif self.inputs.asset_type == AssetType.INFRASTRUCTURE:
            return self._generate_infrastructure_cash_flows()
        else:
            return self._generate_standard_cash_flows()

    def _generate_standard_cash_flows(self) -> List[CashFlowItem]:
        """生成标准物业现金流（产业园、物流、保障房）"""
        cash_flows = []
        current_rent = self.inputs.current_rent

        for year in range(1, self.inputs.remaining_years + 1):
            cf = CashFlowItem(year=year)

            # 计算当年租金（考虑增长）
            annual_rent = current_rent * ((1 + self.inputs.rent_growth_rate) ** (year - 1))

            # 计算年收入
            potential_rental_income = annual_rent * 12 * self.inputs.total_area / 10000  # 转换为万元
            actual_rental_income = potential_rental_income * self.inputs.occupancy_rate
            cf.rental_income = actual_rental_income

            # 其他收入
            cf.other_income = actual_rental_income * self.inputs.other_income_ratio
            cf.total_income = cf.rental_income + cf.other_income

            # 运营成本
            if self.inputs.operating_expense > 0:
                # 按固定金额计算，假设每年增长3%
                cf.operating_expense = self.inputs.operating_expense * ((1.03) ** (year - 1))
            else:
                # 按比例计算
                cf.operating_expense = cf.total_income * self.inputs.operating_expense_ratio

            # 管理费用
            cf.management_fee = cf.total_income * self.inputs.management_fee_ratio

            cash_flows.append(cf)

        return cash_flows

    def _generate_hotel_cash_flows(self) -> List[CashFlowItem]:
        """生成酒店现金流"""
        cash_flows = []
        current_adr = self.inputs.adr

        # 计算可售房晚数
        available_room_nights = self.inputs.room_count * 365

        for year in range(1, self.inputs.remaining_years + 1):
            cf = CashFlowItem(year=year)
            cf.available_room_nights = available_room_nights

            # 计算当年ADR（考虑增长）
            adr = current_adr * ((1 + self.inputs.rent_growth_rate) ** (year - 1))
            cf.adr = adr
            cf.occupancy = self.inputs.occupancy_rate

            # 客房收入
            cf.room_revenue = adr * available_room_nights * self.inputs.occupancy_rate / 10000  # 万元

            # RevPAR
            cf.fb_revenue = cf.room_revenue * self.inputs.fb_revenue_ratio
            cf.other_revenue = cf.room_revenue * 0.05  # 假设其他收入占5%

            cf.total_income = cf.room_revenue + cf.fb_revenue + cf.other_revenue

            # 酒店运营成本较高，通常在60-75%
            cf.operating_expense = cf.total_income * self.inputs.operating_expense_ratio
            cf.management_fee = cf.total_income * 0.03  # 酒店管理费率约3%

            cash_flows.append(cf)

        return cash_flows

    def _generate_infrastructure_cash_flows(self) -> List[CashFlowItem]:
        """生成基础设施现金流（高速、能源）"""
        cash_flows = []
        traffic_volume = self.inputs.traffic_volume

        for year in range(1, self.inputs.remaining_years + 1):
            cf = CashFlowItem(year=year)

            # 计算当年车流量（考虑增长）
            current_traffic = traffic_volume * ((1 + self.inputs.traffic_growth) ** (year - 1))

            # 收入 = 车流量 * 收费标准 * 365天
            annual_income = current_traffic * self.inputs.toll_rate * 365 / 10000  # 万元
            cf.total_income = annual_income
            cf.rental_income = annual_income

            # 基础设施运营成本较高
            if self.inputs.operating_expense > 0:
                cf.operating_expense = self.inputs.operating_expense * ((1.02) ** (year - 1))
            else:
                cf.operating_expense = annual_income * self.inputs.operating_expense_ratio

            # 维护费用
            cf.operating_expense += self.inputs.maintenance_cost

            cf.management_fee = cf.total_income * self.inputs.management_fee_ratio

            cash_flows.append(cf)

        return cash_flows

    def _calculate_npv(self) -> float:
        """计算NPV"""
        npv = 0.0

        for cf in self.cash_flows:
            noi = cf.calculate_noi()
            # 减去资本性支出
            if cf.year == 1:
                noi -= self.inputs.capex

            # 折现
            discount_factor = (1 + self.inputs.discount_rate) ** cf.year
            npv += noi / discount_factor

        # 加上终值（最后一年）
        if self.cash_flows:
            terminal_value = self._calculate_terminal_value()
            final_discount_factor = (1 + self.inputs.discount_rate) ** len(self.cash_flows)
            npv += terminal_value / final_discount_factor

        return npv

    def _calculate_terminal_value(self) -> float:
        """计算终值"""
        if self.inputs.residual_value > 0:
            return self.inputs.residual_value

        # 使用资本化率计算终值
        if self.inputs.cap_rate and self.inputs.cap_rate > 0:
            if self.cash_flows:
                final_year_noi = self.cash_flows[-1].calculate_noi()
                return final_year_noi / self.inputs.cap_rate

        # 使用Gordon增长模型
        if self.cash_flows:
            final_year_noi = self.cash_flows[-1].calculate_noi()
            terminal_growth = 0.02  # 假设永续增长率2%
            return final_year_noi * (1 + terminal_growth) / (self.inputs.discount_rate - terminal_growth)

        return 0.0

    def _calculate_irr(self) -> Optional[float]:
        """计算IRR（简化实现）"""
        # IRR计算较为复杂，这里提供一个简化的实现
        # 实际应用中可能需要使用numpy_financial或scipy
        try:
            import numpy as np
            from numpy_financial import irr

            # 构建现金流序列
            cash_flows = [-self.inputs.capex]  # 初始投资
            for cf in self.cash_flows:
                cash_flows.append(cf.calculate_noi())

            # 加上终值
            if len(cash_flows) > 1:
                cash_flows[-1] += self._calculate_terminal_value()

            return irr(cash_flows)
        except ImportError:
            return None
        except Exception:
            return None

    def _calculate_cap_value(self) -> Optional[float]:
        """使用资本化率计算估值"""
        if not self.inputs.cap_rate or self.inputs.cap_rate <= 0:
            return None

        # 使用第一年的NOI
        if self.cash_flows:
            first_year_noi = self.cash_flows[0].calculate_noi()
            return first_year_noi / self.inputs.cap_rate

        return None

    def _build_assumptions(self) -> Dict[str, Any]:
        """构建假设清单"""
        return {
            "forecast_years": self.inputs.remaining_years,
            "discount_rate": f"{self.inputs.discount_rate:.2%}",
            "rent_growth_rate": f"{self.inputs.rent_growth_rate:.2%}",
            "occupancy_rate": f"{self.inputs.occupancy_rate:.2%}",
            "operating_expense_ratio": f"{self.inputs.operating_expense_ratio:.2%}",
            "capex": f"{self.inputs.capex:.2f}万元",
            "asset_type": self.inputs.asset_type.value,
        }

    def adjust_parameter(self, param_name: str, new_value: Any) -> None:
        """调整单个参数（用于情景分析）"""
        if hasattr(self.inputs, param_name):
            setattr(self.inputs, param_name, new_value)
        else:
            raise CalculationError(f"未知参数: {param_name}")
