"""
Markdown 转 Word (.docx) 工具模块

使用 markdown -> html -> docx 的转换链路。

依赖: pip install python-docx htmldocx markdown
"""

from pathlib import Path

import markdown
from docx import Document
from htmldocx import HtmlToDocx


def md_to_docx(md_text: str, output_path: str) -> str:
    """
    将 Markdown 文本转换为 Word 文档并保存。

    Args:
        md_text: Markdown 格式的文本内容
        output_path: 输出 .docx 文件路径

    Returns:
        保存的文件路径
    """
    # Markdown -> HTML
    html = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "nl2br", "sane_lists"],
    )

    # HTML -> DOCX
    doc = Document()
    parser = HtmlToDocx()
    parser.add_html_to_document(html, doc)

    # 保存
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out))

    return str(out)
