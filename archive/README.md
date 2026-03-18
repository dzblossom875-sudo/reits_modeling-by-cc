# Archive 目录说明

此目录包含项目开发过程中的探索性脚本和过程文件。

## 文件清单

| 文件 | 用途 | 归档原因 |
|------|------|----------|
| `analyze_doc.py` | 早期文档分析探索 | 功能已整合到 src/parsers/ |
| `diagnose_extraction.py` | 提取流程诊断 | 一次性诊断脚本 |
| `example_huazhu_manual.py` | 手动参数示例 | 已整合到 build_dcf_model.py |
| `example_multi_project_hotel.py` | 多项目示例 | 示例代码，已整合 |
| `extract_and_validate.py` | 提取验证探索 | 功能已整合到 src/parsers/ |
| `extract_growth_rates.py` | 增长率提取探索 | 数据已提取，脚本完成使命 |
| `extract_pdf_quick.py` | 快速提取探索 | 功能已整合 |
| `extract_pdf_real.py` | PDF提取探索 | 功能已整合到 src/parsers/ |
| `extract_valuation_pages.py` | 估值页提取 | 数据已提取，脚本完成使命 |
| `huazhu_real_valuation.py` | 早期估值模型 | 已整合到 build_dcf_model.py |
| `search_discount_rate.py` | 折现率搜索 | 数据已提取，脚本完成使命 |
| `search_discount_rate_fast.py` | 快速搜索折现率 | 数据已提取，脚本完成使命 |
| `test_hotel_extractor.py` | 提取器测试 | 测试脚本，已完成测试 |

## 说明

这些文件保留了开发过程中的探索痕迹，如需参考可在此查看。

**当前使用的入口文件**:
- `build_dcf_model.py` - 华住REIT专用DCF建模（根目录）
- `main.py` - 通用REITs建模框架（根目录）

**核心模块**:
- `src/noi_engine.py` - NOI计算引擎
- `src/noi_comparison.py` - NOI比对分析
- `src/schemas.py` - 数据Schema定义
