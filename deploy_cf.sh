#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# 重新部署到 Cloudflare Workers
#
#   线上地址：https://libs.yinux.workers.dev
#
# 用法：
#   bash deploy_cf.sh --check     只预检：算上传体积/文件数，不真部署
#   bash deploy_cf.sh            正式部署
#   bash deploy_cf.sh --rebuild  先从 output/ 重建站点再部署
#
# 前置：
#   - Node 18+
#   - 首次运行需 `npx wrangler@4 login`（浏览器里点授权，之后凭据长期有效）
#
# 说明：本机（大陆网络）直连 workers.dev 常超时，部署本身走 api.cloudflare.com
#      不受影响；部署完的验证请用手机流量或代理访问。
# ---------------------------------------------------------------------------

set -euo pipefail
cd "$(dirname "$0")"

WRANGLER="npx --yes wrangler@4"
EXPECT_FILES=362          # 373 个文件减去 .assetsignore 排除的 11 项（.git 另算）
LOG_DIR=".wrangler"
DO_CHECK=0
DO_REBUILD=0

for arg in "$@"; do
  case "$arg" in
    --check)   DO_CHECK=1 ;;
    --rebuild) DO_REBUILD=1 ;;
    -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
    *) echo "未知参数: $arg（用 --help 查看用法）" >&2; exit 2 ;;
  esac
done

cyan() { printf '\033[36m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
red()  { printf '\033[31m%s\033[0m\n' "$*" >&2; }

mkdir -p "$LOG_DIR"

# ── 1/5 环境检查 ───────────────────────────────────────────────────────────
cyan "── 1/5 检查环境 ──"
command -v node >/dev/null 2>&1 || { red "未找到 node，请先安装 Node 18+"; exit 1; }
node -e 'const v=+process.versions.node.split(".")[0]; if(v<18){console.error("Node 版本过低："+process.version);process.exit(1)}'
green "node $(node -v)"

[ -f wrangler.jsonc ] || { red "缺少 wrangler.jsonc"; exit 1; }
[ -f .assetsignore ]  || { red "缺少 .assetsignore"; exit 1; }
[ -f index.html ]     || { red "缺少 index.html，站点根不对"; exit 1; }

NAME=$(node -e 'const s=require("fs").readFileSync("wrangler.jsonc","utf8");const m=s.match(/"name"\s*:\s*"([^"]+)"/);console.log(m?m[1]:"<未找到>")')
green "wrangler.jsonc → name = $NAME"
if [ "$NAME" != "libs" ]; then
  red "⚠ name 不是 libs。部署会新建一个 Worker，而不是更新 libs.yinux.workers.dev"
  red "  确认要上线到新域名再继续；否则把 name 改回 libs"
  exit 1
fi

# ── 2/5 检查登录 ───────────────────────────────────────────────────────────
cyan "── 2/5 检查 Cloudflare 登录状态 ──"
WHO=$($WRANGLER whoami 2>&1 || true)
if ! grep -qi "logged in" <<<"$WHO"; then
  red "未登录 Cloudflare。请先执行："
  echo "    npx wrangler@4 login"
  exit 1
fi
grep -iE "logged in with|associated with" <<<"$WHO" | sed 's/^/    /'

# ── 3/5 可选：重建站点 ─────────────────────────────────────────────────────
if [ "$DO_REBUILD" = "1" ]; then
  cyan "── 3/5 从 output/ 重建站点 ──"
  PY="python"
  command -v "$PY" >/dev/null 2>&1 || PY="python3"
  "$PY" build_books.py
  "$PY" patch_book_page.py
  "$PY" build_catalog.py
  green "重建完成"
else
  cyan "── 3/5 跳过重建（加 --rebuild 可先从 output/ 同步）──"
fi

# ── 4/5 预检：看会传多少 ───────────────────────────────────────────────────
cyan "── 4/5 预检上传体积 ──"
set +e
$WRANGLER deploy --dry-run > "$LOG_DIR/dryrun.log" 2>&1
DRY_RC=$?
set -e
grep -E "Total Upload|Your Worker has access|assets" "$LOG_DIR/dryrun.log" | sed 's/^/    /' || true

if [ $DRY_RC -ne 0 ]; then
  red "预检失败，最后 20 行："
  tail -20 "$LOG_DIR/dryrun.log" | sed 's/^/    /'
  exit 1
fi

# 确认 .git 没被算进去（41 MB，最容易出问题的一项）
if grep -qE "\.git/" "$LOG_DIR/dryrun.log"; then
  red "⚠ 检测到 .git 可能被上传，检查 .assetsignore 是否生效"
  exit 1
fi
green "预检通过（预期文件数约 $EXPECT_FILES，日志：$LOG_DIR/dryrun.log）"

if [ "$DO_CHECK" = "1" ]; then
  echo
  green "只做了预检，未部署。去掉 --check 即正式部署。"
  exit 0
fi

# ── 5/5 正式部署 ───────────────────────────────────────────────────────────
cyan "── 5/5 部署到 Cloudflare ──"
set +e
$WRANGLER deploy 2>&1 | tee "$LOG_DIR/deploy.log"
RC=${PIPESTATUS[0]}
set -e

if [ $RC -ne 0 ]; then
  red "部署失败，日志：$LOG_DIR/deploy.log"
  exit $RC
fi

echo
green "已部署 → https://libs.yinux.workers.dev/"
echo
echo "  验证方式（本机直连 workers.dev 通常超时，属网络问题）："
echo "    1) 手机流量打开 https://libs.yinux.workers.dev/"
echo "    2) npx wrangler@4 deployments list"
echo "    3) Cloudflare 控制台 → Workers & Pages → libs → Deployments"
echo
echo "  若页面仍是旧内容：Cloudflare 边缘缓存，强制刷新（Ctrl+Shift+R）或等 1–2 分钟。"
echo "  若有文件 404：确认路径大小写与 .assetsignore 没误伤。"
