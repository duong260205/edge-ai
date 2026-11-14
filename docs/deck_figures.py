# -*- coding: utf-8 -*-
"""
deck_figures.py — Vẽ các hình minh họa cho slide phản biện
(BAO_CAO_PHAN_BIEN_VOICE_AUTH_SLIDES.pptx), dùng số liệu thật của dự án 945012.

Nguyên tắc:
- Mọi hình dùng ĐÚNG số liệu đọc từ REST API Edge Impulse của dự án (kích thước model,
  RAM/ROM, độ trễ, confusion matrix, F1, AUC) hoặc là toán học thuần (DCT-II, cửa sổ Hann,
  thang Mel) — không có "dữ liệu đo" nào được bịa ra.
- Hình mang tính minh họa toán học (mel, dct, framing, wilson) được ghi rõ trong chú thích.
- Bảng màu và font trùng với template DSP (đỏ HUST #C02034, Times New Roman).

Kết quả ghi vào docs/_deck_fig/*.png (cache; chỉ vẽ lại khi thiếu hoặc khi force=True).

Dùng: python deck_figures.py           # vẽ tất cả
      python deck_figures.py --force   # vẽ lại từ đầu
"""

import math
import os
import sys

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
FIGDIR = os.path.join(HERE, "_deck_fig")

RED = "#C02034"
RED_DARK = "#8E1626"
DARK = "#212121"
GRAY = "#5A5A5A"
LIGHT = "#FCEFF1"
BLUE = "#14144B"
GOLD = "#7A5B00"
GRID = "#DCDCDE"

plt.rcParams.update({
    "font.family": "Times New Roman",
    "font.size": 8.5,
    "axes.edgecolor": GRAY,
    "axes.labelcolor": DARK,
    "axes.titlesize": 9.5,
    "xtick.color": DARK,
    "ytick.color": DARK,
    "text.color": DARK,
    "figure.facecolor": "white",
    "axes.grid": False,
    "savefig.facecolor": "white",
})

DPI = 300


def _save(fig, name):
    os.makedirs(FIGDIR, exist_ok=True)
    path = os.path.join(FIGDIR, name + ".png")
    fig.savefig(path, dpi=DPI, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    print("  [hình] %-16s %s" % (name, os.path.basename(path)))
    return path


# ---------------------------------------------------------------------------
# Toán học dùng chung
# ---------------------------------------------------------------------------
def mel(f):
    return 2595.0 * np.log10(1.0 + np.asarray(f, dtype=float) / 700.0)


def imel(m):
    return 700.0 * (10.0 ** (np.asarray(m, dtype=float) / 2595.0) - 1.0)


MEL_LO, MEL_HI = float(mel(80.0)), float(mel(8000.0))
N_BANDS = 32
EDGES_MEL = np.linspace(MEL_LO, MEL_HI, N_BANDS + 2)     # 34 mép
EDGES_HZ = imel(EDGES_MEL)


def mel_weights(k, edges=None):
    """Trọng số H_i(f_k) của 32 bộ lọc tam giác tại bin k (Δf = 31,25 Hz)."""
    f = k * 31.25
    return np.where((f >= edges[:-2]) & (f <= edges[1:-1]),
                    (f - edges[:-2]) / (edges[1:-1] - edges[:-2]),
                    np.where((f > edges[1:-1]) & (f <= edges[2:]),
                             (edges[2:] - f) / (edges[2:] - edges[1:-1]), 0.0))


def wilson(k, n, z=1.96):
    """Khoảng Wilson 95 % (có hiệu chỉnh liên tục) cho tỷ lệ k/n → (thấp, cao)."""
    p = k / n
    denom = 2 * (n + z * z)
    centre = 2 * n * p + z * z
    half = z * math.sqrt(z * z - 2 - 1.0 / n + 4 * p * (n * (1 - p) + 1))
    return (centre - 1 - half) / denom, (centre + 1 - half) / denom


# ---------------------------------------------------------------------------
# 1. Pipeline end-to-end (slide "Chuỗi tiền xử lý liền mạch")
# ---------------------------------------------------------------------------
def fig_pipeline():
    boxes = [
        ("Mic INMP441\nI2S @16 kHz", "24-bit → int16"),
        ("Input\n1000 ms", "16 000 mẫu"),
        ("Khử DC\nx' = x − μ", "chuẩn hóa max_val"),
        ("Framing\n512 / 512", "31 khung × 32 ms"),
        ("Hann + FFT 512", "257 bin · Δf 31,25 Hz"),
        ("Mel 32 tam giác", "80–8000 Hz · ln(E+ε)"),
        ("DCT-II 32 → 13", "403 = 31 × 13"),
        ("CNN INT8", "978 tham số"),
        ("P(target) ≥ θ", "θ = 0,70"),
    ]
    fig, ax = plt.subplots(figsize=(9.9, 1.46))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    n = len(boxes)
    pad = 0.012
    w = (1 - pad * (n - 1)) / n

    for i, (label, sub) in enumerate(boxes):
        x = i * (w + pad)
        hot = i >= 3 and i <= 5          # khối DSP — tô đậm
        y, h = 0.30, 0.44
        ax.add_patch(FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.004,rounding_size=0.02",
            linewidth=0.9, edgecolor=RED_DARK if hot else GRAY,
            facecolor=RED if hot else "white", zorder=3))
        ax.text(x + w / 2, y + h * 0.62, label, ha="center", va="center",
                fontsize=7.0, fontweight="bold", zorder=4,
                color="white" if hot else DARK, linespacing=1.25)
        ax.text(x + w / 2, y + h * 0.20, sub, ha="center", va="center",
                fontsize=6.0, zorder=4, color="white" if hot else GRAY)
        if i < n - 1:
            ax.add_patch(FancyArrowPatch(
                (x + w + 0.001, y + h / 2), (x + w + pad - 0.001, y + h / 2),
                arrowstyle="-|>", mutation_scale=7, linewidth=0.9,
                color=RED_DARK, zorder=2))

    # dải chi phí: DSP ~82 % và mạng ~18 %
    ax.add_patch(Rectangle((3 * (w + pad), 0.10), 3 * w + 2 * pad, 0.13,
                           facecolor=LIGHT, edgecolor=RED_DARK, linewidth=0.7))
    ax.text(3 * (w + pad) + (3 * w + 2 * pad) / 2, 0.165,
            "DSP ≈ 71,4 K MAC  (≈ 82 % ngân sách tính toán)",
            ha="center", va="center", fontsize=6.8, fontweight="bold", color=RED_DARK)
    ax.add_patch(Rectangle((7 * (w + pad), 0.10), w, 0.13,
                           facecolor=LIGHT, edgecolor=RED_DARK, linewidth=0.7))
    ax.text(7 * (w + pad) + w / 2, 0.165, "≈ 16,1 K\nMAC (18 %)", ha="center",
            va="center", fontsize=5.8, color=RED_DARK, linespacing=1.1)
    ax.text(0.5, 0.95, "Chuỗi biến đổi liên tục từ mẫu I2S đến quyết định xác thực",
            ha="center", va="center", fontsize=8.5, fontweight="bold", color=DARK)
    return _save(fig, "pipeline")


