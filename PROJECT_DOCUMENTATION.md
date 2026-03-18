# 华住REIT DCF估值建模项目文档

**项目路径**: `D:\AI投研工具\Claude Code\REITs_modeling by cc`

**最后更新**: 2026-03-18

---

## 一、项目结构概览

```
REITs_modeling by cc/
├── main.py                          # 框架主入口（通用REITs建模框架）
├── build_dcf_model.py               # ✅ 华住REIT专用DCF建模脚本（最终版）
│
├── src/                             # 核心源代码
│   ├── noi_engine.py                # NOI计算引擎
│   ├── noi_comparison.py            # NOI比对分析
│   ├── schemas.py                   # 数据Schema定义
│   ├── core/                        # 核心类型定义
│   ├── models/                      # DCF模型、情景分析、敏感性分析
│   ├── exporters/                   # Excel/JSON导出
│   ├── parsers/                     # 文档解析器
│   ├── validators/                  # 参数验证、风险分析
│   └── utils/                       # 工具函数
│
├── input/                           # 输入文件
│   └── 华住募集说明书.pdf           # 招募说明书PDF
│
├── data/                            # 正式数据目录
│   └── huazhu/                      # 华住项目数据
│
├── tmp/huazhu_extract/              # PDF提取结果（临时）
│   ├── extracted_params.json        # ✅ 提取的核心参数
│   ├── page_*.md/txt                # 单页提取文本
│   └── tables/                      # 提取的表格
│
├── output/huazhu_dcf_model/         # DCF模型输出
│   ├── dcf_summary.csv              # 估值汇总表
│   ├── dcf_cashflows.csv            # 现金流明细
│   ├── dcf_sensitivity.csv          # 敏感性分析
│   ├── dcf_results.json             # 完整JSON结果
│   ├── dcf_valuation_final.xlsx     # Excel估值模型
│   └── DCF模型审计报告.md            # 模型审计文档
│
├── memory/                          # 项目文档与记忆
│   ├── MEMORY.md                    # 会话记忆
│   ├── WORKFLOW_DATA_EXTRACTION.md  # 数据提取规范
│   ├── REITs-dcf-pitfalls.md        # 常见陷阱
│   └── REITs-hotel-workflow.md      # 标准流程
│
└── archive/                         # 归档：开发过程文件
    └── README.md                    # 归档文件说明
```

---

## 二、核心程序入口

### 1. 华住REIT专用建模（推荐）

**文件**: `build_dcf_model.py`

**运行方式**:
```bash
python build_dcf_model.py
```

**功能**:
- 从`tmp/huazhu_extract/extracted_params.json`加载提取的数据
- 运行两个情景：基础情景（1%固定增长）和招募说明书情景（分段增长率）
- 输出CSV和JSON结果到`output/huazhu_dcf_model/`

**关键类**:
- `ProjectDCF`: 单个项目DCF模型
- `HuazhuDCFModel`: 华住REIT整体DCF模型

### 2. 通用框架入口

**文件**: `main.py`

**运行方式**:
```bash
python main.py --file input/华住募集说明书.pdf
```

**功能**:
- 通用REITs估值建模框架
- 支持多种资产类型（工业、商业、酒店等）
- 完整的文档解析、参数提取、模型搭建流程

**注意**: 当前华住REIT项目主要使用`build_dcf_model.py`，而非`main.py`

---

## 三、核心流程说明

### 流程1: PDF数据提取（已完成）

**相关文件**:
- `src/parsers/` - PDF解析器模块
- `tmp/huazhu_extract/extracted_params.json` - 提取结果（已归档）

**提取的数据**:
| 数据类型 | 来源页码 | 文件位置 |
|----------|----------|----------|
| 项目基本信息 | 第19页 | `extracted_params.json` |
| 项目详情 | 第64-70页 | `page_064.md` - `page_070.md` |
| 财务指标 | 第161-166页 | `page_16*_financial.md` |
| 收入成本 | 第172-202页 | `page_*_revenue_cost.md` |
| 估值参数 | 第234-242页 | `page_*_valuation.txt` |

