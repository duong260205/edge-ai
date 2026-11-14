# -*- coding: utf-8 -*-
"""
export_phan_bien_pptx.py — Sinh slide thuyết trình phản biện từ báo cáo
BAO_CAO_PHAN_BIEN_VOICE_AUTH.md, dùng template PowerPoint "DSP" (docs/DSP_template.pptx).

- Giữ nguyên thiết kế template: layout "1_Section Header" (dải đỏ trên đỉnh, tiêu đề trắng)
  cho slide nội dung; layout "1_Content with Caption" (khối đỏ bên trái) cho slide phân đoạn;
  slide 1 của template được tái sử dụng làm slide bìa.
- Nội dung dàn trang tự động: đo chiều rộng/chiều cao văn bản (PIL + Times New Roman/Arial)
  rồi mới đặt hộp thoại, cảnh báo nếu tràn khung.
- Ghi chú thuyết trình (speaker notes) cho từng slide.

Cách dùng: python export_phan_bien_pptx.py
"""

import copy
import os
import sys

from PIL import ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

import deck_figures

HERE = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.join(HERE, "DSP_template.pptx")
OUT = os.path.join(HERE, "BAO_CAO_PHAN_BIEN_VOICE_AUTH_SLIDES.pptx")

# ----------------------------------------------------------------------------
# Bảng màu / font (bám theo template DSP: dải đỏ HUST #C02034, chữ serif)
# ----------------------------------------------------------------------------
RED = RGBColor(0xC0, 0x20, 0x34)
RED_DARK = RGBColor(0x8E, 0x16, 0x26)
DARK = RGBColor(0x21, 0x21, 0x21)
GRAY = RGBColor(0x5A, 0x5A, 0x5A)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
ROSE = RGBColor(0xFC, 0xEF, 0xF1)
GRAYBOX = RGBColor(0xF2, 0xF3, 0xF5)
ROWALT = RGBColor(0xF7, 0xF7, 0xF9)
GOLD = RGBColor(0xFF, 0xD9, 0x66)
NAVY = RGBColor(0x14, 0x14, 0x4B)

SERIF = "Times New Roman"
SANS = "Arial"
FONT_FILES = {
    ("times", False, False): "times.ttf",
    ("times", True, False): "timesbd.ttf",
    ("times", False, True): "timesi.ttf",
    ("times", True, True): "timesbi.ttf",
    ("arial", False, False): "arial.ttf",
    ("arial", True, False): "arialbd.ttf",
    ("arial", False, True): "ariali.ttf",
    ("arial", True, True): "arialbi.ttf",
}
FONT_DIR = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
SCALE = 8  # hệ số phóng khi đo để có độ phân giải dưới điểm


# Khung trang (inch) — 13,333 x 7,5 inch
MARGIN = 0.45
CONTENT_W = 13.3333 - 2 * MARGIN       # 12,4333
BAND_H = 0.83                          # chiều cao dải đỏ của layout
TITLE_TOP = 0.10
KICKER_TOP = 0.88
BODY_TOP = 1.38
BODY_BOTTOM = 6.85   # chừa vùng trang trí gạch ngang dưới cùng của layout

_font_cache = {}

# =====================================================================
# PHẦN 1 — máy đo và đặt hộp văn bản (đo bằng PIL, đặt bằng python-pptx)
# =====================================================================

def _norm_family(family):
    """Chuẩn hoá tên font: nhận cả 'times'/'arial' lẫn tên font đầy đủ."""
    if family in (SANS, "arial"):
        return "arial"
    return "times"


# alias Box = BaseBox được đặt sau khi class BaseBox được định nghĩa (cuối file)


def _font(family, size_pt, bold, italic):
    family = _norm_family(family)
    key = (family, round(size_pt, 1), bold, italic)
    if key not in _font_cache:
        name = FONT_FILES[(family, bold, italic)]
        _font_cache[key] = ImageFont.truetype(os.path.join(FONT_DIR, name), int(size_pt * SCALE))
    return _font_cache[key]


