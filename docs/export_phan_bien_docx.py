# -*- coding: utf-8 -*-
"""
export_phan_bien_docx.py — Chuyển BAO_CAO_PHAN_BIEN_VOICE_AUTH.md thành file Word (.docx)
- Công thức LaTeX ($$...$$ và $...$) render thành ảnh PNG (matplotlib mathtext)
- Mermaid block -> hình PNG vẽ sẵn (hinh5_cnn_kien_truc.png)
- Bảng markdown -> bảng Word; code block ASCII -> Consolas
Cách dùng: python export_phan_bien_docx.py
"""
import os
import re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HERE = os.path.dirname(os.path.abspath(__file__))
MD = os.path.join(HERE, "BAO_CAO_PHAN_BIEN_VOICE_AUTH.md")
OUT_DOCX = os.path.join(HERE, "BAO_CAO_PHAN_BIEN_VOICE_AUTH.docx")
TMP_DIR = os.path.join(HERE, "_eq_cache")
os.makedirs(TMP_DIR, exist_ok=True)

BLUE = RGBColor(0x15, 0x65, 0xC0)
DARK = RGBColor(0x21, 0x21, 0x21)
GRAY = RGBColor(0x60, 0x60, 0x60)

# ---------------------------------------------------------------
# LaTeX -> mathtext adapt + render
# ---------------------------------------------------------------

BS2 = chr(92) * 2   # hai ký tự backslash liên tiếp (ngắt dòng LaTeX)


def adapt_to_mathtext(tex):
    """Chuyển LaTeX sang cú pháp matplotlib mathtext hỗ trợ được."""
    B = chr(92)
    t = tex.strip()
    while (B + "boxed{") in t:
        j = t.find(B + "boxed{")
        k = j + len(B + "boxed{")
        depth = 1
        m = k
        while m < len(t) and depth > 0:
            if t[m] == "{":
                depth += 1
            elif t[m] == "}":
                depth -= 1
            m += 1
        inner = t[k:m - 1]
        t = t[:j] + inner + t[m:]
    b_key = B + "begin{cases}"
    e_key = B + "end{cases}"
    if b_key in t:
        j0 = t.find(b_key)
        i0 = j0 + len(b_key)
        i1 = t.find(e_key)
        if i1 > i0:
            inner = t[i0:i1]
            rows = inner.split(BS2)
            clean = []
            for r in rows:
                r = r.strip()
                if r.startswith("{") and r.endswith("}"):
                    r = r[1:-1].strip()
                if r:
                    clean.append(r)
            rows = [r.replace("&", "    ") for r in clean]
            t = t[:j0] + "   ".join(rows) + t[i1 + len(e_key):]
    t = t.replace(B + "text", "")
    t = t.replace(B + "dfrac", B + "frac")
    t = t.replace(B + "left", "")
    t = t.replace(B + "right", "")
    t = t.replace(B + "qquad", "  ")
    t = t.replace(B + "quad", "  ")
    t = t.replace(B + "underbrace", "")
    t = t.replace(B + "mathrm", "")
    t = t.replace(B + "Longleftrightarrow", B + "Leftrightarrow")
    t = t.replace(B + "mathcal{L}", "L")
    # mathtext khong hieu \le / \ge (chi hieu \leq / \geq) — them neu dau sau khong phai chu cai
    t = re.sub(re.escape(B) + "le(?![a-zA-Z])", lambda m: B + "leq", t)
    t = re.sub(re.escape(B) + "ge(?![a-zA-Z])", lambda m: B + "geq", t)
    # \mathrm{xyz} -> xyz
    t = re.sub(re.escape(B) + "mathrm" + re.escape("{") + "([^}]*)" + re.escape("}"), lambda m: m.group(1), t)
    t = t.replace(B + "!", " ")
    t = t.replace("%", chr(92) + "%")
    t = t.replace(chr(215), " times ")
    t = t.replace(chr(8722), "-")
    t = t.replace(chr(8594), B + "rightarrow")
    t = t.replace(chr(8776), B + "approx")
    t = t.replace(chr(8805), B + "geq")
    t = t.replace(chr(8804), B + "leq")
    t = t.replace(chr(10003), B + "checkmark")
    # giu tieng Viet co dau (mathtext/DejaVu render duoc), chi loai CJK tro len
    t = "".join(ch if ord(ch) < 128 or ord(ch) < 11904 else " " for ch in t)
    # buoc ve sinh cuoi: giu ky tu an toan cho mathtext (mathtext doc chu "r/S" thieu buc!
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                  " +-*/=()<>,.;:!?'[]|{}^_")
    allowed.add(chr(92))
    t = "".join(ch if ch in allowed or ord(ch) > 127 else " " for ch in t)
    return t



