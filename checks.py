#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dist/ の完成HTMLに対する機械検査（納品前ゲート）。

検査項目:
  1. 内部リンク切れ 0 件（href の .html / assets が dist に実在するか）
  2. JSON-LD が全ブロック json.loads() で解析可能
  3. 未置換テンプレートトークン {{...}} が 0 件
  4. preview 中は全ページ noindex,nofollow ＋ robots.txt が全Disallow
  5. sitemap.xml の URL が dist の実ファイルと 1:1 対応
  6. プレースホルダ文言（仮置き・受注後に確定 等）の残存 0 件
  7. 公開してはいけない文字列（実名・WSL2絶対パス）の混入 0 件
  8. ビルドの冪等性（2回ビルドして同一出力）

使い方: python3 checks.py   （exit 0 = 全緑）
"""
import json
import re
import subprocess
import sys
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
CFG = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))

errors = []
notes = []


def fail(check, msg):
    errors.append("[{0}] {1}".format(check, msg))


def html_files():
    return sorted(DIST.glob("*.html"))


# ---- 1. 内部リンク切れ ----
def check_links():
    n = 0
    for f in html_files():
        txt = f.read_text(encoding="utf-8")
        for href in re.findall(r'(?:href|src|srcset)="([^"]+)"', txt):
            href = href.split()[0]
            if href.startswith(("http://", "https://", "mailto:", "tel:", "#", "data:")):
                continue
            target = (DIST / href.split("#")[0].split("?")[0])
            n += 1
            if not target.exists():
                fail("links", "{0} -> {1} が存在しない".format(f.name, href))
    notes.append("内部リンク {0} 本を検査".format(n))


# ---- 2. JSON-LD ----
def check_jsonld():
    n = 0
    for f in html_files():
        txt = f.read_text(encoding="utf-8")
        for block in re.findall(
                r'<script type="application/ld\+json">(.*?)</script>', txt, re.S):
            n += 1
            try:
                json.loads(block)
            except ValueError as e:
                fail("jsonld", "{0}: {1}".format(f.name, e))
    notes.append("JSON-LD {0} ブロックを解析".format(n))


# ---- 3. 未置換トークン ----
def check_tokens():
    for f in html_files():
        left = re.findall(r"\{\{[A-Z_]+\}\}", f.read_text(encoding="utf-8"))
        if left:
            fail("tokens", "{0}: 未置換 {1}".format(f.name, sorted(set(left))))


# ---- 4. preview 時の検索除外 ----
def check_preview():
    if not CFG["site"].get("preview"):
        notes.append("preview=false（本番モード）のため noindex 検査はスキップ")
        return
    for f in html_files():
        txt = f.read_text(encoding="utf-8")
        if 'name="robots" content="noindex,nofollow"' not in txt:
            fail("preview", "{0}: noindex,nofollow が無い".format(f.name))
    robots = (DIST / "robots.txt").read_text(encoding="utf-8")
    if "Disallow: /" not in robots or "Allow:" in robots:
        fail("preview", "robots.txt が全Disallowになっていない")
    notes.append("preview=true: 全{0}ページ noindex ＋ robots 全Disallow".format(
        len(html_files())))


# ---- 5. sitemap 整合 ----
def check_sitemap():
    xml = (DIST / "sitemap.xml").read_text(encoding="utf-8")
    locs = re.findall(r"<loc>([^<]+)</loc>", xml)
    base = CFG["site"]["base_url"]
    for loc in locs:
        rel = loc[len(base):].lstrip("/")
        name = rel if rel else "index.html"
        if not (DIST / name).exists():
            fail("sitemap", "{0} に対応するファイルが無い".format(loc))
    # noindex ページが sitemap に載っていないこと
    notes.append("sitemap {0} URL を検査".format(len(locs)))


# ---- 6. プレースホルダ残存 ----
PLACEHOLDER_PAT = [
    "受注後に確定", "受注後に差し替え", "仮置き", "000-0000-0000",
    "info@example.com", "構成見本", "※受注後",
]


def check_placeholders():
    for f in html_files():
        txt = f.read_text(encoding="utf-8")
        for pat in PLACEHOLDER_PAT:
            if pat in txt:
                fail("placeholder", "{0}: 「{1}」が残存".format(f.name, pat))
    # 本番モード（preview=false）でのみ必須になる項目
    if not CFG["site"].get("preview"):
        if not CFG["site"].get("policy_date"):
            fail("placeholder", "site.json policy_date（PP制定日）が未設定のまま本公開しようとしている")
        if not CFG["contact"].get("form_endpoint"):
            fail("placeholder", "contact.form_endpoint 未設定のまま本公開しようとしている（フォームがモック動作になる）")
        # 制作途中であることが読み手に伝わる文言＝残すと信頼を損なう（4AI-check 2026-07-21 指摘）
        # 「雛形」はプライバシーポリシーに残った社内向け注記（harden 2026-07-21 で発見）
        for pat in ["デモ表示", "掲載見本", "準備中", "現在は業種・地域のみ",
                    "雛形", "法務確認のうえ"]:
            for f in html_files():
                if pat in f.read_text(encoding="utf-8"):
                    fail("placeholder",
                         "{0}: 本公開前に外すべき文言「{1}」が残っている".format(f.name, pat))


# ---- 7. 公開禁止文字列 ----
# 開発者の実名検査は pre-commit フック（全リポ共通・core.hooksPath）が担当する。
# ここに実名を書くと「実名を検出する検査器が実名を持ち込む」ことになるため書かない。
# この検査は、納品物に開発環境のローカル絶対パスが漏れていないかだけを見る。
FORBIDDEN = ["/home/", "/mnt/c/", "C:\\Users"]


def check_forbidden():
    for f in html_files():
        txt = f.read_text(encoding="utf-8")
        for pat in FORBIDDEN:
            if pat in txt:
                fail("forbidden", "{0}: 「{1}」が混入".format(f.name, pat))


# ---- 8. 冪等性 ----
def digest():
    h = hashlib.sha256()
    for f in sorted(DIST.rglob("*")):
        if f.is_file():
            h.update(f.name.encode("utf-8"))
            h.update(f.read_bytes())
    return h.hexdigest()


def check_idempotent():
    before = digest()
    subprocess.run([sys.executable, str(ROOT / "build.py")],
                   capture_output=True, check=True)
    after = digest()
    if before != after:
        fail("idempotent", "2回ビルドで出力が変化した")
    else:
        notes.append("冪等性OK（同一ハッシュ {0}）".format(before[:12]))


# ---- 9. 画面のパンくず と 構造化データ(BreadcrumbList) の一致 ----
def check_breadcrumb_sync():
    n = 0
    for f in html_files():
        if f.name == "index.html":
            continue
        txt = f.read_text(encoding="utf-8")
        m = re.search(r'<nav class="breadcrumb"[^>]*>(.*?)</nav>', txt, re.S)
        if not m:
            fail("breadcrumb", "{0}: 画面のパンくずが無い".format(f.name))
            continue
        visible = re.sub(r"<[^>]+>", "", m.group(1)).replace("›", " ").split()
        jl = None
        for block in re.findall(
                r'<script type="application/ld\+json">(.*?)</script>', txt, re.S):
            try:
                data = json.loads(block)
            except ValueError:
                continue  # 解析不能は check_jsonld の担当（ここで落ちない）
            if data.get("@type") == "BreadcrumbList":
                jl = [i["name"] for i in data["itemListElement"]]
        if jl is None:
            fail("breadcrumb", "{0}: BreadcrumbList が無い".format(f.name))
            continue
        n += 1
        if visible != jl:
            fail("breadcrumb",
                 "{0}: 画面{1} と 構造化データ{2} が不一致".format(f.name, visible, jl))
    notes.append("パンくず {0} ページを画面↔構造化データで突合".format(n))


# ---- 10. フォームの結果表示先が form の内側にあるか ----
def check_form_status_inside_form():
    """main.js は form.querySelector(".form-status") で探す。

    外に置くと status が null になり、送信しても成功も失敗も一切表示されない
    （押しても何も起きないフォームになる）。実際にこれで壊れていたので機械化する。
    """
    n = 0
    for f in html_files():
        txt = f.read_text(encoding="utf-8")
        for m in re.finditer(r'<form\b[^>]*id="([^"]+)"[^>]*>(.*?)</form>', txt, re.S):
            form_id, inner = m.group(1), m.group(2)
            if form_id not in ("contact-form", "member-login"):
                continue
            n += 1
            # HTMLコメントを落としてから判定する。説明コメントに ".form-status" と
            # 書いてあるだけで「在る」と誤判定した実例があるため（検査は実体に当てる）。
            body = re.sub(r"<!--.*?-->", "", inner, flags=re.S)
            # contact-form だけ main.js が form.querySelector(".form-status") で探す。
            # member-note は document.getElementById で探すので form の外でもよい。
            if form_id == "contact-form" and 'class="form-status"' not in body:
                fail("form", "{0}: #contact-form の結果表示先 .form-status が form の外にある"
                             "（送信しても何も表示されない）".format(f.name))
            # 必須項目が1つも無いフォームは、同意取得やバリデーションが抜けている疑い
            if "required" not in body:
                fail("form", "{0}: #{1} に required が1つも無い".format(f.name, form_id))
    notes.append("フォーム {0} 件の結果表示先と必須項目を検査".format(n))


def main():
    check_links()
    check_jsonld()
    check_breadcrumb_sync()
    check_form_status_inside_form()
    check_tokens()
    check_preview()
    check_sitemap()
    check_placeholders()
    check_forbidden()
    check_idempotent()

    for n in notes:
        print("  - " + n)
    if errors:
        print("\nNG {0} 件:".format(len(errors)))
        for e in errors:
            print("  " + e)
        return 1
    print("\nALL GREEN ({0} pages)".format(len(html_files())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