# ---------------------------------------------------------------------------
# 2. Ngân sách MAC: DSP vs mạng nơ-ron (PHẦN 1)
# ---------------------------------------------------------------------------
def fig_mac():
    nn = [("Conv1D₁ (31×3×13×8)", 9672), ("Conv1D₂ (16×3×8×16)", 6144),
          ("Dense (128×2)", 256)]
    dsp = 31 * 2304
    total = dsp + sum(v for _, v in nn)

    fig, ax = plt.subplots(figsize=(7.3, 2.15))
    ys = [0.55, 0.0]
    ax.barh(ys[0], dsp, height=0.34, color=RED, edgecolor=RED_DARK, linewidth=0.7)
    ax.text(dsp / 2, ys[0], "DSP MFCC — 31 khung × FFT-512\n≈ 71.424 MAC  (82 %)",
            ha="center", va="center", color="white", fontsize=8, fontweight="bold",
            linespacing=1.3)

    left = 0.0
    shades = ["#8E1626", "#B4515F", "#D7949E"]
    for (lab, val), c in zip(nn, shades):
        ax.barh(ys[1], val, left=left, height=0.34, color=c,
                edgecolor="white", linewidth=0.8)
        left += val
    ax.text(left / 2, ys[1] + 0.30, "Mạng CNN INT8 ≈ 16.072 MAC (18 %)",
            ha="center", va="bottom", fontsize=7.4, color=RED_DARK, fontweight="bold")
    ax.annotate("9.672 MAC · 60 %\ncủa mạng", xy=(4836, 0.34), xytext=(2600, 0.78),
                fontsize=6.8, color=DARK, ha="left",
                arrowprops=dict(arrowstyle="-", color=GRAY, linewidth=0.7))
    ax.annotate("6.144 MAC (38 %)", xy=(9672 + 3072, 0.34), xytext=(8600, 0.78),
                fontsize=6.8, color=DARK, ha="left",
                arrowprops=dict(arrowstyle="-", color=GRAY, linewidth=0.7))

    ax.set_xlim(0, total * 1.02)
    ax.set_ylim(-0.32, 1.05)
    ax.set_yticks([ys[0], ys[1]])
    ax.set_yticklabels(["Toàn hệ\n(on-device)", "Chi tiết\nmạng CNN"], fontsize=7.6)
    ax.set_xlabel("MAC mỗi lần suy luận trên một cửa sổ 1 giây", fontsize=8)
    ax.set_xticks([0, 20000, 40000, 60000, 80000])
    ax.set_xticklabels(["0", "20 K", "40 K", "60 K", "80 K"], fontsize=7.6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(GRAY)
    ax.spines["bottom"].set_color(GRAY)
    ax.tick_params(length=2.5)
    return _save(fig, "mac")


# ---------------------------------------------------------------------------
# 3. 32 bộ lọc tam giác Mel (PHẦN 2)
# ---------------------------------------------------------------------------
def fig_mel():
    fig, (ax, ax2) = plt.subplots(
        1, 2, figsize=(7.3, 2.35), gridspec_kw={"width_ratios": [2.15, 1.0], "wspace": 0.32})

    f = np.linspace(60, 8200, 4000)
    for i in range(N_BANDS):
        lo, ce, hi = EDGES_HZ[i], EDGES_HZ[i + 1], EDGES_HZ[i + 2]
        tri = np.where(f <= ce, np.maximum((f - lo) / (ce - lo), 0.0),
                       np.maximum((hi - f) / (hi - ce), 0.0))
        hot = i in (0, 4, 9, 15, 21, 27, 31)
        ax.plot(f, np.clip(tri, 0, 1), linewidth=1.25 if hot else 0.55,
                color=RED if hot else "#D9A9B0", zorder=3 if hot else 2)
    ax.set_xlim(0, 8300)
    ax.set_ylim(0, 1.16)
    ax.set_xlabel("Tần số (Hz)", fontsize=8)
    ax.set_ylabel("H(f)", fontsize=8)
    ax.set_yticks([])
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_title("32 bộ lọc tam giác · 34 mép chia đều trên trục Mel",
                 fontsize=8.2, color=RED_DARK, fontweight="bold", pad=3)
    for i, txt in [(0, "BW 123 Hz · tâm 139 Hz"), (31, "BW 1.183 Hz · tâm 7.387 Hz")]:
        x = EDGES_HZ[i + 1]
        ax.annotate(txt, xy=(x, 1.0), xytext=(x + (250 if i == 0 else -250), 1.06),
                    fontsize=6.4, color=DARK, ha="left" if i == 0 else "right",
                    va="bottom",
                    arrowprops=dict(arrowstyle="-", color=GRAY, linewidth=0.6))
    ax.text(0.99, 0.03, "bin FFT giữa hai tam giác được chia theo đúng tỷ lệ vị trí",
            transform=ax.transAxes, fontsize=6.2, color=GRAY, va="bottom", ha="right")
    ax.grid(axis="y", color=GRID, linewidth=0.5, zorder=0)

    hz = np.array([63, 100, 200, 500, 1000, 1100, 2000, 4000, 8000.0])
    mm = mel(hz)
    ax2.plot(hz, mm, color=RED, linewidth=1.4)
    ax2.plot([100, 200], mel([100, 200]), "o", color=RED_DARK, markersize=3.2)
    ax2.plot([1000, 1100], mel([1000, 1100]), "o", color=BLUE, markersize=3.2)
    ax2.annotate("100→200 Hz\n+132,7 mel", xy=(200, mel(200)), xytext=(1600, 300),
                 fontsize=6.4, color=RED_DARK,
                 arrowprops=dict(arrowstyle="-", color=GRAY, linewidth=0.6))
    ax2.annotate("1000→1100 Hz\n+64,4 mel", xy=(1100, mel(1100)), xytext=(2500, 1750),
                 fontsize=6.4, color=BLUE,
                 arrowprops=dict(arrowstyle="-", color=GRAY, linewidth=0.6))
    ax2.set_xscale("log")
    ax2.set_xlabel("f (Hz) — thang log", fontsize=7.6)
    ax2.set_ylabel("mel", fontsize=7.6)
    ax2.set_title("m = 2595·log₁₀(1 + f/700)", fontsize=7.6, pad=3, color=DARK)
    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)
    ax2.tick_params(labelsize=6.8)
    return _save(fig, "mel")


