#!/usr/bin/env python3
"""
诊断脚本：检查PDF提取流程和数据
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.parsers import DocumentParser
from src.parsers.hotel_extractor import HotelREITExtractor

def main():
    print("=" * 70)
    print("  华住REIT数据提取诊断")
    print("=" * 70)

    file_path = r"D:\AI投研工具\Claude Code\REITs_modeling by cc\input\华住募集说明书.pdf"

    # 步骤1: 解析文档
    print("\n[步骤1] 解析PDF文档...")
    try:
        doc = DocumentParser().parse(file_path)
        print(f"  [OK] 文件类型: {doc.file_type}")
        print(f"  [OK] 页数: {doc.metadata.get('page_count', 'unknown')}")
        print(f"  [OK] 表格数: {len(doc.tables)}")
    except Exception as e:
        print(f"  [FAIL] 解析失败: {e}")
        return

    # 步骤2: 显示文档基本信息
    print("\n[步骤2] 文档内容预览...")
    text_preview = doc.text[:2000] if doc.text else "无文本内容"
    print(f"  文本长度: {len(doc.text)} 字符")
    print(f"  前500字符:\n{text_preview[:500]}...")

    # 步骤3: 显示表格结构
    print("\n[步骤3] 表格结构分析...")
    print(f"  共发现 {len(doc.tables)} 个表格")
    for i, table in enumerate(doc.tables[:3]):  # 只显示前3个
        print(f"\n  表格{i+1}:")
        print(f"    表头: {table.headers}")
        print(f"    行数: {len(table.rows)}")
        if table.rows:
            print(f"    首行: {table.rows[0]}")

    # 步骤4: 运行提取器
    print("\n[步骤4] 运行酒店REIT提取器...")
    try:
        extractor = HotelREITExtractor()
        data = extractor.extract(doc)

        print(f"\n  [提取结果]")
        print(f"  折现率: {data.discount_rate:.2%}")
        print(f"  剩余年限: {data.remaining_years} 年")
        print(f"  识别项目数: {len(data.projects)}")

        print(f"\n  [项目详情]")
        for i, proj in enumerate(data.projects, 1):
            print(f"\n    项目{i}: {proj.name}")
            print(f"      ADR: {proj.adr:.2f} 元/晚")
            print(f"      入住率: {proj.occupancy_rate:.1%}")
            print(f"      客房数: {proj.room_count} 间")
            print(f"      客房收入: {proj.room_revenue:.2f} 万元")
            print(f"      餐饮收入: {proj.fb_revenue:.2f} 万元")
            print(f"      OTA收入: {proj.ota_revenue:.2f} 万元")
            print(f"      运营费用: {proj.total_operating_expense:.2f} 万元")
            print(f"      GOP: {proj.calculate_gop():.2f} 万元")
            print(f"      年净收益: {proj.calculate_noicf():.2f} 万元")

        # 汇总
        agg = data.get_aggregate_data()
        print(f"\n  [汇总数据]")
        print(f"    客房收入合计: {agg['total_room_revenue']:.2f} 万元")
        print(f"    运营费用合计: {agg['total_operating_expense']:.2f} 万元")
        print(f"    年净收益合计: {agg['total_noicf']:.2f} 万元")
        print(f"    加权平均ADR: {agg['weighted_avg_adr']:.2f} 元")
        print(f"    加权平均入住率: {agg['weighted_avg_occupancy']:.1%}")

    except Exception as e:
        print(f"  [FAIL] 提取失败: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n" + "=" * 70)
    print("  诊断完成")
    print("=" * 70)

if __name__ == "__main__":
    main()
