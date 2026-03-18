"""
NOI计算引擎
基于收入->NOI完整推导关系的计算实现
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

from .schemas import (
    HotelRoomRevenue, OTARevenue, FBRevenue, HotelOtherRevenue,
    CommercialRevenue, TotalRevenue,
    OperatingExpenses, PropertyExpense, InsuranceExpense,
    TaxExpenses, ManagementFee, TotalExpenses,
    CapitalExpenditure, NOICalculation, HotelProjectSchema
)


class NOIEngine:
    """NOI计算引擎"""

    @staticmethod
    def calculate_room_revenue(room_params: Dict) -> float:
        """计算客房收入

        Formula: ADR * 房间数 * OCC * 当年天数
        """
        adr = room_params.get('adr', 0)
        room_count = room_params.get('room_count', 0)
        occupancy_rate = room_params.get('occupancy_rate', 0)
        days = room_params.get('days_per_year', 365)

        return adr * room_count * occupancy_rate * days / 10000  # 转换为万元

    @staticmethod
    def calculate_future_adr(base_adr: float, year: int, cpi_rate: float) -> float:
        """计算未来各年平均房价

        Formula: 首年房价 * (1 + CPI增长率) ^ 年期
        """
        return base_adr * ((1 + cpi_rate) ** (year - 1))

    @staticmethod
    def calculate_room_revenue_by_brand(room_data: Dict, year: int = 1) -> Dict[str, Any]:
        """按品牌计算客房收入

        Returns:
            {
                'total': 总客房收入,
                'by_brand': {
                    '品牌名': {
                        'room_count': 房间数,
                        'adr': ADR,
                        'occupancy_rate': OCC,
                        'revenue': 收入
                    }
                }
            }
        """
        by_brand_data = room_data.get('by_brand', {})

        if not by_brand_data:
            # 没有分品牌数据，使用统一计算
            base_adr = room_data.get('adr', 0)
            room_count = room_data.get('room_count', 0)
            occupancy_rate = room_data.get('occupancy_rate', 0)
            days = room_data.get('days_per_year', 365)

            if year > 1:
                cpi_rate = room_data.get('growth_assumption', {}).get('cpi_rate', 0.025)
                adr = NOIEngine.calculate_future_adr(base_adr, year, cpi_rate)
            else:
                adr = base_adr

            revenue = adr * room_count * occupancy_rate * days / 10000
            return {
                'total': revenue,
                'by_brand': {}
            }

        # 分品牌计算
        total_revenue = 0
        brand_results = {}

        for brand_name, brand_params in by_brand_data.items():
            if brand_name == 'note':
                continue

            base_adr = brand_params.get('adr', 0)
            room_count = brand_params.get('room_count', 0)
            occupancy_rate = brand_params.get('occupancy_rate', 0)
            days = room_data.get('days_per_year', 365)

            if year > 1:
                cpi_rate = room_data.get('growth_assumption', {}).get('cpi_rate', 0.025)
                adr = NOIEngine.calculate_future_adr(base_adr, year, cpi_rate)
            else:
                adr = base_adr

            revenue = adr * room_count * occupancy_rate * days / 10000
            total_revenue += revenue

            brand_results[brand_name] = {
                'room_count': room_count,
                'adr': adr,
                'occupancy_rate': occupancy_rate,
                'revenue': round(revenue, 2)
            }

        return {
            'total': round(total_revenue, 2),
            'by_brand': brand_results
        }

    @staticmethod
    def calculate_hotel_revenue(revenue_data: Dict, year: int = 1) -> Dict[str, float]:
        """计算酒店收入明细

        Returns:
            {
                'room_revenue': 客房收入,
                'room_revenue_by_brand': 分品牌客房收入明细,
                'ota_revenue': OTA收入,
                'fb_revenue': 餐饮收入,
                'other_revenue': 其他收入,
                'total': 酒店总收入
            }
        """
        hotel = revenue_data.get('hotel', {})

        # 1. 客房收入（支持分品牌计算）
        room = hotel.get('room_revenue', {})
        base_room_revenue = room.get('first_year_amount', 0)

        # 检查是否有分品牌数据
        by_brand_result = NOIEngine.calculate_room_revenue_by_brand(room, year)

        if by_brand_result['by_brand']:
            # 使用分品牌计算结果
            room_revenue = by_brand_result['total']
        else:
            # 使用统一计算
            if year > 1:
                # 未来年份考虑ADR增长
                base_adr = room.get('adr', 0)
                cpi_rate = room.get('growth_assumption', {}).get('cpi_rate', 0.025)
                future_adr = NOIEngine.calculate_future_adr(base_adr, year, cpi_rate)

                # 重新计算客房收入
                room_count = room.get('room_count', 0)
                occupancy_rate = room.get('occupancy_rate', 0)
                days = room.get('days_per_year', 365)
                room_revenue = future_adr * room_count * occupancy_rate * days / 10000
            else:
                room_revenue = base_room_revenue

        # 2. OTA收入 - 按客房收入比例
        ota = hotel.get('ota_revenue', {})
        ota_ratio = ota.get('historical_ratio', -1)  # 使用-1表示未设置
        if ota_ratio == -1:
            # 如果历史比例未设置，检查是否有明确设置为0
            if 'historical_ratio' in ota and ota['historical_ratio'] == 0:
                ota_ratio = 0  # 明确设置为0，表示无OTA收入
            else:
                ota_ratio = ota.get('industry_benchmark', 0.15)  # 使用行业基准
        ota_revenue = room_revenue * ota_ratio

        # 3. 餐饮收入 - 按客房收入比例
        fb = hotel.get('fb_revenue', {})
        fb_ratio = fb.get('room_revenue_ratio', 0.05)
        fb_revenue = room_revenue * fb_ratio

        # 4. 其他收入 - 按客房收入比例
        other = hotel.get('other_revenue', {})
        other_ratio = other.get('room_revenue_ratio', 0.02)
        other_revenue = room_revenue * other_ratio

        result = {
            'room_revenue': round(room_revenue, 2),
            'ota_revenue': round(ota_revenue, 2),
            'fb_revenue': round(fb_revenue, 2),
            'other_revenue': round(other_revenue, 2),
            'total': round(room_revenue + ota_revenue + fb_revenue + other_revenue, 2)
        }

        # 添加分品牌明细（如果有）
        if by_brand_result['by_brand']:
            result['room_revenue_by_brand'] = by_brand_result['by_brand']

        return result

    @staticmethod
    def calculate_commercial_revenue(commercial_data: Dict) -> float:
        """计算商业收入"""
        rental = commercial_data.get('rental_income', 0)
        mgmt_fee = commercial_data.get('mgmt_fee_income', 0)
        return rental + mgmt_fee

    @staticmethod
    def calculate_operating_expenses(opex_data: Dict, hotel_revenue: float) -> float:
        """计算运营费用

        优先使用明细，如明细缺失则按历史平均比例估算
        """
        # 尝试使用明细
        detail_fields = [
            'labor_cost', 'fb_cost', 'cleaning_supplies', 'consumables',
            'utilities', 'maintenance', 'marketing', 'data_system', 'other'
        ]

        total = 0
        has_detail = False
        for field in detail_fields:
            value = opex_data.get(field, 0)
            if value > 0:
                total += value
                has_detail = True

        # 如无明细，按历史比例估算
        if not has_detail:
            ratio = opex_data.get('historical_avg_ratio', 0.30)
            total = hotel_revenue * ratio

        return total

    @staticmethod
    def calculate_property_expense(prop_data: Dict) -> float:
        """计算物业费用

        Formula: 建筑面积 * 物业单价 * 12
        """
        area = prop_data.get('building_area', 0)
        unit_price = prop_data.get('unit_price_per_sqm', 0)

        # 如果已有年度总额，直接使用
        annual_total = prop_data.get('annual_total', 0)
        if annual_total > 0:
            return annual_total / 10000  # 转换为万元

        return area * unit_price * 12 / 10000  # 转换为万元

    @staticmethod
    def calculate_tax_expenses(tax_data: Dict, hotel_revenue: float,
                               commercial_rent: float) -> Dict[str, float]:
        """计算税费明细

        注意：hotel_revenue是含税收入，增值税计算需先转换为不含税收入
        不含税收入 = 含税收入 / (1 + 税率)
        增值税 = 不含税收入 × 税率 = 含税收入 × 税率 / (1 + 税率)
        """
        results = {}

        # 1. 增值税及附加
        vat_data = tax_data.get('vat', {})
        vat_hotel_rate = vat_data.get('hotel_rate', 0.06)
        vat_commercial_rate = vat_data.get('commercial_rate', 0.09)
        surcharge_rate = vat_data.get('surcharge_rate', 0.12)

        # 酒店收入增值税：先转为不含税收入再计算
        # 增值税 = 含税收入 × 税率 / (1 + 税率)
        vat_hotel = hotel_revenue * vat_hotel_rate / (1 + vat_hotel_rate)
        # 商业租金增值税（通常租金报价为含税价）
        vat_commercial = commercial_rent * vat_commercial_rate / (1 + vat_commercial_rate)
        vat_total = vat_hotel + vat_commercial
        surcharge = vat_total * surcharge_rate

        results['vat_hotel'] = round(vat_hotel, 2)
        results['vat_commercial'] = round(vat_commercial, 2)
        results['surcharge'] = round(surcharge, 2)
        results['vat_total'] = round(vat_total + surcharge, 2)

        # 2. 房产税
        prop_tax_data = tax_data.get('property_tax', {})

        # 酒店部分（从价）
        hotel_prop = prop_tax_data.get('hotel', {})
        hotel_prop_base = hotel_prop.get('original_value', 0)
        hotel_prop_rate = hotel_prop.get('rate', 0.012)
        hotel_prop_tax = hotel_prop_base * hotel_prop_rate / 10000  # 转换为万元

        # 商业部分（从租）
        commercial_prop = prop_tax_data.get('commercial', {})
        commercial_rent_base = commercial_prop.get('rental_base', commercial_rent)
        commercial_prop_rate = commercial_prop.get('rate', 0.12)
        commercial_prop_tax = commercial_rent_base * commercial_prop_rate

        results['property_tax_hotel'] = round(hotel_prop_tax, 2)
        results['property_tax_commercial'] = round(commercial_prop_tax, 2)
        results['property_tax_total'] = round(hotel_prop_tax + commercial_prop_tax, 2)

        # 3. 城镇土地使用税
        land_data = tax_data.get('land_use_tax', {})
        land_rate = land_data.get('unit_rate', 20)
        land_area = land_data.get('land_area', 0)
        land_tax = land_rate * land_area / 10000  # 转换为万元

        results['land_use_tax'] = round(land_tax, 2)

        # 税费合计
        results['total_tax'] = round(
            results['vat_total'] + results['property_tax_total'] + results['land_use_tax'], 2
        )

        return results

    @staticmethod
    def calculate_management_fee(gop: float, fee_rate: float = 0.03) -> float:
        """计算管理费

        Formula: GOP * 基准费率
        """
        return gop * fee_rate

    @classmethod
    def calculate_noi(cls, project_data: Dict, year: int = 1) -> Dict[str, Any]:
        """计算完整NOI

        Formula: NOI = 总收入 - 总费用 - 资本性支出

        Args:
            project_data: 项目详细数据
            year: 计算年份（1=首年）

        Returns:
            完整NOI计算结果
        """
        result = {
            'year': year,
            'project_name': project_data.get('name', ''),
        }

        # ===== 1. 计算收入 =====
        revenue_data = project_data.get('revenue', {})

        # 酒店收入
        hotel_revenue_detail = cls.calculate_hotel_revenue(revenue_data, year)
        hotel_revenue = hotel_revenue_detail['total']

        # 商业收入
        commercial_revenue = cls.calculate_commercial_revenue(
            revenue_data.get('commercial', {})
        )

        total_income = hotel_revenue + commercial_revenue

        result['revenue'] = {
            'hotel': hotel_revenue_detail,
            'commercial': round(commercial_revenue, 2),
            'total': round(total_income, 2)
        }

        # ===== 2. 计算费用 =====
        expenses_data = project_data.get('expenses', {})

        # 2.1 运营费用
        operating_expense = cls.calculate_operating_expenses(
            expenses_data.get('operating', {}),
            hotel_revenue
        )

        # GOP = 酒店收入 - 运营费用
        gop = hotel_revenue - operating_expense

        # 2.2 物业费用
        property_expense = cls.calculate_property_expense(
            expenses_data.get('property_expense', {})
        )

        # 2.3 保险费
        insurance_expense = expenses_data.get('insurance', {}).get('annual_amount', 0)

        # 2.4 税费
        tax_detail = cls.calculate_tax_expenses(
            expenses_data.get('tax', {}),
            hotel_revenue,
            revenue_data.get('commercial', {}).get('rental_income', 0)
        )

        # 2.5 管理费
        mgmt_fee_rate = expenses_data.get('management_fee', {}).get('fee_rate', 0.03)
        management_fee = cls.calculate_management_fee(gop, mgmt_fee_rate)

        # 费用合计
        total_expense = (
            operating_expense + property_expense + insurance_expense +
            tax_detail['total_tax'] + management_fee
        )

        result['expenses'] = {
            'operating': round(operating_expense, 2),
            'property': round(property_expense, 2),
            'insurance': round(insurance_expense, 2),
            'tax': tax_detail,
            'management_fee': round(management_fee, 2),
            'total': round(total_expense, 2)
        }

        result['gop'] = round(gop, 2)

        # ===== 3. 资本性支出 =====
        capex_data = project_data.get('capex', {})
        capex_forecast = capex_data.get('forecast', [])

        if year <= len(capex_forecast):
            capex = capex_forecast[year - 1]
        else:
            # 超出预测期，使用最后一年的值
            capex = capex_forecast[-1] if capex_forecast else 0

        result['capex'] = round(capex, 2)

        # ===== 4. 计算NOI =====
        noi = total_income - total_expense - capex

        result['noi'] = round(noi, 2)
        result['noi_margin'] = round(noi / total_income * 100, 2) if total_income > 0 else 0

        return result

    @classmethod
    def calculate_multi_year_noi(cls, project_data: Dict, years: int = 5) -> List[Dict]:
        """计算多年NOI预测"""
        results = []
        for year in range(1, years + 1):
            noi_result = cls.calculate_noi(project_data, year)
            results.append(noi_result)
        return results


class NOIReportGenerator:
    """NOI报告生成器"""

    @staticmethod
    def generate_noi_report(project_data: Dict, years: int = 5) -> Dict[str, Any]:
        """生成完整NOI报告"""
        engine = NOIEngine()

        report = {
            'project_name': project_data.get('name', ''),
            'brand': project_data.get('brand', ''),
            'location': project_data.get('location', ''),
            'total_rooms': project_data.get('total_rooms', 0),
            'calculation_method': '收入->NOI完整推导',
            'multi_year_noi': engine.calculate_multi_year_noi(project_data, years),
        }

        # 计算关键指标
        first_year = report['multi_year_noi'][0] if report['multi_year_noi'] else {}
        if first_year:
            report['key_metrics'] = {
                'first_year_noi': first_year.get('noi', 0),
                'first_year_revenue': first_year.get('revenue', {}).get('total', 0),
                'first_year_expenses': first_year.get('expenses', {}).get('total', 0),
                'first_year_capex': first_year.get('capex', 0),
                'noi_margin': first_year.get('noi_margin', 0),
            }

        return report

    @staticmethod
    def export_to_json(report: Dict, output_path: str):
        """导出报告为JSON"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    @staticmethod
    def print_noi_summary(report: Dict):
        """打印NOI汇总"""
        print(f"\n{'='*60}")
        print(f"NOI计算报告: {report['project_name']}")
        print(f"{'='*60}")
        print(f"品牌: {report['brand']}")
        print(f"位置: {report['location']}")
        print(f"房间数: {report['total_rooms']}间")
        print(f"\n{'年份':<6}{'总收入':>12}{'总费用':>12}{'Capex':>10}{'NOI':>12}{'NOI率':>8}")
        print('-' * 60)

        for year_data in report['multi_year_noi']:
            year = year_data['year']
            revenue = year_data['revenue']['total']
            expenses = year_data['expenses']['total']
            capex = year_data['capex']
            noi = year_data['noi']
            margin = year_data['noi_margin']

            print(f"{year:<6}{revenue:>12.2f}{expenses:>12.2f}{capex:>10.2f}{noi:>12.2f}{margin:>7.1f}%")

        print(f"{'='*60}")


def load_and_calculate_noi(json_path: str, project_name: Optional[str] = None) -> Dict:
    """从JSON文件加载并计算NOI

    Args:
        json_path: JSON文件路径
        project_name: 指定项目名称（如None则计算所有项目）

    Returns:
        NOI计算结果
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    projects = data.get('projects', [])

    if project_name:
        # 查找指定项目
        project = next((p for p in projects if p['name'] == project_name), None)
        if not project:
            raise ValueError(f"未找到项目: {project_name}")
        projects = [project]

    # 计算所有项目的NOI
    results = {}
    for project in projects:
        report = NOIReportGenerator.generate_noi_report(project, years=5)
        results[project['name']] = report

    return results


if __name__ == '__main__':
    # 测试代码
    print("NOI计算引擎测试")
    print("=" * 60)

    # 加载测试数据
    test_data_path = Path(__file__).parent.parent / 'data' / 'huazhu' / 'extracted_params_detailed.json'

    if test_data_path.exists():
        results = load_and_calculate_noi(str(test_data_path))

        for project_name, report in results.items():
            NOIReportGenerator.print_noi_summary(report)
    else:
        print(f"测试数据文件不存在: {test_data_path}")
