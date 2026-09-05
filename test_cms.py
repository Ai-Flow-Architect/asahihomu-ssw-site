#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CMS 記事（content/cms_posts.json → build.py）と fetch_cms.py を実ビルドで検証する。

T1 JSONなし＝従来どおり / T2 fixture 2本＝ページ・一覧順・sitemap・JSON-LD・checks緑
T3 slug不正 / T4 slug衝突・重複 / T5 危険HTML / T6 本番モードでCMS本文の「準備中」は落とさない
T7 fetch 鍵なし＝JSONを触らない / T8 fetch ページング完走（ローカルHTTPサーバー） / T9 docs/ 無変更

終了時に JSON・site.json・dist を復元する（test_videos.py と同じ流儀）。
環境変数 ASAHI_ROOT でリポの場所を差し替えられる（変異テスト用）。
"""
import http.server
import json
import os
import pathlib
import re
import subprocess
import sys
import threading

ROOT = pathlib.Path(os.environ.get("ASAHI_ROOT") or pathlib.Path(__file__).resolve().parent)
JSON_PATH = ROOT / "content" / "cms_posts.json"
SITE = ROOT / "site.json"
PY = sys.executable
fails = []


def run(*args, env=None):
    return subprocess.run([PY, *args], cwd=ROOT, capture_output=True, text=True, env=env)


def build():
    return run("build.py")


def write_posts(posts):
    JSON_PATH.parent.mkdir(exist_ok=True)
    JSON_PATH.write_text(json.dumps({"fetched_at": "test", "posts": posts}, ensure_ascii=False),
                         encoding="utf-8")


def post(slug, date, title="テスト記事", body="<p>本文</p>", **kw):
    d = {"slug": slug, "title": title, "description": "", "category": "制度解説",
         "date": date, "body": body, "eyecatch": ""}
    d.update(kw)
    return d


def check(cond, msg):
    if not cond:
        fails.append(msg)


def expect_fail(posts, label):
    write_posts(posts)
    r = build()
    check(r.returncode != 0, "%s: ビルドが止まらなかった" % label)
    return r


orig_json = JSON_PATH.read_bytes() if JSON_PATH.exists() else None
orig_site = SITE.read_bytes()
try:
    # ---- T1 JSONなし ----
    if JSON_PATH.exists():
        JSON_PATH.unlink()
    r = build()
    check(r.returncode == 0, "T1: JSONなしでビルド失敗: " + r.stderr[-300:])
    n_static = len(list((ROOT / "dist").glob("*.html")))
    blog = (ROOT / "dist" / "blog.html").read_text(encoding="utf-8")
    check("{{" not in blog, "T1: blog.html に未置換トークン")
    check(not list((ROOT / "dist").glob("blog-t2-*.html")), "T1: JSONなしなのにCMSページがある")
    print("T1 JSONなし: %d ページ・CMSページ0" % n_static)

    # ---- T2 fixture 2本 ----
    yt = '<iframe src="https://www.youtube-nocookie.com/embed/abc123" allowfullscreen></iframe>'
    write_posts([
        post("t2-older", "2026-09-10", title="A&B 更新のポイント",
             body="<p>古い方。&amp; を含む本文。</p>" + yt,
             eyecatch="https://images.microcms-assets.io/x/a.jpg"),
        post("t2-newer", "2026-09-20", title="新しい記事", body="<h2>見出し</h2><p>新しい方</p>"),
    ])
    r = build()
    check(r.returncode == 0, "T2: ビルド失敗: " + r.stderr[-300:])
    dist = ROOT / "dist"
    check((dist / "blog-t2-older.html").exists() and (dist / "blog-t2-newer.html").exists(),
          "T2: CMSページが生成されていない")
    check(len(list(dist.glob("*.html"))) == n_static + 2, "T2: ページ数が +2 でない")
    blog = (dist / "blog.html").read_text(encoding="utf-8")
    i_new, i_old, i_static = (blog.find("blog-t2-newer.html"), blog.find("blog-t2-older.html"),
                              blog.find("blog-illegal-work.html"))
    check(0 <= i_new < i_old < i_static, "T2: 一覧の並びが date 降順→静的 でない (%d,%d,%d)" % (i_new, i_old, i_static))
    check("A&amp;B" in blog and "&amp;amp;" not in blog, "T2: タイトルのエスケープが二重/欠落")
    sm = (dist / "sitemap.xml").read_text(encoding="utf-8")
    check("blog-t2-older.html" in sm and "blog-t2-newer.html" in sm, "T2: sitemap に載っていない")
    older = (dist / "blog-t2-older.html").read_text(encoding="utf-8")
    check('"@type": "BlogPosting"' in older and '"datePublished": "2026-09-10"' in older,
          "T2: BlogPosting/日付が無い")
    check('"image": "https://images.microcms-assets.io/x/a.jpg"' in older, "T2: JSON-LD に image が無い")
    check("youtube-nocookie.com/embed/abc123" in older, "T2: YouTube 埋め込みが通っていない")
    m = re.search(r'<meta name="description" content="([^"]*)"', older)
    check(m and "<" not in m.group(1), "T2: meta description にタグ混入")
    check("2026.09.10 更新" in older and "制度解説" in older, "T2: 日付/カテゴリ表示が無い")
    check('name="robots" content="noindex,nofollow"' in older, "T2: preview 中なのに noindex でない")
    r = run("checks.py")
    check(r.returncode == 0, "T2: checks.py が赤: " + r.stdout[-400:])
    print("T2 fixture2本: ページ+2・並び順OK・sitemap/JSON-LD OK・checks %s" % ("緑" if r.returncode == 0 else "赤"))

    # ---- T3 slug 不正 ----
    for bad in ["Bad Slug", "ビザ更新", "ab", "a" * 61, "under_score"]:
        expect_fail([post(bad, "2026-09-01")], "T3 slug=%r" % bad)
    print("T3 slug不正 5種: 全て停止")

    # ---- T4 衝突・重複 ----
    expect_fail([post("cost", "2026-09-01")], "T4 既存記事 blog-cost と衝突")
    expect_fail([post("dup", "2026-09-01"), post("dup", "2026-09-02")], "T4 JSON内重複")
    expect_fail([post("no-title", "2026-09-01", title="  ")], "T4 タイトル空")
    expect_fail([post("bad-date", "2026/09/01")], "T4 日付形式")
    print("T4 衝突/重複/空タイトル/日付: 全て停止")

    # ---- T5 危険HTML ----
    for label, body in [
        ("script", "<p>x</p><script>alert(1)</script>"),
        ("SCRIPT大文字", "<SCRIPT src=x></SCRIPT>"),
        ("onerror", '<img src="x" onerror="alert(1)">'),
        ("javascript:", '<a href="javascript:alert(1)">x</a>'),
        ("iframe他社", '<iframe src="https://evil.example/x"></iframe>'),
        ("object", "<object data='x'></object>"),
    ]:
        expect_fail([post("t5-x", "2026-09-01", body=body)], "T5 %s" % label)
    print("T5 危険HTML 6種: 全て停止（YouTube iframe は T2 で通過）")

    # ---- T6 本番モードで CMS 本文の「準備中」は落とさない ----
    write_posts([post("t6-junbi", "2026-09-01", body="<p>次回の説明会は準備中です。</p>")])
    site = json.loads(orig_site.decode("utf-8"))
    site["site"]["preview"] = False
    SITE.write_text(json.dumps(site, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    r = build()
    check(r.returncode == 0, "T6: ビルド失敗")
    r = run("checks.py")
    hit = [l for l in r.stdout.splitlines() if "blog-t6-junbi.html" in l and "準備中" in l]
    check(not hit, "T6: CMS記事の「準備中」で checks.py が落ちた: %s" % hit)
    SITE.write_bytes(orig_site)
    print("T6 本番モード: CMS本文の「準備中」は指摘されない")

    # ---- T7 fetch 鍵なし ----
    write_posts([post("t7-keep", "2026-09-01")])
    before = JSON_PATH.read_bytes()
    env = {k: v for k, v in os.environ.items() if not k.startswith("MICROCMS_")}
    r = run("fetch_cms.py", env=env)
    check(r.returncode == 0, "T7: 鍵なしで exit≠0")
    check(JSON_PATH.read_bytes() == before, "T7: 鍵なしなのに JSON を書き換えた")
    r = run("fetch_cms.py", "--require-key", env=env)
    check(r.returncode != 0, "T7: --require-key なのに鍵なしで通った")
    print("T7 fetch 鍵なし: exit 0・JSON 不変／--require-key は停止")

    # ---- T8 fetch ページング（1件ずつ返すサーバーで2件を完走） ----
    ITEMS = [
        {"id": "1", "slug": "page-one", "title": "一件目", "body": "<p>A &amp; B</p>",
         "category": ["制度解説"], "publishedAt": "2026-08-31T16:00:00.000Z"},   # JST 9/1
        {"id": "2", "slug": "page-two", "title": "二件目", "body": "<p>二</p>",
         "category": "費用", "date": "2026-09-15T00:00:00.000Z",
         "eyecatch": {"url": "https://images.microcms-assets.io/x/b.png"}},
    ]
    seen = []

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            seen.append(self.path)
            off = int(re.search(r"offset=(\d+)", self.path).group(1))
            if self.headers.get("X-MICROCMS-API-KEY") != "k":
                self.send_response(401); self.end_headers(); return
            body = json.dumps({"contents": ITEMS[off:off + 1], "totalCount": len(ITEMS),
                               "offset": off, "limit": 1}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.end_headers(); self.wfile.write(body)

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    env = dict(os.environ, MICROCMS_SERVICE_DOMAIN="http://127.0.0.1:%d" % srv.server_port,
               MICROCMS_API_KEY="k")
    r = run("fetch_cms.py", env=env)
    srv.shutdown()
    check(r.returncode == 0, "T8: fetch 失敗: " + r.stderr[-300:])
    got = json.loads(JSON_PATH.read_text(encoding="utf-8"))["posts"] if r.returncode == 0 else []
    check(len(got) == 2, "T8: 2件取れていない（1ページ目で止まった？） 取得=%d 要求=%s" % (len(got), seen))
    check([p["slug"] for p in got] == ["page-two", "page-one"], "T8: date 降順でない: %s" % [p["slug"] for p in got])
    check(got and got[-1]["date"] == "2026-09-01", "T8: publishedAt の JST 変換が違う: %s" % (got and got[-1]["date"]))
    check(got and got[0]["date"] == "2026-09-15", "T8: date フィールド優先でない")
    check(got and got[-1]["description"] == "A & B", "T8: description のタグ除去/実体復元が違う: %r" % (got and got[-1]["description"]))
    check(got and got[-1]["category"] == "制度解説", "T8: セレクト(配列)の先頭を取っていない")
    check(got and got[0]["eyecatch"].endswith("b.png"), "T8: eyecatch URL が取れていない")
    check("警告" in r.stderr and "t7-keep" in r.stderr, "T8: 消えた slug の警告が出ていない")
    r = build()
    check(r.returncode == 0, "T8: fetch した JSON でビルド失敗: " + r.stderr[-300:])
    print("T8 fetch ページング: 2件完走・JST日付・description・警告 OK")
finally:
    if orig_json is None:
        if JSON_PATH.exists():
            JSON_PATH.unlink()
    else:
        JSON_PATH.write_bytes(orig_json)
    SITE.write_bytes(orig_site)
    build()

# ---- T9 docs/ 無変更（git 管理下のときだけ） ----
if (ROOT / ".git").exists():
    st = subprocess.run(["git", "status", "--porcelain", "docs"], cwd=ROOT, capture_output=True, text=True).stdout
    check(st.strip() == "", "T9: docs/ に差分が出た:\n" + st)
    print("T9 docs/: 差分なし")

print("=" * 50)
if fails:
    print("🔴 %d 件\n  - " % len(fails) + "\n  - ".join(fails))
    sys.exit(1)
print("🟢 全て通過（T1〜T9）")
