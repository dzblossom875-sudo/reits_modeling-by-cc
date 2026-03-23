"""
NOI推导过程可视化 Dashboard
对比历史数据、推导数据、招募说明书数据的差异
运行方式: streamlit run scripts/noi_dashboard.py
"""
import os
import json
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)

# ── 1. 页面配置 ──────────────────────────────────────────────
st.set_page_config(page_title="NOI推导对比分析", layout="wide", page_icon="🏨")

st.sidebar.header("🎨 视觉设置")
theme_mode = st.sidebar.radio("配色方案", ["Cloud Blue", "平安集团"], index=0)
project_sel = st.sidebar.radio("项目选择", ["广州项目", "上海项目", "两者对比"], index=0)

if theme_mode == "Cloud Blue":
    bg_color     = "#f2f6fb"
    text_color   = "#0a1428"
    grid_color   = "rgba(26,74,128,0.10)"
    template     = "plotly_white"
    c_hist       = "#4a78b8"      # 历史均值 - steel blue
    c_calc       = "#1a6ca0"      # 推导值 - dark blue
    c_prosp      = "#00806a"      # 招募值 - teal
    c_pos        = "#1a4a80"
    c_neg        = "#c85a00"
    metric_color = "#1a4a80"
    yr_colors    = ["#d0e4f7", "#7db3e0", "#1a4a80"]  # 2023/2024/2025
else:
    bg_color     = "#F8F6F4"
    text_color   = "#1A1A1A"
    grid_color   = "rgba(0,0,0,0.08)"
    template     = "plotly_white"
    c_hist       = "#909090"
    c_calc       = "#F04E23"
    c_prosp      = "#007D5E"
    c_pos        = "#007D5E"
    c_neg        = "#C83800"
    metric_color = "#F04E23"
    yr_colors    = ["#f5c6b8", "#f0956e", "#F04E23"]

st.markdown(f"""
<style>
.main .block-container {{max-width:1400px; padding-top:1.2rem; margin:0 auto;}}
[data-testid="stMetricValue"] {{font-size:1.6rem; color:{metric_color}; font-weight:700;}}
.stMetric {{background:{bg_color}; padding:12px; border-radius:8px; border:1px solid {grid_color};}}
</style>""", unsafe_allow_html=True)

# ── 2. 数据加载 ───────────────────────────────────────────────
@st.cache_data
def load_data():
    hist_path  = os.path.join(_ROOT, "output", "historical_financial_3years.json")
    calc_path  = os.path.join(_ROOT, "output", "noi_comparison_report.json")
    cmp_path   = os.path.join(_ROOT, "output", "dcf_noi_comparison.json")

    with open(hist_path, encoding="utf-8") as f:
        hist = json.load(f)
    with open(calc_path, encoding="utf-8") as f:
        calc = json.load(f)
    with open(cmp_path, encoding="utf-8") as f:
        cmp  = json.load(f)
    return hist, calc, cmp

hist_data, calc_data, cmp_data = load_data()

# ── 3. 数据整理助手 ───────────────────────────────────────────
def get_hist_years(proj_key):
    """返回 {科目: {2023:x, 2024:x, 2025:x, 3年均:x}}"""
    d = hist_data[proj_key]
    result = {}
    for k, v in d.items():
        row = {}
        for yr in ["2023", "2024", "2025"]:
            row[yr] = v.get(yr, None)
        row["3年均"] = v.get("3年平均", None)
        result[k] = row
    return result

def get_calc_proj(proj_name):
    """从 noi_comparison_report 拿到对应项目的详细推导数据"""
    for p in calc_data["projects"]:
        if proj_name in p["project_name"]:
            return p["detailed_calculations"]
    return {}

def get_prosp_proj(proj_key):
    """从 dcf_noi_comparison 拿招募说明书2026年预测"""
    return cmp_data.get("2026年预测(招募说明书)", {}).get(proj_key, {})

