#!/usr/bin/env bash
# 部署到 GitHub Pages。
#
# 為什麼不用 git push / gh auth git-credential:
#   這台機器上的 git-credential-manager 與 gh auth git-credential 在非互動
#   環境下都不會回應 —— 兩者都會卡住直到逾時。實測:
#     GCM get          → 20 秒無輸出
#     gh 認證 helper   → 150 秒逾時
#     inline token     → 0.75 秒完成
#   唯一可靠的方式是從已登入的 gh CLI 取 token,當場組出 Authorization 標頭。
#
# 用法:
#   ./deploy.sh            推送 main 並部署 gh-pages
#   ./deploy.sh --pages    只重新部署網站(不動 main)

set -euo pipefail
cd "$(dirname "$0")"

if ! command -v gh >/dev/null 2>&1; then
  echo "需要 GitHub CLI: https://cli.github.com" >&2
  exit 1
fi

TOKEN=$(gh auth token)
if [ -z "$TOKEN" ]; then
  echo "gh 未登入,先執行: gh auth login" >&2
  exit 1
fi
AUTH=$(printf 'x-access-token:%s' "$TOKEN" | base64 -w0)

# 關閉 credential helper,免得 git 又去呼叫會卡住的 GCM
git config --local credential.helper ""

push() {
  git -c "http.extraHeader=Authorization: Basic $AUTH" push origin "$1"
}

# 先確保網站是最新的
python gen_facts_index.py
python gen_github_bookmarks.py
python gen_standalone_bookmarks.py
python tools/bookmarks/gen_bookmarks.py
# anonymize_paths 對二進位字串表裡的 Windows 路徑會回傳 1 —— 那是客戶端
# 自己的字串常數,不是本機路徑,verify_wiki_claims.py 也有意豁免。
python tools/anonymize_paths.py || true
# 獨立書籤頁由 mkdocs.yml 的 extra: 複製進輸出,不需手動 cp
# (mkdocs 會 clean site/,手動放的檔案會被清掉)
python -m mkdocs build --strict

if [ "${1:-}" != "--pages" ]; then
  git add -A
  if git diff --cached --quiet; then
    echo "沒有變更,略過 commit"
  else
    git -c user.name="e78-png" \
        -c user.email="e78-png@users.noreply.github.com" \
        commit -q -m "$(git log -1 --pretty=%B)"
  fi
  echo "推送 main..."
  push main
fi

echo "部署 gh-pages..."
# mkdocs gh-deploy 內部會自己呼叫 git push,同樣會踩到 credential helper。
# 用 GIT_CONFIG_* 環境變數把認證標頭傳給它啟動的 git 子行程。
GIT_CONFIG_COUNT=2 \
GIT_CONFIG_KEY_0="http.extraHeader" \
GIT_CONFIG_VALUE_0="Authorization: Basic $AUTH" \
GIT_CONFIG_KEY_1="credential.helper" \
GIT_CONFIG_VALUE_1="" \
  python -m mkdocs gh-deploy --force --strict

echo
echo "完成: https://e78-png.github.io/maplestory-v83-dev-wiki/"
