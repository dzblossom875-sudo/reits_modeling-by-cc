# REITs DCF建模项目 - 最终结论快照

> **更新日期**: 2026-03-24
> **最新 Commit**: `9bffde0`

---

## 1. 项目架构（最终版）

### 目录结构

```
REITs_modeling/
├── src/                          # 核心引擎
│   ├── core/
│   │   ├── config.py             # 全局配置、枚举、阈值
│   │   ├── types.py              # 数据类型定义
│   │   └── project_config.py     # 项目配置管理器（多项目隔离）
│   ├── models/
│   │   ├── base_dcf.py           # DCF模型抽象基类
│   │   ├── dcf_result.py         # 统一结果格式
│   │   ├── multi_asset_dcf.py    # 多业态综合体DCF（mall+hotel）
│   │   ├── hotel/                # 酒店业态模型
│   │   │   ├── dcf.py            # HotelDCFModel
│   │   │   ├── noi_engine.py     # NOIDeriver（收入→NOI推导）
│   │   │   └── params.py         # 参数配置类
│   │   ├── mall/                 # 商业业态模型
│   │   │   ├── dcf.py            # MallDCFModel
│   │   │   └── noi_engine.py     # MallNOIDeriver
│   │   ├── industrial/           # 产业园模型（框架）
│   │   └── logistics/            # 物流仓储模型（框架）
│   ├── parsers/                  # 数据解析
│   │   ├── hotel_extractor.py    # 酒店数据提取
│   │   └── hotel_template.py     # 酒店提取模板
│   └── pipeline.py               # 流水线编排
├── data/                         # 数据仓库（按项目分目录）
│   ├── huazhu/                   # 华住安住REIT
│   └── huarun_chengdu/           # 华润成都万象城REIT
├── output/                       # 输出（按项目隔离）
│   ├── huazhu_dcf_model/         # 华住项目DCF结果
│   ├── dcf_model/                # DCF模型审计报告
│   └── sensitivity_charts/       # 敏感性分析图表
├── scripts/                      # 辅助脚本
│   ├── generate_sensitivity_charts.py
│   ├── generate_waterfall_charts.py
│   ├── validate_mall_dcf.py
│   └── test_multi_asset_dcf.py   # 综合体测试脚本
├── docs/                         # 文档
├── memory/                       # 项目记忆
├── run_config.yaml               # 项目配置中心
└── main.py                       # 统一入口
```

---

## 2. 输出文件清单

### 2.1 DCF建模结果

| 文件 | 说明 | 生成方式 |
|------|------|----------|
| `output/huazhu_dcf_model/dcf_results.json` | DCF计算结果（估值/NOI/现金流） | `main.py --pipeline` |
| `output/huazhu_dcf_model/DCF模型审计报告.md` | 审计轨迹与差异分析 | `main.py --pipeline` |
| `output/dcf_model/DCF模型审计报告.md` | 历史DCF模型审计 | pipeline生成 |
| `output/dcf_noi_comparison.json` | NOI推导对比数据 | pipeline中间产物 |

### 2.2 敏感性分析图表

| 文件 | 说明 |
|------|------|
| `output/sensitivity_charts/01_tornado.png` | 龙卷风图（单因素敏感性） |
| `output/sensitivity_charts/02_sensitivity_discount_rate.png` | 折现率敏感性曲线 |
| `output/sensitivity_charts/03_sensitivity_growth.png` | 增长率敏感性曲线 |
| `output/sensitivity_charts/04_sensitivity_noicf.png` | NOI/CF敏感性曲线 |
| `output/sensitivity_charts/05_two_way_heatmap.png` | 双因素热力图（折现率×增长率） |
| `output/sensitivity_charts/06_stress_test.png` | 压力测试情景分析 |
| `output/sensitivity_charts/07_waterfall.png` | 瀑布图（DCF构成分解） |

### 2.3 财务对比分析

| 文件 | 说明 |
|------|------|
| `output/historical_financial_3years.json` | 2023-2025年历史财务数据 |
| `output/财务对比表_广州.csv` | 广州项目历史vs预测对比 |
| `output/财务对比表_上海.csv` | 上海项目历史vs预测对比 |
| `output/财务对比表_完整版.md` | Markdown格式完整对比表 |
| `output/历史财务数据与DCF对比分析.md` | 文字分析+可视化图表 |
| `output/数据更新影响分析.md` | 数据更新对估值的影响 |

### 2.4 Mall DCF校验

| 文件 | 说明 |
|------|------|
| `output/mall_dcf_validation.json` | Mall模型校验结果 |
| `output/dcf_pages_scan.txt` | DCF相关页码扫描 |
| `output/dcf_numerical_table.txt` | 数值表提取 |
| `output/dcf_table_pages.txt` | 表格页码索引 |

---

## 3. 最佳实践

