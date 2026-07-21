#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build.safe_rmtree / publish のガードが実際に止まることを実証する。

「消してよいディレクトリ以外は消さない」という守りは、壊れていても普段は何も起きない。
だから禁止側（止まるべきケース）を実行して確かめる。

使い方: python3 test_safe_rmtree.py   （exit 0 = ガードは生きている）
"""
import importlib.util
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent

spec = importlib.util.spec_from_file_location("sitebuild", ROOT / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

failures = []


def expect_blocked(label, path):
    """safe_rmtree が SystemExit で止まり、かつ対象が消えていないこと。"""
    existed = Path(path).exists()
    try:
        build.safe_rmtree(Path(path))
    except SystemExit as e:
        if Path(path).exists() != existed:
            failures.append("{0}: 止まったのに対象の存在状態が変わった".format(label))
        else:
            print("  BLOCKED {0} -> {1}".format(label, str(e)[:60]))
        return
    failures.append("{0}: 止まらなかった（危険）".format(label))


def expect_allowed(label, path):
    """想定どおりの dist/docs は消せること（合格側も実行証明する）。"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    (p / "canary.txt").write_text("x", encoding="utf-8")
    try:
        build.safe_rmtree(p)
    except SystemExit as e:
        failures.append("{0}: 消せるはずが止まった: {1}".format(label, e))
        return
    if p.exists():
        failures.append("{0}: 消えていない".format(label))
    else:
        print("  ALLOWED {0}".format(label))


tmp = Path(tempfile.mkdtemp())
(tmp / "important").mkdir()

print("禁止側（止まるべきケース）:")
expect_blocked("ROOT外の一時ディレクトリ", tmp / "important")
expect_blocked("ホームディレクトリ", Path.home())
expect_blocked("ルート", Path("/"))
expect_blocked("ROOT直下だが名前が違う（src）", ROOT / "src")
expect_blocked("ROOT直下だが名前が違う（screenshots）", ROOT / "screenshots")
expect_blocked("dist という名前だが場所が違う", tmp / "dist")

print("\n許可側（消せるべきケース）:")
expect_allowed("ROOT/dist", ROOT / "dist")

# 後片付け: dist を消したので再ビルドして元に戻す
build.main()

if failures:
    print("\nNG {0} 件:".format(len(failures)))
    for f in failures:
        print("  " + f)
    sys.exit(1)
print("\nガードは生きている（禁止6件を阻止・許可1件は通過）")
