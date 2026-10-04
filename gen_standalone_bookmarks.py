#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""產生獨立全屏的專案書籤頁。

wiki 內的 70-resources/github-bookmarks/ 是嵌在 Material 版面裡的,帶側欄、
目錄與 admonition;本頁則是獨立網址的全螢幕版本,只留書籤本身:圖卡網格 +
一句話說明 + 分類膠囊 + 搜尋與篩選。

兩個頁面共用 tools/bookmarks/_repos.json,所以不會漂移:
    tools/bookmarks/gen_bookmarks.py   → 單���離線 HTML(本地用)
    gen_standalone_bookmarks.py       → 本頁(線上獨立網址)
    gen_github_bookmarks.py           → wiki 內嵌版

Run:  python gen_standalone_bookmarks.py
"""
import glob
import io
import json
import os
import re
from collections import Counter

REPO = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(REPO, "tools", "bookmarks", "_repos.json")
OUT_DIR = os.path.join(REPO, "docs", "bookmarks")
OUT = os.path.join(OUT_DIR, "index.md")

# 取既有分類定義,避免這裡再寫一份
GEN = open(os.path.join(REPO, "tools", "bookmarks", "gen_bookmarks.py"),
           encoding="utf-8").read()
CATS = eval("[" + re.search(r"CATS = \[(.*?)\n\]", GEN, re.S).group(1) + "]")
MANUAL = eval("{" + re.search(r"MANUAL = \{(.*?)\n\}", GEN, re.S).group(1) + "}")

rows = json.load(open(DATA, encoding="utf-8"))
by_name = {r["full_name"]: r for r in rows}


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;") \
                  .replace(">", "&gt;").replace('"', "&quot;")


def pick(fn):
    for key, _t, _h in CATS:
        if MANUAL.get(fn) == key:
            return key
    return "misc"


groups = {}
for r in rows:
    groups.setdefault(pick(r["full_name"]), []).append(r)
for k in groups:
    groups[k].sort(key=lambda r: -r["stars"])

# GitHub 頭像:用 avatar 路徑,避免再引入外部服務
def avatar(fn, size=64):
    return "https://avatars.githubusercontent.com/" + fn


langs = sorted({r.get("lang") for r in rows if r.get("lang")})
vers = Counter(r.get("_ver") for r in rows if r.get("_ver"))
ages = ["活躍", "維護中", "靜止", "已封存"]

css = """
:root{--bg:#080b11;--bg1:#0e131c;--bg2:#141a26;--bg3:#1c2434;
 --line:#232d3f;--line2:#2e3a4f;--fg0:#e8edf5;--fg1:#a8b4c8;--fg2:#6b7a91;
 --ac:#22d3ee;--warn:#fbbf24;--ok:#34d399}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg0);
 font:15px/1.7 "Inter","Segoe UI","PingFang TC","Microsoft JhengHei",system-ui,sans-serif}
.wrap{max-width:1560px;margin:0 auto;padding:26px 20px 70px}
header{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;margin-bottom:6px}
h1{font-size:24px;font-weight:700;letter-spacing:-.02em;margin:0}
.count{color:var(--fg2);font-size:13px}
.count b{color:var(--ac)}
.hint{color:var(--fg2);font-size:13px;margin:0 0 16px}
.back{display:inline-block;margin-top:18px;color:var(--fg1);font-size:13px;
 text-decoration:none;border:1px solid var(--line);border-radius:8px;padding:5px 11px}
.back:hover{color:var(--ac);border-color:var(--ac);text-decoration:none}
.bar{display:flex;gap:9px;flex-wrap:wrap;align-items:center;margin:0 0 12px;
 position:sticky;top:0;background:var(--bg);padding:10px 0;z-index:5;
 border-bottom:1px solid var(--line)}
input[type=search],select{background:var(--bg2);border:1px solid var(--line);
 color:var(--fg0);border-radius:8px;padding:9px 12px;font-size:14px;outline:none}
input[type=search]{flex:1;min-width:240px}
input[type=search]:focus,select:focus{border-color:var(--ac);
 box-shadow:0 0 0 3px rgba(34,211,238,.12)}