### 3.1 项目启动流程

```bash
# 1. 确认当前项目
cat run_config.yaml | grep active_project

# 2. 运行完整流水线
python main.py --pipeline

# 3. 查看结果
cat output/huazhu_dcf_model/DCF模型审计报告.md
```

### 3.2 多业态项目测试

```bash
# 测试华润成都万象城（mall+hotel）
python scripts/test_multi_asset_dcf.py
```

### 3.3 敏感性分析运行

```bash
python scripts/generate_sensitivity_charts.py
```

### 3.4 NOI Dashboard启动

```bash
streamlit run scripts/noi_dashboard.py
# 访问 http://localhost:8501
```

---

## 4. 避坑指南（精简版）

### 4.1 数据提取阶段

| 陷阱 | 正确做法 |
|------|----------|
| 五位数金额数字错位 | 交叉验证ADR公式计算值与招募值 |
| 含税vs不含税混淆 | ADR含税÷1.06，收入已是不含税 |
| 数据页码偏移 | PDF页码 = 文档页码 - 1 |
| 房产原值单位错误 | 数据文件已是万元，无需÷10000 |

### 4.2 建模阶段

| 陷阱 | 正确做法 |
|------|----------|
| **增值税重复扣除** | 中国GAAP收入已不含税，NOI推导不单独扣VAT |
| **成本口径混用** | 二选一：A)历史利润表运营成本 B)REITs明细成本 |
| **管理费口径错误** | 管理费=GOP×3%，非利润表"管理费用" |
| **税金及附加** | 优先使用实际缴纳值，推导值仅作对照 |
| **capex_forecast格式** | 支持列表[...]或字典{"2026": val, ...} |

### 4.3 综合体项目特殊注意

| 陷阱 | 正确做法 |
|------|----------|
| Mall数据格式不同 | financial_data中可能只有历史数据，需从historical推算Y1 |
| 业态检测失败 | 确保projects[].asset_type = "mall"或"hotel" |
| 子模型计算为0 | 启用招募说明书估值回退机制 |

---

## 5. 核心公式（最终版）

```
酒店REIT:
  营业收入(不含税) = ADR × rooms × OCC × 365 / 1.06
  运营成本(REITs口径) = Σ运营明细 + 物业费(独立) + 保险(独立)
  GOP = 营业收入 - 运营成本 - 税金及附加(实际缴纳)
  管理费 = GOP × 3%
  NOI = GOP - 管理费
  NOI/CF = NOI - Capex
  DCF = Σ(NOI×累积增长 - Capex) / (1+r)^t  （含部分年，无残值）

商业REIT:
  收入口径 = 不含税净额
  增值税 = 纯过路，不进NOI计算
  附加税 = VAT × 12%
  房产税(从租) = 12% × 不含税租金
```

---

## 6. 架构演进记录

| 阶段 | 日期 | Commit | 核心变更 |
|------|------|--------|----------|
| Phase 1 | 2026-03-23 | c4b9844 | 项目隔离配置体系（run_config.yaml） |
| Phase 2 | 2026-03-23 | 7675afc | main.py集成--project参数 |
| Phase 3 | 2026-03-23 | 待提交 | 清理硬编码项目值，支持动态读取 |
| Phase 4 | 2026-03-24 | 96bffbc | 多业态综合体DCF模型（mall+hotel） |
| 归档 | 2026-03-24 | e597d5f | 清理旧代码，归档输出文件 |
| 文档更新 | 2026-03-24 | 9bffde0 | 更新CHANGELOG与MEMORY |

---

## 7. 待续事项

- [ ] 优化mall模型参数使估值更接近招募说明书（当前-5.7%差异）
- [ ] 完善华润成都酒店部分数据提取（当前使用回退估值）
- [ ] 补充产业园/物流仓储业态完整实现（当前仅框架）
- [ ] 执行未提交的Phase 3变更归档

---

## 8. 快速参考

### 8.1 重要阈值

| 参数 | 值 | 说明 |
|------|-----|------|
| COMPARISON_THRESHOLD | 5% | NOI差异判定阈值 |
| 酒店默认折现率 | 5.75% | extracted_params定义 |
| Mall默认折现率 | 6.5% | 风险溢价 |
| 增值税率（酒店） | 6% | ADR价税分离用 |
| 管理费率 | 3% | GOP×3% |
| 房产税（从租） | 12% | 商业租金 |

### 8.2 关键文件路径

```
数据输入:
  data/{project}/extracted_params.json
  data/{project}/extracted_params_detailed.json

DCF输出:
  output/{project}/latest/dcf_results.json
  output/{project}/latest/DCF模型审计报告.md

配置:
  run_config.yaml
```

---

> **文档维护**: 每次代码变更后同步更新
> **上次更新**: 2026-03-24 by A (Claude Code)
