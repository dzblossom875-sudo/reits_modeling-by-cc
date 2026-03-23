"""
数据类型定义（使用dataclass）
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum

from .config import AssetType, ParamCategory, SourceCategory


@dataclass
class Table:
    """提取的表格数据结构"""
    headers: List[str]
    rows: List[List[Any]]
    page_number: Optional[int] = None
    caption: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "headers": self.headers,
            "rows": self.rows,
            "page_number": self.page_number,
            "caption": self.caption,
        }


@dataclass
class ParsedDocument:
    """解析后的文档结构"""
    text: str                              # 全文文本
    tables: List[Table] = field(default_factory=list)  # 提取的表格
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    file_path: str = ""                    # 原始文件路径
    file_type: str = ""                    # 文件类型 (pdf/word/excel)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text[:500] + "..." if len(self.text) > 500 else self.text,
            "tables_count": len(self.tables),
            "metadata": self.metadata,
            "file_path": self.file_path,
            "file_type": self.file_type,
        }


@dataclass
class ExtractedParam:
    """单个提取的参数"""
    name: str                              # 参数名称（标准字段名）
    value: Union[float, str, int]          # 参数值
    original_name: str                     # 原始名称（文档中的表述）
    source: str                            # 来源（页码/章节/表格）
    confidence: float = 1.0                # 置信度（0-1）
    category: Optional[ParamCategory] = None  # 参数类别
    source_category: Optional[SourceCategory] = None  # 来源分类
    unit: Optional[str] = None             # 单位（元/㎡/月、%等）
    notes: Optional[str] = None            # 备注说明
    page_number: Optional[int] = None      # 招募说明书页码

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "original_name": self.original_name,
            "source": self.source,
            "confidence": self.confidence,
            "category": self.category.value if self.category else None,
            "source_category": self.source_category.value if self.source_category else None,
            "unit": self.unit,
            "notes": self.notes,
            "page_number": self.page_number,
        }


@dataclass
class ExtractedParams:
    """参数提取结果"""
    extracted: Dict[str, ExtractedParam] = field(default_factory=dict)  # 成功提取
    missing: List[str] = field(default_factory=list)                   # 缺失参数
    uncertain: Dict[str, ExtractedParam] = field(default_factory=dict) # 不确定
    asset_type: Optional[AssetType] = None                             # 识别的资产类型

    def get_param_value(self, name: str, default: Any = None) -> Any:
        """获取参数值"""
        if name in self.extracted:
            return self.extracted[name].value
        return default

    def to_dict(self) -> Dict[str, Any]:
        return {
            "extracted": {k: v.to_dict() for k, v in self.extracted.items()},
            "missing": self.missing,
            "uncertain": {k: v.to_dict() for k, v in self.uncertain.items()},
            "asset_type": self.asset_type.value if self.asset_type else None,
        }


@dataclass
class ProjectInfo:
    """项目基础信息"""
    name: str = ""                         # 项目名称
    asset_type: Optional[AssetType] = None  # 资产类型
    total_area: Optional[float] = None     # 总建筑面积（㎡）
    leasable_area: Optional[float] = None  # 可租赁面积（㎡）
    remaining_years: Optional[int] = None  # 剩余年限
    location: Optional[str] = None         # 地理位置
    completion_date: Optional[str] = None  # 竣工时间

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "asset_type": self.asset_type.value if self.asset_type else None,
            "total_area": self.total_area,
            "leasable_area": self.leasable_area,
            "remaining_years": self.remaining_years,
            "location": self.location,
            "completion_date": self.completion_date,
        }


@dataclass
class CashFlowItem:
    """单期现金流项目"""
    year: int                              # 年份
    rental_income: float = 0.0            # 租金收入
    other_income: float = 0.0             # 其他收入
    total_income: float = 0.0             # 总收入
    operating_expense: float = 0.0        # 运营费用
    management_fee: float = 0.0           # 管理费用

    # 酒店特有
    room_revenue: float = 0.0             # 客房收入
    fb_revenue: float = 0.0               # 餐饮收入
    other_revenue: float = 0.0            # 其他收入
    adr: float = 0.0                      # 平均房价
    occupancy: float = 0.0                # 入住率
    available_room_nights: float = 0.0    # 可售房晚数

    def calculate_noi(self) -> float:
        """计算净营业收入(NOI)"""
        if self.room_revenue > 0:  # 酒店类
            return self.room_revenue + self.fb_revenue + self.other_revenue - self.operating_expense
        return self.total_income - self.operating_expense - self.management_fee

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "year": self.year,
            "rental_income": self.rental_income,
            "other_income": self.other_income,
            "total_income": self.total_income,
            "operating_expense": self.operating_expense,
            "management_fee": self.management_fee,
            "noi": self.calculate_noi(),
        }
        # 酒店特有字段
        if self.room_revenue > 0:
            result.update({
                "room_revenue": self.room_revenue,
                "fb_revenue": self.fb_revenue,
                "other_revenue": self.other_revenue,
                "adr": self.adr,
                "occupancy": self.occupancy,
            })
        return result


@dataclass
class ValuationResult:
    """估值结果"""
    # 基础信息
    project_info: ProjectInfo
    asset_type: AssetType

    # 估值结果
    npv: float                             # 净现值
    irr: Optional[float] = None           # 内部收益率
    cap_rate: Optional[float] = None      # 资本化率估值
    dcf_value: float = 0.0                # DCF估值

    # 情景信息
    scenario_name: str = "Base Case"      # 情景名称

    # 现金流预测
    cash_flows: List[CashFlowItem] = field(default_factory=list)

    # 关键假设
    assumptions: Dict[str, Any] = field(default_factory=dict)

    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    calculation_notes: List[str] = field(default_factory=list)

    def get_total_noi(self) -> float:
        """获取总NOI"""
        return sum(cf.calculate_noi() for cf in self.cash_flows)

    def get_avg_noi(self) -> float:
        """获取平均年NOI"""
        if not self.cash_flows:
            return 0.0
        return self.get_total_noi() / len(self.cash_flows)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_info": self.project_info.to_dict(),
            "asset_type": self.asset_type.value,
            "scenario_name": self.scenario_name,
            "npv": round(self.npv, 2),
            "irr": round(self.irr, 4) if self.irr else None,
            "cap_rate": round(self.cap_rate, 4) if self.cap_rate else None,
            "dcf_value": round(self.dcf_value, 2),
            "cash_flows": [cf.to_dict() for cf in self.cash_flows],
            "assumptions": self.assumptions,
            "created_at": self.created_at.isoformat(),
            "calculation_notes": self.calculation_notes,
        }


@dataclass
class ScenarioResult:
    """情景对比结果"""
    scenario_name: str
    valuation: ValuationResult
    vs_base_percent: Optional[float] = None  # 相对于基准的变化百分比

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_name": self.scenario_name,
            "valuation": self.valuation.to_dict(),
            "vs_base_percent": round(self.vs_base_percent, 2) if self.vs_base_percent else None,
        }


@dataclass
class RiskItem:
    """风险项"""
    level: str                             # 风险等级: high/medium/low
    category: str                          # 风险类别
    description: str                       # 风险描述
    param_name: Optional[str] = None      # 相关参数
    param_value: Optional[Any] = None     # 参数值
    benchmark: Optional[Any] = None       # 行业基准
    suggestion: Optional[str] = None      # 建议

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "category": self.category,
            "description": self.description,
            "param_name": self.param_name,
            "param_value": self.param_value,
            "benchmark": self.benchmark,
            "suggestion": self.suggestion,
        }


@dataclass
class ValidationIssue:
    """验证问题"""
    severity: str                          # 严重程度: error/warning/info
    param_name: str                        # 参数名称
    message: str                           # 问题描述
    current_value: Optional[Any] = None   # 当前值
    expected_range: Optional[tuple] = None  # 期望范围

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "param_name": self.param_name,
            "message": self.message,
            "current_value": self.current_value,
            "expected_range": self.expected_range,
        }


@dataclass
class SensitivityResult:
    """敏感度分析结果"""
    param_name: str                        # 参数名称
    base_value: float                      # 基准值
    base_npv: float                        # 基准NPV
    variations: List[Dict[str, Any]] = field(default_factory=list)  # 变化结果

    def add_variation(self, variation_pct: float, new_value: float, new_npv: float):
        """添加变化结果"""
        self.variations.append({
            "variation_pct": variation_pct,
            "new_value": new_value,
            "new_npv": new_npv,
            "npv_change": new_npv - self.base_npv,
            "npv_change_pct": (new_npv - self.base_npv) / self.base_npv if self.base_npv != 0 else 0,
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "param_name": self.param_name,
            "base_value": self.base_value,
            "base_npv": self.base_npv,
            "variations": self.variations,
        }