"""
PDF文档解析器
使用PyPDF2提取文本和表格
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

from .base import BaseParser
from ..core.types import ParsedDocument, Table
from ..core.exceptions import DocumentParseError


class PDFParser(BaseParser):
    """PDF文档解析器"""

    SUPPORTED_EXTENSIONS = [".pdf"]

    def __init__(self, use_pdfplumber: bool = True):
        super().__init__()
        self.use_pdfplumber = use_pdfplumber and PDFPLUMBER_AVAILABLE

    def _do_parse(self, file_path: str) -> ParsedDocument:
        """解析PDF文件"""
        if self.use_pdfplumber:
            return self._parse_with_pdfplumber(file_path)
        else:
            return self._parse_with_pypdf2(file_path)

    def _parse_with_pdfplumber(self, file_path: str) -> ParsedDocument:
        """使用pdfplumber解析（推荐，支持表格）"""
        if not PDFPLUMBER_AVAILABLE:
            raise DocumentParseError("pdfplumber未安装，请运行: pip install pdfplumber")

        text_content = []
        tables = []
        metadata = self._extract_metadata(Path(file_path))

        with pdfplumber.open(file_path) as pdf:
            metadata["page_count"] = len(pdf.pages)

            for page_num, page in enumerate(pdf.pages, 1):
                # 提取文本
                page_text = page.extract_text()
                if page_text:
                    text_content.append(f"\n--- Page {page_num} ---\n{page_text}")

                # 提取表格
                page_tables = page.extract_tables()
                for table_data in page_tables:
                    if table_data and len(table_data) > 1:
                        table = self._convert_to_table(table_data, page_num)
                        if table:
                            tables.append(table)

        full_text = "\n".join(text_content)

        return ParsedDocument(
            text=full_text,
            tables=tables,
            metadata=metadata,
            file_path=file_path,
            file_type="pdf"
        )

    def _parse_with_pypdf2(self, file_path: str) -> ParsedDocument:
        """使用PyPDF2解析（备用方案）"""
        if not PYPDF2_AVAILABLE:
            raise DocumentParseError("PyPDF2未安装，请运行: pip install PyPDF2")

        text_content = []
        metadata = self._extract_metadata(Path(file_path))

        with open(file_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            metadata["page_count"] = len(pdf_reader.pages)

            for page_num, page in enumerate(pdf_reader.pages, 1):
                text = page.extract_text()
                if text:
                    text_content.append(f"\n--- Page {page_num} ---\n{text}")

        full_text = "\n".join(text_content)

        return ParsedDocument(
            text=full_text,
            tables=[],  # PyPDF2不支持表格提取
            metadata=metadata,
            file_path=file_path,
            file_type="pdf"
        )

    def _convert_to_table(self, table_data: List[List[Any]], page_num: int) -> Optional[Table]:
        """将原始表格数据转换为Table对象"""
        if not table_data or len(table_data) < 2:
            return None

        # 第一行作为表头
        headers = [str(cell).strip() if cell else "" for cell in table_data[0]]
        rows = []

        for row_data in table_data[1:]:
            row = [str(cell).strip() if cell else "" for cell in row_data]
            if any(row):  # 跳过空行
                rows.append(row)

        return Table(
            headers=headers,
            rows=rows,
            page_number=page_num
        )

    def extract_sections(self, text: str) -> Dict[str, str]:
        """
        提取文档章节

        Args:
            text: 文档全文

        Returns:
            Dict[str, str]: 章节名称到内容的映射
        """
        sections = {}

        # 常见的章节标题模式
        section_patterns = [
            r'第[一二三四五六七八九十]+章\s*(.+?)(?=第[一二三四五六七八九十]+章|$)',
            r'第\d+章\s*(.+?)(?=第\d+章|$)',
            r'\d+\.\d+\s+(.+?)(?=\d+\.\d+|$)',
        ]

        for pattern in section_patterns:
            matches = re.finditer(pattern, text, re.DOTALL)
            for match in matches:
                section_title = match.group(0).split('\n')[0].strip()
                section_content = match.group(0)
                sections[section_title] = section_content

        return sections
