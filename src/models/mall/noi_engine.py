"""
商业购物中心NOI推导引擎 v1.0

NOI结构（与估价报告一致）:
  一.收入: 固定租金 + 提成租金 + 联营(净) + 物业管理费 + 推广费 + 停车场 + 多经 + 冰场 + 其他
  二.成本: 营销推广费 + 物业管理费 + 房屋大修 + 人工 + 行政 + 平台费 + 冰场支出 + 保险
  三.税金: 增值税 + 附加税 + 房产税 + 土地使用税 + 印花税
  四.资本性支出
  NOI/CF = 总收入 - 总成本 - 税金 - 资本性支出

所有金额单位：万元
参考：成都万象城及木棉花酒店估价报告@20251031，Page 77-85
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class MallYearNOI:
    """单年NOI推导结果"""
    year_idx: int            # 年期序号（1=Y1 2026）

    # 收入
    fixed_rent: float = 0.0
    perf_rent: float = 0.0
    joint_op_net: float = 0.0
    prop_mgmt_fee: float = 0.0
    marketing_fee_income: float = 0.0
    parking_excl_tax: float = 0.0
    multi_channel: float = 0.0
    ice_rink_revenue: float = 0.0
    other_revenue: float = 0.0

    # 收入调整（收缴率）
    collection_adj: float = 0.0   # 本年少收1%（延至下年）+上年延收1%
    total_revenue: float = 0.0

    # 成本
    marketing_promo_cost: float = 0.0
    prop_mgmt_cost: float = 0.0
    repairs_cost: float = 0.0
    labor_cost: float = 0.0
    admin_cost: float = 0.0
    platform_fee: float = 0.0
    ice_rink_cost: float = 0.0
    insurance_cost: float = 0.0
    total_opex: float = 0.0

    # 税金
    vat_phase1: float = 0.0
    vat_phase2: float = 0.0
    vat_joint_op: float = 0.0
    vat_parking: float = 0.0
    vat_services: float = 0.0
    vat_total: float = 0.0
    vat_surtax: float = 0.0
    property_tax_from_rent: float = 0.0
    property_tax_from_value: float = 0.0
    land_use_tax: float = 0.0
    stamp_duty: float = 0.0
    total_tax: float = 0.0

    # 资本性支出
    capex: float = 0.0

    # NOI结果
    noi: float = 0.0       # NOI = 总收入 - 总成本 - 税金
    fcf: float = 0.0       # FCF = NOI - Capex
    noi_margin_pct: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {
            "year_idx": self.year_idx,
            "fixed_rent": round(self.fixed_rent, 2),
            "perf_rent": round(self.perf_rent, 2),
            "joint_op_net": round(self.joint_op_net, 2),
            "prop_mgmt_fee": round(self.prop_mgmt_fee, 2),
            "marketing_fee_income": round(self.marketing_fee_income, 2),
            "parking_excl_tax": round(self.parking_excl_tax, 2),
            "multi_channel": round(self.multi_channel, 2),
            "ice_rink_revenue": round(self.ice_rink_revenue, 2),
            "other_revenue": round(self.other_revenue, 2),
            "total_revenue": round(self.total_revenue, 2),
            "total_opex": round(self.total_opex, 2),
            "total_tax": round(self.total_tax, 2),
            "capex": round(self.capex, 2),
            "noi": round(self.noi, 2),
            "fcf": round(self.fcf, 2),
            "noi_margin_pct": round(self.noi_margin_pct, 1),
        }


# ---------------------------------------------------------------------------
# 成长率辅助
# ---------------------------------------------------------------------------

def _specialty_growth(year_idx: int, schedule: Dict[str, Any]) -> float:
    """返回专门店第year_idx年（相对Y1）的累积增长乘数，Y1=1.0"""
    rates = schedule.get("specialty", {})
    g_map = {
        2: rates.get("Y2", 0.05),
        3: rates.get("Y3", 0.04),
        4: rates.get("Y4", 0.04),
        5: rates.get("Y5", 0.03),
    }
    cumul = 1.0
    for y in range(2, year_idx + 1):
        if y <= 9:
            rate = g_map.get(y, rates.get("Y6", 0.03))
        else:
            rate = rates.get("Y10", 0.025)
        cumul *= (1 + rate)
    return cumul


def _anchor_growth(year_idx: int, schedule: Dict[str, Any]) -> float:
    rates = schedule.get("anchor", {})
    g_map = {
        2: rates.get("Y2", 0.03), 3: rates.get("Y3", 0.03),
        4: rates.get("Y4", 0.0275), 5: rates.get("Y5", 0.0275),
        6: rates.get("Y6", 0.0275),
    }
    anchor_late = rates.get("Y7", 0.025)
    cumul = 1.0
    for y in range(2, year_idx + 1):
        if y <= 9:
            rate = g_map.get(y, anchor_late)
        else:
            rate = rates.get("Y10", 0.02)
        cumul *= (1 + rate)
    return cumul


def _cinema_growth(year_idx: int, schedule: Dict[str, Any]) -> float:
    rate = schedule.get("cinema_supermarket", {}).get("all_years", 0.02)
    return (1 + rate) ** (year_idx - 1)


def _blended_rent_growth(year_idx: int, schedule: Dict[str, Any],
                          phase_split: Dict[str, float]) -> float:
    """
    固定租金混合增长乘数。
    按专门店/主力店/超市影院分别计算，加权得到整体乘数。
    """
    # 权重近似：专门店75%，主力店16%，超市影院9%（按GLA）
    w_spec = 0.75
    w_anchor = 0.16
    w_cinema = 0.09
    g_spec = _specialty_growth(year_idx, schedule)
    g_anchor = _anchor_growth(year_idx, schedule)
    g_cinema = _cinema_growth(year_idx, schedule)
    return w_spec * g_spec + w_anchor * g_anchor + w_cinema * g_cinema


# ---------------------------------------------------------------------------
# 主引擎
# ---------------------------------------------------------------------------

class MallNOIDeriver:
    """
    商业购物中心NOI推导引擎（成都万象城参数化版本）

    调用方式:
        # 计算全预测期现金流序列
        years = MallNOIDeriver.derive_all_years(project_detail)

        # 比较历史与Y1预测
        comparison = MallNOIDeriver.compare_historical(project_detail)
    """

    @classmethod
    def derive_year(cls, year_idx: int, proj: Dict[str, Any]) -> MallYearNOI:
        """
        计算第 year_idx 年的NOI（year_idx=1 → Y1/2026）。
        """
        y1 = proj.get("y1_forecast_wan", {})
        schedule = proj.get("rent_growth_schedule", {})
        phase = proj.get("phase_split", {})
        opex = proj.get("opex_detailed", {})
        vat = proj.get("vat_rates", {})
        tax = proj.get("taxes", {})
        coll = proj.get("collection_rate", {})

        result = MallYearNOI(year_idx=year_idx)

        # ── 1. 固定租金（含提成/联营） ───────────────────────────────────────
        rent_g = _blended_rent_growth(year_idx, schedule, phase)
        fixed_rent_y1 = y1.get("fixed_rent_excl_tax", 53152)
        result.fixed_rent = fixed_rent_y1 * rent_g

        perf_ratio = y1.get("perf_rent_pct_of_rent_income", 0.22)
        result.perf_rent = result.fixed_rent * perf_ratio / (1 - perf_ratio)
        rent_income = result.fixed_rent + result.perf_rent  # 租金收入 = 固定+提成

        joint_ratio = y1.get("joint_op_pct_of_rent_income", 0.01)
        result.joint_op_net = rent_income * joint_ratio

        # ── 2. 物业管理费（每5年+5%） ──────────────────────────────────────
        pm_y1 = y1.get("prop_mgmt_fee_excl_tax", 14134)
        pm_incr_5yr = schedule.get("prop_mgmt_fee", {}).get("increase_pct_every_5yr", 0.05)
        pm_steps = (year_idx - 1) // 5   # 0,0,0,0,0→1,1,1,1,1→2...
        result.prop_mgmt_fee = pm_y1 * ((1 + pm_incr_5yr) ** pm_steps)

        # ── 3. 推广费收入（不增长） ─────────────────────────────────────────
        result.marketing_fee_income = y1.get("marketing_fee_excl_tax", 1537)

        # ── 4. 停车场收入（Y2起+1%） ────────────────────────────────────────
        park_y1_incl = y1.get("parking_incl_tax", 3201.19)
        park_vat = vat.get("parking", 0.09)
        park_excl_y1 = park_y1_incl / (1 + park_vat)
        park_g = schedule.get("parking", {}).get("growth_from_Y2", 0.01)
        result.parking_excl_tax = park_excl_y1 * ((1 + park_g) ** max(0, year_idx - 1))

        # ── 5. 多经（Y3起+2%） ──────────────────────────────────────────────
        mc_y1 = y1.get("multi_channel_excl_tax", 3742)
        mc_g = schedule.get("multi_channel", {}).get("growth_from_Y3", 0.02)
        result.multi_channel = mc_y1 * ((1 + mc_g) ** max(0, year_idx - 2))

        # ── 6. 冰场收入（Y3起+1%） ─────────────────────────────────────────
        rink_y1 = y1.get("ice_rink_excl_tax", 797)
        rink_g = schedule.get("ice_rink", {}).get("growth_from_Y3", 0.01)
        result.ice_rink_revenue = rink_y1 * ((1 + rink_g) ** max(0, year_idx - 2))

        # ── 7. 其他收入（Y3起+2%） ─────────────────────────────────────────
        other_y1 = y1.get("other_excl_tax", 1140)
        other_g = schedule.get("other", {}).get("growth_from_Y3", 0.02)
        result.other_revenue = other_y1 * ((1 + other_g) ** max(0, year_idx - 2))

        # ── 8. 收入合计（不含收缴率调整） ───────────────────────────────────
        gross_rev = (result.fixed_rent + result.perf_rent + result.joint_op_net
                     + result.prop_mgmt_fee + result.marketing_fee_income
                     + result.parking_excl_tax + result.multi_channel
                     + result.ice_rink_revenue + result.other_revenue)

        # 收缴率：当年收99%（简化：不对Y1做调整，Y1按99%收）
        coll_rate = coll.get("current_year_pct", 0.99)
        result.total_revenue = gross_rev * coll_rate
        result.collection_adj = gross_rev * (1 - coll_rate)

        # ── 9. 成本 ────────────────────────────────────────────────────────
        # 营销推广费：6%×不含税收入
        mkt_pct = opex.get("marketing_promo_pct_of_rev", 0.06)
        result.marketing_promo_cost = result.total_revenue * mkt_pct

        # 物业管理费支出：50%×物管收入（含税）
        pm_cost_pct = opex.get("prop_mgmt_cost_pct_of_prop_mgmt_incl_tax", 0.50)
        svc_vat = vat.get("services_mgmt_promo_multi_rink_other", 0.06)
        pm_incl_tax = result.prop_mgmt_fee * (1 + svc_vat)
        result.prop_mgmt_cost = pm_incl_tax * pm_cost_pct

        # 房屋大修：0.5%×不含税收入
        repairs_pct = opex.get("repairs_pct_of_rev", 0.005)
        result.repairs_cost = result.total_revenue * repairs_pct

        # 人工：基数+2%/年
        labor_y1 = opex.get("labor_y1_wan", 2973)
        labor_g = opex.get("labor_growth", 0.02)
        result.labor_cost = labor_y1 * ((1 + labor_g) ** (year_idx - 1))

        # 行政管理费：基数+2%/年
        admin_y1 = opex.get("admin_y1_wan", 482)
        admin_g = opex.get("admin_growth", 0.02)
        result.admin_cost = admin_y1 * ((1 + admin_g) ** (year_idx - 1))

        # 商业平台费：基数+2%/年
        platform_y1 = tax.get("platform_fee_base_wan", opex.get("platform_fee_y1_wan", 1297.36))
        platform_g = tax.get("platform_fee_growth_rate", opex.get("platform_fee_growth", 0.02))
        result.platform_fee = platform_y1 * ((1 + platform_g) ** (year_idx - 1))

        # 冰场支出：40%×冰场收入
        rink_cost_pct = opex.get("ice_rink_cost_pct_of_revenue", 0.40)
        result.ice_rink_cost = result.ice_rink_revenue * rink_cost_pct

        # 保险：固定
        result.insurance_cost = opex.get("insurance_annual_wan", 104.51)

        result.total_opex = (result.marketing_promo_cost + result.prop_mgmt_cost
                             + result.repairs_cost + result.labor_cost
                             + result.admin_cost + result.platform_fee
                             + result.ice_rink_cost + result.insurance_cost)

        # ── 10. 税金 ──────────────────────────────────────────────────────
        p1_frac = phase.get("phase1_rent_fraction", 0.55)
        p2_frac = phase.get("phase2_rent_fraction", 0.45)

        # 增值税 = 销项税 - 进项税
        vat_p1_rate = vat.get("phase1_rent_simplified", 0.05)
        vat_p2_rate = vat.get("phase2_rent_general", 0.09)
        vat_jo_rate = vat.get("joint_op_sales", 0.13)
        vat_park_rate = vat.get("parking", 0.09)
        vat_svc_rate = vat.get("services_mgmt_promo_multi_rink_other", 0.06)

        # 销项税：固定+提成租金（同税率）、联营、停车、服务类
        result.vat_phase1 = (result.fixed_rent + result.perf_rent) * p1_frac * vat_p1_rate
        result.vat_phase2 = (result.fixed_rent + result.perf_rent) * p2_frac * vat_p2_rate
        result.vat_joint_op = result.joint_op_net * vat_jo_rate
        result.vat_parking = result.parking_excl_tax * vat_park_rate
        svc_base = (result.prop_mgmt_fee + result.marketing_fee_income
                    + result.multi_channel + result.ice_rink_revenue + result.other_revenue)
        result.vat_services = svc_base * vat_svc_rate
        output_vat = (result.vat_phase1 + result.vat_phase2 + result.vat_joint_op
                      + result.vat_parking + result.vat_services)

        # 进项税：物管成本(6%)、房屋大修(9%)、平台费(6%)
        input_vat = (result.prop_mgmt_cost * 6 / 106
                     + result.repairs_cost * 9 / 109
                     + result.platform_fee * 6 / 106)
        # 一期简易征收不可抵扣进项（对应一期租金比例）
        input_vat_deductible = input_vat * p2_frac

        result.vat_total = max(0.0, output_vat - input_vat_deductible)

        # 增值税附加：12%×实际缴纳增值税
        surtax_rate = vat.get("surtax_on_vat", 0.12)
        result.vat_surtax = result.vat_total * surtax_rate

        # 房产税（从租）：12%×不含税(固定租金+停车场)
        pt_lease_rate = tax.get("property_tax_from_lease", 0.12)
        result.property_tax_from_rent = (result.fixed_rent + result.parking_excl_tax) * pt_lease_rate

        # 房产税（从价）：空置/自用/联营部分，0.84%×评估原值
        # 简化：联营部分按其收入规模估算占用价值
        # 联营面积≈总GLA×1%（占比很小），暂以固定金额估算
        gla = proj.get("property", {}).get("gla_sqm", 160423.79)
        appraised_wan = proj.get("appraisal_value_wan", 920500)
        value_per_sqm_wan = appraised_wan / gla / 10000  # 万元/sqm
        pt_value_rate = tax.get("property_tax_from_value", {}).get("effective_rate", 0.0084)
        # 联营+空置面积约占2%
        vacant_joint_area = gla * 0.02
        result.property_tax_from_value = vacant_joint_area * value_per_sqm_wan * 10000 * pt_value_rate

        # 土地使用税：固定
        result.land_use_tax = tax.get("land_use_tax", {}).get("annual_total_wan", 110.48)

        # 印花税：1‰×固定租金不含税
        stamp_rate = tax.get("stamp_duty_per_mille", 1) / 1000
        result.stamp_duty = result.fixed_rent * stamp_rate

        # 增值税为价外税（收入已按不含税口径列示），属于代收代付的过路资金，不计入成本。
        # 仅附加税（城建税+教育费附加 = VAT×12%）为真实税负。
        result.total_tax = (result.vat_surtax
                            + result.property_tax_from_rent + result.property_tax_from_value
                            + result.land_use_tax + result.stamp_duty)

        # ── 11. 资本性支出：2.5%×不含税收入 ───────────────────────────────
        capex_pct = opex.get("capex_pct_of_revenue_excl_tax", 0.025)
        result.capex = result.total_revenue * capex_pct

        # ── 12. NOI / FCF ──────────────────────────────────────────────────
        result.noi = result.total_revenue - result.total_opex - result.total_tax
        result.fcf = result.noi - result.capex
        result.noi_margin_pct = result.noi / result.total_revenue * 100 if result.total_revenue else 0.0

        return result

    @classmethod
    def derive_all_years(cls, proj: Dict[str, Any],
                         total_years: float = 20.10) -> List[MallYearNOI]:
        """计算全预测期（20.10年）逐年NOI，返回列表（含末年分数期）"""
        full = int(total_years)
        partial = total_years - full
        results = []
        for y in range(1, full + 1):
            results.append(cls.derive_year(y, proj))
        if partial > 0.01:
            partial_yr = cls.derive_year(full + 1, proj)
            # 按分数年等比缩减
            for attr in ["fixed_rent", "perf_rent", "joint_op_net", "prop_mgmt_fee",
                         "marketing_fee_income", "parking_excl_tax", "multi_channel",
                         "ice_rink_revenue", "other_revenue", "collection_adj",
                         "total_revenue", "marketing_promo_cost", "prop_mgmt_cost",
                         "repairs_cost", "labor_cost", "admin_cost", "platform_fee",
                         "ice_rink_cost", "insurance_cost", "total_opex",
                         "vat_phase1", "vat_phase2", "vat_joint_op", "vat_parking",
                         "vat_services", "vat_total", "vat_surtax",
                         "property_tax_from_rent", "property_tax_from_value",
                         "land_use_tax", "stamp_duty", "total_tax",
                         "capex", "noi", "fcf"]:
                setattr(partial_yr, attr, getattr(partial_yr, attr) * partial)
            partial_yr.noi_margin_pct = (
                partial_yr.noi / partial_yr.total_revenue * 100
                if partial_yr.total_revenue else 0.0
            )
            results.append(partial_yr)
        return results

    @classmethod
    def compare_historical(cls, proj: Dict[str, Any]) -> Dict[str, Any]:
        """
        逐项对比历史2024年数据 vs Y1(2026)预测，
        展示NOI推导链的一致性。
        """
        hist = proj.get("historical_revenue_wan", {})
        y1 = cls.derive_year(1, proj)

        def h(key: str) -> float:
            return hist.get(key, {}).get("2024", 0)

        h_fixed = h("fixed_rent_excl_tax")
        h_perf = h("performance_rent_excl_tax")
        h_joint = h("joint_op_net")
        h_pm = h("property_mgmt_fee_excl_tax")
        h_mkt = h("marketing_fee_excl_tax")
        h_park = h("parking_excl_tax")
        h_mc = h("multi_channel_excl_tax")
        h_rink = h("ice_rink_excl_tax")
        h_other = h("other_excl_tax")
        h_total = h_fixed + h_perf + h_joint + h_pm + h_mkt + h_park + h_mc + h_rink + h_other

        comparison = {
            "收入对比（万元，不含税）": {
                "项目": ["固定租金", "提成租金", "联营收入(净)", "物业管理费",
                         "推广费", "停车场", "多经", "冰场", "其他", "合计"],
                "2024历史": [h_fixed, h_perf, h_joint, h_pm, h_mkt,
                              h_park, h_mc, h_rink, h_other, h_total],
                "Y1预测(2026)": [
                    round(y1.fixed_rent, 0), round(y1.perf_rent, 0),
                    round(y1.joint_op_net, 0), round(y1.prop_mgmt_fee, 0),
                    round(y1.marketing_fee_income, 0), round(y1.parking_excl_tax, 0),
                    round(y1.multi_channel, 0), round(y1.ice_rink_revenue, 0),
                    round(y1.other_revenue, 0), round(y1.total_revenue, 0),
                ],
                "增长率(%)": [
                    _pct(h_fixed, y1.fixed_rent), _pct(h_perf, y1.perf_rent),
                    _pct(h_joint, y1.joint_op_net), _pct(h_pm, y1.prop_mgmt_fee),
                    _pct(h_mkt, y1.marketing_fee_income), _pct(h_park, y1.parking_excl_tax),
                    _pct(h_mc, y1.multi_channel), _pct(h_rink, y1.ice_rink_revenue),
                    _pct(h_other, y1.other_revenue), _pct(h_total, y1.total_revenue),
                ],
            },
            "NOI推导（万元）": {
                "Y1总收入": round(y1.total_revenue, 0),
                "Y1总成本": round(y1.total_opex, 0),
                "Y1税金": round(y1.total_tax, 0),
                "Y1资本性支出": round(y1.capex, 0),
                "Y1 FCF (NOI-Capex)": round(y1.fcf, 0),
                "Y1 NOI利润率(%)": round(y1.noi_margin_pct, 1),
            },
        }
        return comparison


def _pct(hist: float, forecast: float) -> Optional[float]:
    if hist and hist > 0:
        return round((forecast / hist - 1) * 100, 1)
    return None
