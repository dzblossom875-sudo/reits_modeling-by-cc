#!/usr/bin/env python3
"""
综合体多业态DCF模型测试脚本

测试华润成都万象城项目（mall + hotel）的合并计算。
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import build_dcf_model, MultiAssetDCFModel


def test_multi_asset_dcf():
    """测试多业态综合体DCF计算"""
    print("=" * 60)
    print("  综合体多业态DCF模型测试")
    print("=" * 60)

    # 加载华润成都项目数据
    data_path = Path("data/huarun_chengdu/extracted_params.json")
    if not data_path.exists():
        print(f"[错误] 数据文件不存在: {data_path}")
        return False

    with open(data_path, "r", encoding="utf-8") as f:
        extracted_data = json.load(f)

    print(f"\n[项目] {extracted_data.get('fund_info', {}).get('name', '未知')}")
    print(f"[位置] {extracted_data.get('fund_info', {}).get('location', '未知')}")

    # 显示检测到的业态
    projects = extracted_data.get("projects", [])
    print(f"\n[子项目] 共 {len(projects)} 个:")
    for proj in projects:
        print(f"  - {proj.get('name')} (asset_type: {proj.get('asset_type')})")

    # 创建多业态模型
    print("\n[构建模型] 使用 MultiAssetDCFModel...")
    model = build_dcf_model("mixed", extracted_data)

    print(f"[检测业态] {model.asset_types}")
    print(f"[是否综合体] {model.is_mixed_asset}")

    # 执行计算
    print("\n[计算DCF] ...")
    result = model.calculate()

    # 输出结果
    print("\n" + "=" * 60)
    print("  DCF计算结果")
    print("=" * 60)
    print(result.summary())

    # 分业态明细
    print("\n" + "-" * 60)
    print("  分业态明细")
    print("-" * 60)
    for asset_type in model.asset_types:
        sub_result = model.get_sub_result(asset_type)
        if sub_result:
            print(f"\n[{asset_type.upper()}]")
            print(f"  估值: {sub_result.total_valuation:,.2f} 万元")
            print(f"  Y1 NOI: {sub_result.total_noi_year1:,.2f} 万元")
            print(f"  项目数: {len(sub_result.projects)}")

            # 显示第一个项目的现金流前几期
            if sub_result.projects:
                proj = sub_result.projects[0]
                print(f"\n  项目: {proj.name}")
                print(f"  剩余年限: {proj.remaining_years:.2f} 年")
                if proj.cash_flows:
                    print("  现金流明细（前5年）:")
                    for cf in proj.cash_flows[:5]:
                        print(f"    Y{cf.year}: NOI={cf.noi:,.0f}, Capex={cf.capex:,.0f}, FCF={cf.fcf:,.0f}, PV={cf.pv:,.0f}")
                    if len(proj.cash_flows) > 5:
                        print(f"    ... 共 {len(proj.cash_flows)} 期")

    # 与招募说明书对比
    print("\n" + "-" * 60)
    print("  估值对比")
    print("-" * 60)
    benchmark = extracted_data.get("valuation_results", {}).get("total_wan", 0)
    if benchmark:
        diff_pct = (result.total_valuation - benchmark) / benchmark * 100
        print(f"招募说明书估值: {benchmark:,.2f} 万元 ({benchmark/10000:.2f} 亿元)")
        print(f"模型估值:       {result.total_valuation:,.2f} 万元 ({result.total_valuation/10000:.2f} 亿元)")
        print(f"差异:           {diff_pct:+.2f}%")

    print("\n" + "=" * 60)
    print("  测试完成")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        test_multi_asset_dcf()
    except Exception as e:
        print(f"\n[错误] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
