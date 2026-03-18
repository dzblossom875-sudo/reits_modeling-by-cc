"""
情景管理模块
支持多情景对比分析
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from copy import deepcopy

from .dcf_model import DCFModel, DCFInputs
from ..core.types import ValuationResult, ScenarioResult
from ..core.exceptions import CalculationError


@dataclass
class Scenario:
    """情景定义"""
    name: str                              # 情景名称
    description: str                       # 情景描述
    adjustments: Dict[str, Any]            # 参数调整
    valuation: Optional[ValuationResult] = None  # 估值结果


class ScenarioManager:
    """情景管理器"""

    def __init__(self, base_inputs: DCFInputs):
        self.base_inputs = base_inputs
        self.base_model = DCFModel(deepcopy(base_inputs))
        self.scenarios: Dict[str, Scenario] = {}

        # 自动计算基准情景
        self.base_scenario = Scenario(
            name="Base Case",
            description="基准情景",
            adjustments={}
        )

    def add_scenario(self, name: str, adjustments: Dict[str, Any], description: str = "") -> None:
        """
        添加新情景

        Args:
            name: 情景名称
            adjustments: 参数调整字典 {param_name: new_value}
            description: 情景描述
        """
        self.scenarios[name] = Scenario(
            name=name,
            description=description,
            adjustments=adjustments
        )

    def remove_scenario(self, name: str) -> None:
        """删除情景"""
        if name in self.scenarios:
            del self.scenarios[name]

    def calculate_all(self) -> List[ScenarioResult]:
        """
        计算所有情景

        Returns:
            List[ScenarioResult]: 所有情景的结果
        """
        results = []

        # 先计算基准情景
        base_result = self.base_model.calculate("Base Case")
        self.base_scenario.valuation = base_result

        results.append(ScenarioResult(
            scenario_name="Base Case",
            valuation=base_result,
            vs_base_percent=0.0
        ))

        # 计算其他情景
        for name, scenario in self.scenarios.items():
            result = self._calculate_scenario(scenario)
            vs_base = self._compare_to_base(result)

            results.append(ScenarioResult(
                scenario_name=name,
                valuation=result,
                vs_base_percent=vs_base
            ))

        return results

    def _calculate_scenario(self, scenario: Scenario) -> ValuationResult:
        """计算单个情景"""
        # 复制基准输入
        scenario_inputs = deepcopy(self.base_inputs)

        # 应用调整
        for param_name, new_value in scenario.adjustments.items():
            if hasattr(scenario_inputs, param_name):
                setattr(scenario_inputs, param_name, new_value)
            else:
                raise CalculationError(f"未知参数: {param_name}")

        # 创建模型并计算
        model = DCFModel(scenario_inputs)
        return model.calculate(scenario.name)

    def _compare_to_base(self, result: ValuationResult) -> float:
        """与基准情景对比"""
        if not self.base_scenario.valuation:
            return 0.0

        base_npv = self.base_scenario.valuation.npv
        if base_npv == 0:
            return 0.0

        return (result.npv - base_npv) / base_npv

    def get_scenario_comparison(self) -> Dict[str, Any]:
        """
        获取情景对比数据

        Returns:
            包含各情景关键指标的字典
        """
        if not self.base_scenario.valuation:
            self.calculate_all()

        comparison = {
            "scenarios": [],
            "base_npv": self.base_scenario.valuation.npv if self.base_scenario.valuation else 0,
        }

        # 基准情景
        if self.base_scenario.valuation:
            comparison["scenarios"].append({
                "name": "Base Case",
                "npv": round(self.base_scenario.valuation.npv, 2),
                "irr": round(self.base_scenario.valuation.irr, 4) if self.base_scenario.valuation.irr else None,
                "vs_base": 0.0,
                "adjustments": {}
            })

        # 其他情景
        for name, scenario in self.scenarios.items():
            if scenario.valuation:
                vs_base = self._compare_to_base(scenario.valuation)
                comparison["scenarios"].append({
                    "name": name,
                    "npv": round(scenario.valuation.npv, 2),
                    "irr": round(scenario.valuation.irr, 4) if scenario.valuation.irr else None,
                    "vs_base": round(vs_base * 100, 2),
                    "adjustments": scenario.adjustments
                })

        return comparison

    def get_parameter_sensitivity_ranking(self) -> List[Dict[str, Any]]:
        """
        获取参数敏感度排名
        通过逐个调整参数±10%来看对NPV的影响

        Returns:
            按敏感度排序的参数列表
        """
        if not self.base_scenario.valuation:
            self.base_model.calculate("Base Case")

        base_npv = self.base_scenario.valuation.npv
        sensitivities = []

        # 关键参数列表
        key_params = [
            "discount_rate",
            "rent_growth_rate",
            "occupancy_rate",
            "operating_expense_ratio",
            "current_rent",
        ]

        for param in key_params:
            if not hasattr(self.base_inputs, param):
                continue

            base_value = getattr(self.base_inputs, param)
            if base_value == 0:
                continue

            # +10%
            inputs_plus = deepcopy(self.base_inputs)
            new_value_plus = base_value * 1.1
            setattr(inputs_plus, param, new_value_plus)
            model_plus = DCFModel(inputs_plus)
            result_plus = model_plus.calculate()
            npv_change_plus = (result_plus.npv - base_npv) / base_npv if base_npv != 0 else 0

            # -10%
            inputs_minus = deepcopy(self.base_inputs)
            new_value_minus = base_value * 0.9
            setattr(inputs_minus, param, new_value_minus)
            model_minus = DCFModel(inputs_minus)
            result_minus = model_minus.calculate()
            npv_change_minus = (result_minus.npv - base_npv) / base_npv if base_npv != 0 else 0

            # 计算平均影响
            avg_impact = (abs(npv_change_plus) + abs(npv_change_minus)) / 2

            sensitivities.append({
                "param_name": param,
                "base_value": base_value,
                "impact_plus_10": round(npv_change_plus * 100, 2),
                "impact_minus_10": round(npv_change_minus * 100, 2),
                "avg_impact": round(avg_impact * 100, 2)
            })

        # 按影响程度排序
        sensitivities.sort(key=lambda x: x["avg_impact"], reverse=True)

        return sensitivities

    @staticmethod
    def create_common_scenarios(base_inputs: DCFInputs) -> "ScenarioManager":
        """
        创建常见情景（乐观、悲观、压力测试）

        Args:
            base_inputs: 基准输入

        Returns:
            配置好常见情景的ScenarioManager
        """
        manager = ScenarioManager(base_inputs)

        # 乐观情景
        manager.add_scenario(
            name="Optimistic",
            description="乐观情景：租金增长加快，空置率下降",
            adjustments={
                "rent_growth_rate": base_inputs.rent_growth_rate * 1.5,
                "occupancy_rate": min(base_inputs.occupancy_rate * 1.05, 0.98),
                "discount_rate": base_inputs.discount_rate * 0.95
            }
        )

        # 悲观情景
        manager.add_scenario(
            name="Pessimistic",
            description="悲观情景：租金增长放缓，空置率上升",
            adjustments={
                "rent_growth_rate": base_inputs.rent_growth_rate * 0.5,
                "occupancy_rate": base_inputs.occupancy_rate * 0.90,
                "discount_rate": base_inputs.discount_rate * 1.1
            }
        )

        # 压力情景
        manager.add_scenario(
            name="Stress Test",
            description="压力测试：极端市场条件",
            adjustments={
                "rent_growth_rate": 0.005,
                "occupancy_rate": max(base_inputs.occupancy_rate * 0.80, 0.70),
                "discount_rate": base_inputs.discount_rate * 1.2,
                "operating_expense_ratio": base_inputs.operating_expense_ratio * 1.15
            }
        )

        return manager
