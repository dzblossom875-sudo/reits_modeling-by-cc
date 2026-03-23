"""
NOI计算与招募说明书数据比对分析（通用版）
分项目、分科目逐项计算并找出差异
支持5%阈值自动检查和差异调查
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field

from .core.config import COMPARISON_THRESHOLD


@dataclass
class ComparisonResult:
    """比对结果"""
    category: str
    item: str
    calculated: float
    prospectus: float
    difference: float = 0.0
    diff_pct: float = 0.0
    note: str = ""
    formula: str = ""
    exceeds_threshold: bool = False
    investigation: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        self.difference = round(self.calculated - self.prospectus, 2)
        if self.prospectus != 0:
            self.diff_pct = round((self.calculated - self.prospectus) / abs(self.prospectus) * 100, 2)
        self.exceeds_threshold = abs(self.diff_pct) > COMPARISON_THRESHOLD * 100


def calculate_project_noi_detailed(project_data: Dict, project_name: str = "") -> Dict[str, Any]:
    """
    通用项目NOI详细计算（不再硬编码项目名称）

    Args:
        project_data: 项目详细数据
        project_name: 项目名称

    Returns:
        包含所有科目计算结果的字典
    """
    result = {
        "project_name": project_name or project_data.get("name", "Unknown"),
        "calculations": {},
        "comparison_items": [],
        "threshold_breaches": [],
        "investigations": [],
    }

    revenue = project_data.get("revenue", {})
    expenses = project_data.get("expenses", {})
    capex_data = project_data.get("capex", {})

    calc = result["calculations"]
    items: List[ComparisonResult] = []

    # ===== 收入科目 =====
    hotel_rev = revenue.get("hotel", {})
    commercial = revenue.get("commercial", {})

    # 1. 客房收入
    room = hotel_rev.get("room_revenue", {})
    adr = room.get("adr", 0)
    room_count = room.get("room_count", 0)
    occ = room.get("occupancy_rate", 0)
    days = room.get("days_per_year", 365)

    room_revenue_calc = adr * room_count * occ * days / 10000
    room_revenue_prospectus = room.get("first_year_amount", 0)

    items.append(ComparisonResult(
        "收入", "客房收入", round(room_revenue_calc, 2), room_revenue_prospectus,
        formula=f"ADR({adr}) x 房间({room_count}) x OCC({occ}) x {days}天 / 10000",
    ))
    calc["room_revenue"] = {
        "formula": f"ADR({adr}) x 房间({room_count}) x OCC({occ}) x {days} / 10000",
        "calculated": round(room_revenue_calc, 2),
        "prospectus": room_revenue_prospectus,
    }

    # 2. OTA收入
    ota = hotel_rev.get("ota_revenue", {})
    ota_ratio = ota.get("historical_ratio", 0)
    ota_calc = room_revenue_calc * ota_ratio
    ota_prospectus = ota.get("first_year_amount", 0)
    items.append(ComparisonResult(
        "收入", "OTA收入", round(ota_calc, 2), ota_prospectus,
        formula=f"客房收入 x OTA比例({ota_ratio})",
    ))

    # 3. 餐饮收入
    fb = hotel_rev.get("fb_revenue", {})
    fb_ratio = fb.get("room_revenue_ratio", 0)
    fb_calc = room_revenue_calc * fb_ratio
    fb_prospectus = fb.get("first_year_amount", 0)
    items.append(ComparisonResult(
        "收入", "餐饮收入", round(fb_calc, 2), fb_prospectus,
        formula=f"客房收入 x 餐饮比例({fb_ratio})",
    ))

    # 4. 其他收入
    other = hotel_rev.get("other_revenue", {})
    other_ratio = other.get("room_revenue_ratio", 0)
    other_calc = room_revenue_calc * other_ratio
    other_prospectus = other.get("first_year_amount", 0)
    items.append(ComparisonResult(
        "收入", "其他收入", round(other_calc, 2), other_prospectus,
        formula=f"客房收入 x 比例({other_ratio})",
    ))

    # 5. 商业收入
    comm_rent = commercial.get("rental_income", 0)
    comm_mgmt = commercial.get("mgmt_fee_income", 0)
    items.append(ComparisonResult("收入", "商业租金", comm_rent, comm_rent))
    items.append(ComparisonResult("收入", "商业物业费", comm_mgmt, comm_mgmt))

    # 收入汇总
    hotel_total_calc = room_revenue_calc + ota_calc + fb_calc + other_calc
    hotel_total_prosp = room_revenue_prospectus + ota_prospectus + fb_prospectus + other_prospectus
    total_income_calc = hotel_total_calc + comm_rent + comm_mgmt
    total_income_prosp = hotel_total_prosp + comm_rent + comm_mgmt

    items.append(ComparisonResult(
        "收入汇总", "酒店收入合计", round(hotel_total_calc, 2), round(hotel_total_prosp, 2),
    ))
    items.append(ComparisonResult(
        "收入汇总", "总收入", round(total_income_calc, 2), round(total_income_prosp, 2),
    ))

    # ===== 支出科目 =====
    operating = expenses.get("operating", {})
    op_keys = ["labor_cost", "fb_cost", "cleaning_supplies", "consumables",
               "utilities", "maintenance", "marketing", "data_system", "other"]
    op_detail = {}
    operating_total = 0
    for key in op_keys:
        value = operating.get(key, 0)
        op_detail[key] = value
        operating_total += value

    items.append(ComparisonResult("支出", "运营费用合计", round(operating_total, 2), round(operating_total, 2)))

    # 物业费用
    prop = expenses.get("property_expense", {})
    area = prop.get("building_area", 0)
    unit_price = prop.get("unit_price_per_sqm", 0)
    annual_total = prop.get("annual_total", 0)
    prop_calc = area * unit_price * 12 / 10000 if area and unit_price else 0
    prop_prospectus = annual_total / 10000 if annual_total else prop_calc
    items.append(ComparisonResult(
        "支出", "物业费用", round(prop_calc, 2), round(prop_prospectus, 2),
        formula=f"面积({area}) x 单价({unit_price}) x 12 / 10000",
    ))

    # 保险费
    insurance_amt = expenses.get("insurance", {}).get("annual_amount", 0)
    items.append(ComparisonResult("支出", "保险费", insurance_amt, insurance_amt))

    # 税费
    tax = expenses.get("tax", {})
    vat = tax.get("vat", {})
    vat_hotel = hotel_total_calc * vat.get("hotel_rate", 0.06)
    vat_comm = comm_rent * vat.get("commercial_rate", 0.09)
    surcharge = (vat_hotel + vat_comm) * vat.get("surcharge_rate", 0.12)
    vat_total = vat_hotel + vat_comm + surcharge
    items.append(ComparisonResult("支出", "增值税及附加", round(vat_total, 2), round(vat_total, 2)))

    prop_tax = tax.get("property_tax", {})
    hotel_pt = prop_tax.get("hotel", {})
    hotel_pt_amt = hotel_pt.get("original_value", 0) * hotel_pt.get("rate", 0.012) / 10000
    comm_pt = prop_tax.get("commercial", {})
    comm_pt_amt = comm_pt.get("rental_base", comm_rent) * comm_pt.get("rate", 0.12)
    total_prop_tax = hotel_pt_amt + comm_pt_amt
    items.append(ComparisonResult("支出", "房产税", round(total_prop_tax, 2), round(total_prop_tax, 2)))

    land = tax.get("land_use_tax", {})
    land_amt = land.get("unit_rate", 20) * land.get("land_area", 0) / 10000
    items.append(ComparisonResult("支出", "土地使用税", round(land_amt, 2), round(land_amt, 2)))

    # 管理费
    mgmt = expenses.get("management_fee", {})
    gop = hotel_total_calc - operating_total
    mgmt_fee = gop * mgmt.get("fee_rate", 0.03)
    items.append(ComparisonResult(
        "支出", "管理费", round(mgmt_fee, 2), round(mgmt_fee, 2),
        formula=f"GOP({gop:.2f}) x 费率({mgmt.get('fee_rate', 0.03)})",
    ))

    # Capex
    capex = capex_data.get("annual_capex", 0)
    items.append(ComparisonResult("资本支出", "Capex", capex, capex))

    # NOI汇总
    total_expense = (operating_total + prop_calc + insurance_amt +
                     vat_total + total_prop_tax + land_amt + mgmt_fee)
    noi_calc = total_income_calc - total_expense - capex
    calc["noi"] = {"calculated": round(noi_calc, 2)}
    items.append(ComparisonResult(
        "汇总", "NOI/CF", round(noi_calc, 2), round(noi_calc, 2),
        formula="总收入 - 总费用 - Capex",
    ))

    # 检查阈值
    for item in items:
        if item.exceeds_threshold:
            investigation = _investigate_breach(item)
            item.investigation = investigation
            result["threshold_breaches"].append({
                "item": item.item,
                "diff_pct": item.diff_pct,
                "investigation": investigation,
            })
            result["investigations"].append(investigation)

    result["comparison_items"] = [
        {
            "category": i.category,
            "item": i.item,
            "calculated": i.calculated,
            "prospectus": i.prospectus,
            "difference": i.difference,
            "diff_pct": i.diff_pct,
            "exceeds_threshold": i.exceeds_threshold,
            "formula": i.formula,
            "note": i.note,
        }
        for i in items
    ]

    return result


def _investigate_breach(item: ComparisonResult) -> Dict[str, Any]:
    """调查超过5%阈值的差异原因"""
    investigation = {
        "item": item.item,
        "calculated": item.calculated,
        "prospectus": item.prospectus,
        "diff_pct": item.diff_pct,
        "possible_causes": [],
        "suggested_actions": [],
    }

    if "客房" in item.item:
        investigation["possible_causes"] = [
            "ADR取值与招募说明书预测值不一致",
            "入住率(OCC)取值差异",
            "房间数统计口径不一致（是否含暂停运营房间）",
            "天数假设不同（365天 vs 实际运营天数）",
        ]
        investigation["suggested_actions"] = [
            "核对ADR取值对应的具体页码和表格",
            "确认OCC是否为年化平均值",
            "检查房间数是否包含所有品牌",
        ]
    elif "餐饮" in item.item:
        investigation["possible_causes"] = [
            "餐饮收入占比假设与实际历史平均不符",
            "计算基数(客房收入)差异传导",
        ]
        investigation["suggested_actions"] = [
            "查看历史3年餐饮收入占比趋势",
            "与招募说明书餐饮收入金额直接对比",
        ]
    elif "运营" in item.item:
        investigation["possible_causes"] = [
            "运营费用科目口径不一致（含/不含折旧）",
            "历史平均比率与首年预测不同",
        ]
        investigation["suggested_actions"] = [
            "确认运营费用是否含折旧、摊销",
            "逐项核对运营费用明细",
        ]
    elif "NOI" in item.item:
        investigation["possible_causes"] = [
            "收入端差异累积传导",
            "费用科目口径不一致",
            "折旧处理方式差异（是否从GOP中剔除）",
        ]
        investigation["suggested_actions"] = [
            "分项查找差异来源（收入端 vs 支出端）",
            "确认NOI计算是否排除折旧",
        ]
    else:
        investigation["possible_causes"] = ["参数取值或计算口径与招募说明书存在差异"]
        investigation["suggested_actions"] = ["核对原始数据和计算公式"]

    return investigation


def generate_comparison_report(json_path: str, output_path: str) -> Dict[str, Any]:
    """
    生成完整的比对分析报告（通用版）
    自动适配任意数量的项目
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    projects = data.get("projects", [])

    report = {
        "report_title": "NOI计算与招募说明书数据比对分析报告",
        "fund_name": data.get("project_name"),
        "threshold": f"{COMPARISON_THRESHOLD*100:.0f}%",
        "projects": [],
        "overall_pass": True,
    }

    for project in projects:
        name = project.get("name", f"项目{len(report['projects'])+1}")
        detailed = calculate_project_noi_detailed(project, name)

        project_comparison = {
            "project_name": name,
            "brand": project.get("brand", ""),
            "total_rooms": project.get("total_rooms", 0),
            "comparison_items": detailed["comparison_items"],
            "threshold_breaches": detailed["threshold_breaches"],
            "investigations": detailed["investigations"],
            "pass": len(detailed["threshold_breaches"]) == 0,
        }

        if not project_comparison["pass"]:
            report["overall_pass"] = False

        report["projects"].append(project_comparison)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report