# ---------------------------------------------------------------------------
# 4. DCT-II: cơ sở trực giao + nén năng lượng (PHẦN 3)
# ---------------------------------------------------------------------------
def fig_dct_basis():
    N = 32
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(7.3, 2.10),
                                  gridspec_kw={"wspace": 0.30})
    n = np.arange(N)
    for k, c in zip([0, 1, 2, 3], [RED, RED_DARK, BLUE, GRAY]):
        ax.plot(n, np.cos(np.pi * k * (2 * n + 1) / (2 * N)), linewidth=1.5 if k < 2 else 1.0,
                color=c, label="k = %d" % k)
    ax.set_xlabel("i (băng Mel 1…32)", fontsize=7.8)
    ax.set_ylabel("cos[π·k·(2i+1)/64]", fontsize=7.8)
    ax.set_title("Hàm cơ sở DCT-II (trực giao)", fontsize=8.2,
                 color=RED_DARK, fontweight="bold", pad=3)
    ax.legend(fontsize=6.4, frameon=False, ncol=4, loc="lower center",
              handlelength=1.1, columnspacing=1.0)
    ax.set_xlim(-0.5, N - 0.5)
    ax.set_xticks([0, 8, 16, 24, 31])
    ax.tick_params(labelsize=7)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    # đường bao log-Energy tổng hợp (minh họa) → DCT-II → năng lượng theo bậc
    hz_c = EDGES_HZ[1:-1]                                   # 32 tâm băng Mel
    env = (1.0 * np.exp(-((hz_c - 500) ** 2) / (2 * 260.0 ** 2))
           + 0.8 * np.exp(-((hz_c - 1500) ** 2) / (2 * 420.0 ** 2))
           + 0.5 * np.exp(-((hz_c - 3200) ** 2) / (2 * 900.0 ** 2)) + 0.25)
    logenv = 20.0 * np.log10(env)
    C = np.array([np.sum(logenv * np.cos(np.pi * k * (2 * np.arange(N) + 1) / (2 * N)))
                  for k in range(N)])
    energy = C ** 2
    share = np.cumsum(energy) / energy.sum() * 100.0
    ks = np.arange(1, N + 1)
    ax2.bar(ks, share, width=0.62, color=["#D9A9B0"] * N, edgecolor="none")
    ax2.bar(ks[:13], share[:13], width=0.62, color=RED, edgecolor="none")
    ax2.axvline(13.5, color=BLUE, linewidth=0.9, linestyle="--")
    ax2.text(13.9, 55, "cắt ở 13\n(C₀…C₁₂)", fontsize=6.6, color=BLUE)
    ax2.axhline(99, color=GRAY, linewidth=0.7, linestyle=":")
    ax2.text(18, 92, "99 % năng lượng", fontsize=6.6, color=GRAY)
    ax2.set_xlabel("Bậc cepstral k", fontsize=7.8)
    ax2.set_ylabel("% năng lượng tích lũy", fontsize=7.8)
    ax2.set_xlim(0, N + 0.5)
    ax2.set_ylim(0, 105)
    ax2.set_xticks([1, 5, 10, 13, 20, 31])
    ax2.tick_params(labelsize=7)
    ax2.set_title("Nén năng lượng của DCT-II (minh họa)", fontsize=8.2,
                  color=RED_DARK, fontweight="bold", pad=3)
    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)
    return _save(fig, "dct_basis")


