"""
可视化图表生成器
生成估值相关的图表
"""

from typing import Dict, List, Any, Optional
from pathlib import Path

try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # 使用非交互式后端
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from ..core.types import ValuationResult, ScenarioResult
from ..core.exceptions import ExportError


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
