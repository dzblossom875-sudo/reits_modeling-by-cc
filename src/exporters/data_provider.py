"""
结构化数据提供器（方式B）
提供完整的数据和公式指引，供用户自行整理到Excel
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from ..core.types import ValuationResult, ScenarioResult, SensitivityResult
from ..core.config import FORECAST_YEARS, EXCEL_TEMPLATE_CONFIG


@dataclass
class ExcelFormula:
    """Excel公式定义"""
    cell: str                          # 单元格位置
    formula: str                       # 公式内容
    description: str                   # 公式说明


@dataclass
class DataSheet:
    """数据Sheet结构"""
    name: str
    data: Dict[str, Any]
    formulas: List[ExcelFormula] = field(default_factory=list)


class DataProvider:
    """
    结构化数据提供器
    为方式B提供完整的数据结构和Excel公式指引
    """

    def __init__(self):
        pass

    def get_structured_data(self, valuation: ValuationResult) -> Dict[str, Any]:
        """
        获取估值的完整结构化数据

        Args:
            valuation: 估值结果

        Returns:
            包含所有sheet数据的字典
        """
        return {
            "dashboard": self._build_dashboard(valuation),
            "assumptions": self._build_assumptions(valuation),
            "dcf": self._build_dcf(valuation),
            "data": self._build_data_sheet(valuation),
        }

    def get_multi_scenario_data(
        self,
        scenarios: List[ScenarioResult]
    ) -> Dict[str, Any]:
        """
        获取多情景对比的结构化数据

        Args:
            scenarios: 情景结果列表

        Returns:
            包含情景对比数据的字典
        """
        return {
            "scenarios": self._build_scenarios(scenarios),
            "sensitivity": {},  # 由SensitivityAnalyzer生成
        }

    def _build_dashboard(self, valuation: ValuationResult) -> DataSheet:
        """构建Dashboard数据"""
        data = {
            "project_name": valuation.project_info.name,
            "asset_type": valuation.asset_type.value,
            "valuation_date": valuation.created_at.strftime("%Y-%m-%d"),

            # 关键指标
            "key_metrics": {
                "dcf_valuation": {
                    "value": round(valuation.dcf_value, 2),
                    "unit": "万元",
                    "description": "DCF估值"
                },
                "npv": {
                    "value": round(valuation.npv, 2),
                    "unit": "万元",
                    "description": "净现值(NPV)"
                },
                "irr": {
                    "value": round(valuation.irr * 100, 2) if valuation.irr else None,
                    "unit": "%",
                    "description": "内部收益率(IRR)"
                },
                "cap_rate": {
                    "value": round(valuation.cap_rate * 100, 2) if valuation.cap_rate else None,
                    "unit": "%",
                    "description": "资本化率估值"
                },
            },

            # 项目信息
            "project_info": {
                "total_area": valuation.project_info.total_area,
                "leasable_area": valuation.project_info.leasable_area,
                "remaining_years": valuation.project_info.remaining_years,
            },

            # 现金流汇总
            "cashflow_summary": {
                "total_noi": sum(cf.calculate_noi() for cf in valuation.cash_flows),
                "avg_annual_noi": sum(cf.calculate_noi() for cf in valuation.cash_flows) / len(valuation.cash_flows) if valuation.cash_flows else 0,
            }
        }

        formulas = [
            ExcelFormula("C5", "=DCF!F15", "NPV计算结果"),
            ExcelFormula("C6", "=IRR(DCF!F3:F13)", "IRR计算"),
        ]

        return DataSheet("Dashboard", data, formulas)

    def _build_assumptions(self, valuation: ValuationResult) -> DataSheet:
        """构建Assumptions数据"""
        assumptions_data = []

        for key, value in valuation.assumptions.items():
            assumptions_data.append({
                "param_name": key,
                "value": value,
                "category": self._categorize_param(key)
            })

        data = {
            "assumptions": assumptions_data,
            "forecast_years": FORECAST_YEARS,
        }

        return DataSheet("Assumptions", data)

    def _build_dcf(self, valuation: ValuationResult) -> DataSheet:
        """构建DCF计算表数据"""
        cashflow_data = []

        for cf in valuation.cash_flows:
            cashflow_data.append({
                "year": cf.year,
                "rental_income": cf.rental_income,
                "other_income": cf.other_income,
                "total_income": cf.total_income,
                "operating_expense": cf.operating_expense,
                "management_fee": cf.management_fee,
                "noi": cf.calculate_noi(),
                "discount_factor": f"=1/(1+Assumptions!$C$5)^{cf.year}",
                "present_value": f"=H{cf.year+2}*I{cf.year+2}",  # NOI * 折现因子
            })

        data = {
            "cashflows": cashflow_data,
            "terminal_value": self._calculate_terminal_value(valuation),
            "npv_formula": "=SUM(J3:J12)+TerminalValue/(1+Assumptions!$C$5)^10",
        }

        formulas = [
            ExcelFormula(f"H{row}", f"=E{row}-F{row}-G{row}", "NOI计算")
            for row in range(3, 3 + len(valuation.cash_flows))
        ]

        return DataSheet("DCF", data, formulas)

    def _build_data_sheet(self, valuation: ValuationResult) -> DataSheet:
        """构建数据来源记录表"""
        data = {
            "extraction_timestamp": valuation.created_at.isoformat(),
            "calculation_notes": valuation.calculation_notes,
            "raw_params": valuation.assumptions,
        }

        return DataSheet("Data", data)

    def _build_scenarios(self, scenarios: List[ScenarioResult]) -> DataSheet:
        """构建情景对比数据"""
        scenario_data = []

        for scenario in scenarios:
            scenario_data.append({
                "name": scenario.scenario_name,
                "npv": round(scenario.valuation.npv, 2),
                "irr": round(scenario.valuation.irr * 100, 2) if scenario.valuation.irr else None,
                "vs_base": round(scenario.vs_base_percent * 100, 2) if scenario.vs_base_percent else 0,
            })

        data = {
            "scenarios": scenario_data,
            "comparison_chart_data": scenario_data,
        }

        return DataSheet("Scenarios", data)

    def _categorize_param(self, param_name: str) -> str:
        """参数分类"""
        categories = {
            "forecast_years": "基本假设",
            "discount_rate": "资本端",
            "rent_growth_rate": "收入端",
            "occupancy_rate": "收入端",
            "operating_expense_ratio": "成本端",
            "capex": "资本端",
            "asset_type": "项目信息",
        }
        return categories.get(param_name, "其他")

    def _calculate_terminal_value(self, valuation: ValuationResult) -> Dict[str, Any]:
        """计算终值相关数据"""
        if not valuation.cash_flows:
            return {}

        final_year_noi = valuation.cash_flows[-1].calculate_noi()

        return {
            "final_year_noi": final_year_noi,
            "terminal_growth": 0.02,
            "discount_rate": 0.075,
            "terminal_value_formula": f"={final_year_noi}*(1+0.02)/(0.075-0.02)",
        }

    def get_formula_guide(self) -> str:
        """
        获取Excel公式指引文档

        Returns:
            Markdown格式的公式指引
        """
        guide = """
