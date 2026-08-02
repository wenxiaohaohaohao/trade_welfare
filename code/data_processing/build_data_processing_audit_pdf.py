from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import reportlab
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    LongTable,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    TableStyle,
    XPreformatted,
)
from reportlab.platypus.tableofcontents import TableOfContents


PROJECT_ROOT_DEFAULT = Path(__file__).resolve().parents[2]
FONT_REGULAR = Path(r"C:\Windows\Fonts\simsun.ttc")
FONT_BOLD = Path(r"C:\Windows\Fonts\simsun.ttc")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def register_fonts() -> None:
    if not FONT_REGULAR.exists() or not FONT_BOLD.exists():
        raise FileNotFoundError(
            "SimSun font is required at "
            f"{FONT_REGULAR} and {FONT_BOLD}."
        )
    pdfmetrics.registerFont(TTFont("SimSun", str(FONT_REGULAR)))
    pdfmetrics.registerFont(TTFont("SimSun-Bold", str(FONT_BOLD)))
    pdfmetrics.registerFontFamily(
        "SimSun",
        normal="SimSun",
        bold="SimSun-Bold",
        italic="SimSun",
        boldItalic="SimSun-Bold",
    )


def markdown_inline(text: str) -> str:
    escaped = html.escape(text, quote=False)
    escaped = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<link href="\2" color="#1F5A85">\1</link>',
        escaped,
    )
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(
        r"`([^`]+)`",
        r'<font name="SimSun" color="#6E3B12">\1</font>',
        escaped,
    )
    return escaped


def visible_width(text: str) -> int:
    width = 0
    for char in re.sub(r"`|\*\*", "", text):
        width += 1 if ord(char) < 128 else 2
    return max(width, 1)


def split_table_row(line: str) -> list[str]:
    stripped = line.strip().strip("|")
    return [cell.strip() for cell in stripped.split("|")]


def is_table_separator(line: str) -> bool:
    cells = split_table_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def table_widths(rows: list[list[str]], available_width: float) -> list[float]:
    column_count = max(len(row) for row in rows)
    maxima = []
    for column in range(column_count):
        cell_widths = [
            min(visible_width(row[column]), 42)
            for row in rows
            if column < len(row)
        ]
        maxima.append(max(max(cell_widths or [6]), 6))
    total = sum(maxima)
    widths = [available_width * value / total for value in maxima]
    minimum = 18 * mm
    if column_count <= 4:
        widths = [max(width, minimum) for width in widths]
        scale = available_width / sum(widths)
        widths = [width * scale for width in widths]
    return widths


class ResearchDocTemplate(BaseDocTemplate):
    def __init__(
        self,
        filename: str,
        *,
        document_title: str,
        version: str,
        **kwargs,
    ):
        super().__init__(filename, **kwargs)
        self.document_title = document_title
        self.version_label = version
        self._heading_counter = 0
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="normal",
        )
        self.addPageTemplates(
            PageTemplate(
                id="audit",
                frames=[frame],
                onPage=self._draw_header_footer,
            )
        )

    def beforeDocument(self) -> None:
        self._heading_counter = 0

    def _draw_header_footer(self, canvas, doc) -> None:
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#B7C4CC"))
        canvas.setLineWidth(0.4)
        canvas.line(
            self.leftMargin,
            A4[1] - 16 * mm,
            A4[0] - self.rightMargin,
            A4[1] - 16 * mm,
        )
        canvas.setFont("SimSun", 7.5)
        canvas.setFillColor(colors.HexColor("#52636D"))
        canvas.drawString(
            self.leftMargin,
            A4[1] - 12.5 * mm,
            self.document_title[:44],
        )
        canvas.drawRightString(
            A4[0] - self.rightMargin,
            A4[1] - 12.5 * mm,
            "内部审计材料",
        )
        canvas.line(
            self.leftMargin,
            14 * mm,
            A4[0] - self.rightMargin,
            14 * mm,
        )
        canvas.drawString(self.leftMargin, 9.5 * mm, self.version_label)
        canvas.drawRightString(
            A4[0] - self.rightMargin,
            9.5 * mm,
            f"第 {doc.page} 页",
        )
        canvas.restoreState()

    def afterFlowable(self, flowable) -> None:
        if isinstance(flowable, Paragraph):
            style_name = flowable.style.name
            if style_name in {"H1", "H2", "H3"}:
                level = {"H1": 0, "H2": 1, "H3": 2}[style_name]
                text = flowable.getPlainText()
                bookmark = f"heading-{self._heading_counter}"
                self._heading_counter += 1
                self.canv.bookmarkPage(bookmark)
                self.canv.addOutlineEntry(text, bookmark, level=level, closed=False)
                self.notify("TOCEntry", (level, text, self.page, bookmark))


