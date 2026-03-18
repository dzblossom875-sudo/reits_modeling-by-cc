"""
通用工具函数
"""

from typing import Optional, Any


def format_currency(value: float, unit: str = "万元") -> str:
    """格式化货币金额"""
    if value is None:
        return "N/A"
    return f"{value:,.2f} {unit}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """格式化百分比"""
    if value is None:
        return "N/A"
    return f"{value * 100:.{decimals}f}%"


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """安全除法，避免除零错误"""
    if denominator == 0:
        return default
    return numerator / denominator


def truncate_string(s: str, max_length: int = 100) -> str:
    """截断字符串"""
    if len(s) <= max_length:
        return s
    return s[:max_length] + "..."


def parse_numeric_value(value: Any) -> Optional[float]:
    """解析数值"""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        # 移除常见单位
        value = value.replace(',', '').replace('万元', '').replace('元', '').replace('%', '').strip()
        try:
            return float(value)
        except ValueError:
            return None

    return None