WRAP_SAFETY = 0.985   # PowerPoint vẽ Times rộng hơn phép đo ~1 % → ngắt sớm một chút


def wrap(text, width_in, size_pt, bold=False, italic=False, family="times"):
    """Ngắt dòng giữ nguyên từ; trả về danh sách dòng đã ngắt."""
    f = _font(family, size_pt, bold, italic)
    limit = width_in * 72 * SCALE * WRAP_SAFETY
    lines, cur = [], ""
    for word in text.split():
        cand = (cur + " " + word).strip()
        if not cur or f.getlength(cand) <= limit:
            cur = cand
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def text_h(text, width_in, size_pt, bold=False, italic=False, family="times", lh=1.18):
    """Chiều cao hộp văn bản (inch) sau ngắt dòng."""
    return len(wrap(text, width_in, size_pt, bold, italic, family)) \
        * size_pt * lh / 72.0


def text_w(text, size_pt, bold=False, italic=False, family="times"):
    """Chiều rộng tự nhiên (inch) của một dòng văn bản đơn."""
    return _font(family, size_pt, bold, italic).getlength(text) / (72.0 * SCALE)


class BaseBox:
    """Hộp văn bản: thêm từng đoạn (par) rồi finish() để đo độ cao thật và ghi vào slide."""

    def __init__(self, slide_or_shape, left, top, width, height=2.0,
                 scale=1.0, dry=False, dry_top=0.0):
        if hasattr(slide_or_shape, "shapes"):
            self.shape = slide_or_shape.shapes.add_textbox(
                Inches(left), Inches(top), Inches(width), Inches(height))
            self.slide = slide_or_shape
        else:
            self.shape = slide_or_shape
            self.slide = None
        self.tf = self.shape.text_frame
        self.tf.word_wrap = True
        _no_autofit(self.tf)
        self.tf.margin_left = Inches(0.10)
        self.tf.margin_right = Inches(0.10)
        self.tf.margin_top = Inches(0.04)
        self.tf.margin_bottom = Inches(0.04)
        self.left, self.top, self.width = left, top, width
        self.height, self.scale, self.dry = height, scale, dry
        self.dry_top = dry_top
        self.paras = []          # (text, kwargs)
        self.warnings = []

    # --- thêm nội dung -------------------------------------------------
    def par(self, text, size=12.5, color=DARK, family=SERIF, bold=False,
            italic=False, align=None, bullet=None, hang=0.18, space_after=4.0,
            line_spacing=1.06):
        self.paras.append(dict(text=text, size=size, color=color, family=family,
                               bold=bold, italic=italic, align=align,
                               bullet=bullet, hang=hang, space_after=space_after,
                               line_spacing=line_spacing))
        return self

    # --- đo + ghi ------------------------------------------------------
    def finish(self):
        """Return tổng chiều cao thực (inch) và, nếu không dry, ghi hình vào slide."""
        total = 0.0
        for i, p in enumerate(self.paras):
            lines = wrap(p["text"], self.width - 0.2, p["size"],
                         p["bold"], p["italic"], p["family"])
            h = len(lines) * p["size"] * p["line_spacing"] / 72.0
            sa = p["space_after"] / 72.0
            total += h + sa
            if self.dry:
                continue
            para = self.tf.paragraphs[0] if i == 0 else self.tf.add_paragraph()
            para.space_after = Pt(p["space_after"])
            para.line_spacing = p["line_spacing"]
            if p["align"] is not None:
                para.alignment = p["align"]
            if p["bullet"]:
                _set_bullet(para, p["bullet"], p["hang"])
            run = para.add_run()
            run.text = p["text"]
            f = run.font
            f.size = Pt(p["size"])
            f.bold = p["bold"]
            f.italic = p["italic"]
            f.color.rgb = p["color"]
            f.name = p["family"]
            _set_latin(run, p["family"])
        if not self.dry:
            self.shape.height = Inches(max(total + 0.10, 0.4))
        return total

    def fit_height(self, max_bottom=None, pad=0.05):
        """Trả về chiều cao đề xuất khớp nội dung (dùng khi cần tự nới khung)."""
        return self.finish() + pad


