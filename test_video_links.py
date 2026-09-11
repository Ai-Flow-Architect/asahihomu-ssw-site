"""動画ページ ⇔ お役立ち記事 の相互リンクを実行証明する（2026-09-11・8/7 のお約束の履行）。

① videos.html の各動画に related_posts の記事リンクが出る／各動画に id がある
② related_posts の各記事ページに videos.html#<動画slug> が出る
③ 存在しない slug を related_posts に入れるとビルドが止まる（リンク切れを公開しない）
"""
import json, pathlib, subprocess, sys
repo = pathlib.Path.home()/"projects/asahihomu-ssw-site"
sj = repo/"site.json"; orig = sj.read_text(encoding="utf-8")
fails = []


def build():
    return subprocess.run([sys.executable, "build.py"], cwd=repo, capture_output=True, text=True)


try:
    r = build()
    if r.returncode != 0:
        fails.append("通常ビルドが失敗: " + (r.stderr or r.stdout)[-200:])
    vids = json.loads(orig)["videos"]["items"]
    vh = (repo/"dist/videos.html").read_text(encoding="utf-8")
    n_rel = 0
    for v in vids:
        if 'id="%s"' % v["slug"] not in vh:
            fails.append("videos.html に id=%s が無い" % v["slug"])
        for s in v.get("related_posts", []):
            n_rel += 1
            if 'href="%s.html"' % s not in vh:
                fails.append("videos.html に %s への記事リンクが無い" % s)
            ph = (repo/"dist"/(s + ".html")).read_text(encoding="utf-8")
            if 'href="videos.html#%s"' % v["slug"] not in ph:
                fails.append("%s.html に videos.html#%s が無い" % (s, v["slug"]))
    if n_rel == 0:
        fails.append("related_posts が1件も無い（空虚な検査）")
    print("①② 相互リンク %d 本を検査" % n_rel)
    # ③ 存在しない slug はビルドを止める
    d = json.loads(orig)
    d["videos"]["items"][0].setdefault("related_posts", []).append("blog-does-not-exist")
    sj.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    r = build()
    if r.returncode == 0:
        fails.append("存在しない slug でもビルドが通った")
    print("③ 存在しない slug: ビルド rc=%d（0以外が正）" % r.returncode)
finally:
    sj.write_text(orig, encoding="utf-8")
    build()
if sj.read_text(encoding="utf-8") != orig:
    fails.append("site.json が元に戻っていない")
print("=" * 50)
if fails:
    print("🔴 " + " / ".join(fails)); sys.exit(1)
print("🟢 全て通過（動画⇔記事の相互リンク／リンク切れはビルドで止まる／復元も確認）")
