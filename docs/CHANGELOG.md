# CHANGELOG

---

## 2026-03-23 (续)

### feat: 新增NOI推导对比可视化Dashboard
- **文件**: `scripts/noi_dashboard.py`（新建）
- **功能**: Streamlit交互式Dashboard，三方数据源对比（历史3年均值 / 推导值 / 招募说明书预测）
  - 关键指标卡：历史均值NOI、推导NOI、招募预测NOI、FCF及差异率
  - 瀑布图：收入→运营成本→物业保险→税费→管理费→NOI→Capex→FCF，可切换三种数据源
  - 三方柱状图：关键科目并排对比
  - 历史趋势：2023-2025折线+2026招募预测点
  - 结构饼图：收入结构/运营成本结构
  - 逐项明细表：含历史3年+推导+招募+差异列，按5个分类分节展示
  - 两者对比模式：广州/上海并排瀑布图+汇总柱状图
- **主题**: 支持Cloud Blue / 平安集团双配色，项目可选广州/上海/两者对比
- **数据源**: `output/historical_financial_3years.json` + `output/noi_comparison_report.json` + `output/dcf_noi_comparison.json`
- **运行**: `streamlit run scripts/noi_dashboard.py`，访问 http://localhost:8501

---

## 2026-03-23

### fix: 修正商业REIT Mall NOI引擎增值税双重扣除
- **文件**: `src/models/mall/noi_engine.py`
- **问题**: 收入已按不含税口径列示，但`total_tax`中仍包含`vat_total`，导致增值税被双重扣除
- **根因**: 增值税为价外税（价税分离），不含税收入已是税后净额，VAT为纯过路资金，不应计入成本
- **修正**: `total_tax`移除`vat_total`，仅保留`vat_surtax`（附加税=VAT×12%）为真实税负
- **验证**: Y1 FCF 57,419→63,446万；模型估值 786,384→868,036万；报告差异从-14.6%→-5.7%

### feat: 新增商业购物中心REITs参数提取模板
- **文件**: `src/parsers/mall_template.py`（新建）
- **内容**: 完整商业REIT参数提取模板，6个Tier层级，54个字段
  - Tier1: 基础信息（GLA/停车位/土地年限/开业期数）
  - Tier2: 租户结构（出租率/收缴率/一二期分摊/业态拆分）
  - Tier3: 收入参数（Y1各科目/增长率计划/翻新假设）
  - Tier4: 成本税金（各成本比率/增值税处理规则/附加税）
  - Tier5: 估值参数（折现率/收益期/报告估值/Capex验证）
  - Tier6: 历史数据（近3年各科目）
- **用途**: 后续商业REIT项目参数提取的标准化checklist

---

## 2026-03-19

### feat: 完成历史财务对比可视化与NOI引擎修复（酒店REIT）
- 参见 `docs/lessons-learned.md` 条目1-10

