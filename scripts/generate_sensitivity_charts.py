"""
敏感性分析图表生成
从pipeline结果JSON中读取敏感性分析数据，生成可视化图表
"""

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "sensitivity_charts"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_pipeline_results(path: str = None) -> dict:
    if path is None:
        path = Path(__file__).parent.parent / "output" / "pipeline_results" / "pipeline_full_results.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def plot_tornado(tornado_data: list, base_val: float, save_path: Path):
    fig, ax = plt.subplots(figsize=(12, 5))

    labels = [t["param_name"] for t in tornado_data]
    low_impacts = [t["low_impact"] for t in tornado_data]
    high_impacts = [t["high_impact"] for t in tornado_data]

    y_pos = np.arange(len(labels))

    for i, (lo, hi) in enumerate(zip(low_impacts, high_impacts)):
        left = min(lo, hi, 0)
        right = max(lo, hi, 0)
        color_lo = '#e74c3c' if lo < 0 else '#27ae60'
        color_hi = '#27ae60' if hi > 0 else '#e74c3c'

        if lo < 0:
            ax.barh(i, lo, height=0.5, color=color_lo, alpha=0.85, edgecolor='white')
        else:
            ax.barh(i, lo, height=0.5, color=color_lo, alpha=0.85, edgecolor='white')

        if hi > 0:
            ax.barh(i, hi, height=0.5, color=color_hi, alpha=0.85, edgecolor='white')
        else:
            ax.barh(i, hi, height=0.5, color=color_hi, alpha=0.85, edgecolor='white')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=12)
    ax.axvline(x=0, color='black', linewidth=0.8)
    ax.set_xlabel('估值变化 (万元)', fontsize=11)
    ax.set_title(f'Tornado图 — 参数敏感性分析\n基准估值: {base_val:,.0f} 万元', fontsize=14, fontweight='bold')

    for i, t in enumerate(tornado_data):
        lo_label = t.get("low_label", "")
        hi_label = t.get("high_label", "")
        ax.text(low_impacts[i], i, f' {lo_label} ({low_impacts[i]/base_val*100:+.1f}%)',
                va='center', ha='right' if low_impacts[i] < 0 else 'left', fontsize=9)
        ax.text(high_impacts[i], i, f' {hi_label} ({high_impacts[i]/base_val*100:+.1f}%)',
                va='center', ha='left' if high_impacts[i] > 0 else 'right', fontsize=9)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [OK] Tornado图: {save_path}")


