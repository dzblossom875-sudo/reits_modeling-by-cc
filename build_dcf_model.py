#!/usr/bin/env python3
"""
华住REIT DCF建模脚本
基于提取的真实数据构建DCF估值模型
"""

import json
import sys
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
import math

def load_extracted_data(path: str) -> Dict[str, Any]:
    """加载提取的数据"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@dataclass
class ProjectDCF:
    """单个项目DCF模型"""
    name: str
    base_noicf: float  # 首年NOI/CF（已扣capex）
    base_capex: float  # 首年资本性支出
    remaining_years: float
    capex_forecast: List[float]
    discount_rate: float = 0.0575
    revenue_growth: float = 0.01  # 默认1%温和增长
    use_prospectus_growth: bool = False  # 是否使用招募说明书的分段增长率

    @property
    def base_noi(self) -> float:
        """
        运营现金流NOI（不扣除资本性支出）
        从NOI/CF反推：NOI = NOI/CF + capex
        """
        return self.base_noicf + self.base_capex

    def get_growth_rate_for_year(self, year: int) -> float:
        """
        获取指定年份的增长率

        注意：广州项目和上海项目的增长率不同
        - 广州项目（Page 250）：2027年2%，其余与上海相同
        - 上海项目（Page 236）：2027年1%，2028年2%，2029-2035年3%，2036年后2.25%

        分段增长率（year从1开始，1=2026年）：
        - 第1年（2026年）：0%（基准年）
        - 第2年（2027年）：广州2%，上海1%
        - 第3年（2028年）：2%
        - 第4-10年（2029-2035年）：3%
        - 第11年起（2036年+）：2.25%
        """
        if not self.use_prospectus_growth:
            return self.revenue_growth

        # 判断项目类型（根据名称判断）
        is_guangzhou = "广州" in self.name

        # 分段增长率
        if year == 1:
            # 2026年：基准年，不增长
            return 0.0
        elif year == 2:  # 2027年
            # 广州项目2%，上海项目1%
            return 0.02 if is_guangzhou else 0.01
        elif year == 3:  # 2028年
            return 0.02  # 2%
        elif 4 <= year <= 10:  # 2029-2035年
            return 0.03  # 3%
        else:  # 2036年及以后
            return 0.0225  # 2.25%

    def calculate_growth_rate(self) -> float:
        """计算增长率提示"""
        return self.revenue_growth

    def generate_cash_flows(self) -> List[Dict[str, Any]]:
        """生成未来现金流预测（持有到期，残值归零）"""
        cash_flows = []
        years = int(self.remaining_years)

        # 累积增长因子
        cumulative_growth = 1.0

        for year in range(1, years + 1):
            # 获取当年增长率
            growth_rate = self.get_growth_rate_for_year(year)

            # 更新累积增长因子（首年为基础值）
            if year == 1:
                cumulative_growth = 1.0
            else:
                cumulative_growth *= (1 + growth_rate)

            # 运营现金流NOI（不扣除capex）
            noi = self.base_noi * cumulative_growth

            # 资本性支出
            if year <= len(self.capex_forecast):
                capex = self.capex_forecast[year - 1]
            else:
                # 后续年份capex也按增长率增长（简化处理）
                base_capex = self.capex_forecast[-1] if self.capex_forecast else 0
                # capex增长幅度较小，按2%年化增长
                capex = base_capex * ((1.02) ** (year - len(self.capex_forecast)))

            # 自由现金流 = NOI - capex
            fcf = noi - capex

            # 折现计算
            discount_factor = (1 + self.discount_rate) ** year
            pv = fcf / discount_factor

            cash_flows.append({
                "year": year,
                "noi": round(noi, 2),
                "capex": round(capex, 2),
                "fcf": round(fcf, 2),
                "growth_rate": growth_rate,
                "cumulative_growth": round(cumulative_growth, 4),
                "discount_factor": round(discount_factor, 4),
                "pv": round(pv, 2)
            })

        return cash_flows

    def calculate_dcf(self) -> Dict[str, float]:
        """计算DCF估值（持有到期，无终值）"""
        cash_flows = self.generate_cash_flows()

        total_pv = sum(cf["pv"] for cf in cash_flows)

        # 持有到期模型，残值归零
        terminal_value = 0

        return {
            "pv_cash_flows": round(total_pv, 2),
            "pv_terminal": 0,
            "total_valuation": round(total_pv, 2),
            "cash_flows": cash_flows
        }


class HuazhuDCFModel:
    """华住REIT整体DCF模型"""

    def __init__(self, extracted_data: Dict[str, Any], revenue_growth: float = 0.03, use_prospectus_growth: bool = False):
        self.data = extracted_data
        self.discount_rate = extracted_data.get("valuation_parameters", {}).get("discount_rate", 0.0575)
        self.revenue_growth = revenue_growth  # 默认增长率
        self.use_prospectus_growth = use_prospectus_growth  # 是否使用招募说明书的分段增长率

        # 计算历史增长率作为对比提示
        self._calculate_historical_growth()

        # 创建项目模型
        self.projects = self._create_project_models()

    def _calculate_historical_growth(self):
        """计算历史ADR增长率"""
        projects = self.data.get("projects", [])

        growth_rates = []
        for p in projects:
            adr_2023 = p.get("adr_2023", 0)
            adr_2025 = p.get("adr_2025", 0)
            if adr_2023 > 0 and adr_2025 > 0:
                # 两年复合增长率
                cagr = (adr_2025 / adr_2023) ** 0.5 - 1
                growth_rates.append(cagr)

        self.historical_growth = sum(growth_rates) / len(growth_rates) if growth_rates else -0.028

    def _create_project_models(self) -> List[ProjectDCF]:
        """创建各项目DCF模型"""
        projects = []
        fin_data = self.data.get("financial_data", {})

        # 广州项目
        gz_data = fin_data.get("广州项目", {})
        gz_remaining = self.data.get("projects", [{}])[0].get("remaining_years", 19.28)
        gz_capex = gz_data.get("capex_forecast", [141.63, 145.16, 148.77])
        gz_base_capex = gz_capex[0] if gz_capex else 141.63  # 首年capex

        # 评估基准日2025年12月31日，首年NOI应为2026年数据（Page 235表格）
        # 2026年年净收益 = 8,107.60万元（已扣capex）
        # 基础NOI = 年净收益 + capex = 8,107.60 + 141.63 = 8,249.23万元
        gz_2026_noicf = 8107.60  # 来自Page 235表格：年净收益

        projects.append(ProjectDCF(
            name="广州项目（美居+全季）",
            base_noicf=gz_2026_noicf,  # 2026年年净收益（已扣capex）
            base_capex=gz_base_capex,
            remaining_years=gz_remaining,
            capex_forecast=gz_capex,
            discount_rate=self.discount_rate,
            revenue_growth=self.revenue_growth,
            use_prospectus_growth=self.use_prospectus_growth
        ))

        # 上海项目
        sh_data = fin_data.get("上海项目", {})
        sh_remaining = self.data.get("projects", [{}])[2].get("remaining_years", 30.65)
        sh_capex = sh_data.get("capex_forecast", [38.92, 39.89, 40.88])
        sh_base_capex = sh_capex[0] if sh_capex else 38.92  # 首年capex

        # 评估基准日2025年12月31日，首年NOI应为2026年数据（Page 241表格）
        # 2026年年净收益 = 1,752.07万元（已扣capex）
        # 基础NOI = 年净收益 + capex = 1,752.07 + 38.92 = 1,790.99万元
        sh_2026_noicf = 1752.07  # 来自Page 241表格：年净收益

        projects.append(ProjectDCF(
            name="上海项目（桔子水晶）",
            base_noicf=sh_2026_noicf,  # 2026年年净收益（已扣capex）
            base_capex=sh_base_capex,
            remaining_years=sh_remaining,
            capex_forecast=sh_capex,
            discount_rate=self.discount_rate,
            revenue_growth=self.revenue_growth,
            use_prospectus_growth=self.use_prospectus_growth
        ))

        return projects

    def calculate(self) -> Dict[str, Any]:
        """执行完整DCF计算"""
        results = {
            "projects": [],
            "total_valuation": 0,
            "total_pv_cash_flows": 0
        }

        for proj in self.projects:
            proj_result = proj.calculate_dcf()
            results["projects"].append({
                "name": proj.name,
                "remaining_years": proj.remaining_years,
                "base_noi": round(proj.base_noi, 2),
                "base_capex": round(proj.base_capex, 2),
                "base_fcf": round(proj.base_noi - proj.base_capex, 2),
                "valuation": proj_result["total_valuation"],
                "pv_cash_flows": proj_result["pv_cash_flows"],
                "cash_flows": proj_result["cash_flows"]
            })
            results["total_valuation"] += proj_result["total_valuation"]
            results["total_pv_cash_flows"] += proj_result["pv_cash_flows"]

        # 计算KPI
        total_noicf = self.data.get("total_annual_noicf", 2735.65)
        results["kpis"] = {
            "total_rooms": self.data.get("total_rooms", 1044),
            "value_per_room": round(results["total_valuation"] * 10000 / self.data.get("total_rooms", 1044), 2),
            "implied_cap_rate": round(total_noicf / results["total_valuation"], 4),
            "annual_yield": round(total_noicf / results["total_valuation"], 4)
        }

        # 对比分析
        results["comparison"] = {
            "dcf_valuation_billion": round(results["total_valuation"] / 10000, 2),
            "fund_raise_billion": 13.2,
            "asset_valuation_billion": 15.91,
            "vs_fund_raise": round(results["total_valuation"] / 10000 - 13.2, 2),
            "vs_asset_valuation": round(results["total_valuation"] / 10000 - 15.91, 2)
        }

        return results

    def sensitivity_analysis(self) -> Dict[str, Any]:
        """敏感性分析"""
        base_result = self.calculate()
        base_valuation = base_result["total_valuation"]

        # 折现率敏感性
        dr_results = {}
        for dr in [0.045, 0.05, 0.055, 0.0575, 0.06, 0.065, 0.07]:
            self.discount_rate = dr
            self.projects = self._create_project_models()
            result = self.calculate()
            dr_results[f"{dr:.2%}"] = round(result["total_valuation"], 2)

        # 恢复基准
        self.discount_rate = 0.0575
        self.projects = self._create_project_models()

        # 增长率敏感性
        gr_results = {}
        for gr in [0.0, 0.005, 0.01, 0.015, 0.02]:
            self.revenue_growth = gr
            self.projects = self._create_project_models()
            result = self.calculate()
            gr_results[f"{gr:.1%}"] = round(result["total_valuation"], 2)

        # 恢复基准
        self.revenue_growth = 0.01
        self.projects = self._create_project_models()

        return {
            "discount_rate_sensitivity": dr_results,
            "growth_rate_sensitivity": gr_results,
            "base_valuation": round(base_valuation, 2)
        }

    def export_to_dict(self) -> Dict[str, Any]:
        """导出完整结果"""
        return {
            "fund_info": self.data.get("fund_info", {}),
            "dcf_inputs": {
                "discount_rate": self.discount_rate,
                "discount_rate_percent": f"{self.discount_rate:.2%}",
                "revenue_growth": self.revenue_growth,
                "revenue_growth_percent": f"{self.revenue_growth:.1%}",
                "historical_growth": self.historical_growth,
                "historical_growth_percent": f"{self.historical_growth:.1%}",
                "growth_note": "历史ADR负增长，采用1%温和增长假设",
                "valuation_method": "报酬率全周期DCF法（持有到期，残值归零）"
            },
            "dcf_results": self.calculate(),
            "sensitivity": self.sensitivity_analysis(),
            "extraction_source": self.data.get("source_pages", {})
        }


def generate_csv_output(model: HuazhuDCFModel, output_dir: Path):
    """生成CSV输出"""
    import csv

    result = model.calculate()

    # 1. 现金流明细表
    cf_path = output_dir / "dcf_cashflows.csv"
    with open(cf_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["项目名称", "年份", "NOI(万元)", "资本性支出(万元)", "自由现金流(万元)", "折现因子", "现值(万元)"])

        for proj in result["projects"]:
            for cf in proj["cash_flows"]:
                writer.writerow([
                    proj["name"],
                    cf["year"],
                    cf["noi"],
                    cf["capex"],
                    cf["fcf"],
                    cf["discount_factor"],
                    cf["pv"]
                ])

    # 2. 估值汇总表
    summary_path = output_dir / "dcf_summary.csv"
    with open(summary_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["指标", "数值", "单位"])
        writer.writerow(["", "", ""])
        writer.writerow(["DCF估值结果", "", ""])
        writer.writerow(["折现率", f"{model.discount_rate:.2%}", ""])
        writer.writerow(["收入增长率", f"{model.revenue_growth:.1%}", "假设值（用户指定）"])
        writer.writerow(["历史ADR增长", f"{model.historical_growth:.1%}", "2023-2025实际"])
        writer.writerow(["", "", ""])

        for proj in result["projects"]:
            writer.writerow([f"{proj['name']}", "", ""])
            writer.writerow(["  预测年限", proj["remaining_years"], "年"])
            writer.writerow(["  首年运营NOI", proj["base_noi"], "万元（不扣capex）"])
            writer.writerow(["  首年资本性支出", proj["base_capex"], "万元"])
            writer.writerow(["  首年自由现金流", proj["base_fcf"], "万元"])
            writer.writerow(["  估值", proj["valuation"], "万元"])
            writer.writerow(["", "", ""])

        writer.writerow(["总估值", round(result["total_valuation"], 2), "万元"])
        writer.writerow(["总估值", round(result["total_valuation"] / 10000, 2), "亿元"])
        writer.writerow(["", "", ""])
        writer.writerow(["对比分析", "", ""])
        writer.writerow(["vs 募集资金", result["comparison"]["vs_fund_raise"], "亿元"])
        writer.writerow(["vs 资产评估值", result["comparison"]["vs_asset_valuation"], "亿元"])
        writer.writerow(["", "", ""])
        writer.writerow(["关键指标", "", ""])
        writer.writerow(["单房估值", result["kpis"]["value_per_room"], "元/间"])
        writer.writerow(["隐含资本化率", f"{result['kpis']['implied_cap_rate']:.2%}", ""])

    # 3. 敏感性分析表
    sens = model.sensitivity_analysis()
    sens_path = output_dir / "dcf_sensitivity.csv"
    with open(sens_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["折现率敏感性分析"])
        writer.writerow(["折现率", "总估值(万元)"])
        for dr, val in sens["discount_rate_sensitivity"].items():
            marker = " <-- 基准" if dr == "5.75%" else ""
            writer.writerow([dr, f"{val}{marker}"])

        writer.writerow([])
        writer.writerow(["增长率敏感性分析"])
        writer.writerow(["增长率", "总估值(万元)"])
        for gr, val in sens["growth_rate_sensitivity"].items():
            marker = " <-- 基准" if gr == "1.0%" else ""
            writer.writerow([gr, f"{val}{marker}"])

    return cf_path, summary_path, sens_path


def run_dcf_scenario(extracted_data: Dict[str, Any], scenario_name: str,
                     use_prospectus_growth: bool = False, revenue_growth: float = 0.01,
                     output_suffix: str = "") -> tuple:
    """
    运行单个DCF情景分析

    Args:
        extracted_data: 提取的数据
        scenario_name: 情景名称
        use_prospectus_growth: 是否使用招募说明书的分段增长率
        revenue_growth: 基础增长率（当不使用招募说明书增长率时）
        output_suffix: 输出文件后缀

    Returns:
        (model, results) 元组
    """
    print(f"\n{'='*60}")
    print(f"情景: {scenario_name}")
    print("="*60)

    # 构建模型
    model = HuazhuDCFModel(
        extracted_data,
        revenue_growth=revenue_growth,
        use_prospectus_growth=use_prospectus_growth
    )

    if use_prospectus_growth:
        print("增长率假设（招募说明书第236页）：")
        print("  - 2027年（第2年）：1%")
        print("  - 2028年（第3年）：2%")
        print("  - 2029-2035年（第4-10年）：3%")
        print("  - 2036年后（第11年起）：2.25%")
    else:
        print(f"增长率假设：固定{revenue_growth:.1%}")

    # 计算估值
    results = model.calculate()
    print(f"\n估值结果：")
    print(f"  - 广州项目估值: {results['projects'][0]['valuation']:,.2f}万元")
    print(f"  - 上海项目估值: {results['projects'][1]['valuation']:,.2f}万元")
    print(f"  - 总估值: {results['total_valuation']:,.2f}万元 ({results['total_valuation']/10000:.2f}亿元)")

    # 对比分析
    comp = results["comparison"]
    print(f"\n对比分析：")
    print(f"  - 资产评估值: {comp['asset_valuation_billion']:.2f}亿元")
    print(f"  - DCF估值: {comp['dcf_valuation_billion']:.2f}亿元")
    print(f"  - vs 评估值: {comp['vs_asset_valuation']:+.2f}亿元 ({(comp['dcf_valuation_billion']/comp['asset_valuation_billion']-1)*100:+.1f}%)")

    # KPI
    kpis = results["kpis"]
    print(f"\n关键指标：")
    print(f"  - 单房估值: {kpis['value_per_room']:,.0f}元/间")
    print(f"  - 隐含资本化率: {kpis['implied_cap_rate']:.2%}")

    return model, results


def main():
    """主函数"""
    base_path = Path(__file__).parent
    extracted_path = base_path / "tmp/huazhu_extract/extracted_params.json"
    output_dir = base_path / "output/huazhu_dcf_model"

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("华住REIT DCF估值模型 - 多情景分析")
    print("=" * 80)

    # 加载数据
    print(f"\n加载提取数据: {extracted_path}")
    extracted_data = load_extracted_data(str(extracted_path))
    print(f"   - 基金名称: {extracted_data.get('project_name')}")
    print(f"   - 项目数量: {len(extracted_data.get('projects', []))}")
    print(f"   - 折现率: {extracted_data.get('valuation_parameters', {}).get('discount_rate_percent', '5.75%')}")

    # 运行两个情景
    scenarios = []

    # 情景1: 基础情景（1%固定增长）
    model1, results1 = run_dcf_scenario(
        extracted_data,
        scenario_name="基础情景（1%固定增长）",
        use_prospectus_growth=False,
        revenue_growth=0.01,
        output_suffix="_base"
    )
    scenarios.append(("基础情景（1%固定增长）", model1, results1))

    # 情景2: 招募说明书情景（分段增长率）
    model2, results2 = run_dcf_scenario(
        extracted_data,
        scenario_name="招募说明书情景（分段增长率）",
        use_prospectus_growth=True,
        revenue_growth=0.01,  # 这个值不会被使用
        output_suffix="_prospectus"
    )
    scenarios.append(("招募说明书情景", model2, results2))

    # 对比总结
    print(f"\n{'='*60}")
    print("情景对比总结")
    print("="*60)
    print(f"{'情景':<25} {'总估值(亿元)':<15} {'vs评估值':<15}")
    print("-"*60)
    for name, model, results in scenarios:
        valuation_b = results['total_valuation']/10000
        vs_asset = results['comparison']['vs_asset_valuation']
        print(f"{name:<25} {valuation_b:<15.2f} {vs_asset:+.2f}亿元")

    # 使用招募说明书情景作为主要输出
    print(f"\n{'='*60}")
    print("选择招募说明书情景作为最终输出")
    print("="*60)
    model = model2
    results = results2

    # 导出CSV
    print(f"\n7. 导出结果")
    cf_path, summary_path, sens_path = generate_csv_output(model, output_dir)
    print(f"   - 现金流明细: {cf_path}")
    print(f"   - 估值汇总: {summary_path}")
    print(f"   - 敏感性分析: {sens_path}")

    # 导出JSON
    json_path = output_dir / "dcf_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(model.export_to_dict(), f, ensure_ascii=False, indent=2)
    print(f"   - JSON结果: {json_path}")

    print(f"\n" + "=" * 80)
    print("DCF建模完成")
    print("=" * 80)

    return model, results


if __name__ == "__main__":
    model, results = main()
