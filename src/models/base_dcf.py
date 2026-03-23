"""
BaseDCF - 所有业态DCF模型的抽象基类

每个业态子类必须实现:
  calculate() -> DCFResult
  adjust(...)  -> BaseDCF   （返回调参后的新实例，不改变原实例）

通过 adjust() 的统一接口，SensitivityEngine 可以对任何业态做敏感性分析，
而不需要知道业态内部细节。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .dcf_result import DCFResult


class BaseDCF(ABC):
    """
    REITs DCF建模抽象基类。

    子类实现规则：
    1. __init__ 接收 extracted_data (Dict) 和可选的覆盖参数
    2. calculate() 返回 DCFResult（缓存结果，重复调用不重算）
    3. adjust() 构造并返回新实例（不修改 self），调参参数：
         discount_rate  : float  折现率
         growth_rate    : float  固定增长率（覆盖分段增长率；None=不覆盖）
         noi_multiplier : float  首年NOI乘数（默认1.0=不变）
    4. recalculate() 清除缓存并重算（用于就地修改后重跑）
    """

    @abstractmethod
    def calculate(self) -> DCFResult:
        """运行DCF计算，返回统一结果对象（可缓存）"""
        ...

    @abstractmethod
    def adjust(self,
               discount_rate: Optional[float] = None,
               growth_rate: Optional[float] = None,
               noi_multiplier: float = 1.0) -> "BaseDCF":
        """
        返回一个调参后的新模型实例。
        不传的参数保持原值。
        """
        ...

    def recalculate(self) -> DCFResult:
        """清除缓存后重算（子类可覆盖）"""
        if hasattr(self, "_result"):
            self._result = None
        return self.calculate()

    def run_sensitivity(self):
        """
        便捷方法：返回绑定到本模型的 SensitivityEngine。

        用法:
            engine = model.run_sensitivity()
            engine.tornado()
            engine.stress_test()
        """
        from .dcf_result import SensitivityEngine
        return SensitivityEngine(self)