# ── 4. 构建对比 DataFrame ─────────────────────────────────────
def build_compare_df(proj_key, proj_name):
    hist = get_hist_years(proj_key)
    calc = get_calc_proj(proj_name)
    prosp = get_prosp_proj(proj_key)

    dc = calc  # shorthand

    rows = []

    def row(label, h_key, calc_val, prosp_val, unit="万元", section=""):
        h = hist.get(h_key, {})
        rows.append({
            "科目": label,
            "分类": section,
            "2023": h.get("2023"),
            "2024": h.get("2024"),
            "2025": h.get("2025"),
            "历史3年均": h.get("3年均"),
            "推导值": calc_val,
            "招募预测": prosp_val,
            "单位": unit,
        })

    # 收入
    row("营业收入(含税)", "营业收入",
        dc.get("total_income", {}).get("calculated"),
        prosp.get("营业收入"),
        section="收入")
    row("  客房收入", None,
        dc.get("room_revenue", {}).get("calculated"),
        None, section="收入")
    row("  餐饮收入", None,
        dc.get("fb_revenue", {}).get("calculated"),
        None, section="收入")
    row("  其他收入", None,
        dc.get("other_revenue", {}).get("calculated"),
        None, section="收入")
    row("  商业收入", None,
        dc.get("commercial_revenue", {}).get("calculated"),
        None, section="收入")

    # 运营成本
    exp = dc.get("operating_expenses", {})
    exp_detail = exp.get("detail", {})
    row("运营成本合计", "运营成本(不含折旧)",
        exp.get("total_calculated"),
        prosp.get("营业成本"),
        section="成本")
    for k, v in exp_detail.items():
        row(f"  {v['name']}", None, v.get("value"), None, section="成本")
    row("  物业管理费", None,
        dc.get("property_expense", {}).get("calculated"),
        None, section="成本")
    row("  保险费", None,
        dc.get("insurance", {}).get("calculated") or dc.get("insurance", {}).get("value"),
        None, section="成本")

    # 税费
    tax = dc.get("tax_total", {})
    row("税金及附加", "税金及附加",
        tax.get("calculated"),
        prosp.get("税金及附加"),
        section="税费")
    tv = dc.get("tax_vat", {})
    row("  增值税附加", None, tv.get("surcharge"), None, section="税费")
    row("  房产税", None, dc.get("tax_property", {}).get("total"), None, section="税费")
    row("  土地使用税", None, dc.get("tax_land", {}).get("total"), None, section="税费")

    # GOP & 管理费
    mgmt = dc.get("management_fee", {})
    row("GOP", "GOP(息税折旧前)",
        mgmt.get("gop"),
        None, section="利润")
    row("管理费(GOP×3%)", "管理费用",
        mgmt.get("calculated"),
        prosp.get("管理费用"),
        section="利润")

    # NOI & Capex & FCF
    noi_calc = dc.get("noi", {}).get("calculated")
    capex_calc = dc.get("capex", {}).get("value")
    fcf_calc = (noi_calc - capex_calc) if noi_calc and capex_calc else None
    row("NOI", None, noi_calc, None, section="NOI")
    row("资本性支出(Capex)", None, capex_calc, prosp.get("资本性支出"), section="NOI")
    row("年净收益(FCF)", "经营活动现金流",
        fcf_calc,
        prosp.get("年净收益"),
        section="NOI")

    return pd.DataFrame(rows)