def render_tex_image(tex: str, fname: str, fontsize=13, display=True):
    """Render một công thức LaTeX thành PNG; trả về đường dẫn file."""
    path = os.path.join(TMP_DIR, fname)
    if os.path.exists(path):
        return path
    mt = adapt_to_mathtext(tex)
    dpi = 220
    if not mt.startswith("$"):
        mt = "$" + mt + "$"
    try:
        fig = plt.figure(figsize=(0.1, 0.1), dpi=dpi)
        fig.text(0, 0, mt, fontsize=fontsize)
        fig.savefig(path, dpi=dpi, bbox_inches="tight", pad_inches=0.04,
                    facecolor="white")
        plt.close(fig)
        if os.path.exists(path) and os.path.getsize(path) > 100:
            return path
    except Exception as e:
        plt.close("all")
        print("  [warn] render fail (%s): %s" % (fname, str(e)))
    # fallback: vẽ text thuần
    fig = plt.figure(figsize=(6, 0.6), dpi=dpi)
    fig.text(0.01, 0.5, tex.strip(), fontsize=9, family="DejaVu Sans", va="center")
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def draw_cnn_diagram():
    """Vẽ kiến trúc CNN (mermaid block trong báo cáo) thành PNG."""
    path = os.path.join(TMP_DIR, "hinh5_cnn_kien_truc.png")
    if os.path.exists(path):
        return path
    layers = [
        ("Input\n403 = 31 khung × 13 hệ số", "#607D8B"),
        ("Reshape\n(31, 13)", "#5C6BC0"),
        ("Conv1D · 8 filters\nkernel 3 · ReLU\n320 tham số", "#2196F3"),
        ("MaxPooling1D\npool 2 · stride 2\n31 → 16", "#26A69A"),
        ("Dropout\n0.25", "#FFA726"),
        ("Conv1D · 16 filters\nkernel 3 · ReLU\n400 tham số", "#2196F3"),
        ("MaxPooling1D\npool 2 · stride 2\n16 → 8", "#26A69A"),
        ("Dropout\n0.25", "#FFA726"),
        ("Flatten\n128", "#8D6E63"),
        ("Dense 2 · Softmax\n258 tham số\nP(noise), P(target)", "#E53935"),
    ]
    n = len(layers)
    fig, ax = plt.subplots(figsize=(13.2, 2.6), dpi=160)
    ax.set_xlim(0, n * 2)
    ax.set_ylim(0, 2)
    ax.axis("off")
    w = 1.7
    for i, (txt, col) in enumerate(layers):
        x = i * 2 + 0.15
        box = matplotlib.patches.FancyBboxPatch(
            (x, 0.35), w, 1.3,
            boxstyle="round,pad=0.02,rounding_size=0.08",
            linewidth=1.4, edgecolor="#263238", facecolor=col)
        ax.add_patch(box)
        ax.text(x + w / 2, 1.0, txt, ha="center", va="center",
                fontsize=8.2, fontweight="bold", color="white", linespacing=1.35)
        if i < n - 1:
            ax.annotate("", xy=(x + 2.02, 1.0), xytext=(x + w + 0.05, 1.0),
                        arrowprops=dict(arrowstyle="-|>", color="#455A64", lw=1.6))
    ax.set_title("Kiến trúc CNN 1D của dự án (978 tham số, ~16,1 K MAC/suy luận)",
                 fontsize=12, fontweight="bold", pad=10)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


# ---------------------------------------------------------------
# Word helpers
# ---------------------------------------------------------------

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


_inline_eq_n = [0]


def add_math_image_run(par, tex, fontsize=10.5, max_h_cm=0.55):
    _inline_eq_n[0] += 1
    path = render_tex_image(tex, "eq_i%03d.png" % _inline_eq_n[0],
                            fontsize=fontsize, display=False)
    run = par.add_run()
    try:
        from PIL import Image
        with Image.open(path) as im:
            h_px = im.size[1]
        h_cm = h_px / 220 * 2.54
        h_cm = min(h_cm, max_h_cm)
        run.add_picture(path, height=Cm(h_cm))
    except Exception:
        run.add_text("$" + tex + "$")


def add_runs_with_math(par, text, base_size=12, color=DARK, font="Times New Roman"):
    parts = re.split(r"(\$[^$]+\$)", text)
    for seg in parts:
        if not seg:
            continue
        if seg.startswith("$") and seg.endswith("$") and len(seg) > 2:
            add_math_image_run(par, seg[1:-1])
        else:
            add_runs_with_bold(par, seg, base_size=base_size, color=color, font=font)


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
            run = par.add_run(re.sub(r"\*\*", "", text))
            run.font.size = Pt(9.5)
            set_vietnamese_font(run)
            if i == 0:
                run.bold = True
                shd = OxmlElement("w:shd")
                shd.set(qn("w:val"), "clear")
                shd.set(qn("w:fill"), "DCE9F7")
                cell._element.get_or_add_tcPr().append(shd)
    doc.add_paragraph()


