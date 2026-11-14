# -*- coding: utf-8 -*-
"""
export_docx.py — Chuyển BAO_CAO_DU_AN.md thành file Word (.docx) có định dạng
- Parse heading, bảng, danh sách, chữ đậm, mermaid block (thay bằng ảnh PNG tương ứng)
- Chèn 4 hình đã render từ render_diagrams.py vào đúng vị trí
Cách dùng: python export_docx.py
"""
import os
import re
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HERE = os.path.dirname(os.path.abspath(__file__))
MD = os.path.join(HERE, "BAO_CAO_DU_AN.md")
OUT_DOCX = os.path.join(HERE, "BAO_CAO_DU_AN.docx")

# Ánh xạ mermaid block -> ảnh PNG (theo thứ tự xuất hiện trong báo cáo)
MERMAID_IMAGES = [
    "hinh1_kien_truc.png",
    "hinh2_may_trang_thai.png",
    "hinh3_voice_pipeline.png",
    "hinh4_face_pipeline.png",
]

BLUE = RGBColor(0x15, 0x65, 0xC0)
DARK = RGBColor(0x21, 0x21, 0x21)
GRAY = RGBColor(0x60, 0x60, 0x60)


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


def add_runs_with_bold(par, text, base_size=12, color=DARK, font="Times New Roman"):
    """Thêm text hỗ trợ **đậm** inline."""
    parts = re.split(r"(\*\*.+?\*\*)", text)
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = par.add_run(part[2:-2])
            run.bold = True
        else:
            run = par.add_run(part)
        run.font.size = Pt(base_size)
        run.font.color.rgb = color
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
            par = cell.paragraphs[0]
            run = par.add_run(re.sub(r"\*\*", "", text))
            run.font.size = Pt(10.5)
            set_vietnamese_font(run)
            if i == 0:
                run.bold = True
                shd = OxmlElement("w:shd")
                shd.set(qn("w:val"), "clear")
                shd.set(qn("w:fill"), "DCE9F7")
                cell._element.get_or_add_tcPr().append(shd)


def add_image(doc, img_name, caption=None, width_cm=16.5):
    path = os.path.join(HERE, img_name)
    if not os.path.exists(path):
        par = doc.add_paragraph("[Thiếu ảnh: %s]" % img_name)
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


def main():
    with open(MD, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    doc = Document()

    # Lề trang chuẩn báo cáo
    for section in doc.sections:
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(3.0)
        section.right_margin = Cm(2.5)

    # Style mặc định
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")

    mermaid_idx = 0
    i = 0
    n = len(lines)
    in_table = False
    table_buf = []
    in_code = False
    code_is_mermaid = False

    def flush_table():
        nonlocal in_table, table_buf
        if table_buf:
            add_table(doc, table_buf)
        in_table = False
        table_buf = []

    while i < n:
        line = lines[i]

        # --- code fence / mermaid ---
        if line.strip().startswith("```"):
            if not in_code:
                in_code = True
                code_is_mermaid = "mermaid" in line
                if not code_is_mermaid:
                    # code block thường: in nguyên văn monospace
                    i += 1
                    while i < n and not lines[i].strip().startswith("```"):
                        par = doc.add_paragraph()
                        run = par.add_run(lines[i])
                        run.font.name = "Consolas"
                        run.font.size = Pt(9)
                        run.font.color.rgb = DARK
                        i += 1
                    in_code = False
                else:
                    # mermaid -> thay bằng ảnh tương ứng
                    if mermaid_idx < len(MERMAID_IMAGES):
                        add_image(doc, MERMAID_IMAGES[mermaid_idx])
                        mermaid_idx += 1
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

        # --- bỏ qua caption mermaid cũ (đã có ảnh) ---
        if stripped.startswith("*Hình") and stripped.endswith("*"):
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
                par = doc.add_heading(text, level=0)
                for run in par.runs:
                    run.font.color.rgb = BLUE
                    set_vietnamese_font(run)
                par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                h = doc.add_heading("", level=min(level - 1, 3))
                add_runs_with_bold(h, text, base_size={2: 16, 3: 13.5, 4: 12.5}.get(level, 12.5),
                                   color=BLUE)
                h.alignment = WD_ALIGN_PARAGRAPH.LEFT
            i += 1
            continue

        # --- dòng kẻ ngang ---
        if stripped == "---":
            i += 1
            continue

        # --- danh sách có số / gạch đầu dòng ---
        m_num = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        m_bul = re.match(r"^[-*]\s+(.*)$", stripped)
        if m_num:
            par = doc.add_paragraph(style="List Number")
            add_runs_with_bold(par, m_num.group(2))
            i += 1
            continue
        if m_bul:
            par = doc.add_paragraph(style="List Bullet")
            add_runs_with_bold(par, m_bul.group(1))
            i += 1
            continue

        # --- dòng trống ---
        if not stripped:
            i += 1
            continue

        # --- paragraph thường ---
        par = doc.add_paragraph()
        par.paragraph_format.first_line_indent = Cm(0.8)
        par.paragraph_format.space_after = Pt(6)
        par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        add_runs_with_bold(par, stripped)

        i += 1

    if in_table:
        flush_table()

    doc.save(OUT_DOCX)
    print("Da xuat:", OUT_DOCX)


if __name__ == "__main__":
    main()
