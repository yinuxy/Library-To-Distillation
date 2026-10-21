#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给书籍详情页注入「返回书架」入口。

书籍页是各自独立生成的单文件页面，结构并不统一——目前存在两种布局：

1. **topbar 布局**（日本蜡烛图技术）：顶部工具条里有 ``<div class="bt">``，
   适合把返回按钮做成工具条里的一枚圆形图标；
2. **hero 布局**（江恩系列、艾略特）：顶部是居中的 ``<header class="hero">``，
   没有工具条，塞进 header 会破坏居中排版，因此改用**固定定位的浮动按钮**。

脚本按上述顺序探测，命中哪种用哪种；已注入过的页面直接跳过，可安全重复执行。
只改 ``site/books/<id>/index.html``，``../output`` 下的原件不受影响。

用法::

    python patch_book_page.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent
MARK = 'class="backlib'

# 布局一：工具条内联按钮
CSS_INLINE = """
/* ---- 站点注入：返回书架（工具条内联） ---- */
.backlib{flex:0 0 auto;width:30px;height:30px;display:grid;place-items:center;border:1px solid var(--line);
  border-radius:50%;color:var(--muted);font-size:13px;line-height:1;text-decoration:none;transition:.18s}
.backlib:hover{color:var(--ink);border-color:var(--muted);background:rgba(0,0,0,.03)}
@media (max-width:700px){.backlib{width:26px;height:26px;font-size:12px}}
"""
ANCHOR_BT = '<div class="bt">'
LINK_BT = '<a class="backlib" href="{href}" title="返回书架" aria-label="返回书架">←</a>\n  '

# 布局二：固定定位浮动按钮（不依赖页面内部排版）
CSS_FIXED = """
/* ---- 站点注入：返回书架（浮动按钮） ---- */
.backlib{position:fixed;top:14px;left:14px;z-index:9999;width:34px;height:34px;display:grid;
  place-items:center;border-radius:50%;border:1px solid rgba(0,0,0,.10);background:rgba(255,255,255,.88);
  -webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);color:#5d6880;font-size:15px;line-height:1;
  text-decoration:none;box-shadow:0 2px 10px rgba(0,0,0,.07);transition:.18s}
.backlib:hover{color:#1b2233;background:#fff;transform:translateX(-1px)}
@media print{.backlib{display:none}}
"""
LINK_FIXED = '<a class="backlib" href="{href}" title="返回书架" aria-label="返回书架">←</a>\n'


def patch(page: Path, href: str) -> str | None:
    """向单个页面注入返回链接。

    Args:
        page: 目标 HTML 文件。
        href: 返回主页的相对路径。

    Returns:
        str | None: 命中策略（``inline`` / ``fixed``）；已注入或无需修改时返回 None。

    Raises:
        SystemExit: 页面既无 ``</style>`` 也无 ``<body>`` 锚点时终止。
    """
    html = page.read_text(encoding="utf-8")
    if MARK in html:
        return None
    if "</style>" not in html:
        sys.exit(f"[x] {page} 缺少 </style>，无法注入样式")

    if ANCHOR_BT in html:
        html = html.replace("</style>", CSS_INLINE + "</style>", 1)
        html = html.replace(ANCHOR_BT, LINK_BT.format(href=href) + ANCHOR_BT, 1)
        page.write_text(html, encoding="utf-8")
        return "inline"

    # 浮动按钮：紧跟 <body ...> 插入，兼容带属性的 body 标签
    idx = html.find("<body")
    if idx < 0:
        sys.exit(f"[x] {page} 既无 {ANCHOR_BT} 也无 <body>")
    end = html.find(">", idx)
    if end < 0:
        sys.exit(f"[x] {page} 的 <body> 标签未闭合")
    html = html.replace("</style>", CSS_FIXED + "</style>", 1)
    html = html[: end + 1] + "\n" + LINK_FIXED.format(href=href) + html[end + 1:]
    page.write_text(html, encoding="utf-8")
    return "fixed"


def main() -> int:
    """遍历 books/*/index.html 逐个注入。

    Returns:
        int: 退出码，0 表示全部处理成功。
    """
    pages = sorted(SITE.glob("books/*/index.html"))
    if not pages:
        sys.exit("[x] 未找到 books/*/index.html")

    stat = {"inline": 0, "fixed": 0, "skip": 0}
    for page in pages:
        depth = len(page.relative_to(SITE).parts) - 1  # books/<id>/index.html → 2
        href = "../" * depth + "index.html"
        mode = patch(page, href)
        if mode is None:
            stat["skip"] += 1
            print(f"  -  跳过（已注入）{page.parent.name}")
        else:
            stat[mode] += 1
            print(f"  √  已注入 {page.parent.name} [{mode}] → {href}")

    print(f"[√] 完成：内联 {stat['inline']} · 浮动 {stat['fixed']} · 跳过 {stat['skip']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