def build_styles():
    base = getSampleStyleSheet()
    styles = {
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=base["Title"],
            fontName="SimSun-Bold",
            fontSize=24,
            leading=34,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#17384C"),
            spaceAfter=14,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle",
            fontName="SimSun",
            fontSize=11,
            leading=18,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#52636D"),
        ),
        "h1": ParagraphStyle(
            "H1",
            fontName="SimSun-Bold",
            fontSize=16,
            leading=22,
            textColor=colors.HexColor("#17384C"),
            spaceBefore=12,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2",
            fontName="SimSun-Bold",
            fontSize=13,
            leading=18,
            textColor=colors.HexColor("#1F5A85"),
            spaceBefore=10,
            spaceAfter=6,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "H3",
            fontName="SimSun-Bold",
            fontSize=10.5,
            leading=15,
            textColor=colors.HexColor("#2F657D"),
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body",
            fontName="SimSun",
            fontSize=8.7,
            leading=14,
            alignment=TA_JUSTIFY,
            textColor=colors.HexColor("#1F2A30"),
            spaceAfter=5,
            splitLongWords=True,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            fontName="SimSun",
            fontSize=8.5,
            leading=13,
            leftIndent=13,
            firstLineIndent=-8,
            bulletIndent=4,
            spaceAfter=3,
        ),
        "number": ParagraphStyle(
            "Number",
            fontName="SimSun",
            fontSize=8.5,
            leading=13,
            leftIndent=15,
            firstLineIndent=-10,
            spaceAfter=3,
        ),
        "code": ParagraphStyle(
            "Code",
            fontName="SimSun",
            fontSize=7.1,
            leading=10,
            leftIndent=6,
            rightIndent=6,
            backColor=colors.HexColor("#F2F5F7"),
            borderColor=colors.HexColor("#CBD5DB"),
            borderWidth=0.4,
            borderPadding=6,
            spaceBefore=3,
            spaceAfter=7,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            fontName="SimSun-Bold",
            fontSize=6.8,
            leading=9,
            textColor=colors.white,
            alignment=TA_LEFT,
        ),
        "table_cell": ParagraphStyle(
            "TableCell",
            fontName="SimSun",
            fontSize=6.5,
            leading=9,
            textColor=colors.HexColor("#1F2A30"),
            alignment=TA_LEFT,
        ),
        "toc_title": ParagraphStyle(
            "TOCTitle",
            fontName="SimSun-Bold",
            fontSize=18,
            leading=24,
            textColor=colors.HexColor("#17384C"),
            spaceAfter=12,
        ),
    }
    return styles


def extract_metadata(lines: list[str]) -> tuple[str, str]:
    title = next(
        (line[2:].strip() for line in lines if line.startswith("# ")),
        "数据处理审计材料",
    )
    version = "unversioned"
    for line in lines:
        if line.startswith("- Version Label:"):
            version = line.split(":", 1)[1].strip().strip("`")
            break
    return title, version


