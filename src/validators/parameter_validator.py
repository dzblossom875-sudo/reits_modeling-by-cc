"""
参数验证器
验证参数的合理性和一致性
"""

from typing import Dict, List, Any, Optional

from ..core.types import ValidationIssue, ExtractedParams
from ..models.dcf_model import DCFInputs
from ..core.config import AssetType, INDUSTRY_BENCHMARKS
from ..core.exceptions import ValidationError


class ParameterValidator:
    """参数验证器"""

    def __init__(self):
        pass

    def validate_inputs(self, inputs: DCFInputs) -> List[ValidationIssue]:
        """
        验证DCF输入参数的合理性

        Args:
            inputs: DCF输入参数

        Returns:
            验证问题列表
        """
        issues = []

        # 基础验证
        issues.extend(self._validate_basic(inputs))

        # 收入端验证
        issues.extend(self._validate_revenue(inputs))

        # 成本端验证
        issues.extend(self._validate_cost(inputs))

        # 资本端验证
        issues.extend(self._validate_capital(inputs))

        # 资产类型特化验证
        issues.extend(self._validate_by_asset_type(inputs))

        return issues

    def validate_extracted_params(self, params: ExtractedParams) -> List[ValidationIssue]:
        """
        验证提取的参数

        Args:
            params: 提取的参数

        Returns:
            验证问题列表
        """
        issues = []

        # 检查缺失参数
        for missing_param in params.missing:
            issues.append(ValidationIssue(
                severity="warning",
                param_name=missing_param,
                message=f"参数 '{missing_param}' 缺失，需要从文档中提取或用户补充"
            ))

        # 检查提取参数的有效性
        for name, param in params.extracted.items():
            if param.value is None or param.value == "":
                issues.append(ValidationIssue(
                    severity="error",
                    param_name=name,
                    message=f"参数 '{name}' 提取值为空"
                ))

            # 数值参数检查
            if isinstance(param.value, (int, float)):
                if param.value < 0 and name not in ["growth_rate", "rent_growth_rate"]:
                    issues.append(ValidationIssue(
                        severity="error",
                        param_name=name,
                        message=f"参数 '{name}' 为负数: {param.value}",
                        current_value=param.value
                    ))

        return issues

    def _validate_basic(self, inputs: DCFInputs) -> List[ValidationIssue]:
        """基础信息验证"""
        issues = []

        if inputs.total_area <= 0:
            issues.append(ValidationIssue(
                severity="error",
                param_name="total_area",
                message="总面积必须大于0",
                current_value=inputs.total_area
            ))

        if inputs.remaining_years <= 0:
            issues.append(ValidationIssue(
                severity="error",
                param_name="remaining_years",
                message="剩余年限必须大于0",
                current_value=inputs.remaining_years
            ))

        if inputs.remaining_years > 100:
            issues.append(ValidationIssue(
                severity="warning",
                param_name="remaining_years",
                message=f"剩余年限 {inputs.remaining_years} 年过长，请确认",
                current_value=inputs.remaining_years
            ))

        return issues

    def _validate_revenue(self, inputs: DCFInputs) -> List[ValidationIssue]:
        """收入端验证"""
        issues = []

        # 租金/房价检查
        if inputs.current_rent < 0 and inputs.adr <= 0:
            issues.append(ValidationIssue(
                severity="error",
                param_name="current_rent",
                message="当前租金/房价必须大于等于0",
                current_value=inputs.current_rent
            ))

        # 增长率检查
        if inputs.rent_growth_rate < 0:
            issues.append(ValidationIssue(
                severity="info",
                param_name="rent_growth_rate",
                message="租金增长率为负，表示预期租金下降",
                current_value=inputs.rent_growth_rate
            ))

        if inputs.rent_growth_rate > 0.15:
            issues.append(ValidationIssue(
                severity="warning",
                param_name="rent_growth_rate",
                message=f"租金增长率 {inputs.rent_growth_rate:.2%} 较高，请确认合理性",
                current_value=inputs.rent_growth_rate,
                expected_range=(0, 0.15)
            ))

        # 出租率/入住率检查
        if inputs.occupancy_rate <= 0 or inputs.occupancy_rate > 1:
            issues.append(ValidationIssue(
                severity="error",
                param_name="occupancy_rate",
                message="出租率/入住率必须在0-100%之间",
                current_value=inputs.occupancy_rate,
                expected_range=(0, 1)
            ))

        if inputs.occupancy_rate > 0.98:
            issues.append(ValidationIssue(
                severity="info",
                param_name="occupancy_rate",
                message=f"入住率 {inputs.occupancy_rate:.1%} 接近100%，可能过于乐观",
                current_value=inputs.occupancy_rate
            ))

        return issues

    def _validate_cost(self, inputs: DCFInputs) -> List[ValidationIssue]:
        """成本端验证"""
        issues = []

        # 运营费用率检查
        if inputs.operating_expense_ratio < 0 or inputs.operating_expense_ratio > 1:
            issues.append(ValidationIssue(
                severity="error",
                param_name="operating_expense_ratio",
                message="运营费用率必须在0-100%之间",
                current_value=inputs.operating_expense_ratio,
                expected_range=(0, 1)
            ))

        # 酒店类运营成本通常较高
        if inputs.asset_type == AssetType.HOTEL and inputs.operating_expense_ratio < 0.5:
            issues.append(ValidationIssue(
                severity="warning",
                param_name="operating_expense_ratio",
                message=f"酒店类运营费用率 {inputs.operating_expense_ratio:.1%} 偏低",
                current_value=inputs.operating_expense_ratio,
                expected_range=(0.5, 0.8)
            ))

        return issues

    def _validate_capital(self, inputs: DCFInputs) -> List[ValidationIssue]:
        """资本端验证"""
        issues = []

        # 折现率检查
        if inputs.discount_rate <= 0:
            issues.append(ValidationIssue(
                severity="error",
                param_name="discount_rate",
                message="折现率必须大于0",
                current_value=inputs.discount_rate
            ))

        if inputs.discount_rate > 0.20:
            issues.append(ValidationIssue(
                severity="warning",
                param_name="discount_rate",
                message=f"折现率 {inputs.discount_rate:.2%} 较高，请确认",
                current_value=inputs.discount_rate,
                expected_range=(0.05, 0.20)
            ))

        # 资本化率与折现率关系检查
        if inputs.cap_rate and inputs.cap_rate > 0:
            if inputs.cap_rate > inputs.discount_rate:
                issues.append(ValidationIssue(
                    severity="warning",
                    param_name="cap_rate",
                    message=f"资本化率({inputs.cap_rate:.2%})高于折现率({inputs.discount_rate:.2%})，可能导致估值倒挂",
                    current_value=inputs.cap_rate
                ))

        return issues

    def _validate_by_asset_type(self, inputs: DCFInputs) -> List[ValidationIssue]:
        """根据资产类型进行特化验证"""
        issues = []
        benchmarks = INDUSTRY_BENCHMARKS.get(inputs.asset_type, {})

        # 租金范围验证
        if inputs.current_rent > 0:
            rent_range = benchmarks.get("rent_range")
            if rent_range and (inputs.current_rent < rent_range[0] or inputs.current_rent > rent_range[1]):
                issues.append(ValidationIssue(
                    severity="info",
                    param_name="current_rent",
                    message=f"租金 {inputs.current_rent} 超出行业常见范围 {rent_range}",
                    current_value=inputs.current_rent,
                    expected_range=rent_range
                ))

        # 出租率范围验证
        occ_range = benchmarks.get("occupancy_range")
        if occ_range and inputs.occupancy_rate > 0:
            if inputs.occupancy_rate < occ_range[0]:
                issues.append(ValidationIssue(
                    severity="warning",
                    param_name="occupancy_rate",
                    message=f"出租率 {inputs.occupancy_rate:.1%} 低于行业下限 {occ_range[0]:.0%}",
                    current_value=inputs.occupancy_rate,
                    expected_range=occ_range
                ))

        return issues

    def check_consistency(self, inputs: DCFInputs) -> List[ValidationIssue]:
        """
        检查参数间的一致性

        Args:
            inputs: DCF输入参数

        Returns:
            一致性问题列表
        """
        issues = []

        # 检查运营费用两种定义的一致性
        if inputs.operating_expense > 0 and inputs.operating_expense_ratio > 0:
            # 如果有固定运营费用和比例两种定义，需要确认一致性
            issues.append(ValidationIssue(
                severity="info",
                param_name="operating_expense",
                message="同时定义了固定运营费用和运营费用率，系统将优先使用固定金额"
            ))

        # 检查资本化率估值与DCF估值的差异
        if inputs.cap_rate and inputs.cap_rate > 0:
            from ..models.dcf_model import DCFModel
            model = DCFModel(inputs)
            result = model.calculate()

            if result.cap_rate and result.dcf_value > 0:
                diff_pct = abs(result.cap_rate - result.dcf_value) / result.dcf_value
                if diff_pct > 0.20:  # 差异超过20%
                    issues.append(ValidationIssue(
                        severity="warning",
                        param_name="valuation",
                        message=f"资本化率估值({result.cap_rate:.0f})与DCF估值({result.dcf_value:.0f})差异超过20%",
                        current_value=f"Cap: {result.cap_rate:.0f}, DCF: {result.dcf_value:.0f}"
                    ))

        return issues