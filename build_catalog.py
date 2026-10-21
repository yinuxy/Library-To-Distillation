#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建蒸馏图书馆站点。

以 ``catalog.json`` 为唯一数据源，重新生成：

1. ``index.html`` 中 ``<!--CATALOG_START-->`` 与 ``<!--CATALOG_END-->``
   之间的内联书目数据（页面本身不需要联网 fetch，双击即可打开）；
2. ``sitemap.xml``（若 catalog.site.base_url 已填真实域名）。

用法::

    python build_catalog.py            # 构建
    python build_catalog.py --check    # 只检查 index.html 是否与 catalog.json 同步
    python build_catalog.py --list     # 列出书目与文件校验结果

约定：``catalog.json`` 中每本书的 ``path`` 指向站点内相对目录，
目录下必须有 ``index.html``；``outputs[].file`` 指向可下载文件。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "catalog.json"
INDEX = ROOT / "index.html"
SITEMAP = ROOT / "sitemap.xml"
ROBOTS = ROOT / "robots.txt"
PAGE404 = ROOT / "404.html"

START = "<!--CATALOG_START-->"
END = "<!--CATALOG_END-->"
BLOCK_RE = re.compile(
    re.escape(START) + r".*?" + re.escape(END),
    re.DOTALL,
)
SITE_ROOT_RE = re.compile(r'(<meta name="site-root" content=")[^"]*(">)')


def load_catalog() -> dict:
    """读取并做基础结构校验。

    Returns:
        dict: 解析后的书目字典。

    Raises:
        SystemExit: JSON 语法错误或缺少 books 字段时终止。
    """
    try:
        data = json.loads(CATALOG.read_text(encoding="utf-8"))
    except FileNotFoundError:
        sys.exit(f"[x] 找不到 {CATALOG.name}")
    except json.JSONDecodeError as exc:
        sys.exit(f"[x] {CATALOG.name} JSON 语法错误：{exc}")

    if not isinstance(data.get("books"), list):
        sys.exit("[x] catalog.json 缺少 books 数组")
    return data


def validate(data: dict) -> list[str]:
    """校验书目引用的文件是否存在。

    Args:
        data: 书目字典。

    Returns:
        list[str]: 问题描述列表，空列表表示全部通过。
    """
    problems: list[str] = []
    seen: set[str] = set()

    for book in data["books"]:
        bid = book.get("id", "<无 id>")
        if bid in seen:
            problems.append(f"id 重复：{bid}")
        seen.add(bid)

        page = ROOT / (book.get("path") or "") / "index.html"
        if not book.get("path"):
            problems.append(f"{bid}: 缺少 path")
        elif not page.is_file():
            problems.append(f"{bid}: 页面不存在 {page.relative_to(ROOT).as_posix()}")

        for out in book.get("outputs") or []:
            target = ROOT / (out.get("file") or "")
            if not out.get("file") or not target.is_file():
                problems.append(f"{bid}: 下载文件缺失 {out.get('file')}")

    return problems


def build_block(data: dict) -> str:
    """生成要嵌入 index.html 的数据块。

    Args:
        data: 书目字典。

    Returns:
        str: 完整的 START/END 包裹块，JSON 已转义 ``</`` 以防提前闭合标签。
    """
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    # 防止 JSON 字符串中出现 </script> 导致标签提前闭合
    payload = payload.replace("</", "<\\/")
    return (
        f"{START}\n"
        f'<script id="catalog" type="application/json">{payload}</script>\n'
        f"{END}"
    )


def write_index(data: dict) -> bool:
    """把数据块写回 index.html。

    Args:
        data: 书目字典。

    Returns:
        bool: True 表示文件有变更，False 表示本来就是最新的。
    """
    html = INDEX.read_text(encoding="utf-8")
    if not BLOCK_RE.search(html):
        sys.exit(f"[x] index.html 中找不到 {START} / {END} 标记")

    new_block = build_block(data)
    updated = BLOCK_RE.sub(lambda _: new_block, html, count=1)
    if updated == html:
        return False
    INDEX.write_text(updated, encoding="utf-8")
    return True


