"""
可视化图表生成器
生成估值相关的图表
"""

from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import matplotlib.lines as mlines
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')  # 使用非交互式后端
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from ..core.types import ValuationResult, ScenarioResult
from ..core.exceptions import ExportError


@dataclass
class WaterfallItem:
    """瀑布图单项数据"""
    label: str
    value: float
    item_type: str  # 'increase', 'decrease', 'total', 'subtotal'
    category: str   # 'revenue', 'expense', 'noi'


class Visualizer:
    """可视化图表生成器"""

    def __init__(self, output_dir: str = "./output"):
        if not MATPLOTLIB_AVAILABLE:
            raise ExportError("matplotlib未安装，请运行: pip install matplotlib")

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

    def generate_all_charts(
        self,
        valuation: ValuationResult,
        scenarios: Optional[List[ScenarioResult]] = None,
        tornado_data: Optional[List[Dict]] = None
    ) -> Dict[str, str]:
        """
        生成所有图表

        Args:
            valuation: 基准估值
            scenarios: 情景列表
            tornado_data: Tornado图数据

        Returns:
            图表路径字典
        """
        paths = {}

        # 现金流趋势图
        paths['cashflow_trend'] = self.plot_cashflow_trend(valuation)

        # 情景对比图
        if scenarios:
            paths['scenario_comparison'] = self.plot_scenario_comparison(scenarios)

        # Tornado图
        if tornado_data:
            paths['tornado'] = self.plot_tornado(tornado_data)

        return paths

    def plot_cashflow_trend(self, valuation: ValuationResult) -> str:
        """
        绘制现金流趋势图

        Args:
            valuation: 估值结果

        Returns:
            图表文件路径
        """
        if not valuation.cash_flows:
            return ""

        years = [cf.year for cf in valuation.cash_flows]
        nois = [cf.calculate_noi() for cf in valuation.cash_flows]
        incomes = [cf.total_income for cf in valuation.cash_flows]
        expenses = [cf.operating_expense + cf.management_fee for cf in valuation.cash_flows]

        fig, ax = plt.subplots(figsize=(10, 6))

        ax.plot(years, nois, 'b-o', label='NOI', linewidth=2, markersize=6)
        ax.plot(years, incomes, 'g--s', label='总收入', linewidth=1.5, markersize=5)
        ax.plot(years, expenses, 'r--^', label='总费用', linewidth=1.5, markersize=5)

        ax.set_xlabel('年份', fontsize=12)
        ax.set_ylabel('金额（万元）', fontsize=12)
        ax.set_title(f'{valuation.project_info.name or "项目"} - 现金流预测', fontsize=14)
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)

        # 添加数值标签
        for i, (year, noi) in enumerate(zip(years, nois)):
            if i % 2 == 0:  # 每隔一个显示
                ax.annotate(f'{noi:.0f}', xy=(year, noi), textcoords="offset points",
                           xytext=(0, 10), ha='center', fontsize=8)

        filepath = self.output_dir / f'cashflow_trend_{valuation.created_at.strftime("%Y%m%d")}.png'
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

        return str(filepath)

    def plot_scenario_comparison(self, scenarios: List[ScenarioResult]) -> str:
        """
        绘制情景对比柱状图

        Args:
            scenarios: 情景结果列表

        Returns:
            图表文件路径
        """
        if not scenarios:
            return ""

        names = [s.scenario_name for s in scenarios]
        npvs = [s.valuation.npv for s in scenarios]

        # 设置颜色（基准为蓝色，其他根据高低着色）
        colors = ['#1f77b4']  # 基准蓝色
        base_npv = npvs[0] if npvs else 0
        for npv in npvs[1:]:
            if npv >= base_npv:
                colors.append('#2ca02c')  # 绿色（优于基准）
            else:
                colors.append('#d62728')  # 红色（低于基准）

        fig, ax = plt.subplots(figsize=(10, 6))

        bars = ax.bar(names, npvs, color=colors, edgecolor='black', linewidth=1)

        # 添加数值标签
        for bar, npv in zip(bars, npvs):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{npv:.0f}',
                   ha='center', va='bottom', fontsize=10)

        ax.set_ylabel('NPV（万元）', fontsize=12)
        ax.set_title('多情景估值对比', fontsize=14)
        ax.axhline(y=base_npv, color='gray', linestyle='--', alpha=0.5, label='基准线')
        ax.legend()
        ax.grid(True, axis='y', alpha=0.3)

        # 旋转x轴标签
        plt.xticks(rotation=15, ha='right')

        filepath = self.output_dir / f'scenario_comparison_{scenarios[0].valuation.created_at.strftime("%Y%m%d")}.png'
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

        return str(filepath)

    def plot_tornado(self, tornado_data: List[Dict[str, Any]]) -> str:
        """
        绘制Tornado图（敏感度分析）

        Args:
            tornado_data: Tornado数据

        Returns:
            图表文件路径
        """
        if not tornado_data:
            return ""

        # 准备数据
        param_names = [d['display_name'] for d in tornado_data[:6]]  # 取前6个
        minus_impacts = [d['minus_10_impact'] for d in tornado_data[:6]]
        plus_impacts = [d['plus_10_impact'] for d in tornado_data[:6]]

        fig, ax = plt.subplots(figsize=(10, 8))

        y_pos = range(len(param_names))

        # 绘制双向柱状图
        ax.barh(y_pos, minus_impacts, color='#d62728', alpha=0.7, label='-10%')
        ax.barh(y_pos, plus_impacts, color='#2ca02c', alpha=0.7, label='+10%')

        ax.set_yticks(y_pos)
        ax.set_yticklabels(param_names)
        ax.axvline(x=0, color='black', linewidth=0.8)
        ax.set_xlabel('NPV变化（万元）', fontsize=12)
        ax.set_title('敏感度分析 - Tornado图', fontsize=14)
        ax.legend()
        ax.grid(True, axis='x', alpha=0.3)

        # 反转y轴使最重要的在顶部
        ax.invert_yaxis()

        filepath = self.output_dir / f'tornado_{param_names[0] if param_names else "sensitivity"}.png'
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

        return str(filepath)

    def plot_valuation_range(
        self,
        min_val: float,
        max_val: float,
        base_val: float,
        title: str = "估值区间"
    ) -> str:
        """
        绘制估值区间图

        Args:
            min_val: 最小估值
            max_val: 最大估值
            base_val: 基准估值
            title: 图表标题

        Returns:
            图表文件路径
        """
        fig, ax = plt.subplots(figsize=(10, 4))

        # 绘制区间
        ax.barh(0, max_val - min_val, left=min_val, height=0.3,
                color='lightgray', edgecolor='black', alpha=0.5)

        # 标记基准点
        ax.scatter(base_val, 0, color='blue', s=200, zorder=5, label='基准估值')
        ax.axvline(x=base_val, color='blue', linestyle='--', alpha=0.5)

        # 标记极值点
        ax.scatter(min_val, 0, color='red', s=100, zorder=5)
        ax.scatter(max_val, 0, color='green', s=100, zorder=5)

        ax.text(min_val, 0.2, f'最小: {min_val:.0f}', ha='center', fontsize=10)
        ax.text(max_val, 0.2, f'最大: {max_val:.0f}', ha='center', fontsize=10)
        ax.text(base_val, -0.25, f'基准: {base_val:.0f}', ha='center', fontsize=10, color='blue')

        ax.set_xlim(min_val * 0.9, max_val * 1.1)
        ax.set_ylim(-0.5, 0.5)
        ax.set_yticks([])
        ax.set_xlabel('估值（万元）', fontsize=12)
        ax.set_title(title, fontsize=14)
        ax.legend()

        filepath = self.output_dir / f'valuation_range_{base_val:.0f}.png'
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

        return str(filepath)

    def plot_noir_waterfall(
        self,
        items: List[WaterfallItem],
        title: str = "收入支出瀑布图",
        subtitle: str = "",
        ylabel: str = "金额（万元）",
        figsize: Tuple[int, int] = (14, 8),
        filename: str = None
    ) -> str:
        """
        绘制NOI瀑布图

        展示从收入到NOI的转化过程

        Args:
            items: 瀑布图数据项列表
            title: 图表标题
            subtitle: 副标题
            ylabel: Y轴标签
            figsize: 图表尺寸
            filename: 文件名（不含扩展名）

        Returns:
            图表文件路径
        """
        # 颜色配置
        colors = {
            'increase': '#2E7D32',      # 深绿色 - 收入增加
            'decrease': '#C62828',      # 深红色 - 费用减少
            'total': '#1565C0',         # 深蓝色 - 总计
            'subtotal': '#5E35B1',      # 紫色 - 小计
        }

        fig, ax = plt.subplots(figsize=figsize)

        # 计算累计值
        cumulative = []
        running_total = 0

        for item in items:
            if item.item_type in ['total', 'subtotal']:
                cumulative.append(0)
                running_total = item.value
            else:
                cumulative.append(running_total)
                if item.item_type == 'increase':
                    running_total += item.value
                else:  # decrease
                    running_total -= abs(item.value)

        # 准备绘图数据
        labels = [item.label for item in items]
        values = [item.value for item in items]

        # 计算条形图高度和底部位置
        heights = []
        bottoms = []

        for item, cum in zip(items, cumulative):
            if item.item_type in ['total', 'subtotal']:
                heights.append(abs(item.value))
                bottoms.append(0)
            else:
                heights.append(abs(item.value))
                if item.item_type == 'increase':
                    bottoms.append(cum)
                else:  # decrease
                    bottoms.append(cum - abs(item.value))

        # 绘制条形
        x_pos = np.arange(len(labels))
        bar_width = 0.6

        for i, (item, height, bottom) in enumerate(zip(items, heights, bottoms)):
            color = colors.get(item.item_type, '#757575')

            # 总计/小计使用不同样式
            if item.item_type in ['total', 'subtotal']:
                ax.bar(x_pos[i], height, bar_width,
                      bottom=bottom, color=color,
                      edgecolor='black', linewidth=1.5, alpha=0.9)
            else:
                ax.bar(x_pos[i], height, bar_width,
                      bottom=bottom, color=color,
                      edgecolor='black', linewidth=0.5, alpha=0.8)

        # 添加连接线
        for i in range(len(items) - 1):
            if items[i].item_type not in ['total', 'subtotal']:
                if items[i].item_type == 'increase':
                    y_start = cumulative[i] + values[i]
                else:
                    y_start = cumulative[i] - abs(values[i])

                y_end = y_start  # 水平连接

                ax.plot([x_pos[i] + bar_width/2, x_pos[i+1] - bar_width/2],
                       [y_start, y_end],
                       'k--', linewidth=0.8, alpha=0.5)

        # 添加数值标签
        for i, (item, height, bottom) in enumerate(zip(items, heights, bottoms)):
            value = item.value

            # 确定标签位置
            if item.item_type == 'increase':
                y_pos = bottom + height + max(heights) * 0.02
            elif item.item_type == 'decrease':
                y_pos = bottom - max(heights) * 0.05
            else:  # total/subtotal
                y_pos = height + max(heights) * 0.02

            # 格式化数值
            if abs(value) >= 10000:
                label_text = f'{value/10000:.2f}亿'
            else:
                label_text = f'{value:.0f}'

            # 添加符号
            if item.item_type == 'increase':
                label_text = f'+{label_text}'
            elif item.item_type == 'decrease':
                label_text = f'-{label_text}'

            ax.text(x_pos[i], y_pos, label_text,
                   ha='center', va='bottom',
                   fontsize=9, fontweight='bold',
                   color='black')

        # 设置图表样式
        ax.set_xticks(x_pos)
        ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=10)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(title, fontsize=14, fontweight='bold', pad=10)

        if subtitle:
            ax.text(0.5, 1.02, subtitle,
                   transform=ax.transAxes,
                   ha='center', va='bottom',
                   fontsize=10, style='italic')

        # 添加网格线和零线
        ax.yaxis.grid(True, linestyle='--', alpha=0.3)
        ax.set_axisbelow(True)
        ax.axhline(y=0, color='black', linewidth=0.8)

        # 添加图例
        legend_elements = [
            mpatches.Patch(facecolor=colors['increase'], label='收入增加'),
            mpatches.Patch(facecolor=colors['decrease'], label='费用减少'),
            mpatches.Patch(facecolor=colors['subtotal'], label='小计'),
            mpatches.Patch(facecolor=colors['total'], label='总计'),
        ]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=9)

        # 调整布局
        plt.tight_layout()

        # 保存
        if filename is None:
            from datetime import datetime
            filename = f'noi_waterfall_{datetime.now().strftime("%Y%m%d")}'

        filepath = self.output_dir / f'{filename}.png'
        plt.savefig(filepath, dpi=150, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()

        return str(filepath)

    def _build_noir_waterfall_items(
        self,
        revenue: Dict,
        expenses: Dict,
        capex_annual: float,
        growth_factor: float = 1.0
    ) -> List[WaterfallItem]:
        """
        构建NOI瀑布图数据项（不含中间汇总项）

        Args:
            revenue: 收入数据
            expenses: 费用数据
            capex_annual: 年度资本性支出
            growth_factor: 增长因子（用于预测年份）

        Returns:
            瀑布图数据项列表
        """
        items = []

        # 收入项（应用增长因子）
        room_revenue = revenue['hotel']['room_revenue']['first_year_amount'] * growth_factor
        items.append(WaterfallItem("客房收入", room_revenue, 'increase', 'revenue'))

        # OTA收入
        ota_amount = revenue['hotel']['ota_revenue'].get('first_year_amount', 0) * growth_factor
        if ota_amount > 0:
            items.append(WaterfallItem("OTA收入", ota_amount, 'increase', 'revenue'))

        # 餐饮收入
        fb_amount = revenue['hotel']['fb_revenue']['first_year_amount'] * growth_factor
        items.append(WaterfallItem("餐饮收入", fb_amount, 'increase', 'revenue'))

        # 其他收入
        other_amount = revenue['hotel']['other_revenue']['first_year_amount'] * growth_factor
        items.append(WaterfallItem("其他收入", other_amount, 'increase', 'revenue'))

        # 商业收入
        commercial_rental = revenue['commercial']['rental_income'] * growth_factor
        commercial_mgmt = revenue['commercial']['mgmt_fee_income'] * growth_factor
        total_commercial = commercial_rental + commercial_mgmt
        items.append(WaterfallItem("商业收入", total_commercial, 'increase', 'revenue'))

        # 费用项（应用增长因子）
        operating = expenses['operating']
        total_operating = sum([
            operating['labor_cost'], operating['fb_cost'],
            operating['cleaning_supplies'], operating['consumables'],
            operating['utilities'], operating['maintenance'],
            operating['marketing'], operating['data_system'],
            operating['other']
        ]) * growth_factor
        items.append(WaterfallItem("运营费用", -total_operating, 'decrease', 'expense'))

        # 商业费用
        commercial_expense = total_commercial * 0.2 * growth_factor
        if commercial_expense > 0:
            items.append(WaterfallItem("商业费用", -commercial_expense, 'decrease', 'expense'))

        # 物业费用
        property_expense = expenses['property_expense']['annual_total'] / 10000 * growth_factor
        items.append(WaterfallItem("物业费用", -property_expense, 'decrease', 'expense'))

        # 保险费用
        insurance = expenses['insurance']['annual_amount'] * growth_factor
        items.append(WaterfallItem("保险费用", -insurance, 'decrease', 'expense'))

        # 税费
        land_tax = expenses['tax']['land_use_tax']['annual_amount'] / 10000 * growth_factor
        property_tax = 0
        if expenses['tax']['property_tax']['hotel'].get('original_value'):
            property_tax = (expenses['tax']['property_tax']['hotel']['original_value'] *
                          expenses['tax']['property_tax']['hotel']['rate'] * 0.7 / 10000 * growth_factor)

        total_tax = property_tax + land_tax
        if total_tax > 0:
            items.append(WaterfallItem("税费", -total_tax, 'decrease', 'expense'))

        # 管理费（基于GOP，需要先计算GOP）
        hotel_total = room_revenue + ota_amount + fb_amount + other_amount
        gop = hotel_total - total_operating
        mgmt_fee = gop * expenses['management_fee']['fee_rate']
        items.append(WaterfallItem("管理费", -mgmt_fee, 'decrease', 'expense'))

        # Capex
        capex = capex_annual * growth_factor
        items.append(WaterfallItem("资本性支出", -capex, 'decrease', 'expense'))

        # NOI总计（唯一汇总项）
        total_revenue = hotel_total + total_commercial
        total_expense = (total_operating + commercial_expense + property_expense +
                        insurance + total_tax + mgmt_fee + capex)
        noi = total_revenue - total_expense
        items.append(WaterfallItem("NOI/CF", noi, 'total', 'noi'))

        return items

    def plot_project_noir_waterfall_comparison(
        self,
        project_data: Dict[str, Any],
        year1_label: str = "2025年历史",
        year2_label: str = "2026年预测",
        growth_rate: float = 0.025,
        filename: str = None
    ) -> str:
        """
        生成2025vs2026对比瀑布图（左右并排显示）

        Args:
            project_data: 项目详细数据
            year1_label: 第一年标签
            year2_label: 第二年标签
            growth_rate: 年增长率（用于计算第二年数据）
            filename: 文件名

        Returns:
            图表文件路径
        """
        revenue = project_data['revenue']
        expenses = project_data['expenses']
        capex_annual = project_data['capex']['annual_capex']

        # 构建两年的数据
        items_year1 = self._build_noir_waterfall_items(revenue, expenses, capex_annual, growth_factor=1.0)
        items_year2 = self._build_noir_waterfall_items(revenue, expenses, capex_annual, growth_factor=1.0 + growth_rate)

        # 创建双图布局
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))

        # 颜色配置
        colors = {
            'increase': '#2E7D32',
            'decrease': '#C62828',
            'total': '#1565C0',
        }

        # 绘制两个瀑布图
        max_value = 0
        for ax, items, year_label in [(ax1, items_year1, year1_label), (ax2, items_year2, year2_label)]:
            self._plot_single_waterfall(ax, items, colors, year_label)
            # 记录最大值用于统一Y轴
            max_val = max([item.value for item in items if item.item_type == 'total'])
            max_value = max(max_value, max_val)

        # 统一Y轴范围
        y_max = max_value * 1.2
        ax1.set_ylim(0, y_max)
        ax2.set_ylim(0, y_max)

        # 总标题
        project_name = project_data['name']
        brand = project_data['brand']
        rooms = project_data['total_rooms']
        fig.suptitle(f"{project_name} - 收入支出结构对比", fontsize=16, fontweight='bold', y=1.02)
        fig.text(0.5, 0.98, f"品牌: {brand} | 房间数: {rooms}间 | 假设增长率: {growth_rate*100:.1f}%",
                ha='center', va='bottom', fontsize=11, style='italic')

        # 添加图例
        legend_elements = [
            mpatches.Patch(facecolor=colors['increase'], label='收入'),
            mpatches.Patch(facecolor=colors['decrease'], label='费用'),
            mpatches.Patch(facecolor=colors['total'], label='NOI'),
        ]
        fig.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, -0.02),
                  ncol=3, fontsize=10)

        # 计算汇总指标用于表格展示
        summary_data = self._calculate_summary_metrics(
            revenue, expenses, capex_annual, growth_rate
        )

        # 添加汇总表格
        self._add_summary_table(fig, summary_data)

        plt.tight_layout(rect=[0, 0.15, 1, 0.96])  # 为表格留出空间

        # 保存
        if filename is None:
            filename = f"{project_name.replace(' ', '_')}_comparison_waterfall"

        filepath = self.output_dir / f'{filename}.png'
        plt.savefig(filepath, dpi=150, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()

        return str(filepath)

    def _calculate_summary_metrics(
        self,
        revenue: Dict,
        expenses: Dict,
        capex_annual: float,
        growth_rate: float
    ) -> Dict[str, Dict[str, float]]:
        """
        计算汇总指标

        Returns:
            {
                '2025': {'hotel_revenue': ..., 'gop': ..., 'noi': ...},
                '2026': {'hotel_revenue': ..., 'gop': ..., 'noi': ...}
            }
        """
        results = {}

        for year, factor in [('2025', 1.0), ('2026', 1.0 + growth_rate)]:
            # 收入
            room_revenue = revenue['hotel']['room_revenue']['first_year_amount'] * factor
            ota_amount = revenue['hotel']['ota_revenue'].get('first_year_amount', 0) * factor
            fb_amount = revenue['hotel']['fb_revenue']['first_year_amount'] * factor
            other_amount = revenue['hotel']['other_revenue']['first_year_amount'] * factor

            commercial_rental = revenue['commercial']['rental_income'] * factor
            commercial_mgmt = revenue['commercial']['mgmt_fee_income'] * factor
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
            ]) * factor

            gop = hotel_total - total_operating

            commercial_expense = total_commercial * 0.2 * factor
            property_expense = expenses['property_expense']['annual_total'] / 10000 * factor
            insurance = expenses['insurance']['annual_amount'] * factor

            land_tax = expenses['tax']['land_use_tax']['annual_amount'] / 10000 * factor
            property_tax = 0
            if expenses['tax']['property_tax']['hotel'].get('original_value'):
                property_tax = (expenses['tax']['property_tax']['hotel']['original_value'] *
                              expenses['tax']['property_tax']['hotel']['rate'] * 0.7 / 10000 * factor)
            total_tax = property_tax + land_tax

            mgmt_fee = gop * expenses['management_fee']['fee_rate']
            capex = capex_annual * factor

            total_revenue = hotel_total + total_commercial
            total_expense = (total_operating + commercial_expense + property_expense +
                            insurance + total_tax + mgmt_fee + capex)
            noi = total_revenue - total_expense

            results[year] = {
                'hotel_revenue': hotel_total,
                'commercial_revenue': total_commercial,
                'total_revenue': total_revenue,
                'operating_expense': total_operating,
                'gop': gop,
                'other_expenses': (commercial_expense + property_expense + insurance + total_tax + mgmt_fee + capex),
                'noi': noi
            }

        return results

    def _add_summary_table(self, fig, summary_data: Dict):
        """
        在图下方添加汇总指标表格

        Args:
            fig: matplotlib figure对象
            summary_data: 汇总数据
        """
        # 创建表格数据
        metrics = [
            ('酒店总收入', 'hotel_revenue'),
            ('商业收入', 'commercial_revenue'),
            ('总收入', 'total_revenue'),
            ('运营费用', 'operating_expense'),
            ('GOP', 'gop'),
            ('其他费用', 'other_expenses'),
            ('NOI/CF', 'noi')
        ]

        table_data = []
        for label, key in metrics:
            val_2025 = summary_data['2025'][key]
            val_2026 = summary_data['2026'][key]
            change = ((val_2026 - val_2025) / val_2025 * 100) if val_2025 != 0 else 0

            # 格式化数值
            if abs(val_2025) >= 10000:
                val_2025_str = f"{val_2025/10000:.2f}亿"
            else:
                val_2025_str = f"{val_2025:.0f}"

            if abs(val_2026) >= 10000:
                val_2026_str = f"{val_2026/10000:.2f}亿"
            else:
                val_2026_str = f"{val_2026:.0f}"

            table_data.append([label, val_2025_str, val_2026_str, f"{change:+.1f}%"])

        # 创建表格axes
        table_ax = fig.add_axes([0.1, 0.02, 0.8, 0.12])
        table_ax.axis('off')

        # 创建表格
        table = table_ax.table(
            cellText=table_data,
            colLabels=['指标', '2025年历史', '2026年预测', '变化'],
            loc='center',
            cellLoc='center',
            colWidths=[0.25, 0.25, 0.25, 0.25]
        )

        # 设置表格样式
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.5)

        # 设置表头样式
        for i in range(4):
            table[(0, i)].set_facecolor('#E3F2FD')
            table[(0, i)].set_text_props(weight='bold')

        # 高亮关键行
        highlight_rows = [0, 4, 6]  # 酒店总收入, GOP, NOI
        for row in highlight_rows:
            for col in range(4):
                table[(row + 1, col)].set_facecolor('#FFF8E1')

    def _plot_single_waterfall(
        self,
        ax,
        items: List[WaterfallItem],
        colors: Dict[str, str],
        title: str
    ):
        """
        在指定axes上绘制单个瀑布图

        Args:
            ax: matplotlib axes对象
            items: 瀑布图数据项
            colors: 颜色配置
            title: 子图标题
        """
        # 计算累计值
        cumulative = []
        running_total = 0

        for item in items:
            if item.item_type == 'total':
                cumulative.append(0)
                running_total = item.value
            else:
                cumulative.append(running_total)
                if item.item_type == 'increase':
                    running_total += item.value
                else:  # decrease
                    running_total -= abs(item.value)

        # 准备绘图数据
        labels = [item.label for item in items]
        values = [item.value for item in items]

        # 计算条形图高度和底部位置
        heights = []
        bottoms = []

        for item, cum in zip(items, cumulative):
            if item.item_type == 'total':
                heights.append(abs(item.value))
                bottoms.append(0)
            else:
                heights.append(abs(item.value))
                if item.item_type == 'increase':
                    bottoms.append(cum)
                else:  # decrease
                    bottoms.append(cum - abs(item.value))

        # 绘制条形
        x_pos = np.arange(len(labels))
        bar_width = 0.6

        for i, (item, height, bottom) in enumerate(zip(items, heights, bottoms)):
            color = colors.get(item.item_type, '#757575')

            if item.item_type == 'total':
                ax.bar(x_pos[i], height, bar_width,
                      bottom=bottom, color=color,
                      edgecolor='black', linewidth=1.5, alpha=0.9)
            else:
                ax.bar(x_pos[i], height, bar_width,
                      bottom=bottom, color=color,
                      edgecolor='black', linewidth=0.5, alpha=0.8)

        # 添加连接线（不包括最后一项NOI）
        for i in range(len(items) - 2):  # -2 排除最后NOI和倒数第二项的连接
            if items[i].item_type != 'total':
                if items[i].item_type == 'increase':
                    y_start = cumulative[i] + values[i]
                else:
                    y_start = cumulative[i] - abs(values[i])

                ax.plot([x_pos[i] + bar_width/2, x_pos[i+1] - bar_width/2],
                       [y_start, y_start],
                       'k--', linewidth=0.8, alpha=0.5)

        # 添加数值标签
        for i, (item, height, bottom) in enumerate(zip(items, heights, bottoms)):
            value = item.value

            if item.item_type == 'increase':
                y_pos = bottom + height + max(heights) * 0.02
            elif item.item_type == 'decrease':
                y_pos = bottom - max(heights) * 0.05
            else:  # total
                y_pos = height + max(heights) * 0.02

            # 格式化数值
            if abs(value) >= 10000:
                label_text = f'{value/10000:.2f}亿'
            else:
                label_text = f'{value:.0f}'

            if item.item_type == 'increase':
                label_text = f'+{label_text}'
            elif item.item_type == 'decrease':
                label_text = f'-{label_text}'

            ax.text(x_pos[i], y_pos, label_text,
                   ha='center', va='bottom',
                   fontsize=8, fontweight='bold',
                   color='black')

        # 设置样式
        ax.set_xticks(x_pos)
        ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=9)
        ax.set_ylabel('金额（万元）', fontsize=10)
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.yaxis.grid(True, linestyle='--', alpha=0.3)
        ax.set_axisbelow(True)
        ax.axhline(y=0, color='black', linewidth=0.8)
