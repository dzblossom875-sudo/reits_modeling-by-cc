#!/usr/bin/env python3
"""
生成财务对比图表（Matplotlib版本）
运行环境要求：Python 3.x + matplotlib + pandas
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# 设置图表样式
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10

# 设置中文字体
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False


def load_data():
    """加载财务数据"""
    with open('output/financial_comparison_data.json', 'r', encoding='utf-8') as f:
        return json.load(f)


def create_revenue_comparison_chart(data, output_dir='output/charts'):
    """创建收入对比图"""
    import os
    os.makedirs(output_dir, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    for idx, (project_name, project_data) in enumerate(data.items()):
        ax = axes[idx]

        years = ['2023', '2024', '2025', '3年平均', '2026预测']
        revenue = [project_data['营业收入'][y] for y in years]

        # 设置颜色
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
    plt.savefig(f'{output_dir}/01_收入对比图.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"图表已保存: {output_dir}/01_收入对比图.png")


def create_noi_comparison_chart(data, output_dir='output/charts'):
    """创建NOI对比图"""
    import os
    os.makedirs(output_dir, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    for idx, (project_name, project_data) in enumerate(data.items()):
        ax = axes[idx]

        years = ['2023', '2024', '2025', '3年平均', '2026预测']
        noi = [project_data['经营现金流'][y] for y in years]

        colors = ['#9b59b6', '#9b59b6', '#9b59b6', '#e74c3c', '#2ecc71']
        bars = ax.bar(years, noi, color=colors, edgecolor='black', linewidth=1.2)

        for bar, val in zip(bars, noi):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{val:.0f}',
                   ha='center', va='bottom', fontsize=9)

        ax.set_title(f'{project_name}\nNOI/CF对比', fontsize=12, fontweight='bold')
        ax.set_ylabel('金额（万元）', fontsize=10)
        ax.set_ylim(0, max(noi) * 1.15)

        growth = (noi[-1] - noi[-2]) / noi[-2] * 100
        ax.annotate(f'增长率: {growth:+.1f}%',
                   xy=(4, noi[-1]), xytext=(3, noi[-1] * 1.08),
                   arrowprops=dict(arrowstyle='->', color='red'),
                   fontsize=9, color='red', fontweight='bold')

    plt.tight_layout()
    plt.savefig(f'{output_dir}/02_NOI对比图.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"图表已保存: {output_dir}/02_NOI对比图.png")


def create_cost_breakdown_chart(data, output_dir='output/charts'):
    """创建成本结构分解图"""
    import os
    os.makedirs(output_dir, exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    cost_items = ['运营成本(不含折旧)', '税金及附加', '管理费用', '财务费用']
    colors = ['#3498db', '#e74c3c', '#f39c12', '#9b59b6']

    for idx, (project_name, project_data) in enumerate(data.items()):
        # 3年平均成本结构（饼图）
        ax1 = axes[idx, 0]
        avg_costs = [project_data[item]['3年平均'] for item in cost_items]
        wedges, texts, autotexts = ax1.pie(
            avg_costs, labels=cost_items, autopct='%1.1f%%',
            colors=colors, startangle=90
        )
        ax1.set_title(f'{project_name}\n3年平均成本结构', fontsize=11, fontweight='bold')

        # 2026年预测成本结构（饼图）
        ax2 = axes[idx, 1]
        pred_costs = [project_data[item]['2026预测'] for item in cost_items]
        wedges, texts, autotexts = ax2.pie(
            pred_costs, labels=cost_items, autopct='%1.1f%%',
            colors=colors, startangle=90
        )
        ax2.set_title(f'{project_name}\n2026年预测成本结构', fontsize=11, fontweight='bold')

    plt.tight_layout()
    plt.savefig(f'{output_dir}/03_成本结构对比图.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"图表已保存: {output_dir}/03_成本结构对比图.png")


def create_trend_chart(data, output_dir='output/charts'):
    """创建趋势对比图"""
    import os
    os.makedirs(output_dir, exist_ok=True)

    fig, axes = plt.subplots(2, 3, figsize=(16, 10))

    metrics = [
        ('营业收入', '万元'),
        ('营业成本', '万元'),
        ('GOP', '万元'),
        ('税金及附加', '万元'),
        ('经营现金流', '万元'),
        ('净利润', '万元')
    ]

    for idx, (metric, unit) in enumerate(metrics):
        ax = axes[idx // 3, idx % 3]

        for project_name, project_data in data.items():
            years = ['2023', '2024', '2025', '3年平均', '2026预测']
            values = [project_data[metric][y] for y in years]

            if project_name == '广州项目':
                ax.plot(years, values, 'o-', linewidth=2, markersize=8,
                       label=project_name, color='#3498db')
            else:
                ax.plot(years, values, 's--', linewidth=2, markersize=8,
                       label=project_name, color='#e74c3c')

            # 标注关键数值
            for i, (x, y) in enumerate(zip(years, values)):
                if i == 3 or i == 4:
                    ax.annotate(f'{y:.0f}', (x, y), textcoords="offset points",
                               xytext=(0, 10), ha='center', fontsize=8)

        ax.set_title(metric, fontsize=11, fontweight='bold')
        ax.set_ylabel(unit, fontsize=9)
        ax.legend(loc='best', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis='x', rotation=45)

    plt.suptitle('关键财务指标趋势对比', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/04_关键指标趋势图.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"图表已保存: {output_dir}/04_关键指标趋势图.png")


def create_waterfall_chart(data, output_dir='output/charts'):
    """创建NOI变化瀑布图"""
    import os
    os.makedirs(output_dir, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for idx, (project_name, project_data) in enumerate(data.items()):
        ax = axes[idx]

        # 计算变化分解
        base = project_data['经营现金流']['3年平均']
        revenue_change = project_data['营业收入']['2026预测'] - project_data['营业收入']['3年平均']
        cost_change = -(project_data['运营成本(不含折旧)']['2026预测'] - project_data['运营成本(不含折旧)']['3年平均'])
        tax_change = -(project_data['税金及附加']['2026预测'] - project_data['税金及附加']['3年平均'])
        mgmt_change = -(project_data['管理费用']['2026预测'] - project_data['管理费用']['3年平均'])
        fin_change = -(project_data['财务费用']['2026预测'] - project_data['财务费用']['3年平均'])

        categories = ['3年平均\nNOI/CF', '收入增长', '成本优化', '税金变化', '管理优化', '财务费用\n消除', '2026预测\nNOI/CF']
        values = [base, revenue_change, cost_change, tax_change, mgmt_change, fin_change]

        # 计算累计值
        cumulative = [base]
        for v in values[1:]:
            cumulative.append(cumulative[-1] + v)

        # 绘制瀑布图
        colors = ['#3498db', '#2ecc71', '#2ecc71', '#e74c3c', '#2ecc71', '#2ecc71', '#9b59b6']

        for i, (cat, val, cum, color) in enumerate(zip(categories, [base] + values, [0] + cumulative, colors)):
            if i == 0:
                ax.bar(i, base, color=color, edgecolor='black', linewidth=1.2)
                ax.text(i, base + max(cumulative)*0.02, f'{base:.0f}', ha='center', fontsize=9, fontweight='bold')
            elif i == len(categories) - 1:
                final = cumulative[-1]
                ax.bar(i, final, color=color, edgecolor='black', linewidth=1.2)
                ax.text(i, final + max(cumulative)*0.02, f'{final:.0f}', ha='center', fontsize=9, fontweight='bold')
            else:
                bottom = cumulative[i-1] if val > 0 else cumulative[i-1] + val
                height = abs(val)
                ax.bar(i, height, bottom=bottom, color=color, edgecolor='black', linewidth=1.2, alpha=0.8)
                ax.text(i, bottom + height/2, f'{val:+.0f}', ha='center', va='center',
                       fontsize=8, fontweight='bold', color='white' if abs(val) > max(cumulative)*0.1 else 'black')

        # 连接线
        for i in range(len(cumulative) - 1):
            ax.plot([i+0.4, i+0.6], [cumulative[i], cumulative[i]], 'k--', alpha=0.5, linewidth=1)

        ax.set_xticks(range(len(categories)))
        ax.set_xticklabels(categories, fontsize=9)
        ax.set_title(f'{project_name}\nNOI/CF变化分解（万元）', fontsize=12, fontweight='bold')
        ax.set_ylabel('金额（万元）', fontsize=10)
        ax.axhline(y=base, color='gray', linestyle='--', alpha=0.5)
        ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(f'{output_dir}/05_NOI变化瀑布图.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"图表已保存: {output_dir}/05_NOI变化瀑布图.png")


def create_summary_table(data, output_dir='output/charts'):
    """创建汇总对比表"""
    import os
    os.makedirs(output_dir, exist_ok=True)

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.axis('tight')
    ax.axis('off')

    # 准备数据
    table_data = []
    headers = ['指标', '广州-3年平均', '广州-2026预测', '广州-变化率',
               '上海-3年平均', '上海-2026预测', '上海-变化率']

    metrics = ['营业收入', '营业成本', '税金及附加', '管理费用', '财务费用',
               '运营成本(不含折旧)', 'GOP', '经营现金流']

    for metric in metrics:
        gz_avg = data['广州项目'][metric]['3年平均']
        gz_2026 = data['广州项目'][metric]['2026预测']
        gz_change = (gz_2026 - gz_avg) / gz_avg * 100 if gz_avg != 0 else 0

        sh_avg = data['上海项目'][metric]['3年平均']
        sh_2026 = data['上海项目'][metric]['2026预测']
        sh_change = (sh_2026 - sh_avg) / sh_avg * 100 if sh_avg != 0 else 0

        table_data.append([
            metric,
            f'{gz_avg:.0f}',
            f'{gz_2026:.0f}',
            f'{gz_change:+.1f}%',
            f'{sh_avg:.0f}',
            f'{sh_2026:.0f}',
            f'{sh_change:+.1f}%'
        ])

    # 创建表格
    table = ax.table(cellText=table_data, colLabels=headers,
                    cellLoc='center', loc='center',
                    colWidths=[0.2, 0.12, 0.12, 0.1, 0.12, 0.12, 0.1])

    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2)

    # 设置表头颜色
    for i in range(len(headers)):
        table[(0, i)].set_facecolor('#3498db')
        table[(0, i)].set_text_props(weight='bold', color='white')

    # 高亮变化率列
    for i in range(1, len(table_data) + 1):
        # 广州变化率
        val = float(table_data[i-1][3].replace('%', '').replace('+', ''))
        if val > 0:
            table[(i, 3)].set_facecolor('#d5f5e3')
        elif val < 0:
            table[(i, 3)].set_facecolor('#fadbd8')

        # 上海变化率
        val = float(table_data[i-1][6].replace('%', '').replace('+', ''))
        if val > 0:
            table[(i, 6)].set_facecolor('#d5f5e3')
        elif val < 0:
            table[(i, 6)].set_facecolor('#fadbd8')

    plt.title('华住REIT 历史3年平均 vs 2026年预测对比表（单位：万元）',
             fontsize=14, fontweight='bold', pad=20)
    plt.savefig(f'{output_dir}/06_汇总对比表.png', dpi=300, bbox_inches='tight')
    plt.close()
    print(f"图表已保存: {output_dir}/06_汇总对比表.png")


def main():
    """主函数"""
    print("=" * 60)
    print("生成财务对比图表")
    print("=" * 60)

    try:
        data = load_data()

        print("\n正在生成图表...")
        create_revenue_comparison_chart(data)
        create_noi_comparison_chart(data)
        create_cost_breakdown_chart(data)
        create_trend_chart(data)
        create_waterfall_chart(data)
        create_summary_table(data)

        print("\n" + "=" * 60)
        print("所有图表生成完毕！")
        print("输出目录: output/charts/")
        print("=" * 60)
        print("\n生成的图表列表:")
        print("  1. 01_收入对比图.png")
        print("  2. 02_NOI对比图.png")
        print("  3. 03_成本结构对比图.png")
        print("  4. 04_关键指标趋势图.png")
        print("  5. 05_NOI变化瀑布图.png")
        print("  6. 06_汇总对比表.png")

    except FileNotFoundError:
        print("\n错误: 未找到数据文件 output/financial_comparison_data.json")
        print("请先运行数据准备脚本")
    except Exception as e:
        print(f"\n错误: {e}")


if __name__ == '__main__':
    main()
