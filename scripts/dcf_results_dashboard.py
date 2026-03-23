"""
DCF结果实时看板 - 直接读取最新Pipeline输出
运行: streamlit run scripts/dcf_results_dashboard.py --server.port 8502
"""
import streamlit as st
import json
import os
from datetime import datetime
from pathlib import Path

st.set_page_config(page_title="DCF建模结果看板", layout="wide", page_icon="📊")

# 查找最新结果
RESULTS_DIR = Path("output/huazhu")

def find_latest_run():
    """找到最新的run目录"""
    runs = sorted([d for d in RESULTS_DIR.glob("run_*") if d.is_dir()], reverse=True)
    return runs[0] if runs else None

# 加载数据
latest_dir = find_latest_run()
if not latest_dir:
    st.error("未找到运行结果")
    st.stop()

with open(latest_dir / "pipeline_results.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 页面标题
st.title("🏨 华住安住REIT - DCF建模结果")
st.caption(f"运行时间: {latest_dir.name.replace('run_', '')}")

# 关键指标
st.header("📈 关键指标")

col1, col2, col3, col4 = st.columns(4)

dcf_results = data.get("step3_dcf", {}).get("dcf_results", {})
total_val = dcf_results.get("total_valuation", 0) / 10000  # 转换为亿元
total_noi = dcf_results.get("total_noi_year1", 0) / 10000

with col1:
    st.metric("总估值", f"{total_val:.2f}亿元")
with col2:
    st.metric("首年NOI", f"{total_noi:.2f}亿元")
with col3:
    # 招募说明书估值对比
    prospectus_val = 15.90  # 亿元
    diff_pct = (total_val - prospectus_val) / prospectus_val * 100
    st.metric("vs 招募说明书", f"{diff_pct:+.1f}%", delta=f"{total_val-prospectus_val:.2f}亿")
with col4:
    cap_rate = dcf_results.get("implied_cap_rate", 0) * 100
    st.metric("隐含Cap Rate", f"{cap_rate:.2f}%")

# 项目明细
st.header("📋 项目明细")

projects = dcf_results.get("projects", [])
for proj in projects:
    with st.expander(f"**{proj['name']}** - {proj['valuation']/10000:.2f}亿元"):
        cols = st.columns(3)
        with cols[0]:
            st.write("**NOI**")
            st.write(f"Y1 NOI: {proj['base_noi']/10000:.2f}亿元")
            st.write(f"NOI来源: {proj.get('noi_source', 'unknown')}")
        with cols[1]:
            st.write("**估值参数**")
            st.write(f"折现率: {proj.get('discount_rate', 0)*100:.2f}%")
            st.write(f"收益期: {proj.get('remaining_years', 0):.1f}年")
        with cols[2]:
            st.write("**验证**")
            validation = proj.get('validation', {})
            noi_diff = validation.get('noi_diff_pct', 0)
            st.write(f"NOI差异: {noi_diff:+.1f}%")
            if abs(noi_diff) <= 5:
                st.success("✓ PASS")
            else:
                st.warning(f"⚠ 差异 {noi_diff:+.1f}%")

# 敏感性图表
st.header("📊 敏感性分析")

chart_dir = latest_dir / "charts"
chart_files = [
    ("龙卷风图", "sensitivity_tornado.png"),
    ("折现率敏感性", "sensitivity_discount_rate.png"),
    ("增长率敏感性", "sensitivity_growth.png"),
    ("NOI/CF敏感性", "sensitivity_noicf.png"),
    ("双因素热力图", "sensitivity_two_way.png"),
    ("压力测试", "sensitivity_stress_test.png"),
]

for name, filename in chart_files:
    chart_path = chart_dir / filename
    if chart_path.exists():
        with st.expander(name):
            st.image(str(chart_path), use_container_width=True)

# 原始JSON查看
st.header("🔍 原始数据")
with st.expander("查看完整JSON"):
    st.json(data)