# ── 5. 瀑布图 ─────────────────────────────────────────────────
def make_waterfall(proj_key, proj_name, data_source="推导值"):
    dc = get_calc_proj(proj_name)
    prosp = get_prosp_proj(proj_key)
    hist_avg = hist_data[proj_key]

    def v(key, sub=None, fallback=None):
        if sub:
            return dc.get(key, {}).get(sub, fallback) or fallback
        return dc.get(key, fallback) or fallback

    if data_source == "推导值":
        revenue    = v("total_income", "calculated", 0)
        op_exp     = v("operating_expenses", "total_calculated", 0)
        prop_exp   = v("property_expense", "calculated", 0)
        insurance  = v("insurance", "calculated") or v("insurance", "value", 0)
        taxes      = v("tax_total", "calculated", 0)
        mgmt_fee   = v("management_fee", "calculated", 0)
        capex      = v("capex", "value", 0)
        noi        = v("noi", "calculated", 0)
    elif data_source == "招募预测":
        revenue  = prosp.get("营业收入", 0)
        op_exp   = prosp.get("营业成本", 0)
        prop_exp = 0
        insurance = 0
        taxes    = prosp.get("税金及附加", 0)
        mgmt_fee = prosp.get("管理费用", 0)
        capex    = prosp.get("资本性支出", 0)
        noi      = prosp.get("年净收益", 0) + capex  # back-calc NOI
    else:  # 历史3年均
        hd = {k: v2.get("3年平均", 0) for k, v2 in hist_avg.items()}
        revenue  = hd.get("营业收入", 0)
        op_exp   = hd.get("运营成本(不含折旧)", 0)
        prop_exp = 0
        insurance = 0
        taxes    = hd.get("税金及附加", 0)
        mgmt_fee = hd.get("管理费用", 0)
        capex    = 0
        noi      = hd.get("GOP(息税折旧前)", 0) - mgmt_fee

    fcf = noi - capex

    labels = ["营业收入", "运营成本", "物业费+保险", "税金及附加", "管理费(GOP×3%)", "NOI", "Capex", "年净收益"]
    measures = ["absolute", "relative", "relative", "relative", "relative", "total", "relative", "total"]
    values = [revenue, -op_exp, -(prop_exp + insurance), -taxes, -mgmt_fee, 0, -capex, 0]
    # fix totals
    values[5] = noi
    values[7] = fcf

    colors_pos = c_pos
    colors_neg = c_neg

    fig = go.Figure(go.Waterfall(
        name=data_source,
        orientation="v",
        measure=measures,
        x=labels,
        y=values,
        connector={"line": {"color": grid_color, "width": 1.5}},
        increasing={"marker": {"color": colors_pos}},
        decreasing={"marker": {"color": colors_neg}},
        totals={"marker": {"color": "#8b5cf6"}},
        texttemplate="%{y:,.0f}",
        textposition="outside",
    ))
    fig.update_layout(
        template=template,
        height=420,
        margin=dict(t=30, b=20, l=10, r=10),
        yaxis_title="万元",
        font=dict(size=11, color=text_color),
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
    )
    return fig


# ── 6. 三方对比柱状图 ─────────────────────────────────────────
def make_bar_compare(proj_key, proj_name):
    df = build_compare_df(proj_key, proj_name)
    # 只取关键科目
    key_items = ["营业收入(含税)", "运营成本合计", "税金及附加", "管理费(GOP×3%)", "NOI", "资本性支出(Capex)", "年净收益(FCF)"]
    dff = df[df["科目"].isin(key_items)].copy()

    fig = go.Figure()
    fig.add_bar(name="历史3年均", x=dff["科目"], y=dff["历史3年均"],
                marker_color=c_hist, opacity=0.85)
    fig.add_bar(name="推导值", x=dff["科目"], y=dff["推导值"],
                marker_color=c_calc, opacity=0.85)
    fig.add_bar(name="招募预测2026", x=dff["科目"], y=dff["招募预测"],
                marker_color=c_prosp, opacity=0.85)
    fig.update_layout(
        barmode="group",
        template=template,
        height=400,
        margin=dict(t=20, b=60, l=10, r=10),
        yaxis_title="万元",
        legend=dict(orientation="h", y=1.05),
        font=dict(size=11, color=text_color),
        plot_bgcolor=bg_color,
        paper_bgcolor=bg_color,
    )
    return fig


