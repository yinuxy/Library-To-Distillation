#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地预览服务器。

只服务本目录，行为尽量贴近线上静态托管：

- 目录自动补 ``index.html``；
- 未命中的路径返回 ``404.html``（而不是默认的目录列表）；
- 关闭缓存，改完刷新即生效。

用法::

    python serve.py              # http://127.0.0.1:8000
    python serve.py --port 9000  # 换端口
    python serve.py --lan        # 允许局域网访问（手机同网段可测）

注意：这里不做 gzip，本地无必要；线上请用 Nginx 的 gzip_static/gzip 配置，
详见 README 与 nginx.conf.example。
"""

from __future__ import annotations

import argparse
import http.server
import io
import socket
import socketserver
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


class Handler(http.server.SimpleHTTPRequestHandler):
    """静态文件处理器：404 回退 + 禁用缓存。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        """统一附加 no-cache 头，便于本地反复调试。"""
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def send_head(self):
        """未命中路径改为返回 404 页。

        Returns:
            文件对象或 None，与父类语义一致。
        """
        target = Path(self.translate_path(self.path))
        if not target.exists():
            page = ROOT / "404.html"
            body = page.read_bytes() if page.is_file() else b"404 Not Found"
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return io.BytesIO(body)
        return super().send_head()

    def log_message(self, fmt: str, *args) -> None:
        """精简日志：只打印请求行与状态码。"""
        sys.stderr.write(f"  {self.address_string()}  {fmt % args}\n")


class Server(socketserver.ThreadingTCPServer):
    """支持端口复用与多线程的服务器。"""

    allow_reuse_address = True
    daemon_threads = True


def local_ip() -> str:
    """取本机在局域网中的 IPv4 地址。

    Returns:
        str: 形如 ``192.168.1.23``；获取失败时返回 ``127.0.0.1``。
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def main() -> int:
    """启动服务器。

    Returns:
        int: 退出码。
    """
    parser = argparse.ArgumentParser(description="蒸馏图书馆本地预览")
    parser.add_argument("--port", type=int, default=8000, help="端口，默认 8000")
    parser.add_argument("--lan", action="store_true", help="允许局域网访问")
    args = parser.parse_args()

    host = "0.0.0.0" if args.lan else "127.0.0.1"
    shown = local_ip() if args.lan else "127.0.0.1"

    with Server((host, args.port), Handler) as httpd:
        print("\n  蒸馏图书馆 · 本地预览")
        print(f"  → http://{shown}:{args.port}/")
        print("  Ctrl+C 停止\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  已停止")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
