"""
参数提取器
从解析后的文档中提取REITs估值参数
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from ..core.types import ParsedDocument, ExtractedParam, ExtractedParams, Table
from ..core.config import (
    AssetType, ParamCategory, PARAM_NAME_MAPPINGS,
    DEFAULT_DISCOUNT_RATES, DEFAULT_GROWTH_RATES
)
from ..core.exceptions import ParameterExtractionError


@dataclass
class ExtractionRule:
    """参数提取规则"""
    param_name: str                    # 标准参数名
    patterns: List[str]                # 匹配模式（正则）
    category: ParamCategory            # 参数类别
    value_extractor: str = "default"   # 值提取方式
    unit: Optional[str] = None         # 单位
    required: bool = False             # 是否必需


class ParameterExtractor:
    """参数提取器"""

    # 定义各类资产的必需参数
    REQUIRED_PARAMS = {
        AssetType.INDUSTRIAL: [
            "current_rent", "rent_growth_rate", "occupancy_rate",
            "operating_expense", "discount_rate"
        ],
        AssetType.LOGISTICS: [
            "current_rent", "rent_growth_rate", "occupancy_rate",
            "operating_expense", "discount_rate"
        ],
        AssetType.HOUSING: [
            "current_rent", "rent_growth_rate", "occupancy_rate",
            "operating_expense", "discount_rate"
        ],
        AssetType.INFRASTRUCTURE: [
            "traffic_volume", "toll_rate", "traffic_growth",
            "operating_expense", "discount_rate", "remaining_years"
        ],
        AssetType.HOTEL: [
            "adr", "occupancy_rate", "room_count",
            "fb_revenue_ratio", "operating_expense", "discount_rate"
        ],
    }

    # 提取规则
    EXTRACTION_RULES = [
        # 基础信息
        ExtractionRule("asset_type", [r"项目类型[：:]\s*(.+?)(?:\n|$)"], ParamCategory.BASIC),
        ExtractionRule("total_area", [r"建筑总面积[：:]\s*(\d+[\.\d]*)\s*平方米?"], ParamCategory.BASIC, unit="㎡"),
        ExtractionRule("leasable_area", [r"可租赁面积[：:]\s*(\d+[\.\d]*)\s*平方米?"], ParamCategory.BASIC, unit="㎡"),
        ExtractionRule("remaining_years", [r"剩余年限[：:]\s*(\d+)\s*年"], ParamCategory.BASIC, unit="年"),
        ExtractionRule("location", [r"项目地点[：:]\s*(.+?)(?:\n|$)"], ParamCategory.BASIC),

        # 收入端 - 通用
        ExtractionRule("current_rent", [
            r"当前租金[单价]*[：:]\s*(\d+[\.\d]*)\s*元",
            r"平均租金[：:]\s*(\d+[\.\d]*)\s*元",
            r"租金[单价][：:]\s*(\d+[\.\d]*)\s*元"
        ], ParamCategory.REVENUE, unit="元/㎡/月"),
        ExtractionRule("rent_growth_rate", [
            r"租金增长[率]*[：:]\s*(\d+[\.\d]*)\s*%",
            r"年租金增长[：:]\s*(\d+[\.\d]*)\s*%"
        ], ParamCategory.REVENUE, unit="%"),
        ExtractionRule("occupancy_rate", [
            r"出租率[：:]\s*(\d+[\.\d]*)\s*%",
            r"入住率[：:]\s*(\d+[\.\d]*)\s*%",
            r"满租率[：:]\s*(\d+[\.\d]*)\s*%"
        ], ParamCategory.REVENUE, unit="%"),

        # 收入端 - 酒店特有
        ExtractionRule("adr", [
            r"平均房价[：:]\s*(\d+[\.\d]*)\s*元",
            r"ADR[：:]\s*(\d+[\.\d]*)\s*元"
        ], ParamCategory.REVENUE, unit="元/晚"),
        ExtractionRule("revpar", [
            r"RevPAR[：:]\s*(\d+[\.\d]*)\s*元"
        ], ParamCategory.REVENUE, unit="元"),
        ExtractionRule("room_count", [
            r"客房数[量]*[：:]\s*(\d+)\s*间"
        ], ParamCategory.REVENUE, unit="间"),
        ExtractionRule("fb_revenue_ratio", [
            r"餐饮收入占比[：:]\s*(\d+[\.\d]*)\s*%"
        ], ParamCategory.REVENUE, unit="%"),

        # 收入端 - 基础设施特有
        ExtractionRule("traffic_volume", [
            r"日均车流量[：:]\s*(\d+[\.\d]*)\s*万辆"
        ], ParamCategory.REVENUE, unit="万辆/日"),
        ExtractionRule("toll_rate", [
            r"收费标准[：:]\s*(\d+[\.\d]*)\s*元"
        ], ParamCategory.REVENUE, unit="元"),
        ExtractionRule("traffic_growth", [
            r"车流量增长[率]*[：:]\s*(\d+[\.\d]*)\s*%"
        ], ParamCategory.REVENUE, unit="%"),

        # 成本端
        ExtractionRule("operating_expense", [
            r"运营[成本]*[费用]*[：:]\s*(\d+[\.\d]*)\s*万元",
            r"年运营成本[：:]\s*(\d+[\.\d]*)\s*万元"
        ], ParamCategory.COST, unit="万元/年"),
        ExtractionRule("operating_expense_ratio", [
            r"运营费用率[：:]\s*(\d+[\.\d]*)\s*%"
        ], ParamCategory.COST, unit="%"),
        ExtractionRule("management_fee", [
            r"管理费[用]*[：:]\s*(\d+[\.\d]*)\s*万元"
        ], ParamCategory.COST, unit="万元/年"),
        ExtractionRule("maintenance_cost", [
            r"维护费[用]*[：:]\s*(\d+[\.\d]*)\s*万元",
            r"维修费[用]*[：:]\s*(\d+[\.\d]*)\s*万元"
        ], ParamCategory.COST, unit="万元/年"),
        ExtractionRule("tax_rate", [
            r"税率[：:]\s*(\d+[\.\d]*)\s*%"
        ], ParamCategory.COST, unit="%"),

        # 资本端
        ExtractionRule("discount_rate", [
            r"折现率[：:]\s*(\d+[\.\d]*)\s*%",
            r"WACC[：:]\s*(\d+[\.\d]*)\s*%"
        ], ParamCategory.CAPITAL, unit="%"),
        ExtractionRule("cap_rate", [
            r"资本化率[：:]\s*(\d+[\.\d]*)\s*%"
        ], ParamCategory.CAPITAL, unit="%"),
        ExtractionRule("capex", [
            r"资本性支出[：:]\s*(\d+[\.\d]*)\s*万元"
        ], ParamCategory.CAPITAL, unit="万元/年"),
    ]

    def __init__(self, asset_type: Optional[AssetType] = None):
        self.asset_type = asset_type
        self.rules = {rule.param_name: rule for rule in self.EXTRACTION_RULES}

    def extract(self, doc: ParsedDocument) -> ExtractedParams:
        """
        从文档中提取参数

        Args:
            doc: 解析后的文档

        Returns:
            ExtractedParams: 提取结果
        """
        extracted = {}
        uncertain = {}

        # 1. 从文本中提取参数
        for rule in self.EXTRACTION_RULES:
            result = self._extract_from_text(doc.text, rule)
            if result:
                param, confidence = result
                extracted[rule.param_name] = param

        # 2. 从表格中提取参数
        for table in doc.tables:
            table_params = self._extract_from_table(table)
            for name, param in table_params.items():
                if name not in extracted:
                    extracted[name] = param

        # 3. 识别资产类型
        if not self.asset_type and "asset_type" in extracted:
            self.asset_type = self._identify_asset_type(extracted["asset_type"].value)

        # 4. 确定缺失参数
        missing = self._identify_missing_params(extracted)

        return ExtractedParams(
            extracted=extracted,
            missing=missing,
            uncertain=uncertain,
            asset_type=self.asset_type
        )

    def _extract_from_text(self, text: str, rule: ExtractionRule) -> Optional[Tuple[ExtractedParam, float]]:
        """从文本中提取单个参数"""
        for pattern in rule.patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    value_str = match.group(1)
                    value = self._parse_value(value_str)

                    # 确定来源位置
                    start = max(0, match.start() - 20)
                    end = min(len(text), match.end() + 20)
                    context = text[start:end].replace('\n', ' ')

                    param = ExtractedParam(
                        name=rule.param_name,
                        value=value,
                        original_name=match.group(0).split('：')[0] if '：' in match.group(0) else rule.param_name,
                        source=f"文本匹配: {context[:50]}...",
                        confidence=0.8,
                        category=rule.category,
                        unit=rule.unit
                    )
                    return param, 0.8
                except (ValueError, IndexError):
                    continue
        return None

    def _extract_from_table(self, table: Table) -> Dict[str, ExtractedParam]:
        """从表格中提取参数"""
        params = {}

        for row in table.rows:
            if len(row) < 2:
                continue

            # 第一列通常是参数名
            key = row[0].strip()
            value_str = row[1].strip() if len(row) > 1 else ""

            # 匹配参数名
            standard_name = self._match_param_name(key)
            if standard_name and value_str:
                try:
                    value = self._parse_value(value_str)
                    rule = self.rules.get(standard_name)

                    param = ExtractedParam(
                        name=standard_name,
                        value=value,
                        original_name=key,
                        source=f"表格提取 (Sheet/Page {table.page_number or 'unknown'})",
                        confidence=0.9,
                        category=rule.category if rule else None,
                        unit=rule.unit if rule else None
                    )
                    params[standard_name] = param
                except ValueError:
                    continue

        return params

    def _match_param_name(self, original_name: str) -> Optional[str]:
        """匹配原始参数名到标准参数名"""
        # 直接匹配
        if original_name in PARAM_NAME_MAPPINGS:
            return PARAM_NAME_MAPPINGS[original_name]

        # 模糊匹配
        for cn_name, en_name in PARAM_NAME_MAPPINGS.items():
            if cn_name in original_name or original_name in cn_name:
                return en_name

        return None

    def _parse_value(self, value_str: str) -> Any:
        """解析数值"""
        # 移除单位和其他字符
        value_str = value_str.strip()
        value_str = re.sub(r'[万元平方米间晚辆%/]', '', value_str)
        value_str = value_str.replace(',', '')

        # 尝试解析为数字
        try:
            if '.' in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            return value_str

    def _identify_asset_type(self, type_str: str) -> Optional[AssetType]:
        """识别资产类型"""
        type_mapping = {
            "产业园": AssetType.INDUSTRIAL,
            "工业园区": AssetType.INDUSTRIAL,
            "工业": AssetType.INDUSTRIAL,
            "物流": AssetType.LOGISTICS,
            "仓储": AssetType.LOGISTICS,
            "保障房": AssetType.HOUSING,
            "租赁住房": AssetType.HOUSING,
            "公寓": AssetType.HOUSING,
            "高速": AssetType.INFRASTRUCTURE,
            "公路": AssetType.INFRASTRUCTURE,
            "能源": AssetType.INFRASTRUCTURE,
            "环保": AssetType.INFRASTRUCTURE,
            "污水": AssetType.INFRASTRUCTURE,
            "酒店": AssetType.HOTEL,
            "宾馆": AssetType.HOTEL,
        }

        for keyword, asset_type in type_mapping.items():
            if keyword in type_str:
                return asset_type

        return None

    def _identify_missing_params(self, extracted: Dict[str, ExtractedParam]) -> List[str]:
        """识别缺失的必需参数"""
        if not self.asset_type:
            return []

        required = self.REQUIRED_PARAMS.get(self.asset_type, [])
        missing = [p for p in required if p not in extracted]

        return missing

    def get_param_suggestion(self, param_name: str, asset_type: AssetType) -> Dict[str, Any]:
        """
        获取参数建议值（基于行业数据）

        Args:
            param_name: 参数名
            asset_type: 资产类型

        Returns:
            包含建议值和说明的字典
        """
        # 折现率建议
        if param_name == "discount_rate":
            default_rate = DEFAULT_DISCOUNT_RATES.get(asset_type, 0.075)
            return {
                "suggested_value": default_rate,
                "unit": "%",
                "description": f"基于{asset_type.value}资产类型的行业参考值",
                "range": (default_rate - 0.01, default_rate + 0.01)
            }

        # 增长率建议
        if param_name in ["rent_growth_rate", "adr_growth"]:
            growth_data = DEFAULT_GROWTH_RATES.get(asset_type, {})
            suggested = growth_data.get("rent_growth", 0.025)
            return {
                "suggested_value": suggested,
                "unit": "%",
                "description": f"基于{asset_type.value}资产类型的历史增长数据",
                "range": (0.01, 0.05)
            }

        # 出租率建议
        if param_name == "occupancy_rate":
            growth_data = DEFAULT_GROWTH_RATES.get(asset_type, {})
            suggested = growth_data.get("occupancy", 0.90)
            return {
                "suggested_value": suggested,
                "unit": "%",
                "description": f"基于{asset_type.value}资产类型的市场平均水平",
                "range": (0.80, 0.98)
            }

        return {
            "suggested_value": None,
            "description": "请根据项目实际情况提供该参数"
        }
