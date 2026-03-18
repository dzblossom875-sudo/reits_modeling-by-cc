#!/usr/bin/env python3
"""
快速搜索招募说明书中的折现率/资本化率/报酬率
专注搜索评估相关章节
"""

import pdfplumber
import re

def search_key_pages():
    file_path = r"D:\AI投研工具\Claude Code\REITs_modeling by cc\input\华住募集说明书.pdf"

    print("="*80)
    print("搜索招募说明书中的折现率/资本化率")
    print("="*80)

    keywords = [
        (r'折现率[:\s]*([\d.]+)\s*%', '折现率'),
        (r'资本化率[:\s]*([\d.]+)\s*%', '资本化率'),
        (r'报酬率[:\s]*([\d.]+)\s*%', '报酬率'),
        (r'贴现率[:\s]*([\d.]+)\s*%', '贴现率'),
        (r'资本成本[:\s]*([\d.]+)\s*%', '资本成本'),
    ]

    results = []

    with pdfplumber.open(file_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"总页数: {total_pages}")

        # 评估章节通常在200-400页或800-1000页之间
        search_ranges = [(200, 400), (800, 1000)]

        for start, end in search_ranges:
            print(f"\n搜索页面范围: {start}-{end}")
            for page_num in range(start, min(end, total_pages)):
                if page_num % 50 == 0:
                    print(f"  正在处理第{page_num}页...")

                page = pdf.pages[page_num]
                text = page.extract_text() or ""

                # 首先检查是否包含评估相关关键词
                if not any(kw in text for kw in ['评估', '估值', '价值评估', '资产评估']):
                    continue

                for pattern, name in keywords:
                    matches = re.finditer(pattern, text)
                    for match in matches:
                        value = match.group(1)
                        # 获取上下文
                        start_pos = max(0, match.start() - 100)
                        end_pos = min(len(text), match.end() + 100)
                        context = text[start_pos:end_pos].replace('\n', ' ')

                        results.append({
                            'page': page_num + 1,
                            'type': name,
                            'value': value,
                            'context': context
                        })
                        print(f"\n>>> 找到: 第{page_num+1}页 | {name}: {value}%")
                        print(f"    上下文: ...{context}...")

    print("\n" + "="*80)
    print("搜索完成")
    print("="*80)

    if results:
        print(f"\n共找到 {len(results)} 条结果:")
        for r in results:
            print(f"  第{r['page']}页 | {r['type']}: {r['value']}%")
    else:
        print("\n未找到折现率/资本化率数据")

    return results

if __name__ == "__main__":
    search_key_pages()
