# -*- coding: utf-8 -*-
"""
export_khoa_hoc.py — Gộp toàn bộ khóa học docs/khoa_hoc/*.md thành 1 file Word (.docx)
có định dạng, theo phong cách của export_docx.py (báo cáo dự án):
- Parse heading, bảng, danh sách, checkbox, blockquote (hộp ghi chú), chữ đậm/nghiêng, inline code
- Mermaid block -> thay bằng ảnh PNG đã render sẵn (hinh1/hinh2/hinh4)
- Trang bìa + mục lục + ngắt trang giữa các buổi

Cách dùng:  python docs/khoa_hoc/export_khoa_hoc.py
Kết quả:    docs/KHOA_HOC_EDGE_AI.docx
"""
import os
import re
import glob
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HERE = os.path.dirname(os.path.abspath(__file__))          # docs/khoa_hoc
DOCS = os.path.dirname(HERE)                                # docs/
OUT_DOCX = os.path.join(DOCS, "KHOA_HOC_EDGE_AI.docx")

# Thứ tự file: README làm phần mở đầu, sau đó các buổi theo tên (buoi00..buoi12 tự sắp đúng)
SESSION_FILES = ["README.md"] + sorted(
    os.path.basename(p) for p in glob.glob(os.path.join(HERE, "buoi*.md"))
)

# Ánh xạ mermaid block -> ảnh PNG (theo thứ tự xuất hiện trong toàn khóa học):
# 1) buoi01 flowchart kiến trúc, 2) buoi05 stateDiagram máy trạng thái
MERMAID_IMAGES = [
    os.path.join(DOCS, "hinh1_kien_truc.png"),
    os.path.join(DOCS, "hinh2_may_trang_thai.png"),
]

BLUE = RGBColor(0x15, 0x65, 0xC0)
DARK = RGBColor(0x21, 0x21, 0x21)
GRAY = RGBColor(0x60, 0x60, 0x60)
CODE_COLOR = RGBColor(0xB3, 0x1B, 0x4E)

INLINE_RE = re.compile(r"(\*\*.+?\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\)|\*[^*\n]+\*)")


def set_vietnamese_font(run, name="Times New Roman"):
    run.font.name = name
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), name)
    rFonts.set(qn("w:hAnsi"), name)
    rFonts.set(qn("w:eastAsia"), name)
    rFonts.set(qn("w:cs"), name)


def shade_par(par, fill):
    pPr = par._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), fill)
    pPr.append(shd)


def add_inline(par, text, base_size=12, color=DARK, font="Times New Roman", italic=False):
    """Thêm text hỗ trợ **đậm**, `inline code`, [link](url) và *nghiêng*."""
    for part in INLINE_RE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = par.add_run(part[2:-2])
            run.bold = True
        elif part.startswith("`") and part.endswith("`") and len(part) > 2:
            run = par.add_run(part[1:-1])
            run.font.size = Pt(max(base_size - 1.5, 8))
            run.font.color.rgb = CODE_COLOR
            set_vietnamese_font(run, "Consolas")
            continue
        elif part.startswith("[") and "](" in part:
            m = re.match(r"\[([^\]]+)\]\([^)]+\)", part)
            run = par.add_run(m.group(1) if m else part)
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            run = par.add_run(part[1:-1])
            run.italic = True
        else:
            run = par.add_run(part)
        run.font.size = Pt(base_size)
        run.font.color.rgb = color
        if italic:
            run.italic = True
        set_vietnamese_font(run, font)


def add_table(doc, rows):
    """Thêm bảng từ các dòng markdown (đã bỏ dòng separator)."""
    rows = [r for r in rows if not re.match(r"^\s*\|[\s\-:|]+\|\s*$", r)]
    if not rows:
        return
    parsed = []
    for r in rows:
        cells = [c.strip() for c in r.strip().strip("|").split("|")]
        parsed.append(cells)
    ncols = max(len(r) for r in parsed)
    table = doc.add_table(rows=len(parsed), cols=ncols)
    table.style = "Table Grid"
    for i, row in enumerate(parsed):
        for j in range(ncols):
            cell = table.cell(i, j)
            text = row[j] if j < len(row) else ""
            # bỏ markdown trong ô: ** đậm, ` code`, link
            text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
            par = cell.paragraphs[0]
            add_inline(par, text, base_size=10.5)
            if i == 0:
                for run in par.runs:
                    run.bold = True
                shd = OxmlElement("w:shd")
                shd.set(qn("w:val"), "clear")
                shd.set(qn("w:fill"), "DCE9F7")
                cell._element.get_or_add_tcPr().append(shd)


