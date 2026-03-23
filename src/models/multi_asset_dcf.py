"""
综合体多业态DCF模型

自动识别项目中的多种业态（mall/hotel/industrial/logistics），
分别调用对应业态的DCF模型计算，最后合并输出统一结果。

使用场景:
    - 华润成都万象城（mall + hotel）
    - 未来可能的多业态综合体项目

数据流:
    extracted_data (包含projects数组，每个元素有asset_type)
        ↓
    按asset_type分组
        ↓
    MallDCFModel / HotelDCFModel / ... 分别计算
        ↓
    合并为统一的 DCFResult
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

from .base_dcf import BaseDCF
from .dcf_result import DCFResult, ProjectResult
from .mall.dcf import MallDCFModel
from .hotel.dcf import HotelDCFModel


# 业态模型注册表
ASSET_TYPE_REGISTRY: Dict[str, Type[BaseDCF]] = {
    "mall": MallDCFModel,
    "hotel": HotelDCFModel,
    # 未来扩展:
    # "industrial": IndustrialDCFModel,
    # "logistics": LogisticsDCFModel,
}


class MultiAssetDCFModel(BaseDCF):
    """
    多业态综合体DCF模型。

    从数据文件中自动识别包含的业态，分别计算后合并结果。
    对外暴露统一的 BaseDCF 接口（calculate/adjust）。
    """

    def __init__(
        self,
        extracted_data: Dict[str, Any],
        detailed_data: Optional[Dict[str, Any]] = None,
        fixed_growth: Optional[float] = None,
        noi_multiplier: float = 1.0,
    ):
        self.data = extracted_data
        self.detailed_data = detailed_data
        self.fixed_growth = fixed_growth
        self.noi_multiplier = noi_multiplier
        self._result: Optional[DCFResult] = None

        # 识别包含的业态
        self.asset_types = self._detect_asset_types()

        # 为每个业态创建子模型
        self.sub_models = self._build_sub_models()

    def _detect_asset_types(self) -> List[str]:
        """从数据文件中检测包含的业态类型"""
        projects = self.data.get("projects", [])
        asset_types = set()
        for proj in projects:
            at = proj.get("asset_type", "")
            if at in ASSET_TYPE_REGISTRY:
                asset_types.add(at)
        return sorted(list(asset_types))

    def _build_sub_models(self) -> Dict[str, BaseDCF]:
        """为每个业态创建对应的DCF模型"""
        models = {}
        for asset_type in self.asset_types:
            model_class = ASSET_TYPE_REGISTRY[asset_type]
            models[asset_type] = model_class(
                extracted_data=self.data,
                detailed_data=self.detailed_data,
                fixed_growth=self.fixed_growth,
                noi_multiplier=self.noi_multiplier,
            )
        return models

    def calculate(self) -> DCFResult:
        """计算所有业态的DCF并合并结果"""
        if self._result is not None:
            return self._result

        # 分别计算各业态（跳过计算失败的）
        sub_results: List[DCFResult] = []
        for asset_type, model in self.sub_models.items():
            try:
                result = model.calculate()
                sub_results.append(result)
            except Exception as e:
                print(f"[WARN] {asset_type} 业态计算失败: {e}")
                continue

        # 合并结果
        self._result = self._merge_results(sub_results)
        return self._result

    def _merge_results(self, sub_results: List[DCFResult]) -> DCFResult:
        """合并多个业态的DCF结果"""
        if not sub_results:
            return DCFResult(
                fund_name=self.data.get("fund_info", {}).get("name", ""),
                asset_type="mixed",
                projects=[],
                total_valuation=0.0,
                total_noi_year1=0.0,
                discount_rate=self._get_discount_rate(),
                implied_cap_rate=0.0,
            )

        # 汇总所有子项目
        all_projects: List[ProjectResult] = []
        total_valuation = 0.0
        total_noi_year1 = 0.0

        for result in sub_results:
            all_projects.extend(result.projects)
            total_valuation += result.total_valuation
            total_noi_year1 += result.total_noi_year1

        # 检查是否有缺失或计算失败的业态（估值为0但招募说明书有估值）
        valuation_breakdown = self.data.get("valuation_results", {}).get("breakdown", {})

        # 按业态汇总计算结果
        asset_type_valuation: Dict[str, float] = {}
        for result in sub_results:
            asset_type_valuation[result.asset_type] = result.total_valuation

        # 如果商业部分计算为0或缺失但招募说明书有数据，添加回退项目
        commercial_val = valuation_breakdown.get("commercial_wan", 0)
        if commercial_val > 0 and asset_type_valuation.get("mall", 0) == 0:
            all_projects.append(ProjectResult(
                name="商业部分（招募说明书估值回退）",
                asset_type="mall",
                valuation=commercial_val,
                base_noi=0,
                base_capex=0,
                remaining_years=self.data.get("valuation_parameters", {}).get("income_period_years", 20),
                discount_rate=self._get_discount_rate(),
                implied_cap_rate=0,
                noi_source="appraisal_fallback",
            ))
            total_valuation += commercial_val

        # 如果酒店部分计算为0或缺失但招募说明书有数据，添加回退项目
        hotel_val = valuation_breakdown.get("hotel_wan", 0)
        if hotel_val > 0 and asset_type_valuation.get("hotel", 0) == 0:
            all_projects.append(ProjectResult(
                name="酒店部分（招募说明书估值回退）",
                asset_type="hotel",
                valuation=hotel_val,
                base_noi=0,
                base_capex=0,
                remaining_years=self.data.get("valuation_parameters", {}).get("income_period_years", 20),
                discount_rate=self._get_discount_rate(),
                implied_cap_rate=0,
                noi_source="appraisal_fallback",
            ))
            total_valuation += hotel_val

        # 计算综合指标
        cap_rate = total_noi_year1 / total_valuation if total_valuation > 0 else 0.0

        # 获取招募说明书总估值（用于对比）
        benchmark_total = self.data.get("valuation_results", {}).get("total_wan", 0.0)

        fund_info = self.data.get("fund_info", {})

        return DCFResult(
            fund_name=fund_info.get("name", ""),
            asset_type="mixed",
            projects=all_projects,
            total_valuation=round(total_valuation, 2),
            total_noi_year1=round(total_noi_year1, 2),
            discount_rate=self._get_discount_rate(),
            implied_cap_rate=round(cap_rate, 4),
            benchmark_valuation=benchmark_total,
            benchmark_diff_pct=(
                (total_valuation - benchmark_total) / benchmark_total
                if benchmark_total > 0
                else 0.0
            ),
            params={
                "discount_rate": self._get_discount_rate(),
                "growth_rate": self.fixed_growth,
                "noi_multiplier": self.noi_multiplier,
                "asset_types": self.asset_types,
            },
        )

    def _get_discount_rate(self) -> float:
        """从数据中获取折现率"""
        return self.data.get("valuation_parameters", {}).get("discount_rate", 0.065)

    def adjust(
        self,
        discount_rate: Optional[float] = None,
        growth_rate: Optional[float] = None,
        noi_multiplier: float = 1.0,
    ) -> "MultiAssetDCFModel":
        """返回调参后的新实例（敏感性分析用）"""
        new = MultiAssetDCFModel(
            extracted_data=self.data,
            detailed_data=self.detailed_data,
            fixed_growth=growth_rate if growth_rate is not None else self.fixed_growth,
            noi_multiplier=noi_multiplier,
        )
        if discount_rate is not None:
            # 更新数据中的折现率，子模型会从这里读取
            new.data = dict(self.data)
            new.data["valuation_parameters"] = dict(
                new.data.get("valuation_parameters", {})
            )
            new.data["valuation_parameters"]["discount_rate"] = discount_rate
            # 重建子模型以应用新折现率
            new.sub_models = new._build_sub_models()
        return new

    def get_sub_result(self, asset_type: str) -> Optional[DCFResult]:
        """获取指定业态的计算结果（用于分业态分析）"""
        if asset_type not in self.sub_models:
            return None
        return self.sub_models[asset_type].calculate()

    @property
    def is_mixed_asset(self) -> bool:
        """是否为多业态综合体"""
        return len(self.asset_types) > 1
