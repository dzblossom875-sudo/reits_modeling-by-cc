"""
Excel文档解析器
支持.xlsx和.xls格式
"""

from pathlib import Path
from typing import List, Optional, Dict, Any

try:
    import pandas as pd
    import openpyxl
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

from .base import BaseParser
from ..core.types import ParsedDocument, Table
from ..core.exceptions import DocumentParseError


class ExcelParser(BaseParser):
    """Excel文档解析器"""

    SUPPORTED_EXTENSIONS = [".xlsx", ".xls"]

    def __init__(self, sheet_name: Optional[str] = None):
        super().__init__()
        self.sheet_name = sheet_name  # 指定工作表名称，None表示读取所有

    def _do_parse(self, file_path: str) -> ParsedDocument:
        """解析Excel文件"""
        if not PANDAS_AVAILABLE:
            raise DocumentParseError(
                "pandas和openpyxl未安装，请运行: pip install pandas openpyxl"
            )

        metadata = self._extract_metadata(Path(file_path))
        text_content = []
        tables = []

        try:
            # 读取Excel文件
            xl_file = pd.ExcelFile(file_path)
            metadata["sheet_names"] = xl_file.sheet_names

            # 确定要读取的工作表
            sheets_to_read = [self.sheet_name] if self.sheet_name else xl_file.sheet_names

            for sheet in sheets_to_read:
                if sheet not in xl_file.sheet_names:
                    continue

                # 读取为DataFrame
                df = pd.read_excel(xl_file, sheet_name=sheet)

                # 添加到文本内容
                text_content.append(f"\n=== Sheet: {sheet} ===\n")
                text_content.append(df.to_string())

                # 转换为Table对象
                table = self._convert_dataframe_to_table(df, sheet)
                if table:
                    tables.append(table)

        except Exception as e:
            raise DocumentParseError(
                f"解析Excel文件失败: {file_path}",
                details={"error": str(e)}
            )

        full_text = "\n".join(text_content)

        return ParsedDocument(
            text=full_text,
            tables=tables,
            metadata=metadata,
            file_path=file_path,
            file_type="excel"
        )

    def _convert_dataframe_to_table(self, df: Any, sheet_name: str) -> Optional[Table]:
        """将DataFrame转换为Table对象"""
        if df.empty:
            return None

        # 清理数据
        df = df.fillna('')  # 将NaN替换为空字符串

        headers = df.columns.tolist()
        rows = df.values.tolist()

        # 转换为字符串
        headers = [str(h) for h in headers]
        rows = [[str(cell) if cell is not None else '' for cell in row] for row in rows]

        return Table(
            headers=headers,
            rows=rows,
            caption=sheet_name
        )

    def parse_to_dataframes(self, file_path: str) -> Dict[str, Any]:
        """
        解析为DataFrame字典（便于直接数据处理）

        Args:
            file_path: 文件路径

        Returns:
            Dict[str, DataFrame]: 工作表名称到DataFrame的映射
        """
        if not PANDAS_AVAILABLE:
            raise DocumentParseError("pandas未安装")

        try:
            xl_file = pd.ExcelFile(file_path)
            result = {}

            for sheet_name in xl_file.sheet_names:
                df = pd.read_excel(xl_file, sheet_name=sheet_name)
                result[sheet_name] = df

            return result
        except Exception as e:
            raise DocumentParseError(
                f"解析Excel失败: {file_path}",
                details={"error": str(e)}
            )