# ---------------------------------------------------------------------------
# 5. FP32 → INT8: bộ nhớ và độ trễ (PHẦN 4)
# ---------------------------------------------------------------------------
def fig_quant():
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(7.3, 2.4),
                                  gridspec_kw={"width_ratios": [1.35, 1.0], "wspace": 0.34})
    labels = ["Model file\n(trọng số)", "RAM\nsuy luận", "ROM\nsuy luận"]
    fp32 = [7564, 5208, 26296]
    int8 = [5920, 3432, 30952]
    x = np.arange(3)
    ax.bar(x - 0.19, fp32, width=0.34, color="#C9CDD2", edgecolor=GRAY, linewidth=0.6,
           label="Float32")
    ax.bar(x + 0.19, int8, width=0.34, color=RED, edgecolor=RED_DARK, linewidth=0.6,
           label="INT8 (EON)")
    for xi, (a, b) in enumerate(zip(fp32, int8)):
        ax.text(xi - 0.19, a + 700, "{:,}".format(a).replace(",", "."), ha="center",
                fontsize=6.4, color=GRAY)
        ax.text(xi + 0.19, b + 700, "{:,}".format(b).replace(",", "."), ha="center",
                fontsize=6.4, color=RED_DARK, fontweight="bold")
        pct = 100.0 * (b - a) / a
        ax.text(xi, max(a, b) + 3400, "%+.1f %%" % pct, ha="center", fontsize=6.6,
                color=BLUE, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=6.9)
    ax.set_ylim(0, 39000)
    ax.set_ylabel("byte", fontsize=7.8)
    ax.legend(fontsize=6.8, frameon=False, loc="upper left")
    ax.set_title("Bộ nhớ: −21,7 % model · −34,1 % RAM", fontsize=8.0,
                 color=RED_DARK, fontweight="bold", pad=3)
    ax.tick_params(labelsize=7)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    lab2 = ["Nicla Vision M4\n(đích khai báo)", "espressif-esp32\n(lớp 240 MHz)"]
    f32 = [6, 16]
    i8 = [1, 3]
    y = np.arange(2)
    ax2.barh(y + 0.17, f32, height=0.30, color="#C9CDD2", edgecolor=GRAY, linewidth=0.6)
    ax2.barh(y - 0.17, i8, height=0.30, color=RED, edgecolor=RED_DARK, linewidth=0.6)
    for yi, (a, b) in enumerate(zip(f32, i8)):
        ax2.text(a + 0.4, yi + 0.17, "%d ms" % a, va="center", fontsize=6.6, color=GRAY)
        ax2.text(b + 0.4, yi - 0.17, "%d ms  (%.1f×)" % (b, a / b), va="center",
                 fontsize=6.6, color=RED_DARK, fontweight="bold")
    ax2.set_yticks(y)
    ax2.set_yticklabels(lab2, fontsize=6.9)
    ax2.set_xlim(0, 25)
    ax2.set_xlabel("Độ trễ suy luận (ms)", fontsize=7.8)
    ax2.set_title("Độ trễ: FP32 → INT8", fontsize=8.0, color=RED_DARK,
                  fontweight="bold", pad=3)
    ax2.tick_params(labelsize=7)
    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)
    return _save(fig, "quant")


