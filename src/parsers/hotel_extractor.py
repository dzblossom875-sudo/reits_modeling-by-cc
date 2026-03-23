"""
酒店REITs专用参数提取器
支持多项目、酒店+商业混合结构的复杂提取
增强版：完整模板、来源分类、历史多年数据
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from ..core.types import ParsedDocument, ExtractedParam, Table
from ..core.config import AssetType, SourceCategory
from .hotel_template import (
    HOTEL_REIT_TEMPLATE, TemplateField, FieldTier,
    get_all_regex_patterns, get_all_table_keywords,
    generate_extraction_checklist,
)


@dataclass
class HotelProject:
    """单个酒店项目数据结构"""
    name: str = ""                          # 项目名称

    # 酒店部分
    adr: float = 0.0                        # 平均房价（元/晚）
    occupancy_rate: float = 0.0             # 入住率
    room_count: int = 0                     # 客房数
    room_revenue_growth: float = 0.03       # 客房收入增长率

    # 收入细分
    room_revenue: float = 0.0               # 客房收入（万元）
    ota_revenue: float = 0.0                # OTA收入（万元）
    fb_revenue: float = 0.0                 # 餐饮收入（万元）
    other_revenue: float = 0.0              # 其他收入（万元）

    # 运营费用
    operating_expenses: Dict[str, float] = field(default_factory=dict)  # 各项运营费用
    total_operating_expense: float = 0.0    # 总运营费用（万元）

    # 商业部分
    commercial_rent: float = 0.0            # 商业租金收入（万元）
    commercial_management_fee: float = 0.0  # 商业物业管理费（万元）
    commercial_operating_expense: float = 0.0  # 商业运营费用（万元）

    # 其他费用
    property_fee: float = 0.0               # 物业费（万元）
    insurance: float = 0.0                  # 保险费（万元）
    property_tax: float = 0.0               # 房产税（万元）
    land_use_tax: float = 0.0               # 土地使用税（万元）
    management_fee: float = 0.0             # 酒店管理公司管理费（万元）

    # 资本性支出
    capex: float = 0.0                      # 资本性支出（万元）

    def calculate_hotel_revenue(self) -> float:
        """计算酒店部分总收入"""
        return self.room_revenue + self.ota_revenue + self.fb_revenue + self.other_revenue

    def calculate_gop(self) -> float:
        """计算酒店部分GOP（营业毛利）"""
        return self.calculate_hotel_revenue() - self.total_operating_expense

    def calculate_commercial_net(self) -> float:
        """计算商业部分净收益"""
        commercial_income = self.commercial_rent + self.commercial_management_fee
        return commercial_income - self.commercial_operating_expense

    def calculate_other_expenses(self) -> float:
        """计算其他总费用"""
        return (self.property_fee + self.insurance + self.property_tax +
                self.land_use_tax + self.management_fee)

    def calculate_noicf(self) -> float:
        """
        计算年净收益（NOI/CF）
        公式：酒店GOP + 商业净收益 - 其他费用 - 资本性支出
        """
        return (self.calculate_gop() + self.calculate_commercial_net() -
                self.calculate_other_expenses() - self.capex)


@dataclass
class HotelREITExtractedData:
    """酒店REIT提取的完整数据"""
    projects: List[HotelProject] = field(default_factory=list)
    discount_rate: float = 0.075            # 折现率
    remaining_years: int = 19               # 剩余年限

    def get_total_noicf(self) -> float:
        """获取所有项目年净收益合计"""
        return sum(p.calculate_noicf() for p in self.projects)

    def get_aggregate_data(self) -> Dict[str, Any]:
        """获取汇总数据"""
        total_room_revenue = sum(p.room_revenue for p in self.projects)
        total_ota = sum(p.ota_revenue for p in self.projects)
        total_fb = sum(p.fb_revenue for p in self.projects)
        total_other = sum(p.other_revenue for p in self.projects)
        total_opex = sum(p.total_operating_expense for p in self.projects)
        total_noicf = self.get_total_noicf()

        return {
            "project_count": len(self.projects),
            "total_room_revenue": total_room_revenue,
            "total_ota_revenue": total_ota,
            "total_fb_revenue": total_fb,
            "total_other_revenue": total_other,
            "total_operating_expense": total_opex,
            "total_noicf": total_noicf,
            "weighted_avg_adr": sum(p.adr * p.room_count for p in self.projects) /
                               sum(p.room_count for p in self.projects) if self.projects else 0,
            "weighted_avg_occupancy": sum(p.occupancy_rate * p.room_count for p in self.projects) /
                                     sum(p.room_count for p in self.projects) if self.projects else 0,
        }


class HotelREITExtractor:
    """酒店REIT专用提取器"""

    # 华住REIT特定关键词模式
    PROJECT_NAME_PATTERNS = [
        r"南京\w+酒店",
        r"汉庭\w+酒店",
        r"全季\w+酒店",
        r"桔子\w+酒店",
    ]

    REVENUE_PATTERNS = {
        "adr": [
            r"平均房价.*?([\d,]+\.?\d*)\s*元",
            r"ADR.*?([\d,]+\.?\d*)",
            r"日均房价.*?([\d,]+\.?\d*)",
        ],
        "occupancy_rate": [
            r"入住率.*?([\d\.]+)\s*%",
            r"出租率.*?([\d\.]+)\s*%",
            r"Occ.*?([\d\.]+)\s*%",
        ],
        "room_count": [
            r"客房数.*?([\d,]+)\s*间",
            r"房间数.*?([\d,]+)",
            r"客房间数.*?([\d,]+)",
        ],
        "room_revenue": [
            r"客房收入.*?([\d,]+\.?\d*)\s*万",
            r"房间收入.*?([\d,]+\.?\d*)\s*万",
        ],
        "fb_revenue": [
            r"餐饮收入.*?([\d,]+\.?\d*)\s*万",
            r"F&B收入.*?([\d,]+\.?\d*)",
        ],
        "ota_revenue": [
            r"OTA收入.*?([\d,]+\.?\d*)\s*万",
            r"在线旅游.*?([\d,]+\.?\d*)\s*万",
            r"渠道收入.*?([\d,]+\.?\d*)\s*万",
        ],
    }

    EXPENSE_PATTERNS = {
        "personnel": r"人工.*?([\d,]+\.?\d*)\s*万",
        "fb_cost": r"餐饮成本.*?([\d,]+\.?\d*)\s*万",
        "cleaning": r"清洁.*?([\d,]+\.?\d*)\s*万",
        "utilities": r"能源.*?([\d,]+\.?\d*)\s*万",
        "maintenance": r"维护.*?([\d,]+\.?\d*)\s*万",
        "marketing": r"营销.*?([\d,]+\.?\d*)\s*万",
    }

    def __init__(self):
        self.data = HotelREITExtractedData()

    def extract(self, doc: ParsedDocument) -> HotelREITExtractedData:
        """
        从文档中提取酒店REIT完整数据

        Args:
            doc: 解析后的文档

        Returns:
            提取的完整数据
        """
        # 1. 识别项目数量
        projects = self._identify_projects(doc)

        # 2. 从表格中提取详细数据
        for table in doc.tables:
            self._extract_from_table(table, projects)

        # 3. 从文本中提取补充数据
        self._extract_from_text(doc.text, projects)

        # 4. 提取全局参数（折现率、年限等）
        self._extract_global_params(doc)

        self.data.projects = list(projects.values())
        return self.data

    def _identify_projects(self, doc: ParsedDocument) -> Dict[str, HotelProject]:
        """识别文档中的所有酒店项目"""
        projects = {}

        # 尝试从文本中识别项目名称
        for pattern in self.PROJECT_NAME_PATTERNS:
            matches = re.finditer(pattern, doc.text)
            for match in matches:
                name = match.group(0)
                if name not in projects:
                    projects[name] = HotelProject(name=name)

        # 如果没找到，尝试从表格中识别
        if not projects:
            for table in doc.tables:
                for row in table.rows:
                    for cell in row:
                        for pattern in self.PROJECT_NAME_PATTERNS:
                            if re.search(pattern, str(cell)):
                                name = re.search(pattern, str(cell)).group(0)
                                if name not in projects:
                                    projects[name] = HotelProject(name=name)

        # 如果还是没找到，创建一个默认项目
        if not projects:
            projects["华住酒店项目"] = HotelProject(name="华住酒店项目")

        return projects

    def _extract_from_table(self, table: Table, projects: Dict[str, HotelProject]):
        """从表格中提取数据"""
        # 识别表格类型
        headers_str = " ".join(table.headers).lower()

        # 收入表
        if any(kw in headers_str for kw in ["收入", "营收", "adr", "入住率"]):
            self._extract_revenue_table(table, projects)

        # 费用表
        elif any(kw in headers_str for kw in ["费用", "成本", "支出", "运营"]):
            self._extract_expense_table(table, projects)

        # 税费表
        elif any(kw in headers_str for kw in ["税", "保险", "物业"]):
            self._extract_other_expenses_table(table, projects)

    def _extract_revenue_table(self, table: Table, projects: Dict[str, HotelProject]):
        """提取收入相关表格"""
        # 查找ADR、入住率、收入等列
        adr_col = self._find_column_index(table.headers, ["adr", "平均房价", "房价"])
        occ_col = self._find_column_index(table.headers, ["入住率", "出租率", "occ"])
        room_col = self._find_column_index(table.headers, ["客房收入", "房费收入"])
        fb_col = self._find_column_index(table.headers, ["餐饮", "fb"])

        for row in table.rows:
            # 尝试匹配项目名称
            project_name = self._match_project_name(row, projects)
            if not project_name:
                continue

            proj = projects[project_name]

            # 提取ADR
            if adr_col is not None and adr_col < len(row):
                value = self._parse_numeric(row[adr_col])
                if value > 0:
                    proj.adr = value

            # 提取入住率
            if occ_col is not None and occ_col < len(row):
                value = self._parse_rate(row[occ_col])
                if value > 0:
                    proj.occupancy_rate = value

            # 提取客房收入
            if room_col is not None and room_col < len(row):
                value = self._parse_numeric(row[room_col])
                if value > 0:
                    proj.room_revenue = value

            # 提取餐饮收入
            if fb_col is not None and fb_col < len(row):
                value = self._parse_numeric(row[fb_col])
                if value > 0:
                    proj.fb_revenue = value

    def _extract_expense_table(self, table: Table, projects: Dict[str, HotelProject]):
        """提取费用相关表格"""
        # 简化处理：提取总运营费用
        for row in table.rows:
            row_text = " ".join(row).lower()

            if "合计" in row_text or "总计" in row_text or "总费用" in row_text:
                for cell in row:
                    value = self._parse_numeric(cell)
                    if value > 100:  # 假设总费用至少100万
                        # 分配到所有项目（简化）
                        for proj in projects.values():
                            if proj.total_operating_expense == 0:
                                proj.total_operating_expense = value / len(projects)
                        break

    def _extract_other_expenses_table(self, table: Table, projects: Dict[str, HotelProject]):
        """提取其他费用表（税、保险、物业等）"""
        for row in table.rows:
            row_text = " ".join(row)

            for cell in row:
                value = self._parse_numeric(cell)
                if value <= 0:
                    continue

                if "房产税" in row_text:
                    for proj in projects.values():
                        proj.property_tax = value / len(projects)
                elif "土地" in row_text and "税" in row_text:
                    for proj in projects.values():
                        proj.land_use_tax = value / len(projects)
                elif "保险" in row_text:
                    for proj in projects.values():
                        proj.insurance = value / len(projects)
                elif "物业" in row_text and "管理" in row_text:
                    for proj in projects.values():
                        proj.property_fee = value / len(projects)
                elif "管理费" in row_text:
                    for proj in projects.values():
                        proj.management_fee = value / len(projects)

    def _extract_from_text(self, text: str, projects: Dict[str, HotelProject]):
        """从文本中提取补充数据"""
        # 提取折现率
        discount_patterns = [
            r"折现率.*?([\d\.]+)\s*%",
            r"WACC.*?([\d\.]+)\s*%",
            r"要求回报率.*?([\d\.]+)\s*%",
        ]
        for pattern in discount_patterns:
            match = re.search(pattern, text)
            if match:
                self.data.discount_rate = float(match.group(1)) / 100
                break

        # 提取剩余年限
        year_patterns = [
            r"剩余年限.*?([\d\.]+)\s*年",
            r"特许经营.*?([\d\.]+)\s*年",
            r"期限.*?([\d\.]+)\s*年",
        ]
        for pattern in year_patterns:
            match = re.search(pattern, text)
            if match:
                self.data.remaining_years = int(float(match.group(1)))
                break

        # 提取资本性支出
        capex_patterns = [
            r"资本性支出.*?([\d,]+\.?\d*)\s*万",
            r"capex.*?([\d,]+\.?\d*)\s*万",
        ]
        for pattern in capex_patterns:
            match = re.search(pattern, text)
            if match:
                capex = float(match.group(1).replace(",", ""))
                for proj in projects.values():
                    proj.capex = capex / len(projects)
                break

    def _extract_global_params(self, doc: ParsedDocument):
        """提取全局参数"""
        text = doc.text

        # 尝试多种模式提取关键参数
        # 折现率
        for pattern in [r"折现率[：:]\s*([\d\.]+)\s*%", r"WACC[：:]\s*([\d\.]+)\s*%"]:
            match = re.search(pattern, text)
            if match:
                self.data.discount_rate = float(match.group(1)) / 100
                break

        # 剩余年限
        for pattern in [r"剩余年限[：:]\s*([\d\.]+)", r"特许经营期[限]*[：:]\s*([\d\.]+)"]:
            match = re.search(pattern, text)
            if match:
                self.data.remaining_years = int(float(match.group(1)))
                break

    def _find_column_index(self, headers: List[str], keywords: List[str]) -> Optional[int]:
        """查找包含关键词的列索引"""
        headers_lower = [h.lower() for h in headers]
        for i, header in enumerate(headers_lower):
            for kw in keywords:
                if kw.lower() in header:
                    return i
        return None

    def _match_project_name(self, row: List[str], projects: Dict[str, HotelProject]) -> Optional[str]:
        """匹配行中的项目名称"""
        for cell in row:
            for name in projects.keys():
                if name in cell:
                    return name
        return None

    def _parse_numeric(self, value: str) -> float:
        """解析数值"""
        if not value:
            return 0.0

        # 清理字符串
        cleaned = str(value).replace(",", "").replace("万", "").replace("元", "").replace("%", "").strip()

        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _parse_rate(self, value: str) -> float:
        """解析比率（处理%号）"""
        num = self._parse_numeric(value)
        if num > 1:  # 如果是百分比数值（如75表示75%）
            return num / 100
        return num

    def generate_parameter_inventory(self) -> Dict[str, Any]:
        """
        生成参数清单（含来源分类）
        列出所有已提取的字段，标注来源分类（招募/行业/假设）
        """
        inventory = {
            "total_extracted": 0,
            "by_source": {
                SourceCategory.PROSPECTUS.value: [],
                SourceCategory.INDUSTRY.value: [],
                SourceCategory.ASSUMPTION.value: [],
            },
            "by_tier": {},
            "missing_required": [],
        }

        checklist = generate_extraction_checklist()

        extracted_names = set()
        for proj in self.data.projects:
            if proj.adr > 0:
                extracted_names.add("adr_2025")
            if proj.occupancy_rate > 0:
                extracted_names.add("occupancy_rate_2025")
            if proj.room_count > 0:
                extracted_names.add("total_rooms")
            if proj.room_revenue > 0:
                extracted_names.add("room_revenue")
            if proj.fb_revenue > 0:
                extracted_names.add("fb_revenue")
            if proj.other_revenue > 0:
                extracted_names.add("other_revenue")
            if proj.ota_revenue > 0:
                extracted_names.add("ota_revenue")
            if proj.total_operating_expense > 0:
                extracted_names.add("total_operating_expense")
            if proj.capex > 0:
                extracted_names.add("capex_year1")
            if proj.commercial_rent > 0:
                extracted_names.add("commercial_rental")
        if self.data.discount_rate > 0:
            extracted_names.add("discount_rate")

        for tmpl in HOTEL_REIT_TEMPLATE:
            entry = {
                "name": tmpl.name,
                "display_name": tmpl.display_name,
                "tier": tmpl.tier.value,
                "source_category": tmpl.source_category.value,
                "extracted": tmpl.name in extracted_names,
                "unit": tmpl.unit,
            }

            source_key = tmpl.source_category.value
            inventory["by_source"][source_key].append(entry)

            tier_key = tmpl.tier.value
            if tier_key not in inventory["by_tier"]:
                inventory["by_tier"][tier_key] = []
            inventory["by_tier"][tier_key].append(entry)

            if entry["extracted"]:
                inventory["total_extracted"] += 1
            elif tmpl.required:
                inventory["missing_required"].append(tmpl.display_name)

        return inventory

    def extract_with_template(self, doc: ParsedDocument) -> Dict[str, Any]:
        """使用完整模板进行提取（增强版）"""
        base_result = self.extract(doc)

        all_patterns = get_all_regex_patterns()
        for field_name, patterns in all_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, doc.text, re.IGNORECASE)
                for match in matches:
                    pass  # Template-driven extraction placeholder

        historical_data = self._extract_historical_data(doc)
        inventory = self.generate_parameter_inventory()

        return {
            "extraction_data": base_result,
            "historical_data": historical_data,
            "parameter_inventory": inventory,
        }

    def _extract_historical_data(self, doc: ParsedDocument) -> Dict[str, Any]:
        """提取历史多年数据（2023/2024/2025）"""
        historical = {"years": [2023, 2024, 2025], "projects": {}}

        year_patterns = {
            2023: [r"2023[年度]*", r"FY2023"],
            2024: [r"2024[年度]*", r"FY2024"],
            2025: [r"2025[年度]*", r"FY2025"],
        }

        for table in doc.tables:
            header_str = " ".join(table.headers)
            has_years = any(
                any(re.search(p, header_str) for p in patterns)
                for patterns in year_patterns.values()
            )
            if has_years and any(kw in header_str for kw in
                                 ["收入", "ADR", "入住率", "GOP", "利润"]):
                year_cols = {}
                for i, h in enumerate(table.headers):
                    for year, patterns in year_patterns.items():
                        if any(re.search(p, h) for p in patterns):
                            year_cols[year] = i
                            break

                for row in table.rows:
                    if not row:
                        continue
                    row_label = str(row[0]).strip()
                    for year, col_idx in year_cols.items():
                        if col_idx < len(row):
                            val = self._parse_numeric(str(row[col_idx]))
                            if val > 0:
                                if year not in historical:
                                    historical[year] = {}
                                historical[year][row_label] = val

        return historical

    def generate_report(self) -> str:
        """生成提取结果报告"""
        lines = ["# 华住REIT参数提取报告\n"]

        lines.append(f"## 全局参数")
        lines.append(f"- 折现率: {self.data.discount_rate:.2%}")
        lines.append(f"- 剩余年限: {self.data.remaining_years} 年")
        lines.append(f"- 项目数量: {len(self.data.projects)}\n")

        lines.append(f"## 各项目数据\n")

        for i, proj in enumerate(self.data.projects, 1):
            lines.append(f"### 项目{i}: {proj.name}")
            lines.append(f"**酒店部分**")
            lines.append(f"- 平均房价(ADR): {proj.adr:.2f} 元/晚")
            lines.append(f"- 入住率: {proj.occupancy_rate:.1%}")
            lines.append(f"- 客房数: {proj.room_count} 间")
            lines.append(f"- 客房收入: {proj.room_revenue:.2f} 万元")
            lines.append(f"- OTA收入: {proj.ota_revenue:.2f} 万元")
            lines.append(f"- 餐饮收入: {proj.fb_revenue:.2f} 万元")
            lines.append(f"- 其他收入: {proj.other_revenue:.2f} 万元")
            lines.append(f"- 酒店总收入: {proj.calculate_hotel_revenue():.2f} 万元")
            lines.append(f"- 运营费用: {proj.total_operating_expense:.2f} 万元")
            lines.append(f"- GOP: {proj.calculate_gop():.2f} 万元\n")

            lines.append(f"**商业部分**")
            lines.append(f"- 商业租金: {proj.commercial_rent:.2f} 万元")
            lines.append(f"- 商业物业费: {proj.commercial_management_fee:.2f} 万元")
            lines.append(f"- 商业净收益: {proj.calculate_commercial_net():.2f} 万元\n")

            lines.append(f"**其他费用**")
            lines.append(f"- 物业费: {proj.property_fee:.2f} 万元")
            lines.append(f"- 保险费: {proj.insurance:.2f} 万元")
            lines.append(f"- 房产税: {proj.property_tax:.2f} 万元")
            lines.append(f"- 土地使用税: {proj.land_use_tax:.2f} 万元")
            lines.append(f"- 管理费: {proj.management_fee:.2f} 万元")
            lines.append(f"- 其他费用合计: {proj.calculate_other_expenses():.2f} 万元")
            lines.append(f"- 资本性支出: {proj.capex:.2f} 万元\n")

            lines.append(f"**年净收益(NOI/CF)**")
            lines.append(f"- **{proj.calculate_noicf():.2f} 万元**\n")

        # 汇总
        agg = self.data.get_aggregate_data()
        lines.append(f"## 汇总数据")
        lines.append(f"- 项目数量: {agg['project_count']} 个")
        lines.append(f"- 客房收入合计: {agg['total_room_revenue']:.2f} 万元")
        lines.append(f"- OTA收入合计: {agg['total_ota_revenue']:.2f} 万元")
        lines.append(f"- 餐饮收入合计: {agg['total_fb_revenue']:.2f} 万元")
        lines.append(f"- 运营费用合计: {agg['total_operating_expense']:.2f} 万元")
        lines.append(f"- **年净收益合计: {agg['total_noicf']:.2f} 万元**")
        lines.append(f"- 加权平均ADR: {agg['weighted_avg_adr']:.2f} 元")
        lines.append(f"- 加权平均入住率: {agg['weighted_avg_occupancy']:.1%}")

        return "\n".join(lines)
