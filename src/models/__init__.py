"""
REITs DCF建模模块

业态路由:
    from src.models import build_dcf_model
    model = build_dcf_model("hotel", extracted_data, detailed_data)
    result = model.calculate()          # -> DCFResult
    engine = model.run_sensitivity()    # -> SensitivityEngine
    engine.tornado()
    engine.stress_test()

综合体多业态:
    model = build_dcf_model("mixed", extracted_data, detailed_data)
    # 自动识别数据文件中的多个业态并分别计算
"""

from typing import Any, Dict, Optional

from .base_dcf import BaseDCF
from .dcf_result import DCFResult, ProjectResult, CashFlowRow, SensitivityEngine

# 业态模块
from .hotel import HotelDCFModel, GrowthSchedule, HOTEL_PITFALLS
from .mall import MallDCFModel, MALL_PITFALLS
from .industrial import IndustrialDCFModel, INDUSTRIAL_PITFALLS
from .logistics import LogisticsDCFModel, LOGISTICS_PITFALLS

# 多业态综合体
from .multi_asset_dcf import MultiAssetDCFModel


def build_dcf_model(asset_type: str,
                    extracted_data: Dict[str, Any],
                    detailed_data: Optional[Dict[str, Any]] = None,
                    historical_data: Optional[Dict[str, Any]] = None,
                    **kwargs) -> BaseDCF:
    """
    业态路由工厂函数。

    Args:
        asset_type:     "hotel" | "mall" | "industrial" | "logistics" | "mixed"
        extracted_data: 从 data/{fund}/extracted_params.json 加载
        detailed_data:  从 data/{fund}/extracted_params_detailed.json 加载（可选）
        historical_data: 历史财务数据（可选，酒店用于校准税金）
        **kwargs:       传递给具体模型的额外参数

    Returns:
        BaseDCF 子类实例，调用 .calculate() 得到 DCFResult

    Example:
        # 单业态
        model = build_dcf_model("hotel", data, detailed, historical)
        result = model.calculate()
        print(result.summary())

        # 敏感性分析
        engine = model.run_sensitivity()
        print(engine.tornado())

        # 综合体多业态（自动识别）
        model = build_dcf_model("mixed", data, detailed)
        result = model.calculate()  # 包含mall + hotel合并结果
        print(result.summary())

        # 获取分业态明细
        mall_result = model.get_sub_result("mall")
        hotel_result = model.get_sub_result("hotel")
    """
    # 多业态综合体
    if asset_type.lower() in ("mixed", "multi", "complex"):
        return MultiAssetDCFModel(
            extracted_data=extracted_data,
            detailed_data=detailed_data,
            **kwargs
        )

    _registry = {
        "hotel":      HotelDCFModel,
        "mall":       MallDCFModel,
        "industrial": IndustrialDCFModel,
        "logistics":  LogisticsDCFModel,
    }

    cls = _registry.get(asset_type.lower())
    if cls is None:
        raise ValueError(
            f"未知资产类型: '{asset_type}'。"
            f"支持的类型: {list(_registry.keys())} | mixed"
        )

    if asset_type == "hotel":
        return cls(extracted_data, detailed_data, historical_data, **kwargs)
    return cls(extracted_data, detailed_data, **kwargs)


__all__ = [
    "build_dcf_model",
    "BaseDCF",
    "DCFResult",
    "ProjectResult",
    "CashFlowRow",
    "SensitivityEngine",
    "HotelDCFModel",
    "GrowthSchedule",
    "HOTEL_PITFALLS",
    "MallDCFModel",
    "MALL_PITFALLS",
    "IndustrialDCFModel",
    "INDUSTRIAL_PITFALLS",
    "LogisticsDCFModel",
    "LOGISTICS_PITFALLS",
    "MultiAssetDCFModel",
]
