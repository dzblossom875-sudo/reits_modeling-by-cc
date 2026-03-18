#!/usr/bin/env python3
"""
REITs估值建模Agent - 主程序入口

该程序提供完整的REITs项目估值建模功能，包括：
1. 从招募说明书/交易文件中提取关键参数
2. 构建DCF估值模型
3. 支持多情景分析和压力测试
4. 生成投行风格的Excel模型和可视化报告

Usage:
    python main.py --file path/to/prospectus.pdf --asset-type industrial
    python main.py --interactive
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import AssetType, FORECAST_YEARS
from src.core.types import ParsedDocument, ExtractedParams, ValuationResult
from src.parsers import DocumentParser
from src.parsers.extractor import ParameterExtractor
from src.models.dcf_model import DCFModel, DCFInputs
from src.models.scenarios import ScenarioManager
from src.models.sensitivity import SensitivityAnalyzer
from src.exporters import ExcelGenerator, DataProvider, JSONExporter, Visualizer
from src.validators import ParameterValidator, RiskAnalyzer


def print_header(text: str):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_section(text: str):
    """打印小节标题"""
    print(f"\n>>> {text}")


def print_table(data: List[Dict[str, Any]], headers: List[str] = None):
    """打印表格"""
    if not data:
        print("  (无数据)")
        return

    if headers is None:
        headers = list(data[0].keys())

    # 计算列宽
    col_widths = {}
    for h in headers:
        col_widths[h] = max(len(str(h)), max(len(str(d.get(h, ""))) for d in data))

    # 打印表头
    header_line = "  | " + " | ".join(f"{h:{col_widths[h]}}" for h in headers) + " |"
    print("\n" + header_line)
    print("  " + "-" * (len(header_line) - 2))

    # 打印数据
    for row in data:
        row_str = "  | " + " | ".join(f"{str(row.get(h, '')):{col_widths[h]}}" for h in headers) + " |"
        print(row_str)
    print()


class REITsModelingAgent:
    """
    REITs估值建模Agent主类

    提供完整的估值建模流程：
    1. 文档解析
    2. 参数提取
    3. 模型搭建
    4. 情景分析
    5. 报告生成
    """

    def __init__(self):
        self.document_parser = DocumentParser()
        self.param_validator = ParameterValidator()
        self.risk_analyzer = RiskAnalyzer()

        # 存储中间结果
        self.parsed_doc: Optional[ParsedDocument] = None
        self.extracted_params: Optional[ExtractedParams] = None
        self.base_valuation: Optional[ValuationResult] = None
        self.scenarios: List[Any] = []

    def parse_document(self, file_path: str) -> ParsedDocument:
        """
        解析文档

        Args:
            file_path: 文件路径

        Returns:
            解析后的文档对象
        """
        print_section(f"正在解析文档: {file_path}")

        self.parsed_doc = self.document_parser.parse(file_path)

        print(f"  [OK] 文件类型: {self.parsed_doc.file_type}")
        print(f"  [OK] 文本长度: {len(self.parsed_doc.text)} 字符")
        print(f"  [OK] 提取表格: {len(self.parsed_doc.tables)} 个")

        return self.parsed_doc

    def extract_parameters(self, asset_type: Optional[AssetType] = None) -> ExtractedParams:
        """
        从文档中提取估值参数

        Args:
            asset_type: 资产类型（可选，用于指导提取）

        Returns:
            提取的参数
        """
        print_section("正在提取估值参数...")

        extractor = ParameterExtractor(asset_type=asset_type)
        self.extracted_params = extractor.extract(self.parsed_doc)

        # 显示提取结果
        if self.extracted_params.extracted:
            print(f"\n  成功提取 {len(self.extracted_params.extracted)} 个参数:")
            extracted_data = [
                {
                    "参数": p.name,
                    "数值": p.value,
                    "来源": p.source[:30] + "..." if len(p.source) > 30 else p.source
                }
                for p in self.extracted_params.extracted.values()
            ]
            print_table(extracted_data, ["参数", "数值", "来源"])

        # 显示缺失参数
        if self.extracted_params.missing:
            print(f"\n  [WARN] 缺失 {len(self.extracted_params.missing)} 个参数:")
            for p in self.extracted_params.missing:
                print(f"    - {p}")

        # 验证提取的参数
        issues = self.param_validator.validate_extracted_params(self.extracted_params)
        if issues:
            print(f"\n  [WARN] 发现 {len(issues)} 个验证问题")

        return self.extracted_params

    def confirm_parameters(self) -> DCFInputs:
        """
        确认参数并构建DCF输入
        在实际应用中，这里应该与用户交互确认

        Returns:
            DCF输入参数
        """
        print_section("确认参数并构建模型")

        # 使用提取的参数构建DCF输入
        inputs = DCFInputs.from_extracted_params(self.extracted_params)

        # 如果有缺失参数，使用默认值
        if self.extracted_params.missing:
            print(f"\n  为 {len(self.extracted_params.missing)} 个缺失参数使用默认值:")
            for param_name in self.extracted_params.missing:
                default_value = getattr(inputs, param_name, None)
                if default_value is not None:
                    print(f"    - {param_name}: {default_value}")

        print(f"\n  [OK] 资产类型: {inputs.asset_type.value}")
        print(f"  [OK] 预测年限: {inputs.remaining_years} 年")

        return inputs

    def build_model(self, inputs: DCFInputs) -> ValuationResult:
        """
        构建DCF模型并计算

        Args:
            inputs: DCF输入参数

        Returns:
            估值结果
        """
        print_section("构建DCF模型并计算")

        # 验证输入
        issues = self.param_validator.validate_inputs(inputs)
        if issues:
            print(f"\n  [WARN] 参数验证发现 {len(issues)} 个问题:")
            for issue in issues[:5]:  # 只显示前5个
                print(f"    [{issue.severity}] {issue.param_name}: {issue.message}")

        # 创建模型并计算
        model = DCFModel(inputs)
        self.base_valuation = model.calculate("Base Case")

        # 显示结果
        print(f"\n  [RESULT] 估值结果:")
        print(f"    - DCF估值: {self.base_valuation.dcf_value:,.2f} 万元")
        if self.base_valuation.irr:
            print(f"    - IRR: {self.base_valuation.irr:.2%}")
        if self.base_valuation.cap_rate:
            print(f"    - 资本化率估值: {self.base_valuation.cap_rate:,.2f} 万元")

        # 现金流汇总
        if self.base_valuation.cash_flows:
            total_noi = sum(cf.calculate_noi() for cf in self.base_valuation.cash_flows)
            print(f"    - 10年总NOI: {total_noi:,.2f} 万元")

        return self.base_valuation

    def analyze_scenarios(self, inputs: DCFInputs) -> List[Any]:
        """
        多情景分析

        Args:
            inputs: 基准DCF输入

        Returns:
            情景结果列表
        """
        print_section("多情景分析")

        # 创建情景管理器并添加常见情景
        manager = ScenarioManager(inputs)

        # 添加预设情景
        manager.add_scenario(
            name="Optimistic",
            description="乐观情景",
            adjustments={
                "rent_growth_rate": inputs.rent_growth_rate * 1.5,
                "occupancy_rate": min(inputs.occupancy_rate * 1.05, 0.98),
                "discount_rate": inputs.discount_rate * 0.95
            }
        )

        manager.add_scenario(
            name="Pessimistic",
            description="悲观情景",
            adjustments={
                "rent_growth_rate": inputs.rent_growth_rate * 0.5,
                "occupancy_rate": inputs.occupancy_rate * 0.90,
                "discount_rate": inputs.discount_rate * 1.1
            }
        )

        manager.add_scenario(
            name="Stress Test",
            description="压力测试",
            adjustments={
                "rent_growth_rate": 0.005,
                "occupancy_rate": max(inputs.occupancy_rate * 0.80, 0.70),
                "discount_rate": inputs.discount_rate * 1.2,
                "operating_expense_ratio": inputs.operating_expense_ratio * 1.15
            }
        )

        # 计算所有情景
        self.scenarios = manager.calculate_all()

        # 显示结果
        print(f"\n  [RESULT] 情景对比:")
        scenario_data = [
            {
                "情景": s.scenario_name,
                "NPV(万元)": f"{s.valuation.npv:,.0f}",
                "vs基准": f"{s.vs_base_percent * 100:+.1f}%" if s.vs_base_percent else "-"
            }
            for s in self.scenarios
        ]
        print_table(scenario_data, ["情景", "NPV(万元)", "vs基准"])

        return self.scenarios

    def analyze_risks(self) -> List[Any]:
        """
        风险分析

        Returns:
            风险项列表
        """
        print_section("风险分析")

        risks = self.risk_analyzer.analyze(self.base_valuation)

        # 按等级统计
        high_risks = [r for r in risks if r.level == "high"]
        medium_risks = [r for r in risks if r.level == "medium"]
        low_risks = [r for r in risks if r.level == "low"]

        print(f"\n  [RISK] 风险统计: 高{len(high_risks)} / 中{len(medium_risks)} / 低{len(low_risks)}")

        if high_risks:
            print(f"\n  [HIGH RISK] 高风险项:")
            for risk in high_risks:
                print(f"    - {risk.category}: {risk.description}")

        if medium_risks:
            print(f"\n  [MED RISK] 中风险项:")
            for risk in medium_risks[:3]:  # 只显示前3个
                print(f"    - {risk.category}: {risk.description}")

        return risks

    def generate_report(
        self,
        output_dir: str = "./output",
        export_excel: bool = True,
        export_json: bool = True,
        generate_charts: bool = True
    ) -> Dict[str, str]:
        """
        生成完整报告

        Args:
            output_dir: 输出目录
            export_excel: 是否导出Excel
            export_json: 是否导出JSON
            generate_charts: 是否生成图表

        Returns:
            生成的文件路径字典
        """
        print_section("生成报告")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        generated_files = {}

        # 1. 导出Excel
        if export_excel:
            try:
                excel_gen = ExcelGenerator()
                excel_path = excel_gen.generate(
                    self.base_valuation,
                    self.scenarios,
                    str(output_path / "reit_valuation_model.xlsx")
                )
                generated_files['excel'] = excel_path
                print(f"  [OK] Excel模型: {excel_path}")
            except Exception as e:
                print(f"  [FAIL] Excel导出失败: {e}")

        # 2. 导出JSON
        if export_json:
            try:
                json_exporter = JSONExporter()
                json_path = str(output_path / "valuation_report.json")
                json_exporter.export_complete_report(
                    self.base_valuation,
                    self.scenarios,
                    {},
                    json_path
                )
                generated_files['json'] = json_path
                print(f"  [OK] JSON报告: {json_path}")
            except Exception as e:
                print(f"  [FAIL] JSON导出失败: {e}")

        # 3. 生成图表
        if generate_charts:
            try:
                visualizer = Visualizer(str(output_path))
                chart_paths = visualizer.generate_all_charts(
                    self.base_valuation,
                    self.scenarios
                )
                generated_files.update(chart_paths)
                for name, path in chart_paths.items():
                    print(f"  [OK] 图表 ({name}): {path}")
            except Exception as e:
                print(f"  [FAIL] 图表生成失败: {e}")

        # 4. 生成结构化数据（方式B）
        try:
            data_provider = DataProvider()
            structured_data = data_provider.get_structured_data(self.base_valuation)
            generated_files['structured_data'] = str(output_path / "structured_data.json")
            print(f"  [OK] 结构化数据已准备（可用于手动整理Excel）")
        except Exception as e:
            print(f"  [FAIL] 结构化数据生成失败: {e}")

        return generated_files

    def run_complete_workflow(
        self,
        file_path: str,
        asset_type: Optional[AssetType] = None,
        output_dir: str = "./output"
    ) -> Dict[str, Any]:
        """
        运行完整估值流程

        Args:
            file_path: 招募说明书文件路径
            asset_type: 资产类型
            output_dir: 输出目录

        Returns:
            完整结果字典
        """
        print_header("REITs估值建模Agent")

        # 步骤1: 解析文档
        self.parse_document(file_path)

        # 步骤2: 提取参数
        self.extract_parameters(asset_type)

        # 步骤3: 确认参数（实际应用中与用户交互）
        inputs = self.confirm_parameters()

        # 步骤4: 构建模型
        self.build_model(inputs)

        # 步骤5: 情景分析
        self.analyze_scenarios(inputs)

        # 步骤6: 风险分析
        self.analyze_risks()

        # 步骤7: 生成报告
        files = self.generate_report(output_dir)

        print_header("估值完成")
        print(f"\n  [DIR] 输出目录: {output_dir}")
        print(f"  [RESULT] 基准估值: {self.base_valuation.dcf_value:,.2f} 万元")

        return {
            "valuation": self.base_valuation,
            "scenarios": self.scenarios,
            "files": files
        }


def interactive_mode():
    """交互式模式"""
    print_header("REITs估值建模Agent - 交互模式")

    agent = REITsModelingAgent()

    # 获取文件路径
    file_path = input("\n请输入招募说明书文件路径: ").strip()

    if not Path(file_path).exists():
        print(f"错误: 文件不存在: {file_path}")
        return

    # 获取资产类型
    print("\n选择资产类型:")
    print("  1. 产业园 (industrial)")
    print("  2. 物流仓储 (logistics)")
    print("  3. 保障性租赁住房 (housing)")
    print("  4. 基础设施 (infrastructure)")
    print("  5. 酒店 (hotel)")

    type_choice = input("请输入选项 (1-5) 或直接回车自动识别: ").strip()

    asset_type_map = {
        "1": AssetType.INDUSTRIAL,
        "2": AssetType.LOGISTICS,
        "3": AssetType.HOUSING,
        "4": AssetType.INFRASTRUCTURE,
        "5": AssetType.HOTEL,
    }

    asset_type = asset_type_map.get(type_choice)

    # 运行完整流程
    result = agent.run_complete_workflow(file_path, asset_type)

    print("\n✅ 估值流程完成！")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="REITs估值建模Agent - 从招募说明书到估值模型",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py -f 招募说明书.pdf -t industrial
  python main.py -i  # 交互模式
        """
    )

    parser.add_argument(
        "-f", "--file",
        help="招募说明书文件路径 (PDF/Word/Excel)"
    )

    parser.add_argument(
        "-t", "--asset-type",
        choices=["industrial", "logistics", "housing", "infrastructure", "hotel"],
        help="资产类型"
    )

    parser.add_argument(
        "-o", "--output",
        default="./output",
        help="输出目录 (默认: ./output)"
    )

    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="交互模式"
    )

    args = parser.parse_args()

    if args.interactive or (not args.file):
        interactive_mode()
    else:
        # 命令行模式
        asset_type = None
        if args.asset_type:
            asset_type = AssetType(args.asset_type)

        agent = REITsModelingAgent()
        agent.run_complete_workflow(args.file, asset_type, args.output)


if __name__ == "__main__":
    main()
