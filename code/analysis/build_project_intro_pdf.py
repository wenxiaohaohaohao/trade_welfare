from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs" / "project_brief_cn.md"
OUT = ROOT / "output" / "memo" / "ToLongfei.pdf"

FONT_SONG = Path(r"C:\Windows\Fonts\simsun.ttc")
FONT_HEI = Path(r"C:\Windows\Fonts\simhei.ttf")

PAGE_W, PAGE_H = A4
MARGIN_X = 18 * mm
TOP_MARGIN = 16 * mm
BOTTOM_MARGIN = 13 * mm
CONTENT_W = PAGE_W - 2 * MARGIN_X

BODY_SIZE = 8.5
BODY_LEADING = 4.25 * mm
PARA_GAP = 0.8 * mm
HEADING_SIZE = 9.4

BLACK = colors.HexColor("#111111")
GREY = colors.HexColor("#666666")
LIGHT_GREY = colors.HexColor("#b8b8b8")


def parse_markdown():
    lines = SOURCE.read_text(encoding="utf-8").strip().splitlines()
    title = re.sub(r"^#\s*", "", lines[0]).strip()
    sections = []
    current = None
    for raw in lines[1:]:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("## "):
            if current:
                sections.append(current)
            current = {"heading": line[3:].strip(), "body": []}
        elif current:
            current["body"].append(line)
    if current:
        sections.append(current)

    abstract = []
    body_sections = []
    for section in sections:
        if section["heading"].lower() == "abstract" or section["heading"] == "摘要":
            abstract = section["body"]
        else:
            body_sections.append(section)
    return title, abstract, body_sections


def clean_text(text):
    return text.replace("`", "")


def is_ascii_token(token):
    return all(ord(ch) < 128 for ch in token)


def token_font(token, bold=False, italic=False):
    if is_ascii_token(token):
        if bold:
            return "Times-Bold"
        if italic:
            return "Times-Italic"
        return "Times-Roman"
    return "SimHei" if bold else "SimSun"


def token_width(token, size, bold=False, italic=False):
    return pdfmetrics.stringWidth(token, token_font(token, bold=bold, italic=italic), size)


def tokenize_mixed(text):
    tokens = []
    buf = []
    for ch in clean_text(text):
        if ch.isspace():
            if buf:
                tokens.append("".join(buf))
                buf = []
            tokens.append(" ")
        elif ord(ch) < 128:
            buf.append(ch)
        else:
            if buf:
                tokens.append("".join(buf))
                buf = []
            tokens.append(ch)
    if buf:
        tokens.append("".join(buf))
    return tokens


def line_width(tokens, size, bold=False, italic=False):
    return sum(token_width(tok, size, bold=bold, italic=italic) for tok in tokens)


def split_long_token(token, max_width, size, bold=False, italic=False):
    pieces = []
    current = ""
    for ch in token:
        trial = current + ch
        if current and token_width(trial, size, bold=bold, italic=italic) > max_width:
            pieces.append(current)
            current = ch
        else:
            current = trial
    if current:
        pieces.append(current)
    return pieces


def wrap_mixed(text, width, size, first_indent=0, bold=False, italic=False):
    lines = []
    current = []
    max_width = width - first_indent
    for token in tokenize_mixed(text):
        if token == " " and not current:
            continue
        trial = current + [token]
        if line_width(trial, size, bold=bold, italic=italic) <= max_width:
            current = trial
            continue

        if current:
            while current and current[-1] == " ":
                current.pop()
            lines.append(current)
            current = []
            max_width = width

        token = token.lstrip() if token == " " else token
        if not token:
            continue
        if token_width(token, size, bold=bold, italic=italic) <= max_width:
            current = [token]
        else:
            pieces = split_long_token(token, max_width, size, bold=bold, italic=italic)
            for piece in pieces[:-1]:
                lines.append([piece])
                max_width = width
            current = [pieces[-1]]

    if current:
        while current and current[-1] == " ":
            current.pop()
        if current:
            lines.append(current)
    return lines


def draw_tokens(c, tokens, x, y, size, bold=False, italic=False, color=BLACK):
    c.setFillColor(color)
    cursor = x
    for token in tokens:
        font = token_font(token, bold=bold, italic=italic)
        c.setFont(font, size)
        c.drawString(cursor, y, token)
        cursor += token_width(token, size, bold=bold, italic=italic)


def draw_rule(c, y, color=BLACK, width=0.45):
    c.setStrokeColor(color)
    c.setLineWidth(width)
    c.line(MARGIN_X, y, PAGE_W - MARGIN_X, y)


def draw_footer(c, page_num):
    c.setStrokeColor(LIGHT_GREY)
    c.setLineWidth(0.3)
    c.line(MARGIN_X, BOTTOM_MARGIN - 4 * mm, PAGE_W - MARGIN_X, BOTTOM_MARGIN - 4 * mm)
    c.setFillColor(GREY)
    c.setFont("SimSun", 7.5)
    c.drawString(MARGIN_X, BOTTOM_MARGIN - 8.5 * mm, "连接型经济体 JMP 项目")
    c.drawRightString(PAGE_W - MARGIN_X, BOTTOM_MARGIN - 8.5 * mm, str(page_num))


