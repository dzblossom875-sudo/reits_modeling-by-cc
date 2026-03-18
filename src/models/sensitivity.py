"""
敏感度分析模块
支持单变量和多变量敏感度分析
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from copy import deepcopy

from .dcf_model import DCFModel, DCFInputs
from ..core.types import SensitivityResult
from ..core.exceptions import CalculationError


@dataclass
class SensitivityVariable:
    """敏感度分析变量"""
    param_name: str                    # 参数名
    base_value: float                  # 基准值
    variations: List[float]            # 变化幅度列表（如 [-0.2, -0.1, 0, 0.1, 0.2]）
    unit: str = ""                     # 单位（用于显示）


class SensitivityAnalyzer:
    """敏感度分析器"""

    def __init__(self, base_inputs: DCFInputs):
        self.base_inputs = base_inputs
        self.base_model = DCFModel(deepcopy(base_inputs))
        self.base_result = self.base_model.calculate()

    def analyze_single_variable(
        self,
        param_name: str,
        variations: Optional[List[float]] = None,
        variation_range: Tuple[float, float] = (-0.20, 0.20),
        steps: int = 5
    ) -> SensitivityResult:
        """
        单变量敏感度分析

        Args:
            param_name: 要分析的参数名
            variations: 变化幅度列表（如[-0.2, -0.1, 0, 0.1, 0.2]），None时自动生成
            variation_range: 变化范围（默认±20%）
            steps: 分析步数

        Returns:
            SensitivityResult: 敏感度分析结果
        """
        if not hasattr(self.base_inputs, param_name):
            raise CalculationError(f"未知参数: {param_name}")

        base_value = getattr(self.base_inputs, param_name)
        base_npv = self.base_result.npv

        result = SensitivityResult(
            param_name=param_name,
            base_value=base_value,
            base_npv=base_npv
        )

        # 生成变化幅度
        if variations is None:
            variations = self._generate_variations(variation_range, steps)

        # 计算各变化下的NPV
        for var_pct in variations:
            new_value = base_value * (1 + var_pct)

            # 复制输入并修改参数
            inputs_copy = deepcopy(self.base_inputs)
            setattr(inputs_copy, param_name, new_value)

            # 计算新NPV
            model = DCFModel(inputs_copy)
            new_result = model.calculate()

            result.add_variation(
                variation_pct=var_pct * 100,
                new_value=new_value,
                new_npv=new_result.npv
            )

        return result

    def analyze_multiple_variables(
        self,
        variables: List[SensitivityVariable]
    ) -> Dict[str, SensitivityResult]:
        """
        多变量敏感度分析

        Args:
            variables: 变量列表

        Returns:
            Dict[str, SensitivityResult]: 各变量的分析结果
        """
        results = {}

        for var in variables:
            result = self.analyze_single_variable(
                param_name=var.param_name,
                variations=var.variations
            )
            results[var.param_name] = result

        return results

    def generate_tornado_data(self) -> List[Dict[str, Any]]:
        """
        生成Tornado图数据
        分析关键参数±10%变化对NPV的影响

        Returns:
            用于Tornado图的数据
        """
        tornado_data = []
        base_npv = self.base_result.npv

        # 关键参数及其基准值
        key_params = [
            ("discount_rate", "折现率"),
            ("rent_growth_rate", "租金增长率"),
            ("occupancy_rate", "出租率"),
            ("operating_expense_ratio", "运营费用率"),
            ("current_rent", "当前租金"),
            ("capex", "资本性支出"),
        ]

        for param_name, display_name in key_params:
            if not hasattr(self.base_inputs, param_name):
                continue

            base_value = getattr(self.base_inputs, param_name)
            if base_value == 0:
                continue

            # -10%
            inputs_minus = deepcopy(self.base_inputs)
            setattr(inputs_minus, param_name, base_value * 0.9)
            model_minus = DCFModel(inputs_minus)
            npv_minus = model_minus.calculate().npv

            # +10%
            inputs_plus = deepcopy(self.base_inputs)
            setattr(inputs_plus, param_name, base_value * 1.1)
            model_plus = DCFModel(inputs_plus)
            npv_plus = model_plus.calculate().npv

            tornado_data.append({
                "param_name": param_name,
                "display_name": display_name,
                "base_value": base_value,
                "base_npv": base_npv,
                "minus_10_npv": npv_minus,
                "plus_10_npv": npv_plus,
                "minus_10_impact": npv_minus - base_npv,
                "plus_10_impact": npv_plus - base_npv,
                "total_swing": abs(npv_plus - base_npv) + abs(npv_minus - base_npv)
            })

        # 按总波动幅度排序
        tornado_data.sort(key=lambda x: x["total_swing"], reverse=True)

        return tornado_data

    def find_break_even(
        self,
        param_name: str,
        target_npv: float = 0,
        tolerance: float = 0.01,
        max_iterations: int = 50
    ) -> Optional[float]:
        """
        寻找参数盈亏平衡点（NPV=target_npv时的参数值）

        Args:
            param_name: 参数名
            target_npv: 目标NPV，默认0
            tolerance: 容差
            max_iterations: 最大迭代次数

        Returns:
            盈亏平衡时的参数值，或None（未找到）
        """
        if not hasattr(self.base_inputs, param_name):
            raise CalculationError(f"未知参数: {param_name}")

        base_value = getattr(self.base_inputs, param_name)

        # 二分查找
        low, high = base_value * 0.5, base_value * 1.5

        for _ in range(max_iterations):
            mid = (low + high) / 2

            inputs_copy = deepcopy(self.base_inputs)
            setattr(inputs_copy, param_name, mid)

            model = DCFModel(inputs_copy)
            npv = model.calculate().npv

            if abs(npv - target_npv) < tolerance:
                return mid

            # 根据NPV与目标的关系调整搜索范围
            if npv > target_npv:
                # NPV偏高，需要降低收入或提高成本
                if param_name in ["discount_rate", "operating_expense_ratio"]:
                    low = mid
                else:
                    high = mid
            else:
                if param_name in ["discount_rate", "operating_expense_ratio"]:
                    high = mid
                else:
                    low = mid

        return None

    def generate_sensitivity_table(
        self,
        param1: str,
        param2: str,
        range1: Tuple[float, float] = (-0.2, 0.2),
        range2: Tuple[float, float] = (-0.2, 0.2),
        steps: int = 5
    ) -> Dict[str, Any]:
        """
        生成双变量敏感度分析表

        Args:
            param1: 第一个参数
            param2: 第二个参数
            range1: 参数1的变化范围
            range2: 参数2的变化范围
            steps: 步数

        Returns:
            敏感度表格数据
        """
        if not hasattr(self.base_inputs, param1) or not hasattr(self.base_inputs, param2):
            raise CalculationError(f"未知参数: {param1} 或 {param2}")

        base_value1 = getattr(self.base_inputs, param1)
        base_value2 = getattr(self.base_inputs, param2)

        # 生成变化值
        values1 = [base_value1 * (1 + r) for r in self._generate_variations(range1, steps)]
        values2 = [base_value2 * (1 + r) for r in self._generate_variations(range2, steps)]

        # 计算表格
        table = []
        for v1 in values1:
            row = []
            for v2 in values2:
                inputs_copy = deepcopy(self.base_inputs)
                setattr(inputs_copy, param1, v1)
                setattr(inputs_copy, param2, v2)

                model = DCFModel(inputs_copy)
                npv = model.calculate().npv
                row.append(round(npv, 2))
            table.append(row)

        return {
            "param1": param1,
            "param2": param2,
            "values1": [round(v, 4) for v in values1],
            "values2": [round(v, 4) for v in values2],
            "table": table
        }

    def _generate_variations(
        self,
        range_tuple: Tuple[float, float],
        steps: int
    ) -> List[float]:
        """生成变化幅度列表"""
        start, end = range_tuple
        step_size = (end - start) / (steps - 1)
        return [start + i * step_size for i in range(steps)]