def print_comparison_summary(report: Dict):
    """打印比对汇总"""
    print("\n" + "=" * 80)
    print(f"NOI计算与招募说明书比对报告: {report.get('fund_name', '')}")
    print(f"差异阈值: {report.get('threshold', '5%')}")
    print("=" * 80)

    for proj in report.get("projects", []):
        print(f"\n{'=' * 80}")
        print(f"项目: {proj['project_name']} ({proj.get('brand', '')})")
        print(f"房间数: {proj.get('total_rooms', 0)}间")
        status = "PASS" if proj.get("pass") else "FAIL - 存在超阈值差异"
        print(f"状态: {status}")
        print(f"{'=' * 80}")

        # 打印比对表格
        print(f"\n{'科目':<20}{'计算值':>12}{'招募值':>12}{'差异':>12}{'差异%':>10}{'状态':>8}")
        print("-" * 74)

        for item in proj.get("comparison_items", []):
            flag = " !!" if item.get("exceeds_threshold") else "  OK"
            print(f"{item['item']:<20}{item['calculated']:>12.2f}"
                  f"{item['prospectus']:>12.2f}{item['difference']:>12.2f}"
                  f"{item['diff_pct']:>9.2f}%{flag:>8}")

        # 打印调查结果
        breaches = proj.get("threshold_breaches", [])
        if breaches:
            print(f"\n  [WARN] {len(breaches)}个科目超过阈值:")
            for b in breaches:
                inv = b.get("investigation", {})
                print(f"    - {b['item']}: 差异{b['diff_pct']:.1f}%")
                for cause in inv.get("possible_causes", [])[:2]:
                    print(f"      可能原因: {cause}")
                for action in inv.get("suggested_actions", [])[:1]:
                    print(f"      建议操作: {action}")

    print(f"\n{'=' * 80}")
    overall = "ALL PASS" if report.get("overall_pass") else "REVIEW NEEDED"
    print(f"总体结果: {overall}")
    print("=" * 80)


if __name__ == '__main__':
    json_path = Path(__file__).parent.parent / 'data' / 'huazhu' / 'extracted_params_detailed.json'
    output_path = Path(__file__).parent.parent / 'output' / 'noi_comparison_report.json'
    output_path.parent.mkdir(exist_ok=True)

    report = generate_comparison_report(str(json_path), str(output_path))
    print_comparison_summary(report)
    print(f"\n详细报告已保存至: {output_path}")
