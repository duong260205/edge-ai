# -*- coding: utf-8 -*-
"""
export_phan_tich_paper_docx.py — Chuyển markdown thành Word (.docx)
Định dạng học thuật: Times New Roman 12, lề chuẩn, bảng Table Grid, tiêu đề màu xanh.
Mặc định: BAO_CAO_PHAN_TICH_HAI_BAI_BAO.md.
Có thể gộp nhiều nguồn vào MỘT file Word (ngắt trang giữa các nguồn):
  python export_phan_tich_paper_docx.py --out KET_QUA.docx phan1.md phan2.md
"""
import argparse
import os
import re
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HERE = os.path.dirname(os.path.abspath(__file__))
MD = os.path.join(HERE, "BAO_CAO_PHAN_TICH_HAI_BAI_BAO.md")
OUT_DOCX = os.path.join(HERE, "BAO_CAO_PHAN_TICH_HAI_BAI_BAO.docx")
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
    """Thêm text hỗ trợ **đậm** và *nghiêng* inline."""
    parts = re.split(r"(\*\*.+?\*\*|\*[^*]+?\*)", text)
    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            run = par.add_run(part[2:-2])
            run.bold = True
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            run = par.add_run(part[1:-1])
            run.italic = True
        else:
            run = par.add_run(part)
        run.font.size = Pt(base_size)
        run.font.color.rgb = color
        set_vietnamese_font(run, font)


def add_table(doc, rows):
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
            run = par.add_run(re.sub(r"\*+", "", text))
            run.font.size = Pt(10.5)
            set_vietnamese_font(run)
            if i == 0:
                run.bold = True
                shd = OxmlElement("w:shd")
                shd.set(qn("w:val"), "clear")
                shd.set(qn("w:fill"), "DCE9F7")
                cell._element.get_or_add_tcPr().append(shd)


def convert_markdown(doc, md_path):
    """Chuyển một file markdown phóng vào Document (không tạo/lưu file)."""
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    i = 0
    n = len(lines)
    in_table = False
    table_buf = []

    def flush_table():
        nonlocal in_table, table_buf
        if table_buf:
            add_table(doc, table_buf)
        in_table = False
        table_buf = []

    while i < n:
        line = lines[i]

        # --- bảng markdown ---
        if line.strip().startswith("|"):
            table_buf.append(line)
            in_table = True
            i += 1
            continue
        elif in_table:
            flush_table()

        stripped = line.strip()

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
                add_runs_with_bold(h, text,
                                   base_size={2: 16, 3: 13.5, 4: 12.5}.get(level, 12.5),
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

        # --- chữ nghiêng nguyên khối (ghi chú cuối, trích dẫn italic) ---
        if (stripped.startswith("*") and stripped.endswith("*") and len(stripped) > 2
                and not (stripped.startswith("**") and stripped.endswith("**"))):
            par = doc.add_paragraph()
            par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            run = par.add_run(stripped.strip("*"))
            run.italic = True
            run.font.size = Pt(11)
            run.font.color.rgb = GRAY
            set_vietnamese_font(run)
            i += 1
            continue

        # --- dòng trống ---
        if not stripped:
            i += 1
            continue

        # --- ảnh minh họa ![caption](đường-dẫn) ---
        m_img = re.match(r"^!\[(.*?)\]\((.+?)\)$", stripped)
        if m_img:
            caption, img = m_img.group(1).strip(), m_img.group(2).strip()
            img_path = img if os.path.isabs(img) else os.path.join(HERE, img)
            if os.path.exists(img_path):
                par = doc.add_paragraph()
                par.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = par.add_run()
                run.add_picture(img_path, width=Cm(15.2))
                if caption:
                    cap = doc.add_paragraph()
                    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    run_c = cap.add_run(caption)
                    run_c.italic = True
                    run_c.font.size = Pt(10.5)
                    run_c.font.color.rgb = GRAY
                    set_vietnamese_font(run_c)
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT_DOCX, help="File .docx kết quả")
    ap.add_argument("inputs", nargs="*", default=None,
                    help="Danh sách file .md nguồn (mặc định: 1 file phân tích hai bài báo)")
    args = ap.parse_args()
    sources = args.inputs if args.inputs else [MD]
    out = args.out if os.path.isabs(args.out) else os.path.join(os.getcwd(), args.out)

    doc = Document()
    for section in doc.sections:
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(3.0)
        section.right_margin = Cm(2.5)

    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")

    for k, src in enumerate(sources):
        if k > 0:  # ngắt trang giữa các phần gộp
            doc.add_page_break()
        convert_markdown(doc, src)

    doc.save(out)
    print("Đã xuất:", out)


if __name__ == "__main__":
    main()
