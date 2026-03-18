"""
统一文档解析入口
自动识别文件类型并调用相应解析器
"""

from pathlib import Path
from typing import Optional

from .pdf_parser import PDFParser
from .word_parser import WordParser
from .excel_parser import ExcelParser
from ..core.types import ParsedDocument
from ..core.exceptions import DocumentParseError


class DocumentParser:
    """
    统一文档解析器
    自动根据文件扩展名选择合适的解析器
    """

    def __init__(self):
        self.parsers = {
            "pdf": PDFParser(),
            "word": WordParser(),
            "excel": ExcelParser(),
        }

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
        path = Path(file_path)

        if not path.exists():
            raise DocumentParseError(f"文件不存在: {file_path}")

        # 根据扩展名选择解析器
        ext = path.suffix.lower()

        if ext == ".pdf":
            return self.parsers["pdf"].parse(file_path)
        elif ext in [".docx", ".doc"]:
            return self.parsers["word"].parse(file_path)
        elif ext in [".xlsx", ".xls"]:
            return self.parsers["excel"].parse(file_path)
        else:
            raise DocumentParseError(
                f"不支持的文件格式: {ext}",
                details={"supported_formats": [".pdf", ".docx", ".doc", ".xlsx", ".xls"]}
            )

    def can_parse(self, file_path: str) -> bool:
        """检查是否支持该文件格式"""
        path = Path(file_path)
        return path.suffix.lower() in [".pdf", ".docx", ".doc", ".xlsx", ".xls"]

    def get_supported_formats(self) -> list:
        """获取支持的文件格式列表"""
        return [".pdf", ".docx", ".doc", ".xlsx", ".xls"]