.pills{display:flex;gap:7px;flex-wrap:wrap;margin:0 0 18px}
.pill{background:var(--bg1);border:1px solid var(--line);color:var(--fg1);
 border-radius:999px;padding:5px 14px;font-size:12.5px;cursor:pointer;transition:.12s}
.pill:hover{color:var(--fg0);border-color:var(--line2)}
.pill.on{background:var(--ac);border-color:var(--ac);color:#04121a;font-weight:600}
h2{font-size:14px;font-weight:600;color:var(--fg1);margin:26px 0 3px;
 display:flex;align-items:baseline;gap:8px}
h2 span{color:var(--fg2);font-size:12px;font-weight:400}
h2 .desc{color:var(--fg2);font-size:12.5px;font-weight:400;margin:0 0 12px;
 display:block;letter-spacing:0}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(292px,1fr));gap:11px}
.card{background:var(--bg1);border:1px solid var(--line);border-radius:12px;
 padding:14px 15px;display:flex;gap:12px;transition:.14s}
.card:hover{border-color:var(--ac);transform:translateY(-2px);background:var(--bg2)}
.ico{width:40px;height:40px;flex-shrink:0;border-radius:9px;background:var(--bg3);
 display:grid;place-items:center;font-size:17px;font-weight:700;color:var(--ac)}
.meta{min-width:0;flex:1}
.name{font-weight:600;font-size:14px;color:var(--fg0);word-break:break-all;
 text-decoration:none;display:block}
.name:hover{color:var(--ac);text-decoration:none}
.tags{display:flex;gap:4px;flex-wrap:wrap;margin:5px 0 6px}
.tag{font-size:10.5px;border:1px solid var(--line2);color:var(--fg2);
 border-radius:4px;padding:0 6px;white-space:nowrap}
