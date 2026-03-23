# 酒店REITs DCF建模系统架构

## 系统结构

```
REITs_modeling/
├── src/                          # 核心引擎
│   ├── core/
│   │   ├── config.py             # 全局配置、枚举、阈值
│   │   ├── types.py              # 数据类型定义（ExtractedParam等）
│   │   └── project_config.py     # 项目配置管理器（多项目隔离）
│   ├── models/
│   │   └── hotel_dcf.py          # DCF模型（NOIDeriver + HotelDCFModel）
│   ├── exporters/                # 输出模块（Excel/JSON/Chart）
│   ├── pipeline.py               # 流水线编排
│   └── ...
├── data/                         # 数据仓库（按项目分目录）
│   ├── huazhu/                   # 华住安住REIT数据
│   │   └── extracted_params.json
│   └── huarun_chengdu/           # 华润成都万象城REIT数据
│       └── extracted_params.json
├── output/                       # 输出（按项目隔离）
│   ├── huazhu/                   # 华住项目输出
│   │   ├── latest/               # 最新结果软链接/复制
│   │   └── run_YYYYMMDD_HHMMSS/  # 历史运行记录
│   └── huarun_chengdu/           # 华润项目输出
│       ├── latest/
│       └── run_YYYYMMDD_HHMMSS/
├── run_config.yaml               # 项目配置文件（active_project切换）
├── docs/                         # 文档
│   ├── architecture.md           # 本文件
│   └── lessons-learned.md        # 调试结论与避坑记录
├── memory/                       # 项目记忆
├── scripts/                      # 辅助脚本
└── main.py                       # 统一入口（支持--project参数）
```

## 项目隔离机制

### 配置层级（优先级从高到低）

```
1. 命令行参数: python main.py --project huarun_chengdu
2. 环境变量: REITS_PROJECT=huarun_chengdu
3. 配置文件: run_config.yaml 中的 active_project
4. 默认值: huazhu
```

### 项目配置管理器

```python
from src.core.project_config import get_config

# 自动选择（非交互式，推荐用于脚本）
config = get_config()

# 强制指定项目
config = get_config(project_name="huarun_chengdu")

# 交互式选择（TTY环境显示项目列表）
config = get_config(auto_confirm=False)

# 使用路径接口
data_path = config.get_data_path("extracted_params.json")
output_path = config.get_output_path("dcf_results.json", use_latest=True)
```

### 多业态支持

`run_config.yaml` 支持多业态项目：

```yaml
projects:
  huarun_chengdu:
    asset_types: [mall, hotel]  # 商业综合体
    data_dir: data/huarun_chengdu
    output_dir: output/huarun_chengdu
```

## 数据流

```
PDF招募说明书
  ↓ extract_pdf_real.py
extracted_params_detailed.json (项目数据目录)
  ↓ pipeline.py step1
参数提取 & 交叉验证
  ↓ pipeline.py step2
历史数据比对 + 图表
  ↓ pipeline.py step3 (NOIDeriver + HotelDCFModel)
NOI推导 → DCF估值 → 敏感性分析
  ↓ pipeline.py save_results
output/{project}/run_YYYYMMDD_HHMMSS/
  ↓ 同步至
output/{project}/latest/
```

---

## Immutable Rules

以下规则经实际调试验证，是建模正确性的底线约束。违反任意一条将导致估值偏差。

### IR-1: 增值税禁止重复扣除

```
中国GAAP"营业收入"= 不含增值税净额
"税金及附加"≠ 增值税
NOI推导中禁止单独计算和扣除增值税
```

> 违反后果: NOI偏低800-1000万（约10%），估值偏低>10%

### IR-2: 成本口径二选一，不可混用

```
口径A: 历史利润表"运营成本(不含折旧)" → 已含物业/保险
口径B: REITs明细 = 运营明细 + 物业(独立) + 保险(独立)
```

REITs建模使用口径B。若引用口径A作参考，需标注"历史利润表口径"。

> 违反后果: 物业费+保险双重计算（广州约481万/年），NOI偏低

### IR-3: 管理费 = GOP × fee_rate

```
管理费 = GOP × 管理费率（通常3%）
```

不得使用利润表"管理费用"（含公司行政开支，REITs后由基金承担）。

> 违反后果: 管理费虚高（上海偏差146万），NOI偏低

### IR-4: 税金及附加使用实际缴纳值

税金及附加优先使用实际缴纳值（历史/招募），推导值仅作对照参考。

```
推导值高于实际值的原因: 减免政策/基数差异/税率优惠
使用实际值 + 标注推导差异
```

### IR-5: ADR含税统一6%增值税率

```
ADR(含税) × rooms × OCC × 365 = 含税客房收入
含税 ÷ 1.06 = 不含税收入
```

对比时必须统一口径（含税vs含税，或不含税vs不含税），禁止不同隐含税率反推。

### IR-6: 始终使用推导NOI

```
NOI始终使用收支明细推导值，不回退到招募值
差异≤5%: 标注PASS
差异>5%: 标注差异百分比，仍使用推导值
```

推导NOI反映REITs后实际成本结构，与招募利润表口径的差异是口径差异。

### IR-7: 无残值、持有到期

```
终值 = 0（土地使用权到期后无残值）
不使用永续增长模型
DCF年限 = 土地使用权剩余年限（含部分年）
```

### IR-8: 输出不可覆盖

所有输出写入时间戳目录 `output/run_YYYYMMDD_HHMMSS/`，禁止覆盖历史版本。

### IR-9: 参数提取前置

所有计算参数必须在第一步（参数提取阶段）完成并归档至 `extracted_params_detailed.json`。建模阶段禁止临时补充参数提取。

### IR-10: 部分年限处理

```
剩余年限不取整
完整年 + 部分年(按比例计算NOI)
折现因子 = (1+r)^(full_years + partial_fraction)
```

---

## 核心公式（最终版）

```
营业收入(不含税) = first_year_amount
运营成本(REITs口径) = Σ运营明细项 + 物业费(独立) + 保险(独立)
GOP = 营业收入 - 运营成本 - 税金及附加(实际缴纳)
管理费 = GOP × 3%
NOI = GOP - 管理费
NOI/CF = NOI - Capex
FCF_t = NOI × 累积增长因子 - Capex_t
DCF = Σ FCF_t / (1+r)^t   (t=1..N, 含部分年, 无残值)
```
