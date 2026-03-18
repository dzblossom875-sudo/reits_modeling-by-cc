#!/usr/bin/env python3
"""
提取广州项目和上海项目的各自增长率假设
"""

import pdfplumber
import os

os.chdir(r'D:\AI投研工具\Claude Code\REITs_modeling by cc')
file_path = r'input/华住募集说明书.pdf'

with pdfplumber.open(file_path) as pdf:
    print("="*80)
    print("查找广州项目和上海项目的增长率假设")
    print("="*80)

    # 查找关键词
    keywords = ['房价增长率', '房价每年增长率', '2027年', '2028年', '2029', '增长率']

    found_pages = []
    for page_num in range(230, 250):  # 估值章节范围
        text = pdf.pages[page_num].extract_text() or ''

        if '房价增长率' in text or '房价每年增长率' in text:
            found_pages.append(page_num)

    print(f"\n找到 {len(found_pages)} 个包含增长率的页面")

    for page_num in found_pages:
        print(f"\n{'='*60}")
        print(f"Page {page_num + 1}")
        print("="*60)

        text = pdf.pages[page_num].extract_text() or ''
        lines = text.split('\n')

        # 判断是广州还是上海项目
        if '天河' in text or '广州' in text[:500]:
            project = "广州项目"
        elif '江桥' in text or '上海' in text[:500]:
            project = "上海项目"
        else:
            project = "未知"

        print(f"项目: {project}")
        print("-"*60)

        for i, line in enumerate(lines):
            if any(kw in line for kw in keywords) or ('%' in line and '20' in line):
                print(f"{i}: {line}")
