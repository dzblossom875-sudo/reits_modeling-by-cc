#!/usr/bin/env python3
"""
REITs估值建模Agent - 主程序入口

统一Pipeline: PDF提取 -> 历史/预测比对 -> DCF建模 -> 敏感性分析

Usage:
    python main.py --file path/to/prospectus.pdf --asset-type hotel
    python main.py --data data/huazhu/extracted_params.json --pipeline
    python main.py --project huazhu --pipeline
    python main.py --interactive
    python main.py --project huarun_chengdu --interactive
"""

import argparse
import sys
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import AssetType, FORECAST_YEARS
from src.core.types import ParsedDocument, ExtractedParams, ValuationResult
from src.core.project_config import get_config, ProjectConfigManager
from src.parsers import DocumentParser
from src.parsers.extractor import ParameterExtractor
from src.models.dcf_model import DCFModel, DCFInputs
from src.models.hotel_dcf import HotelDCFModel, GrowthSchedule
from src.models.scenarios import ScenarioManager
from src.models.sensitivity import SensitivityAnalyzer
from src.exporters import ExcelGenerator, DataProvider, JSONExporter, Visualizer
from src.validators import ParameterValidator, RiskAnalyzer
from src.pipeline import HotelREITsPipeline


def print_header(text: str):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_section(text: str):
    print(f"\n>>> {text}")


