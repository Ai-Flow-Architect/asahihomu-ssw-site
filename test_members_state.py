"""members.html の「鍵が揃えば準備中が消える／欠ければ出る」を実行証明する。

2026-09-02 新設。8/31 にガイドブックPDF（download.guidebook_url）を配置したのに、
ページは「ガイドブックは現在準備中です」と手打ちの文言を言い続けていた＝
**実物が進んでも文言が追従しない**状態だった。文言を build.py で
download.{guidebook_url, form_endpoint} から機械生成する形に変えたので、
「消えるべき時に消える」ことをここで実行証明する（消し忘れを人の記憶に頼らない）。
"""
import json, pathlib, subprocess, sys
repo = pathlib.Path.home()/"projects/asahihomu-ssw-site"
sj = repo/"site.json"; orig = sj.read_text(encoding="utf-8")
fails = []
BAD = ["準備中", "デモ表示"]


def build(guide, endpoint):
    d = json.loads(orig)
    d["download"]["guidebook_url"] = guide
    d["download"]["form_endpoint"] = endpoint
    sj.write_text(json.dumps(d, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    subprocess.run([sys.executable, "build.py"], cwd=repo, capture_output=True, check=True)
    return (repo/"dist/members.html").read_text(encoding="utf-8")


try:
    # ① 両方揃う＝本番動作。制作途中の文言は1つも出ない
    h = build("assets/docs/tokutei-ginou-guidebook.pdf", "https://example.invalid/f/dl")
    left = [w for w in BAD if w in h]
    if left: fails.append("両方設定なのに残っている文言: " + " / ".join(left))
    if "ダウンロードできます" not in h: fails.append("本番の文言（ダウンロードできます）が出ていない")
    if 'data-endpoint="https://example.invalid/f/dl"' not in h: fails.append("送信先がフォームに入っていない")
    print("① 両方設定: 制作途中の文言=%d件 本番文言=%s" % (len(left), "ダウンロードできます" in h))

    # ② 送信先だけ空＝受付が動かない。準備中/デモ表示を必ず出す（黙って本番の顔をしない）
    h = build("assets/docs/tokutei-ginou-guidebook.pdf", "")
    miss = [w for w in BAD if w not in h]
    if miss: fails.append("送信先が空なのに出ていない文言: " + " / ".join(miss))
    if "ダウンロードできます" in h: fails.append("送信先が空なのに本番の文言が出ている")
    print("② 送信先のみ空: 準備中=%s デモ表示=%s" % ("準備中" in h, "デモ表示" in h))

    # ③ PDFだけ空＝同じく受付は動かない
    h = build("", "https://example.invalid/f/dl")
    miss = [w for w in BAD if w not in h]
    if miss: fails.append("PDFが空なのに出ていない文言: " + " / ".join(miss))
    print("③ PDFのみ空: 準備中=%s デモ表示=%s" % ("準備中" in h, "デモ表示" in h))
finally:
    sj.write_text(orig, encoding="utf-8")
    subprocess.run([sys.executable, "build.py"], cwd=repo, capture_output=True)

if sj.read_text(encoding="utf-8") != orig: fails.append("site.json が元に戻っていない")
h = (repo/"dist/members.html").read_text(encoding="utf-8")
d = json.loads(orig)["download"]
ready = bool(d.get("guidebook_url")) and bool(d.get("form_endpoint"))
if ready and any(w in h for w in BAD): fails.append("復元後: 鍵が揃っているのに制作途中の文言がある")
if not ready and not all(w in h for w in BAD): fails.append("復元後: 鍵が欠けているのに制作途中の文言が無い")
print("④ 復元: site.json一致 / 現物は %s" % ("本番動作" if ready else "受付準備中（鍵が未設定）"))
print("=" * 50)
if fails:
    print("🔴 " + " / ".join(fails)); sys.exit(1)
print("🟢 全て通過（揃えば消える／欠ければ出る／復元も確認）")