def _set_latin(run, typeface):
    rPr = run._r.get_or_add_rPr()
    latin = rPr.find(qn("a:latin"))
    if latin is None:
        latin = rPr.makeelement(qn("a:latin"), {})
        rPr.append(latin)
    latin.set("typeface", typeface)


def _set_bullet(paragraph, char, hang):
    pPr = paragraph._p.get_or_add_pPr()
    pPr.set("marL", str(int(hang * 914400)))
    pPr.set("indent", str(int(-hang * 914400)))
    for tag in ("a:buNone", "a:buChar", "a:buAutoNum"):
        el = pPr.find(qn(tag))
        if el is not None:
            pPr.remove(el)
    bu = pPr.makeelement(qn("a:buChar"), {"char": char})
    pPr.append(bu)


def _no_autofit(tf):
    bodyPr = tf._txBody.find(qn("a:bodyPr"))
    if bodyPr is None:
        return
    for tag in ("a:normAutofit", "a:spAutoFit"):
        el = bodyPr.find(qn(tag))
        if el is not None:
            bodyPr.remove(el)


def fill_box(box, color):
    """Tô màu hình hộp (shape) — hoạt động với BaseBox hoặc shape."""
    shape = box.shape if hasattr(box, "shape") else box
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()


def table_heights(header, rows, ratios, width, size, hsize, first_col_bold, pad=0.05):
    """Dự đoán chiều cao bảng (inch) — tổng chiều cao từng hàng."""
    def row_h(cells, bold_first):
        h = 0.0
        for c, r in zip(cells, ratios):
            plane = str(c)
            h = max(h, text_h(plane, width * r - 0.16, size,
                              bold_first and cells.index(c) == 0))
        return h + pad
    total = row_h(header, True)
    for row in rows:
        total += row_h(row, first_col_bold)
    return total


def table_height(spec, width, scale=1.0):
    return table_heights(spec["header"], spec["rows"], spec["ratios"],
                         width, spec.get("size", 10.5) * scale,
                         spec.get("hsize", spec.get("size", 10.5)) * scale,
                         spec.get("first_col_bold", False))


def add_table(slide, left, top, width, header, rows, ratios, size=10.5, hsize=10.5,
              first_col_bold=True, row_alt=True, header_color=RED):
    """Bảng TrueGrid: header đỏ, dòng xen kẽ xám, ô đo chiều cao từng dòng."""
    n_rows, n_cols = len(rows) + 1, len(header)
    heights = table_heights(header, rows, ratios, width, size, hsize, first_col_bold,
                            pad=0.06)
    col_w = [width * r for r in ratios]
    shape = slide.shapes.add_table(n_rows, n_cols, Inches(left), Inches(top),
                                   Inches(width), Inches(heights))
    tbl = shape.table
    # tắt style banded mặc định
    tbl.first_row = True
    tbl.horz_banding = False
    for j, w in enumerate(col_w):
        tbl.columns[j].width = Inches(w)

    def fill_cell(cell, text, bold, color_bg, color_tx, sz):
        cell.margin_left = Inches(0.06)
        cell.margin_right = Inches(0.06)
        cell.margin_top = Inches(0.02)
        cell.margin_bottom = Inches(0.02)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf = cell.text_frame
        tf.word_wrap = True
        para = tf.paragraphs[0]
        run = para.add_run()
        run.text = str(text)
        run.font.size = Pt(sz)
        run.font.bold = bold
        run.font.color.rgb = color_tx
        run.font.name = SERIF
        _set_latin(run, SERIF)

    for j, txt in enumerate(header):
        fill_cell(tbl.cell(0, j), txt, True, header_color, WHITE, hsize)
    for i, row in enumerate(rows):
        for j, txt in enumerate(row):
            cell = tbl.cell(i + 1, j)
            alt = row_alt and i % 2 == 1
            fill_cell(cell, txt, first_col_bold and j == 0, ROWALT if alt else WHITE,
                      DARK, size)
    return heights


