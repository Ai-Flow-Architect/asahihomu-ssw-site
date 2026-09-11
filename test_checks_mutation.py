#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""checks.py が「不合格side」を実際に検出できるかをミューテーションで実証する。

恒真式ゲート（何を壊しても緑を出す検査器）を信用しないための実行証明。
各ミュータントを dist/ に注入 → checks.py が exit 1 を返すことを確認 → 再ビルドで復元。

使い方: python3 test_checks_mutation.py   （exit 0 = 全ミュータント撃墜）

🔴 2026-09-11 本公開設定（preview=false）へ倒した時点で「noindex剥がし」が注入不能になり RED になった
  ＝このテストは「現物の site.json が preview=true であること」に依存していた（test_videos 8/31 と同型）。
  → 検査器の検出力を測る間だけ preview=true に倒し、終わったら site.json をバイト単位で復元する
    （test_publish_gate と同じ作法）。本番モード専用の検査は test_publish_gate が担当する。
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
CFG_PATH = ROOT / "site.json"
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
    # 2026-08-01 に実際に起きた事故そのもの。画面の本文だけ是正され、head の構造化データに
    # 旧相場が生き残っていた。JSON-LD は head にあるため置換1回目が構造化データ側に当たる
    # ＝「本文は正しいのに構造化データだけ古い」状態を忠実に再現する。
    ("構造化データだけ旧金額", "faq.html", "780万円", "1,200万円", "faq_sync", 1),
    # 同じ日に見つかった2つ目のズレ: 本文8問に対し構造化データ5問（3問が丸ごと欠落）。
    ("構造化データの件数欠落", "faq.html",
     "<p>まずはお問い合わせください。対応可否を含めてご相談を承ります。</p></div>",
     "<p>まずはお問い合わせください。対応可否を含めてご相談を承ります。</p></div>"
     '<button class="faq__q">追加質問</button><div class="faq__a"><p>追加回答</p></div>',
     "faq_sync"),
    # 根拠を超えた比較広告の復活（客様提供の出典2本が裏づけないレンジ＋「当社調べ」）。
    ("旧相場レンジの復活", "pricing.html",
     "<h1>料金プラン</h1>", "<h1>料金プラン</h1><p>月額35,000円〜50,000円（当社調べ）</p>",
     "forbidden"),
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


def main_preview_forced():
    cfg_bak = CFG_PATH.read_bytes()
    cfg = json.loads(cfg_bak.decode("utf-8"))
    try:
        if not cfg["site"].get("preview"):
            cfg["site"]["preview"] = True
            CFG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        return main()
    finally:
        CFG_PATH.write_bytes(cfg_bak)
        rebuild()


if __name__ == "__main__":
    sys.exit(main_preview_forced())