def draw_header(c, page_num, title):
    if page_num == 1:
        return
    c.setFillColor(GREY)
    c.setFont("SimSun", 7.7)
    c.drawString(MARGIN_X, PAGE_H - 12 * mm, title[:86])
    c.drawRightString(PAGE_W - MARGIN_X, PAGE_H - 12 * mm, "合作者讨论稿")
    c.setStrokeColor(LIGHT_GREY)
    c.setLineWidth(0.25)
    c.line(MARGIN_X, PAGE_H - 14.5 * mm, PAGE_W - MARGIN_X, PAGE_H - 14.5 * mm)


class SingleColumnWriter:
    def __init__(self, c, title, y):
        self.c = c
        self.title = title
        self.page_num = 1
        self.y = y

    def new_page(self):
        draw_footer(self.c, self.page_num)
        self.c.showPage()
        self.page_num += 1
        draw_header(self.c, self.page_num, self.title)
        self.y = PAGE_H - 22 * mm

    def ensure_space(self, needed):
        if self.y - needed < BOTTOM_MARGIN:
            self.new_page()

    def draw_heading(self, heading):
        lines = wrap_mixed(heading.upper(), CONTENT_W, HEADING_SIZE, bold=True)
        self.ensure_space(len(lines) * 4.25 * mm + 2.2 * mm)
        for tokens in lines:
            draw_tokens(self.c, tokens, MARGIN_X, self.y, HEADING_SIZE, bold=True)
            self.y -= 4.25 * mm
        self.y -= 1.5 * mm

    def draw_paragraph(self, text, size=BODY_SIZE, leading=BODY_LEADING, first_indent=4.5 * mm, color=BLACK):
        lines = wrap_mixed(text, CONTENT_W, size, first_indent=first_indent)
        for idx, tokens in enumerate(lines):
            self.ensure_space(leading)
            indent = first_indent if idx == 0 else 0
            draw_tokens(self.c, tokens, MARGIN_X + indent, self.y, size, color=color)
            self.y -= leading
        self.y -= PARA_GAP

    def draw_info_line(self, label, value):
        self.ensure_space(4.2 * mm)
        label_text = f"{label}: "
        label_tokens = tokenize_mixed(label_text)
        draw_tokens(self.c, label_tokens, MARGIN_X, self.y, 8.0, bold=True)
        label_w = line_width(label_tokens, 8.0, bold=True)
        value_lines = wrap_mixed(value, CONTENT_W - label_w, 8.0)
        for idx, tokens in enumerate(value_lines):
            x = MARGIN_X + label_w if idx == 0 else MARGIN_X + label_w
            draw_tokens(self.c, tokens, x, self.y, 8.0, color=GREY)
            self.y -= 3.85 * mm
        self.y -= 0.5 * mm

    def finish(self):
        draw_footer(self.c, self.page_num)


def draw_title(c, title):
    y = PAGE_H - TOP_MARGIN
    c.setFont("SimHei", 10.0)
    c.setFillColor(BLACK)
    c.drawString(MARGIN_X, y, "研究说明")
    c.setFont("SimSun", 8.0)
    c.setFillColor(GREY)
    c.drawRightString(PAGE_W - MARGIN_X, y, "合作者讨论稿")
    y -= 4.6 * mm
    draw_rule(c, y, BLACK, 0.45)

    y -= 8.2 * mm
    for tokens in wrap_mixed(title, CONTENT_W, 15.2, bold=True):
        draw_tokens(c, tokens, MARGIN_X, y, 15.2, bold=True)
        y -= 7.0 * mm

    c.setFont("SimSun", 8.1)
    c.setFillColor(GREY)
    c.drawString(MARGIN_X, y - 0.2 * mm, "给龙飞")
    c.setFont("SimSun", 8.0)
    c.drawRightString(PAGE_W - MARGIN_X, y - 0.2 * mm, "July 2026")
    return y - 7.3 * mm


def draw_front_matter(c, y, abstract):
    writer = SingleColumnWriter(c, "", y)
    draw_rule(c, writer.y, BLACK, 0.4)
    writer.y -= 4.4 * mm

    writer.draw_heading("项目信息")
    writer.draw_info_line("英文题目", "Connector Economies and the Hidden Cost of Geoeconomic Fragmentation")
    writer.draw_info_line("研究领域", "国际贸易；全球价值链；跨国生产；地缘经济碎片化")
    writer.draw_info_line("JEL 分类", "F12；F14；F23；F51；F62")
    writer.draw_info_line("关键词", "连接型经济体；供应链重组；贸易绕行；跨国生产；福利成本")

    writer.y -= 1.0 * mm
    writer.draw_heading("摘要")
    for paragraph in abstract:
        writer.draw_paragraph(paragraph, size=8.25, leading=4.25 * mm, first_indent=0)

    writer.y -= 1.0 * mm
    draw_rule(c, writer.y, LIGHT_GREY, 0.35)
    return writer.y - 5.2 * mm


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdfmetrics.registerFont(TTFont("SimSun", str(FONT_SONG)))
    pdfmetrics.registerFont(TTFont("SimHei", str(FONT_HEI)))

    title, abstract, sections = parse_markdown()
    c = canvas.Canvas(str(OUT), pagesize=A4)
    c.setTitle("Connector Economies - ToLongfei")
    c.setAuthor("Connector Economies JMP Project")

    y = draw_title(c, title)
    y = draw_front_matter(c, y, abstract)

    writer = SingleColumnWriter(c, title, y)
    for section in sections:
        writer.draw_heading(section["heading"])
        for paragraph in section["body"]:
            writer.draw_paragraph(paragraph)

    writer.finish()
    c.save()
    print(OUT)


if __name__ == "__main__":
    main()