# ── 7. 历史年度趋势 ───────────────────────────────────────────
def make_hist_trend(proj_key, proj_name):
    hd = hist_data[proj_key]
    years = ["2023", "2024", "2025"]
    metrics = ["营业收入", "GOP(息税折旧前)", "经营活动现金流"]
    labels  = ["营业收入", "GOP", "经营现金流"]

    prosp = get_prosp_proj(proj_key)
    dc    = get_calc_proj(proj_name)

    fig = make_subplots(rows=1, cols=3,
                        subplot_titles=["营业收入趋势", "GOP趋势", "现金流趋势"])
    for col_i, (metric, label) in enumerate(zip(metrics, labels), start=1):
        yvals = [hd[metric].get(yr) for yr in years]
        fig.add_scatter(row=1, col=col_i, x=years, y=yvals,
                        mode="lines+markers+text", name=f"历史{label}",
                        line=dict(color=yr_colors[-1], width=2),
                        marker=dict(size=7),
                        text=[f"{v:,.0f}" if v else "" for v in yvals],
                        textposition="top center",
                        textfont=dict(size=9),
                        showlegend=(col_i == 1))

        # 招募预测点 (2026)
        pv_map = {"营业收入": prosp.get("营业收入"), "GOP(息税折旧前)": None,
                  "经营活动现金流": prosp.get("年净收益")}
        pv = pv_map[metric]
        if pv:
            fig.add_scatter(row=1, col=col_i, x=["2026预测"], y=[pv],
                            mode="markers+text", name="招募预测",
                            marker=dict(color=c_prosp, size=10, symbol="diamond"),
                            text=[f"{pv:,.0f}"], textposition="top center",
                            textfont=dict(size=9),
                            showlegend=(col_i == 1))

    fig.update_layout(
        template=template, height=340,
        margin=dict(t=50, b=20, l=10, r=10),
        font=dict(size=10, color=text_color),
        plot_bgcolor=bg_color, paper_bgcolor=bg_color,
        legend=dict(orientation="h", y=-0.15),
    )
    return fig


# ── 8. 收入/成本结构饼图 ──────────────────────────────────────
def make_structure_pie(proj_name, which="revenue"):
    dc = get_calc_proj(proj_name)
    if which == "revenue":
        labels = ["客房收入", "餐饮收入", "其他收入", "商业收入"]
        values = [
            dc.get("room_revenue", {}).get("calculated", 0),
            dc.get("fb_revenue", {}).get("calculated", 0),
            dc.get("other_revenue", {}).get("calculated", 0),
            dc.get("commercial_revenue", {}).get("calculated", 0),
        ]
        title = "收入结构（推导值）"
    else:
        exp = dc.get("operating_expenses", {}).get("detail", {})
        labels = [v["name"] for v in exp.values()]
        values = [v.get("value", 0) for v in exp.values()]
        labels += ["物业管理费", "保险费"]
        values += [
            dc.get("property_expense", {}).get("calculated", 0),
            dc.get("insurance", {}).get("calculated") or dc.get("insurance", {}).get("value", 0),
        ]
        title = "运营成本结构（推导值）"

    palette = [c_pos, c_prosp, c_hist, c_neg, "#8b5cf6", "#d4a000",
               "#006080", "#c83060", "#3a8040", "#804020", "#205080"]
    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.38,
        marker_colors=palette[:len(labels)],
        textinfo="label+percent",
        textfont_size=10,
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color=text_color)),
        template=template, height=320,
        margin=dict(t=40, b=10, l=10, r=10),
        paper_bgcolor=bg_color,
        showlegend=False,
    )
    return fig