class REITsModelingAgent:
    """
    REITs估值建模Agent主类
    支持两种模式：
    1. 通用模式：从PDF提取 -> 通用DCF模型
    2. Pipeline模式：酒店REITs 4步统一流程
    """

    def __init__(self):
        self.document_parser = DocumentParser()
        self.param_validator = ParameterValidator()
        self.risk_analyzer = RiskAnalyzer()

        self.parsed_doc: Optional[ParsedDocument] = None
        self.extracted_params: Optional[ExtractedParams] = None
        self.base_valuation: Optional[ValuationResult] = None
        self.scenarios: List[Any] = []

    def parse_document(self, file_path: str) -> ParsedDocument:
        print_section(f"正在解析文档: {file_path}")
        self.parsed_doc = self.document_parser.parse(file_path)
        print(f"  [OK] 文件类型: {self.parsed_doc.file_type}")
        print(f"  [OK] 文本长度: {len(self.parsed_doc.text)} 字符")
        print(f"  [OK] 提取表格: {len(self.parsed_doc.tables)} 个")
        return self.parsed_doc

    def extract_parameters(self, asset_type: Optional[AssetType] = None) -> ExtractedParams:
        print_section("正在提取估值参数...")
        extractor = ParameterExtractor(asset_type=asset_type)
        self.extracted_params = extractor.extract(self.parsed_doc)

        if self.extracted_params.extracted:
            print(f"\n  成功提取 {len(self.extracted_params.extracted)} 个参数")

        if self.extracted_params.missing:
            print(f"\n  [WARN] 缺失 {len(self.extracted_params.missing)} 个参数:")
            for p in self.extracted_params.missing:
                print(f"    - {p}")

        issues = self.param_validator.validate_extracted_params(self.extracted_params)
        if issues:
            print(f"\n  [WARN] 发现 {len(issues)} 个验证问题")

        return self.extracted_params

    def confirm_parameters(self) -> DCFInputs:
        print_section("确认参数并构建模型")
        inputs = DCFInputs.from_extracted_params(self.extracted_params)

        if self.extracted_params.missing:
            print(f"\n  为 {len(self.extracted_params.missing)} 个缺失参数使用默认值")

        print(f"\n  [OK] 资产类型: {inputs.asset_type.value}")
        print(f"  [OK] 预测年限: {inputs.remaining_years} 年")
        return inputs

    def build_model(self, inputs: DCFInputs) -> ValuationResult:
        print_section("构建DCF模型并计算")
        issues = self.param_validator.validate_inputs(inputs)
        if issues:
            print(f"\n  [WARN] 参数验证发现 {len(issues)} 个问题:")
            for issue in issues[:5]:
                print(f"    [{issue.severity}] {issue.param_name}: {issue.message}")

        model = DCFModel(inputs)
        self.base_valuation = model.calculate("Base Case")

        print(f"\n  [RESULT] 估值结果:")
        print(f"    - DCF估值: {self.base_valuation.dcf_value:,.2f} 万元")
        if self.base_valuation.irr:
            print(f"    - IRR: {self.base_valuation.irr:.2%}")
        return self.base_valuation

    def analyze_scenarios(self, inputs: DCFInputs) -> List[Any]:
        print_section("多情景分析")
        manager = ScenarioManager(inputs)

        manager.add_scenario(
            name="Optimistic", description="乐观情景",
            adjustments={
                "rent_growth_rate": inputs.rent_growth_rate * 1.5,
                "occupancy_rate": min(inputs.occupancy_rate * 1.05, 0.98),
                "discount_rate": inputs.discount_rate * 0.95,
            })
        manager.add_scenario(
            name="Pessimistic", description="悲观情景",
            adjustments={
                "rent_growth_rate": inputs.rent_growth_rate * 0.5,
                "occupancy_rate": inputs.occupancy_rate * 0.90,
                "discount_rate": inputs.discount_rate * 1.1,
            })
        manager.add_scenario(
            name="Stress Test", description="压力测试",
            adjustments={
                "rent_growth_rate": 0.005,
                "occupancy_rate": max(inputs.occupancy_rate * 0.80, 0.70),
                "discount_rate": inputs.discount_rate * 1.2,
                "operating_expense_ratio": inputs.operating_expense_ratio * 1.15,
            })

        self.scenarios = manager.calculate_all()
        return self.scenarios

    def analyze_risks(self) -> List[Any]:
        print_section("风险分析")
        risks = self.risk_analyzer.analyze(self.base_valuation)
        high_risks = [r for r in risks if r.level == "high"]
        print(f"\n  [RISK] 风险统计: 高{len(high_risks)} / 中{len([r for r in risks if r.level == 'medium'])} / 低{len([r for r in risks if r.level == 'low'])}")
        return risks

    def generate_report(self, output_dir: str = "./output",
                        export_excel: bool = True,
                        export_json: bool = True,
                        generate_charts: bool = True) -> Dict[str, str]:
        print_section("生成报告")
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        generated_files = {}

        if export_excel:
            try:
                excel_gen = ExcelGenerator()
                excel_path = excel_gen.generate(
                    self.base_valuation, self.scenarios,
                    str(output_path / "reit_valuation_model.xlsx"))
                generated_files['excel'] = excel_path
                print(f"  [OK] Excel模型: {excel_path}")
            except Exception as e:
                print(f"  [FAIL] Excel导出失败: {e}")

        if export_json:
            try:
                json_exporter = JSONExporter()
                json_path = str(output_path / "valuation_report.json")
                json_exporter.export_complete_report(
                    self.base_valuation, self.scenarios, {}, json_path)
                generated_files['json'] = json_path
                print(f"  [OK] JSON报告: {json_path}")
            except Exception as e:
                print(f"  [FAIL] JSON导出失败: {e}")

        if generate_charts:
            try:
                visualizer = Visualizer(str(output_path))
                chart_paths = visualizer.generate_all_charts(
                    self.base_valuation, self.scenarios)
                generated_files.update(chart_paths)
            except Exception as e:
                print(f"  [FAIL] 图表生成失败: {e}")

        try:
            data_provider = DataProvider()
            data_provider.get_structured_data(self.base_valuation)
            generated_files['structured_data'] = str(output_path / "structured_data.json")
        except Exception as e:
            print(f"  [FAIL] 结构化数据生成失败: {e}")

        return generated_files

    def run_complete_workflow(self, file_path: str,
                             asset_type: Optional[AssetType] = None,
                             output_dir: str = "./output") -> Dict[str, Any]:
        """通用REITs完整估值流程"""
        print_header("REITs估值建模Agent")

        self.parse_document(file_path)
        self.extract_parameters(asset_type)
        inputs = self.confirm_parameters()
        self.build_model(inputs)
        self.analyze_scenarios(inputs)
        self.analyze_risks()
        files = self.generate_report(output_dir)

        print_header("估值完成")
        print(f"\n  [RESULT] 基准估值: {self.base_valuation.dcf_value:,.2f} 万元")

        return {
            "valuation": self.base_valuation,
            "scenarios": self.scenarios,
            "files": files,
        }

    @staticmethod
    def run_hotel_pipeline(data_path: str = None,
                           detailed_path: Optional[str] = None,
                           output_dir: str = None,
                           custom_scenarios: Optional[List[Dict]] = None,
                           project_config: Optional[ProjectConfigManager] = None) -> Dict[str, Any]:
        """
        酒店REITs 4步统一Pipeline
        Step 1: 参数提取
        Step 2: 历史vs预测逐项比对(5%阈值)
        Step 3: DCF建模与估值比对
        Step 4: 敏感性分析

        Args:
            data_path: 参数JSON路径（如不提供，从project_config获取）
            detailed_path: 详细参数JSON路径
            output_dir: 输出目录（如不提供，从project_config获取）
            custom_scenarios: 自定义情景
            project_config: 项目配置管理器（推荐）
        """
        print_header("酒店REITs 4步统一Pipeline")

        # 使用项目配置管理器获取路径
        if project_config:
            if not data_path:
                data_path = str(project_config.get_data_path("extracted_params.json"))
            if not detailed_path:
                detailed_path = str(project_config.get_data_path("extracted_params_detailed.json"))
            if not output_dir:
                output_dir = str(project_config.get_output_path())
            project_config.create_output_dirs()

        if not data_path or not Path(data_path).exists():
            raise FileNotFoundError(f"数据文件不存在: {data_path}")

        pipeline = HotelREITsPipeline(
            data_path=data_path,
            detailed_data_path=detailed_path,
            output_base=output_dir,
        )

        result = pipeline.run()

        for log in result.logs:
            print(f"  {log}")

        pipeline.save_results()

        print_header("Pipeline完成")
        if result.step3_dcf:
            val = result.step3_dcf["dcf_results"]["total_valuation"]
            print(f"\n  [RESULT] DCF估值: {val:,.2f}万元 ({val/10000:.2f}亿元)")

        return result.to_dict()


