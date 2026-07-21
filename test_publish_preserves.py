#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""publish が GitHub Pages の制御ファイルを消さないことを実証する。

publish() は docs/ を作り直す（rmtree→copytree）。dist/ に存在しない .nojekyll や
CNAME は、素朴に実装すると毎回消える。消えても画面上は何も変わらないので気づけず、
CNAME が消えた場合は独自ドメインが落ちる。だから「消えないこと」を実行で確かめる。

使い方: python3 test_publish_preserves.py   （exit 0 = 保持されている）
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
PY = sys.executable

spec = importlib.util.spec_from_file_location("sitebuild", ROOT / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

CNAME = DOCS / "CNAME"
cname_existed = CNAME.exists()
cname_backup = CNAME.read_bytes() if cname_existed else None

failures = []
try:
    # 独自ドメイン設定を模した CNAME を置いて publish を通す
    CNAME.write_bytes(b"example.invalid\n")
    subprocess.run([PY, str(ROOT / "build.py"), "--publish"],
                   capture_output=True, check=True)

    if not (DOCS / ".nojekyll").exists():
        failures.append(".nojekyll が publish で消えた")
    if not CNAME.exists():
        failures.append("CNAME が publish で消えた（独自ドメインが落ちる）")
    elif CNAME.read_bytes() != b"example.invalid\n":
        failures.append("CNAME の中身が書き換わった")

    # 制御ファイルが1つも無い状態からでも .nojekyll は作られること
    (DOCS / ".nojekyll").unlink()
    CNAME.unlink()
    subprocess.run([PY, str(ROOT / "build.py"), "--publish"],
                   capture_output=True, check=True)
    if not (DOCS / ".nojekyll").exists():
        failures.append("退避元が無いとき .nojekyll が新規作成されない")
finally:
    if cname_existed:
        CNAME.write_bytes(cname_backup)
    elif CNAME.exists():
        CNAME.unlink()
    subprocess.run([PY, str(ROOT / "build.py"), "--publish"], capture_output=True)

if failures:
    print("NG:")
    for f in failures:
        print("  " + f)
    sys.exit(1)
print("publish は Pages 制御ファイルを保持する（.nojekyll 保持・CNAME 保持・不在時は .nojekyll 生成）")