class Renderer:
    """Vẽ một stack các khối (head, bullets, lead, text, formula, chain, callout,
    table, figure, cols, gap) vào slide, tự đo cao từng khối."""

    HEAD_SIZE = 17.0

    def __init__(self, slide, scale=1.0, dry=False):
        self.slide = slide
        self.scale = scale
        self.dry = dry
        self.boxes = []
        self.warnings = []

    def box(self, left, top, width, height=None):
        return BaseBox(self.slide, left, top, width, height or 2.0,
                       scale=self.scale, dry=self.dry)

    def head(self, text, size=17, sub=None):
        b = self.box(MARGIN, KICKER_TOP - 0.02, CONTENT_W)
        b.par(text, size=self.HEAD_SIZE if size == 17 else size, bold=True,
              color=RED_DARK, family=SERIF, space_after=0)
        b.finish()
        self.boxes.append(b)
        return b

    def stack(self, blocks, top, left, width):
        """Vẽ danh sách khối theo chiều dọc, trả về toạ độ đáy."""
        y = top
        for kind, *rest in blocks:
            if kind == "gap":
                y += rest[0]
                continue
            if kind == "bullets":
                items, = rest
                b = self.box(left, y, width)
                for it in items:
                    if isinstance(it, tuple):
                        lvl, txt = it
                    else:
                        lvl, txt = 0, it
                    if lvl == 0:
                        b.par(txt, size=13.5, bullet="\u2022", space_after=3.5)
                    elif lvl == 1:
                        b.par(txt, size=12.5, bullet="\u2013", space_after=2.5)
                    else:
                        b.par(txt, size=11.5, bullet="\u00b7", space_after=2.5)
                y += b.finish() + 0.12
                self.boxes.append(b)
            elif kind == "lead":
                text, = rest
                b = self.box(left, y, width)
                b.par(text, size=13.5, bold=True, color=RED_DARK, space_after=0)
                y += b.finish() + 0.10
                self.boxes.append(b)
            elif kind == "text":
                text, = rest
                b = self.box(left, y, width)
                b.par(text, size=12.5, color=DARK, space_after=0)
                y += b.finish() + 0.10
                self.boxes.append(b)
            elif kind == "formula":
                text, = rest
                b = self.box(left + 0.10, y + 0.07, width - 0.20)
                b.par(text, size=13, italic=True, family="times",
                      align=PP_ALIGN.CENTER, color=NAVY,
                      space_after=1.0, line_spacing=1.1)
                h = b.finish() + 0.14
                fill_box(b, ROSE)
                y += h + 0.14
                self.boxes.append(b)
            elif kind == "chain":
                text, = rest
                b = self.box(left, y + 0.07, width)
                b.par(text, size=12, bold=True, color=WHITE,
                      align=PP_ALIGN.CENTER, space_after=1.0, line_spacing=1.15)
                h = b.finish() + 0.14
                fill_box(b, RED)
                y += h + 0.14
                self.boxes.append(b)
            elif kind == "callout":
                (text, tone), = rest
                b = self.box(left + 0.10, y + 0.06, width - 0.20)
                b.par(text, size=12, bold=(tone == "rose"), italic=(tone != "rose"),
                      color=RED_DARK if tone == "rose" else RGBColor(0x33, 0x33, 0x33),
                      space_after=0, line_spacing=1.08)
                h = b.finish()
                fill_box(b, ROSE if tone == "rose" else GRAYBOX)
                y += h + 0.22
                self.boxes.append(b)
            elif kind == "table":
                spec, = rest
                sc = self.scale
                h = table_heights(spec["header"], spec["rows"], spec["ratios"],
                                  width, spec.get("size", 10.5) * sc,
                                  spec.get("hsize", spec.get("size", 10.5)) * sc,
                                  spec.get("first_col_bold", True))
                if not self.dry:
                    add_table(self.slide, left, y, width, spec["header"], spec["rows"],
                              spec["ratios"], size=spec.get("size", 10.5) * sc,
                              hsize=spec.get("hsize", spec.get("size", 10.5)) * sc,
                              first_col_bold=spec.get("first_col_bold", True))
                y += h + 0.18
            elif kind == "figure":
                spec, = rest
                w_in = min(spec.get("width", 8.0) * self.scale, width)
                _s, _w, h_in = figure_size(spec["name"], w_in, max_h=4.8)
                if not self.dry:
                    place_figure(self.slide, spec["name"], left + (width - _w) / 2.0,
                                 y, min(w_in, width), max_h=4.8)
                y += h_in + 0.12
            elif kind == "cols":
                left_blocks, right_blocks, split = rest
                gap = 0.30
                w_l = (width - gap) * split
                w_r = width - gap - w_l
                d_l = Renderer(self.slide, scale=self.scale, dry=True)
                y_l_end = d_l.stack(left_blocks, y, left, w_l)
                d_r = Renderer(self.slide, scale=self.scale, dry=True)
                y_r_end = d_r.stack(right_blocks, y, left + w_l + gap, w_r)
                if not self.dry:
                    rl = Renderer(self.slide, scale=self.scale)
                    rl.stack(left_blocks, y, left, w_l)
                    rr = Renderer(self.slide, scale=self.scale)
                    rr.stack(right_blocks, y, left + w_l + gap, w_r)
                y = max(y_l_end, y_r_end)
        return y


