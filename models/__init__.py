"""
REITs估值模型模块

包含：
- base.py: 模型基类和通用工具
- factory.py: 模型工厂，根据业态选择对应模型
- specialized/: 各类专用模型
"""

from .base import BaseDCFModel, DCFResult, ProjectConfig
from .factory import ModelFactory

__all__ = ['BaseDCFModel', 'DCFResult', 'ProjectConfig', 'ModelFactory']