def parse_markdown(
    lines: list[str],
    *,
    styles,
    available_width: float,
) -> list:
    story = []
    paragraph_buffer: list[str] = []
    code_buffer: list[str] = []
    in_code = False
    skipped_first_h1 = False

    def flush_paragraph() -> None:
        nonlocal paragraph_buffer
        if paragraph_buffer:
            text = " ".join(part.strip() for part in paragraph_buffer).strip()
            if text:
                story.append(Paragraph(markdown_inline(text), styles["body"]))
            paragraph_buffer = []

    index = 0
    while index < len(lines):
        line = lines[index].rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            if in_code:
                story.append(
                    XPreformatted(
                        html.escape("\n".join(code_buffer)),
                        styles["code"],
                    )
                )
                code_buffer = []
                in_code = False
            else:
                in_code = True
            index += 1
            continue

        if in_code:
            code_buffer.append(line)
            index += 1
            continue

        if not stripped:
            flush_paragraph()
            index += 1
            continue

        if stripped == "<!-- PAGEBREAK -->":
            flush_paragraph()
            story.append(PageBreak())
            index += 1
            continue

        if line.startswith("# "):
            flush_paragraph()
            if not skipped_first_h1:
                skipped_first_h1 = True
            else:
                story.append(Paragraph(markdown_inline(line[2:]), styles["h1"]))
            index += 1
            continue
        if line.startswith("## "):
            flush_paragraph()
            story.append(Paragraph(markdown_inline(line[3:]), styles["h1"]))
            index += 1
            continue
        if line.startswith("### "):
            flush_paragraph()
            story.append(Paragraph(markdown_inline(line[4:]), styles["h2"]))
            index += 1
            continue
        if line.startswith("#### "):
            flush_paragraph()
            story.append(Paragraph(markdown_inline(line[5:]), styles["h3"]))
            index += 1
            continue

        if stripped.startswith("|") and index + 1 < len(lines):
            next_line = lines[index + 1].strip()
            if next_line.startswith("|") and is_table_separator(next_line):
                flush_paragraph()
                raw_rows = [split_table_row(line)]
                index += 2
                while index < len(lines) and lines[index].strip().startswith("|"):
                    raw_rows.append(split_table_row(lines[index]))
                    index += 1
                column_count = max(len(row) for row in raw_rows)
                normalized = [
                    row + [""] * (column_count - len(row))
                    for row in raw_rows
                ]
                pdf_rows = []
                for row_index, row in enumerate(normalized):
                    style = (
                        styles["table_header"]
                        if row_index == 0
                        else styles["table_cell"]
                    )
                    pdf_rows.append(
                        [Paragraph(markdown_inline(cell), style) for cell in row]
                    )
                table = LongTable(
                    pdf_rows,
                    colWidths=table_widths(normalized, available_width),
                    repeatRows=1,
                    hAlign="LEFT",
                    splitByRow=True,
                )
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#315E73")),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C5CC")),
                            ("LEFTPADDING", (0, 0), (-1, -1), 3),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                            ("TOPPADDING", (0, 0), (-1, -1), 3),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                            (
                                "ROWBACKGROUNDS",
                                (0, 1),
                                (-1, -1),
                                [colors.white, colors.HexColor("#F5F7F8")],
                            ),
                        ]
                    )
                )
                story.extend([table, Spacer(1, 6)])
                continue

        bullet_match = re.match(r"^[-*]\s+(.*)$", stripped)
        if bullet_match:
            flush_paragraph()
            story.append(
                Paragraph(
                    f"• {markdown_inline(bullet_match.group(1))}",
                    styles["bullet"],
                )
            )
            index += 1
            continue

        number_match = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if number_match:
            flush_paragraph()
            story.append(
                Paragraph(
                    f"{number_match.group(1)}. {markdown_inline(number_match.group(2))}",
                    styles["number"],
                )
            )
            index += 1
            continue

        paragraph_buffer.append(stripped)
        index += 1

    flush_paragraph()
    if in_code and code_buffer:
        story.append(
            XPreformatted(html.escape("\n".join(code_buffer)), styles["code"])
        )
    return story