def fig_size_h(name, width_in, max_h=99.0):
    _s, _w, h_in = figure_size(name, width_in, max_h)
    return h_in


def find_layout(prs, layout_name):
    for layout in prs.slide_layouts:
        if layout.name == layout_name:
            return layout
    raise SystemExit("Không tìm thấy layout: %s" % layout_name)


def drop_placeholders(slide):
    for sh in list(slide.shapes):
        if sh.is_placeholder and sh.placeholder_format.type in (
                PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT,
                PP_PLACEHOLDER.PICTURE, PP_PLACEHOLDER.TABLE):
            sh._element.getparent().remove(sh._element)


def delete_slides(prs, keep=1):
    xml_slides = prs.slides._sldIdLst
    slides = list(xml_slides)
    for s in slides[keep:]:
        xml_slides.remove(s)


def new_slide(prs, page_field):
    """Tạo slide mới từ layout Section Header; placeholder số trang có sẵn từ layout."""
    import copy as _copy
    layout = find_layout(prs, "1_Section Header")
    slide = prs.slides.add_slide(layout)
    # placeholder tiêu đề có sẵn từ layout — xoá để dùng hộp riêng
    for sh in list(slide.shapes):
        if sh.is_placeholder and sh.placeholder_format.type == PP_PLACEHOLDER.TITLE:
            sh._element.getparent().remove(sh._element)
    # placeholder số trang/Object có sẵn từ layout - badcase khong dùng copy
    # giữ nguyên để tránh trùng lặp
    return slide


def plain(text):
    return text.replace("**", "").replace("*", "")


def set_title(slide, text, size=25):
    for sh in slide.shapes:
        if sh.is_placeholder and sh.placeholder_format.type == PP_PLACEHOLDER.TITLE:
            tf = sh.text_frame
            tf.clear()
            for i, line in enumerate(text.split("\n")):
                para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                run = para.add_run()
                run.text = line
                run.font.size = Pt(size)
                run.font.bold = True
                run.font.color.rgb = WHITE
                run.font.name = SANS
                _set_latin(run, SANS)
            return sh
    return None


