#!/usr/bin/env python3
"""
测试酒店REIT专用提取器
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.parsers import DocumentParser
from src.parsers.hotel_extractor import HotelREITExtractor

def main():
    print("=" * 70)
    print("  华住REIT专用提取器测试")
    print("=" * 70)

    file_path = r"D:\AI投研工具\Claude Code\REITs_modeling by cc\input\华住募集说明书.pdf"

    print(f"\n>>> 解析文档: {file_path}")

    # 解析文档
    doc = DocumentParser().parse(file_path)
    print(f"  [OK] 文件类型: {doc.file_type}")
    print(f"  [OK] 页数: {doc.metadata.get('page_count', 'unknown')}")
    print(f"  [OK] 表格数: {len(doc.tables)}")

    # 使用专用提取器
    print("\n>>> 使用酒店REIT专用提取器...")
    extractor = HotelREITExtractor()
    data = extractor.extract(doc)

    # 显示提取结果
    print("\n" + "=" * 70)
    print("  提取结果")
    print("=" * 70)

    print(f"\n[全局参数]")
    print(f"  折现率: {data.discount_rate:.2%}")
    print(f"  剩余年限: {data.remaining_years} 年")
    print(f"  识别项目数: {len(data.projects)}")

    print(f"\n[项目详情]")
    for i, proj in enumerate(data.projects, 1):
        print(f"\n  项目{i}: {proj.name}")
        print(f"    ADR: {proj.adr:.2f} 元/晚")
        print(f"    入住率: {proj.occupancy_rate:.1%}")
        print(f"    客房数: {proj.room_count} 间")
        print(f"    客房收入: {proj.room_revenue:.2f} 万元")
        print(f"    餐饮收入: {proj.fb_revenue:.2f} 万元")
        print(f"    OTA收入: {proj.ota_revenue:.2f} 万元")
        print(f"    运营费用: {proj.total_operating_expense:.2f} 万元")
        print(f"    GOP: {proj.calculate_gop():.2f} 万元")
        print(f"    年净收益: {proj.calculate_noicf():.2f} 万元")

    # 汇总
    agg = data.get_aggregate_data()
    print(f"\n[汇总数据]")
    print(f"  客房收入合计: {agg['total_room_revenue']:.2f} 万元")
    print(f"  运营费用合计: {agg['total_operating_expense']:.2f} 万元")
    print(f"  年净收益合计: {agg['total_noicf']:.2f} 万元")
    print(f"  加权平均ADR: {agg['weighted_avg_adr']:.2f} 元")
    print(f"  加权平均入住率: {agg['weighted_avg_occupancy']:.1%}")

    # 生成报告
    print("\n>>> 生成提取报告...")
    report = extractor.generate_report()
    report_path = Path("./output/hotel_extraction_report.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"  [OK] 报告已保存: {report_path}")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
