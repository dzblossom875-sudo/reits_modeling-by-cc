"""
自定义异常类
"""


class REITsModelingError(Exception):
    """基础异常类"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DocumentParseError(REITsModelingError):
    """文档解析异常"""
    pass


class ParameterExtractionError(REITsModelingError):
    """参数提取异常"""
    pass


class ValidationError(REITsModelingError):
    """参数验证异常"""
    pass


class CalculationError(REITsModelingError):
    """计算异常"""
    pass


class ExportError(REITsModelingError):
    """导出异常"""
    pass


class AssetTypeError(REITsModelingError):
    """资产类型错误"""
    pass