def add_notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def fig_info(name):
    """Trả về (path, design_w, aspect_ratio, ok) — dùng qua deck_figures.info()."""
    path, design_w, ar = deck_figures.info(name)
    return path, design_w, ar, True


def figure_size(name, max_w, max_h=99.0, min_scale=0.10):
    """(scale, width_in, height_in) chiều hình vừa vào khung (max_w, max_h).
    design_w là bề rộng thiết kế gốc của hình — hình vẽ ở width_in = design_w * scale."""
    path, design_w, ar = deck_figures.info(name)
    w_in = min(max_w, design_w)
    h_in = w_in * ar
    if max_h < 99.0 and h_in > max_h:
        h_in = max_h
        w_in = h_in / ar if ar > 0 else max_w
    scale = w_in / max(design_w, 0.01)
    return max(scale, min_scale), w_in, h_in


def place_figure(slide, name, left, top, max_w, max_h=99.0, center_w=None):
    scale, w, h = figure_size(name, max_w, max_h)
    if center_w and w < center_w:
        left += (center_w - w) / 2.0
    path, _dw, _ar = deck_figures.info(name)
    return slide.shapes.add_picture(path, Inches(left), Inches(top),
                                   Inches(w), Inches(h))


def _points_height(points):
    total = 0.0
    for p in points:
        total += text_h(p, CONTENT_W - 1.2, 13)
    return total


def divider(prs, page_field, kicker, title, points, notes="", fig=None, fig_first=False):
    """Slide phân đoạn: layout Content with Caption (khối đỏ bên trái)."""
    layout = find_layout(prs, "1_Content with Caption")
    slide = prs.slides.add_slide(layout)
    # layout này đã có sẵn SLIDE_NUMBER placeholder; không copy thêm
    b = Box(slide, 0.45, 1.30, 3.9, 1.0)
    b.par(kicker, size=15, bold=True, color=GOLD, family="arial", space_after=4)
    b.finish()
    y = 2.10
    for ln in title.split("\n"):
        b = Box(slide, 0.45, y, 3.9, 0.7)
        b.par(ln, size=22, bold=True, color=WHITE, family="arial", space_after=0,
              line_spacing=1.05)
        h = b.finish()
        y += h + 0.10
    x_right = 4.9
    w_right = 13.3333 - x_right - 0.55
    if fig and fig_first:
        place_figure(slide, fig, x_right, 1.35, w_right)
        top = 1.35 + fig_size_h(fig, w_right, max_h=2.6) + 0.25
    else:
        top = 1.35
    for p in points[:5]:
        b = Box(slide, x_right, top, w_right)
        b.par(p, size=13, bullet="\u2022", space_after=6)
        h = b.finish()
        top += h + 0.14
    if notes:
        add_notes(slide, notes)
    return slide, None


def unify_divider_titles():
    return None


def time_plan_text():
    return ""


# Alias tương thích bản gốc — đặt tại đây (sau khi class BaseBox đã tồn tại)
Box = BaseBox


def content(prs, page_field, title, head, blocks=(), notes=""):
    """Slide nội dung chuẩn: layout Section Header, head đỏ, dàn khối tự do,
    trả về (slide, slack) — slack là phần trang còn trống dưới đáy (inch)."""
    slide = new_slide(prs, page_field)
    set_title(slide, title)
    r = Renderer(slide)
    r.head(head)
    bottom = r.stack(list(blocks), BODY_TOP, MARGIN, CONTENT_W)
    slack = BODY_BOTTOM - bottom
    if slack < -0.02:
        print("   [warn] tràn khung %.2f in — %s" % (-slack, title[:50]))
    if notes:
        add_notes(slide, notes)
    return slide, slack
