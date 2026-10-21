#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 ``../output/`` 下的全部蒸馏成果同步进站点，并重建 ``catalog.json``。

数据流::

    output/<书名>/*_蒸馏图鉴.html   → books/<id>/index.html
    output/<书名>/figures/*         → books/<id>/figures/*
    output/<书名>/*.md              → downloads/<id>/<ASCII 名>.md
    ↑ 以上同步完成后，本脚本重写 catalog.json 的 books 数组

为什么文件名要 ASCII：中文路径在 Nginx / 对象存储 / CDN 上容易 404 或乱码，
所以 ``file`` 用 ASCII，中文名放在 ``download_name``（浏览器另存为时生效）。

幂等：重复执行不产生多余改动；``--check`` 只报告差异不落盘。

用法::

    python build_books.py            # 同步并重建 catalog.json
    python build_books.py --check    # 只检查，不写文件
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent
OUTPUT = SITE.parent / "output"
CATALOG = SITE / "catalog.json"
BOOKS_DIR = SITE / "books"
DL_DIR = SITE / "downloads"

VERSION = "v1.0.0"

# ---------------------------------------------------------------- 书目元数据
# 数值取自各书 output/<书名>/00_总览与导航.md 的「核心蒸馏指标」表，
# 页数取自 books/ 下源 PDF 的实际页数；epub 来源的书不填 pages（宁可缺，不编）。
BOOKS: list[dict] = [
    {
        "id": "japanese-candlestick",
        "no": "01",
        "src": "《日本蜡烛图技术（第2版）》",
        "html_glob": "*蒸馏图鉴.html",
        "title": "日本蜡烛图技术",
        "edition": "第 2 版",
        "subtitle": "古老东方投资术的现代指南",
        "author": "史蒂夫·尼森",
        "author_en": "Steve Nison",
        "translator": "丁圣元",
        "category": "技术分析",
        "tags": ["技术分析", "K 线形态", "交易系统"],
        "keywords": ("吞没 孕线 锤子线 上吊线 启明星 黄昏星 十字线 流星 倒锤 缺口 跳空 "
                     "支撑 阻挡 趋势线 反转 持续 突破 假突破 止损 风险报偿比 仓位 "
                     "长白 长黑 影线 开盘 收市"),
        "desc": ("蜡烛图把开高低收四价编码成图形——形状不表意，位置才表意。全书蒸馏为 84 个可检索形态、"
                 "49 条带锚点命题与一套五步判读流程。"),
        "stats": [{"value": "84", "label": "形态图鉴"},
                  {"value": "49", "label": "骨架命题"},
                  {"value": "32", "label": "概念节点"},
                  {"value": "5", "label": "判读 SOP"}],
        "meta": {"pages": 407, "words": "17.9 万", "figures": 302, "distilled": "2026-10"},
        "cover_bg": "linear-gradient(155deg,#2e2a22 0%,#1d1a14 55%,#2a2018 100%)",
        "cover_fg": "#efe7d6",
        "featured": True,
    },
    {
        "id": "gann-commodity-futures",
        "no": "02",
        "src": "江恩商品期货核心教程",
        "html_glob": "*蒸馏图鉴.html",
        "title": "江恩商品期货核心教程",
        "subtitle": "一部源于江恩权威培训教程的期货交易秘籍",
        "author": "威廉·D·江恩",
        "author_en": "William D. Gann",
        "category": "江恩理论",
        "tags": ["江恩理论", "期货交易", "时间周期"],
        "keywords": ("江恩 期货 机械交易法 趋势指标 两日图 三日图 几何角度 角度线 时间正方 "
                     "时间周期 主方图 144 六边形 螺旋图 棉花 谷物 鸡蛋 咖啡 止损"),
        "desc": ("从机械交易法、两日/三日图到 144 主方图与 360° 主图，把江恩的期货教程拆成"
                 "可复算的角度线与时间周期规则。"),
        "stats": [{"value": "33", "label": "概念节点"},
                  {"value": "5", "label": "交付产物"},
                  {"value": "3.0%", "label": "蒸馏比"},
                  {"value": "57", "label": "插图"}],
        "meta": {"figures": 57, "distilled": "2026-10"},
        "cover_bg": "linear-gradient(155deg,#1f2b33 0%,#141c22 55%,#1b2a2c 100%)",
        "cover_fg": "#dfe9e6",
    },
    {
        "id": "gann-stock-truth",
        "no": "03",
        "src": "江恩股市定律(批注版) (股市投资经典译丛) (威廉·D.江恩(Williiam D.Gann)) (z-library.sk, 1lib.sk, z-lib.sk)",
        "html_glob": "*蒸馏图鉴.html",
        "title": "江恩股市定律",
        "edition": "批注版",
        "subtitle": "华尔街百年交易大师的看盘与风控奠基之作",
        "author": "威廉·D·江恩",
        "author_en": "William D. Gann",
        "translator": "田继鸣 等",
        "category": "江恩理论",
        "tags": ["江恩理论", "交易规则", "风险控制"],
        "keywords": ("江恩 十二条规则 七个行动区域 板块轮动 总体趋势 顶底形态 突破水平 "
                     "派发区间 供求 人性 止损 金字塔加仓 棉花 小麦 玉米"),
        "desc": ("十二条交易规则、七个行动区域、板块轮动与顶底形态——批注版补齐了大量实战注解，"
                 "是江恩体系里最像「操作手册」的一本。"),
        "stats": [{"value": "32", "label": "概念节点"},
                  {"value": "5", "label": "交付产物"},
                  {"value": "3.5%", "label": "蒸馏比"},
                  {"value": "31", "label": "插图"}],
        "meta": {"figures": 31, "distilled": "2026-10"},
        "cover_bg": "linear-gradient(155deg,#33291f 0%,#221b13 55%,#2f2620 100%)",
        "cover_fg": "#efe3cf",
    },
    {
        "id": "gann-trend-theory",
        "no": "04",
        "src": "江恩股市趋势理论",
        "html_glob": "*蒸馏图鉴.html",
        "title": "江恩股市趋势理论",
        "edition": "专业解读版",
        "subtitle": "趋势探测器的七章结构与解读增补",
        "author": "威廉·D·江恩",
        "author_en": "William D. Gann",
        "translator": "张艺博",
        "category": "江恩理论",
        "tags": ["江恩理论", "趋势判定", "三图分工"],
        "keywords": ("江恩 趋势探测器 三图 三点确认 强弱 道氏理论 个股 平均指数 历史重演 "
                     "牛熊周期 支撑 阻力 七条原则 止损 独立操作"),
        "desc": ("三图分工、三点确认、强弱识别——七章讲透一件事：如何用不同时间尺度的图，"
                 "判断趋势是真转向还是假动作。"),
        "stats": [{"value": "26", "label": "概念节点"},
                  {"value": "5", "label": "交付产物"},
                  {"value": "2.8%", "label": "蒸馏比"},
                  {"value": "13", "label": "插图"}],
        "meta": {"pages": 227, "figures": 13, "distilled": "2026-10"},
        "cover_bg": "linear-gradient(155deg,#26222e 0%,#171420 55%,#241f2b 100%)",
        "cover_fg": "#e6e0ef",
    },
    {
        "id": "gann-investment-bible",
        "no": "05",
        "src": "江恩股票投资圣经",
        "html_glob": "*蒸馏图鉴.html",
        "title": "江恩股票投资圣经",
        "subtitle": "一部源于江恩权威培训教程的股市投资秘籍",
        "author": "威廉·D·江恩",
        "author_en": "William D. Gann",
        "category": "江恩理论",
        "tags": ["江恩理论", "选股", "季节规律"],
        "keywords": ("江恩 交易法则 图表体系 总市值 相对强弱 时间周期 角度线 正方图 隔夜图 "
                     "机械式交易 季节性 趋势线 供需"),
        "desc": ("交易法则、图表体系、总市值与相对强弱，加上时间周期、角度线与正方图，"
                 "是江恩股市方法的集大成教程。"),
        "stats": [{"value": "37", "label": "概念节点"},
                  {"value": "5", "label": "交付产物"},
                  {"value": "2.0%", "label": "蒸馏比"},
                  {"value": "60", "label": "插图"}],
        "meta": {"figures": 60, "distilled": "2026-10"},
        "cover_bg": "linear-gradient(155deg,#2b2620 0%,#191510 55%,#2a221a 100%)",
        "cover_fg": "#f0e8d8",
    },
    {
        "id": "gann-trend-detection",
        "no": "06",
        "src": "江恩股票走势探测",
        "html_glob": "*蒸馏图鉴.html",
        "title": "江恩股票走势探测",
        "subtitle": "用三图判势、三点确认与量能验证捕捉个股趋势",
        "author": "威廉·D·江恩",
        "author_en": "William D. Gann",
        "category": "江恩理论",
        "tags": ["江恩理论", "量价", "实盘复盘"],
        "keywords": ("江恩 走势探测 三图 三点确认 成交量 四条法则 克莱斯勒 十年实盘 七条法则 "
                     "新政 证券交易法 道琼斯 背离 未来股市"),
        "desc": ("三图分工、成交量四条法则、七条实用交易方法，附克莱斯勒十年实盘复盘——"
                 "江恩体系里最贴近实盘记录的一本。"),
        "stats": [{"value": "26", "label": "概念节点"},
                  {"value": "5", "label": "交付产物"},
                  {"value": "3.6%", "label": "蒸馏比"},
                  {"value": "88", "label": "插图"}],
        "meta": {"pages": 374, "figures": 88, "distilled": "2026-10"},
        "cover_bg": "linear-gradient(155deg,#20262c 0%,#131920 55%,#1d262c 100%)",
        "cover_fg": "#dde7ee",
    },
    {
        "id": "gann-trend-forecast",
        "no": "07",
        "src": "江恩趋势预测法",
        "html_glob": "*蒸馏图鉴.html",
        "title": "江恩趋势预测法",
        "subtitle": "以形态解读、时间周期与摆动交易预测商品期货趋势",
        "author": "威廉·D·江恩",
        "author_en": "William D. Gann",
        "translator": "何君",
        "category": "江恩理论",
        "tags": ["江恩理论", "时间周期", "摆动交易"],
        "keywords": ("江恩 趋势预测 五项先决条件 百分比 50% 位 28 条规则 时间周期 时间逆转 "
                     "摆动交易 缺口 盘势陷阱 止损 商品期货"),
        "desc": ("五项先决条件、50% 位与 28 条规则、时间逆转与缺口——这本书回答的是"
                 "「什么时候会变」，不是「会涨到哪」。"),
        "stats": [{"value": "25", "label": "概念节点"},
                  {"value": "5", "label": "交付产物"},
                  {"value": "3.4%", "label": "蒸馏比"},
                  {"value": "146", "label": "原书页"}],
        "meta": {"pages": 146, "distilled": "2026-10"},
        "cover_bg": "linear-gradient(155deg,#2c2422 0%,#1b1513 55%,#2a211e 100%)",
        "cover_fg": "#efe0da",
    },
    {
        "id": "gann-stock-selection",
        "no": "08",
        "src": "江恩选股方略",
        "html_glob": "*蒸馏图鉴.html",
        "title": "江恩选股方略",
        "subtitle": "用图表、交易规则与选股方略回顾并预判股市",
        "author": "威廉·D·江恩",
        "author_en": "William D. Gann",
        "translator": "何君",
        "category": "江恩理论",
        "tags": ["江恩理论", "选股", "领涨股"],
        "keywords": ("江恩 选股 24 条规则 资金 止损 买卖点 加仓 时间周期 年线 月线 周线 日线 "
                     "强弱 领涨股 板块 总市值 周期"),
        "desc": ("24 条交易规则、不同时间周期图表的层级用法、领涨股的早期与晚期特征——"
                 "把「选哪只」拆成可核对的几条标准。"),
        "stats": [{"value": "29", "label": "概念节点"},
                  {"value": "5", "label": "交付产物"},
                  {"value": "2.8%", "label": "蒸馏比"},
                  {"value": "20", "label": "插图"}],
        "meta": {"pages": 208, "figures": 20, "distilled": "2026-10"},
        "cover_bg": "linear-gradient(155deg,#232a26 0%,#151b18 55%,#1f2823 100%)",
        "cover_fg": "#dfeae3",
    },
    {
        "id": "elliott-wave",
        "no": "09",
        "src": "艾略特波浪理论",
        "html_glob": "*蒸馏图鉴.html",
        "title": "艾略特波浪理论",
        "subtitle": "研判股市底部与顶部的有效工具",
        "author": "拉尔夫·N·艾略特",
        "author_en": "Ralph Nelson Elliott",
        "category": "波浪理论",
        "tags": ["波浪理论", "形态识别", "比例测算"],
        "keywords": ("艾略特 波浪 五浪 三浪 推进浪 调整浪 十三种调整形态 失败形态 斐波那契 "
                     "回撤 比例 平行通道 交替规则 等长规则 时间周期 层级 自然法则"),
        "desc": ("五浪推进与三浪调整、十三种调整形态、斐波那契比例与通道交替规则——"
                 "把「数浪」从感觉变成可核对的清单。"),
        "stats": [{"value": "25", "label": "概念节点"},
                  {"value": "5", "label": "交付产物"},
                  {"value": "3.7%", "label": "蒸馏比"},
                  {"value": "26", "label": "插图"}],
        "meta": {"pages": 233, "figures": 26, "distilled": "2026-10"},
        "cover_bg": "linear-gradient(155deg,#1f2a2e 0%,#121a1e 55%,#1c262a 100%)",
        "cover_fg": "#dfeaee",
    },
]

# ---------------------------------------------------------------- md 命名映射
# (正则, code, 中文名, ASCII 文件名)；顺序敏感，先匹配先返回。
MD_RULES: list[tuple[str, str, str, str]] = [
    (r"^00_", "00", "总览", "00_overview.md"),
    (r"_D1精华_", "D1", "精华", f"D1_essence_{VERSION}.md"),
    (r"_D2模型_", "D2", "模型", f"D2_model_{VERSION}.md"),
    (r"_D3行动_", "D3", "行动", f"D3_action_{VERSION}.md"),
    (r"_D5图谱_", "D5", "图谱", f"D5_map_{VERSION}.md"),
    (r"^附录A_形态图鉴", "A", "形态附录", f"appendixA_patterns_{VERSION}.md"),
    (r"^附录_", "附", "速查卡", f"appendix_rules_{VERSION}.md"),
]


def classify(name: str) -> tuple[str, str, str] | None:
    """把中文 md 文件名归类成 (code, 中文名, ASCII 文件名)。

    Args:
        name: 源文件名，如 ``《江恩选股方略》_D1精华_M_v1.0.0.md``。

    Returns:
        tuple[str, str, str] | None: 命中规则返回三元组，否则 None。
    """
    for pattern, code, label, target in MD_RULES:
        if re.search(pattern, name):
            return code, label, target
    return None


def copy_if_changed(src: Path, dst: Path) -> bool:
    """仅在内容可能变化时复制，保持幂等。

    Args:
        src: 源文件。
        dst: 目标文件。

    Returns:
        bool: True 表示实际写入了文件。
    """
    if dst.is_file() and dst.stat().st_size == src.stat().st_size \
            and dst.stat().st_mtime >= src.stat().st_mtime:
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def sync_book(spec: dict, check: bool) -> tuple[list[str], list[str]]:
    """同步单本书的页面、图片与可下载 md。

    Args:
        spec: BOOKS 中的一条书目配置。
        check: True 时只统计不落盘。

    Returns:
        tuple[list[str], list[str]]: (变更描述, 问题描述)。
    """
    changes: list[str] = []
    problems: list[str] = []
    src_dir = OUTPUT / spec["src"]
    if not src_dir.is_dir():
        return [], [f"{spec['id']}: 源目录不存在 {src_dir}"]

    # 1) 图鉴页
    pages = sorted(src_dir.glob(spec["html_glob"]))
    if not pages:
        problems.append(f"{spec['id']}: 找不到 {spec['html_glob']}")
    else:
        dst = BOOKS_DIR / spec["id"] / "index.html"
        if check:
            if not dst.is_file() or dst.stat().st_size != pages[0].stat().st_size:
                changes.append(f"页面待同步 {spec['id']}/index.html")
        elif copy_if_changed(pages[0], dst):
            changes.append(f"页面 {spec['id']}/index.html")

    # 2) 图片目录（图鉴用相对路径引用，必须整目录带过去）
    fig_src = src_dir / "figures"
    if fig_src.is_dir():
        fig_dst = BOOKS_DIR / spec["id"] / "figures"
        wanted = {p.name: p for p in fig_src.glob("*") if p.is_file()}
        if check:
            have = {p.name for p in fig_dst.glob("*")} if fig_dst.is_dir() else set()
            gap = len(set(wanted) - have)
            if gap:
                changes.append(f"图片待同步 {spec['id']}: {gap} 张")
        else:
            n = sum(1 for name, p in wanted.items() if copy_if_changed(p, fig_dst / name))
            if n:
                changes.append(f"图片 {spec['id']}: {n} 张")

    # 3) 可下载 md
    expected: set[str] = set()
    for md in sorted(src_dir.glob("*.md")):
        hit = classify(md.name)
        if not hit:
            problems.append(f"{spec['id']}: md 未归类 {md.name}")
            continue
        code, label, target = hit
        expected.add(target)
        dst = DL_DIR / spec["id"] / target
        if check:
            if not dst.is_file() or dst.stat().st_size != md.stat().st_size:
                changes.append(f"下载待同步 {spec['id']}/{target}")
        elif copy_if_changed(md, dst):
            changes.append(f"下载 {spec['id']}/{target}")

    # 4) 清掉旧命名留下的孤儿文件（例如改名前的 appendixA_84patterns）
    dl_book = DL_DIR / spec["id"]
    if dl_book.is_dir():
        for stale in sorted(dl_book.glob("*.md")):
            if stale.name not in expected:
                changes.append(f"孤儿待清理 downloads/{spec['id']}/{stale.name}")
                if not check:
                    stale.unlink()

    return changes, problems


def build_outputs(spec: dict) -> list[dict]:
    """按目录中实际存在的 md 生成 catalog 的 outputs 列表。

    Args:
        spec: BOOKS 中的一条书目配置。

    Returns:
        list[dict]: 前端下载按钮所需的数据；顺序按 code 排序。
    """
    src_dir = OUTPUT / spec["src"]
    short = re.sub(r"[（(].*?[)）]", "", spec["title"]).strip()
    rows: list[dict] = []
    for md in sorted(src_dir.glob("*.md")) if src_dir.is_dir() else []:
        hit = classify(md.name)
        if not hit:
            continue
        code, label, target = hit
        rows.append({
            "code": code,
            "name": label,
            "file": (DL_DIR / spec["id"] / target).relative_to(SITE).as_posix(),
            "download_name": f"{short}_{code}_{label}_{VERSION}.md",
        })
    order = {"00": 0, "D1": 1, "D2": 2, "D3": 3, "D5": 4, "A": 5, "附": 6}
    return sorted(rows, key=lambda r: order.get(r["code"], 9))


def build_catalog(check: bool) -> list[str]:
    """重写 catalog.json 的 books 数组，保留 site 段。

    Args:
        check: True 时只报告差异。

    Returns:
        list[str]: 变更/问题描述。
    """
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    entries: list[dict] = []
    for spec in BOOKS:
        outputs = build_outputs(spec)
        if not outputs:
            continue
        entry = {k: v for k, v in spec.items() if k not in ("src", "html_glob")}
        entry["path"] = f"books/{spec['id']}/"
        entry["outputs"] = outputs
        entries.append(entry)

    new_data = {"site": data.get("site", {}), "books": entries}
    text = json.dumps(new_data, ensure_ascii=False, indent=2) + "\n"
    if check:
        return [] if text == CATALOG.read_text(encoding="utf-8") else ["catalog.json 待重写"]
    if text != CATALOG.read_text(encoding="utf-8"):
        CATALOG.write_text(text, encoding="utf-8")
        return [f"catalog.json 已重写（{len(entries)} 本）"]
    return []


def prune_stale(check: bool) -> list[str]:
    """删除不在 BOOKS 名单里的残留书目录。

    Args:
        check: True 时只报告。

    Returns:
        list[str]: 变更描述。
    """
    keep = {b["id"] for b in BOOKS}
    out: list[str] = []
    for base in (BOOKS_DIR, DL_DIR):
        if not base.is_dir():
            continue
        for d in sorted(base.iterdir()):
            if d.is_dir() and d.name not in keep:
                out.append(f"残留待清理 {d.relative_to(SITE).as_posix()}")
                if not check:
                    shutil.rmtree(d, ignore_errors=True)
    return out


def main() -> int:
    """命令入口。

    Returns:
        int: 0 表示成功；1 表示存在需要人工处理的问题。
    """
    ap = argparse.ArgumentParser(description="把 output/ 的蒸馏成果同步进站点")
    ap.add_argument("--check", action="store_true", help="只检查，不写文件")
    args = ap.parse_args()

    if not OUTPUT.is_dir():
        sys.exit(f"[x] 找不到输出目录 {OUTPUT}")

    all_changes: list[str] = []
    all_problems: list[str] = []

    for spec in BOOKS:
        ch, pr = sync_book(spec, args.check)
        all_changes += ch
        all_problems += pr

    all_changes += prune_stale(args.check)
    all_changes += build_catalog(args.check)

    label = "[检查]" if args.check else "[同步]"
    if all_changes:
        print(f"{label} {len(all_changes)} 项变更：")
        for c in all_changes[:60]:
            print("  ·", c)
        if len(all_changes) > 60:
            print(f"  …… 其余 {len(all_changes) - 60} 项")
    else:
        print(f"{label} 站点已是最新，无变更")

    if all_problems:
        print(f"[!] {len(all_problems)} 个问题：")
        for p in all_problems:
            print("  -", p)
        return 1

    total_html = sum(1 for _ in BOOKS_DIR.glob("*/index.html"))
    total_md = sum(1 for _ in DL_DIR.glob("*/*.md"))
    total_fig = sum(1 for _ in BOOKS_DIR.glob("*/figures/*"))
    print(f"[ok] books={total_html} · downloads={total_md} · figures={total_fig}")
    print("下一步：python patch_book_page.py && python build_catalog.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
