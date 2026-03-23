# REITs DCF建模工作流程

> **更新日期**: 2026-03-24

---

## 1. 标准工作流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         REITs DCF建模标准流程                                │
└─────────────────────────────────────────────────────────────────────────────┘

Phase 1: 参数提取 (必须完整)
─────────────────────────────
PDF招募说明书
    ↓
extract_pdf_real.py / extract_and_validate.py
    ↓
├── extracted_params_detailed.json  (★ 第一步唯一输出)
├── extraction_summary.md           (提取摘要)
└── cross_validation_report         (交叉验证报告)

Phase 2: 参数确认
─────────────────
确认关键假设:
  - 折现率 (discount_rate)
  - 增长率假设 (growth_rate schedule)
  - Capex预测 (capex_forecast)
  - 剩余年限 (remaining_years)
标记确认状态 → 数据文件冻结

Phase 3: 建模计算
─────────────────
extracted_params_detailed.json
    ↓
NOIDeriver (收入→NOI推导)
    ↓
HotelDCFModel / MallDCFModel (逐期现金流计算)
    ↓
DCFResult (统一结果格式)
    ↓
敏感性分析引擎
    ↓
output/{project}/run_YYYYMMDD_HHMMSS/

Phase 4: 结果比对与审计
────────────────────────
计算结果 vs 招募说明书估值
    ↓
差异分析报告
    ↓
├── DCF模型审计报告.md
├── 敏感性分析图表
└── 估值差异说明
```

---

## 2. 多业态项目流程（综合体）

```
以华润成都万象城为例:

extracted_params.json (包含mall+hotel项目)
    ↓
MultiAssetDCFModel
    ├── 检测业态 → ["mall", "hotel"]
    ├── 构建子模型
    │   ├── MallDCFModel → 商业部分估值
    │   └── HotelDCFModel → 酒店部分估值
    ├── 分别计算
    │   ├── Mall: 从历史数据推算Y1，逐年增长
    │   └── Hotel: 从NOI/CF+Capex计算NOI
    └── 合并结果
        ├── 汇总估值
        ├── 检查回退（某业态计算为0时启用招募估值）
        └── 输出统一DCFResult

注意: 综合体项目数据格式与单业态不同
  - financial_data中可能无预测参数
  - Mall需从历史收入数据推算Y1
  - 酒店部分可能需使用招募估值回退
```

---

## 3. 数据流图

### 3.1 酒店REIT数据流

```
PDF招募说明书
    │
    ├── 项目基础信息 ─────┐
    │   (房间数/ADR/OCC)  │
    │                     │
    ├── 历史财务数据 ─────┤
    │   (2023-2025)       │
    │                     ├──→ extracted_params_detailed.json
    ├── 2026年预测数据 ───┤    (第一步完整归档)
    │   (Page 235/241)    │
    │                     │
    ├── 增长率假设 ───────┤
    │   (Page 236/250)    │
    │                     │
    └── Capex预测 ────────┘

                          ↓

              ┌───────────────────────┐
              │   NOIDeriver推导      │
              │  (收入→GOP→NOI→NOI/CF) │
              └───────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ↓               ↓               ↓
    广州项目NOI     上海项目NOI      与招募对比
          │               │               ↓
          └───────────────┤         差异≤5%: PASS
                          │         差异>5%: 标注但用推导值
                          ↓
              ┌───────────────────────┐
              │   HotelDCFModel       │
              │  (逐年现金流折现)      │
              │                       │
              │  FCF_t = NOI_t - Capex_t│
              │  PV_t = FCF_t / (1+r)^t │
              │  DCF = ΣPV_t            │
              └───────────────────────┘
                          │
                          ↓
              ┌───────────────────────┐
              │    DCFResult          │
              │  - total_valuation    │
              │  - total_noi_year1    │
              │  - implied_cap_rate   │
              │  - projects[]         │
              │  - cash_flows[]       │
              └───────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ↓               ↓               ↓
    敏感性分析       Excel输出         审计报告
          │               │               │
          ↓               ↓               ↓
