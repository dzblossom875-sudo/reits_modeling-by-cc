#!/usr/bin/env python3
"""
提取评估相关页面的内容
"""

import pdfplumber
import os

os.chdir(r'D:\AI投研工具\Claude Code\REITs_modeling by cc')

file_path = r'input/华住募集说明书.pdf'

with pdfplumber.open(file_path) as pdf:
    # 提取第375-385页的内容（评估章节）
    for page_num in range(374, 385):
        print(f'\n{"="*80}')
        print(f'Page {page_num + 1}')
        print("="*80)
        text = pdf.pages[page_num].extract_text() or ''

        # 显示所有包含百分比的行
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if '%' in line:
                # 过滤出可能相关的行
                if any(kw in line for kw in ['率', '折现', '资本', '评估', '价值', '收益', '报酬']):
                    print(f'{i}: {line}')

        print('\n--- Full text (first 3000 chars) ---')
        print(text[:3000])
        print('---')
