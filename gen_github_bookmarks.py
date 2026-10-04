# -*- coding: utf-8 -*-
"""把單檔書籤轉成 WIKI 網站內的嵌入版頁面。

資料流是單向的,兩邊永遠一致:

    tools/bookmarks/_repos.json          (來源:GitHub API + 人工註解)
      └─ tools/bookmarks/gen_bookmarks.py
           └─ tools/bookmarks/楓之谷專案書籤.html   (單檔離線版)
                └─ 本腳本
                     └─ docs/70-resources/github-bookmarks/index.md

執行: python gen_github_bookmarks.py
"""
import io, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "tools", "bookmarks", "楓之谷專案書籤.html")
DST_DIR = os.path.join(HERE, "docs", "70-resources", "github-bookmarks")

if not os.path.exists(SRC):
    raise SystemExit(
        "找不到 %s\n先執行: python tools/bookmarks/gen_bookmarks.py" % SRC)

html = io.open(SRC, encoding="utf-8").read()
css = re.search(r"<style>(.*?)</style>", html, re.S).group(1)
body_js = re.search(r"<script>\n(.*?)</script>", html, re.S).group(1)
data = re.search(r"const DATA = (\[.*?\]);\n", body_js, re.S).group(1)
logic = re.sub(r"const DATA = \[.*?\];\n", "", body_js, flags=re.S)

# WIKI 版樣式:跟隨 mkdocs material 的亮/暗色,不用固定深色
css = css.replace(":root{--bg:#0f1115;--panel:#161a22;--panel2:#1b2029;--line:#262d3a;--fg:#e6e9ef;--dim:#8b95a7;--acc:#5aa9ff;--acc2:#7ee0a8}", "")
css = """
.md-typeset .bm-toolbar{display:flex;gap:9px;flex-wrap:wrap;align-items:center;margin:14px 0 12px}
.md-typeset .bm-toolbar input,.md-typeset .bm-toolbar select{
  background:var(--md-default-bg-color);border:1px solid var(--md-default-fg-color--lightest);
  color:var(--md-default-fg-color);border-radius:7px;padding:8px 11px;font-size:14px;outline:none}
.md-typeset .bm-toolbar input{flex:1;min-width:210px}
.md-typeset .bm-toolbar input:focus{border-color:var(--md-accent-fg-color)}
.md-typeset .bm-nav{display:flex;gap:6px;flex-wrap:wrap;margin:10px 0 4px}
.md-typeset .bm-nav button{background:transparent;border:1px solid var(--md-default-fg-color--lightest);
  color:var(--md-default-fg-color--light);border-radius:999px;padding:4px 12px;font-size:12.5px;cursor:pointer}
.md-typeset .bm-nav button:hover{color:var(--md-default-fg-color);border-color:var(--md-accent-fg-color)}
.md-typeset .bm-nav button.on{background:var(--md-accent-fg-color);border-color:var(--md-accent-fg-color);
  color:var(--md-primary-bg-color);font-weight:600}
.md-typeset .bm-count{color:var(--md-default-fg-color--light);font-size:12.5px;white-space:nowrap}
.md-typeset .bm-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:9px}
.md-typeset .bm-card{border:1px solid var(--md-default-fg-color--lightest);border-radius:9px;padding:11px 13px}
.md-typeset .bm-card:hover{border-color:var(--md-accent-fg-color)}
.md-typeset .bm-top{display:flex;justify-content:space-between;align-items:flex-start;gap:9px}
.md-typeset .bm-repo{font-weight:600;font-size:14px;word-break:break-all}
.md-typeset .bm-tags{display:flex;gap:4px;flex-wrap:wrap;justify-content:flex-end;max-width:112px}
.md-typeset .bm-tag{font-size:10.5px;border:1px solid var(--md-default-fg-color--lightest);
  color:var(--md-default-fg-color--light);border-radius:4px;padding:0 6px;white-space:nowrap}
.md-typeset .bm-tag.st{color:#b8860b;border-color:#b8860b55}
.md-typeset .bm-tag.ver{color:#7b52ab;border-color:#7b52ab55}
.md-typeset .bm-tag.live{color:#2e7d4f;border-color:#2e7d4f55}
.md-typeset .bm-tag.slow{color:#a07d20;border-color:#a07d2055}
.md-typeset .bm-tag.dead{color:#888}
.md-typeset .bm-tag.arch{color:#b04a4a;border-color:#b04a4a55}
.md-typeset .bm-desc{color:var(--md-default-fg-color--light);font-size:12.5px;margin-top:5px}
.md-typeset .bm-cn{font-size:13px;margin-top:7px;padding-left:9px;
  border-left:2px solid var(--md-accent-fg-color)}
.md-typeset .bm-empty{color:var(--md-default-fg-color--light);padding:34px;text-align:center}
.md-typeset .bm-sec{margin-bottom:28px}
.md-typeset .bm-sec h3{font-size:15.5px;margin:0 0 3px}
.md-typeset .bm-sec h3 .n{color:var(--md-accent-fg-color);font-size:12.5px}
.md-typeset .bm-hint{color:var(--md-default-fg-color--light);font-size:12.5px;margin:0 0 10px}
"""

