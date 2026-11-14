# -*- coding: utf-8 -*-
"""
render_diagrams.py — Vẽ 4 sơ đồ kiến trúc của dự án edge-ai thành ảnh PNG
(để chèn vào báo cáo Word và slide PowerPoint, hỗ trợ tiếng Việt)
Cách dùng: python render_diagrams.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

OUT = os.path.dirname(os.path.abspath(__file__))

# Font hỗ trợ tiếng Việt trên Windows
plt.rcParams["font.family"] = ["Segoe UI", "Arial", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

C_INPUT = "#4CAF50"   # xanh lá - đầu vào
C_ESP   = "#2196F3"   # xanh dương - ESP32
C_OUT   = "#FF9800"   # cam - đầu ra
C_FAIL  = "#F44336"   # đỏ - thất bại
C_OK    = "#00C853"   # xanh - thành công
C_BOX   = "#FFFFFF"
C_LINE  = "#455A64"


def box(ax, x, y, w, h, text, fc, fontsize=10.5, bold=True, text_color="white"):
    """Vẽ hộp bo tròn với chữ căn giữa."""
    p = FancyBboxPatch((x - w/2, y - h/2), w, h,
                       boxstyle="round,pad=0.02,rounding_size=0.08",
                       linewidth=1.4, edgecolor="#263238", facecolor=fc)
    ax.add_patch(p)
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize,
            fontweight="bold" if bold else "normal", color=text_color, linespacing=1.4)


def arrow(ax, x1, y1, x2, y2, label="", color=C_LINE, fontsize=9,
          label_dxy=(0.0, 0.06), style="-|>"):
    """Vẽ mũi tên có nhãn."""
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                        mutation_scale=16, linewidth=1.6, color=color,
                        shrinkA=2, shrinkB=2)
    ax.add_patch(a)
    if label:
        mx, my = (x1 + x2) / 2 + label_dxy[0], (y1 + y2) / 2 + label_dxy[1]
        ax.text(mx, my, label, ha="center", va="bottom", fontsize=fontsize,
                color=color, style="italic",
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.85))


def new_ax(w, h):
    fig, ax = plt.subplots(figsize=(w, h), dpi=150)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    return fig, ax


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Da tao:", name)


# ============================================================
# HÌNH 1 — KIẾN TRÚC TỔNG THỂ
# ============================================================
def fig1_architecture():
    fig, ax = new_ax(10, 6.2)

    # Khung nhóm
    for x, y, w, h, label, col in [
        (1.55, 5.0, 2.7, 8.6, "ĐẦU VÀO", C_INPUT),
        (5.0, 5.0, 3.1, 9.2, "ESP32-S3 (FreeRTOS)", C_ESP),
        (8.45, 5.0, 2.7, 8.6, "ĐẦU RA", C_OUT),
    ]:
        ax.add_patch(FancyBboxPatch((x - w/2, y - h/2), w, h,
                     boxstyle="round,pad=0.03,rounding_size=0.1",
                     linewidth=2.2, edgecolor=col, facecolor=col + "14"))
        ax.text(x, y + h/2 - 0.45, label, ha="center", va="center",
                fontsize=11.5, fontweight="bold", color=col)

    # Đầu vào
    box(ax, 1.55, 6.6, 2.1, 1.5, "📷 Camera\nOV2640\n(640×480 JPEG)", C_INPUT)
    box(ax, 1.55, 3.2, 2.1, 1.5, "🎙️ Micro\nINMP441\n(I2S, 16 kHz)", C_INPUT)

    # ESP32
    box(ax, 5.0, 7.6, 2.6, 1.35, "voice_auth_task\nAI giọng nói CNN\n(chạy liên tục)", C_ESP)
    box(ax, 5.0, 5.3, 2.6, 1.35, "face_task\nAI khuôn mặt\n(ngủ chờ đánh thức)", C_ESP)
    box(ax, 5.0, 3.0, 2.6, 1.35, "state_machine\nNHÀ ĐIỀU PHỐI", "#0D47A1")
    box(ax, 5.0, 1.1, 2.6, 1.1, "Web Server\n:80 — UI + API", "#5C6BC0")

    # Đầu ra
    box(ax, 8.45, 5.8, 2.1, 1.4, "🚪 Servo\nmở/đóng cửa", C_OUT)
    box(ax, 8.45, 3.4, 2.1, 1.4, "💡 LED WS2812\nbáo trạng thái", C_OUT)

    # Mũi tên
    arrow(ax, 2.65, 3.2, 3.68, 7.0, "âm thanh")
    arrow(ax, 2.65, 6.6, 3.68, 5.6, "khung hình")
    arrow(ax, 6.32, 7.4, 6.32, 6.0, "VOICE_OK\n≥ 0.7", C_OK, label_dxy=(0.85, -0.15))
    arrow(ax, 5.0, 6.62, 5.0, 6.0, "đánh thức\n(semaphore)", C_LINE, label_dxy=(1.15, -0.3))
    arrow(ax, 6.32, 5.1, 6.32, 3.7, "FACE_OK /\ntimeout 10s", C_OK, label_dxy=(0.95, 0.1))
    arrow(ax, 5.9, 2.5, 7.6, 5.2, "mở cửa", C_OUT, label_dxy=(-0.65, 0.0))
    arrow(ax, 6.32, 3.0, 7.38, 3.4, "trạng thái", C_OUT, label_dxy=(0.0, 0.12))
    arrow(ax, 5.0, 1.68, 5.0, 2.3, style="<|-|>", label="điều khiển\n& truy vấn", label_dxy=(1.0, -0.25))

    ax.set_title("Hình 1 — Kiến trúc tổng thể hệ thống (Edge AI trên ESP32-S3)",
                 fontsize=13, fontweight="bold", pad=14)
    save(fig, "hinh1_kien_truc.png")


# ============================================================
# HÌNH 2 — MÁY TRẠNG THÁI
# ============================================================
def fig2_state_machine():
    fig, ax = new_ax(10, 4.6)

    states = [
        (1.35, 5.0, "STANDBY", "#607D8B", "🎙️ Mic lắng nghe\nFaceID TẮT — LED tắt"),
        (3.85, 5.0, "VOICE_\nTRIGGERED", C_ESP, "🟢 LED xanh\nđánh thức FaceID"),
        (6.35, 5.0, "FACE_AUTH", "#0D47A1", "🟢 Chụp & so sánh\ncửa sổ 10 giây"),
        (8.75, 5.0, "DOOR_OPEN", C_OK, "🚪 Servo mở 90°\nnháy xanh 3 lần"),
    ]
    for x, y, t1, col, t2 in states:
        box(ax, x, y, 2.15, 2.0, t1 + "\n\n" + t2, col, fontsize=9.5)
        ax.text(x, y - 1.55, t1.replace("\n", ""), ha="center", fontsize=9,
                color=col, fontweight="bold")

    arrow(ax, 2.45, 5.5, 2.75, 5.5, "giọng khớp\n≥ 0.7", C_OK, label_dxy=(0, 0.55))
    arrow(ax, 4.95, 5.5, 5.25, 5.5, "được kích hoạt", C_LINE, label_dxy=(0, 0.5))
    arrow(ax, 7.45, 5.5, 7.65, 5.5, "mặt khớp\n≥ 0.5", C_OK, label_dxy=(0, 0.5))

    # Nhánh thất bại vòng về STANDBY (cong phía trên)
    a = FancyArrowPatch((6.35, 6.05), (1.35, 6.05), connectionstyle="arc3,rad=-0.35",
                        arrowstyle="-|>", mutation_scale=16, linewidth=1.6, color=C_FAIL)
    ax.add_patch(a)
    ax.text(3.85, 8.15, "hết 10 giây / người lạ / giọng trượt → quay về STANDBY",
            ha="center", fontsize=9.5, color=C_FAIL, style="italic")

    # Vòng tự đóng cửa (cong phía dưới)
    a = FancyArrowPatch((8.75, 3.95), (1.35, 3.95), connectionstyle="arc3,rad=0.3",
                        arrowstyle="-|>", mutation_scale=16, linewidth=1.6, color=C_LINE)
    ax.add_patch(a)
    ax.text(5.0, 1.85, "sau 5 giây → tự đóng cửa → STANDBY (chu trình mới)",
            ha="center", fontsize=9.5, color=C_LINE, style="italic")

    ax.set_title("Hình 2 — Máy trạng thái 4 trạng thái (mọi nhánh đều về STANDBY)",
                 fontsize=13, fontweight="bold", pad=14)
    save(fig, "hinh2_may_trang_thai.png")


# ============================================================
# HÌNH 3 — PIPELINE GIỌNG NÓI
# ============================================================
def fig3_voice_pipeline():
    fig, ax = new_ax(10, 4.2)

    steps = [
        ("🎙️ Thu âm\n1s @ 16kHz\ngain ×4", C_INPUT),
        ("🧹 VAD lọc nhiễu\nRMS > 30\npeak > 100", "#00897B"),
        ("📊 MFCC 32×13\nFFT 512 + Hann\nlog năng lượng", C_ESP),
        ("🔢 Quantize INT8\nscale/zero_point\ntừ model", "#5C6BC0"),
        ("🧠 CNN ~12KB\nConv→Pool\n→FC→Logistic", "#7E57C2"),
    ]
    xs = [1.1, 3.05, 5.0, 6.95, 8.9]
    for (txt, col), x in zip(steps, xs):
        box(ax, x, 5.0, 1.85, 2.6, txt, col, fontsize=9)
    for i in range(len(xs) - 1):
        arrow(ax, xs[i] + 0.95, 5.0, xs[i+1] - 0.95, 5.0)

    # Quyết định
    box(ax, 8.9, 1.7, 2.0, 1.2, "🎯 Score ≥ 0.7 ?", "#F57F17", fontsize=10)
    arrow(ax, 8.9, 3.65, 8.9, 2.35)
    box(ax, 5.6, 1.7, 2.4, 1.2, "✅ VOICE_OK\nkích hoạt FaceID", C_OK, fontsize=9.5)
    box(ax, 2.3, 1.7, 2.4, 1.2, "❌ Trượt — LED đỏ\nvề STANDBY", C_FAIL, fontsize=9.5)
    arrow(ax, 7.85, 1.7, 6.85, 1.7, "đạt", C_OK, label_dxy=(0, 0.1))
    arrow(ax, 7.85, 1.55, 3.55, 1.7, "không đạt", C_FAIL, label_dxy=(1.9, 0.35))

    ax.set_title("Hình 3 — Pipeline nhận dạng giọng nói (từ sóng âm đến quyết định)",
                 fontsize=13, fontweight="bold", pad=14)
    save(fig, "hinh3_voice_pipeline.png")


# ============================================================
# HÌNH 4 — PIPELINE KHUÔN MẶT
# ============================================================
def fig4_face_pipeline():
    fig, ax = new_ax(10, 4.2)

    box(ax, 1.3, 6.5, 2.0, 1.6, "📷 Khung VGA\n640×480 JPEG", C_INPUT, fontsize=9.5)
    box(ax, 4.0, 6.5, 2.3, 1.6, "🔍 Detector\nMSRMNP tìm mặt", C_ESP, fontsize=9.5)
    box(ax, 7.0, 6.5, 2.2, 1.4, "✂️ Cắt vùng mặt\n(keypoints)", "#0D47A1", fontsize=9.5)
    box(ax, 8.8, 3.6, 2.1, 1.6, "🧠 MobileFaceNet\nvector đặc trưng", "#7E57C2", fontsize=9.5)
    box(ax, 5.6, 3.6, 2.5, 1.6, "💾 So cosine với\n10 người × 5 mẫu\n(SPIFFS database)", "#5C6BC0", fontsize=9)
    box(ax, 2.4, 3.6, 2.0, 1.6, "🎯 sim ≥ 0.5 ?", "#F57F17", fontsize=10)

    arrow(ax, 2.35, 6.5, 2.85, 6.5)
    arrow(ax, 5.15, 6.5, 5.9, 6.5)
    arrow(ax, 8.1, 6.5, 8.35, 4.45, style="-|>")
    arrow(ax, 7.75, 3.6, 6.9, 3.6)
    arrow(ax, 4.35, 3.6, 3.45, 3.6)

    box(ax, 2.4, 1.2, 2.6, 1.2, "✅ Nhận ra: tên →\nmở cửa (nếu FACE_AUTH)", C_OK, fontsize=9.5)
    box(ax, 6.6, 1.2, 2.6, 1.2, "❌ Người lạ / không mặt\n→ reset Unknown", C_FAIL, fontsize=9.5)
    arrow(ax, 2.15, 2.8, 2.35, 1.85, "đạt", C_OK, label_dxy=(0.3, 0))
    arrow(ax, 2.7, 2.75, 6.1, 1.85, "dưới ngưỡng", C_FAIL, label_dxy=(-1.0, 0.45))

    ax.set_title("Hình 4 — Pipeline nhận dạng khuôn mặt (dò tìm trước, nhận dạng sau)",
                 fontsize=13, fontweight="bold", pad=14)
    save(fig, "hinh4_face_pipeline.png")


if __name__ == "__main__":
    fig1_architecture()
    fig2_state_machine()
    fig3_voice_pipeline()
    fig4_face_pipeline()
    print("Hoàn tất 4 hình trong:", OUT)
