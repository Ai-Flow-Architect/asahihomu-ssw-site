#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本公開モード（preview=false）専用の検査が、実際に発火することを実証する。

このゲートは「本公開の瞬間」にしか動かない＝壊れていても普段は誰も気づけない。
そこで site.json を一時的に本番モードへ倒し、想定どおり赤になることを確認して元に戻す。

使い方: python3 test_publish_gate.py   （exit 0 = ゲートは生きている）
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CFG_PATH = ROOT / "site.json"
BACKUP = ROOT / "site.json.testbak"
PY = sys.executable

# 本番モードで必ず検出されるべき項目（preview=false にしただけで全部出る状態が今）
EXPECT = [
    "policy_date",       # PP制定日 未設定
    "contact.form_endpoint",   # お問い合わせの送信先 未設定
    "download.form_endpoint",  # 資料DL登録の送信先 未設定
    "download.guidebook_url",  # ガイドブックPDF 未配置
    "デモ表示",           # 制作途中の文言
    "掲載見本",
    "準備中",
]


def run(cmd):
    return subprocess.run(cmd, capture_output=True)


def main():
    shutil.copy(CFG_PATH, BACKUP)
    try:
        cfg = json.loads(CFG_PATH.read_text(encoding="utf-8"))
        cfg["site"]["preview"] = False
        CFG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        run([PY, str(ROOT / "build.py")])
        r = run([PY, str(ROOT / "checks.py")])
        out = r.stdout.decode("utf-8", "replace")

        if r.returncode == 0:
            print("NG: 本番モードなのに ALL GREEN を返した（ゲートが死んでいる）")
            print(out)
            return 1
        missing = [e for e in EXPECT if e not in out]
        if missing:
            print("NG: 検出されるべき項目が出ていない:", missing)
            print(out)
            return 1
        print("本番モードで想定どおり赤:")
        for line in out.splitlines():
            if line.strip().startswith("["):
                print("   " + line.strip())
    finally:
        shutil.move(str(BACKUP), str(CFG_PATH))
        run([PY, str(ROOT / "build.py")])

    r = run([PY, str(ROOT / "checks.py")])
    if r.returncode != 0:
        print("NG: 復元後に赤が残っている")
        print(r.stdout.decode("utf-8", "replace"))
        return 1
    print("\n復元OK（preview=true・ALL GREEN）— 本公開ゲートは生きている")
    return 0


if __name__ == "__main__":
    sys.exit(main())