# ---------------------------------------------------------------------------
# 6. Đóng khung: cửa sổ Hann vs chữ nhật (PHẦN 5)
# ---------------------------------------------------------------------------
def fig_framing():
    N = 512
    n = np.arange(N)
    hann = 0.5 * (1 - np.cos(2 * np.pi * n / (N - 1)))
    rect = np.ones(N)

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(7.3, 1.95),
                                  gridspec_kw={"wspace": 0.30})
    ax.plot(n, rect, color=GRAY, linewidth=1.2, label="Chữ nhật (cắt thô)")
    ax.plot(n, hann, color=RED, linewidth=1.4, label="Hann w[n]")
    ax.set_xlim(0, N - 1)
    ax.set_ylim(-0.05, 1.12)
    ax.set_xlabel("mẫu trong khung (512)", fontsize=7.8)
    ax.set_ylabel("w[n]", fontsize=7.8)
    ax.legend(fontsize=6.6, frameon=False, loc="lower center", ncol=2,
              bbox_to_anchor=(0.5, -0.42), handlelength=1.3, columnspacing=1.2)
    ax.set_title("w[n] = 0,5·(1 − cos(2πn/(N−1)))", fontsize=8.0,
                 color=RED_DARK, fontweight="bold", pad=3)
    ax.tick_params(labelsize=7)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)

    for w, c, lab in ((rect, GRAY, "Chữ nhật"), (hann, RED, "Hann")):
        spec = np.abs(np.fft.rfft(w, 8192))
        spec /= spec.max()
        fq = np.arange(spec.size) * 16000.0 / 8192.0
        db = 20 * np.log10(np.maximum(spec, 1e-6))
        ax2.plot(fq[1:60], db[1:60], color=c, linewidth=1.2, label=lab)
    ax2.axhline(-13.26, color=GRAY, linewidth=0.6, linestyle=":")
    ax2.axhline(-31.47, color=RED, linewidth=0.6, linestyle=":")
    ax2.text(70, -11.4, "−13 dB", fontsize=6.4, color=GRAY)
    ax2.text(70, -29.5, "−31 dB", fontsize=6.4, color=RED)
    ax2.set_xlim(0, 115)
    ax2.set_ylim(-70, 5)
    ax2.set_xlabel("lệch so với bin trung tâm (Hz)", fontsize=7.4)
    ax2.set_ylabel("biên độ búp bên (dB)", fontsize=7.4)
    ax2.set_title("Rò rỉ phổ: sidelobe đầu tiên", fontsize=8.0, color=RED_DARK,
                  fontweight="bold", pad=3)
    ax2.tick_params(labelsize=7)
    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)
    return _save(fig, "framing")


# ---------------------------------------------------------------------------
# 7. Confusion matrix 36 cửa sổ validation (PHẦN 6)
# ---------------------------------------------------------------------------
def fig_confusion():
    cm = np.array([[21, 4], [2, 9]])
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(7.3, 2.2),
                                  gridspec_kw={"width_ratios": [1.0, 0.85], "wspace": 0.30})
    im = ax.imshow(cm, cmap="Reds", vmin=0, vmax=24)
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(["Dự đoán\nnoise", "Dự đoán\ntarget"], fontsize=7.2)
    ax.set_yticklabels(["Thực tế\nnoise", "Thực tế\ntarget"], fontsize=7.2)
    names = [["TN = 21", "FP = 4"], ["FN = 2", "TP = 9"]]
    for i in range(2):
        for j in range(2):
            ax.text(j, i, names[i][j], ha="center", va="center", fontsize=9,
                    fontweight="bold",
                    color="white" if cm[i, j] > 12 else RED_DARK)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("36 cửa sổ validation", fontsize=8.2, color=RED_DARK,
                 fontweight="bold", pad=3)
    ax.tick_params(length=0)

    ax2.axis("off")
    rows = [
        ("Accuracy", "(21+9)/36", "83,33 %"),
        ("TPR — recall target", "9/11", "81,8 %"),
        ("TNR — recall noise", "21/25", "84,0 %"),
        ("Precision target", "9/13", "69,2 %"),
        ("F1 weighted / macro", "— / —", "0,84 / 0,81"),
        ("ROC AUC", "—", "0,83"),
    ]
    ax2.text(0.0, 1.02, "Chỉ số dẫn xuất từ chính confusion matrix này",
             fontsize=8.0, fontweight="bold", color=RED_DARK, va="bottom")
    for i, (lab, frac, val) in enumerate(rows):
        yy = 0.88 - i * 0.155
        ax2.text(0.0, yy, lab, fontsize=7.2, color=DARK, va="center")
        ax2.text(0.60, yy, frac, fontsize=7.0, color=GRAY, va="center", ha="right")
        ax2.text(1.0, yy, val, fontsize=7.4, color=BLUE, va="center", ha="right",
                 fontweight="bold")
        ax2.plot([0.0, 1.0], [yy - 0.075, yy - 0.075], color=GRID, linewidth=0.5)
    ax2.set_xlim(-0.02, 1.02)
    ax2.set_ylim(-0.12, 1.08)
    return _save(fig, "confusion")


