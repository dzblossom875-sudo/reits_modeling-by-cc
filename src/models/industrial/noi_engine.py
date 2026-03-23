"""产业园NOI推导引擎（框架占位）"""

from typing import Any, Dict, Optional


class IndustrialNOIDeriver:
    @classmethod
    def derive(cls, project_detail: Dict[str, Any],
               prospectus_noi: float,
               historical_data: Optional[Dict[str, Any]] = None):
        raise NotImplementedError(
            "IndustrialNOIDeriver.derive() 尚未实现。\n"
            "参考 src/models/hotel/noi_engine.py 的结构完成实现。"
        )