def add_image(doc, path, caption=None, max_width_cm=16.8):
    if not path or not os.path.exists(path):
        return
    from PIL import Image
    try:
        with Image.open(path) as im:
            w_px, h_px = im.size
        dpi = 220 if "_eq_cache" in path else 160
        w_cm = w_px / dpi * 2.54
        scale = min(1.0, max_width_cm / w_cm)
        par = doc.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = par.add_run()
        run.add_picture(path, width=Cm(w_cm * scale))
        if caption:
            cap = doc.add_paragraph()
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = cap.add_run(caption)
            r.italic = True
            r.font.size = Pt(9.5)
            r.font.color.rgb = GRAY
            set_vietnamese_font(r)
    except Exception as e:
        print("  [warn] image fail:", str(e))


# ---------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------

def main():
    with open(MD, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

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

    eq_counter = 0
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
        stripped = line.strip()

        # ---- code fence (ASCII art) ----
        if stripped.startswith("```"):
            flush_table()
            lang = stripped[3:].strip()
            i += 1
            block = []
            while i < n and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            if lang == "mermaid":
                add_image(doc, draw_cnn_diagram(),
                          "Hình 5.1 — Kiến trúc CNN 1D của dự án (vẽ lại từ sơ đồ Mermaid)")
            else:
                for bl in block:
                    par = doc.add_paragraph()
                    par.paragraph_format.space_after = Pt(0)
                    run = par.add_run(bl)
                    run.font.name = "Consolas"
                    run.font.size = Pt(7.5)
                    run.font.color.rgb = DARK
                    rPr = run._element.get_or_add_rPr()
                    rFonts = rPr.find(qn("w:rFonts"))
                    if rFonts is None:
                        rFonts = OxmlElement("w:rFonts")
                        rPr.append(rFonts)
                    for attr in ("w:ascii", "w:hAnsi", "w:cs"):
                        rFonts.set(qn(attr), "Consolas")
                doc.add_paragraph()
            continue

        # ---- display math $$...$$ ----
        if stripped.startswith("$$"):
            flush_table()
            eq = stripped[2:].strip()
            if not eq.endswith("$$"):
                i += 1
                while i < n and not lines[i].strip().endswith("$$"):
                    eq += " " + lines[i].strip()
                    i += 1
                eq += " " + lines[i].strip().rstrip("$$").strip() if i < n else ""
                if i < n:
                    eq = eq.rstrip("$$").strip()
            eq_counter += 1
            path = render_tex_image(eq, "eq_%03d.png" % eq_counter, fontsize=12.5)
            add_image(doc, path)
            i += 1
            continue

        # ---- bảng ----
        if stripped.startswith("|"):
            table_buf.append(line)
            in_table = True
            i += 1
            continue
        elif in_table:
            flush_table()

        # ---- heading ----
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            text = re.sub(r"\*+", "", m.group(2)).strip()
            if level == 1:
                par = doc.add_heading(text, level=0)
                for run in par.runs:
                    run.font.color.rgb = BLUE
                    set_vietnamese_font(run)
                par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                h = doc.add_heading("", level=min(level - 1, 3))
                add_runs_with_math(h, text,
                                   base_size={2: 15, 3: 13, 4: 12}.get(level, 12),
                                   color=BLUE)
                h.alignment = WD_ALIGN_PARAGRAPH.LEFT
            i += 1
            continue

        # ---- hr ----
        if stripped == "---":
            i += 1
            continue

        # ---- blockquote ----
        if stripped.startswith("> "):
            par = doc.add_paragraph()
            par.paragraph_format.left_indent = Cm(0.6)
            add_runs_with_math(par, stripped[2:], base_size=11, color=GRAY)
            i += 1
            continue

        # ---- list ----
        m_num = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        m_bul = re.match(r"^[-*]\s+(.*)$", stripped)
        if m_num:
            par = doc.add_paragraph(style="List Number")
            add_runs_with_math(par, m_num.group(2))
            i += 1
            continue
        if m_bul:
            par = doc.add_paragraph(style="List Bullet")
            add_runs_with_math(par, m_bul.group(1))
            i += 1
            continue

        # ---- trống ----
        if not stripped:
            i += 1
            continue

        # ---- paragraph: tách inline math $...$ ----
        par = doc.add_paragraph()
        par.paragraph_format.first_line_indent = Cm(0.7)
        par.paragraph_format.space_after = Pt(6)
        par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        add_runs_with_math(par, stripped)
        i += 1

    if in_table:
        flush_table()

    doc.save(OUT_DOCX)
    print("Đã xuất:", OUT_DOCX)


def add_runs_with_bold_into(par, text, base_size=12, color=DARK):
    add_runs_with_bold(par, text, base_size=base_size, color=color)


if __name__ == "__main__":
    main()
