# -*- coding: utf-8 -*-
"""Tạo trang HTML xem nhanh các hình trong _deck_fig (chỉ dùng để kiểm tra bằng mắt)."""
import glob
import os
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
imgs = sorted(glob.glob(str(HERE / "_deck_fig" / "*.png")))
items = "\n".join(
    '<figure><img src="%s"><figcaption>%s</figcaption></figure>'
    % (pathlib.Path(p).relative_to(HERE).as_posix(), os.path.basename(p))
    for p in imgs)
html = """<!doctype html><meta charset="utf-8"><title>Deck figures</title>
<style>body{font-family:Segoe UI,sans-serif;margin:0;padding:16px;background:#fff}
figure{margin:0 0 18px}img{width:1180px;border:1px solid #ddd;display:block}
figcaption{font:12px monospace;color:#666;margin-top:4px}</style>
%s""" % items
out = HERE / "_fig_gallery.html"
out.write_text(html, encoding="utf-8")
print("wrote", out, len(imgs), "figures")