js = (logic
      .replace("const qEl = document.getElementById('q');\n", "")
      .replace("const langEl = document.getElementById('lang');\n", "")
      .replace("const verEl = document.getElementById('ver');\n", "")
      .replace("const ageEl = document.getElementById('age');\n", "")
      .replace("let cat = \"\";\n", "")
      .replace("document.getElementById('main')", "document.getElementById('bmMain')")
      .replace("document.getElementById('nav')", "document.getElementById('bmNav')")
      .replace("document.getElementById('cnt')", "document.getElementById('bmCnt')")
      .replace("'<section><h2>'", "'<section class=\"bm-sec\"><h3>'")
      .replace("'</h2>'", "'</h3>'")
      .replace("'<p class=\"hint\">'", "'<p class=\"bm-hint\">'")
      .replace("'<div class=\"grid\">'", "'<div class=\"bm-grid\">'")
      .replace("'<div class=\"card\"><div class=\"top\">'", "'<div class=\"bm-card\"><div class=\"bm-top\">'")
      .replace("'<span class=\"tags\">'", "'<span class=\"bm-tags\">'")
      .replace("'<span class=\"tag ", "'<span class=\"bm-tag ")
      .replace("'<div class=\"desc\">'", "'<div class=\"bm-desc\">'")
      .replace("'<div class=\"cn\">'", "'<div class=\"bm-cn\">'")
      .replace("'<div class=\"empty\">'", "'<div class=\"bm-empty\">'")
      .replace("'<button class=\"'", "'<button class=\"bm-btn '"))

# 整段包進 IIFE,避免與 mkdocs material 的全域變數(cat 等)衝突
js = ("(function(){\n"
      "const DATA = __DATA__;\n"
      "let cat = \"\";\n"
      "const qEl = document.getElementById('bmQ');\n"
      "const langEl = document.getElementById('lang');\n"
      "const verEl = document.getElementById('ver');\n"
      "const ageEl = document.getElementById('age');\n"
      + js.rstrip() + "\n})();")

