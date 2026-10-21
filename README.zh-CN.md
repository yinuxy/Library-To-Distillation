# 蒸馏图书馆 · Library-To-Distillation

> English: [README.md](./README.md)

把书籍蒸馏成果（精华 / 图谱 / 行动 / 图鉴）组织成一个纯静态小站。
零构建依赖、零外部 CDN、零服务端代码 —— 丢进任意静态托管就能跑。

> 每本书拆成四层产物：**D1 精华**（骨架 + 命题）、**D3 行动**（SOP + 清单）、
> **D5 图谱**（概念关系）、**附录**（可检索形态表）。所有页面单文件、图片内联、离线可开。

## 在线访问

- <https://libs.yinux.workers.dev/>（Cloudflare Pages）

## 一键部署

点按钮即可把本仓库部署到对应平台。站点是纯静态文件、就在仓库根目录 —— **无需构建命令、无需输出目录**。

[![Deploy to GitHub Pages](https://img.shields.io/badge/Deploy-GitHub_Pages-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/yinuxy/Library-To-Distillation/settings/pages)
[![Deploy to Vercel](https://img.shields.io/badge/Deploy-Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fyinuxy%2FLibrary-To-Distillation)
[![Deploy to Netlify](https://img.shields.io/badge/Deploy-Netlify-00C7B7?style=for-the-badge&logo=netlify&logoColor=white)](https://app.netlify.com/start/deploy?repository=https%3A%2F%2Fgithub.com%2Fyinuxy%2FLibrary-To-Distillation)
[![Deploy to Cloudflare Pages](https://img.shields.io/badge/Deploy-Cloudflare_Pages-F38020?style=for-the-badge&logo=cloudflare&logoColor=white)](https://dash.cloudflare.com/?to=/:account/pages/create)
[![Deploy to Render](https://img.shields.io/badge/Deploy-Render-46E3B7?style=for-the-badge&logo=render&logoColor=black)](https://render.com/deploy?repo=https://github.com/yinuxy/Library-To-Distillation)

> 点击后授权平台读取本仓库、从仓库根目录部署即可。Vercel / Netlify / Render 的按钮会直达本仓库的新部署流程。

## 能把这个仓库直接展示成 Pages 的托管平台

以下平台都能连接 GitHub 仓库、自动构建并输出 HTTPS 站点，免费额度对个人/文档站绰绰有余：

| 平台 | 免费额度（2026） | 亮点 |
|---|---|---|
| **GitHub Pages** | 1 GB 存储 · 100 GB/月带宽（软限） | 与仓库原生集成、零第三方 |
| **Cloudflare Pages** | **无限带宽** · 500 构建/月 · 100 项目 | 无限带宽、全球 300+ 节点、国内访问友好 |
| **Vercel** | 100 GB/月 · 6000 构建分钟/月 | 前端生态好、预览部署 |
| **Netlify** | 100 GB/月 · 300 构建分钟/月 | 支持拖拽、表单、Serverless 函数 |
| **Render** | 750 实例小时/月 | 静态之外还能跑小后端 |
| **Firebase Hosting** | 10 GB 存储 · 360 MB/天传输 | 与 Google 生态打通 |
| **Surge.sh** | 无限发布次数 | 纯命令行一条命令上线 |

> 免费额度会调整，以各平台官网为准。看重国内访问速度选 Cloudflare Pages，最省事就留在 GitHub Pages。

### 接入通用三步（以本仓库为例）

1. 授权平台读取本仓库（OAuth）；
2. 构建命令留空、**输出目录留空**（站点文件就在仓库根目录）；
3. 部署完成后访问平台给的域名。

> 本仓库是纯静态文件，**无需任何构建步骤**，直接发布仓库根目录即可。

## 目录结构

```
.
├── index.html                      # 目录主页（书目数据已内联，双击可开）
├── catalog.json                    # ★ 唯一数据源：站点信息 + 书目清单
├── build_catalog.py                # 构建：注入书目 / 生成 sitemap+robots / 校验链接
├── patch_book_page.py              # 给书籍详情页注入「返回书架」按钮（幂等）
├── serve.py                        # 本地预览服务器
├── 404.html                        # 404 页（返回路径随 base_url 自动同步）
├── robots.txt                      # Sitemap 随构建自动更新
├── sitemap.xml                     # 随构建自动生成
├── books/
│   └── japanese-candlestick/
│       └── index.html              # 书籍详情页（单文件，84 张图全内联）
└── downloads/
    └── japanese-candlestick/       # 该书可下载的 .md 蒸馏稿
```

## 新增一本书

1. 详情页放到 `books/<新书 id>/index.html`，蒸馏稿放到 `downloads/<新书 id>/`。
2. 在 `catalog.json` 的 `books` 数组追加一条（字段见下方）。
3. 重新构建并提交：

```bash
python build_catalog.py            # 注入书目 + 生成 sitemap/robots + 同步 404 路径
python patch_book_page.py          # 给新页面补「返回书架」按钮（可重复执行）
python build_catalog.py --check    # 确认同步
git add -A && git commit -m "add book <id>" && git push
```

### 书目字段速查

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` / `path` | 是 | 唯一标识 / 站点内相对目录（`books/<id>/`） |
| `no` / `title` / `author` | 是 | 编号 / 书名 / 作者 |
| `tags` / `category` | 否 | 标签与分类（分类自动成为筛选 chip） |
| `keywords` | 否 | 书内概念词，用于站内搜索穿透到详情页内容 |
| `stats` | 否 | 书卡上的 3–4 个关键数字 |
| `outputs` | 否 | 下载按钮，`file` 为站点内相对路径 |
| `cover_bg` / `cover_fg` | 否 | 书封渐变与文字色，不给用默认墨色 |
| `meta.distilled` | 否 | `YYYY-MM`，首页「最近更新」取最大值 |

## 本地预览

```bash
python serve.py                # → http://127.0.0.1:8000
python serve.py --lan          # 手机同网段访问
```

也可以直接双击 `index.html`：书目数据已内联，`file://` 下同样能看。

## 换域名 / 换平台

只需改 `catalog.json` 里的 `site.base_url`，重跑 `build_catalog.py`。
sitemap、robots、404 页的返回路径都会自动同步（见「新增一本书」第 3 步）。

## 说明

- 配色：纸感底色 + 墨色文字 + 朱红强调，与书籍详情页同一套设计变量。
- 书封：纯 CSS 生成（竖排书名 + 书脊压痕 + 微光边），书名过长自动缩字号。
- 内容为 AI 辅助生成的知识蒸馏成果，用于学习研究，**非原书替代品**。