# ── 9. 详细对比表格 ───────────────────────────────────────────
def render_table(proj_key, proj_name):
    df = build_compare_df(proj_key, proj_name)

    def fmt(v):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return "—"
        return f"{v:,.1f}"

    def diff_fmt(calc, prosp):
        if calc is None or prosp is None:
            return "—", ""
        d = calc - prosp
        pct = d / prosp * 100 if prosp else 0
        arrow = "▲" if d > 0 else "▼" if d < 0 else "—"
        color = c_neg if d > 50 else (c_pos if d < -50 else text_color)
        return f"{arrow} {abs(d):,.1f} ({pct:+.1f}%)", color

    # 分节渲染
    sections = ["收入", "成本", "税费", "利润", "NOI"]
    section_names = {"收入": "📊 收入明细", "成本": "📦 运营成本",
                     "税费": "🧾 税金及附加", "利润": "📈 GOP & 管理费", "NOI": "💰 NOI & FCF"}

    for sec in sections:
        sec_df = df[df["分类"] == sec]
        if sec_df.empty:
            continue
        st.markdown(f"**{section_names[sec]}**")

        header = ["科目", "2023", "2024", "2025", "历史3年均", "推导值", "招募预测", "差异(推导-招募)"]
        table_rows = []
        for _, r in sec_df.iterrows():
            diff_str, _ = diff_fmt(r["推导值"], r["招募预测"])
            table_rows.append({
                "科目": r["科目"],
                "2023": fmt(r["2023"]),
                "2024": fmt(r["2024"]),
                "2025": fmt(r["2025"]),
                "历史3年均": fmt(r["历史3年均"]),
                "推导值": fmt(r["推导值"]),
                "招募预测": fmt(r["招募预测"]),
                "差异": diff_str,
            })
        st.dataframe(
            pd.DataFrame(table_rows).rename(columns={"差异": "差异(推导-招募)"}),
            use_container_width=True, hide_index=True
        )


# ── 10. 单项目页面 ────────────────────────────────────────────
def render_project(proj_key, proj_name, short):
    dc    = get_calc_proj(proj_name)
    prosp = get_prosp_proj(proj_key)
    hd    = hist_data[proj_key]

    noi_calc  = dc.get("noi", {}).get("calculated", 0) or 0
    capex_val = dc.get("capex", {}).get("value", 0) or 0
    fcf_calc  = noi_calc - capex_val
    noi_prosp = (prosp.get("年净收益", 0) or 0) + (prosp.get("资本性支出", 0) or 0)
    fcf_prosp = prosp.get("年净收益", 0) or 0
    noi_hist  = hd.get("GOP(息税折旧前)", {}).get("3年平均", 0) or 0
    rev_hist  = hd.get("营业收入", {}).get("3年平均", 0) or 0
    rev_calc  = dc.get("total_income", {}).get("calculated", 0) or 0
    rev_prosp = prosp.get("营业收入", 0) or 0

    st.subheader(f"{'🏨'} {short} — 关键指标")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("历史均值NOI(GOP口径)", f"{noi_hist:,.0f} 万元")
    c2.metric("推导NOI", f"{noi_calc:,.0f} 万元",
              f"{(noi_calc-noi_hist)/noi_hist*100:+.1f}% vs 历史" if noi_hist else None)
    c3.metric("招募预测NOI", f"{noi_prosp:,.0f} 万元",
              f"{(noi_prosp-noi_hist)/noi_hist*100:+.1f}% vs 历史" if noi_hist else None)
    c4.metric("推导年净收益(FCF)", f"{fcf_calc:,.0f} 万元")
    c5.metric("招募预测年净收益", f"{fcf_prosp:,.0f} 万元",
              f"{(fcf_calc-fcf_prosp)/fcf_prosp*100:+.1f}% 推导vs招募" if fcf_prosp else None)

    st.markdown("---")

    # 瀑布图 + 三方柱状图
    col_a, col_b = st.columns([1, 1])
    with col_a:
        wf_src = st.selectbox("瀑布图数据源", ["推导值", "招募预测", "历史3年均"],
                              key=f"wf_{proj_key}")
        st.plotly_chart(make_waterfall(proj_key, proj_name, wf_src),
                        use_container_width=True)
    with col_b:
        st.markdown("**三方对比（关键科目）**")
        st.plotly_chart(make_bar_compare(proj_key, proj_name), use_container_width=True)

    # 历史趋势
    st.markdown("**历史年度趋势 + 2026预测**")
    st.plotly_chart(make_hist_trend(proj_key, proj_name), use_container_width=True)

    # 结构饼图
    col_c, col_d = st.columns(2)
    with col_c:
        st.plotly_chart(make_structure_pie(proj_name, "revenue"), use_container_width=True)
    with col_d:
        st.plotly_chart(make_structure_pie(proj_name, "cost"), use_container_width=True)

    # 详细表格
    st.markdown("---")
    st.subheader("📋 逐项明细对比（万元）")
    render_table(proj_key, proj_name)


