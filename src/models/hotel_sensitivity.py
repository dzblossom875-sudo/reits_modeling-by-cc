"""
酒店REITs敏感性分析模块
支持酒店特有参数(ADR/OCC/RevPAR)、瀑布图分解、自定义压力测试
"""

import json
from copy import deepcopy
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

from .hotel_dcf import HotelDCFModel, GrowthSchedule


@dataclass
class SensitivityScenario:
    """敏感性分析情景"""
    name: str
    description: str = ""
    adjustments: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WaterfallStep:
    """瀑布图单步分解"""
    factor: str
    from_value: float
    to_value: float
    valuation_impact: float
    impact_pct: float
    explanation: str = ""


class HotelSensitivityAnalyzer:
    """
    酒店REITs专用敏感性分析器
    支持:
    - 单变量/多变量敏感性
    - 酒店特有参数（折现率、增长率、NOI/CF调整）
    - 瀑布图差异分解
    - 自定义压力测试
    - Tornado图数据
    """

    def __init__(self, extracted_data: Dict[str, Any]):
        self.data = extracted_data
        self.base_model = HotelDCFModel(extracted_data)
        self.base_results = self.base_model.calculate()
        self.base_valuation = self.base_results["total_valuation"]

    def single_variable_sensitivity(self, param_name: str,
                                     values: List[float]) -> Dict[str, Any]:
        """
        单变量敏感性分析

        Args:
            param_name: 参数名 (discount_rate / fixed_growth / noicf_adjustment)
            values: 测试值列表
        """
        results = []
        for val in values:
            model = self._create_adjusted_model(param_name, val)
            model_val = model.calculate()["total_valuation"]
            results.append({
                "value": val,
                "valuation": round(model_val, 2),
                "vs_base": round(model_val - self.base_valuation, 2),
                "vs_base_pct": round((model_val - self.base_valuation) / self.base_valuation * 100, 2),
            })

        return {
            "parameter": param_name,
            "base_value": self._get_base_value(param_name),
            "base_valuation": round(self.base_valuation, 2),
            "results": results,
        }

    def tornado_analysis(self, variation_pct: float = 0.10) -> List[Dict[str, Any]]:
        """
        Tornado图分析 - 各参数±变化对估值影响

        Args:
            variation_pct: 变化幅度（默认±10%）
        """
        tornado = []

        param_configs = [
            ("折现率", "discount_rate", self.base_model.discount_rate),
            ("首年NOI/CF", "noicf_adjustment", 1.0),
        ]

        for display_name, param_key, base_val in param_configs:
            low = base_val * (1 - variation_pct)
            high = base_val * (1 + variation_pct)

            model_low = self._create_adjusted_model(param_key, low)
            model_high = self._create_adjusted_model(param_key, high)

            val_low = model_low.calculate()["total_valuation"]
            val_high = model_high.calculate()["total_valuation"]

            if param_key == "discount_rate":
                low_label = f"{low:.2%}"
                high_label = f"{high:.2%}"
            else:
                low_label = f"{low:.2f}"
                high_label = f"{high:.2f}"

            tornado.append({
                "param_name": display_name,
                "param_key": param_key,
                "base_value": base_val,
                "low_value": low,
                "high_value": high,
                "low_label": low_label,
                "high_label": high_label,
                "val_at_low": round(val_low, 2),
                "val_at_high": round(val_high, 2),
                "val_at_base": round(self.base_valuation, 2),
                "low_impact": round(val_low - self.base_valuation, 2),
                "high_impact": round(val_high - self.base_valuation, 2),
                "total_swing": round(abs(val_high - val_low), 2),
                "total_swing_pct": round(abs(val_high - val_low) / self.base_valuation * 100, 2),
            })

        growth_rates_low = [0.005, 0.01, 0.015, 0.02, 0.0225]
        growth_rates_high = [0.01, 0.02, 0.025, 0.035, 0.03]
        model_low_g = HotelDCFModel(self.data, fixed_growth=0.005)
        model_high_g = HotelDCFModel(self.data, fixed_growth=0.025)
        val_low_g = model_low_g.calculate()["total_valuation"]
        val_high_g = model_high_g.calculate()["total_valuation"]

        tornado.append({
            "param_name": "固定增长率",
            "param_key": "fixed_growth",
            "base_value": "分段增长",
            "low_value": 0.005,
            "high_value": 0.025,
            "low_label": "0.5%",
            "high_label": "2.5%",
            "val_at_low": round(val_low_g, 2),
            "val_at_high": round(val_high_g, 2),
            "val_at_base": round(self.base_valuation, 2),
            "low_impact": round(val_low_g - self.base_valuation, 2),
            "high_impact": round(val_high_g - self.base_valuation, 2),
            "total_swing": round(abs(val_high_g - val_low_g), 2),
            "total_swing_pct": round(abs(val_high_g - val_low_g) / self.base_valuation * 100, 2),
        })

        tornado.sort(key=lambda x: x["total_swing"], reverse=True)
        return tornado

    def waterfall_decomposition(self, scenario: SensitivityScenario) -> Dict[str, Any]:
        """
        瀑布图差异分解
        将总估值差异分解到各个调整因素

        Args:
            scenario: 包含多个参数调整的情景
        """
        steps: List[WaterfallStep] = []
        running_val = self.base_valuation
        adjustments = scenario.adjustments

        param_order = ["discount_rate", "fixed_growth", "noicf_adjustment"]

        for param_key in param_order:
            if param_key not in adjustments:
                continue

            new_val = adjustments[param_key]
            model = self._create_adjusted_model(param_key, new_val)
            new_valuation = model.calculate()["total_valuation"]
            impact = new_valuation - running_val

            base_val = self._get_base_value(param_key)
            steps.append(WaterfallStep(
                factor=self._get_display_name(param_key),
                from_value=base_val if not isinstance(base_val, str) else 0,
                to_value=new_val,
                valuation_impact=round(impact, 2),
                impact_pct=round(impact / self.base_valuation * 100, 2),
                explanation=self._explain_impact(param_key, base_val, new_val, impact),
            ))
            running_val = new_valuation

        final_model = self._create_scenario_model(adjustments)
        final_val = final_model.calculate()["total_valuation"]

        return {
            "scenario_name": scenario.name,
            "description": scenario.description,
            "base_valuation": round(self.base_valuation, 2),
            "final_valuation": round(final_val, 2),
            "total_difference": round(final_val - self.base_valuation, 2),
            "total_difference_pct": round((final_val - self.base_valuation) / self.base_valuation * 100, 2),
            "steps": [
                {
                    "factor": s.factor,
                    "from_value": s.from_value,
                    "to_value": s.to_value,
                    "valuation_impact": s.valuation_impact,
                    "impact_pct": s.impact_pct,
                    "explanation": s.explanation,
                }
                for s in steps
            ],
        }

    def stress_test(self, scenarios: List[SensitivityScenario]) -> Dict[str, Any]:
        """
        压力测试 - 运行多个自定义情景

        Args:
            scenarios: 压力测试情景列表
        """
        results = []
        for scenario in scenarios:
            model = self._create_scenario_model(scenario.adjustments)
            val = model.calculate()["total_valuation"]
            waterfall = self.waterfall_decomposition(scenario)

            results.append({
                "name": scenario.name,
                "description": scenario.description,
                "adjustments": scenario.adjustments,
                "valuation": round(val, 2),
                "vs_base": round(val - self.base_valuation, 2),
                "vs_base_pct": round((val - self.base_valuation) / self.base_valuation * 100, 2),
                "waterfall": waterfall,
            })

        return {
            "base_valuation": round(self.base_valuation, 2),
            "scenarios": results,
        }

    def two_way_sensitivity(self, param1: str, values1: List[float],
                             param2: str, values2: List[float]) -> Dict[str, Any]:
        """
        双变量敏感性分析表

        Args:
            param1: 参数1名称
            values1: 参数1测试值列表
            param2: 参数2名称
            values2: 参数2测试值列表
        """
        table = []
        for v1 in values1:
            row = []
            for v2 in values2:
                model = self._create_scenario_model({param1: v1, param2: v2})
                val = model.calculate()["total_valuation"]
                row.append(round(val, 2))
            table.append(row)

        return {
            "param1": param1,
            "param1_display": self._get_display_name(param1),
            "values1": values1,
            "param2": param2,
            "param2_display": self._get_display_name(param2),
            "values2": values2,
            "table": table,
            "base_valuation": round(self.base_valuation, 2),
        }

    def run_default_hotel_analysis(self) -> Dict[str, Any]:
        """运行酒店REITs默认敏感性分析套件"""
        results = {}

        results["tornado"] = self.tornado_analysis()

        results["discount_rate_sensitivity"] = self.single_variable_sensitivity(
            "discount_rate", [0.05, 0.0525, 0.055, 0.0575, 0.06, 0.0625, 0.065])

        results["growth_sensitivity"] = self.single_variable_sensitivity(
            "fixed_growth", [0.0, 0.005, 0.01, 0.015, 0.02, 0.025, 0.03])

        results["noicf_sensitivity"] = self.single_variable_sensitivity(
            "noicf_adjustment", [0.85, 0.90, 0.95, 1.0, 1.05, 1.10, 1.15])

        results["two_way_dr_growth"] = self.two_way_sensitivity(
            "discount_rate", [0.05, 0.055, 0.0575, 0.06, 0.065],
            "fixed_growth", [0.005, 0.01, 0.015, 0.02, 0.025])

        default_scenarios = [
            SensitivityScenario("乐观情景", "折现率下降+增长率上升",
                                {"discount_rate": 0.055, "fixed_growth": 0.02}),
            SensitivityScenario("悲观情景", "折现率上升+增长率下降",
                                {"discount_rate": 0.065, "fixed_growth": 0.005}),
            SensitivityScenario("压力测试", "极端不利条件",
                                {"discount_rate": 0.07, "noicf_adjustment": 0.85}),
        ]
        results["stress_test"] = self.stress_test(default_scenarios)

        return results

    def _create_adjusted_model(self, param_name: str, value: float) -> HotelDCFModel:
        if param_name == "discount_rate":
            model = HotelDCFModel(deepcopy(self.data))
            model.adjust_discount_rate(value)
            return model
        elif param_name == "fixed_growth":
            return HotelDCFModel(deepcopy(self.data), fixed_growth=value)
        elif param_name == "noicf_adjustment":
            modified = json.loads(json.dumps(self.data))
            fin = modified.get("financial_data", {})
            for proj_key in fin:
                if "noicf_2026" in fin[proj_key]:
                    fin[proj_key]["noicf_2026"] *= value
            return HotelDCFModel(modified)
        else:
            return HotelDCFModel(deepcopy(self.data))

    def _create_scenario_model(self, adjustments: Dict[str, Any]) -> HotelDCFModel:
        modified = json.loads(json.dumps(self.data))

        if "noicf_adjustment" in adjustments:
            fin = modified.get("financial_data", {})
            for proj_key in fin:
                if "noicf_2026" in fin[proj_key]:
                    fin[proj_key]["noicf_2026"] *= adjustments["noicf_adjustment"]

        model = HotelDCFModel(modified,
                               fixed_growth=adjustments.get("fixed_growth"))
        if "discount_rate" in adjustments:
            model.adjust_discount_rate(adjustments["discount_rate"])

        return model

    def _get_base_value(self, param_name: str):
        if param_name == "discount_rate":
            return self.base_model.discount_rate
        elif param_name == "fixed_growth":
            return "分段增长"
        elif param_name == "noicf_adjustment":
            return 1.0
        return None

    def _get_display_name(self, param_name: str) -> str:
        display_names = {
            "discount_rate": "折现率",
            "fixed_growth": "增长率",
            "noicf_adjustment": "NOI/CF调整系数",
        }
        return display_names.get(param_name, param_name)

    def _explain_impact(self, param_key: str, from_val, to_val, impact: float) -> str:
        direction = "增加" if impact > 0 else "减少"
        abs_impact = abs(impact)

        if param_key == "discount_rate":
            change = "提高" if to_val > (from_val if isinstance(from_val, (int, float)) else 0.0575) else "降低"
            return (f"折现率{change}至{to_val:.2%}，"
                    f"导致估值{direction}{abs_impact:,.0f}万元。"
                    f"折现率每变化25bp，估值变化约3-4%。")
        elif param_key == "fixed_growth":
            return (f"增长率调整为固定{to_val:.1%}，"
                    f"导致估值{direction}{abs_impact:,.0f}万元。"
                    f"增长率通过影响未来各年NOI而影响总估值。")
        elif param_key == "noicf_adjustment":
            return (f"首年NOI/CF调整系数{to_val:.0%}，"
                    f"导致估值{direction}{abs_impact:,.0f}万元。"
                    f"NOI/CF的变化会线性传导至所有预测年份。")
        return f"参数调整导致估值{direction}{abs_impact:,.0f}万元"