def build_pdf(source: Path, output: Path, *, overwrite: bool) -> dict:
    if not source.exists():
        raise FileNotFoundError(source)
    if output.exists() and not overwrite:
        raise FileExistsError(f"{output} exists; pass --overwrite to replace it.")

    register_fonts()
    text = source.read_text(encoding="utf-8")
    lines = text.splitlines()
    title, version = extract_metadata(lines)
    styles = build_styles()

    output.parent.mkdir(parents=True, exist_ok=True)
    document = ResearchDocTemplate(
        str(output),
        document_title=title,
        version=version,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=20 * mm,
        title=title,
        author="Connector Economies research project",
        subject="Internal data processing audit and variable construction guidance",
    )

    story = [
        Spacer(1, 38 * mm),
        Paragraph(markdown_inline(title), styles["cover_title"]),
        Spacer(1, 8 * mm),
        Paragraph("内部严格审查材料", styles["cover_subtitle"]),
        Spacer(1, 3 * mm),
        Paragraph(version, styles["cover_subtitle"]),
        Spacer(1, 3 * mm),
        Paragraph(
            f"由 {source.as_posix()} 可重复生成",
            styles["cover_subtitle"],
        ),
        Spacer(1, 50 * mm),
        Paragraph(
            "用途：合作者复核数据来源、处理规则、变量定义、验证结果和解释边界。",
            styles["cover_subtitle"],
        ),
        PageBreak(),
        Paragraph("目录", styles["toc_title"]),
    ]

    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(
            "TOC1",
            fontName="SimSun",
            fontSize=9,
            leading=14,
            leftIndent=0,
            firstLineIndent=0,
            textColor=colors.HexColor("#17384C"),
        ),
        ParagraphStyle(
            "TOC2",
            fontName="SimSun",
            fontSize=8,
            leading=12,
            leftIndent=12,
            firstLineIndent=0,
            textColor=colors.HexColor("#315E73"),
        ),
        ParagraphStyle(
            "TOC3",
            fontName="SimSun",
            fontSize=7.5,
            leading=11,
            leftIndent=24,
            firstLineIndent=0,
        ),
    ]
    story.extend([toc, PageBreak()])
    story.extend(parse_markdown(lines, styles=styles, available_width=document.width))
    document.multiBuild(story)

    reader = PdfReader(str(output))
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    if len(reader.pages) < 2:
        raise RuntimeError("PDF unexpectedly has fewer than two pages.")
    if title not in extracted:
        raise RuntimeError("PDF text extraction did not recover the document title.")
    if len(extracted) < max(5000, int(len(text) * 0.35)):
        raise RuntimeError(
            "PDF extracted text is unexpectedly short; generation may be incomplete."
        )

    summary = {
        "validation_status": "PASS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_path": source.as_posix(),
        "source_sha256": sha256_file(source),
        "source_character_count": len(text),
        "output_path": output.as_posix(),
        "output_sha256": sha256_file(output),
        "output_size_bytes": output.stat().st_size,
        "page_count": len(reader.pages),
        "extracted_character_count": len(extracted),
        "title_check_pass": title in extracted,
        "reportlab_version": reportlab.Version,
        "font_regular": str(FONT_REGULAR),
        "font_bold": str(FONT_BOLD),
        "rendering_review_status": "PENDING_PNG_REVIEW",
    }
    summary_path = output.with_name(f"{output.stem}_build_summary.json")
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a styled, searchable PDF from the project audit Markdown."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT_DEFAULT,
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("docs/data_processing_audit_trail.md"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/pdf/data_processing_audit_trail.pdf"),
    )
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.project_root.resolve()
    source = args.source if args.source.is_absolute() else root / args.source
    output = args.output if args.output.is_absolute() else root / args.output
    summary = build_pdf(source.resolve(), output.resolve(), overwrite=args.overwrite)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
