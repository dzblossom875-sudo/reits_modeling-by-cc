#!/usr/bin/env python3
"""
使用 Plotly 生成交互式NOI瀑布图
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent))

import plotly.graph_objects as go
from plotly.subplots import make_subplots


def load_project_data(data_path: str = "data/huazhu/extracted_params_detailed.json") -> dict:
    """加载项目数据"""
    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def calculate_metrics(revenue: Dict, expenses: Dict, capex_annual: float, growth_factor: float = 1.0) -> Dict:
    """计算各项指标"""
    # 收入
    room_revenue = revenue['hotel']['room_revenue']['first_year_amount'] * growth_factor
    ota_amount = revenue['hotel']['ota_revenue'].get('first_year_amount', 0) * growth_factor
    fb_amount = revenue['hotel']['fb_revenue']['first_year_amount'] * growth_factor
    other_amount = revenue['hotel']['other_revenue']['first_year_amount'] * growth_factor

    commercial_rental = revenue['commercial']['rental_income'] * growth_factor
    commercial_mgmt = revenue['commercial']['mgmt_fee_income'] * growth_factor
    total_commercial = commercial_rental + commercial_mgmt

    hotel_total = room_revenue + ota_amount + fb_amount + other_amount

    # 费用
    operating = expenses['operating']
    total_operating = sum([
        operating['labor_cost'], operating['fb_cost'],
        operating['cleaning_supplies'], operating['consumables'],
        operating['utilities'], operating['maintenance'],
        operating['marketing'], operating['data_system'],
        operating['other']
    ]) * growth_factor

    gop = hotel_total - total_operating

    commercial_expense = total_commercial * 0.2 * growth_factor
    property_expense = expenses['property_expense']['annual_total'] / 10000 * growth_factor
    insurance = expenses['insurance']['annual_amount'] * growth_factor

    land_tax = expenses['tax']['land_use_tax']['annual_amount'] / 10000 * growth_factor
    property_tax = 0
    if expenses['tax']['property_tax']['hotel'].get('original_value'):
        property_tax = (expenses['tax']['property_tax']['hotel']['original_value'] *
                       expenses['tax']['property_tax']['hotel']['rate'] * 0.7 / 10000 * growth_factor)
    total_tax = property_tax + land_tax

    mgmt_fee = gop * expenses['management_fee']['fee_rate']
    capex = capex_annual * growth_factor

    total_revenue = hotel_total + total_commercial
    total_expense = total_operating + commercial_expense + property_expense + insurance + total_tax + mgmt_fee + capex
    noi = total_revenue - total_expense

    return {
        '客房收入': room_revenue,
        '餐饮收入': fb_amount,
        '其他收入': other_amount,
        '商业收入': total_commercial,
        '运营费用': -total_operating,
        '商业费用': -commercial_expense,
        '物业费用': -property_expense,
        '保险费用': -insurance,
        '税费': -total_tax,
        '管理费': -mgmt_fee,
        '资本性支出': -capex,
        'NOI/CF': noi,
        # 汇总指标
        '酒店总收入': hotel_total,
        'GOP': gop,
        '总收入': total_revenue,
    }


def create_waterfall_chart(metrics: Dict, title: str, subtitle: str) -> go.Figure:
    """使用Plotly创建瀑布图"""

    # 定义瀑布图数据
    categories = ['客房收入', '餐饮收入', '其他收入', '商业收入',
                  '运营费用', '商业费用', '物业费用', '保险费用',
                  '税费', '管理费', '资本性支出', 'NOI/CF']

    values = [metrics[cat] for cat in categories]

    # 确定measure类型
    measures = []
    for i, cat in enumerate(categories):
        if cat == 'NOI/CF':
            measures.append('total')
        else:
            measures.append('relative')

    fig = go.Figure(go.Waterfall(
        name="NOI",
        orientation="v",
        measure=measures,
        x=categories,
        y=values,
        textposition="outside",
        text=[f"{v:,.0f}" if abs(v) < 10000 else f"{v/10000:.2f}亿" for v in values],
        connector={"line": {"color": "rgb(63, 63, 63)", "dash": "dot"}},
        decreasing={"marker": {"color": "#C62828"}},  # 红色-费用
        increasing={"marker": {"color": "#2E7D32"}},  # 绿色-收入
        totals={"marker": {"color": "#1565C0"}},      # 蓝色-NOI
    ))

    fig.update_layout(
        title={
            'text': f"{title}<br><sup>{subtitle}</sup>",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18}
        },
        yaxis_title="金额（万元）",
        yaxis=dict(
            gridcolor='lightgray',
            gridwidth=1,
        ),
        xaxis=dict(
            tickangle=45,
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12),
        showlegend=False,
        height=600,
        width=900,
        margin=dict(l=80, r=80, t=100, b=100),
    )

    # 添加网格线
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')

    return fig


def create_comparison_chart(metrics_2025: Dict, metrics_2026: Dict,
                            project_name: str, brand: str, rooms: int) -> go.Figure:
    """创建2025 vs 2026对比图（使用子图）"""

    from plotly.subplots import make_subplots

    # 创建3行2列的子图
    # 第1行：瀑布图对比
    # 第2行：收入占比饼图 + 成本占比饼图
    # 第3行：汇总表格
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=('2025年历史', '2026年预测', '收入结构占比', '成本结构占比', None, None),
        horizontal_spacing=0.1,
        vertical_spacing=0.08,
        specs=[
            [{"type": "waterfall"}, {"type": "waterfall"}],
            [{"type": "pie"}, {"type": "pie"}],
            [{"type": "table", "colspan": 2}, None]
        ],
        row_heights=[0.45, 0.35, 0.20]
    )

    categories = ['客房收入', '餐饮收入', '其他收入', '商业收入',
                  '运营费用', '商业费用', '物业费用', '保险费用',
                  '税费', '管理费', '资本性支出', 'NOI/CF']

    measures = ['relative'] * 11 + ['total']

    colors = {'increasing': '#2E7D32', 'decreasing': '#C62828', 'total': '#1565C0'}

    # 2025年数据
    values_2025 = [metrics_2025[cat] for cat in categories]
    fig.add_trace(
        go.Waterfall(
            name="2025",
            orientation="v",
            measure=measures,
            x=categories,
            y=values_2025,
            textposition="outside",
            text=[f"{v:,.0f}" if abs(v) < 10000 else f"{v/10000:.2f}亿" for v in values_2025],
            connector={"line": {"color": "gray", "dash": "dot"}},
            decreasing={"marker": {"color": colors['decreasing']}},
            increasing={"marker": {"color": colors['increasing']}},
            totals={"marker": {"color": colors['total']}},
            showlegend=False
        ),
        row=1, col=1
    )

    # 2026年数据
    values_2026 = [metrics_2026[cat] for cat in categories]
    fig.add_trace(
        go.Waterfall(
            name="2026",
            orientation="v",
            measure=measures,
            x=categories,
            y=values_2026,
            textposition="outside",
            text=[f"{v:,.0f}" if abs(v) < 10000 else f"{v/10000:.2f}亿" for v in values_2026],
            connector={"line": {"color": "gray", "dash": "dot"}},
            decreasing={"marker": {"color": colors['decreasing']}},
            increasing={"marker": {"color": colors['increasing']}},
            totals={"marker": {"color": colors['total']}},
            showlegend=False
        ),
        row=1, col=2
    )

    # 添加关键指标标注线
    def add_annotations(fig, metrics, col_idx):
        """添加关键指标标注 - 使用形状和注释"""
        xaxis = f'x{col_idx}' if col_idx > 1 else 'x'
        yaxis = f'y{col_idx}' if col_idx > 1 else 'y'

        total_revenue = metrics['总收入']
        gop = metrics['GOP']
        noi = metrics['NOI/CF']

        # 添加总收入水平线（在第4项之后）
        fig.add_hline(y=total_revenue, line_dash="dash", line_color="#5E35B1",
                      opacity=0.6, row=1, col=col_idx)

        # 添加GOP水平线（在第5项之后）
        fig.add_hline(y=gop, line_dash="dash", line_color="#F57C00",
                      opacity=0.6, row=1, col=col_idx)

        # 添加注释文本
        fig.add_annotation(
            x=2, y=total_revenue + 500,
            xref=xaxis, yref=yaxis,
            text=f"总收入<br><b>{total_revenue/10000:.2f}亿</b>" if total_revenue >= 10000 else f"总收入<br><b>{total_revenue:,.0f}</b>",
            showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1.5,
            arrowcolor='#5E35B1',
            font=dict(size=10, color='#5E35B1'),
            bgcolor='rgba(255,255,255,0.95)',
            bordercolor='#5E35B1', borderwidth=1,
            ax=0, ay=-20, row=1, col=col_idx
        )

        fig.add_annotation(
            x=2, y=gop + 500,
            xref=xaxis, yref=yaxis,
            text=f"GOP<br><b>{gop:,.0f}</b>",
            showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1.5,
            arrowcolor='#F57C00',
            font=dict(size=10, color='#F57C00'),
            bgcolor='rgba(255,248,225,0.95)',
            bordercolor='#F57C00', borderwidth=2,
            ax=0, ay=-20, row=1, col=col_idx
        )

        fig.add_annotation(
            x=10.5, y=noi + 800,
            xref=xaxis, yref=yaxis,
            text=f"NOI<br><b>{noi:,.0f}</b>",
            showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2,
            arrowcolor='#1565C0',
            font=dict(size=11, color='#1565C0', weight='bold'),
            bgcolor='rgba(227,242,253,0.95)',
            bordercolor='#1565C0', borderwidth=2,
            ax=0, ay=-30, row=1, col=col_idx
        )

    add_annotations(fig, metrics_2025, 1)
    add_annotations(fig, metrics_2026, 2)

    # 统一Y轴范围
    max_y = max(max(abs(v) for v in values_2025), max(abs(v) for v in values_2026)) * 1.25
    fig.update_yaxes(range=[0, max_y], row=1, col=1)
    fig.update_yaxes(range=[0, max_y], row=1, col=2)

    # 添加收入占比饼图（2025年）
    revenue_labels = ['客房收入', '餐饮收入', '其他收入', '商业收入']
    revenue_values_2025 = [abs(metrics_2025[k]) for k in revenue_labels]
    revenue_colors = ['#2E7D32', '#43A047', '#66BB6A', '#81C784']

    fig.add_trace(
        go.Pie(
            labels=revenue_labels,
            values=revenue_values_2025,
            name="收入结构",
            hole=0.4,
            marker_colors=revenue_colors,
            textinfo='label+percent',
            textfont_size=10,
            showlegend=False,
            domain=dict(row=1, column=0)
        ),
        row=2, col=1
    )

    # 添加成本占比饼图（2025年）
    cost_labels = ['运营费用', '商业费用', '物业费用', '保险费用', '税费', '管理费', '资本性支出']
    cost_values_2025 = [abs(metrics_2025[k]) for k in cost_labels]
    cost_colors = ['#C62828', '#D32F2F', '#E57373', '#EF5350', '#F44336', '#FF7043', '#FF8A65']

    fig.add_trace(
        go.Pie(
            labels=cost_labels,
            values=cost_values_2025,
            name="成本结构",
            hole=0.4,
            marker_colors=cost_colors,
            textinfo='label+percent',
            textfont_size=9,
            showlegend=False,
            domain=dict(row=1, column=1)
        ),
        row=2, col=2
    )

    # 添加汇总表格
    summary_items = [
        ('酒店总收入', '酒店总收入'),
        ('商业收入', '商业收入'),
        ('总收入', '总收入'),
        ('运营费用', '运营费用'),
        ('GOP', 'GOP'),
        ('NOI/CF', 'NOI/CF'),
    ]

    table_data = []
    for label, key in summary_items:
        val_2025 = metrics_2025[key]
        val_2026 = metrics_2026[key]
        change_pct = ((val_2026 - val_2025) / val_2025 * 100) if val_2025 != 0 else 0
        change_abs = val_2026 - val_2025

        def fmt(v):
            return f"{v/10000:.2f}亿" if abs(v) >= 10000 else f"{v:,.0f}"

        table_data.append([label, fmt(val_2025), fmt(val_2026), fmt(change_abs), f"{change_pct:+.1f}%"])

    fig.add_trace(
        go.Table(
            header=dict(
                values=['指标', '2025年历史', '2026年预测', '绝对变化', '变化率'],
                fill_color='#E3F2FD',
                align='center',
                font=dict(size=12, color='black'),
                line_color='darkslategray',
                line_width=1.5
            ),
            cells=dict(
                values=list(zip(*table_data)),
                fill_color=[['white', '#FFF8E1'] * 3],
                align='center',
                font=dict(size=11),
                line_color='darkslategray',
                line_width=1,
                height=25
            )
        ),
        row=3, col=1
    )

    # 更新布局
    fig.update_layout(
        title={
            'text': f"{project_name} - 收入支出结构分析<br><sup>品牌: {brand} | 房间数: {rooms}间</sup>",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20}
        },
        height=1400,
        width=1600,
        plot_bgcolor='white',
        paper_bgcolor='white',
        yaxis=dict(gridcolor='lightgray', title='金额（万元）'),
        yaxis2=dict(gridcolor='lightgray', title='金额（万元）'),
        margin=dict(l=80, r=80, t=120, b=50),
        annotations=[
            # 饼图中心文字
            dict(text='收入<br>结构', x=0.20, y=0.52, font_size=12, showarrow=False, xref='paper', yref='paper'),
            dict(text='成本<br>结构', x=0.80, y=0.52, font_size=12, showarrow=False, xref='paper', yref='paper'),
        ]
    )

    # 更新x轴
    fig.update_xaxes(tickangle=45, row=1, col=1)
    fig.update_xaxes(tickangle=45, row=1, col=2)

    return fig


def create_summary_table(metrics_2025: Dict, metrics_2026: Dict) -> go.Figure:
    """创建汇总指标表格"""

    summary_items = [
        ('酒店总收入', '酒店总收入'),
        ('商业收入', '商业收入'),
        ('总收入', '总收入'),
        ('运营费用', '运营费用'),
        ('GOP', 'GOP'),
        ('NOI/CF', 'NOI/CF'),
    ]

    table_data = []
    for label, key in summary_items:
        val_2025 = metrics_2025[key]
        val_2026 = metrics_2026[key]
        change_pct = ((val_2026 - val_2025) / val_2025 * 100) if val_2025 != 0 else 0
        change_abs = val_2026 - val_2025

        # 格式化
        def fmt(v):
            return f"{v/10000:.2f}亿" if abs(v) >= 10000 else f"{v:,.0f}"

        table_data.append([
            label,
            fmt(val_2025),
            fmt(val_2026),
            fmt(change_abs),
            f"{change_pct:+.1f}%"
        ])

    fig = go.Figure(data=[go.Table(
        header=dict(
            values=['指标', '2025年历史', '2026年预测', '绝对变化', '变化率'],
            fill_color='#E3F2FD',
            align='center',
            font=dict(size=14, color='black', weight='bold'),
            line_color='darkslategray',
            line_width=2
        ),
        cells=dict(
            values=list(zip(*table_data)),
            fill_color=[['white', '#FFF8E1'] * 3],
            align='center',
            font=dict(size=12),
            line_color='darkslategray',
            line_width=1,
            height=30
        )
    )])

    fig.update_layout(
        title="关键指标汇总",
        width=800,
        height=300,
        margin=dict(l=20, r=20, t=60, b=20),
    )

    return fig


def main():
    print("=" * 70)
    print("  使用 Plotly 生成交互式NOI瀑布图")
    print("=" * 70)

    # 创建输出目录
    output_dir = Path("output/waterfall_plotly")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 加载数据
    print("\n加载项目数据...")
    data = load_project_data()
    cpi_rate = data.get('valuation_parameters', {}).get('growth_rate', {}).get('cpi_baseline', 0.025)

    for project in data['projects']:
        project_name = project['name']
        brand = project['brand']
        rooms = project['total_rooms']

        print(f"\n生成 {project_name} 图表...")

        revenue = project['revenue']
        expenses = project['expenses']
        capex = project['capex']['annual_capex']

        # 计算两年数据
        metrics_2025 = calculate_metrics(revenue, expenses, capex, 1.0)
        metrics_2026 = calculate_metrics(revenue, expenses, capex, 1.0 + cpi_rate)

        # 1. 生成对比瀑布图
        fig_comparison = create_comparison_chart(
            metrics_2025, metrics_2026, project_name, brand, rooms
        )

        comparison_path = output_dir / f"{project_name.replace(' ', '_')}_comparison.html"
        fig_comparison.write_html(str(comparison_path))
        print(f"  [OK] 对比图: {comparison_path}")

        # 2. 生成汇总表格
        fig_table = create_summary_table(metrics_2025, metrics_2026)

        table_path = output_dir / f"{project_name.replace(' ', '_')}_summary.html"
        fig_table.write_html(str(table_path))
        print(f"  [OK] 汇总表: {table_path}")

        # 3. 同时生成静态PNG
        png_path = output_dir / f"{project_name.replace(' ', '_')}_comparison.png"
        fig_comparison.write_image(str(png_path), scale=2)
        print(f"  [OK] 静态图: {png_path}")

    print("\n" + "=" * 70)
    print("所有图表已生成！")
    print(f"输出目录: {output_dir}/")
    print("提示: HTML文件可在浏览器中打开查看交互式图表")
    print("=" * 70)


if __name__ == "__main__":
    main()