.tag.st{color:#ffd479;border-color:#4a3d22}
.tag.ver{color:#c792ea;border-color:#3d2f52}
.tag.live{color:var(--ok);border-color:#26452f}
.tag.slow{color:var(--warn);border-color:#4d402a}
.tag.dead{color:var(--fg2)}
.note{font-size:12.5px;color:var(--fg1);line-height:1.6}
.empty{color:var(--fg2);padding:60px;text-align:center}
@media(max-width:600px){.grid{grid-template-columns:1fr}.wrap{padding:18px 14px 60px}}
@media(prefers-color-scheme:light){
 body{--bg:#f6f8fc;--bg1:#fff;--bg2:#eef2f8;--bg3:#e4eaf3;
  --line:#d9e0ec;--line2:#c3cddd;--fg0:#0f1729;--fg1:#3d4a60;--fg2:#6b7a91;
  --ac:#0891b2;--warn:#b45309;--ok:#047857}
 .pill.on{color:#fff}.ico{color:#0891b2}
}
"""

js = """
const DATA=__DATA__, CATS=__CATS__;
let cat='';
const $=id=>document.getElementById(id);
function esc(s){return (s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function initial(s){return (s||'?').replace(/^\\//,'').charAt(0).toUpperCase()}
function buildNav(){
 $('pills').innerHTML='<button class="pill'+(cat===''?' on':'')+'" data-c="">全部 ('+DATA.reduce((a,c)=>a+c.items.length,0)+')</button>'+
  DATA.map(c=>'<button class="pill'+(cat===c.key?' on':'')+'" data-c="'+c.key+'">'+esc(c.title.replace(/^★\\s*/,''))+' ('+c.items.length+')</button>').join('');
 document.querySelectorAll('.pill').forEach(b=>b.onclick=()=>{cat=b.dataset.c;buildNav();render()});
}
function render(){
 const q=$('q').value.trim().toLowerCase(), lg=$('lang').value,
       vv=$('ver').value, ag=$('age').value;
 let shown=0, out='';
 for(const c of DATA){
  if(cat && c.key!==cat) continue;
  const items=c.items.filter(it=>{
   if(lg && it.lang!==lg) return false;
   if(vv && it.ver!==vv) return false;
   if(ag && it.age!==ag) return false;
   if(!q) return true;
   return (it.full_name+' '+it.note+' '+(it.lang||'')+' '+(it.ver||'')).toLowerCase().includes(q);
  });
  if(!items.length) continue;
  shown+=items.length;
  out+='<h2>'+esc(c.title.replace(/^★\\s*/,''))+'<span>'+items.length+' 個</span></h2>'+
   '<p class="desc">'+esc(c.hint)+'</p><div class="grid">'+items.map(it=>{
    let t='';
    if(it.stars) t+='<span class="tag st">★ '+it.stars+'</span>';
    if(it.ver)  t+='<span class="tag ver">'+esc(it.ver)+'</span>';
    if(it.lang) t+='<span class="tag">'+esc(it.lang)+'</span>';
    if(it.age){const k=it.age==='活躍'?'live':(it.age==='維護中'?'slow':'dead');t+='<span class="tag '+k+'">'+esc(it.age)+'</span>';}
    return '<div class="card"><div class="ico">'+initial(it.full_name)+'</div><div class="meta">'+
     '<a class="name" href="'+esc(it.url)+'" target="_blank" rel="noopener">'+esc(it.full_name)+'</a>'+
     '<div class="tags">'+t+'</div><div class="note">'+esc(it.note)+'</div></div></div>';
   }).join('')+'</div>';
 }
 $('main').innerHTML = shown ? out : '<div class="empty">找不到符合的專案</div>';
 $('cnt').innerHTML = '顯示 <b>'+shown+'</b> / '+DATA.reduce((a,c)=>a+c.items.length,0)+' 個';
}
$('q').addEventListener('input',render);
$('lang').addEventListener('change',render);
$('ver').addEventListener('change',render);
$('age').addEventListener('change',render);
buildNav();render();
"""


def main():
    lang_opts = "".join('<option value="%s">%s</option>' % (l, l) for l in langs)
    ver_opts = "".join('<option value="%s">%s</option>' % (v, v)
                        for v, _ in vers.most_common())
    age_opts = "".join('<option value="%s">%s</option>' % (a, a) for a in ages)

    data = [{
        "key": k,
        "title": t,
        "hint": h,
        "items": [{
            "full_name": r["full_name"], "url": r["url"], "stars": r["stars"],
            "lang": r.get("lang") or "", "ver": r.get("_ver") or "",
            "age": r.get("_age") or "", "note": r.get("note") or r.get("desc") or "",
        } for r in groups.get(k, [])]
    } for k, t, h in CATS]

    total = sum(len(c["items"]) for c in data)
    # 相對於 standalone/ 的 WIKI 內嵌版路徑
    back = "../70-resources/github-bookmarks/"

    # 這是一支獨立 HTML,不經 mkdocs:沒有側欄、目錄、頁首,就是一張書籤頁。
    html = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>楓之谷 v83 專案書籤</title>
<meta name="description" content="{total} 個楓之谷 v83 二次開發社群專案,依用途分類">
<style>
{css}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>楓之谷 v83 專案書籤</h1>
  <span class="count">共 <b>{total}</b> 個專案 · {len(data)} 類</span>
</header>
<p class="hint">只給「名稱 + 一句話 + 連結」。需要完整靜態清單與版本/維護狀態篩選請看
<a href="{back}" style="color:var(--ac)">WIKI 內嵌版</a>。</p>

<div class="bar">
  <input type="search" id="q" placeholder="搜尋專案名稱、用途說明、版本…（例如 v83 / wz / 解析度）">
  <select id="lang"><option value="">所有語言</option>{lang_opts}</select>
  <select id="ver"><option value="">所有版本</option>{ver_opts}</select>
  <select id="age"><option value="">所有狀態</option>{age_opts}</select>
  <span class="count" id="cnt"></span>
</div>
<div class="pills" id="pills"></div>

<div id="main"></div>

<a class="back" href="{back}">← WIKI 內嵌版(含完整靜態清單)</a>
</div>

<script>
{js.replace("__DATA__", json.dumps(data, ensure_ascii=False))
   .replace("__CATS__", json.dumps([], ensure_ascii=False))}
</script>
</body>
</html>
"""

    # 直接寫進 docs/ 之外的 standalone/,部署時複製到 site/standalone/
    out_dir = os.path.join(REPO, "standalone")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "index.html")
    io.open(out, "w", encoding="utf-8").write(html)
    print("written: %s (%d bytes, %d projects)"
          % (out, os.path.getsize(out), total))


if __name__ == "__main__":
    main()
