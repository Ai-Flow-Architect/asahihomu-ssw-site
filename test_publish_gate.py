#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本公開モード（preview=false）専用の検査が、実際に発火することを実証する。

このゲートは「本公開の瞬間」にしか動かない＝壊れていても普段は誰も気づけない。

🔴 2026-09-02 作りを変えた理由
  旧版は「site.json を preview=false に倒せば、実物が未完成なので全部赤くなる」ことに
  依存していた＝**実物を直すたびにこのテストが赤くなる**。実際 8/31 にガイドブックPDFを
  配置した時点で `download.guidebook_url` が検出されなくなり RED のまま放置されていた。
  そこで直し方の楽な道は EXPECT から1行消すこと＝**検出力の証拠を1つ捨てる**ことになる。
  → 実物の未完成度に頼らず、**欠陥をこちらから注入して検出されることを確かめる**形へ変えた。
  （実物に残っている本公開ブロッカーは「参考」として表示するだけで、合否には使わない）

使い方: python3 test_publish_gate.py   （exit 0 = ゲートは生きている）
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CFG_PATH = ROOT / "site.json"
INJECT_PAGE = ROOT / "src" / "pages" / "privacy.html"
PY = sys.executable

# 空にすると本番モードで必ず赤になるべき設定キー
BLANK_KEYS = [
    ("site", "policy_date"),
    ("contact", "form_endpoint"),
    ("download", "form_endpoint"),
    ("download", "guidebook_url"),
]

# ページに残っていたら本番モードで必ず赤になるべき「制作途中」の文言
BAD_WORDS = ["デモ表示", "掲載見本", "準備中", "現在は業種・地域のみ",
             "雛形", "法務確認のうえ"]

EXPECT = [k for _, k in BLANK_KEYS] + BAD_WORDS


def run(cmd):
    return subprocess.run(cmd, capture_output=True)


def checks_output():
    r = run([PY, str(ROOT / "checks.py")])
    return r.returncode, r.stdout.decode("utf-8", "replace")


def blockers(out):
    return [l.strip() for l in out.splitlines() if l.strip().startswith("[")]


def main():
    cfg_bak = CFG_PATH.read_bytes()
    page_bak = INJECT_PAGE.read_bytes()
    try:
        cfg = json.loads(cfg_bak.decode("utf-8"))

        # ---- 参考: 実物のまま本公開へ倒すと、いま何が残っているか ----
        cfg["site"]["preview"] = False
        CFG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        run([PY, str(ROOT / "build.py")])
        rc_real, out_real = checks_output()

        # ---- 本題: 欠陥を注入して、ゲートが1件ずつ検出することを確かめる ----
        for sec, key in BLANK_KEYS:
            cfg.setdefault(sec, {})[key] = ""
        CFG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        INJECT_PAGE.write_bytes(
            page_bak
            + ('\n<p class="placeholder-note">検出力テスト用の注入: '
               + " / ".join(BAD_WORDS) + "</p>\n").encode("utf-8"))

        run([PY, str(ROOT / "build.py")])
        rc, out = checks_output()
        if rc == 0:
            print("NG: 欠陥を注入したのに ALL GREEN を返した（ゲートが死んでいる）")
            print(out)
            return 1
        missing = [e for e in EXPECT if e not in out]
        if missing:
            print("NG: 注入した欠陥のうち検出されなかったもの:", missing)
            print(out)
            return 1
        print("検出力: 注入した {0} 件をすべて検出".format(len(EXPECT)))
        for line in blockers(out):
            print("   " + line)
    finally:
        CFG_PATH.write_bytes(cfg_bak)
        INJECT_PAGE.write_bytes(page_bak)
        run([PY, str(ROOT / "build.py")])

    rc, out = checks_output()
    if rc != 0:
        print("NG: 復元後に赤が残っている")
        print(out)
        return 1
    if CFG_PATH.read_bytes() != cfg_bak or INJECT_PAGE.read_bytes() != page_bak:
        print("NG: 復元が完全でない")
        return 1

    print("\n復元OK（preview=true・ALL GREEN）— 本公開ゲートは生きている")
    print("\n参考: 実物のまま本公開へ倒した場合に残るブロッカー "
          "{0} 件（合否には使わない）".format(len(blockers(out_real))))
    for line in blockers(out_real):
        print("   " + line)
    if rc_real == 0:
        print("   （なし＝本公開の準備が整っている）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
