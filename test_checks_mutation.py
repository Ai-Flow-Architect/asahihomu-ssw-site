#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""checks.py が「不合格side」を実際に検出できるかをミューテーションで実証する。

恒真式ゲート（何を壊しても緑を出す検査器）を信用しないための実行証明。
各ミュータントを dist/ に注入 → checks.py が exit 1 を返すことを確認 → 再ビルドで復元。

使い方: python3 test_checks_mutation.py   （exit 0 = 全ミュータント撃墜）
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
PY = sys.executable


def rebuild():
    subprocess.run([PY, str(ROOT / "build.py")], capture_output=True, check=True)


def run_checks():
    r = subprocess.run([PY, str(ROOT / "checks.py")], capture_output=True)
    return r.returncode, r.stdout.decode("utf-8", "replace")


# (名前, 対象ファイル, 置換前, 置換後, 期待する検出タグ)
MUTANTS = [
    ("リンク切れ", "index.html",
     'href="pricing.html"', 'href="pricing-nonexistent.html"', "links"),
    ("JSON-LD破壊", "faq.html",
     '"@context": "https://schema.org"', '"@context": BROKEN', "jsonld"),
    ("未置換トークン", "about-us.html",
     "<h2>ワンストップの強み</h2>", "<h2>{{ORG_LEGAL}}</h2>", "tokens"),
    ("noindex剥がし", "voice.html",
     'content="noindex,nofollow"', 'content="index,follow"', "preview"),
    ("ローカル絶対パス混入", "contact.html",
     "<h1>お問い合わせ・無料相談</h1>",
     "<h1>お問い合わせ</h1><!-- /home/dev/project/src -->", "forbidden"),
    ("プレースホルダ復活", "pricing.html",
     "<h1>料金プラン</h1>", "<h1>料金プラン（構成見本）</h1>", "placeholder"),
    ("パンくず不整合", "members.html",
     "<span>›</span>資料ダウンロード</nav>", "<span>›</span>会員ページ</nav>", "breadcrumb"),
    # 実際に起きていた欠陥: .form-status が form の外にあり送信結果が一切表示されなかった
    ("結果表示先がformの外", "contact.html",
     '<div class="form-status" role="status" aria-live="polite"></div>', "", "form"),
    ("フォームの必須項目消失", "contact.html", " required", "", "form", -1),
    # 本番URLで実際に見つかった: 本文を直しても meta description に旧法人名が残っていた
    ("旧法人名がmetaに残存", "about-us.html",
     'name="description" content="', 'name="description" content="あさひ労務管理センター。',
     "forbidden"),
    ("拠点の誤記(2拠点)", "index.html", "<h2>", "<h2>茨城・千葉の2拠点</h2><h2>", "forbidden"),
]


def main():
    rebuild()
    rc, _ = run_checks()
    if rc != 0:
        print("FATAL: ミューテーション前が既に赤。先に本体を緑にすること。")
        return 1
    print("baseline: GREEN")

    survived = []
    for mut in MUTANTS:
        name, fname, old, new, tag = mut[:5]
        count = mut[5] if len(mut) > 5 else 1  # -1 = 全置換
        target = DIST / fname
        original = target.read_text(encoding="utf-8")
        if old not in original:
            print("  SKIP {0}: 対象文字列が見つからない（{1}）".format(name, fname))
            survived.append(name + "（注入不能）")
            rebuild()
            continue
        target.write_text(original.replace(old, new, count), encoding="utf-8")
        rc, out = run_checks()
        rebuild()
        if rc == 0:
            print("  SURVIVED {0}: 検査器が見逃した".format(name))
            survived.append(name)
        elif "[{0}]".format(tag) not in out:
            print("  MISLABELED {0}: 赤にはなったが [{1}] で検出されていない".format(name, tag))
            survived.append(name + "（検出タグ違い）")
        else:
            print("  KILLED {0} -> [{1}]".format(name, tag))

    rc, _ = run_checks()
    if rc != 0:
        print("FATAL: 復元後に赤が残っている。")
        return 1

    if survived:
        print("\nNG: 生き残ったミュータント {0} 件: {1}".format(len(survived), survived))
        return 1
    print("\nALL MUTANTS KILLED ({0}/{0}) — checks.py は不合格sideを検出できる".format(len(MUTANTS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
