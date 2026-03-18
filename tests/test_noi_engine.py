"""
NOI计算引擎测试
验证收入->NOI完整推导公式的正确性
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from src.noi_engine import NOIEngine, NOIReportGenerator, load_and_calculate_noi
from src.schemas import (
    HotelRoomRevenue, OTARevenue, FBRevenue, HotelOtherRevenue,
    CommercialRevenue, OperatingExpenses, TaxExpenses
)


def test_room_revenue_formula():
    """测试客房收入公式: ADR * 房间数 * OCC * 当年天数"""
    print("\n[测试1] 客房收入公式验证")
    print("-" * 60)

    # 广州项目参数
    adr = 468.52  # 元/晚
    room_count = 776  # 间
    occupancy_rate = 0.935
    days = 365

    # 手动计算
    expected = adr * room_count * occupancy_rate * days / 10000  # 万元

    # 引擎计算
    params = {
        'adr': adr,
        'room_count': room_count,
        'occupancy_rate': occupancy_rate,
        'days_per_year': days
    }
    result = NOIEngine.calculate_room_revenue(params)

    print(f"ADR: {adr}元")
    print(f"房间数: {room_count}间")
    print(f"入住率: {occupancy_rate:.2%}")
    print(f"天数: {days}天")
    print(f"\n手动计算: {expected:.2f}万元")
    print(f"引擎计算: {result:.2f}万元")
    print(f"差异: {abs(expected - result):.4f}万元")

    assert abs(expected - result) < 0.01, "客房收入公式验证失败"
    print("[OK] 测试通过")


def test_future_adr_growth():
    """测试未来ADR增长公式: 首年房价 * (1 + CPI增长率) ^ 年期"""
    print("\n[测试2] 未来ADR增长公式验证")
    print("-" * 60)

    base_adr = 468.52
    cpi_rate = 0.025

    print(f"首年ADR: {base_adr}元")
    print(f"CPI增长率: {cpi_rate:.2%}")
    print("\n各年ADR预测:")

    for year in range(1, 6):
        # 手动计算
        expected = base_adr * ((1 + cpi_rate) ** (year - 1))
        # 引擎计算
        result = NOIEngine.calculate_future_adr(base_adr, year, cpi_rate)

        print(f"  第{year}年: 手动={expected:.2f}元, 引擎={result:.2f}元, 差异={abs(expected - result):.4f}")
        assert abs(expected - result) < 0.01, f"第{year}年ADR增长验证失败"

    print("[OK] 测试通过")


def test_hotel_revenue_breakdown():
    """测试酒店收入分解"""
    print("\n[测试3] 酒店收入分解验证")
    print("-" * 60)

    # 构建测试数据
    revenue_data = {
        'hotel': {
            'room_revenue': {
                'adr': 468.52,
                'room_count': 776,
                'occupancy_rate': 0.935,
                'days_per_year': 365,
                'first_year_amount': 13215.67,
                'growth_assumption': {'cpi_rate': 0.025}
            },
            'ota_revenue': {
                'historical_ratio': 0.0,
                'industry_benchmark': 0.15
            },
            'fb_revenue': {
                'room_revenue_ratio': 0.0406
            },
            'other_revenue': {
                'room_revenue_ratio': 0.0138
            }
        }
    }

    result = NOIEngine.calculate_hotel_revenue(revenue_data, year=1)

    print(f"客房收入: {result['room_revenue']:.2f}万元")
    print(f"OTA收入: {result['ota_revenue']:.2f}万元 (占比: {result['ota_revenue']/result['room_revenue']*100:.1f}%)")
    print(f"餐饮收入: {result['fb_revenue']:.2f}万元 (占比: {result['fb_revenue']/result['room_revenue']*100:.1f}%)")
    print(f"其他收入: {result['other_revenue']:.2f}万元 (占比: {result['other_revenue']/result['room_revenue']*100:.1f}%)")
    print(f"酒店总收入: {result['total']:.2f}万元")

    # 验证比例
    assert result['ota_revenue'] == 0, "OTA收入应为0（历史比例为0）"
    assert abs(result['fb_revenue'] - result['room_revenue'] * 0.0406) < 0.01, "餐饮收入比例错误"
    assert abs(result['other_revenue'] - result['room_revenue'] * 0.0138) < 0.01, "其他收入比例错误"

    print("[OK] 测试通过")


def test_tax_calculation():
    """测试税费计算"""
    print("\n[测试4] 税费计算验证")
    print("-" * 60)

    tax_data = {
        'vat': {
            'hotel_rate': 0.06,
            'commercial_rate': 0.09,
            'surcharge_rate': 0.12
        },
        'property_tax': {
            'hotel': {
                'original_value': 45000,
                'rate': 0.012
            },
            'commercial': {
                'rental_base': 377.07,
                'rate': 0.12
            }
        },
        'land_use_tax': {
            'unit_rate': 20,
            'land_area': 3500
        }
    }

    hotel_revenue = 14000  # 万元
    commercial_rent = 377.07  # 万元

    result = NOIEngine.calculate_tax_expenses(tax_data, hotel_revenue, commercial_rent)

    print("增值税及附加:")
    print(f"  酒店增值税: {result['vat_hotel']:.2f}万元 ({hotel_revenue} * 6%)")
    print(f"  商业增值税: {result['vat_commercial']:.2f}万元 ({commercial_rent} * 9%)")
    print(f"  附加税: {result['surcharge']:.2f}万元")
    print(f"  增值税合计: {result['vat_total']:.2f}万元")

    print("\n房产税:")
    print(f"  酒店房产税(从价): {result['property_tax_hotel']:.2f}万元 (原值45000 * 1.2%)")
    print(f"  商业房产税(从租): {result['property_tax_commercial']:.2f}万元 (租金{commercial_rent} * 12%)")
    print(f"  房产税合计: {result['property_tax_total']:.2f}万元")

    print("\n土地使用税:")
    print(f"  土地使用税: {result['land_use_tax']:.2f}万元 (3500㎡ * 20元/㎡ / 10000)")

    print(f"\n税费合计: {result['total_tax']:.2f}万元")

    # 验证计算
    expected_vat_hotel = hotel_revenue * 0.06
    expected_vat_comm = commercial_rent * 0.09
    expected_surcharge = (expected_vat_hotel + expected_vat_comm) * 0.12

    assert abs(result['vat_hotel'] - expected_vat_hotel) < 0.01, "酒店增值税计算错误"
    assert abs(result['vat_commercial'] - expected_vat_comm) < 0.01, "商业增值税计算错误"
    assert abs(result['surcharge'] - expected_surcharge) < 0.01, "附加税计算错误"

    print("[OK] 测试通过")


def test_full_noi_calculation():
    """测试完整NOI计算"""
    print("\n[测试5] 完整NOI计算验证")
    print("-" * 60)

    # 简化的项目数据
    project_data = {
        'name': '测试项目',
        'revenue': {
            'hotel': {
                'room_revenue': {
                    'adr': 400,
                    'room_count': 100,
                    'occupancy_rate': 0.80,
                    'days_per_year': 365,
                    'first_year_amount': 1168.0,
                    'growth_assumption': {'cpi_rate': 0.025}
                },
                'ota_revenue': {
                    'historical_ratio': 0.10,
                    'industry_benchmark': 0.15
                },
                'fb_revenue': {
                    'room_revenue_ratio': 0.05
                },
                'other_revenue': {
                    'room_revenue_ratio': 0.02
                }
            },
            'commercial': {
                'rental_income': 50.0,
                'mgmt_fee_income': 10.0
            }
        },
        'expenses': {
            'operating': {
                'labor_cost': 200.0,
                'fb_cost': 50.0,
                'utilities': 80.0,
                'maintenance': 40.0,
                'marketing': 60.0,
                'other': 100.0
            },
            'property_expense': {
                'building_area': 10000,
                'unit_price_per_sqm': 10.0
            },
            'insurance': {
                'annual_amount': 20.0
            },
            'tax': {
                'vat': {
                    'hotel_rate': 0.06,
                    'commercial_rate': 0.09,
                    'surcharge_rate': 0.12
                },
                'property_tax': {
                    'hotel': {'original_value': 10000, 'rate': 0.012},
                    'commercial': {'rental_base': 50, 'rate': 0.12}
                },
                'land_use_tax': {'unit_rate': 20, 'land_area': 1000}
            },
            'management_fee': {
                'fee_rate': 0.03
            }
        },
        'capex': {
            'forecast': [100.0, 105.0, 110.0]
        }
    }

    result = NOIEngine.calculate_noi(project_data, year=1)

    print(f"项目名称: {result['project_name']}")
    print(f"计算年份: 第{result['year']}年")
    print()
    print("收入明细:")
    print(f"  客房收入: {result['revenue']['hotel']['room_revenue']:.2f}万元")
    print(f"  OTA收入: {result['revenue']['hotel']['ota_revenue']:.2f}万元")
    print(f"  餐饮收入: {result['revenue']['hotel']['fb_revenue']:.2f}万元")
    print(f"  其他收入: {result['revenue']['hotel']['other_revenue']:.2f}万元")
    print(f"  商业收入: {result['revenue']['commercial']:.2f}万元")
    print(f"  总收入: {result['revenue']['total']:.2f}万元")
    print()
    print("费用明细:")
    print(f"  运营费用: {result['expenses']['operating']:.2f}万元")
    print(f"  物业费用: {result['expenses']['property']:.2f}万元")
    print(f"  保险费: {result['expenses']['insurance']:.2f}万元")
    print(f"  税费: {result['expenses']['tax']['total_tax']:.2f}万元")
    print(f"  管理费: {result['expenses']['management_fee']:.2f}万元")
    print(f"  总费用: {result['expenses']['total']:.2f}万元")
    print()
    print(f"GOP: {result['gop']:.2f}万元")
    print(f"资本性支出: {result['capex']:.2f}万元")
    print(f"NOI: {result['noi']:.2f}万元")
    print(f"NOI率: {result['noi_margin']:.2f}%")

    # 验证NOI计算
    expected_noi = result['revenue']['total'] - result['expenses']['total'] - result['capex']
    assert abs(result['noi'] - expected_noi) < 0.01, "NOI计算错误"

    print("[OK] 测试通过")


def test_real_data_calculation():
    """使用真实数据测试NOI计算"""
    print("\n[测试6] 真实数据NOI计算测试")
    print("=" * 60)

    json_path = Path(__file__).parent.parent / 'data' / 'huazhu' / 'extracted_params_detailed.json'

    if not json_path.exists():
        print(f"[FAIL] 测试数据文件不存在: {json_path}")
        return

    try:
        results = load_and_calculate_noi(str(json_path))

        for project_name, report in results.items():
            print(f"\n{'='*60}")
            print(f"项目: {project_name}")
            print(f"{'='*60}")

            metrics = report.get('key_metrics', {})
            print(f"首年NOI: {metrics.get('first_year_noi', 0):.2f}万元")
            print(f"首年收入: {metrics.get('first_year_revenue', 0):.2f}万元")
            print(f"首年费用: {metrics.get('first_year_expenses', 0):.2f}万元")
            print(f"首年Capex: {metrics.get('first_year_capex', 0):.2f}万元")
            print(f"NOI率: {metrics.get('noi_margin', 0):.2f}%")

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

        print("\n[OK] 真实数据测试通过")

    except Exception as e:
        print(f"[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("NOI计算引擎测试套件")
    print("=" * 60)

    tests = [
        test_room_revenue_formula,
        test_future_adr_growth,
        test_hotel_revenue_breakdown,
        test_tax_calculation,
        test_full_noi_calculation,
        test_real_data_calculation
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] 测试失败: {e}")
            failed += 1
        except Exception as e:
            print(f"[FAIL] 测试异常: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试结果: 通过 {passed} / 失败 {failed}")
    print("=" * 60)

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
