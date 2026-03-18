"""
酒店REIT NOI推导数据模型
基于收入->NOI的完整推导关系定义
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum


class RevenueSource(Enum):
    """收入来源类型"""
    HOTEL_ROOM = "hotel_room"           # 酒店客房收入
    HOTEL_OTA = "hotel_ota"             # OTA收入
    HOTEL_FB = "hotel_fb"               # 餐饮收入
    HOTEL_OTHER = "hotel_other"         # 酒店其他收入
    COMMERCIAL_RENT = "commercial_rent" # 商业租金
    COMMERCIAL_MGMT = "commercial_mgmt" # 商业物业费


class ExpenseCategory(Enum):
    """费用类别"""
    OPERATING = "operating"             # 运营费用
    PROPERTY_MGMT = "property_mgmt"     # 物业费用
    INSURANCE = "insurance"             # 保险费
    TAX = "tax"                         # 税费
    MANAGEMENT_FEE = "management_fee"   # 管理费


class TaxType(Enum):
    """税费类型"""
    VAT_HOTEL = "vat_hotel"             # 酒店增值税(6%)
    VAT_COMMERCIAL = "vat_commercial"   # 商业增值税(9%)
    PROPERTY_HOTEL = "property_hotel"   # 酒店房产税(从价)
    PROPERTY_COMMERCIAL = "property_commercial"  # 商业房产税(从租)
    LAND_USE = "land_use"               # 城镇土地使用税


@dataclass
class HotelRoomRevenue:
    """酒店客房收入参数"""
    adr: float                          # 平均房价(ADR, 元/晚)
    room_count: int                     # 房间数
    occupancy_rate: float               # 入住率(OCC)
    days_per_year: int = 365            # 当年天数

    # 增长假设
    cpi_growth_rate: float = 0.025      # 居民消费价格指数增长率(默认2.5%)
    growth_note: str = "需用户确认：考虑经济发展、通胀、成本等综合因素"

    def calculate_first_year(self) -> float:
        """计算首年客房收入"""
        return self.adr * self.room_count * self.occupancy_rate * self.days_per_year

    def calculate_year_n(self, year: int) -> float:
        """计算第N年客房收入（考虑增长）"""
        base = self.calculate_first_year()
        return base * ((1 + self.cpi_growth_rate) ** (year - 1))


@dataclass
class OTARevenue:
    """OTA收入参数"""
    first_year_amount: float            # 首年OTA收入金额
    historical_ratio: float             # 历史占客房收入比例
    industry_benchmark: float = 0.15    # 行业平均占比(15%)

    # 假设说明
    assumption_source: str = "参考历史OTA收入占比和行业平均数据"
    needs_confirmation: bool = True     # 需用户确认


@dataclass
class FBRevenue:
    """餐饮收入参数"""
    first_year_amount: float            # 首年餐饮收入
    room_revenue_ratio: float           # 占客房收入比例
    historical_avg_ratio: float = 0.05  # 历史平均比例(5%)

    assumption_note: str = "参考历史占客房收入的比例"


@dataclass
class HotelOtherRevenue:
    """酒店其他收入参数"""
    first_year_amount: float            # 首年其他收入
    room_revenue_ratio: float           # 占客房收入比例

    # 组成说明
    components: Dict[str, float] = field(default_factory=lambda: {
        "membership_card": 0.0,         # 会员卡销售
        "meeting_service": 0.0,         # 会议服务
        "retail_goods": 0.0,            # 小商品销售
        "other": 0.0                    # 其他
    })

    assumption_note: str = "参考历史占客房收入的比例"


@dataclass
class CommercialRevenue:
    """商业收入参数"""
    rental_income: float                # 商业租金收入
    mgmt_fee_income: float              # 商业物业管理费收入
    building_area: float                # 商业建筑面积(㎡)
    rent_per_sqm: float = 0.0           # 单位租金(元/㎡/月)

    def calculate_total(self) -> float:
        """计算商业总收入"""
        return self.rental_income + self.mgmt_fee_income


@dataclass
class TotalRevenue:
    """总收入结构"""
    # 酒店收入
    hotel_room: HotelRoomRevenue
    hotel_ota: OTARevenue
    hotel_fb: FBRevenue
    hotel_other: HotelOtherRevenue

    # 商业收入
    commercial: CommercialRevenue

    def calculate_hotel_revenue(self, year: int = 1) -> float:
        """计算酒店收入"""
        room = self.hotel_room.calculate_year_n(year) if year > 1 else self.hotel_room.calculate_first_year()
        # OTA、餐饮、其他按历史比例估算
        ota = room * self.hotel_ota.historical_ratio
        fb = room * self.hotel_fb.room_revenue_ratio
        other = room * self.hotel_other.room_revenue_ratio
        return room + ota + fb + other

    def calculate_total(self, year: int = 1) -> float:
        """计算总收入"""
        return self.calculate_hotel_revenue(year) + self.commercial.calculate_total()


@dataclass
class OperatingExpenses:
    """运营费用明细"""
    labor_cost: float                   # 人工成本
    fb_cost: float                      # 餐饮成本
    cleaning_supplies: float            # 清洁物料
    consumables: float                  # 耗材
    utilities: float                    # 能源费用
    maintenance: float                  # 维护费
    marketing: float                    # 营销推广费用
    data_system: float                  # 数据系统费用
    other: float                        # 其他费用

    # 计算方法
    calculation_method: str = "一般用历史运营费用合计的平均比例"
    historical_avg_ratio: float = 0.35  # 历史平均占收入比例(35%)

    def calculate_total(self) -> float:
        """计算运营费用合计"""
        return sum([
            self.labor_cost, self.fb_cost, self.cleaning_supplies,
            self.consumables, self.utilities, self.maintenance,
            self.marketing, self.data_system, self.other
        ])


@dataclass
class PropertyExpense:
    """物业费用"""
    building_area: float                # 建筑面积(㎡)
    unit_price_per_sqm: float           # 物业单价(元/㎡/月)
    monthly_total: float = 0.0          # 月度合计
    annual_total: float = 0.0           # 年度合计

    def calculate(self) -> float:
        """计算物业费用"""
        self.monthly_total = self.building_area * self.unit_price_per_sqm
        self.annual_total = self.monthly_total * 12
        return self.annual_total


@dataclass
class InsuranceExpense:
    """保险费"""
    annual_amount: float                # 年度保险费用
    insurance_type: str = ""            # 保险类型
    note: str = "按实际金额"             # 备注


@dataclass
class TaxExpenses:
    """税费明细"""
    # 增值税及附加
    vat_hotel_rate: float = 0.06        # 酒店部分税率(6%)
    vat_commercial_rate: float = 0.09   # 商业租金税率(9%)
    vat_surcharge_rate: float = 0.12    # 附加税率(12% of VAT)

    # 房产税
    property_tax_hotel_rate: float = 0.012  # 酒店房产税(从价1.2%)
    property_tax_hotel_base: float = 0.0    # 酒店房产原值
    property_tax_commercial_rate: float = 0.12  # 商业房产税(从租12%)
    property_tax_commercial_base: float = 0.0   # 不含税租金收入

    # 城镇土地使用税
    land_use_tax_per_sqm: float = 0.0   # 单位面积税额(元/㎡/年)
    land_area: float = 0.0              # 土地面积(㎡)

    def calculate_vat(self, hotel_revenue: float, commercial_rent: float) -> float:
        """计算增值税及附加"""
        vat_hotel = hotel_revenue * self.vat_hotel_rate
        vat_commercial = commercial_rent * self.vat_commercial_rate
        vat_total = vat_hotel + vat_commercial
        surcharge = vat_total * self.vat_surcharge_rate
        return vat_total + surcharge

    def calculate_property_tax(self) -> float:
        """计算房产税"""
        hotel_tax = self.property_tax_hotel_base * self.property_tax_hotel_rate
        commercial_tax = self.property_tax_commercial_base * self.property_tax_commercial_rate
        return hotel_tax + commercial_tax

    def calculate_land_use_tax(self) -> float:
        """计算城镇土地使用税"""
        return self.land_use_tax_per_sqm * self.land_area


@dataclass
class ManagementFee:
    """酒店管理费用"""
    gop_base: float                     # GOP基数
    fee_rate: float                     # 费率(通常3-5%)
    annual_amount: float = 0.0          # 年度管理费

    note: str = "付给酒店管理公司的费用，按GOP×基准费率缴纳"

    def calculate(self, gop: float) -> float:
        """计算管理费"""
        self.gop_base = gop
        self.annual_amount = gop * self.fee_rate
        return self.annual_amount


@dataclass
class TotalExpenses:
    """总费用结构"""
    operating: OperatingExpenses        # 运营费用
    property_expense: PropertyExpense   # 物业费用
    insurance: InsuranceExpense         # 保险费
    tax: TaxExpenses                    # 税费
    management_fee: ManagementFee       # 管理费

    def calculate_total(self, hotel_revenue: float, commercial_rent: float, gop: float) -> float:
        """计算总费用"""
        operating_total = self.operating.calculate_total()
        property_total = self.property_expense.calculate()
        vat = self.tax.calculate_vat(hotel_revenue, commercial_rent)
        property_tax = self.tax.calculate_property_tax()
        land_tax = self.tax.calculate_land_use_tax()
        mgmt_fee = self.management_fee.calculate(gop)

        return operating_total + property_total + self.insurance.annual_amount + \
               vat + property_tax + land_tax + mgmt_fee


@dataclass
class CapitalExpenditure:
    """资本性支出"""
    annual_capex: float                 # 年度资本性支出
    renovation_cycle: int = 5           # 翻新周期(年)
    major_renovation_cost: float = 0.0  # 大额翻新成本

    note: str = "需考虑定期翻新和设施更新"


@dataclass
class NOICalculation:
    """NOI计算结果"""
    # 收入
    total_revenue: TotalRevenue

    # 费用
    total_expenses: TotalExpenses

    # 资本性支出
    capex: CapitalExpenditure

    # 计算结果
    year: int = 1                       # 计算年份
    hotel_revenue: float = 0.0          # 酒店收入
    commercial_revenue: float = 0.0     # 商业收入
    total_income: float = 0.0           # 总收入
    total_expense: float = 0.0          # 总费用
    gop: float = 0.0                    # 营业毛利
    noi_before_capex: float = 0.0       # 扣除capex前NOI
    noi: float = 0.0                    # 年净收益(NOI)

    def calculate(self) -> float:
        """执行完整NOI计算"""
        # 收入
        self.hotel_revenue = self.total_revenue.calculate_hotel_revenue(self.year)
        self.commercial_revenue = self.total_revenue.commercial.calculate_total()
        self.total_income = self.hotel_revenue + self.commercial_revenue

        # GOP = 酒店收入 - 运营费用
        self.gop = self.hotel_revenue - self.total_expenses.operating.calculate_total()

        # 总费用
        self.total_expense = self.total_expenses.calculate_total(
            self.hotel_revenue,
            self.total_revenue.commercial.rental_income,
            self.gop
        )

        # NOI = 总收入 - 总费用 - 资本性支出
        self.noi_before_capex = self.total_income - self.total_expense
        self.noi = self.noi_before_capex - self.capex.annual_capex

        return self.noi

    def to_dict(self) -> Dict[str, Any]:
        """导出计算详情"""
        return {
            "year": self.year,
            "revenue": {
                "hotel_revenue": round(self.hotel_revenue, 2),
                "commercial_revenue": round(self.commercial_revenue, 2),
                "total_income": round(self.total_income, 2),
            },
            "expenses": {
                "operating": round(self.total_expenses.operating.calculate_total(), 2),
                "property": round(self.total_expenses.property_expense.calculate(), 2),
                "insurance": round(self.total_expenses.insurance.annual_amount, 2),
                "tax": round(self.total_expenses.tax.calculate_vat(
                    self.hotel_revenue,
                    self.total_revenue.commercial.rental_income
                ) + self.total_expenses.tax.calculate_property_tax() +
                self.total_expenses.tax.calculate_land_use_tax(), 2),
                "management_fee": round(self.total_expenses.management_fee.annual_amount, 2),
                "total_expense": round(self.total_expense, 2),
            },
            "gop": round(self.gop, 2),
            "capex": round(self.capex.annual_capex, 2),
            "noi": round(self.noi, 2),
        }


@dataclass
class HotelProjectSchema:
    """酒店项目完整数据Schema"""
    # 项目基本信息
    project_name: str
    location: str
    brand: str
    room_count: int
    building_area: float
    land_area: float
    remaining_years: float

    # 关键运营指标
    adr: float                          # 平均房价
    occupancy_rate: float               # 入住率

    # 收入结构
    revenue: TotalRevenue

    # 费用结构
    expenses: TotalExpenses

    # 资本性支出
    capex: CapitalExpenditure

    # 增长率假设
    growth_assumptions: Dict[str, Any] = field(default_factory=dict)

    # 来源信息
    data_sources: Dict[str, str] = field(default_factory=dict)

    def calculate_noi(self, year: int = 1) -> NOICalculation:
        """计算指定年份的NOI"""
        calc = NOICalculation(
            total_revenue=self.revenue,
            total_expenses=self.expenses,
            capex=self.capex,
            year=year
        )
        calc.calculate()
        return calc

    def to_dict(self) -> Dict[str, Any]:
        """导出完整数据结构"""
        return {
            "project_name": self.project_name,
            "location": self.location,
            "brand": self.brand,
            "room_count": self.room_count,
            "building_area": self.building_area,
            "land_area": self.land_area,
            "remaining_years": self.remaining_years,
            "adr": self.adr,
            "occupancy_rate": self.occupancy_rate,
            "revpar": self.adr * self.occupancy_rate,
            "first_year_noi": self.calculate_noi(1).to_dict(),
            "growth_assumptions": self.growth_assumptions,
            "data_sources": self.data_sources,
        }
