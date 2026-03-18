#!/usr/bin/env python3
"""
华住REIT手动参数建模示例
基于招募说明书关键数据
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import AssetType
from src.models.dcf_model import DCFModel, DCFInputs
from src.models.scenarios import ScenarioManager
from src.models.sensitivity import SensitivityAnalyzer
from src.validators import RiskAnalyzer, ParameterValidator
from src.exporters import ExcelGenerator, JSONExporter, Visualizer, DataProvider
from src.models.asset_types.hotel import HotelREIT

def main():
    print("=" * 70)
    print("  华住REIT估值建模 - 手动参数输入示例")
    print("=" * 70)

    # ============================================
    # 手动输入华住REIT关键参数（基于招募说明书）
    # ============================================
    print("\n>>> 设置估值参数...")

    inputs = DCFInputs(
        asset_type=AssetType.HOTEL,
        project_name="华泰紫金南京华住酒店REIT",
        remaining_years=19,  # 特许经营剩余年限约19年

        # 收入端参数
        adr=495.58,  # 平均房价（元/晚），2024年数据
        room_count=495,  # 客房总数
        occupancy_rate=0.75,  # 入住率75%（2024年约76%，保守估计）
        rent_growth_rate=0.03,  # ADR年增长率3%
        fb_revenue_ratio=0.30,  # 餐饮收入占比约30%

        # 成本端参数
        operating_expense=5267.45,  # 年运营成本（万元）
        operating_expense_ratio=0.65,  # 酒店运营成本率约65%
        management_fee_ratio=0.03,  # 管理费率3%
        maintenance_cost=311.91,  # 年维护费用（万元）

        # 资本端参数
        discount_rate=0.0575,  # 折现率5.75%（招募说明书披露）
        capex=400.0,  # 年均资本性支出（万元）
    )

    # 显示输入参数
    print("\n  [基础信息]")
    print(f"    项目名称: {inputs.project_name}")
    print(f"    资产类型: {inputs.asset_type.value}")
    print(f"    预测年限: {inputs.remaining_years} 年")

    print("\n  [收入端假设]")
    print(f"    平均房价(ADR): {inputs.adr:.2f} 元/晚")
    print(f"    客房数量: {inputs.room_count} 间")
    print(f"    入住率: {inputs.occupancy_rate:.1%}")
    print(f"    ADR年增长率: {inputs.rent_growth_rate:.2%}")
    print(f"    餐饮收入占比: {inputs.fb_revenue_ratio:.1%}")

    print("\n  [成本端假设]")
    print(f"    年运营成本: {inputs.operating_expense:.2f} 万元")
    print(f"    运营成本率: {inputs.operating_expense_ratio:.1%}")
    print(f"    管理费率: {inputs.management_fee_ratio:.1%}")
    print(f"    年维护费用: {inputs.maintenance_cost:.2f} 万元")

    print("\n  [资本端假设]")
    print(f"    折现率(WACC): {inputs.discount_rate:.2%}")
    print(f"    年资本性支出: {inputs.capex:.2f} 万元")

    # ============================================
    # 步骤1: 参数验证
    # ============================================
    print("\n" + "=" * 70)
    print("  步骤1: 参数验证")
    print("=" * 70)

    validator = ParameterValidator()
    issues = validator.validate_inputs(inputs)

    if issues:
        print(f"\n  发现 {len(issues)} 个验证提示:")
        for issue in issues:
            print(f"    [{issue.severity.upper()}] {issue.param_name}: {issue.message}")
    else:
        print("\n  [OK] 所有参数验证通过")

    # 酒店特有验证
    hotel_handler = HotelREIT()
    hotel_issues = hotel_handler.validate_params(inputs)
    if hotel_issues:
        print(f"\n  酒店特有风险提示:")
        for issue in hotel_issues:
            print(f"    [{issue['level'].upper()}] {issue['param']}: {issue['message']}")

    # ============================================
    # 步骤2: DCF估值计算
    # ============================================
    print("\n" + "=" * 70)
    print("  步骤2: DCF估值计算")
    print("=" * 70)

    model = DCFModel(inputs)
    base_result = model.calculate("Base Case")

    print(f"\n  [估值结果]")
    print(f"    DCF估值: {base_result.dcf_value:,.2f} 万元")
    if base_result.irr:
        print(f"    IRR: {base_result.irr:.2%}")

    # 现金流汇总
    total_noi = sum(cf.calculate_noi() for cf in base_result.cash_flows)
    avg_noi = total_noi / len(base_result.cash_flows) if base_result.cash_flows else 0
    print(f"\n  [现金流分析]")
    print(f"    {inputs.remaining_years}年总NOI: {total_noi:,.2f} 万元")
    print(f"    平均年NOI: {avg_noi:,.2f} 万元")

    # 显示前5年现金流
    print(f"\n  [前5年现金流预测]")
    print(f"    {'年份':<6} {'收入(万元)':<12} {'费用(万元)':<12} {'NOI(万元)':<12}")
    print(f"    {'-'*50}")
    for cf in base_result.cash_flows[:5]:
        noi = cf.calculate_noi()
        print(f"    {cf.year:<6} {cf.total_income:<12.2f} {cf.operating_expense:<12.2f} {noi:<12.2f}")

    # ============================================
    # 步骤3: 多情景分析
    # ============================================
    print("\n" + "=" * 70)
    print("  步骤3: 多情景分析")
    print("=" * 70)

    scenario_mgr = ScenarioManager(inputs)

    # 添加自定义情景
    scenario_mgr.add_scenario(
        name="Optimistic",
        description="乐观情景：入住率提升，ADR增长加快",
        adjustments={
            "occupancy_rate": 0.82,
            "rent_growth_rate": 0.04,
            "discount_rate": 0.055
        }
    )

    scenario_mgr.add_scenario(
        name="Pessimistic",
        description="悲观情景：入住率下降，成本上升",
        adjustments={
            "occupancy_rate": 0.68,
            "rent_growth_rate": 0.02,
            "operating_expense_ratio": 0.70,
            "discount_rate": 0.065
        }
    )

    scenario_mgr.add_scenario(
        name="Stress Test",
        description="压力测试：极端市场条件",
        adjustments={
            "occupancy_rate": 0.60,
            "rent_growth_rate": 0.01,
            "operating_expense_ratio": 0.75,
            "discount_rate": 0.075
        }
    )

    scenarios = scenario_mgr.calculate_all()

    print(f"\n  [情景对比结果]")
    print(f"    {'情景':<15} {'NPV(万元)':<15} {'vs基准':<10}")
    print(f"    {'-'*45}")
    for s in scenarios:
        vs_base = f"{s.vs_base_percent*100:+.1f}%" if s.vs_base_percent else "-"
        print(f"    {s.scenario_name:<15} {s.valuation.npv:<15,.0f} {vs_base:<10}")

    # ============================================
    # 步骤4: 敏感度分析
    # ============================================
    print("\n" + "=" * 70)
    print("  步骤4: 敏感度分析")
    print("=" * 70)

    analyzer = SensitivityAnalyzer(inputs)
    tornado_data = analyzer.generate_tornado_data()

    print(f"\n  [关键参数敏感度排名]")
    print(f"    {'参数':<20} {'-10%影响':<15} {'+10%影响':<15}")
    print(f"    {'-'*55}")
    for item in tornado_data[:5]:
        print(f"    {item['display_name']:<20} {item['minus_10_impact']:<15.0f} {item['plus_10_impact']:<15.0f}")

    # ============================================
    # 步骤5: 风险分析
    # ============================================
    print("\n" + "=" * 70)
    print("  步骤5: 风险分析")
    print("=" * 70)

    risk_analyzer = RiskAnalyzer()
    risks = risk_analyzer.analyze(base_result)

    high_risks = [r for r in risks if r.level == "high"]
    medium_risks = [r for r in risks if r.level == "medium"]

    print(f"\n  风险统计: 高{len(high_risks)} / 中{len(medium_risks)} / 低{len(risks)-len(high_risks)-len(medium_risks)}")

    if medium_risks:
        print(f"\n  [中风险项]")
        for risk in medium_risks[:3]:
            print(f"    - {risk.category}: {risk.description}")

    # ============================================
    # 步骤6: 生成报告
    # ============================================
    print("\n" + "=" * 70)
    print("  步骤6: 生成输出报告")
    print("=" * 70)

    output_dir = Path("./output/huazhu_manual")
    output_dir.mkdir(parents=True, exist_ok=True)

    generated_files = []

    # Excel
    try:
        excel_gen = ExcelGenerator()
        excel_path = excel_gen.generate(
            base_result,
            scenarios,
            str(output_dir / "华住REIT估值模型.xlsx")
        )
        generated_files.append(f"Excel: {excel_path}")
        print(f"\n  [OK] Excel模型: {excel_path}")
    except Exception as e:
        print(f"\n  [FAIL] Excel导出失败: {e}")

    # JSON
    try:
        json_exporter = JSONExporter()
        json_path = str(output_dir / "valuation_report.json")
        json_exporter.export_complete_report(
            base_result,
            scenarios,
            {"tornado": tornado_data},
            json_path
        )
        generated_files.append(f"JSON: {json_path}")
        print(f"  [OK] JSON报告: {json_path}")
    except Exception as e:
        print(f"  [FAIL] JSON导出失败: {e}")

    # 图表
    try:
        visualizer = Visualizer(str(output_dir))
        chart_paths = visualizer.generate_all_charts(base_result, scenarios)
        for name, path in chart_paths.items():
            generated_files.append(f"Chart({name}): {path}")
            print(f"  [OK] 图表 ({name})")
    except Exception as e:
        print(f"  [FAIL] 图表生成失败: {e}")

    # 结构化数据
    try:
        data_provider = DataProvider()
        data_provider.export_to_json(base_result, str(output_dir / "structured_data.json"))
        print(f"  [OK] 结构化数据已导出")
    except Exception as e:
        print(f"  [FAIL] 结构化数据导出失败: {e}")

    # ============================================
    # 完成
    # ============================================
    print("\n" + "=" * 70)
    print("  估值完成")
    print("=" * 70)
    print(f"\n  基准估值: {base_result.dcf_value:,.2f} 万元")
    print(f"  估值区间: {min(s.valuation.npv for s in scenarios):,.0f} ~ {max(s.valuation.npv for s in scenarios):,.0f} 万元")
    print(f"\n  输出目录: {output_dir}")
    print("\n  生成文件:")
    for f in generated_files:
        print(f"    - {f}")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
