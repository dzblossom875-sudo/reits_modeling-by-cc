"""
文档解析器基类
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from ..core.types import ParsedDocument
from ..core.exceptions import DocumentParseError


class BaseParser(ABC):
    """文档解析器基类"""

    # 支持的文件扩展名
    SUPPORTED_EXTENSIONS: list = []

    def __init__(self):
        self.file_path: Optional[Path] = None

    def can_parse(self, file_path: str) -> bool:
        """检查是否支持该文件格式"""
        path = Path(file_path)
        return path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def parse(self, file_path: str) -> ParsedDocument:
        """
        解析文档

        Args:
            file_path: 文件路径

        Returns:
            ParsedDocument: 解析后的文档对象

        Raises:
            DocumentParseError: 解析失败时抛出
        """
        self.file_path = Path(file_path)

        if not self.file_path.exists():
            raise DocumentParseError(f"文件不存在: {file_path}")

        if not self.can_parse(file_path):
            raise DocumentParseError(
                f"不支持的文件格式: {self.file_path.suffix}. "
                f"支持的格式: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )

        try:
            return self._do_parse(file_path)
        except Exception as e:
            raise DocumentParseError(
                f"解析文件失败: {file_path}",
                details={"error": str(e)}
            )

    @abstractmethod
    def _do_parse(self, file_path: str) -> ParsedDocument:
        """
        实际解析逻辑，子类必须实现

        Args:
            file_path: 文件路径

        Returns:
            ParsedDocument: 解析后的文档对象
        """
        pass

    def _extract_metadata(self, file_path: Path) -> dict:
        """提取文件元数据"""
        stat = file_path.stat()
        return {
            "file_name": file_path.name,
            "file_size": stat.st_size,
            "file_type": file_path.suffix.lower(),
        }