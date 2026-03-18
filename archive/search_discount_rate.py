#!/usr/bin/env python3
"""
搜索招募说明书中的折现率/资本化率/报酬率
"""

import pdfplumber
import re

def search_valuation_pages():
    file_path = r"D:\AI投研工具\Claude Code\REITs_modeling by cc\input\华住募集说明书.pdf"

    # 首先搜索目录页，找到评估章节位置
    print("="*80)
    print("步骤1: 搜索目录，找到资产评估章节")
    print("="*80)

    with pdfplumber.open(file_path) as pdf:
        # 搜索前50页找目录
        for page_num in range(min(50, len(pdf.pages))):
            page = pdf.pages[page_num]
            text = page.extract_text() or ""

            # 找评估/估值章节
            if any(kw in text for kw in ['评估', '估值', '资产评估', '价值评估', '收益法']):
                print(f"\n第{page_num+1}页可能包含评估相关内容:")
                lines = text.split('\n')
                for i, line in enumerate(lines):
                    if any(kw in line for kw in ['评估', '估值', '资产', '价值']):
                        print(f"  {line.strip()}")

def extract_valuation_details():
    file_path = r"D:\AI投研工具\Claude Code\REITs_modeling by cc\input\华住募集说明书.pdf"

    print("\n" + "="*80)
    print("步骤2: 搜索关键估值参数")
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

        # 评估章节通常在中间部分，搜索300-800页
        start_page = 300
        end_page = min(800, total_pages)

        for page_num in range(start_page, end_page):
            page = pdf.pages[page_num]
            text = page.extract_text() or ""

            for pattern, name in keywords:
                matches = re.finditer(pattern, text)
                for match in matches:
                    value = match.group(1)
                    # 获取上下文
                    start = max(0, match.start() - 100)
                    end = min(len(text), match.end() + 100)
                    context = text[start:end].replace('\n', ' ')

                    results.append({
                        'page': page_num + 1,
                        'type': name,
                        'value': value,
                        'context': context
                    })

    # 显示结果
    if results:
        print(f"\n找到 {len(results)} 条结果:")
        for r in results[:20]:
            print(f"\n第{r['page']}页 | {r['type']}: {r['value']}%")
            print(f"上下文: ...{r['context']}...")
    else:
        print("\n未找到明确的折现率/资本化率数据")

    return results

def search_specific_pages():
    """搜索特定页面范围"""
    file_path = r"D:\AI投研工具\Claude Code\REITs_modeling by cc\input\华住募集说明书.pdf"

    print("\n" + "="*80)
    print("步骤3: 搜索评估报告相关页面")
    print("="*80)

    # 搜索包含评估的页面
    valuation_pages = []

    with pdfplumber.open(file_path) as pdf:
        for page_num in range(len(pdf.pages)):
            page = pdf.pages[page_num]
            text = page.extract_text() or ""

            # 检查是否包含评估关键词
            if any(kw in text for kw in ['资产评估', '价值评估', '估值', '评估值', '收益法', '市场法']):
                # 检查是否包含百分比数字
                if re.search(r'[\d.]+%', text):
                    valuation_pages.append(page_num + 1)

    print(f"找到 {len(valuation_pages)} 个可能包含估值的页面")
    print(f"页面列表: {valuation_pages[:30]}")

    # 提取这些页面的关键信息
    if valuation_pages:
        print("\n提取关键页面内容:")
        with pdfplumber.open(file_path) as pdf:
            for page_num in valuation_pages[:10]:
                page = pdf.pages[page_num - 1]
                text = page.extract_text() or ""

                # 找包含百分比数字的行
                lines = text.split('\n')
                for line in lines:
                    if any(kw in line for kw in ['率', '折现', '资本化', '报酬']):
                        if '%' in line:
                            print(f"第{page_num}页: {line.strip()}")

if __name__ == "__main__":
    search_valuation_pages()
    extract_valuation_details()
    search_specific_pages()
