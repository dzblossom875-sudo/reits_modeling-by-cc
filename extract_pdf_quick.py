#!/usr/bin/env python3
"""
快速提取PDF前10页内容 - 获取项目基本信息
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import re

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    print("[ERROR] pdfplumber未安装")
    sys.exit(1)

def main():
    print("="*80)
    print("  华住REIT PDF快速提取 (前10页)")
    print("="*80)

    file_path = r"D:\AI投研工具\Claude Code\REITs_modeling by cc\input\华住募集说明书.pdf"

    print(f"\n>>> 解析PDF前10页...")

    text_content = []
    tables = []

    with pdfplumber.open(file_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"  总页数: {total_pages}")

        # 只解析前10页
        for page_num in range(min(10, total_pages)):
            page = pdf.pages[page_num]
            page_text = page.extract_text()
            if page_text:
                text_content.append(f"\n--- Page {page_num+1} ---\n{page_text}")

            page_tables = page.extract_tables()
            for table_data in page_tables:
                if table_data and len(table_data) > 1:
                    tables.append({
                        'page': page_num + 1,
                        'headers': table_data[0] if table_data else [],
                        'rows': table_data[1:4] if len(table_data) > 1 else []
                    })

    full_text = "\n".join(text_content)

    print(f"\n[文本预览 - 前5000字符]")
    print("="*80)
    print(full_text[:5000])
    print("="*80)

    # 提取酒店名称
    print("\n[酒店名称搜索]")
    hotel_keywords = ['汉庭', '全季', '桔子', '桔子水晶', '花间堂', '禧玥', '漫心']
    found_hotels = []
    for keyword in hotel_keywords:
        pattern = rf'{keyword}[\w\s]*酒店?'
        matches = re.finditer(pattern, full_text)
        for match in matches:
            name = match.group(0).strip()
            if name and name not in found_hotels:
                found_hotels.append(name)
                print(f"  找到: {name}")

    # 提取地点
    print("\n[地点搜索 - 城市名]")
    city_pattern = r'([\u4e00-\u9fa5]{2,4})(?:市|区)'
    cities = set()
    for match in re.finditer(city_pattern, full_text):
        city = match.group(1)
        if len(city) >= 2:
            cities.add(city)

    for city in sorted(cities)[:30]:
        print(f"  {city}")

    # 表格预览
    print("\n[表格预览]")
    for i, table in enumerate(tables[:5], 1):
        print(f"\n  [表格{i}] 第{table['page']}页")
        print(f"    表头: {table['headers']}")
        for j, row in enumerate(table['rows'][:3], 1):
            print(f"    行{j}: {row}")

    # 保存
    output_path = Path("./output/pdf_extracted_quick.txt")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_text)
    print(f"\n[OK] 文本已保存: {output_path}")

if __name__ == "__main__":
    main()