# ---------------------------------------------------------------------------
# 8. Khoảng tin cậy Wilson 95 % (PHẦN 7)
# ---------------------------------------------------------------------------
def fig_wilson():
    items = [("Accuracy tổng thể", 30, 36), ("Recall lớp target", 9, 11),
             ("Recall lớp noise", 21, 25), ("Precision lớp target", 9, 13)]
    fig, ax = plt.subplots(figsize=(7.3, 2.25))
    ys = np.arange(len(items))[::-1]
    for y, (lab, k, n) in zip(ys, items):
        lo, hi = wilson(k, n)
        p = k / n
        ax.plot([lo * 100, hi * 100], [y, y], color=RED, linewidth=2.4,
                solid_capstyle="round")
        ax.plot([p * 100], [y], "o", color=RED_DARK, markersize=6, zorder=3)
        ax.text(lo * 100 - 1.5, y, "%.1f %%" % (lo * 100), ha="right", va="center",
                fontsize=6.8, color=GRAY)
        ax.text(hi * 100 + 1.5, y, "%.1f %%" % (hi * 100), ha="left", va="center",
                fontsize=6.8, color=GRAY)
        ax.text(102, y, "%d/%d mẫu" % (k, n), ha="left", va="center", fontsize=6.6,
                color=GRAY)
    ax.set_yticks(ys)
    ax.set_yticklabels(["Accuracy\ntổng thể", "Recall\nlớp target", "Recall\nlớp noise",
                        "Precision\nlớp target"], fontsize=7.2)
    ax.set_xlim(28, 121)
    ax.set_xticks([40, 50, 60, 70, 80, 90, 100])
    ax.set_xlabel("Khoảng Wilson 95 % (có hiệu chỉnh liên tục) — %", fontsize=7.8)
    ax.set_title("36 cửa sổ validation là quá ít: khoảng tin cậy rộng ±12…21 điểm %",
                 fontsize=8.2, color=RED_DARK, fontweight="bold", pad=4)
    ax.tick_params(labelsize=7)
    ax.grid(axis="x", color=GRID, linewidth=0.5, zorder=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    return _save(fig, "wilson")


# ---------------------------------------------------------------------------
# 9. Hai pipeline song song (PHẦN 5)
# ---------------------------------------------------------------------------
def fig_two_pipelines():
    fig, ax = plt.subplots(figsize=(10.4, 1.32))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    rows = [
        (0.60, "Pipeline EI chuẩn (số liệu báo cáo)",
         ["32 Mel tam giác 80–8000 Hz", "log(E+ε)", "DCT-II 32 → 13 hệ số",
          "31 × 13 = 403 chiều", "Model EI 978 TS · 5.920 B"],
         RED, RED_DARK, "white"),
        (0.09, "Pipeline firmware tự triển khai (chạy thật trên thiết bị)",
         ["13 băng × 19 bins = 247 bins", "log(E/512² + 1e-6)", "không DCT đầy đủ",
          "32 × 13 = 416 chiều", "voice_auth.tflite 13.601 TS · 20.000 B"],
         "#F4F5F7", GRAY, DARK),
    ]
    for y, title, steps, bg, edge, fg in rows:
        ax.text(0.002, y + 0.30, title, fontsize=7.6, fontweight="bold",
                color=RED_DARK if fg == "white" else DARK, va="bottom")
        w = (0.98 - 0.012 * (len(steps) - 1)) / len(steps)
        for i, st in enumerate(steps):
            x = i * (w + 0.012)
            ax.add_patch(FancyBboxPatch((x, y), w, 0.26,
                                        boxstyle="round,pad=0.003,rounding_size=0.015",
                                        linewidth=0.8, edgecolor=edge, facecolor=bg,
                                        zorder=3))
            ax.text(x + w / 2, y + 0.13, st, ha="center", va="center", fontsize=6.6,
                    color=fg, zorder=4, fontweight="bold" if fg == "white" else "normal")
            if i < len(steps) - 1:
                ax.add_patch(FancyArrowPatch((x + w + 0.0008, y + 0.13),
                                             (x + w + 0.0112, y + 0.13),
                                             arrowstyle="-|>", mutation_scale=6,
                                             linewidth=0.8, color=GRAY, zorder=2))
    return _save(fig, "two_pipelines")


# ---------------------------------------------------------------------------
# 10. Slide kết: bốn chỉ số chốt
# ---------------------------------------------------------------------------
def fig_summary():
    tiles = [
        ("83,33 %", "Accuracy validation\nFP32 = INT8 (0 điểm mất)", RED),
        ("−34,1 %", "RAM suy luận khi PTQ INT8\n5.208 B → 3.432 B", RED_DARK),
        ("1–3 ms", "Độ trễ INT8 trên LX7 240 MHz\nso với budget 100 ms", BLUE),
        ("0,84 / 0,75", "F1 weighted toàn cục /\nF1 lớp target cần cải thiện", GOLD),
    ]
    fig, ax = plt.subplots(figsize=(7.3, 2.05))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    w = 0.235
    for i, (big, sub, col) in enumerate(tiles):
        x = i * (w + 0.02)
        ax.add_patch(FancyBboxPatch((x, 0.03), w, 0.92,
                                    boxstyle="round,pad=0.004,rounding_size=0.03",
                                    linewidth=1.0, edgecolor=col, facecolor=LIGHT))
        ax.text(x + w / 2, 0.70, big, ha="center", va="center", fontsize=15,
                fontweight="bold", color=col)
        ax.text(x + w / 2, 0.30, sub, ha="center", va="center", fontsize=6.8,
                color=DARK, linespacing=1.35)
    return _save(fig, "summary")


# ---------------------------------------------------------------------------
# 4b. Bẻ công thức DCT-II: đường bao + gợn → cosin chậm/nhanh → hệ số dồn về đâu
# ---------------------------------------------------------------------------
def fig_dct_walkthrough():
    """Minh họa 3 bước (toán học thuần, tự dựng): (A) 32 log-Mel = đường bao chậm
    + gợn hài nhanh; (B) hai hàm cosin bậc thấp/cao; (C) hệ số DCT dồn về bậc thấp,
    gợn F0 rơi vào bậc ~14–15 và bị bỏ."""
    N = 32
    i = np.arange(N)
    # Đường bao chậm: ba đỉnh formant (vị trí theo băng Mel — minh họa)
    H = (1.00 * np.exp(-((i - 5.0) ** 2) / (2 * 3.2 ** 2))
         + 0.75 * np.exp(-((i - 13.0) ** 2) / (2 * 3.6 ** 2))
         + 0.45 * np.exp(-((i - 25.0) ** 2) / (2 * 5.0 ** 2)) + 0.30) * 14.0
    # Gợn chu kỳ hài: ~7,2 chu kỳ trên 32 băng (DCT-II dồn gợn này về bậc ~14–15,
    # vì ánh xạ tần số của DCT-II ≈ gấp đôi số chu kỳ/băng), biên độ nhỏ phủ trên đường bao
    S = 1.25 * np.cos(2 * np.pi * 7.2 * i / N + 0.25 * np.pi)
    x = H + S
    C = np.array([np.sum(x * np.cos(np.pi * k * (2 * i + 1) / (2 * N)))
                  for k in range(N)])
    energy = C ** 2
    keep = 100.0 * energy[:13].sum() / energy.sum()
    mag14_15 = 100.0 * energy[13:15].sum() / energy.sum()

    fig, (a, b, c) = plt.subplots(1, 3, figsize=(9.9, 2.55),
                                 gridspec_kw={"wspace": 0.30})

    # (A) 32 log-Mel = H + S
    a.plot(i, x, color=DARK, linewidth=1.6, label="x = H + S (32 log-Mel)", zorder=3)
    a.plot(i, H, color=RED, linewidth=1.9, linestyle="--", zorder=4,
           label="H — đường bao F1/F2/F3 (chậm)")
    a.plot(i, S + H.mean(), color="#3C64B1", linewidth=0.9, alpha=0.85,
           label="S — gợn hài F0 (nhanh)")
    a.set_xlabel("băng Mel i = 1…32", fontsize=7.8)
    a.set_title("(A) 32 thang Mel sau log\n= đường bao chậm + gợn nhanh",
                fontsize=8.0, color=RED_DARK, fontweight="bold", pad=3)
    a.legend(fontsize=5.9, frameon=False, loc="upper right", handlelength=1.4)
    a.set_xlim(-0.5, N - 0.5)
    a.set_xticks([0, 8, 16, 24, 31])
    a.tick_params(labelsize=6.6)
    a.grid(color=GRID, linewidth=0.45, zorder=0)
    for s_ in ("top", "right"):
        a.spines[s_].set_visible(False)

    # (B) hai hàm cosin
    b.plot(i, np.cos(np.pi * 1 * (2 * i + 1) / (2 * N)), color=RED, linewidth=1.8,
           label="cosin n = 1 — chậm")
    b.plot(i, np.cos(np.pi * 15 * (2 * i + 1) / (2 * N)), color="#3C64B1",
           linewidth=1.0, label="cosin n = 15 — nhanh")
    b.set_xlabel("băng Mel i", fontsize=7.8)
    b.set_title("(B) cosin n nhỏ khớp đường bao\nn lớn khớp gợn nhanh",
                fontsize=8.0, color=RED_DARK, fontweight="bold", pad=3)
    b.legend(fontsize=5.9, frameon=False, loc="lower center", handlelength=1.4)
    b.set_xlim(-0.5, N - 0.5)
    b.set_ylim(-1.35, 1.35)
    b.set_xticks([0, 8, 16, 24, 31])
    b.tick_params(labelsize=6.6)
    b.grid(color=GRID, linewidth=0.45, zorder=0)
    for s_ in ("top", "right"):
        b.spines[s_].set_visible(False)

    # (C) hệ số DCT
    ks = np.arange(1, N + 1)   # bậc n = 0…31 hiển thị từ 1
    cols = [RED if k <= 12 else "#C9CDD2" for k in range(N)]
    cols[13:15] = [GOLD, GOLD]
    c.axhline(0, color=GRAY, linewidth=0.5)
    c.bar(ks - 1, C, width=0.7, color=cols, edgecolor="none")
    c.axvline(12.5, color=BLUE, linewidth=0.9, linestyle="--")
    c.annotate("gợn F0 đỉnh tại\nC₁₄–C₁₅ → BỎ\n(giữ C₀–C₁₂)",
               xy=(14, C[14]), xytext=(19, C.max() * 0.55), fontsize=6.3, color=BLUE,
               arrowprops=dict(arrowstyle="-", color=GRAY, linewidth=0.6))
    c.set_xlabel("bậc hệ số n (C₀…C₃₁)", fontsize=7.8)
    c.set_title("(C) DCT-II: năng lượng dồn về C₀–C₁₂\nĐỉnh gợn F0 tại C₁₄–C₁₅ → BỎ, giữ 13 hệ số",
                fontsize=8.0, color=RED_DARK, fontweight="bold", pad=3)
    c.set_xticks([0, 4, 8, 12, 15, 20, 25, 31])
    c.tick_params(labelsize=6.6)
    c.grid(axis="y", color=GRID, linewidth=0.45, zorder=0)
    for s_ in ("top", "right"):
        c.spines[s_].set_visible(False)
    return _save(fig, "dct_walkthrough")


BUILDERS = [
    ("pipeline", fig_pipeline),
    ("mac", fig_mac),
    ("mel", fig_mel),
    ("dct_basis", fig_dct_basis),
    ("quant", fig_quant),
    ("framing", fig_framing),
    ("confusion", fig_confusion),
    ("wilson", fig_wilson),
    ("two_pipelines", fig_two_pipelines),
    ("summary", fig_summary),
    ("dct_walkthrough", fig_dct_walkthrough),
]


# Bề rộng thiết kế (inch) — hình được vẽ ở đúng bề rộng mà slide sẽ dùng,
# nên cỡ chữ bên trong hình giữ nguyên khi chèn vào slide.
DESIGN_W = {"default": 7.3, "pipeline": 9.9, "two_pipelines": 10.4,
            "dct_walkthrough": 9.9}


def ensure(force=False):
    """Vẽ các hình còn thiếu (hoặc tất cả nếu force) và trả về {tên: đường dẫn}."""
    out = {}
    for name, fn in BUILDERS:
        path = os.path.join(FIGDIR, name + ".png")
        if force or not os.path.exists(path):
            path = fn()
        out[name] = path
    return out


def info(name):
    """(đường dẫn, bề rộng thiết kế, tỷ lệ cao/rộng) của một hình."""
    from PIL import Image
    path = os.path.join(FIGDIR, name + ".png")
    if not os.path.exists(path):
        raise SystemExit("Thiếu hình %s — chạy: python deck_figures.py" % name)
    with Image.open(path) as im:
        ar = im.height / float(im.width)
    return path, DESIGN_W.get(name, DESIGN_W["default"]), ar


if __name__ == "__main__":
    imgs = ensure(force="--force" in sys.argv)
    print("\n%d hình trong %s" % (len(imgs), FIGDIR))
