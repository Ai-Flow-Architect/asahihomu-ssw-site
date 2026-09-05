#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_cms.py が「守りを外すと赤くなる」ことを実行証明する（通ることは落ちる証明にならない）。

リポを一時ディレクトリへコピーし、守りを1つずつ壊して test_cms.py を当てる。
全ミュータントが赤（exit≠0）で緑。1つでも緑のままなら検査に穴がある。
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile
import os

ROOT = pathlib.Path(__file__).resolve().parent
PY = sys.executable
SKIP = {".git", "dist", "docs", "screenshots", "__pycache__", ".claude"}

MUTANTS = [
    ("build.py", 'SLUG_RE = re.compile(r"^[a-z0-9-]{3,60}$")', 'SLUG_RE = re.compile(r"^.+$")', "T3 slug正規表現を緩める"),
    ("build.py", "if full in static_slugs or full in seen:", "if False:", "T4 衝突/重複検査を外す"),
    ("build.py", "return sorted(pages, key=lambda x: x[\"date\"], reverse=True)", "return pages", "T2 date降順ソートを外す"),
    ("build.py", "(script|object|embed|form|meta|link|style)", "(object|embed|form|meta|link|style)", "T5 <script> 検査を外す"),
    ("build.py", "if EVENT_ATTR_RE.search(body):", "if False:", "T5 on*= 検査を外す"),
    ("build.py", "if not m.group(1).startswith(IFRAME_OK):", "if False:", "T5 iframe 送信元検査を外す"),
    ("build.py", "if not DATE_RE.match(p.get(\"date\", \"\")):", "if False:", "T4 日付検査を外す"),
    ("fetch_cms.py", "if not page or offset >= total:", "if True:", "T8 ページングを1ページで止める"),
    ("fetch_cms.py", "html.unescape(TAG_RE.sub(\"\", body))", "TAG_RE.sub(\"\", body)", "T8 実体参照の復元を外す"),
    ("fetch_cms.py", "d.astimezone(JST)", "d", "T8 JST変換を外す"),
    ("fetch_cms.py", "if not url:", "if url is None and False:", "T7 鍵なしフォールバックを外す"),
    ("checks.py", "if f.name in cms_names:", "if False:", "T6 CMS記事の文言検査除外を外す"),
    ("fetch_cms.py", 'if "--require-key" in sys.argv:', "if False:", "T7 CIの鍵必須を外す"),
    ("checks.py", '.split("›") if t.strip()]', '.replace("›", " ").split()]', "T2 パンくず検査を空白区切りに戻す"),
]


def main():
    bad = []
    for fname, old, new, label in MUTANTS:
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="asahi_mut_"))
        for item in ROOT.iterdir():
            if item.name in SKIP:
                continue
            (shutil.copytree if item.is_dir() else shutil.copy2)(item, tmp / item.name)
        src = (tmp / fname).read_text(encoding="utf-8")
        if old not in src:
            bad.append("%s: 変異対象の文字列が %s に無い（本体が変わった＝ミュータント更新が要る）" % (label, fname))
            shutil.rmtree(tmp); continue
        (tmp / fname).write_text(src.replace(old, new, 1), encoding="utf-8")
        r = subprocess.run([PY, str(tmp / "test_cms.py")], cwd=tmp, capture_output=True, text=True,
                           env=dict(os.environ, ASAHI_ROOT=str(tmp)))
        tid = label.split()[0]
        hit = r.returncode != 0 and tid in r.stdout
        print("%s %s" % ("撃墜" if hit else "生存🔴", label))
        if not hit:
            bad.append(label + " が赤にならない:\n" + r.stdout[-600:])
        shutil.rmtree(tmp)
    print("=" * 50)
    if bad:
        print("🔴 生存ミュータント %d/%d\n" % (len(bad), len(MUTANTS)) + "\n".join(bad)); return 1
    print("🟢 %d/%d 撃墜" % (len(MUTANTS), len(MUTANTS))); return 0


if __name__ == "__main__":
    sys.exit(main())
