"""
JSON导出器
将估值结果导出为JSON格式
"""

import json
from typing import Dict, Any, List
from pathlib import Path

from ..core.types import ValuationResult, ScenarioResult
from ..core.exceptions import ExportError


class JSONExporter:
    """JSON导出器"""

    def __init__(self, indent: int = 2):
        self.indent = indent

    def export_valuation(
        self,
        valuation: ValuationResult,
        output_path: str
    ) -> str:
        """
        导出单个估值结果为JSON

        Args:
            valuation: 估值结果
            output_path: 输出文件路径

        Returns:
            输出文件路径
        """
        data = valuation.to_dict()

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=self.indent)

        return output_path

    def export_scenarios(
        self,
        scenarios: List[ScenarioResult],
        output_path: str
    ) -> str:
        """
        导出多情景对比结果为JSON

        Args:
            scenarios: 情景结果列表
            output_path: 输出文件路径

        Returns:
            输出文件路径
        """
        data = {
            "scenarios": [s.to_dict() for s in scenarios],
            "comparison_summary": self._generate_comparison_summary(scenarios)
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=self.indent)

        return output_path

    def export_complete_report(
        self,
        base_valuation: ValuationResult,
        scenarios: List[ScenarioResult],
        sensitivity_data: Dict[str, Any],
        output_path: str
    ) -> str:
        """
        导出完整报告（含估值、情景、敏感度）

        Args:
            base_valuation: 基准估值
            scenarios: 情景列表
            sensitivity_data: 敏感度数据
            output_path: 输出文件路径

        Returns:
            输出文件路径
        """
        data = {
            "report_metadata": {
                "type": "REITs Valuation Report",
                "version": "1.0",
                "generated_at": base_valuation.created_at.isoformat(),
            },
            "base_valuation": base_valuation.to_dict(),
            "scenarios": [s.to_dict() for s in scenarios],
            "sensitivity_analysis": sensitivity_data,
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=self.indent)

        return output_path

    def _generate_comparison_summary(
        self,
        scenarios: List[ScenarioResult]
    ) -> Dict[str, Any]:
        """生成情景对比摘要"""
        if not scenarios:
            return {}

        base_scenario = scenarios[0] if scenarios else None

        summary = {
            "scenario_count": len(scenarios),
            "npv_range": {
                "min": min(s.valuation.npv for s in scenarios),
                "max": max(s.valuation.npv for s in scenarios),
            },
            "base_scenario": base_scenario.scenario_name if base_scenario else None,
        }

        # 计算NPV变化范围
        if len(scenarios) > 1 and base_scenario:
            npv_values = [s.valuation.npv for s in scenarios[1:]]
            if npv_values:
                summary["npv_range"]["vs_base_min"] = min(npv_values)
                summary["npv_range"]["vs_base_max"] = max(npv_values)

        return summary

    def to_string(self, valuation: ValuationResult) -> str:
        """
        将估值结果转换为JSON字符串

        Args:
            valuation: 估值结果

        Returns:
            JSON字符串
        """
        return json.dumps(valuation.to_dict(), ensure_ascii=False, indent=self.indent)
