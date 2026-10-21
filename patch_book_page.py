#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给书籍详情页注入「返回书架」入口。

书籍页是独立生成的单文件页面，本身不知道站点结构。本脚本以最小侵入方式
补齐两处：

1. ``</style>`` 前追加 ``.backlib`` 按钮样式；
2. topbar 首个 ``.bt`` 前插入返回链接。

脚本幂等：已注入过的页面会被跳过，可安全重复执行。
原文件不受影响，只改 ``site/books/<id>/index.html``。
"""

from __future__ import annotations

import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent
MARK = 'class="backlib"'

CSS = """
/* ---- 站点注入：返回书架 ---- */
.backlib{flex:0 0 auto;width:30px;height:30px;display:grid;place-items:center;border:1px solid var(--line);
  border-radius:50%;color:var(--muted);font-size:13px;line-height:1;text-decoration:none;transition:.18s}
.backlib:hover{color:var(--ink);border-color:var(--muted);background:rgba(0,0,0,.03)}
@media (max-width:700px){.backlib{width:26px;height:26px;font-size:12px}}
"""

ANCHOR = '<div class="bt">'
LINK = '<a class="backlib" href="{href}" title="返回书架" aria-label="返回书架">←</a>\n  '


def patch(page: Path, href: str) -> bool:
    """向单个页面注入返回链接。

    Args:
        page: 目标 HTML 文件。
        href: 返回主页的相对路径。

    Returns:
        bool: True 表示已修改，False 表示无需修改。

    Raises:
        SystemExit: 页面缺少 ``</style>`` 或 ``.bt`` 锚点时终止。
    """
    html = page.read_text(encoding="utf-8")
    if MARK in html:
        print(f"  - 跳过（已注入）{page.parent.name}")
        return False

    if "</style>" not in html or ANCHOR not in html:
        sys.exit(f"[x] {page} 找不到 </style> 或 {ANCHOR} 锚点")

    html = html.replace("</style>", CSS + "</style>", 1)
    html = html.replace(ANCHOR, LINK.format(href=href) + ANCHOR, 1)
    page.write_text(html, encoding="utf-8")
    print(f"  √ 已注入返回链接 {page.parent.name} → {href}")
    return True


def main() -> int:
    """遍历 books/*/index.html 逐个注入。

    Returns:
        int: 退出码。
    """
    pages = sorted(SITE.glob("books/*/index.html"))
    if not pages:
        sys.exit("[x] 未找到 books/*/index.html")

    changed = 0
    for page in pages:
        depth = len(page.relative_to(SITE).parts) - 1  # books/<id>/index.html → 2
        href = "../" * depth + "index.html"
        changed += 1 if patch(page, href) else 0

    print(f"[√] 完成，修改 {changed}/{len(pages)} 个页面")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