output/sensitivity  output/*.xlsx   output/*审计报告.md
```

### 3.2 商业REIT数据流

```
PDF招募说明书 (Mall)
    │
    ├── 项目基础 ─────────┐
    │   (GLA/停车位/分期) │
    │                     │
    ├── 租户结构 ─────────┤
    │   (主次力店比例)    │
    │                     ├──→ extracted_params_detailed.json
    ├── Y1收入预测 ───────┤    (固定租金/提成/物管/停车等)
    │                     │
    ├── 增长率schedule ───┤
    │   (各业态分段增长)  │
    │                     │
    ├── 成本参数 ─────────┤
    │   (营销/维修/人工)  │
    │                     │
    └── 税金参数 ─────────┘
    (增值税率/房产税/附加税)

                          ↓

              ┌───────────────────────┐
              │   MallNOIDeriver      │
              │  (逐项收入→逐项成本   │
              │   →NOI逐期预测)       │
              │                       │
              │ 注意: 收入已不含税    │
              │ VAT不进成本，只算附加税│
              └───────────────────────┘
                          │
                          ↓
              ┌───────────────────────┐
              │   MallDCFModel        │
              │  (20+年逐期折现)      │
              │                       │
              │  折现约定: 期末折现   │
              │  与酒店模型保持一致   │
              └───────────────────────┘
                          │
                          ↓
                     DCFResult
```

### 3.3 多业态合并数据流

```
extracted_params.json
    │
    ├── projects[0]: asset_type="mall"
    │                 └── 从历史收入推算Y1
    │
    └── projects[1]: asset_type="hotel"
                      └── 从NOI/CF+Capex计算

              ↓

      MultiAssetDCFModel
              │
              ├── 检测业态 → ["mall", "hotel"]
              │
              ├── _build_sub_models()
              │   ├── MallDCFModel(data)
              │   └── HotelDCFModel(data)
              │
              ├── calculate()
              │   ├── mall_result = mall_model.calculate()
              │   └── hotel_result = hotel_model.calculate()
              │
              ├── _merge_results()
              │   ├── 汇总projects[]
              │   ├── 合计valuation
              │   ├── 检查回退逻辑
              │   │   (某业态为0但招募有值→添加回退项目)
              │   └── 计算综合cap_rate
              │
              └── DCFResult (统一格式)
                  ├── asset_type="mixed"
                  ├── projects (合并后)
                  └── 包含分业态明细
```

---

## 4. 项目配置切换流程

```bash
# 方式1: 修改配置文件 (默认)
vi run_config.yaml
# active_project: huazhu

# 方式2: 命令行参数
python main.py --project huarun_chengdu --pipeline

# 方式3: 环境变量
REITS_PROJECT=huarun_chengdu python main.py --pipeline

# 方式4: 交互式选择 (TTY环境)
python main.py -i
# [显示项目列表]
# 请确认或选择项目 [1/2/...]:
```

---

## 5. 质量门禁

### 5.1 参数提取阶段门禁

| 检查项 | 标准 | 失败处理 |
|--------|------|----------|
| 关键字段完整性 | Tier 1-3字段100%填充 | 返回补充提取 |
| ADR公式验证 | 计算值vs招募值差异≤5% | 核查单位/税率 |
| 交叉验证 | 多来源数据一致性 | 标记差异并核查 |
| 页码索引 | 所有数据标注PDF页码 | 补充页码信息 |

### 5.2 建模阶段门禁

| 检查项 | 标准 | 失败处理 |
|--------|------|----------|
| NOI推导差异 | vs招募NOI差异≤10% | 标注差异原因 |
| Cap Rate合理性 | 与行业Cap Rate对比 | 核查NOI或估值 |
| 现金流检验 | 首年FCF>0 | 核查Capex是否过大 |
| 折现因子 | 最后一期DF>0 | 检查年限是否过长 |

### 5.3 输出阶段门禁

| 检查项 | 标准 | 失败处理 |
|--------|------|----------|
| 输出目录隔离 | 按项目+时间戳存储 | 禁止覆盖历史版本 |
| 审计报告完整 | 包含差异说明 | 补充差异分析 |
| 图表生成 | 敏感性分析7张图 | 检查依赖库安装 |

---

## 6. 调试工作流程

```
发现问题
    ↓
定位阶段 (提取/建模/输出)
    ↓
复现问题
    ↓
┌─────────────────────┐
│ 临时调试代码        │
│ (仅用于定位，不提交) │
└─────────────────────┘
    ↓
修复问题
    ↓
验证修复
    ↓
┌─────────────────────┐
│ 移除调试代码        │
│ 格式化文件          │
│ 更新文档            │
└─────────────────────┘
    ↓
Git Commit
    ↓
更新 MEMORY.md + docs/CHANGELOG.md
```

---

## 7. 文件命名规范

### 7.1 数据文件

```
data/{project}/
├── extracted_params.json              # 基础提取数据
├── extracted_params_detailed.json     # 详细提取数据（主要输入）
└── historical_financial.json          # 历史财务数据（可选）
```

### 7.2 输出文件

```
output/{project}/
├── run_YYYYMMDD_HHMMSS/              # 时间戳目录
│   ├── dcf_results.json              # DCF结果
│   ├── DCF模型审计报告.md            # 审计报告
│   ├── noi_comparison_report.json    # NOI对比
│   └── charts/                       # 图表目录
│       ├── sensitivity_*.png
│       └── hist_vs_forecast_*.png
├── latest/                           # 软链接/复制到最新
└── dcf_comparison.json               # 双轨对比结果
```

### 7.3 文档文件

```
docs/
├── architecture.md                   # 系统架构与Immutable Rules
├── CHANGELOG.md                      # 修改历史
├── lessons-learned.md                # 调试结论
├── summary.md                        # 最终结论快照
├── workflow.md                       # 本文件
├── extraction_summary_YYYYMMDD.md    # 数据提取摘要
└── 框架修改 plan YYYYMMDD.md         # 架构改造计划
```

---

## 8. 常见问题排查

### 8.1 模型估值偏差过大

| 检查点 | 可能原因 | 解决方法 |
|--------|----------|----------|
| NOI偏低 | 增值税重复扣除 | 检查noi_engine是否扣VAT |
| NOI偏低 | 成本口径混用 | 确认使用REITs明细成本 |
| NOI偏低 | 物业费双重计算 | 检查是否已含在历史成本中 |
| 估值偏低 | 折现率过高 | 核对招募说明书折现率 |
| 估值偏低 | 增长率假设保守 | 对比招募增长率schedule |

### 8.2 多业态项目问题

| 现象 | 可能原因 | 解决方法 |
|------|----------|----------|
| Mall估值为0 | detailed_data为空 | 检查_extracted_data_fallback是否生效 |
| Hotel估值为0 | asset_type不匹配 | 检查projects[].asset_type="hotel" |
| 合并结果缺失业态 | 子模型抛出异常 | 查看[WARN]日志，检查回退是否生效 |

### 8.3 配置问题

| 现象 | 可能原因 | 解决方法 |
|------|----------|----------|
| 输出到错误目录 | 项目配置未生效 | 检查run_config.yaml active_project |
| 找不到数据文件 | 项目ID不匹配 | 确认data/{project}/目录存在 |
| 模块导入失败 | PYTHONPATH问题 | 检查main.py中sys.path.insert |

---

> **维护说明**: 本文件随架构调整同步更新
> **上次更新**: 2026-03-24
