#!/usr/bin/env python3
"""分析华住募集说明书文档"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.parsers import DocumentParser
from src.parsers.extractor import ParameterExtractor
from src.core.config import AssetType

file_path = r"D:\2026\公募REITs\REIT 2026\商业不动产REITs\华泰紫金华住商业不动产\华住募集说明书.pdf"

print("=" * 60)
print("文档分析")
print("=" * 60)

# 解析文档
doc = DocumentParser().parse(file_path)
print(f"\n文件类型: {doc.file_type}")
print(f"页数: {doc.metadata.get('page_count', 'unknown')}")
print(f"表格数: {len(doc.tables)}")

# 显示关键表格内容
print("\n" + "=" * 60)
print("关键表格分析")
print("=" * 60)

for i, table in enumerate(doc.tables):
    # 查找包含关键信息的表格
    table_text = str(table.headers) + str(table.rows)

    # 查找包含ADR、入住率、房间数等关键词的表格
    keywords = ['ADR', '入住率', '房间', '客房', 'RevPAR', '建筑面积', '总面积']
    if any(kw in table_text for kw in keywords):
        print(f"\n--- 表格 {i} (Page {table.page_number}) ---")
        print(f"表头: {table.headers}")
        print("数据行:")
        for row in table.rows[:5]:
            print(f"  {row}")

# 提取参数
print("\n" + "=" * 60)
print("参数提取结果")
print("=" * 60)

extractor = ParameterExtractor(asset_type=AssetType.HOTEL)
params = extractor.extract(doc)

print(f"\n成功提取 {len(params.extracted)} 个参数:")
for name, param in params.extracted.items():
    print(f"  - {name}: {param.value} (来源: {param.source[:50]}...)")

print(f"\n缺失参数 ({len(params.missing)}):")
for p in params.missing:
    print(f"  - {p}")

print(f"\n不确定参数 ({len(params.uncertain)}):")
for name, param in params.uncertain.items():
    print(f"  - {name}: {param.value}")