# REITs估值模型 - Excel公式指引

## Dashboard Sheet

| 单元格 | 公式 | 说明 |
|--------|------|------|
| C5 | `=DCF!J15` | NPV计算结果 |
| C6 | `=IRR(DCF!F3:F13)` | IRR计算 |
| C7 | `=Dashboard!C5/ProjectInfo!C3` | 每平米估值 |

## DCF Sheet

### 现金流计算（第3-12行）

| 列 | 公式示例 | 说明 |
|----|---------|------|
| E | `=B3*12*Assumptions!$C$3/10000` | 年收入（万元） |
| H | `=E3-F3-G3` | NOI计算 |
| I | `=1/(1+Assumptions!$C$5)^B3` | 折现因子 |
| J | `=H3*I3` | 现值 |

### 终值计算（第13行）

```excel
=H12*(1+Assumptions!$C$8)/(Assumptions!$C$5-Assumptions!$C$8)
```

### NPV总计

```excel
=SUM(J3:J12)+J13/(1+Assumptions!$C$5)^10
```

## Assumptions Sheet

| 参数 | 单元格 | 说明 |
|------|--------|------|
| 总面积 | C3 | 可租赁面积（㎡） |
| 当前租金 | C4 | 元/㎡/月 |
| 折现率 | C5 | WACC/要求回报率 |
| 租金增长率 | C6 | 年增长率 |
| 出租率 | C7 | 目标出租率 |
| 永续增长率 | C8 | Gordon增长模型 |

## 注意事项

1. 所有金额单位统一为"万元"
2. 比率使用小数格式（如0.075表示7.5%）
3. 公式中引用使用绝对引用（$）确保复制时不变
4. 敏感度分析使用数据表功能（What-If Analysis）
"""
        return guide

    def export_to_json(self, valuation: ValuationResult, filepath: str) -> None:
        """
        导出为JSON文件

        Args:
            valuation: 估值结果
            filepath: 输出文件路径
        """
        import json

        data = self.get_structured_data(valuation)

        # 转换为可序列化的格式
        serializable_data = {}
        for sheet_name, sheet in data.items():
            if isinstance(sheet, DataSheet):
                serializable_data[sheet_name] = sheet.data
            else:
                serializable_data[sheet_name] = sheet

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(serializable_data, f, ensure_ascii=False, indent=2)
