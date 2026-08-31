"""videos.html の「IDが空なら埋め込まない／入れたら埋め込む」を実行証明する。"""
import json, pathlib, subprocess, sys, shutil
repo = pathlib.Path.home()/"projects/asahihomu-ssw-site"
sj = repo/"site.json"; orig = sj.read_text(encoding="utf-8")
fails = []
def build():
    subprocess.run([sys.executable, "build.py"], cwd=repo, capture_output=True, check=True)
    return (repo/"dist/videos.html").read_text(encoding="utf-8")
try:
    # ① 全IDを空にする＝埋め込み0・準備中3・目次0
    #    （現物の site.json が空かどうかに依存させない＝IDを入れた後でもこの検査は成立する）
    d = json.loads(orig)
    for it in d["videos"]["items"]: it["youtube_id"] = ""
    sj.write_text(json.dumps(d, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    h = build()
    if h.count("<iframe") != 0: fails.append(f"ID空なのに iframe {h.count('<iframe')} 件")
    if h.count("準備中") != 3: fails.append(f"ID空で準備中が3件でない: {h.count('準備中')}")
    if "chapter-list" in h: fails.append("ID空なのに目次が出ている")
    print(f"① ID空: iframe={h.count('<iframe')} 準備中={h.count('準備中')} 目次={'有' if 'chapter-list' in h else '無'}")
    # ② 1本だけIDを入れる＝埋め込み1・準備中2・目次8
    d = json.loads(orig)
    for it in d["videos"]["items"]: it["youtube_id"] = ""
    d["videos"]["items"][0]["youtube_id"] = "TESTvideoID"
    sj.write_text(json.dumps(d, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    h = build()
    n_ch = h.count('<li><span class="chapter-list__t">')
    if h.count("<iframe") != 1: fails.append(f"ID1本で iframe が1件でない: {h.count('<iframe')}")
    if "TESTvideoID" not in h: fails.append("設定したIDが出力に無い")
    if h.count("準備中") != 2: fails.append(f"残り2本の準備中が出ていない: {h.count('準備中')}")
    want_ch = len(json.loads(orig)["videos"]["items"][0]["chapters"])  # 章数は site.json が正（literal で固定しない）
    if n_ch != want_ch: fails.append(f"目次が{want_ch}件でない: {n_ch}")
    if "youtube-nocookie.com" not in h: fails.append("nocookie ドメインを使っていない")
    print(f"② ID1本: iframe={h.count('<iframe')} 準備中={h.count('準備中')} 目次={n_ch}件/{want_ch} nocookie={'youtube-nocookie.com' in h}")
finally:
    sj.write_text(orig, encoding="utf-8")
    subprocess.run([sys.executable, "build.py"], cwd=repo, capture_output=True)
h = (repo/"dist/videos.html").read_text(encoding="utf-8")
if sj.read_text(encoding="utf-8") != orig: fails.append("site.json が元に戻っていない")
want = sum(1 for it in json.loads(orig)["videos"]["items"] if it["youtube_id"])
if h.count("<iframe") != want: fails.append(f"復元後の iframe が {want} 件でない: {h.count('<iframe')}")
for it in json.loads(orig)["videos"]["items"]:
    if it["youtube_id"] and it["youtube_id"] not in h: fails.append(f"復元後に {it['slug']} のIDが出力に無い")
print("③ 復元: site.json一致 / iframe=%d（元の非空ID %d 件と一致が正）" % (h.count("<iframe"), want))
print("=" * 50)
if fails:
    print("🔴 " + " / ".join(fails)); sys.exit(1)
print("🟢 全て通過（空=載せない／設定=載る／復元も確認）")
