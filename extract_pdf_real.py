#!/usr/bin/env python3
"""
提取PDF真实内容 - 查看华住REIT实际项目信息
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.parsers import DocumentParser
import re

def extract_key_info(text: str):
    """提取关键信息"""
    info = {
        'project_names': [],
        'locations': [],
        'hotels': [],
        'adr': [],
        'occupancy': [],
        'room_counts': [],
        'revenue': [],
    }

    # 提取项目名称/酒店名称
    hotel_patterns = [
        r'汉庭[\w\s]+酒店',
        r'全季[\w\s]+酒店',
        r'桔子[\w\s]+酒店',
        r'桔子水晶[\w\s]+酒店',
        r'([\u4e00-\u9fa5]{2,10}酒店)',
    ]

    for pattern in hotel_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            name = match.group(0)
            if name not in info['hotels'] and len(name) > 3:
                info['hotels'].append(name)

    # 提取地点信息
    location_patterns = [
        r'位于([\u4e00-\u9fa5]{2,10})',
        r'([\u4e00-\u9fa5]{2,10})市',
        r'([\u4e00-\u9fa5]{2,10})区',
    ]

    for pattern in location_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            loc = match.group(1) if match.groups() else match.group(0)
            if loc not in info['locations'] and len(loc) > 1:
                info['locations'].append(loc)

    # 提取ADR
    adr_patterns = [
        r'ADR[\s:：]*([\d,]+\.?\d*)',
        r'平均房价[\s:：]*([\d,]+\.?\d*)',
        r'日均房价[\s:：]*([\d,]+\.?\d*)',
    ]

    for pattern in adr_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            try:
                val = float(match.group(1).replace(',', ''))
                if 100 < val < 2000:
                    info['adr'].append(val)
            except:
                pass

    # 提取入住率
    occ_patterns = [
        r'入住率[\s:：]*([\d\.]+)\s*%',
        r'出租率[\s:：]*([\d\.]+)\s*%',
        r'Occ[\s:：]*([\d\.]+)\s*%',
    ]

    for pattern in occ_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            try:
                val = float(match.group(1))
                if val <= 1 or (val > 10 and val <= 100):
                    info['occupancy'].append(val if val <= 1 else val / 100)
            except:
                pass

    # 提取客房数
    room_patterns = [
        r'客房数[\s:：]*([\d,]+)',
        r'房间数[\s:：]*([\d,]+)',
        r'([\d,]+)\s*间客房',
    ]

    for pattern in room_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            try:
                val = float(match.group(1).replace(',', ''))
                if 50 < val < 1000:
                    info['room_counts'].append(int(val))
            except:
                pass

    return info


def main():
    print("="*80)
    print("  华住REIT PDF真实内容提取")
    print("="*80)

    file_path = r"D:\AI投研工具\Claude Code\REITs_modeling by cc\input\华住募集说明书.pdf"

    print(f"\n>>> 解析PDF: {file_path}")

    try:
        doc = DocumentParser().parse(file_path)
    except Exception as e:
        print(f"[ERROR] 解析失败: {e}")
        return

    print(f"\n[文档信息]")
    print(f"  页数: {doc.metadata.get('page_count', 'unknown')}")
    print(f"  表格数: {len(doc.tables)}")
    print(f"  文本长度: {len(doc.text)} 字符")

    # 提取关键信息
    info = extract_key_info(doc.text)

    print(f"\n[提取的酒店名称] (去重后)")
    for i, hotel in enumerate(info['hotels'][:20], 1):
        print(f"  {i}. {hotel}")

    print(f"\n[提取的地点信息]")
    for i, loc in enumerate(info['locations'][:30], 1):
        print(f"  {i}. {loc}")

    print(f"\n[提取的ADR值]")
    for i, adr in enumerate(info['adr'][:20], 1):
        print(f"  {i}. {adr:.2f} 元")

    print(f"\n[提取的入住率]")
    for i, occ in enumerate(info['occupancy'][:20], 1):
        print(f"  {i}. {occ:.1%}")

    print(f"\n[提取的客房数]")
    for i, rooms in enumerate(info['room_counts'][:20], 1):
        print(f"  {i}. {rooms} 间")

    # 显示文本前3000字符（查看实际内容）
    print("\n" + "="*80)
    print("  文本内容预览 (前3000字符)")
    print("="*80)
    print(doc.text[:3000])

    # 保存完整文本供查看
    output_path = Path("./output/pdf_extracted_text.txt")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(doc.text)
    print(f"\n[OK] 完整文本已保存: {output_path}")

    # 显示前5个表格的内容
    print("\n" + "="*80)
    print("  表格内容预览 (前5个表格)")
    print("="*80)

    for i, table in enumerate(doc.tables[:5], 1):
        print(f"\n[表格{i}] (第{table.page_number}页)")
        print(f"  表头: {table.headers}")
        print(f"  行数: {len(table.rows)}")
        for j, row in enumerate(table.rows[:5], 1):
            print(f"    行{j}: {row}")


if __name__ == "__main__":
    main()
