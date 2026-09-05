#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""microCMS の記事を全件取得して content/cms_posts.json に書く（標準ライブラリのみ）。

役割:
  microCMS（お役立ち情報 API `posts`）→ 正規化 JSON。build.py はこの JSON だけを読む。
  CMS は「記事の供給源」であって、ビルドや公開の判断はしない。

鍵の扱い:
  環境変数 MICROCMS_SERVICE_DOMAIN / MICROCMS_API_KEY のみ（GitHub Secrets → env）。
  コード・リポには書かない。鍵が無ければ JSON に触らず exit 0（＝既存記事だけでビルドされる）。

失敗時:
  HTTP エラー・JSON 不正・件数不一致は exit 1 で止め、JSON を書き換えない
  （壊れたデータで上書きしない＝前回公開した記事がサイトから消えない）。

使い方:
  python3 fetch_cms.py            # 取得して content/cms_posts.json を更新
  python3 fetch_cms.py --dry-run  # 取得だけして件数を表示（書かない）
  python3 fetch_cms.py --require-key  # CI 用: 鍵が無ければ exit 1（Secrets 失効を見逃さない）
"""
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "content" / "cms_posts.json"
ENDPOINT = "posts"
LIMIT = 100  # microCMS の上限
JST = dt.timezone(dt.timedelta(hours=9))
TAG_RE = re.compile(r"<[^>]+>")


def api_base():
    domain = os.environ.get("MICROCMS_SERVICE_DOMAIN", "").strip()
    key = os.environ.get("MICROCMS_API_KEY", "").strip()
    if not domain or not key:
        return None, None
    # テスト用: フルURL（http://127.0.0.1:port）を渡せる。通常はサービスID。
    base = domain if domain.startswith("http") else "https://%s.microcms.io" % domain
    return base + "/api/v1/" + ENDPOINT, key


def get_json(url, key, tries=3):
    """一時障害（429/5xx・接続断）は 2 秒→4 秒 で最大 3 回。4xx はその場で失敗。"""
    req = urllib.request.Request(url, headers={"X-MICROCMS-API-KEY": key})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code != 429 and e.code < 500 or i == tries - 1:
                raise
        except (urllib.error.URLError, OSError):
            if i == tries - 1:
                raise
        time.sleep(2 * (i + 1))


def fetch_all(url, key):
    """totalCount に達するまで offset を進める。1ページ目の件数を全件と見なさない。"""
    items, offset, total = [], 0, None
    while True:
        q = urllib.parse.urlencode({"limit": LIMIT, "offset": offset})
        data = get_json(url + "?" + q, key)
        page = data.get("contents", [])
        total = data.get("totalCount", 0) if total is None else total
        items.extend(page)
        offset += len(page)
        if not page or offset >= total:
            break
    if len(items) != total:
        sys.exit("中止: 取得件数 %d が totalCount %d と一致しない" % (len(items), total))
    return items


def to_date(item):
    """date フィールド優先、無ければ publishedAt。JST の YYYY-MM-DD に揃える。"""
    raw = (item.get("date") or item.get("publishedAt") or "").strip()
    if not raw:
        return ""
    d = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(JST).strftime("%Y-%m-%d")


def normalize(item):
    body = item.get("body") or ""
    desc = (item.get("description") or "").strip()
    if not desc:
        # タグを落とし、&amp; 等の実体参照を文字に戻す（build 側で再エスケープするため二重にしない）
        desc = html.unescape(TAG_RE.sub("", body)).replace("\n", " ").strip()[:120]
    eye = item.get("eyecatch") or {}
    cat = item.get("category")
    if isinstance(cat, list):  # セレクト（複数可）は先頭だけ使う
        cat = cat[0] if cat else ""
    return {
        "slug": (item.get("slug") or "").strip(),
        "title": (item.get("title") or "").strip(),
        "description": desc,
        "category": (cat or "").strip(),
        "date": to_date(item),
        "body": body,
        "eyecatch": (eye.get("url") if isinstance(eye, dict) else "") or "",
    }


def main():
    url, key = api_base()
    if not url:
        # ローカルは鍵なしで通す（既存記事だけでビルド）。CI は --require-key で必ず止める＝
        # Secrets の失効・削除を「差分なしの成功」で見逃さない。
        if "--require-key" in sys.argv:
            sys.exit("中止: --require-key 指定で MICROCMS_SERVICE_DOMAIN / MICROCMS_API_KEY が未設定（Secrets を確認）")
        print("CMS鍵なし（MICROCMS_SERVICE_DOMAIN / MICROCMS_API_KEY 未設定）＝ JSON を変更せず終了")
        return 0
    try:
        raw = fetch_all(url, key)
    except (urllib.error.URLError, ValueError, OSError) as e:
        sys.exit("中止: microCMS 取得に失敗（JSON は変更しない）: %r" % (e,))
    posts = sorted((normalize(i) for i in raw), key=lambda p: p["date"], reverse=True)
    if "--dry-run" in sys.argv:
        print("dry-run: %d 件（書き込みなし）" % len(posts))
        return 0
    # 公開済み記事の slug が消えると旧URLが 404 になる（削除は正当な場合もあるので止めずに知らせる）
    if OUT.exists():
        before = {p["slug"] for p in json.loads(OUT.read_text(encoding="utf-8")).get("posts", [])}
        gone = sorted(before - {p["slug"] for p in posts})
        if gone:
            msg = "警告: 前回あった記事が消えた（旧URLは404になる）: %s" % ", ".join(gone)
            print(msg, file=sys.stderr)
            if os.environ.get("GITHUB_ACTIONS"):
                print("::warning::" + msg)  # Actions の実行サマリーに黄色で出す（ログを開かなくても見える）
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "fetched_at": dt.datetime.now(JST).strftime("%Y-%m-%dT%H:%M:%S%z"),
        "posts": posts,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s（%d 件）" % (OUT.relative_to(ROOT), len(posts)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
