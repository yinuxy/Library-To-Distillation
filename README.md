# Library-To-Distillation

> 中文版：[README.zh-CN.md](./README.zh-CN.md)

A pure-static site that turns book-distillation outputs (essence / concept map / action SOP / atlas)
into a browsable library. Zero build step, zero external CDN, zero server-side code — drop it on any
static host and it just works.

> Each book is distilled into four artifacts: **D1 Essence** (skeleton + propositions),
> **D3 Action** (SOP + checklists), **D5 Map** (concept graph), and an **Appendix** (searchable
> pattern table). Every page is a self-contained single file with inlined images — works offline.

## Live Site

- GitHub Pages: <https://yinuxy.github.io/Library-To-Distillation/>

## One-Click Deploy

Click a button to deploy this repository to the platform of your choice. The site is pure static
files living in the repo root — **no build command, no output directory** needed.

[![Deploy to GitHub Pages](https://img.shields.io/badge/Deploy-GitHub_Pages-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/yinuxy/Library-To-Distillation/settings/pages)
[![Deploy to Vercel](https://img.shields.io/badge/Deploy-Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fyinuxy%2FLibrary-To-Distillation)
[![Deploy to Netlify](https://img.shields.io/badge/Deploy-Netlify-00C7B7?style=for-the-badge&logo=netlify&logoColor=white)](https://app.netlify.com/start/deploy?repository=https%3A%2F%2Fgithub.com%2Fyinuxy%2FLibrary-To-Distillation)
[![Deploy to Cloudflare Pages](https://img.shields.io/badge/Deploy-Cloudflare_Pages-F38020?style=for-the-badge&logo=cloudflare&logoColor=white)](https://dash.cloudflare.com/?to=/:account/pages/create)
[![Deploy to Render](https://img.shields.io/badge/Deploy-Render-46E3B7?style=for-the-badge&logo=render&logoColor=black)](https://render.com/deploy?repo=https://github.com/yinuxy/Library-To-Distillation)

> After clicking, authorize the platform to read this repo and deploy from the repository root.
> For Vercel / Netlify / Render the button above deep-links straight into a new deployment of this repo.

## Hosting Platforms

All of the following can connect to this GitHub repository, build automatically, and serve over
HTTPS. Free tiers are more than enough for personal / documentation sites:

| Platform | Free tier (2026) | Highlight |
|---|---|---|
| **GitHub Pages** | 1 GB storage · 100 GB/mo bandwidth (soft) | Native GitHub integration, zero third party |
| **Cloudflare Pages** | **Unlimited bandwidth** · 500 builds/mo · 100 projects | Unlimited bandwidth, 300+ PoP CDN, China-friendly |
| **Vercel** | 100 GB/mo · 6000 build-min/mo | Great frontend DX, preview deploys |
| **Netlify** | 100 GB/mo · 300 build-min/mo | Drag-drop, forms, serverless functions |
| **Render** | 750 instance-hours/mo | Static plus a small backend if needed |
| **Firebase Hosting** | 10 GB storage · 360 MB/day transfer | Google ecosystem |
| **Surge.sh** | Unlimited publishes | Pure CLI, one command |

> Free tiers change over time — check each provider's site. Pick **Cloudflare Pages** if most of your
> readers are in China; stay on **GitHub Pages** for the simplest setup.

## Project Layout

```
.
├── index.html                      # Catalog homepage (data inlined, works from file://)
├── catalog.json                    # ★ single source of truth: site + book list
├── build_catalog.py                # injects catalog, generates sitemap/robots, validates links
├── patch_book_page.py              # injects "back to library" button into book pages (idempotent)
├── serve.py                        # local preview server
├── 404.html                        # 404 page (return path syncs with base_url)
├── robots.txt                      # Sitemap line auto-updated on build
├── sitemap.xml                     # auto-generated on build
├── books/
│   └── japanese-candlestick/
│       └── index.html              # book page (single file, 84 images inlined)
└── downloads/
    └── japanese-candlestick/       # downloadable .md distillation drafts
```

## Adding a New Book

1. Put the detail page at `books/<book-id>/index.html` and its drafts under `downloads/<book-id>/`.
2. Append one entry to the `books` array in `catalog.json` (fields below).
3. Rebuild and commit:

```bash
python build_catalog.py            # inject catalog + regenerate sitemap/robots + sync 404 path
python patch_book_page.py          # add "back to library" button to the new page (idempotent)
python build_catalog.py --check    # verify index.html is in sync
git add -A && git commit -m "add book <id>" && git push
```

### Book fields

| Field | Required | Description |
|---|---|---|
| `id` / `path` | yes | unique id / relative dir (`books/<id>/`) |
| `no` / `title` / `author` | yes | order number / title / author |
| `tags` / `category` | no | tags and category (category becomes a filter chip) |
| `keywords` | no | in-book terms so search reaches detail-page content |
| `stats` | no | 3–4 key numbers shown on the book card |
| `outputs` | no | download buttons; `file` is a site-relative path |
| `cover_bg` / `cover_fg` | no | cover gradient and text color (defaults provided) |
| `meta.distilled` | no | `YYYY-MM`; homepage "last updated" takes the max |

## Local Preview

```bash
python serve.py                # → http://127.0.0.1:8000
python serve.py --lan          # accessible from your phone on the same LAN
```

You can also just double-click `index.html` — the catalog data is inlined, so it renders from `file://`.

## Changing Domain / Platform

Edit `site.base_url` in `catalog.json`, then re-run `build_catalog.py`. `sitemap.xml`, `robots.txt`,
and the 404 return path all re-sync automatically (see step 3 under "Adding a New Book").

## Notes

- **Palette**: paper background + ink text + vermilion accent, shared with the book pages.
- **Book cover**: pure CSS (vertical title + spine shadow + edge highlight); title font auto-shrinks
  when too long.
- Content is AI-assisted knowledge distillation for study and research — **not a substitute for the
  original book**.