def add_code_line(doc, text):
    par = doc.add_paragraph()
    par.paragraph_format.space_after = Pt(0)
    shade_par(par, "F5F5F5")
    run = par.add_run(text if text else " ")
    run.font.name = "Consolas"
    run.font.size = Pt(9)
    run.font.color.rgb = DARK
    set_vietnamese_font(run, "Consolas")


def add_quote_line(doc, text):
    par = doc.add_paragraph()
    par.paragraph_format.left_indent = Cm(0.4)
    par.paragraph_format.space_after = Pt(2)
    shade_par(par, "E3F2FD")
    add_inline(par, text, base_size=11.5, color=RGBColor(0x0D, 0x47, 0xA1))


def add_image(doc, path, caption=None, width_cm=16.0):
    if not os.path.exists(path):
        par = doc.add_paragraph("[Thiếu ảnh: %s]" % path)
        return
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = par.add_run()
    run.add_picture(path, width=Cm(width_cm))
    if caption:
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = cap.add_run(caption)
        run.italic = True
        run.font.size = Pt(10)
        run.font.color.rgb = GRAY
        set_vietnamese_font(run)


def first_h1(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s.startswith("# "):
                return re.sub(r"[#*]", "", s[2:]).strip()
    return os.path.basename(path)


def parse_markdown(doc, md_path, mermaid_counter, is_first_content=False):
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    if not is_first_content:
        doc.add_page_break()

    i, n = 0, len(lines)
    in_table, table_buf = False, []
    in_code, code_is_mermaid = False, False

    def flush_table():
        nonlocal in_table, table_buf
        if table_buf:
            add_table(doc, table_buf)
        in_table, table_buf = False, []

    while i < n:
        line = lines[i]

        # --- code fence / mermaid ---
        if line.strip().startswith("```"):
            if not in_code:
                in_code = True
                code_is_mermaid = "mermaid" in line
                if not code_is_mermaid:
                    i += 1
                    while i < n and not lines[i].strip().startswith("```"):
                        add_code_line(doc, lines[i])
                        i += 1
                    in_code = False
                else:
                    idx = mermaid_counter[0]
                    mermaid_counter[0] += 1
                    if idx < len(MERMAID_IMAGES):
                        add_image(doc, MERMAID_IMAGES[idx])
                    else:
                        i += 1
                        while i < n and not lines[i].strip().startswith("```"):
                            add_code_line(doc, lines[i])
                            i += 1
                    i += 1
                    while i < n and not lines[i].strip().startswith("```"):
                        i += 1
                    in_code = False
            i += 1
            continue

        # --- bảng markdown ---
        if line.strip().startswith("|"):
            table_buf.append(line)
            in_table = True
            i += 1
            continue
        elif in_table:
            flush_table()

        stripped = line.strip()

        # --- caption nghiêng toàn dòng (*Hình ...*) ---
        if re.match(r"^\*[^*]+\*$", stripped):
            cap = doc.add_paragraph()
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = cap.add_run(stripped.strip("*"))
            run.italic = True
            run.font.size = Pt(10)
            run.font.color.rgb = GRAY
            set_vietnamese_font(run)
            i += 1
            continue

        # --- heading ---
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            text = re.sub(r"[#*]", "", m.group(2)).strip()
            if level == 1:
                h = doc.add_heading("", level=1)
                add_inline(h, text, base_size=20, color=BLUE)
                h.alignment = WD_ALIGN_PARAGRAPH.CENTER
                h.paragraph_format.space_before = Pt(6)
                h.paragraph_format.space_after = Pt(12)
            else:
                # ## -> Heading 2, ### -> Heading 3, #### -> Heading 4
                h = doc.add_heading("", level=level)
                size = {2: 15, 3: 13, 4: 12}.get(level, 12)
                add_inline(h, text, base_size=size, color=BLUE)
                h.alignment = WD_ALIGN_PARAGRAPH.LEFT
            i += 1
            continue

        # --- dòng kẻ ngang ---
        if stripped == "---":
            i += 1
            continue

        # --- blockquote (hộp ghi chú) ---
        if stripped.startswith(">"):
            add_quote_line(doc, stripped.lstrip(">").strip())
            i += 1
            continue

        # --- danh sách ---
        indent = len(line) - len(line.lstrip())
        m_chk = re.match(r"^[-*]\s+\[( |x|X)\]\s+(.*)$", stripped)
        m_num = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        m_bul = re.match(r"^[-*]\s+(.*)$", stripped)
        if m_chk:
            par = doc.add_paragraph()
            par.paragraph_format.left_indent = Cm(0.8 if indent >= 2 else 0.5)
            mark = "☑ " if m_chk.group(1).lower() == "x" else "☐ "
            run = par.add_run(mark)
            run.font.size = Pt(12)
            set_vietnamese_font(run)
            add_inline(par, m_chk.group(2))
            i += 1
            continue
        if m_num:
            par = doc.add_paragraph()
            par.paragraph_format.left_indent = Cm(0.9)
            par.paragraph_format.first_line_indent = Cm(-0.5)
            add_inline(par, m_num.group(1) + ". " + m_num.group(2))
            i += 1
            continue
        if m_bul:
            style = "List Bullet 2" if indent >= 2 else "List Bullet"
            try:
                par = doc.add_paragraph(style=style)
            except KeyError:
                par = doc.add_paragraph()
                par.paragraph_format.left_indent = Cm(0.9)
            add_inline(par, m_bul.group(1))
            i += 1
            continue

        # --- dòng trống ---
        if not stripped:
            i += 1
            continue

        # --- paragraph thường ---
        par = doc.add_paragraph()
        par.paragraph_format.space_after = Pt(6)
        par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        add_inline(par, stripped)
        i += 1

    if in_table:
        flush_table()


def add_cover(doc):
    for _ in range(4):
        doc.add_paragraph()
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = par.add_run("KHÓA HỌC")
    run.font.size = Pt(28)
    run.bold = True
    run.font.color.rgb = GRAY
    set_vietnamese_font(run)

    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = par.add_run("XÂY DỰNG KHÓA CỬA THÔNG MINH\nEDGE AI — GIỌNG NÓI + KHUÔN MẶT")
    run.font.size = Pt(26)
    run.bold = True
    run.font.color.rgb = BLUE
    set_vietnamese_font(run)

    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = par.add_run("12 buổi thực hành dành cho học viên mới bắt đầu\nESP32-S3 · TensorFlow Lite Micro · ESP-DL · FreeRTOS")
    run.font.size = Pt(14)
    run.font.color.rgb = DARK
    set_vietnamese_font(run)

    doc.add_paragraph()
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = par.add_run("Tài liệu sinh từ docs/khoa_hoc/ — biên soạn bằng export_khoa_hoc.py")
    run.font.size = Pt(10)
    run.font.color.rgb = GRAY
    run.italic = True
    set_vietnamese_font(run)
    doc.add_page_break()


def add_toc(doc):
    doc.add_heading("MỤC LỤC", level=1)
    for name in SESSION_FILES:
        title = first_h1(os.path.join(HERE, name))
        par = doc.add_paragraph()
        par.paragraph_format.left_indent = Cm(0.4)
        add_inline(par, "•  " + title, base_size=13)
    doc.add_page_break()


def main():
    doc = Document()

    for section in doc.sections:
        section.top_margin = Cm(2.2)
        section.bottom_margin = Cm(2.2)
        section.left_margin = Cm(2.8)
        section.right_margin = Cm(2.4)

    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")

    add_cover(doc)
    add_toc(doc)

    mermaid_counter = [0]
    for idx, name in enumerate(SESSION_FILES):
        parse_markdown(doc, os.path.join(HERE, name), mermaid_counter,
                       is_first_content=(idx == 0))
        print("Da xu ly:", name)

    doc.save(OUT_DOCX)
    print("Da xuat:", OUT_DOCX)


if __name__ == "__main__":
    main()