**核心提取参数** (`extracted_params.json`):
```json
{
  "project_name": "华泰紫金华住安住封闭式商业不动产REIT",
  "total_rooms": 1044,
  "projects": [...],  // 3个项目详情
  "financial_data": {
    "广州项目": {
      "gop_2025": 8800,      // 已修正
      "annual_noicf": 7441.56
    },
    "上海项目": {
      "gop_2025": 2000,      // 已修正
      "annual_noicf": 1619.66
    }
  },
  "valuation_parameters": {
    "discount_rate": 0.0575,  // 5.75%
    "source_pages": [234, 240]
  }
}
```

### 流程2: DCF建模

**文件**: `build_dcf_model.py`

**建模步骤**:
1. **加载数据**: 从`extracted_params.json`读取参数
2. **创建项目模型**: `ProjectDCF`类（广州+上海）
3. **生成现金流**: 按年计算NOI、Capex、FCF
4. **折现计算**: 使用5.75%折现率
5. **汇总结果**: 计算总估值、KPI

**关键计算公式**:
```python
# 基础NOI（不扣capex）
base_noi = base_noicf + base_capex

# 年度NOI（考虑增长）
NOI_t = base_noi × cumulative_growth_factor

# 自由现金流
FCF_t = NOI_t - capex_t

# 折现
PV_t = FCF_t / (1 + discount_rate)^t

# 项目估值
valuation = Σ(PV_t)
```

### 流程3: 输出生成

**输出文件** (`output/huazhu_dcf_model/`):
- `dcf_summary.csv` - 估值汇总
- `dcf_cashflows.csv` - 50年现金流明细
- `dcf_sensitivity.csv` - 折现率/增长率敏感性
- `dcf_results.json` - 完整结果（JSON格式）

---

## 四、关键修正记录

### 修正1: GOP数据来源（重大修正）

| 项目 | 修正前 | 修正后 | 差异 |
|------|--------|--------|------|
| 广州GOP | 3,285.5万（利润表） | **8,800万**（管理报表） | +168% |
| 上海GOP | 1,188.93万（利润表） | **2,000万**（管理报表） | +68% |

**原因**: 招募说明书第162页管理报表（第162页）与第166页利润表口径不同，应使用管理报表数据

**修正日期**: 2026-03-18

**影响**: 估值从约9亿提升至13.25亿

### 修正2: 折现率确认

| 修正前 | 修正后 | 来源 |
|--------|--------|------|
| 未确认 | **5.75%** | 第234页（上海）、第240页（广州） |

**备注**: 报酬率/折现率，适用于两个项目

### 修正3: 评估基准日和首年NOI（重大修正）

| 修正项 | 修正前 | 修正后 | 差异 |
|--------|--------|--------|------|
| 评估基准日 | 未明确 | **2025年12月31日** | - |
| 广州首年NOI | 7,441.56万（2025） | **8,107.60万（2026）** | +8.9% |
| 上海首年NOI | 1,619.66万（2025） | **1,752.07万（2026）** | +8.2% |

**数据来源**: Page 235（广州）、Page 241（上海）

**影响**: 估值从13.25亿提升至14.51亿

### 修正4: 增长率分项设置（重大修正）

| 年份 | 修正前（统一） | 修正后（分项） | 广州 | 上海 |
|------|---------------|---------------|------|------|
| 2027（第2年） | 1% | **不同** | **2%** | **1%** |
| 2028（第3年） | 2% | 相同 | 2% | 2% |
| 2029-2035 | 3% | 相同 | 3% | 3% |
| 2036+ | 2.25% | 相同 | 2.25% | 2.25% |

**数据来源**: Page 236（上海）、Page 250（广州）

**影响**: 估值进一步校准，与评估值差距缩小

