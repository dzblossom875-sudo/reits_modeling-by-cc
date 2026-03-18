#!/usr/bin/env python3
"""
生成NOI瀑布图
展示历史收入支出结构和预测首年收入支出结构对比
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.exporters.visualizer import Visualizer


def load_project_data(data_path: str = "data/huazhu/extracted_params_detailed.json") -> dict:
    """加载项目数据"""
    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    print("=" * 70)
    print("  NOI瀑布图生成（2025 vs 2026对比）")
    print("=" * 70)

    # 初始化可视化器
    viz = Visualizer(output_dir="output/waterfall_charts")

    # 加载数据
    print("\n加载项目数据...")
    data = load_project_data()

    # 从配置中获取增长率
    cpi_rate = data.get('valuation_parameters', {}).get('growth_rate', {}).get('cpi_baseline', 0.025)

    # 生成各项目的对比瀑布图
    for project in data['projects']:
        project_name = project['name']
        print(f"\n生成 {project_name} 对比瀑布图...")

        # 生成2025 vs 2026对比图
        filepath = viz.plot_project_noir_waterfall_comparison(
            project_data=project,
            year1_label="2025年历史",
            year2_label="2026年预测",
            growth_rate=cpi_rate,
            filename=f"{project_name.replace(' ', '_')}_comparison"
        )
        print(f"  [OK] {filepath}")

    print("\n" + "=" * 70)
    print("所有对比瀑布图已生成！")
    print(f"输出目录: output/waterfall_charts/")
    print("=" * 70)


if __name__ == "__main__":
    main()
