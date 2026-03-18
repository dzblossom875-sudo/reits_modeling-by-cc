"""
NOI计算与招募说明书数据比对分析
分项目、分科目逐项计算并找出差异
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass


@dataclass
class ComparisonResult:
    """比对结果"""
    category: str           # 科目类别
    item: str              # 具体项目
    calculated: float      # 计算值
    prospectus: float      # 招募说明书值
    difference: float      # 差异
    diff_pct: float        # 差异百分比
    note: str = ""         # 备注


def calculate_guangzhou_noi_detailed(project_data: Dict) -> Dict[str, Any]:
    """广州项目详细NOI计算（分科目）"""
    result = {
        "project_name": project_data.get("name"),
        "calculations": {}
    }

    revenue = project_data.get("revenue", {})
    expenses = project_data.get("expenses", {})
    capex_data = project_data.get("capex", {})

    # ===== 收入科目详细计算 =====
    calc = result["calculations"]

    # 1. 客房收入
    room = revenue.get("hotel", {}).get("room_revenue", {})
    adr = room.get("adr", 0)
    room_count = room.get("room_count", 0)
    occ = room.get("occupancy_rate", 0)
    days = room.get("days_per_year", 365)

    room_revenue_calc = adr * room_count * occ * days / 10000
    room_revenue_prospectus = room.get("first_year_amount", 0)

    calc["room_revenue"] = {
        "formula": f"ADR({adr}) × 房间数({room_count}) × OCC({occ}) × 天数({days}) / 10000",
        "calculated": round(room_revenue_calc, 2),
        "prospectus": room_revenue_prospectus,
        "difference": round(room_revenue_calc - room_revenue_prospectus, 2),
        "diff_pct": round((room_revenue_calc - room_revenue_prospectus) / room_revenue_prospectus * 100, 2) if room_revenue_prospectus else 0
    }

    # 2. OTA收入
    ota = revenue.get("hotel", {}).get("ota_revenue", {})
    ota_ratio = ota.get("historical_ratio", 0)
    ota_calc = room_revenue_calc * ota_ratio
    ota_prospectus = ota.get("first_year_amount", 0)

    calc["ota_revenue"] = {
        "formula": f"客房收入({room_revenue_calc:.2f}) × OTA比例({ota_ratio})",
        "calculated": round(ota_calc, 2),
        "prospectus": ota_prospectus,
        "difference": round(ota_calc - ota_prospectus, 2),
        "diff_pct": round((ota_calc - ota_prospectus) / ota_prospectus * 100, 2) if ota_prospectus else 0,
        "note": "招募说明书显示OTA占比为0"
    }

    # 3. 餐饮收入
    fb = revenue.get("hotel", {}).get("fb_revenue", {})
    fb_ratio = fb.get("room_revenue_ratio", 0)
    fb_calc = room_revenue_calc * fb_ratio
    fb_prospectus = fb.get("first_year_amount", 0)

    calc["fb_revenue"] = {
        "formula": f"客房收入({room_revenue_calc:.2f}) × 餐饮比例({fb_ratio})",
        "calculated": round(fb_calc, 2),
        "prospectus": fb_prospectus,
        "difference": round(fb_calc - fb_prospectus, 2),
        "diff_pct": round((fb_calc - fb_prospectus) / fb_prospectus * 100, 2) if fb_prospectus else 0
    }

    # 4. 其他收入
    other = revenue.get("hotel", {}).get("other_revenue", {})
    other_ratio = other.get("room_revenue_ratio", 0)
    other_calc = room_revenue_calc * other_ratio
    other_prospectus = other.get("first_year_amount", 0)

    calc["other_revenue"] = {
        "formula": f"客房收入({room_revenue_calc:.2f}) × 其他收入比例({other_ratio})",
        "calculated": round(other_calc, 2),
        "prospectus": other_prospectus,
        "difference": round(other_calc - other_prospectus, 2),
        "diff_pct": round((other_calc - other_prospectus) / other_prospectus * 100, 2) if other_prospectus else 0
    }

    # 5. 商业收入
    commercial = revenue.get("commercial", {})
    commercial_rent = commercial.get("rental_income", 0)
    commercial_mgmt = commercial.get("mgmt_fee_income", 0)
    commercial_total = commercial_rent + commercial_mgmt

    calc["commercial_revenue"] = {
        "formula": f"租金收入({commercial_rent}) + 物业费({commercial_mgmt})",
        "calculated": round(commercial_total, 2),
        "prospectus": round(commercial_rent + commercial_mgmt, 2),  # 使用相同数据
        "difference": 0,
        "diff_pct": 0,
        "rental_income": commercial_rent,
        "mgmt_fee_income": commercial_mgmt
    }

    # 酒店总收入
    hotel_revenue_calc = room_revenue_calc + ota_calc + fb_calc + other_calc
    hotel_revenue_prospectus = room_revenue_prospectus + ota_prospectus + fb_prospectus + other_prospectus

    calc["total_hotel_revenue"] = {
        "calculated": round(hotel_revenue_calc, 2),
        "prospectus": round(hotel_revenue_prospectus, 2),
        "difference": round(hotel_revenue_calc - hotel_revenue_prospectus, 2),
        "diff_pct": round((hotel_revenue_calc - hotel_revenue_prospectus) / hotel_revenue_prospectus * 100, 2) if hotel_revenue_prospectus else 0
    }

    # 总收入
    total_income_calc = hotel_revenue_calc + commercial_total
    calc["total_income"] = {
        "calculated": round(total_income_calc, 2),
        "prospectus": 13187.36,  # Page 172
        "difference": round(total_income_calc - 13187.36, 2),
        "diff_pct": round((total_income_calc - 13187.36) / 13187.36 * 100, 2)
    }

    # ===== 费用科目详细计算 =====

    # 1. 运营费用明细
    operating = expenses.get("operating", {})
    operating_detail = {}
    operating_total = 0

    operating_items = [
        ("labor_cost", "人工成本"),
        ("fb_cost", "餐饮成本"),
        ("cleaning_supplies", "清洁物料"),
        ("consumables", "耗材"),
        ("utilities", "能源费用"),
        ("maintenance", "维护费"),
        ("marketing", "营销推广"),
        ("data_system", "数据系统"),
        ("other", "其他费用")
    ]

    for key, name in operating_items:
        value = operating.get(key, 0)
        operating_detail[key] = {"name": name, "value": value}
        operating_total += value

    calc["operating_expenses"] = {
        "detail": operating_detail,
        "total_calculated": round(operating_total, 2),
        "historical_ratio": operating.get("historical_avg_ratio", 0)
    }

    # 2. 物业费用
    prop = expenses.get("property_expense", {})
    area = prop.get("building_area", 0)
    unit_price = prop.get("unit_price_per_sqm", 0)
    annual_total = prop.get("annual_total", 0)

    prop_calc = area * unit_price * 12 / 10000  # 万元
    prop_prospectus = annual_total / 10000 if annual_total else prop_calc

    calc["property_expense"] = {
        "formula": f"建筑面积({area}) × 单价({unit_price}) × 12 / 10000",
        "calculated": round(prop_calc, 2),
        "prospectus": round(prop_prospectus, 2),
        "difference": round(prop_calc - prop_prospectus, 2),
        "diff_pct": round((prop_calc - prop_prospectus) / prop_prospectus * 100, 2) if prop_prospectus else 0
    }

    # 3. 保险费
    insurance = expenses.get("insurance", {})
    insurance_amount = insurance.get("annual_amount", 0)

    calc["insurance"] = {
        "calculated": insurance_amount,
        "prospectus": insurance_amount,
        "difference": 0
    }

    # 4. 税费详细计算
    tax = expenses.get("tax", {})

    # 4.1 增值税
    vat = tax.get("vat", {})
    vat_hotel_rate = vat.get("hotel_rate", 0.06)
    vat_commercial_rate = vat.get("commercial_rate", 0.09)
    surcharge_rate = vat.get("surcharge_rate", 0.12)

    vat_hotel = hotel_revenue_calc * vat_hotel_rate
    vat_commercial = commercial_rent * vat_commercial_rate
    vat_total = vat_hotel + vat_commercial
    surcharge = vat_total * surcharge_rate
    vat_and_surcharge = vat_total + surcharge

    calc["tax_vat"] = {
        "vat_hotel": round(vat_hotel, 2),
        "vat_commercial": round(vat_commercial, 2),
        "surcharge": round(surcharge, 2),
        "total": round(vat_and_surcharge, 2)
    }

    # 4.2 房产税
    prop_tax = tax.get("property_tax", {})

    # 酒店部分（从价）
    hotel_prop = prop_tax.get("hotel", {})
    hotel_prop_base = hotel_prop.get("original_value", 0)
    hotel_prop_rate = hotel_prop.get("rate", 0.012)
    hotel_prop_tax = hotel_prop_base * hotel_prop_rate / 10000  # 万元

    # 商业部分（从租）
    commercial_prop = prop_tax.get("commercial", {})
    commercial_rent_base = commercial_prop.get("rental_base", commercial_rent)
    commercial_prop_rate = commercial_prop.get("rate", 0.12)
    commercial_prop_tax = commercial_rent_base * commercial_prop_rate

    total_property_tax = hotel_prop_tax + commercial_prop_tax

    calc["tax_property"] = {
        "hotel_from_value": round(hotel_prop_tax, 2),
        "commercial_from_rent": round(commercial_prop_tax, 2),
        "total": round(total_property_tax, 2)
    }

    # 4.3 土地使用税
    land_tax = tax.get("land_use_tax", {})
    land_rate = land_tax.get("unit_rate", 20)
    land_area = land_tax.get("land_area", 0)
    land_tax_amount = land_rate * land_area / 10000  # 万元

    calc["tax_land"] = {
        "unit_rate": land_rate,
        "land_area": land_area,
        "total": round(land_tax_amount, 2)
    }

    # 税费合计
    total_tax = vat_and_surcharge + total_property_tax + land_tax_amount
    calc["tax_total"] = {
        "calculated": round(total_tax, 2),
        "note": "招募说明书Page 172显示成本合计11085.75万元，包含折旧5421.06万元"
    }

    # 5. 管理费
    mgmt = expenses.get("management_fee", {})
    mgmt_rate = mgmt.get("fee_rate", 0.03)
    gop = hotel_revenue_calc - operating_total
    mgmt_fee = gop * mgmt_rate

    calc["management_fee"] = {
        "gop": round(gop, 2),
        "rate": mgmt_rate,
        "calculated": round(mgmt_fee, 2)
    }

    # 总费用
    total_expense = operating_total + prop_calc + insurance_amount + total_tax + mgmt_fee
    calc["total_expenses"] = {
        "calculated": round(total_expense, 2),
        "note": "不含折旧（折旧已从GOP中剔除）"
    }

    # ===== Capex =====
    capex = capex_data.get("annual_capex", 0)
    calc["capex"] = {
        "value": capex,
        "source": "招募说明书预测"
    }

    # ===== NOI计算 =====
    noi = total_income_calc - total_expense - capex
    calc["noi"] = {
        "formula": "总收入 - 总费用 - Capex",
        "calculated": round(noi, 2),
        "note": "需与招募说明书NOI进行比对"
    }

    return result


def calculate_shanghai_noi_detailed(project_data: Dict) -> Dict[str, Any]:
    """上海项目详细NOI计算（分科目）"""
    result = {
        "project_name": project_data.get("name"),
        "calculations": {}
    }

    revenue = project_data.get("revenue", {})
    expenses = project_data.get("expenses", {})
    capex_data = project_data.get("capex", {})

    calc = result["calculations"]

    # ===== 收入科目详细计算 =====

    # 1. 客房收入
    room = revenue.get("hotel", {}).get("room_revenue", {})
    adr = room.get("adr", 0)
    room_count = room.get("room_count", 0)
    occ = room.get("occupancy_rate", 0)
    days = room.get("days_per_year", 365)

    room_revenue_calc = adr * room_count * occ * days / 10000
    room_revenue_prospectus = room.get("first_year_amount", 0)

    calc["room_revenue"] = {
        "formula": f"ADR({adr}) × 房间数({room_count}) × OCC({occ}) × 天数({days}) / 10000",
        "calculated": round(room_revenue_calc, 2),
        "prospectus": room_revenue_prospectus,
        "difference": round(room_revenue_calc - room_revenue_prospectus, 2),
        "diff_pct": round((room_revenue_calc - room_revenue_prospectus) / room_revenue_prospectus * 100, 2) if room_revenue_prospectus else 0
    }

    # 2. OTA收入
    ota = revenue.get("hotel", {}).get("ota_revenue", {})
    ota_ratio = ota.get("historical_ratio", 0)
    ota_calc = room_revenue_calc * ota_ratio
    ota_prospectus = ota.get("first_year_amount", 0)

    calc["ota_revenue"] = {
        "calculated": round(ota_calc, 2),
        "prospectus": ota_prospectus,
        "difference": round(ota_calc - ota_prospectus, 2),
        "note": "OTA占比为0"
    }

    # 3. 餐饮收入
    fb = revenue.get("hotel", {}).get("fb_revenue", {})
    fb_ratio = fb.get("room_revenue_ratio", 0)
    fb_calc = room_revenue_calc * fb_ratio
    fb_prospectus = fb.get("first_year_amount", 0)

    calc["fb_revenue"] = {
        "calculated": round(fb_calc, 2),
        "prospectus": fb_prospectus,
        "difference": round(fb_calc - fb_prospectus, 2),
        "diff_pct": round((fb_calc - fb_prospectus) / fb_prospectus * 100, 2) if fb_prospectus else 0
    }

    # 4. 其他收入
    other = revenue.get("hotel", {}).get("other_revenue", {})
    other_ratio = other.get("room_revenue_ratio", 0)
    other_calc = room_revenue_calc * other_ratio
    other_prospectus = other.get("first_year_amount", 0)

    calc["other_revenue"] = {
        "calculated": round(other_calc, 2),
        "prospectus": other_prospectus,
        "difference": round(other_calc - other_prospectus, 2),
        "diff_pct": round((other_calc - other_prospectus) / other_prospectus * 100, 2) if other_prospectus else 0
    }

    # 5. 商业收入
    commercial = revenue.get("commercial", {})
    commercial_rent = commercial.get("rental_income", 0)
    commercial_mgmt = commercial.get("mgmt_fee_income", 0)
    commercial_total = commercial_rent + commercial_mgmt

    calc["commercial_revenue"] = {
        "calculated": round(commercial_total, 2),
        "prospectus": round(commercial_rent + commercial_mgmt, 2),
        "rental_income": commercial_rent,
        "mgmt_fee_income": commercial_mgmt
    }

    # 酒店总收入
    hotel_revenue_calc = room_revenue_calc + ota_calc + fb_calc + other_calc
    calc["total_hotel_revenue"] = {
        "calculated": round(hotel_revenue_calc, 2),
        "prospectus": 3269.87  # Page 184 营业收入
    }

    # 总收入
    total_income_calc = hotel_revenue_calc + commercial_total
    calc["total_income"] = {
        "calculated": round(total_income_calc, 2),
        "prospectus": 3313.82,  # Page 184
        "difference": round(total_income_calc - 3313.82, 2),
        "diff_pct": round((total_income_calc - 3313.82) / 3313.82 * 100, 2)
    }

    # ===== 费用科目详细计算 =====

    # 运营费用明细
    operating = expenses.get("operating", {})
    operating_detail = {}
    operating_total = 0

    operating_items = [
        ("labor_cost", "人工成本"),
        ("fb_cost", "餐饮成本"),
        ("cleaning_supplies", "清洁物料"),
        ("consumables", "耗材"),
        ("utilities", "能源费用"),
        ("maintenance", "维护费"),
        ("marketing", "营销推广"),
        ("data_system", "数据系统"),
        ("other", "其他费用")
    ]

    for key, name in operating_items:
        value = operating.get(key, 0)
        operating_detail[key] = {"name": name, "value": value}
        operating_total += value

    calc["operating_expenses"] = {
        "detail": operating_detail,
        "total_calculated": round(operating_total, 2)
    }

    # 物业费用
    prop = expenses.get("property_expense", {})
    area = prop.get("building_area", 0)
    unit_price = prop.get("unit_price_per_sqm", 0)
    annual_total = prop.get("annual_total", 0)

    prop_calc = area * unit_price * 12 / 10000
    prop_prospectus = annual_total / 10000 if annual_total else prop_calc

    calc["property_expense"] = {
        "calculated": round(prop_calc, 2),
        "prospectus": round(prop_prospectus, 2)
    }

    # 保险费
    insurance = expenses.get("insurance", {})
    insurance_amount = insurance.get("annual_amount", 0)
    calc["insurance"] = {"value": insurance_amount}

    # 税费计算
    tax = expenses.get("tax", {})

    # 增值税
    vat = tax.get("vat", {})
    vat_hotel = hotel_revenue_calc * vat.get("hotel_rate", 0.06)
    vat_commercial = commercial_rent * vat.get("commercial_rate", 0.09)
    vat_total = vat_hotel + vat_commercial
    surcharge = vat_total * vat.get("surcharge_rate", 0.12)
    vat_and_surcharge = vat_total + surcharge

    calc["tax_vat"] = {
        "vat_hotel": round(vat_hotel, 2),
        "vat_commercial": round(vat_commercial, 2),
        "surcharge": round(surcharge, 2),
        "total": round(vat_and_surcharge, 2)
    }

    # 房产税
    prop_tax = tax.get("property_tax", {})
    hotel_prop = prop_tax.get("hotel", {})
    hotel_prop_base = hotel_prop.get("original_value", 0)
    hotel_prop_tax = hotel_prop_base * hotel_prop.get("rate", 0.012) / 10000

    commercial_prop = prop_tax.get("commercial", {})
    commercial_rent_base = commercial_prop.get("rental_base", commercial_rent)
    commercial_prop_tax = commercial_rent_base * commercial_prop.get("rate", 0.12)

    total_property_tax = hotel_prop_tax + commercial_prop_tax

    calc["tax_property"] = {
        "hotel_from_value": round(hotel_prop_tax, 2),
        "commercial_from_rent": round(commercial_prop_tax, 2),
        "total": round(total_property_tax, 2)
    }

    # 土地使用税
    land_tax = tax.get("land_use_tax", {})
    land_rate = land_tax.get("unit_rate", 20)
    land_area = land_tax.get("land_area", 0)
    land_tax_amount = land_rate * land_area / 10000

    calc["tax_land"] = {"total": round(land_tax_amount, 2)}

    # 税费合计
    total_tax = vat_and_surcharge + total_property_tax + land_tax_amount
    calc["tax_total"] = {
        "calculated": round(total_tax, 2),
        "note": "招募说明书Page 184显示成本2465.42万元，含折旧802.04万元"
    }

    # 管理费
    mgmt = expenses.get("management_fee", {})
    mgmt_rate = mgmt.get("fee_rate", 0.03)
    gop = hotel_revenue_calc - operating_total
    mgmt_fee = gop * mgmt_rate

    calc["management_fee"] = {
        "gop": round(gop, 2),
        "rate": mgmt_rate,
        "calculated": round(mgmt_fee, 2)
    }

    # 总费用
    total_expense = operating_total + prop_calc + insurance_amount + total_tax + mgmt_fee
    calc["total_expenses"] = {
        "calculated": round(total_expense, 2)
    }

    # Capex
    capex = capex_data.get("annual_capex", 0)
    calc["capex"] = {"value": capex}

    # NOI
    noi = total_income_calc - total_expense - capex
    calc["noi"] = {
        "calculated": round(noi, 2)
    }

    return result


def generate_comparison_report(json_path: str, output_path: str):
    """生成完整的比对分析报告"""

    # 加载数据
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    projects = data.get("projects", [])

    report = {
        "report_title": "NOI计算与招募说明书数据比对分析报告",
        "fund_name": data.get("project_name"),
        "comparison_date": "2025",
        "projects": []
    }

    for project in projects:
        if project.get("name") == "广州项目":
            detailed = calculate_guangzhou_noi_detailed(project)
        elif project.get("name") == "上海项目":
            detailed = calculate_shanghai_noi_detailed(project)
        else:
            continue

        project_comparison = {
            "project_name": project.get("name"),
            "brand": project.get("brand"),
            "total_rooms": project.get("total_rooms"),
            "detailed_calculations": detailed["calculations"],
            "key_differences": []
        }

        report["projects"].append(project_comparison)

    # 保存报告
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report


def print_comparison_summary(report: Dict):
    """打印比对汇总"""
    print("\n" + "="*80)
    print(f"NOI计算与招募说明书比对报告: {report['fund_name']}")
    print("="*80)

    for proj in report["projects"]:
        print(f"\n{'='*80}")
        print(f"项目: {proj['project_name']} ({proj['brand']})")
        print(f"房间数: {proj['total_rooms']}间")
        print(f"{'='*80}")

        calc = proj["detailed_calculations"]

        # 收入比对
        print("\n【收入科目比对】")
        print("-" * 80)
        print(f"{'科目':<20}{'计算值':>12}{'招募值':>12}{'差异':>12}{'差异%':>10}")
        print("-" * 80)

        revenue_items = [
            ("客房收入", calc.get("room_revenue", {})),
            ("OTA收入", calc.get("ota_revenue", {})),
            ("餐饮收入", calc.get("fb_revenue", {})),
            ("其他收入", calc.get("other_revenue", {})),
        ]

        for name, item in revenue_items:
            if item:
                calc_val = item.get("calculated", 0)
                prop_val = item.get("prospectus", 0)
                diff = item.get("difference", calc_val - prop_val)
                diff_pct = item.get("diff_pct", 0)
                print(f"{name:<20}{calc_val:>12.2f}{prop_val:>12.2f}{diff:>12.2f}{diff_pct:>9.2f}%")

        # 商业收入
        comm = calc.get("commercial_revenue", {})
        if comm:
            print(f"{'商业租金':<20}{comm.get('rental_income', 0):>12.2f}{comm.get('rental_income', 0):>12.2f}{0:>12.2f}{0:>10.2f}%")
            print(f"{'商业物业费':<20}{comm.get('mgmt_fee_income', 0):>12.2f}{comm.get('mgmt_fee_income', 0):>12.2f}{0:>12.2f}{0:>10.2f}%")

        # 总收入
        total = calc.get("total_income", {})
        if total:
            print("-" * 80)
            calc_val = total.get("calculated", 0)
            prop_val = total.get("prospectus", 0)
            diff = total.get("difference", 0)
            diff_pct = total.get("diff_pct", 0)
            print(f"{'总收入':<20}{calc_val:>12.2f}{prop_val:>12.2f}{diff:>12.2f}{diff_pct:>9.2f}%")

        # 费用比对
        print("\n【费用科目比对】")
        print("-" * 80)

        # 运营费用明细
        op = calc.get("operating_expenses", {})
        if op and "detail" in op:
            print("运营费用明细:")
            for key, item in op["detail"].items():
                print(f"  {item['name']:<16}{item['value']:>12.2f}万元")
            print(f"  {'运营费用合计':<16}{op.get('total_calculated', 0):>12.2f}万元")

        # 税费
        tax = calc.get("tax_vat", {})
        if tax:
            print(f"\n税费明细:")
            print(f"  酒店增值税: {tax.get('vat_hotel', 0):.2f}万元")
            print(f"  商业增值税: {tax.get('vat_commercial', 0):.2f}万元")
            print(f"  附加税: {tax.get('surcharge', 0):.2f}万元")
            print(f"  增值税合计: {tax.get('total', 0):.2f}万元")

        tax_prop = calc.get("tax_property", {})
        if tax_prop:
            print(f"  酒店房产税(从价): {tax_prop.get('hotel_from_value', 0):.2f}万元")
            print(f"  商业房产税(从租): {tax_prop.get('commercial_from_rent', 0):.2f}万元")
            print(f"  房产税合计: {tax_prop.get('total', 0):.2f}万元")

        tax_land = calc.get("tax_land", {})
        if tax_land:
            print(f"  土地使用税: {tax_land.get('total', 0):.2f}万元")

        # 管理费
        mgmt = calc.get("management_fee", {})
        if mgmt:
            print(f"\n管理费:")
            print(f"  GOP: {mgmt.get('gop', 0):.2f}万元")
            print(f"  费率: {mgmt.get('rate', 0)*100:.1f}%")
            print(f"  管理费: {mgmt.get('calculated', 0):.2f}万元")

        # 物业费用
        prop = calc.get("property_expense", {})
        if prop:
            print(f"\n物业费用: {prop.get('calculated', 0):.2f}万元")

        # 保险费
        ins = calc.get("insurance", {})
        if ins:
            print(f"保险费: {ins.get('value', 0):.2f}万元")

        # NOI
        noi = calc.get("noi", {})
        if noi:
            print("\n" + "="*80)
            print(f"【NOI计算结果】")
            print(f"计算公式: {noi.get('formula', '总收入 - 总费用 - Capex')}")
            print(f"计算NOI: {noi.get('calculated', 0):.2f}万元")
            print("="*80)


if __name__ == '__main__':
    # 路径设置
    json_path = Path(__file__).parent.parent / 'data' / 'huazhu' / 'extracted_params_detailed.json'
    output_path = Path(__file__).parent.parent / 'output' / 'noi_comparison_report.json'

    # 确保输出目录存在
    output_path.parent.mkdir(exist_ok=True)

    # 生成报告
    report = generate_comparison_report(str(json_path), str(output_path))

    # 打印汇总
    print_comparison_summary(report)

    print(f"\n\n详细报告已保存至: {output_path}")