def plot_single_sensitivity(sens_data: dict, save_path: Path, color: str = '#3498db'):
    fig, ax = plt.subplots(figsize=(10, 6))

    param = sens_data["parameter"]
    base_val = sens_data["base_valuation"]
    results = sens_data["results"]

    x = [r["value"] for r in results]
    y = [r["valuation"] for r in results]
    pct = [r["vs_base_pct"] for r in results]

    ax.plot(x, y, 'o-', color=color, linewidth=2, markersize=8)
    ax.axhline(y=base_val, color='gray', linestyle='--', linewidth=1, label=f'基准估值 {base_val:,.0f}')

    display_map = {"discount_rate": "折现率", "fixed_growth": "固定增长率", "noicf_adjustment": "NOI/CF调整系数"}
    display_name = display_map.get(param, param)

    for xi, yi, pi in zip(x, y, pct):
        label = f'{pi:+.1f}%' if abs(pi) > 0.5 else ''
        if label:
            ax.annotate(label, (xi, yi), textcoords="offset points",
                       xytext=(0, 12), ha='center', fontsize=9, color='#555')

    if param == "discount_rate":
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.2%}'))
    elif param == "noicf_adjustment":
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.0%}'))
    else:
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.1%}'))

    ax.set_xlabel(display_name, fontsize=12)
    ax.set_ylabel('估值 (万元)', fontsize=12)
    ax.set_title(f'单变量敏感性分析 — {display_name}', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [OK] 单变量敏感性 ({display_name}): {save_path}")


def plot_two_way_heatmap(two_way: dict, save_path: Path):
    fig, ax = plt.subplots(figsize=(10, 7))

    table = np.array(two_way["table"])
    v1 = two_way["values1"]
    v2 = two_way["values2"]
    base = two_way["base_valuation"]

    pct_table = (table - base) / base * 100

    cmap = plt.cm.RdYlGn
    im = ax.imshow(pct_table, cmap=cmap, aspect='auto')
    cbar = plt.colorbar(im, ax=ax, label='估值变化 (%)')

    ax.set_xticks(range(len(v2)))
    ax.set_xticklabels([f'{v:.1%}' for v in v2], fontsize=10)
    ax.set_yticks(range(len(v1)))
    ax.set_yticklabels([f'{v:.2%}' for v in v1], fontsize=10)

    for i in range(len(v1)):
        for j in range(len(v2)):
            val = table[i][j]
            pct = pct_table[i][j]
            text_color = 'white' if abs(pct) > 15 else 'black'
            ax.text(j, i, f'{val/10000:.2f}亿\n({pct:+.1f}%)',
                   ha='center', va='center', fontsize=8, color=text_color)

    d1 = two_way.get("param1_display", two_way["param1"])
    d2 = two_way.get("param2_display", two_way["param2"])
    ax.set_xlabel(d2, fontsize=12)
    ax.set_ylabel(d1, fontsize=12)
    ax.set_title(f'双变量敏感性分析 — {d1} vs {d2}\n基准: {base:,.0f} 万元 ({base/10000:.2f} 亿元)',
                fontsize=13, fontweight='bold')

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [OK] 双变量热力图: {save_path}")


def plot_stress_test(stress_data: dict, save_path: Path):
    fig, ax = plt.subplots(figsize=(10, 6))

    base = stress_data["base_valuation"]
    scenarios = stress_data["scenarios"]

    names = ["基准"] + [s["name"] for s in scenarios]
    vals = [base] + [s["valuation"] for s in scenarios]
    colors = ['#3498db'] + ['#27ae60' if s["vs_base"] > 0 else '#e74c3c' for s in scenarios]

    bars = ax.bar(names, vals, color=colors, alpha=0.85, edgecolor='white', width=0.6)

    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + base * 0.005,
               f'{val/10000:.2f}亿', ha='center', va='bottom', fontsize=11, fontweight='bold')

    for i, s in enumerate(scenarios, 1):
        pct = s["vs_base_pct"]
        ax.text(i, vals[i] - base * 0.02,
               f'{pct:+.1f}%', ha='center', va='top', fontsize=10, color='white', fontweight='bold')

    ax.axhline(y=base, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax.set_ylabel('估值 (万元)', fontsize=12)
    ax.set_title('压力测试结果', fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [OK] 压力测试: {save_path}")


def plot_waterfall(stress_data: dict, save_path: Path):
    fig, axes = plt.subplots(1, len(stress_data["scenarios"]), figsize=(5 * len(stress_data["scenarios"]), 6))
    if len(stress_data["scenarios"]) == 1:
        axes = [axes]

    for ax, scenario in zip(axes, stress_data["scenarios"]):
        wf = scenario.get("waterfall", {})
        steps = wf.get("steps", [])
        base = wf.get("base_valuation", 0)
        final = wf.get("final_valuation", 0)

        labels = ["基准"] + [s["factor"] for s in steps] + ["最终"]
        values = [base]
        running = base
        bottoms = [0]
        colors_list = ['#3498db']

        for s in steps:
            impact = s["valuation_impact"]
            values.append(abs(impact))
            bottoms.append(running + impact if impact < 0 else running)
            if impact < 0:
                bottoms[-1] = running + impact
            colors_list.append('#27ae60' if impact > 0 else '#e74c3c')
            running += impact

        values.append(final)
        bottoms.append(0)
        colors_list.append('#9b59b6')

        bars = ax.bar(labels, values, bottom=bottoms, color=colors_list, alpha=0.85, width=0.6, edgecolor='white')

        for bar, val, bot in zip(bars, values, bottoms):
            total = bot + val
            ax.text(bar.get_x() + bar.get_width()/2, total + base * 0.005,
                   f'{total/10000:.2f}亿', ha='center', va='bottom', fontsize=8)

        ax.set_title(f'{scenario["name"]}\n({scenario.get("vs_base_pct", 0):+.1f}%)', fontsize=11, fontweight='bold')
        ax.set_ylabel('估值 (万元)', fontsize=10)
        ax.tick_params(axis='x', rotation=30)
        ax.grid(axis='y', alpha=0.3)

    plt.suptitle('Waterfall瀑布图 — 差异分解', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  [OK] Waterfall瀑布图: {save_path}")


def main(results_path: str = None):
    print("=" * 60)
    print("敏感性分析图表生成")
    print("=" * 60)

    data = load_pipeline_results(results_path)
    sens = data.get("step4_sensitivity", {})

    if not sens:
        print("[ERROR] 未找到敏感性分析数据")
        return

    base_val = sens.get("base_valuation", 0)
    print(f"基准估值: {base_val:,.0f} 万元 ({base_val/10000:.2f} 亿元)\n")

    tornado = sens.get("tornado", [])
    if tornado:
        plot_tornado(tornado, base_val, OUTPUT_DIR / "01_tornado.png")

    for key, color, fname in [
        ("discount_rate_sensitivity", "#e74c3c", "02_sensitivity_discount_rate.png"),
        ("growth_sensitivity", "#27ae60", "03_sensitivity_growth.png"),
        ("noicf_sensitivity", "#3498db", "04_sensitivity_noicf.png"),
    ]:
        if key in sens and sens[key]:
            plot_single_sensitivity(sens[key], OUTPUT_DIR / fname, color)

    two_way = sens.get("two_way_table", {})
    if two_way:
        plot_two_way_heatmap(two_way, OUTPUT_DIR / "05_two_way_heatmap.png")

    stress = sens.get("stress_test", {})
    if stress:
        plot_stress_test(stress, OUTPUT_DIR / "06_stress_test.png")
        plot_waterfall(stress, OUTPUT_DIR / "07_waterfall.png")

    print(f"\n图表已保存至: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    main(path)