def interactive_mode(project_config: Optional[ProjectConfigManager] = None):
    print_header("REITs估值建模Agent - 交互模式")

    # 如果提供了项目配置，显示当前项目信息
    if project_config:
        project = project_config.active_project_config
        print(f"\n[当前项目] {project.label} ({project.name})")
        print(f"   业态: {', '.join(project.asset_types)}")
        print(f"   数据目录: {project_config.get_data_path()}")
        print(f"   输出目录: {project_config.get_output_path()}")

    print("\n选择模式:")
    print("  1. 通用REITs估值（从PDF文件）")
    print("  2. 酒店REITs Pipeline（从已提取JSON数据）")

    choice = input("请输入选项 (1-2): ").strip()

    if choice == "2":
        if project_config:
            # 使用项目配置自动获取数据路径
            data_path = str(project_config.get_data_path("extracted_params.json"))
            detailed_path = str(project_config.get_data_path("extracted_params_detailed.json"))
            print(f"\n[自动加载项目数据]")
            print(f"  数据文件: {data_path}")
            print(f"  详细文件: {detailed_path}")
            confirm = input("确认使用以上路径? (回车确认/输入n手动指定): ").strip()
            if confirm.lower() == 'n':
                data_path = input("请输入extracted_params.json路径: ").strip()
                detailed_path = input("请输入extracted_params_detailed.json路径（可留空）: ").strip() or None
        else:
            data_path = input("请输入extracted_params.json路径: ").strip()
            detailed_path = input("请输入extracted_params_detailed.json路径（可留空）: ").strip() or None
        REITsModelingAgent.run_hotel_pipeline(data_path, detailed_path, project_config=project_config)
    else:
        agent = REITsModelingAgent()
        file_path = input("\n请输入招募说明书文件路径: ").strip()
        if not Path(file_path).exists():
            print(f"错误: 文件不存在: {file_path}")
            return

        print("\n选择资产类型:")
        print("  1. 产业园  2. 物流仓储  3. 保障房  4. 基础设施  5. 酒店")
        type_choice = input("请输入选项 (1-5) 或回车自动识别: ").strip()
        asset_type_map = {
            "1": AssetType.INDUSTRIAL, "2": AssetType.LOGISTICS,
            "3": AssetType.HOUSING, "4": AssetType.INFRASTRUCTURE,
            "5": AssetType.HOTEL,
        }
        asset_type = asset_type_map.get(type_choice)
        output_dir = str(project_config.get_output_path()) if project_config else "./output"
        agent.run_complete_workflow(file_path, asset_type, output_dir)


def main():
    parser = argparse.ArgumentParser(
        description="REITs估值建模Agent - 从招募说明书到估值模型",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py -f 招募说明书.pdf -t hotel
  python main.py --project huazhu --pipeline
  python main.py --project huarun_chengdu --data data/huarun/extracted_params.json --pipeline
  python main.py -p huazhu -i
        """)

    parser.add_argument("-f", "--file", help="招募说明书文件路径 (PDF/Word/Excel)")
    parser.add_argument("-t", "--asset-type",
                        choices=["industrial", "logistics", "housing", "infrastructure", "hotel"],
                        help="资产类型")
    parser.add_argument("-o", "--output", help="输出目录（默认使用项目配置）")
    parser.add_argument("-p", "--project",
                        help="项目ID (如: huazhu, huarun_chengdu)")
    parser.add_argument("-i", "--interactive", action="store_true", help="交互模式")
    parser.add_argument("--data", help="已提取参数JSON路径（酒店Pipeline模式）")
    parser.add_argument("--detailed", help="详细参数JSON路径（酒店Pipeline模式）")
    parser.add_argument("--pipeline", action="store_true", help="运行酒店REITs 4步Pipeline")

    args = parser.parse_args()

    # 加载项目配置
    config = get_config(
        project_name=args.project,
        auto_confirm=not args.interactive,
        silent=False
    )
    config.create_output_dirs()

    # 确定输出目录：命令行参数 > 项目配置
    output_dir = args.output if args.output else str(config.get_output_path())

    if args.pipeline:
        # Pipeline模式：自动从项目配置获取数据路径
        data_path = args.data or str(config.get_data_path("extracted_params.json"))
        detailed_path = args.detailed or str(config.get_data_path("extracted_params_detailed.json"))
        REITsModelingAgent.run_hotel_pipeline(
            data_path, detailed_path, output_dir, project_config=config)
    elif args.interactive or (not args.file and not args.data):
        interactive_mode(project_config=config)
    elif args.pipeline and args.data:
        REITsModelingAgent.run_hotel_pipeline(
            args.data, args.detailed, output_dir, project_config=config)
    elif args.file:
        asset_type = AssetType(args.asset_type) if args.asset_type else None
        agent = REITsModelingAgent()
        agent.run_complete_workflow(args.file, asset_type, output_dir)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
