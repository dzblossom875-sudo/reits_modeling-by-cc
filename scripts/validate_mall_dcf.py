"""
成都万象城商业DCF模型验证脚本

验证目标：
  1. Y1 NOI各项与历史2024数据对比
  2. DCF估值结论与报告披露92.05亿对比
  3. 输出差异分析

运行: python scripts/validate_mall_dcf.py
"""

import json
import os
import sys

# 确保 src 可导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models.mall import MallDCFModel, MallNOIDeriver

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "huarun_chengdu")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")


def load_json(filename):
    with open(os.path.join(DATA_DIR, filename), encoding="utf-8") as f:
        return json.load(f)


def write_report(content: str, filename: str):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  → 已输出: {path}")


def main():
    print("=" * 60)
    print("成都万象城商业DCF模型验证")
    print("=" * 60)

    extracted = load_json("extracted_params.json")
    detailed = load_json("extracted_params_detailed.json")

    # ── 找到商业项目详细参数 ─────────────────────────────────────────
    mall_proj = next(
        (p for p in detailed["projects"] if p.get("asset_type") == "mall"), None
    )
    if not mall_proj:
        print("错误：未找到商业项目参数")
        return

    # ── 1. Y1 NOI推导明细 ────────────────────────────────────────────
    print("\n【Step 1】Y1(2026) NOI推导明细 vs 历史2024")
    comparison = MallNOIDeriver.compare_historical(mall_proj)

    rev_cmp = comparison["收入对比（万元，不含税）"]
    noi_cmp = comparison["NOI推导（万元）"]

    print(f"\n{'项目':<16} {'2024历史':>10} {'Y1预测':>10} {'增长率':>8}")
    print("-" * 50)
    for i, name in enumerate(rev_cmp["项目"]):
        h = rev_cmp["2024历史"][i]
        f = rev_cmp["Y1预测(2026)"][i]
        g = rev_cmp["增长率(%)"][i]
        g_str = f"{g:+.1f}%" if g is not None else "N/A"
        print(f"{name:<16} {h:>10,.0f} {f:>10,.0f} {g_str:>8}")

    print(f"\nY1 NOI推导:")
    for k, v in noi_cmp.items():
        print(f"  {k}: {v:,.0f}" if isinstance(v, (int, float)) else f"  {k}: {v}")

    # ── 2. Y1逐项明细 ────────────────────────────────────────────────
    print("\n【Step 2】Y1成本/税金明细")
    y1 = MallNOIDeriver.derive_year(1, mall_proj)
    print(f"\n  成本明细（万元）：")
    print(f"    营销推广费:  {y1.marketing_promo_cost:>8,.0f}")
    print(f"    物业管理费:  {y1.prop_mgmt_cost:>8,.0f}")
    print(f"    房屋大修:    {y1.repairs_cost:>8,.0f}")
    print(f"    人工成本:    {y1.labor_cost:>8,.0f}")
    print(f"    行政管理费:  {y1.admin_cost:>8,.0f}")
    print(f"    商业平台费:  {y1.platform_fee:>8,.0f}")
    print(f"    冰场支出:    {y1.ice_rink_cost:>8,.0f}")
    print(f"    保险费:      {y1.insurance_cost:>8,.0f}")
    print(f"    合计成本:    {y1.total_opex:>8,.0f}")

    print(f"\n  税金明细（万元）：")
    print(f"    增值税(一期): {y1.vat_phase1:>8,.0f}")
    print(f"    增值税(二期): {y1.vat_phase2:>8,.0f}")
    print(f"    增值税(联营): {y1.vat_joint_op:>8,.0f}")
    print(f"    增值税(停车): {y1.vat_parking:>8,.0f}")
    print(f"    增值税(服务): {y1.vat_services:>8,.0f}")
    print(f"    增值税合计:   {y1.vat_total:>8,.0f}")
    print(f"    增值税附加:   {y1.vat_surtax:>8,.0f}")
    print(f"    房产税(从租): {y1.property_tax_from_rent:>8,.0f}")
    print(f"    房产税(从值): {y1.property_tax_from_value:>8,.0f}")
    print(f"    土地使用税:   {y1.land_use_tax:>8,.0f}")
    print(f"    印花税:       {y1.stamp_duty:>8,.0f}")
    print(f"    合计税金:     {y1.total_tax:>8,.0f}")

    print(f"\n  资本性支出:    {y1.capex:>8,.0f}")
    print(f"  FCF (NOI-Capex): {y1.fcf:>8,.0f}")

    # ── 3. DCF估值 ────────────────────────────────────────────────────
    print("\n【Step 3】DCF估值 vs 报告披露")
    model = MallDCFModel(extracted, detailed)
    result = model.calculate()

    target_wan = 920500  # 9.205亿 × 100 = 920,500万
    diff_pct = (result.total_valuation - target_wan) / target_wan * 100

    print(f"\n  模型估值:     {result.total_valuation:>12,.0f} 万元 ({result.total_valuation/10000:.2f} 亿)")
    print(f"  报告披露:     {target_wan:>12,} 万元 ({target_wan/10000:.2f} 亿)")
    print(f"  差异:         {result.total_valuation - target_wan:>+12,.0f} 万元 ({diff_pct:+.2f}%)")
    print(f"\n  Y1 FCF:       {result.total_noi_year1:>12,.0f} 万元")
    print(f"  隐含资本化率: {result.implied_cap_rate*100:.2f}%")
    print(f"  折现率:       {result.discount_rate*100:.1f}%")

    # ── 4. 前5年现金流 ────────────────────────────────────────────────
    print("\n【Step 4】前5年FCF现金流（万元）")
    print(f"{'年期':<6} {'NOI':>10} {'Capex':>8} {'FCF':>10} {'PV':>10}")
    print("-" * 48)
    for cf in result.projects[0].cash_flows[:5]:
        print(f"Y{cf.year:<5} {cf.noi:>10,.0f} {cf.capex:>8,.0f} {cf.fcf:>10,.0f} {cf.pv:>10,.0f}")

    # ── 5. 输出JSON报告 ───────────────────────────────────────────────
    report = {
        "model_valuation_wan": round(result.total_valuation, 0),
        "report_valuation_wan": target_wan,
        "diff_wan": round(result.total_valuation - target_wan, 0),
        "diff_pct": round(diff_pct, 2),
        "y1_fcf_wan": round(result.total_noi_year1, 0),
        "discount_rate": result.discount_rate,
        "implied_cap_rate": round(result.implied_cap_rate, 4),
        "y1_noi_breakdown": {
            "total_revenue": round(y1.total_revenue, 0),
            "fixed_rent": round(y1.fixed_rent, 0),
            "perf_rent": round(y1.perf_rent, 0),
            "joint_op_net": round(y1.joint_op_net, 0),
            "prop_mgmt_fee": round(y1.prop_mgmt_fee, 0),
            "marketing_fee_income": round(y1.marketing_fee_income, 0),
            "parking_excl_tax": round(y1.parking_excl_tax, 0),
            "multi_channel": round(y1.multi_channel, 0),
            "ice_rink_revenue": round(y1.ice_rink_revenue, 0),
            "other_revenue": round(y1.other_revenue, 0),
            "total_opex": round(y1.total_opex, 0),
            "total_tax": round(y1.total_tax, 0),
            "capex": round(y1.capex, 0),
            "noi": round(y1.noi, 0),
            "fcf": round(y1.fcf, 0),
        },
        "all_year_cashflows": [
            {"year": cf.year, "noi": cf.noi, "capex": cf.capex, "fcf": cf.fcf, "pv": cf.pv}
            for cf in result.projects[0].cash_flows
        ],
    }
    write_report(json.dumps(report, ensure_ascii=False, indent=2), "mall_dcf_validation.json")

    print("\n" + "=" * 60)
    if abs(diff_pct) <= 5:
        print(f"✅ 估值误差 {diff_pct:+.2f}% ≤ 5%，模型可还原性良好")
    elif abs(diff_pct) <= 10:
        print(f"⚠️  估值误差 {diff_pct:+.2f}%，需检查参数设定")
    else:
        print(f"❌ 估值误差 {diff_pct:+.2f}%，需调整关键假设")
    print("=" * 60)


if __name__ == "__main__":
    main()