# ── 11. 双项目对比页面 ────────────────────────────────────────
def render_dual():
    projects = [("广州项目", "广州", "广州"), ("上海项目", "上海", "上海")]

    # Summary metrics
    st.subheader("📊 双项目汇总对比")
    cols = st.columns(4)
    total_fcf_calc = total_fcf_prosp = 0
    for i, (pkey, pname, short) in enumerate(projects):
        dc    = get_calc_proj(pname)
        prosp = get_prosp_proj(pkey)
        noi   = dc.get("noi", {}).get("calculated", 0) or 0
        capex = dc.get("capex", {}).get("value", 0) or 0
        fcf   = noi - capex
        fp    = prosp.get("年净收益", 0) or 0
        total_fcf_calc  += fcf
        total_fcf_prosp += fp
        cols[i*2].metric(f"{short} 推导FCF", f"{fcf:,.0f} 万元")
        cols[i*2+1].metric(f"{short} 招募FCF", f"{fp:,.0f} 万元",
                           f"{(fcf-fp)/fp*100:+.1f}%" if fp else None)

    st.markdown("---")
    col_gz, col_sh = st.columns(2)
    with col_gz:
        st.markdown("### 广州项目 (美居+全季, 776间)")
        st.plotly_chart(make_waterfall("广州项目", "广州", "推导值"), use_container_width=True)
        st.plotly_chart(make_hist_trend("广州项目", "广州"), use_container_width=True)
    with col_sh:
        st.markdown("### 上海项目 (桔子水晶, 268间)")
        st.plotly_chart(make_waterfall("上海项目", "上海", "推导值"), use_container_width=True)
        st.plotly_chart(make_hist_trend("上海项目", "上海"), use_container_width=True)

    # Side-by-side bar
    st.markdown("**广州 vs 上海 — 关键指标对比**")
    items = ["营业收入(含税)", "运营成本合计", "税金及附加", "NOI", "年净收益(FCF)"]
    fig = go.Figure()
    for pkey, pname, short in projects:
        df = build_compare_df(pkey, pname)
        dff = df[df["科目"].isin(items)]
        fig.add_bar(name=f"{short}·推导", x=dff["科目"], y=dff["推导值"], opacity=0.85)
        fig.add_bar(name=f"{short}·招募", x=dff["科目"], y=dff["招募预测"],
                    opacity=0.6, marker_pattern_shape="/")
    fig.update_layout(barmode="group", template=template, height=380,
                      margin=dict(t=20, b=60, l=10, r=10),
                      yaxis_title="万元",
                      legend=dict(orientation="h", y=1.05),
                      font=dict(size=11, color=text_color),
                      plot_bgcolor=bg_color, paper_bgcolor=bg_color)
    st.plotly_chart(fig, use_container_width=True)


# ── 12. 主渲染 ────────────────────────────────────────────────
st.title("🏨 华住安住REIT — NOI推导过程对比分析")
st.caption("对比维度：历史财务数据（2023-2025）｜推导NOI（参数计算值）｜招募说明书预测（2026年）")

if project_sel == "广州项目":
    render_project("广州项目", "广州", "广州项目（美居+全季 · 776间）")
elif project_sel == "上海项目":
    render_project("上海项目", "上海", "上海项目（桔子水晶 · 268间）")
else:
    render_dual()
