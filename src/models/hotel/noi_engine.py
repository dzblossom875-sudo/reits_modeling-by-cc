"""
酒店REITs NOI推导引擎 v5.0（最终版）

公式链:
  营业收入(不含税) = first_year_amount（ADR含6%增值税，已价税分离）
  运营成本(REITs口径) = 运营明细 + 物业费(独立) + 保险(独立)
  GOP = 营业收入 - 运营成本 - 税金及附加(实际缴纳)
  管理费 = GOP × fee_rate（付给酒店管理公司，非利润表管理费用）
  NOI = GOP - 管理费
  NOI/CF = NOI - Capex

所有金额单位：万元
"""

from typing import Any, Dict, Optional

from .params import DerivedNOI


THRESHOLD = 0.05        # 推导NOI与招募值的允许偏差（5%）
HOTEL_VAT_RATE = 0.06   # 酒店住宿业一般纳税人增值税率


class NOIDeriver:
    """
    从 extracted_params_detailed.json 中单个 project 节点推导 NOI。

    调用方式:
        derived = NOIDeriver.derive(project_detail, prospectus_noicf, historical_data)
    """

    @classmethod
    def derive(cls,
               project_detail: Dict[str, Any],
               prospectus_noicf: float,
               historical_data: Optional[Dict[str, Any]] = None) -> DerivedNOI:
        """
        主入口：推导单个项目的NOI。

        Args:
            project_detail:   详细参数JSON中的单个project节点
            prospectus_noicf: 招募说明书披露的NOI/CF（用于验证对比）
            historical_data:  历史财务数据（可选，用于税金校准）
        """
        rev = project_detail.get("revenue", {})
        exp = project_detail.get("expenses", {})
        capex_data = project_detail.get("capex", {})

        # ── 1. 收入：first_year_amount 已是不含税净额 ──────────────────────
        hotel = rev.get("hotel", {})
        commercial = rev.get("commercial", {})

        room_data = hotel.get("room_revenue", {})
        room_rev = room_data.get("first_year_amount", 0)
        fb_rev = hotel.get("fb_revenue", {}).get("first_year_amount", 0)
        other_rev = hotel.get("other_revenue", {}).get("first_year_amount", 0)
        ota_rev = hotel.get("ota_revenue", {}).get("first_year_amount", 0)
        hotel_total = room_rev + fb_rev + other_rev + ota_rev

        comm_rent = commercial.get("rental_income", 0)
        comm_mgmt = commercial.get("mgmt_fee_income", 0)
        commercial_total = comm_rent + comm_mgmt

        total_revenue = hotel_total + commercial_total

        # ADR公式验证（不含税）
        adr = room_data.get("adr", 0)
        rooms = room_data.get("room_count", 0)
        occ = room_data.get("occupancy_rate", 0)
        adr_excl_tax = (adr * rooms * occ * 365 / 10000) / (1 + HOTEL_VAT_RATE) if (adr and rooms and occ) else 0
        adr_diff_pct = ((room_rev - adr_excl_tax) / adr_excl_tax * 100) if adr_excl_tax > 0 else 0

        # ── 2. 运营成本：REITs后明细（非历史利润表）────────────────────────
        op = exp.get("operating", {})
        op_keys = ["labor_cost", "fb_cost", "cleaning_supplies", "consumables",
                   "utilities", "maintenance", "marketing", "data_system", "other"]
        operating_items = {k: op.get(k, 0) for k in op_keys}
        operating_subtotal = sum(operating_items.values())

        # 物业费：annual_total单位元→万元
        prop_exp = exp.get("property_expense", {}).get("annual_total", 0) / 10000
        insurance = exp.get("insurance", {}).get("annual_amount", 0)

        cost_excl_dep = operating_subtotal + prop_exp + insurance

        # 历史成本对照（仅记录，不用于计算）
        hist_cost_2025 = 0
        if historical_data and "运营成本(不含折旧)" in historical_data:
            hist_cost_2025 = historical_data["运营成本(不含折旧)"].get("2025", 0)

        # ── 3. 税金及附加：优先实际缴纳值 ──────────────────────────────────
        derived_tax = cls._calc_tax(exp, comm_rent)
        hist_tax_2025 = 0
        if historical_data and "税金及附加" in historical_data:
            hist_tax_2025 = historical_data["税金及附加"].get("2025", 0)

        if hist_tax_2025 > 0:
            tax_total = hist_tax_2025
            tax_source = "实际缴纳2025"
        else:
            tax_total = derived_tax
            tax_source = "从原值推导"

        # ── 4. GOP ──────────────────────────────────────────────────────────
        gop = total_revenue - cost_excl_dep - tax_total

        # ── 5. 管理费 = GOP × fee_rate（酒店运营管理费）──────────────────
        mgmt_rate = exp.get("management_fee", {}).get("fee_rate", 0.03)
        mgmt_fee = gop * mgmt_rate

        total_expense = cost_excl_dep + tax_total + mgmt_fee

        # ── 6. Capex ────────────────────────────────────────────────────────
        capex = capex_data.get("annual_capex", 0)

        # ── 7. NOI/CF 并验证 ─────────────────────────────────────────────
        noi = total_revenue - total_expense - capex
        diff_pct = (noi - prospectus_noicf) / abs(prospectus_noicf) if prospectus_noicf != 0 else 0
        within = abs(diff_pct) <= THRESHOLD

        return DerivedNOI(
            project_name=project_detail.get("name", ""),
            total_revenue=total_revenue,
            hotel_revenue=hotel_total,
            commercial_revenue=commercial_total,
            operating_expense=cost_excl_dep,
            property_expense=prop_exp,
            insurance_expense=insurance,
            tax_total=tax_total,
            management_fee=mgmt_fee,
            total_expense=total_expense,
            capex=capex,
            noi=noi,
            prospectus_noicf=prospectus_noicf,
            diff_pct=diff_pct,
            within_threshold=within,
            revenue_detail={
                "room_revenue_excl_tax": round(room_rev, 2),
                "adr_excl_tax_formula": round(adr_excl_tax, 2),
                "adr_vs_actual_diff_pct": round(adr_diff_pct, 1),
                "vat_rate": HOTEL_VAT_RATE,
                "fb_revenue": round(fb_rev, 2),
                "ota_revenue": round(ota_rev, 2),
                "other_revenue": round(other_rev, 2),
                "commercial_rent": round(comm_rent, 2),
                "commercial_mgmt": round(comm_mgmt, 2),
            },
            expense_detail={
                "operating_items": {k: round(v, 2) for k, v in operating_items.items()},
                "operating_subtotal": round(operating_subtotal, 2),
                "property_expense": round(prop_exp, 2),
                "insurance": round(insurance, 2),
                "hist_cost_2025_ref": round(hist_cost_2025, 2),
                "gop": round(gop, 2),
                "gop_margin_pct": round(gop / total_revenue * 100, 1) if total_revenue else 0,
                "tax_total": round(tax_total, 2),
                "tax_source": tax_source,
                "tax_derived_ref": round(derived_tax, 2),
                "management_fee": round(mgmt_fee, 2),
                "mgmt_rate": mgmt_rate,
            },
        )

    @staticmethod
    def _calc_tax(exp: Dict[str, Any], comm_rent: float) -> float:
        """从明细推导税金及附加（房产税+土地使用税）"""
        tax = exp.get("tax", {})

        # 房产税·酒店部分（从价计征）
        hotel_pt = tax.get("property_tax", {}).get("hotel", {})
        deduction_rate = hotel_pt.get("deduction_rate", 0.30)
        # ⚠️ original_value 已是万元，禁止再除以10000
        hotel_pt_amt = hotel_pt.get("original_value", 0) * (1 - deduction_rate) * hotel_pt.get("rate", 0.012)

        # 房产税·商业部分（从租计征）
        comm_pt = tax.get("property_tax", {}).get("commercial", {})
        comm_pt_amt = comm_pt.get("rental_base", comm_rent) * comm_pt.get("rate", 0.12)

        # 土地使用税
        land = tax.get("land_use_tax", {})
        land_tax = land.get("unit_rate", 0) * land.get("land_area", 0) / 10000

        return hotel_pt_amt + comm_pt_amt + land_tax