out = """# GitHub 專案書籤

!!! tip "想要乾淨的全屏書籤頁?"
    本頁嵌在 WIKI 版面裡(左側有導覽、右側有目錄)。若只要書籤本身,
    改用 **[全屏獨立版 →](../../standalone/)** —— 沒有任何框架元素,
    純粹是圖卡 + 一句話 + 連結,適合貼到別處或當速查表。

> **完整可互動版本**(單檔、離線、雙擊即開)位於
> `wiki/tools/bookmarks/楓之谷專案書籤.html`。
> 重新產生:`python tools/bookmarks/gen_bookmarks.py`。
>
> 本頁是同一份資料的網站內嵌版,可篩選版本 / 語言 / 維護狀態。
> 深度分析(IDA 位址、UI 類別、封包協議)請見本 WIKI 其他章節;
> 機器可讀的事實索引見 `wiki/docs/facts.json`。

## 快速篩選

<div class="bm-toolbar">
  <input type="search" id="bmQ" placeholder="搜尋專案名稱、用途說明、版本…（例如 v83 / wz / 解析度）">
  __LANG_OPTS__
  __VER_OPTS__
  __AGE_OPTS__
  <span class="bm-count" id="bmCnt"></span>
</div>
<div class="bm-nav" id="bmNav"></div>
<div id="bmMain"></div>

## 完整清單

!!! info "以下為靜態索引"
    上方的卡片可互動篩選;本表是同一份資料的純文字版,
    供站內搜尋與文字檢索使用(JS 動態渲染的內容不會被索引)。

__STATIC_TABLE__

<style>
__CSS__
</style>

<script>
__JS__
</script>
"""

import json as _j
langs = sorted({i["lang"] for c in _j.loads(data) for i in c["items"] if i["lang"]})
lang_opts = ('<select id="lang"><option value="">所有語言</option>'
             + "".join('<option value="%s">%s</option>' % (l, l) for l in langs) + "</select>")

from collections import Counter as _C
vers = _C(i["ver"] for c in _j.loads(data) for i in c["items"] if i["ver"])
ver_opts = ('<select id="ver"><option value="">所有版本</option>'
            + "".join('<option value="%s">%s</option>' % (v, v) for v, _ in vers.most_common()) + "</select>")

age_opts = ('<select id="age"><option value="">所有狀態</option>'
            '<option value="活躍">活躍 (1年內)</option><option value="維護中">維護中 (2年內)</option>'
            '<option value="靜止">靜止</option><option value="已封存">已封存</option></select>')


def esc(s):
    """Markdown table cells break on unescaped pipes."""
    return (s or "").replace("|", "\\|").replace("\n", " ").strip()


def static_table(cats):
    """A plain-markdown rendition of the same data.

    mkdocs builds its search index from the static markdown only, so a page
    whose content is injected by JavaScript is invisible to site search and to
    crawlers. Emitting the same rows as a table makes every project name
    findable while the interactive cards stay on top.
    """
    rows = [
        "| 專案 | ★ | 版本 | 語言 | 狀態 | 類別 | 用途 |",
        "|---|---|---|---|---|---|---|",
    ]
    total = 0
    for c in cats:
        for it in c["items"]:
            total += 1
            name = esc(it["full_name"])
            link = "[%s](%s)" % (name, it["url"])
            bits = [link]
            if it.get("stars"):
                bits.append(str(it["stars"]))
            bits.append(esc(it.get("ver") or "—"))
            bits.append(esc(it.get("lang") or "—"))
            bits.append(esc(it.get("age") or "—"))
            bits.append(esc(c["title"]))
            # the note is the reason to click, so it goes in full
            bits.append(esc(it.get("note") or it.get("desc") or ""))
            rows.append("| " + " | ".join(bits) + " |")
    rows.append("")
    rows.append("共 **%d** 個專案,分為 **%d** 類。" % (total, len(cats)))
    return "\n".join(rows)


_cats = _j.loads(data)
page = (out.replace("__CSS__", css)
           .replace("__JS__", js)
           .replace("__DATA__", data)
           .replace("__LANG_OPTS__", lang_opts)
           .replace("__VER_OPTS__", ver_opts)
           .replace("__AGE_OPTS__", age_opts)
           .replace("__STATIC_TABLE__", static_table(_cats)))

dst = os.path.join(DST_DIR, "index.md")
os.makedirs(DST_DIR, exist_ok=True)
io.open(dst, "w", encoding="utf-8").write(page)
print("written:", dst, os.path.getsize(dst), "bytes")
print("projects:", sum(len(c["items"]) for c in _cats))
print("static rows:", sum(len(c["items"]) for c in _cats))
