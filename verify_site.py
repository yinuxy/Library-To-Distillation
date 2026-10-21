#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""站点连通性验收：目录、书页、图片、下载全部打一遍 HTTP。

默认在**本进程内**拉一个线程化静态服务器（复用 ``serve.py`` 的 Handler），
验收完自动关闭 —— 不依赖任何外部后台进程，避免子进程被 shell 回收导致全站 502。

只依赖标准库。用法::

    python verify_site.py                    # 自起服务器，随机端口
    python verify_site.py --port 8899        # 自起服务器，固定端口
    python verify_site.py --base http://127.0.0.1:8000/   # 打已在跑的服务器
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote, urljoin

SITE = Path(__file__).resolve().parent
CATALOG = SITE / "catalog.json"

sys.path.insert(0, str(SITE))
from serve import Handler, Server  # noqa: E402


def head(url: str, timeout: float = 20.0) -> tuple[int, int]:
    """取 URL 的状态码与内容长度。

    Args:
        url: 绝对 URL。
        timeout: 超时秒数。

    Returns:
        tuple[int, int]: (状态码, 字节数)；异常时状态码为 0。
    """
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "verify/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
            return r.status, len(data)
    except urllib.error.HTTPError as exc:
        return exc.code, 0
    except Exception:
        return 0, 0


def start_server(port: int) -> tuple[Server, int]:
    """在当前进程内启动静态服务器线程。

    Args:
        port: 监听端口；传 0 表示由系统分配空闲端口。

    Returns:
        tuple[Server, int]: (服务器对象, 实际端口)。
    """
    httpd = Server(("127.0.0.1", port), Handler)
    actual = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd, actual


def run(base: str) -> int:
    """对给定 base 跑全部检查。

    Args:
        base: 站点根 URL，末尾斜杠可有可无。

    Returns:
        int: 0 表示全部通过。
    """
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    books = data["books"]

    fails: list[str] = []
    checked = {"page": 0, "img": 0, "dl": 0}

    code, size = head(urljoin(base, "index.html"))
    print(f"index.html                 {code}  {size / 1024:8.1f} KB")
    if code != 200:
        fails.append(f"index.html → {code}")

    for b in books:
        bid, path = b["id"], b["path"]
        code, size = head(urljoin(base, path))
        checked["page"] += 1
        flag = "" if code == 200 else f"  ← FAIL {code}"
        print(f"{bid:<26} {code}  {size / 1024:8.1f} KB{flag}")
        if code != 200:
            fails.append(f"{bid} 页面 → {code}")
            continue

        # 页面内图片引用（相对路径）
        page_file = SITE / path / "index.html"
        html = page_file.read_text(encoding="utf-8", errors="ignore")
        imgs = sorted(set(re.findall(r'src="((?:figures|\.\./)[^"]+)"', html)))
        bad = []
        for src in imgs:
            url = urljoin(base + path, quote(src))
            c, _ = head(url)
            checked["img"] += 1
            if c != 200:
                bad.append(f"{src}→{c}")
        print(f"  {'└ 图片':<24} {len(imgs):>3} 张，坏链 {len(bad)}")
        if bad:
            fails.append(f"{bid} 图片坏链 {len(bad)}: {bad[:3]}")

        # 下载文件
        for o in b.get("outputs") or []:
            url = urljoin(base, quote(o["file"]))
            c, _sz = head(url)
            checked["dl"] += 1
            if c != 200:
                fails.append(f"{bid}/{o['code']} 下载 → {c}")

    print("-" * 60)
    print(f"检查：页面 {checked['page']} · 图片 {checked['img']} · 下载 {checked['dl']}")
    if fails:
        print(f"[x] {len(fails)} 项失败：")
        for f in fails:
            print("   -", f)
        return 1
    print("[√] 全部 200")
    return 0


def main() -> int:
    """入口。

    Returns:
        int: 0 表示全部通过。
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="", help="打已在跑的服务器；留空则本进程自起")
    ap.add_argument("--port", type=int, default=0, help="自起服务器时的端口，0=系统分配")
    args = ap.parse_args()

    if args.base:
        base = args.base if args.base.endswith("/") else args.base + "/"
        return run(base)

    httpd, port = start_server(args.port)
    base = f"http://127.0.0.1:{port}/"
    print(f"本地服务器：{base}\n")
    try:
        return run(base)
    finally:
        httpd.shutdown()
        httpd.server_close()


if __name__ == "__main__":
    sys.exit(main())
