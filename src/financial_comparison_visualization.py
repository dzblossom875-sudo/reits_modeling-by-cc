#!/usr/bin/env python3
"""
历史财务数据与2026年预测对比可视化
生成表格和图表用于分析
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from matplotlib import font_manager

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 设置Seaborn样式
sns.set_style("whitegrid")
sns.set_palette("husl")


def load_data_from_json(json_path: str = None) -> dict:
    """从JSON文件加载财务对比数据（优先使用）"""
    if json_path is None:
        from pathlib import Path
        json_path = str(Path(__file__).parent.parent / 'output' / 'financial_comparison_data.json')

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return load_data()


def load_data():
    """加载财务对比数据（硬编码备用）"""
    data = {
        '广州项目': {
            '营业收入': {'2023': 13968.89, '2024': 14254.00, '2025': 13187.36, '3年平均': 13803.42, '2026预测': 14035.15},
            '营业成本': {'2023': 9901.86, '2024': 10427.29, '2025': 9105.43, '3年平均': 9811.53, '2026预测': 9100.00},
            '税金及附加': {'2023': 856.24, '2024': 833.48, '2025': 856.42, '3年平均': 848.71, '2026预测': 1103.86},
            '管理费用': {'2023': 718.42, '2024': 551.02, '2025': 449.11, '3年平均': 572.85, '2026预测': 450.00},
            '财务费用': {'2023': 2575.98, '2024': 2061.74, '2025': 1662.82, '3年平均': 2100.18, '2026预测': 0.00},
            '折旧费用': {'2023': 5347.00, '2024': 5567.00, '2025': 5421.06, '3年平均': 5445.02, '2026预测': 5300.00},
            '运营成本(不含折旧)': {'2023': 4554.86, '2024': 4860.29, '2025': 3684.37, '3年平均': 4366.51, '2026预测': 3800.00},
            'GOP': {'2023': 8557.79, '2024': 8960.23, '2025': 8646.57, '3年平均': 8721.53, '2026预测': 9482.29},
            '净利润': {'2023': -464.94, '2024': -151.52, '2025': -370.05, '3年平均': -328.84, '2026预测': 200.00},
            '经营现金流(NOI/CF)': {'2023': 7206.01, '2024': 9026.15, '2025': 6605.93, '3年平均': 7612.70, '2026预测': 8107.60},
        },
        '上海项目': {
            '营业收入': {'2023': 3088.58, '2024': 3223.93, '2025': 3313.82, '3年平均': 3208.78, '2026预测': 3605.21},
            '营业成本': {'2023': 2070.43, '2024': 2137.79, '2025': 2124.89, '3年平均': 2111.04, '2026预测': 1850.00},
            '税金及附加': {'2023': 230.00, '2024': 240.00, '2025': 186.04, '3年平均': 218.68, '2026预测': 280.00},
            '管理费用': {'2023': 180.00, '2024': 170.00, '2025': 160.00, '3年平均': 170.00, '2026预测': 150.00},
            '财务费用': {'2023': 617.98, '2024': 403.58, '2025': 356.48, '3年平均': 459.35, '2026预测': 0.00},
            '折旧费用': {'2023': 802.00, '2024': 802.00, '2025': 802.04, '3年平均': 802.01, '2026预测': 750.00},
            '运营成本(不含折旧)': {'2023': 1268.43, '2024': 1335.79, '2025': 1322.85, '3年平均': 1309.02, '2026预测': 1100.00},
            'GOP': {'2023': 1590.15, '2024': 1648.14, '2025': 1804.93, '3年平均': 1681.07, '2026预测': 2325.21},
            '净利润': {'2023': -4.28, '2024': 159.62, '2025': 190.23, '3年平均': 115.19, '2026预测': 400.00},
            '经营现金流(NOI/CF)': {'2023': 1300.00, '2024': 1500.00, '2025': 1296.22, '3年平均': 1365.41, '2026预测': 1752.07},
        }
    }
    return data


def create_comparison_tables(data):
    """创建对比表格"""
    tables = {}

    for project_name, project_data in data.items():
        df = pd.DataFrame(project_data).T
        df = df[['2023', '2024', '2025', '3年平均', '2026预测']]
        tables[project_name] = df

        # 保存为CSV
        df.to_csv(f'output/{project_name}_财务对比表.csv', encoding='utf-8-sig')

        # 打印表格
        print(f"\n{'='*80}")
        print(f"{project_name} - 历史3年与2026年预测对比表（单位：万元）")
        print('='*80)
        print(df.to_string())

        # 计算变化率
        print(f"\n{project_name} - 关键指标变化率（2026预测 vs 3年平均）")
        print('-'*60)
        change_pct = ((df['2026预测'] - df['3年平均']) / df['3年平均'] * 100).round(2)
        for idx, val in change_pct.items():
            if not np.isnan(val) and not np.isinf(val):
                print(f"{idx:20s}: {val:+.2f}%")

    return tables


def plot_revenue_comparison(data, output_dir='output'):
    """绘制收入对比图"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    for idx, (project_name, project_data) in enumerate(data.items()):
        ax = axes[idx]

        years = ['2023', '2024', '2025', '3年平均', '2026预测']
        revenue = [project_data['营业收入'][y] for y in years]

        colors = ['#3498db', '#3498db', '#3498db', '#e74c3c', '#2ecc71']
        bars = ax.bar(years, revenue, color=colors, edgecolor='black', linewidth=1.2)

        # 添加数值标签
        for bar, val in zip(bars, revenue):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{val:.0f}',
                   ha='center', va='bottom', fontsize=9)

        ax.set_title(f'{project_name}\n营业收入对比', fontsize=12, fontweight='bold')
        ax.set_ylabel('金额（万元）', fontsize=10)
        ax.set_ylim(0, max(revenue) * 1.15)

        # 添加增长率注释
        growth = (revenue[-1] - revenue[-2]) / revenue[-2] * 100
        ax.annotate(f'增长率: {growth:+.1f}%',
                   xy=(4, revenue[-1]), xytext=(3, revenue[-1] * 1.08),
                   arrowprops=dict(arrowstyle='->', color='red'),
                   fontsize=9, color='red', fontweight='bold')

    plt.tight_layout()
    plt.savefig(f'{output_dir}/收入对比图.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\n图表已保存: {output_dir}/收入对比图.png")


def plot_cost_structure(data, output_dir='output'):
    """绘制成本结构堆叠图"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    cost_items = ['运营成本(不含折旧)', '税金及附加', '管理费用', '财务费用']
    colors = ['#3498db', '#e74c3c', '#f39c12', '#9b59b6']

    for idx, (project_name, project_data) in enumerate(data.items()):
        # 3年平均成本结构
        ax1 = axes[idx, 0]
        avg_costs = [project_data[item]['3年平均'] for item in cost_items]
        wedges, texts, autotexts = ax1.pie(avg_costs, labels=cost_items, autopct='%1.1f%%',
                                            colors=colors, startangle=90)
        ax1.set_title(f'{project_name}\n3年平均成本结构', fontsize=11, fontweight='bold')

        # 2026年预测成本结构
        ax2 = axes[idx, 1]
        pred_costs = [project_data[item]['2026预测'] for item in cost_items]
        wedges, texts, autotexts = ax2.pie(pred_costs, labels=cost_items, autopct='%1.1f%%',
                                            colors=colors, startangle=90)
        ax2.set_title(f'{project_name}\n2026年预测成本结构', fontsize=11, fontweight='bold')

    plt.tight_layout()
    plt.savefig(f'{output_dir}/成本结构对比图.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"图表已保存: {output_dir}/成本结构对比图.png")


def plot_key_metrics_trend(data, output_dir='output'):
    """绘制关键指标趋势图"""
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))

    metrics = [
        ('营业收入', '万元'),
        ('GOP', '万元'),
        ('经营现金流(NOI/CF)', '万元'),
        ('运营成本(不含折旧)', '万元'),
        ('税金及附加', '万元'),
        ('净利润', '万元')
    ]

    for idx, (metric, unit) in enumerate(metrics):
        ax = axes[idx // 3, idx % 3]

        for project_name, project_data in data.items():
            years = ['2023', '2024', '2025', '3年平均', '2026预测']
            values = [project_data[metric][y] for y in years]

            # 使用不同线型和标记
            if project_name == '广州项目':
                ax.plot(years, values, 'o-', linewidth=2, markersize=8,
                       label=project_name, color='#3498db')
            else:
                ax.plot(years, values, 's--', linewidth=2, markersize=8,
                       label=project_name, color='#e74c3c')

            # 添加数值标签
            for i, (x, y) in enumerate(zip(years, values)):
                if i == 3 or i == 4:  # 只标注3年平均和2026预测
                    ax.annotate(f'{y:.0f}', (x, y), textcoords="offset points",
                               xytext=(0, 10), ha='center', fontsize=8)

        ax.set_title(metric, fontsize=11, fontweight='bold')
        ax.set_ylabel(unit, fontsize=9)
        ax.legend(loc='best', fontsize=8)
        ax.grid(True, alpha=0.3)

        # 旋转x轴标签
        ax.tick_params(axis='x', rotation=45)

    plt.suptitle('关键财务指标趋势对比', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/关键指标趋势图.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"图表已保存: {output_dir}/关键指标趋势图.png")


def plot_noi_waterfall(data, output_dir='output'):
    """绘制NOI瀑布图 - 显示从3年平均到2026预测的变化分解"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for idx, (project_name, project_data) in enumerate(data.items()):
        ax = axes[idx]

        # 计算变化分解
        base = project_data['经营现金流(NOI/CF)']['3年平均']
        revenue_change = project_data['营业收入']['2026预测'] - project_data['营业收入']['3年平均']
        cost_change = -(project_data['运营成本(不含折旧)']['2026预测'] - project_data['运营成本(不含折旧)']['3年平均'])
        tax_change = -(project_data['税金及附加']['2026预测'] - project_data['税金及附加']['3年平均'])
        mgmt_change = -(project_data['管理费用']['2026预测'] - project_data['管理费用']['3年平均'])
        fin_change = -(project_data['财务费用']['2026预测'] - project_data['财务费用']['3年平均'])

        categories = ['3年平均\nNOI/CF', '收入增长', '成本优化', '税金变化', '管理优化', '财务费用\n消除', '2026预测\nNOI/CF']
        values = [base, revenue_change, cost_change, tax_change, mgmt_change, fin_change, 0]

        # 计算累计值
        cumulative = [base]
        for v in values[1:-1]:
            cumulative.append(cumulative[-1] + v)

        # 绘制瀑布图
        colors = ['#3498db', '#2ecc71' if revenue_change > 0 else '#e74c3c',
                 '#2ecc71' if cost_change > 0 else '#e74c3c',
                 '#2ecc71' if tax_change > 0 else '#e74c3c',
                 '#2ecc71' if mgmt_change > 0 else '#e74c3c',
                 '#2ecc71', '#9b59b6']

        x_pos = range(len(categories))

        # 绘制柱子
        for i, (cat, val, cum, color) in enumerate(zip(categories, values, [0] + cumulative, colors)):
            if i == 0:
                ax.bar(i, base, color=color, edgecolor='black', linewidth=1.2)
                ax.text(i, base + 50, f'{base:.0f}', ha='center', fontsize=9, fontweight='bold')
            elif i == len(categories) - 1:
                final = cumulative[-1]
                ax.bar(i, final, color=color, edgecolor='black', linewidth=1.2)
                ax.text(i, final + 50, f'{final:.0f}', ha='center', fontsize=9, fontweight='bold')
            else:
                bottom = cumulative[i-1] if val > 0 else cumulative[i-1] + val
                height = abs(val)
                ax.bar(i, height, bottom=bottom, color=color, edgecolor='black', linewidth=1.2)
                ax.text(i, bottom + height/2, f'{val:+.0f}', ha='center', va='center',
                       fontsize=8, fontweight='bold', color='white')

        # 连接线
        for i in range(len(cumulative) - 1):
            ax.plot([i+0.4, i+0.6], [cumulative[i], cumulative[i]], 'k--', alpha=0.5)

        ax.set_xticks(x_pos)
        ax.set_xticklabels(categories, fontsize=9)
        ax.set_title(f'{project_name}\nNOI/CF变化分解（万元）', fontsize=12, fontweight='bold')
        ax.set_ylabel('金额（万元）', fontsize=10)
        ax.axhline(y=base, color='gray', linestyle='--', alpha=0.5)
        ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(f'{output_dir}/NOI变化瀑布图.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"图表已保存: {output_dir}/NOI变化瀑布图.png")


def plot_heatmap_comparison(data, output_dir='output'):
    """绘制热力图对比变化率"""
    fig, axes = plt.subplots(1, 2, figsize=(12, 8))

    for idx, (project_name, project_data) in enumerate(data.items()):
        ax = axes[idx]

        # 计算变化率矩阵
        years = ['2023', '2024', '2025', '3年平均']
        metrics = ['营业收入', '营业成本', 'GOP', '经营现金流(NOI/CF)']

        matrix = []
        for metric in metrics:
            base = project_data[metric]['3年平均']
            row = []
            for year in years:
                change = (project_data[metric][year] - base) / base * 100 if base != 0 else 0
                row.append(change)
            # 添加2026预测
            change_2026 = (project_data[metric]['2026预测'] - base) / base * 100 if base != 0 else 0
            row.append(change_2026)
            matrix.append(row)

        # 绘制热力图
        im = ax.imshow(matrix, cmap='RdYlGn', aspect='auto', vmin=-30, vmax=30)

        # 设置刻度
        ax.set_xticks(range(5))
        ax.set_xticklabels(years + ['2026预测'])
        ax.set_yticks(range(len(metrics)))
        ax.set_yticklabels(metrics)

        # 添加数值
        for i in range(len(metrics)):
            for j in range(5):
                text = ax.text(j, i, f'{matrix[i][j]:.1f}%',
                             ha="center", va="center", color="black", fontsize=9)

        ax.set_title(f'{project_name}\n各指标同比变化率（%）', fontsize=12, fontweight='bold')

        # 添加颜色条
        cbar = plt.colorbar(im, ax=ax, shrink=0.8)
        cbar.set_label('变化率 (%)', rotation=270, labelpad=20)

    plt.tight_layout()
    plt.savefig(f'{output_dir}/变化率热力图.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"图表已保存: {output_dir}/变化率热力图.png")


def generate_summary_report(data, output_dir='output'):
    """生成汇总报告"""
    report = []
    report.append("=" * 80)
    report.append("华住REIT 历史财务数据与2026年预测对比分析汇总")
    report.append("=" * 80)

    for project_name, project_data in data.items():
        report.append(f"\n【{project_name}】")
        report.append("-" * 60)

        # 关键指标
        noi_avg = project_data['经营现金流(NOI/CF)']['3年平均']
        noi_2026 = project_data['经营现金流(NOI/CF)']['2026预测']
        noi_change = (noi_2026 - noi_avg) / noi_avg * 100

        report.append(f"NOI/CF: 3年平均 {noi_avg:.2f}万元 → 2026预测 {noi_2026:.2f}万元 ({noi_change:+.2f}%)")

        # 收入
        rev_avg = project_data['营业收入']['3年平均']
        rev_2026 = project_data['营业收入']['2026预测']
        report.append(f"营业收入: 3年平均 {rev_avg:.2f}万元 → 2026预测 {rev_2026:.2f}万元 ({(rev_2026-rev_avg)/rev_avg*100:+.2f}%)")

        # 主要驱动因素
        fin_eliminate = project_data['财务费用']['3年平均']
        report.append(f"主要驱动: 财务费用消除 {fin_eliminate:.2f}万元/年")

        # 风险因素
        tax_increase = project_data['税金及附加']['2026预测'] - project_data['税金及附加']['3年平均']
        report.append(f"风险因素: 房产税增加 {tax_increase:.2f}万元/年")

    report.append("\n" + "=" * 80)
    report_text = "\n".join(report)

    with open(f'{output_dir}/对比分析汇总.txt', 'w', encoding='utf-8') as f:
        f.write(report_text)

    print("\n" + report_text)
    print(f"\n报告已保存: {output_dir}/对比分析汇总.txt")


def main():
    """主函数"""
    print("=" * 80)
    print("历史财务数据与2026年预测对比可视化")
    print("=" * 80)

    # 加载数据
    data = load_data()

    # 创建对比表格
    print("\n【步骤1】生成对比表格...")
    tables = create_comparison_tables(data)

    # 生成可视化图表
    print("\n【步骤2】生成可视化图表...")
    plot_revenue_comparison(data)
    plot_cost_structure(data)
    plot_key_metrics_trend(data)
    plot_noi_waterfall(data)
    plot_heatmap_comparison(data)

    # 生成汇总报告
    print("\n【步骤3】生成汇总报告...")
    generate_summary_report(data)

    print("\n" + "=" * 80)
    print("所有图表和表格已生成完毕！")
    print("=" * 80)
    print("\n输出文件列表:")
    print("  - 广州项目_财务对比表.csv")
    print("  - 上海项目_财务对比表.csv")
    print("  - 收入对比图.png")
    print("  - 成本结构对比图.png")
    print("  - 关键指标趋势图.png")
    print("  - NOI变化瀑布图.png")
    print("  - 变化率热力图.png")
    print("  - 对比分析汇总.txt")


if __name__ == '__main__':
    main()
