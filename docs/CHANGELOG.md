# CHANGELOG

---

## 2026-03-24 (main.py Pipeline修复)

### fix: 修复 --pipeline 参数直接运行
- **Commit**: 待提交
- **问题**: `main.py --pipeline` 未指定 `--data` 时进入交互模式，而非直接运行
- **修复**:
  - 调整参数优先级判断，使 `--pipeline` 可自动从项目配置获取数据路径
  - 修正 `HotelREITsPipeline` 参数名 `output_dir` → `output_base`
- **运行方式**:
  ```bash
  python main.py --project huazhu --pipeline
  ```
- **验证结果**:
  - 广州项目NOI差异-4.1% [PASS]
  - 上海项目NOI差异-12.0% [差异]
  - 总估值: 138,213.48万元 (13.82亿元)
  - 生成6张敏感性分析图表

---

## 2026-03-24 (文档体系完善)

### docs: 创建核心项目文档体系
- **Commit**: `fb31ecc`
- **新增文档**:
  - `docs/summary.md` - 最终结论快照
    - 项目架构最终版目录结构
    - 完整输出文件清单（DCF结果/敏感性图表/财务对比/校验结果）
    - 最佳实践（项目启动/多业态测试/敏感性分析/NOI Dashboard）
    - 避坑指南精简版（数据提取/建模/综合体特殊注意）
    - 核心公式（酒店REIT + 商业REIT）
    - 架构演进记录（Phase 1-4）
    - 快速参考（重要阈值/关键文件路径）
  - `docs/workflow.md` - 工作流程与数据流
    - 标准4阶段流程（参数提取→确认→建模→比对审计）
    - 多业态项目流程（综合体特殊处理）
    - 详细数据流图（酒店/Mall/多业态合并）
    - 项目配置切换流程（4种方式）
    - 质量门禁（参数提取/建模/输出阶段检查项）
    - 调试工作流程
    - 文件命名规范
    - 常见问题排查指南
  - `docs/decisions.md` - 关键决策记录
    - 10项架构与建模决策（背景/选项分析/最终选择/违反后果）
    - 包括：项目隔离/多业态架构/NOI策略/增值税/成本口径/管理费/折现约定/输出管理/参数提取/回退机制

---

## 2026-03-24 (架构归档)

### refactor: 归档Phase 3-4架构改造变更
- **Commit**: `e597d5f`
- **清理**:
  - 简化 `build_dcf_model.py`（1596行→28行），业务逻辑迁移至 `src/models/`
  - 删除过时 `PROJECT_DOCUMENTATION.md`
  - 移动 `generate_waterfall_charts.py` / `generate_waterfall_plotly.py` 至 `scripts/`
- **新增业态框架**:
  - `src/models/industrial/` - 产业园REITs模型框架（DCF/NOI/Params）
  - `src/models/logistics/` - 物流仓储REITs模型框架（DCF/NOI/Params）
  - `src/models/hotel/` - 酒店模型补充（noi_engine, __init__）
  - `src/models/hotel_dcf.py`, `src/models/hotel_sensitivity.py` - 酒店DCF核心模型
- **新增可视化**:
  - `src/financial_comparison_visualization.py` - 历史财务数据对比可视化
  - `scripts/generate_sensitivity_charts.py` - 敏感性分析图表生成
  - `scripts/validate_mall_dcf.py` - Mall DCF校验工具
- **文档更新**:
  - `memory/REITs-dcf-pitfalls.md` - 更新DCF建模避坑指南
  - `memory/REITs-hotel-workflow.md` - 更新酒店工作流程
  - `memory/WORKFLOW_DATA_EXTRACTION.md` - 更新数据提取规范
  - `docs/extraction_summary_20250317.md` - 补充提取摘要
  - `docs/框架修改 plan 260323.md` - 架构改造计划文档
- **输出归档**:
  - 敏感性分析图表：`output/sensitivity_charts/*.png`（7张）
  - 财务对比表：`output/财务对比表_*.csv/md`
  - DCF校验结果：`output/mall_dcf_validation.json`
  - 历史数据：`output/historical_financial_3years.json`
  - 审计报告：`output/dcf_model/DCF模型审计报告.md`

---

## 2026-03-23 (架构修改 Phase 2)

### feat: 项目隔离架构 - 多项目配置管理支持
- **文件**: `main.py`, `src/core/project_config.py`, `run_config.yaml`
- **功能**: 支持多项目隔离（huazhu / huarun_chengdu），防止数据/模型混淆
  - 新增 `-p/--project` 命令行参数指定项目ID
  - 项目配置优先级：参数 > 环境变量(REITS_PROJECT) > 命令行 > 配置文件
  - 交互式项目确认（TTY环境）：显示可用项目列表、当前选中项目、项目详情
  - 自动创建项目隔离的输出目录结构 `output/{project}/latest/`
  - 统一路径管理：`get_data_path()`, `get_output_path()` 自动解析项目路径
- **单例模式**: `ProjectConfigManager` 确保配置全局唯一，避免重复加载
- **向后兼容**: 未指定项目时仍可使用 `-o/--output` 覆盖输出目录

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

