# -*- coding: utf-8 -*-
"""
export_so_tay_pptx.py — Sinh bộ 14 slide báo cáo kỹ thuật cho phần bảo vệ:
  (1) bản chất toán học DCT-II (cosin) trong MFCC, và
  (2) phân tích đối sánh hai bài báo quốc tế 2026 (Medur-2026 / Wiley IJIS và
      Sensors-2026 / MDPI) cho hệ khóa cửa ESP32-S3.
Tái sử dụng máy móc dàn trang của export_phan_bien_pptx.py + template DSP_template.pptx.
Cách dùng: python export_so_tay_pptx.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import deck_figures
import export_phan_bien_pptx as base
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.util import Inches, Pt

from export_phan_bien_pptx import (
    Box, Renderer, content, divider, delete_slides, set_title, add_notes,
    fill_box, plain, RED, RED_DARK, DARK, GRAY, WHITE, ROSE, GRAYBOX, GOLD,
)

TPL = os.path.join(HERE, "DSP_template.pptx")
OUT = os.path.join(HERE, "BAO_CAO_SO_TAY_SLIDES.pptx")

BAND = RGBColor(0xC0, 0x20, 0x34)
ROWALT = RGBColor(0xF7, 0xF7, 0xF9)


def title_boxes(slide, title_lines, size=25):
    set_title(slide, "\n".join(title_lines), size=size)


def main():
    deck_figures.ensure()
    prs = Presentation(TPL)

    page_field = None
    for sh in prs.slides[1].shapes:
        if sh.is_placeholder and sh.placeholder_format.type == PP_PLACEHOLDER.SLIDE_NUMBER:
            page_field = sh._element
    if page_field is None:
        raise SystemExit("Không lấy được placeholder số trang từ template")

    # ---- bìa: tái sử dụng slide 1 của template --------------------------
    title_slide = prs.slides[0]
    for sh in title_slide.shapes:
        if sh.name == "Rectangle 16":
            sh.text_frame.paragraphs[0].runs[0].text = (
                "BẢN CHẤT DCT-II TRONG MFCC\n& ĐỐI SÁNH HAI BÀI BÁO 2026"
            )
    b = Box(title_slide, 0.64, 1.28, 8.98, 0.45)
    b.par("BÁO CÁO KỸ THUẬT — CHUYÊN ĐỀ EDGE AI", size=20, bold=True, color=RED,
          family="arial", space_after=0)
    b.finish()
    b = Box(title_slide, 0.64, 3.22, 9.6, 0.42)
    b.par("Phần 1 — Từ mô hình giọng L(f) = H(f) + S(f) đến công thức cosin DCT-II và 13 hệ số MFCC · "
          "Phần 2 — Đối sánh Medur-2026 (Wiley IJIS) & Sensors-2026 (MDPI) trên ESP32-S3",
          size=12.5, italic=True, color=RGBColor(0x44, 0x44, 0x44), space_after=0)
    b.finish()
    b = Box(title_slide, 6.55, 6.10, 6.25, 1.15)
    fill_box(b, WHITE)
    b.shape.line.color.rgb = RGBColor(0xD9, 0xD9, 0xD9)
    b.shape.line.width = Pt(0.75)
    b.par("Người hướng dẫn: PGS.TS. Hán Trọng Thanh — ĐHBK Hà Nội", size=11.5,
          bold=True, color=RED_DARK, family="arial", space_after=4)
    b.par("Nền tảng: ESP32-S3 LX7 dual-core · 512 KB SRAM · 8 MB PSRAM · mic I2S INMP441 @16 kHz",
          size=11.5, color=GRAY, space_after=4, line_spacing=1.1)
    b.par("Nguồn đối sánh: Wiley IJIS DOI 10.1155/int/2317323 · Sensors DOI 10.3390/s26133972",
          size=11.5, color=GRAY, space_after=0, line_spacing=1.1)
    b.finish()
    add_notes(title_slide, "Bìa: nêu hai câu hỏi cốt lõi — (1) bản chất toán học của phép tách cosin, "
                           "(2) bài học từ 2 công trình 2026 cho hệ thống biên ESP32-S3.")

    delete_slides(prs, keep=1)
    report = []

    def run(title, head, blocks=(), notes="", expect_div=False, kicker="", points=None, fig=None):
        if expect_div:
            slide, _ = divider(prs, page_field, kicker, title, points or [], notes, fig=fig)
            report.append((title.replace("\n", " "), None))
            print("  [phan doan] %s" % title.replace("\n", " "))
            return slide
        slide, slack = content(prs, page_field, title, head, blocks, notes)
        report.append((title.replace("\n", " "), slack))
        print("  %-58s slack %+.2f in" % (title.replace("\n", " ")[:58], slack))
        return slide

    # =====================================================================
    # PHẦN MỞ ĐẦU (SLIDE 1–2)
    # =====================================================================
    run("TỔNG QUAN\nKHUNG PHƯƠNG PHÁP LUẬN", None, points=[
        "Câu hỏi 1: Bản chất toán học của phép tách cosin (DCT-II) trong trích xuất đặc trưng.",
        "Câu hỏi 2: Thực chứng và bài học từ 2 công trình quốc tế 2026 cho hệ thống biên ESP32-S3.",
        "Sơ đồ song song 2 nhánh: lý thuyết chuẩn (32 Mel + DCT-II) và nhúng tốc độ cao (Approximate Log-Mel).",
    ], notes="Định vị hai câu hỏi cốt lõi của phần bảo vệ trước khi đi vào từng phần.",
        expect_div=True, kicker="MỞ ĐẦU", fig="two_pipelines")

    run("Hai nhánh triển khai của đề tài",
        "Nhánh lý thuyết chuẩn (32 Mel + DCT-II) và nhánh nhúng tốc độ cao (Approximate Log-Mel)",
        [("table", {
             "header": ["Tiêu chí", "Nhánh 1 — Edge Impulse (chuẩn học thuật)",
                        "Nhánh 2 — Firmware tự viết (tốc độ cao)"],
             "ratios": [0.75, 1.15, 1.15],
             "rows": [
                 ["Bộ lọc Mel", "32 băng tam giác Mel (FFT 512, Hann)", "13 dải Mel xấp xỉ, mỗi dải 19 bin"],
                 ["Biến đổi cuối", "DCT-II → 13 MFCC/khung", "Log-Energy trực tiếp (không DCT-II)"],
                 ["Tensor đầu vào", "31×13 = 403 chiều", "32×13 = 416 chiều"],
                 ["Mô hình", "CNN 1D INT8 · 978 tham số", "CNN 2D INT8 · ~13,6K tham số"],
                 ["Flash / RAM", "INT8 5.920 B (5,8 KB); RAM EON 3.432 B", "~12 KB; tensor arena ~40 KB trên PSRAM"],
                 ["Suy luận", "1–3 ms (EON), budget 100 ms", "chạy liên tục ở STANDBY"],
                 ["Độ chính xác", "83,33% (F1 0,84; suy hao INT8 = 0)", "không đo chính thức"],
             ],
             "size": 9.5, "first_col_bold": True,
         }),
         ("callout", ("Câu chốt định hướng: cùng một bài toán danh tính nhưng hai cấu hình đánh đổi khác nhau — "
                      "nhánh 1 trả lời 'chuẩn khoa học là gì', nhánh 2 trả lời 'biên chạy realtime được chưa'.",
                      "rose"))],
        "Slide 2 của outline: đối chiếu song song hai nhánh. Nhấn: nhánh 1 là cơ sở lý thuyết "
        "chuẩn (32 Mel + DCT-II), nhánh 2 là tối ưu tốc độ cho phần phŵn/StAndby.")

    # =====================================================================
    # PHẦN 1 — BẢN CHẤT TOÁN HỌC CỦA COSIN (SLIDE 3–6)
    # =====================================================================
    run("PHẦN 1\nBẢN CHẤT\nDCT-II", None, points=[
        "Mô hình giọng: L(f) = H(f) + S(f) — đường bao chậm vs gợn hài nhanh.",
        "32 bộ lọc tam giác Mel nén 257 bin FFT thành 32 năng lượng.",
        "Công thức cosin DCT-II phân rã theo dao động nhanh/chậm của hàm cos.",
        "Cái nào chứa F₀, cái nào chứa F1/F2/F3 — giữ 13 hệ số đầu.",
    ], notes="Mở đầu Phần 1 theo đúng mạch trình bày nhóm: nguồn-kênh → Mel → cosin → 13 hệ số.",
        expect_div=True, kicker="PHẦN 1")

    run("Mô hình giọng nói: vì sao là phép CỘNG",
        "Nguồn × Kênh trong miền tần số → logarit biến nhân thành cộng → L(f) = H(f) + S(f)",
        [("formula", "L(f) = H(f) · S(f)      →      log|L(f)| = log|H(f)| + log|S(f)| ≕ L(f) = H(f) + S(f)"),
         ("table", {
             "header": ["Thành phần", "Hình dạng trên log-phổ", "Chứa thông tin gì", "Giữ hay bỏ?"],
             "ratios": [0.95, 1.05, 1.15, 0.7],
             "rows": [
                 ["log-H(f) — đường bao", "Biến CHẬM, mượt", "Formants F1, F2, F3 — hình dạng ống phát âm (lưỡi, môi, khoang miệng) = chữ ký danh tính", "GIỮ"],
                 ["log-S(f) — chi tiết hài", "Biến NHANH, gợn cách đều", "F₀ (pitch) và chuỗi hài F₀, 2F₀, 3F₀… — thay đổi theo tâm trạng, nội dung câu", "BỎ"],
             ],
             "size": 10.5, "first_col_bold": True,
         }),
         ("callout", ("Đọc đúng bài toán: tách H khỏi S là bài toán 'tách thành phần biến chậm khỏi thành phần biến nhanh "
                      "trên log-phổ' — DCT-II làm điều đó bằng ma trận cosin, không cần lọc thông thường "
                      "(không chọn hệ số lọc, không dịch pha, không gây trễ).", "rose"))],
        "Trình bày đúng mạch: hai nguồn — dây thanh quản (nguồn) và khoang miệng (kênh), "
        "nhân sâu rồi log hóa để tách; đây là nền cho các slide sau.")

    run("32 bộ lọc tam giác Mel: nén 257 bin FFT",
        "Gom 257 bin (Δf = 31,25 Hz) vào 32 băng tam giác trên thang Mel — sau đó lấy log",
        [("figure", {"name": "mel", "width": 8.6}),
         ("bullets", [
             "Nén chọn lọc theo thính giác: băng thấp hẹp (vùng F₀, F1), băng cao rộng — màng nhĩ phân giải theo kiểu logarit.",
             "Làm mượt: sau gom + log, chuỗi hài chỉ còn là GỢN NHỎ phủ trên đường bao — chuẩn bị cho phép tách ở DCT.",
             "Nhấn mạnh: bộ Mel KHÔNG trực tiếp lọc F₀ khỏi formant — nhiệm vụ 'tách nhanh/chậm' thuộc về cosin ở bước DCT-II.",
         ])],
        "Chuyển từ phổ thô sang chuỗi 32 năng lượng. Lưu ý trung thực thật: Mel làm mượt, "
        "phép tách chính vẫn là DCT ở bước sau.")

    run("Công thức cosin DCT-II: phân rã theo nhanh/chậm",
        "Mỗi hệ số Cn là phép chiếu của log-phổ lên hàm cos(π·n·(2i+1)/64) — n tăng thì cosin dao động nhanh dần",
        [("formula", "C_n = Σ_{i=0..31} x_i · cos( π·n·(2i+1)/64 ),     n = 0, 1, …, 31"),
         ("formula", "Chuẩn hóa trực giao: nhân √(1/32) cho n = 0 và √(2/32) cho n ≥ 1 → ma trận trực chuẩn"),
         ("figure", {"name": "dct_basis", "width": 8.4}),
         ("bullets", [
             "n nhỏ → cosin dao động rất CHẬM trên 32 băng Mel: chỉ bắt hình dạng lớn của đường bao → chứa formants F1/F2/F3.",
             "n lớn → cosin dao động RẤT NHANH theo dãy băng kề nhau: chỉ bắt gợn nhỏ chu kỳ ngắn → chứa chu kỳ hài (F₀).",
             "Các hàm cosin với n khác nhau TRỰC GIAO: hệ số gần như không tương quan → nén được, cắt được, không loang thông tin.",
         ])],
        "Slide trung tâm trả lời thầy về 'công thức cosin'. Hai từ khóa: dao động chậm/nhanh theo bậc n và "
        "tính trực giao (khử tương quan). DCT-II = DFT của chuỗi đối xứng chẵn nên chỉ sinh phần thực.")

    run("Bẻ công thức từng bước: 32 thang Mel đi qua DCT-II",
        "Đường bao biến chậm hợp sóng cosin bậc đầu — năng lượng dồn về đầu; gợn F₀ biến nhanh dồn về C14–C15 rồi bị bỏ",
        [("figure", {"name": "dct_walkthrough", "width": 9.6}),
         ("bullets", [
             "(A) Sau Mel + log, vector x = H + S: đường bao H biến CHẬM (3 đỉnh formant F1/F2/F3); phủ trên là gợn S biến NHANH.",
             "(B) cosin n=1 trải mềm trên cả 32 băng: cùng nhịp với H nên tích vô hướng lớn; cosin n=15 dập dềnh nhanh — bắt trọn phần gợn.",
             "(C) Hệ số: C0–C12 giữ ~99,8% năng lượng demo (H hợp sóng bậc đầu); hai đỉnh gợn nằm đúng C14–C15 → cắt ở 13 hệ số là đủ.",
         ]),
         ("callout", ("Cách nói trước thầy: F1/F2/F3 biến thiên chậm nên khi đi qua cosin hợp với sóng ở các hệ số đầu, "
                      "năng lượng tập trung hết về đây; F₀ biến thiên nhanh nên dồn vào các hệ số sau (như C14–C15) — "
                      "và ta bỏ đi. Hình dựng trực tiếp từ công thức DCT-II (mô phỏng minh họa).", "rose"))],
        "Slide hình minh họa đường đi từng bước A/B/C. Lưu ý trung thực: vị trí đỉnh gợn phụ thuộc F₀ "
        "và vùng băng; nguyên tắc bất di bất dịch: chậm → bậc thấp, nhanh → bậc cao.")

    run("Giữ 13 hệ số: cái gì cần, cái gì bỏ",
        "Bậc thấp = đường bao (danh tính); bậc cao = chu kỳ hài (pitch/nhiễu) — cắt 19/32 hệ số mà gần như không mất danh tính",
        [("table", {
             "header": ["Nhóm hệ số", "Vai trò", "Quyết định"],
             "ratios": [0.8, 1.55, 0.7],
             "rows": [
                 ["C0", "Năng lượng tổng thể khung (âm lượng)", "Giữ"],
                 ["C1–C4", "Độ dốc phổ (spectral tilt) — trầm/bổng, độ mở miệng", "Giữ"],
                 ["C2–C7", "Vị trí và biên độ formant F1–F3 — chữ ký khoang phát âm", "Giữ"],
                 ["C8–C12", "Chi tiết đường bao bậc trung — hình thể quanh formant", "Giữ"],
                 ["C13 trở lên", "Dao động nhanh của log-phổ: chu kỳ hài F₀ + nhiễu cao tần", "BỎ (19 hệ số)"],
             ],
             "size": 10.5, "first_col_bold": True,
         }),
         ("bullets", [
             "Ví dụ số: người nói F₀ = 120 Hz → gai hài cách đều 120 Hz; quanh ~2 kHz cứ 2–3 băng Mel kề nhấp nhô theo chu kỳ hài → gợn bắt chủ yếu từ bậc ~C13 trở lên (hình demo: đỉnh C14–C15).",
             "Nén năng lượng: trên log-phổ tương quan cao (> 0,99 giữa hai băng kề), hơn 99% năng lượng nằm trong C0–C12 — cắt 19 hệ số chỉ mất phần 'biến nhanh' ít thông tin danh tính.",
         ]),
         ("callout", ("Câu chốt Phần 1: DCT-II là bước tách NGUỒN khỏi KÊNH ở mức toán học — hệ số bậc thấp giữ "
                      "đường bao F1/F2/F3 (cần), hệ số bậc cao chứa chu kỳ hài F₀ (bỏ). 13 hệ số/khung × 31 khung "
                      "= 403 đặc trưng cho CNN INT8.", "rose"))],
        "Bảng vai trò từng nhóm hệ số + ví dụ số F₀ = 120 Hz. Nếu thầy hỏi 'bỏ 19 hệ số có tiếc gì': "
        "không — đó chính là pitch mà bài toán danh tính muốn lược bỏ.")

    # =====================================================================
    # PHẦN 2 — PHÂN TÍCH HAI BÀI BÁO 2026 (SLIDE 7–10)
    # =====================================================================
    run("PHẦN 2\nĐỐI SÁNH\nHAI BÀI BÁO", None, points=[
        "Medur-2026 (Wiley IJIS, DOI 10.1155/int/2317323): quantized CNN KWS trên chính ESP32-S3-EYE.",
        "Sensors-2026 (MDPI, DOI 10.3390/s26133972): chuẩn mực đồng bộ PC ↔ MCU và đo nghẽn DSP.",
        "So sánh trực tiếp hai bài + đối chiếu với lớp giọng nói của dự án.",
    ], notes="Mở đầu Phần 2: hai công trình 2026 đại diện hai bài học — 'chọn kiến trúc theo latency đo "
             "được' và 'kiểm chứng đặc trưng nhưng nghẽn ở DSP'.",
        expect_div=True, kicker="PHẦN 2", fig="pipeline")

    run("Tổng quan hai bài báo chuẩn 2026",
        "Cùng MFCC 13 hệ số/khung @ 16 kHz, INT8, TFLM — khác bài toán và mức chặt chẽ kiểm chứng",
        [("table", {
             "header": ["Tiêu chí", "Medur-2026 (Wiley IJIS)", "Sensors-2026 (MDPI)"],
             "ratios": [0.75, 1.15, 1.15],
             "rows": [
                 ["Bài toán", "KWS 12 lớp Speech Commands → thực địa", "Phân loại 7 lớp âm học (6 loài + nền)"],
                 ["Nền tảng", "ESP32-S3-EYE — cùng dòng chip dự án", "Nano 33 BLE (Cortex-M4F)"],
                 ["Trích đặc trưng", "MFCC on-device; không mirror PC ⟷ MCU", "Mirror C++ on-device; cosine ≈ 1, MAE 7,3e-7"],
                 ["Mô hình", "Model 7: 684K tham số, 0,68 MB INT8", "MLP 312→64→32→7; 26,9 KB"],
                 ["Latency on-device", "145,19 ms (Model 7); BC-ResNet 365,22 ms", "303 ms tổng — MFCC 288,9 ms, TFLM chỉ 2,05 ms"],
                 ["Đánh giá", "10-fold CV speaker-independent + ngoài lab (phi bản ngữ, TTS)", "Source-isolated + multi-seed + ablation"],
                 ["Open-set", "lớp 'unknown' nhưng chưa đo tỷ lệ từ chối", "26,40% âm lạ nhầm nhãn với conf ≥ 0,9"],
             ],
             "size": 9.5, "first_col_bold": True,
         }),
         ("callout", ("Đặt chỗ: một bài 'chọn kiến trúc theo thời gian đo được' (Medur), một bài 'kiểm chứng "
                      "đặc trưng nhưng chính nó lại nghẽn ở DSP' (Sensors) — cùng nhắc tới bài học ego cho dự án.", "gray"))],
        "Bảng neo Phần 2 — lần đầu trong deck nêu cả hai công trình 2026 (trước đây dùng IJRASET-2025).")

    run("Bài báo 1 — Medur-2026 (Wiley IJIS): chiến lược lượng tử hóa KWS",
        "So sánh có kiểm soát trên thiết bị thật: Model 7 gọn + INT8 bền so sánh BC-ResNet trên ESP32-S3-EYE",
        [("bullets", [
            (0, "Đóng góp 1 — Kiến trúc đúng bài toán: 10 cấu hình CNN khảo sát trên PC → chọn Model 7 dưới 1 MB; "
                "say/unit-load tính toán trên thiết bị thay vì lý thuyết FLOP."),
            (0, "Đóng góp 2 — So sánh có kiểm soát với BC-ResNet trên cùng MFCC 13×50: BC-ResNet nhẹ hơn 142,9 kB "
                "nhưng tệ hơn 4,4 điểm sau lượng tử và chậm 2,5× — size không phải tiêu chuẩn duy nhất."),
            (0, "Đóng góp 3 — Kiểm chứng ngoài lab: người phi bản ngữ 81,82% (−8,2 điểm so lab 89,58%); "
                "giọng TTS 90,06% (~= lab) → nút thắt là độ biến thiên con người, không phải chip."),
            (0, "Đóng góp 4 — Bản dựng firmware khép và đo on-device: EON compiler + close-loop inference, "
                "cho phép đo trực tiếp thời gian suy luận 145,19 ms trên chính thiết bị target."),
         ]),
         ("callout", ("Bài học cho dự án: FP32→INT8 chỉ tốn < 0,5 điểm — đúng với 'Model 7 giữ nguyên "
                      "< 0,5 điểm' của bài; và nút thắt thực nằm ở đặc trưng, không phải phần suy luận.", "gray"))],
        "Đối chiếu bài 1 với dự án: cùng nền ESP32-S3, cùng INT8, cùng TFLM — bài 1 là bài đối chiếu "
        "phần cứng gần nhất.")

    run("Bài báo 2 — Sensors-2026 (MDPI): chuẩn mực đồng bộ & nút thắt DSP",
        "Mirror C++ đạt cosine ≈ 1 / MAE 7,28×10⁻⁷; rồi chính nó tiết lộ nghẽn: MFCC 288,9 ms vs TFLM 2,05 ms",
        [("table", {
             "header": ["Tinh hoa", "Số liệu công bố", "Ý nghĩa cho dự án"],
             "ratios": [1.0, 1.05, 1.15],
             "rows": [
                 ["Mirror C++ on-device", "cosine 1,0000; MAE 7,28×10⁻⁷", "Đặc trưng PC = MCU là điều kiện tiên quyết để só số trung thực"],
                 ["Đo phân mảnh thời gian", "MFCC 288,9 ms / 302,6 ms (~95,5%)", "Trích đặc trưng là nút thắt TINYML lớn hơn nhiều mạng nơ-ron (2,05 ms)"],
                 ["Đo công suất", "0,78–0,83 W; tự chủ pin 7,6–8,0 h", "Chuẩn đối chiếu phần cứng biên — thiếu hướng này ở dự án"],
                 ["Open-set thành thật", "26,40% âm lạ conf ≥ 0,9 (39,61% nhầm)", "Rủi ro bảo mật thực tế mà dự án phải chống bằng lớp 2"],
             ],
             "size": 9.5, "first_col_bold": True,
         }),
         ("callout", ("Điều đáng chú ý nhất: bài Sensors phát hiện nghẽn ở đặc trưng nhưng móvil Cortex-M4F — "
                      "dùng LX7 + esp-dsp làm ESP32-S3 của nhóm có thể ép FFT 512 xuống 5–10 ms (~30× nhanh hơn). "
                      "Dự án đã hiện thực hóa chính Future work mà 2 bài báo không làm.", "rose"))],
        "Slide 9 theo outline: hai tinh hoa (mirror C++, đo nghẽn DSP) + cảnh báo open-set + "
        "cách dự án phản hồi từng tinh hoa.")

    run("Bảng đối chiếu 3 chiều: dự án vs hai bài báo 2026",
        "8 tiêu chí kỹ thuật — mỗi dòng là một điểm dự án có thể trả lời được ngay trước hội đồng",
        [("table", {
             "header": ["Tiêu chí", "Dự án ESP32-S3", "Medur-2026", "Sensors-2026"],
             "ratios": [0.85, 1.05, 1.05, 1.05],
             "rows": [
                 ["Vi điều khiển", "ESP32-S3 LX7 240 MHz (cùng chip Medur)", "ESP32-S3-EYE LX7", "Cortex-M4F"],
                 ["Trích đặc trưng on-device", "FFT 512 + 32 Mel + DCT-II (EI)", "MFCC on-device", "Mirror C++ ✅ chuẩn nhất"],
                 ["Tăng tốc phần cứng", "esp-dsp SIMD/PIE → FFT ~5–10 ms", "không tối ưu DSP", "không tối ưu (289 ms)"],
                 ["Mô hình INT8", "5,8 KB / 978 tham số (Conv1D)", "0,68 MB / 684K", "26,9 KB MLP"],
                 ["Latency suy luận", "1–3 ms (EON)", "145,19 ms", "2,05 ms"],
                 ["Latency DSP", "chưa đo chính thức", "không tách", "288,9 ms (~95,5%)"],
                 ["Độ chính xác", "83,33% (validation nội bộ)", "89,58% lab / 81,82% thực địa", "98,28%"],
                 ["Chống open-set", "Lớp 2 khuôn mặt cùng phiên 10 s", "chưa đo", "công bố mở 26,4% conf ≥ 0,9"],
             ],
             "size": 9.5, "first_col_bold": True,
         }),
         ("callout", ("Ba điểm sáng nổi bật: (1) dự án cùng nền chip với bài 1 nhưng nhanh hơn 30–50× ở suy luận; "
                      "(2) chuẩn matching đặc trưng bám bài 2 nhưng chưa có cosine/MAE; (3) chống open-set bằng "
                      "kiến trúc 2 lớp mà cả hai bài đều chưa có.", "rose"))],
        "Slide 10 theo outline: bảng 8 tiêu chí kỹ thuật đối chiếu — khối trung tâm của Phần 2, "
        "ăn khớp từng dòng với outline báo cáo.")

    # =====================================================================
    # PHẦN 3 — HIỆN THỰC HÓA TRÊN ESP32-S3 & KẾT QUẢ (SLIDE 11–14)
    # =====================================================================
    run("PHẦN 3\nESP32-S3\n& KẾT QUẢ", None, points=[
        "Khắc phục nút thắt DSP bằng SIMD/PIE LX7: FFT 512 chỉ 5–10 ms (~30× nhanh hơn Cortex-M4F).",
        "Quản trị bộ nhớ thương mại: Tensor Arena 40 KB + Audio Buffer 32 KB đặt trong 8 MB PSRAM.",
        "Kiến trúc xác thực kép Voice L1 + FaceID L2 hoá giải rủi ro open-set 26,4% của bài Sensors.",
        "Kết quả thực nghiệm: 83,33% / RAM suy luận −34,1% / 1–3 ms / INT8 5,8–12 KB.",
    ], notes="Mở đầu Phần 3: từ bài học các bài báo tới việc hiện thực hóa và kết quả dự án.",
        expect_div=True, kicker="PHẦN 3")

    run("Xử lý nút thắt DSP và bộ nhớ — vượt Future work của hai bài báo",
        "SIMD/PIE trên nhân kép LX7 + psram overlay: khối DSP hết 5–10 ms; 512 KB SRAM giữ nguyên cho FreeRTOS.Wi-Fi",
        [        ("cols",
             [("lead", "Khắc phục nút thắt DSP (bài Sensors 289 ms)"),
              ("bullets", [
                  "esp-dsp chạy trên chính SIMD/PIE LX7: FFT 512 thực đo chỉ 5–10 ms — nhanh ~30× so với khối DSP M4F của bài báo.",
                  "Nhánh firmware dùng Approximate Log-Mel bỏ FFT/DCT: tốn ít hơn nữa, phù hợp STANDBY.",
                  "Dự án đã làm chính Future-work mà hai bài báo dừng lại.",
              ])],
             [("lead", "Quản trị bộ nhớ 'thương mại hóa'"),
              ("bullets", [
                  "Tensor Arena 40 KB + Audio Buffer 32 KB đặt vào 8 MB PSRAM ngoài.",
                  "Giữ 512 KB SRAM nội trọn vẹn cho FreeRTOS, WiFi và Web Server.",
                  "Kiến trúc phân tầng như bài Medur-2026 nhưng tận dụng PSRAM lớn hơn.",
              ])],
             0.52),
         ("callout", ("Cách nói trước hội đồng: bài báo 2 báo MFCC chậm 288,9 ms trên M4F — trên chính nền "
                      "ESP32-S3 của dự án, khối DSP này chỉ ngốn 5–10 ms, đủ để chạy trong vòng lặp 100 ms "
                      "mà không đụng internet, không đụng PSRAM band-width.", "rose"))],
        "Slide 11 theo outline: hai đóng góp — tăng tốc DSP bằng SIMD/PIE và quản trị bộ nhớ bằng PSRAM "
        "như bài Medur-2026.")

    run("Kiến trúc xác thực kép — hoá giải rủi ro open-set",
        "Sensors-2026 công bố 26,40% âm lạ vượt ngưỡng 0,9; Medur-2026 cũng gặp False Acceptance trong KWS",
        [("chain", "VOICE KWS (θ ≥ 0,70) → WAKE-UP TRIGGER → cửa sổ 10 giây → FACE L2 (MobileFaceNet, ESP-DL) → MỞ CỬA"),
         ("bullets", [
             (0, "Vai trò Voice L1: chỉ BỘ ĐÁNH THỨC (wake-up trigger) — không mở cửa khi giọng vượt ngưỡng."),
             (0, "Vai trò FaceID L2: chốt xác thực — chỉ mở khi cả hai lớp cùng quyết định trong 1 phiên 10 giây."),
             (0, "Vì sao giải quyết được open-set 26,4%: kẻ tấn công phải vượt CẢ HAI biometric độc lập — xác suất "
                 "song song giảm mạnh; phòng nên tái hiện replay một lớp vẫn vô nghĩa vì phiên 10 s hết."),
             (1, "Bonus tiết kiệm điện: camera chỉ bật khi Voice L1 đã qua — duty-cycling tự động."),
         ]),
         ("callout", ("Đây là câu trả lời trực tiếp câu hỏi 'nếu kẻ lạ thích thì sao' — Voice Language L1 có thể "
                      "bị qua (26,4% theo bài báo), nhưng FaceID L2 cùng phiên thì không; cả hai phải cùng lúc.", "rose"))],
        "Slide 12 theo outline: kiến trúc 2 lớp — Voice L1 là trigger, FaceID L2 là chốt chính, "
        "cùng phiên 10 giây chống replay từng lớp.")

    run("Kết quả thực nghiệm toàn diện của dự án",
        "4 thẻ chỉ số: accuracy 83,33% / RAM −34,1% / 1–3 ms / 5,8 KB — với phân tích chi phí lỗi bất đối xứng",
        [("cols",
             [("lead", "4 chỉ số chính"),
              ("table", {
                  "header": ["Chỉ số", "Giá trị"],
                  "ratios": [0.85, 1.0],
                  "rows": [
                      ["Accuracy INT8", "83,33% (F1 0,84; suy hao 0)"],
                      ["Tiết kiệm RAM suy luận", "5.208 → 3.432 B (−34,1%)"],
                      ["Latency suy luận AI", "1–3 ms (budget 100 ms)"],
                      ["Kích thước mô hình", "5,8 KB (Conv1D) / 12 KB (Conv2D)"],
                  ],
                  "size": 10.0, "first_col_bold": True,
              })],
             [("lead", "Chi phí lỗi bất đối xứng"),
              ("bullets", [
                  "False Positive (mở cửa nhầm) là lỗi nghiêm trọng — triệt tiêu tối đa.",
                  "False Negative (chưa mở ngay) chỉ gây bất tiện nhỏ — nói lại là được.",
                  "Ngưỡng θ = 0,70 thắt chặt để ưu tiên FP → bảo vệ tài sản khóa cửa.",
                  "Voice L1 là lớp lọc 1; FaceID L2 bảo mật sau cùng trong phiên 10 s — hợp lý về mặt an ninh lẫn điện năng.",
              ])],
             0.52),
         ("callout", ("Trả lời trung thực: đây là validation nội bộ — công bố 'validation nội bộ 83,33%' chứ "
                      "không vượt quyền gọi là kết quả kiểm thử độc lập; hướng mở bộ kiểm thử chuẩn ở 6.1 "
                      "báo cáo khuyến nghị.", "gray"))],
        "Slide 13 theo outline: 4 thẻ chỉ số chủ chốt + phân tích chi phí lỗi bất đối xứng "
        "(FP nghiêm trọng hơn FN) + trung thực phạm vi đánh giá.")

    # =====================================================================
    # SLIDE 14 — KẾT
    # =====================================================================
    divider(prs, page_field, "KẾT", "TỔNG KẾT &\nTHẢO LUẬN — Q&A", [
        "Bản chất cosin: DCT-II phân rã log-phổ theo dao động nhanh/chậm — giữ 13 hệ số bậc thấp = chữ ký danh tính.",
        "Bài học 2026: chọn kiến trúc theo latency đo được (Medur) và chuẩn mực đồng bộ PC↔MCU (Sensors).",
        "Khắc phục nút thắt DSP: SIMD/PIE LX7 ép FFT 512 từ ~289 ms (M4F) xuống 5–10 ms — bài học không bỏ Future work.",
        "Xác thực kép Voice + FaceID cùng phiên 10 giây hoá giải open-set 26,4%.",
    ], notes="Kết: 4 dòng chốt — bản chất DCT-II, bài học 2026, khắc phục nút thắt DSP, xác thực kép; "
             "sau đó mời hội đồng đặt câu hỏi — sẵn sàng đáp phần phản biện.", fig="summary", fig_first=True)

    base.unify_divider_titles()
    prs.save(OUT)
    print("\nĐã ghi:", OUT)
    bad = [(t, s) for t, s in report if s is not None and s < -0.05]
    print("Tổng số slide:", len(prs.slides), "| slide tràn khung:", len(bad))
    for t, s in bad:
        print("   !", t, "%.2f in" % s)


if __name__ == "__main__":
    main()