def get_base(data: dict) -> str:
    """取有效的站点 base_url。

    Args:
        data: 书目字典。

    Returns:
        str: 已去尾斜杠的 base_url；未配置或仍为示例域名时返回空串。
    """
    base = (data.get("site") or {}).get("base_url", "").rstrip("/")
    if not base or "example.com" in base:
        return ""
    return base


def site_root_from(base: str) -> str:
    """从 base_url 推导站点根路径（用于 404 页返回链接）。

    Args:
        base: 已去尾斜杠的 base_url。

    Returns:
        str: 站点根路径，如 ``/Library-To-Distillation/`` 或 ``/``。
    """
    path = urlparse(base).path.rstrip("/")
    return path + "/" if path else "/"


def write_sitemap(data: dict, base_override: str = "") -> Path | None:
    """按 base_url 生成 sitemap.xml。

    Args:
        data: 书目字典。
        base_override: 命令行传入的 base_url，非空时覆盖配置里的值
            （用于子路径部署，避免改源文件）。

    Returns:
        Path | None: 生成的文件路径；base_url 未配置时返回 None。
    """
    base = (base_override or get_base(data)).rstrip("/")
    if not base:
        return None

    urls = [f"{base}/"]
    urls += [f"{base}/{quote((b.get('path') or '').lstrip('/'))}" for b in data["books"] if b.get("path")]

    body = "\n".join(
        f"  <url><loc>{u}</loc><changefreq>monthly</changefreq><priority>"
        f"{'1.0' if u == base + '/' else '0.8'}</priority></url>"
        for u in urls
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n</urlset>\n"
    )
    SITEMAP.write_text(xml, encoding="utf-8")
    return SITEMAP


def write_robots(base: str) -> None:
    """按 base_url 重写 robots.txt 的 Sitemap 行。

    Args:
        base: 已去尾斜杠的 base_url。
    """
    ROBOTS.write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {base}/sitemap.xml\n",
        encoding="utf-8",
    )


def write_site_root(root_path: str) -> bool:
    """更新 404.html 的站点根 meta。

    Args:
        root_path: 站点根路径，如 ``/Library-To-Distillation/``。

    Returns:
        bool: True 表示有变更。
    """
    html = PAGE404.read_text(encoding="utf-8")
    new = SITE_ROOT_RE.sub(lambda m: m.group(1) + root_path + m.group(2), html, count=1)
    if new == html:
        return False
    PAGE404.write_text(new, encoding="utf-8")
    return True


def main() -> int:
    """命令入口。

    Returns:
        int: 进程退出码，0 表示成功。
    """
    parser = argparse.ArgumentParser(description="构建蒸馏图书馆站点")
    parser.add_argument("--check", action="store_true", help="只检查是否同步，不写文件")
    parser.add_argument("--list", action="store_true", help="打印书目清单")
    args = parser.parse_args()

    data = load_catalog()
    problems = validate(data)

    if args.list:
        for book in data["books"]:
            print(f"  No.{book.get('no','??')}  {book.get('title','')}  →  {book.get('path','')}")
        print(f"  共 {len(data['books'])} 本，问题 {len(problems)} 项")

    if problems:
        print("[!] 校验未通过：")
        for p in problems:
            print("    -", p)
        if not args.check:
            return 1

    if args.check:
        html = INDEX.read_text(encoding="utf-8")
        current = BLOCK_RE.search(html)
        synced = bool(current) and current.group(0) == build_block(data)
        print("[√] index.html 与 catalog.json 已同步" if synced
              else "[!] index.html 与 catalog.json 不同步，请运行 python build_catalog.py")
        return 0 if synced else 1

    changed = write_index(data)
    base = get_base(data)
    sm = write_sitemap(data)
    if base:
        write_robots(base)
        write_site_root(site_root_from(base))

    print(f"[√] 注入书目：{len(data['books'])} 本  ({'已更新' if changed else '无变化'})")
    print(f"[{'√' if sm else '-'}] sitemap.xml {'已生成' if sm else '跳过（base_url 未配置）'}")
    if base:
        print(f"[√] robots.txt 与 404 站点根已同步（{base}）")

    if problems:
        print(f"[!] 有 {len(problems)} 个链接待修：")
        for p in problems:
            print("    -", p)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