### 修正5: 终值处理

| 修正前 | 修正后 | 说明 |
|--------|--------|------|
| 未明确 | **残值归零** | 持有到期模型，土地使用权到期后无残值 |

**说明**: 保守估计，不考虑续期价值

---

## 五、最终版本状态

### 最终DCF估值结果

| 情景 | 总估值 | vs 资产评估值(15.91亿) |
|------|--------|------------------------|
| 基础情景（1%固定增长） | 12.68亿 | -3.23亿 (-20.3%) |
| **招募说明书情景（推荐）** | **14.51亿** | **-1.40亿 (-8.8%)** |

### 分项估值

| 项目 | 估值 | 首年NOI(2026) | 增长率特点 |
|------|------|---------------|------------|
| 广州项目（美居+全季） | 11.25亿 | 8,107.60万 | 2027年2% |
| 上海项目（桔子水晶） | 3.26亿 | 1,752.07万 | 2027年1% |
| **合计** | **14.51亿** | - | - |

### 关键假设汇总

| 参数 | 假设值 | 来源 |
|------|--------|------|
| 评估基准日 | 2025年12月31日 | 招募说明书 |
| 折现率 | 5.75% | 第234/240页 |
| 首年NOI | 2026年数据 | Page 235/241 |
| 广州2027年增长 | 2% | Page 250 |
| 上海2027年增长 | 1% | Page 236 |
| 2029-2035年增长 | 3% | Page 236 |
| 2036年后增长 | 2.25% | Page 236 |
| 终值 | 0 | 持有到期模型 |

---

## 六、文档记录清单

| 文档 | 路径 | 说明 |
|------|------|------|
| 项目文档 | `PROJECT_DOCUMENTATION.md` | 本文档 |
| 会话记忆 | `memory/MEMORY.md` | 开发日志与修正记录 |
| 数据提取规范 | `memory/WORKFLOW_DATA_EXTRACTION.md` | 三阶段工作流规范 |
| 审计报告 | `output/huazhu_dcf_model/DCF模型审计报告.md` | 完整审计 |
| NOI比对报告 | `output/NOI_comparison_report.md` | NOI计算比对分析 |
| 估值汇总 | `output/huazhu_dcf_model/dcf_summary.csv` | 最终结果 |
| 现金流明细 | `output/huazhu_dcf_model/dcf_cashflows.csv` | 50年明细 |
| Excel模型 | `output/huazhu_dcf_model/dcf_valuation_final.xlsx` | Excel估值模型 |
| JSON结果 | `output/huazhu_dcf_model/dcf_results.json` | 完整数据 |
| 归档文件 | `archive/README.md` | 过程文件归档说明 |

---

## 七、核心模块说明

### 1. DCF建模
```bash
python build_dcf_model.py
```
输出生成在 `output/huazhu_dcf_model/`：
- `dcf_results.json` - 完整JSON结果
- `dcf_valuation_final.xlsx` - Excel估值模型
- `DCF模型审计报告.md` - 审计文档

### 2. NOI计算引擎
```bash
python src/noi_comparison.py
```
功能：
- 从ADR/OCC计算客房收入
- 完整收入→NOI推导链条
- 与招募说明书逐项比对

### 3. 通用框架（备用）
```bash
python main.py --file input/华住募集说明书.pdf
```

---

## 八、项目演进说明

### 当前架构
- **根目录**: 仅保留最终入口脚本 (`build_dcf_model.py`, `main.py`)
- **src/**: 核心模块代码（NOI引擎、DCF模型、解析器等）
- **archive/**: 开发过程文件（探索脚本、测试代码等）

### 已归档文件
开发过程中的探索性脚本已移至 `archive/` 目录，包括：
- PDF提取探索脚本
- 早期估值模型示例
- 测试和诊断脚本

详见 `archive/README.md`

---

**文档版本**: v1.1

**最后更新**: 2026-03-18

**维护者**: Claude Code
