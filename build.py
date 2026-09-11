#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
あさひほうむ 特定技能サポート — 静的サイト ビルダー

役割:
  src/templates/base.html（共通レイアウト）に
  src/pages/<slug>.html（各ページ本文）を流し込み、
  共通トークン（社名・連絡先・ナビ・SEOメタ・構造化データ）を置換して
  dist/ に全ページの完成HTML + sitemap.xml + robots.txt を出力する。

特徴:
  - ヘッダー/フッター/ナビは base.html に一元化（DRY・更新は1か所）
  - 連絡先・社名等は site.json に一元化（受注後の差し替えが1ファイルで完結）
  - 依存ライブラリなし。python3 build.py だけで再生成可能。

使い方:
  python3 build.py              # dist/ を再生成（ローカル確認用）
  python3 build.py --publish    # dist/ を docs/ へ同期（GitHub Pages 公開ディレクトリ）
                                # ⚠️ push するとクライアント可視のプレビューURLに即反映される
"""
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
DIST = ROOT / "dist"
DOCS = ROOT / "docs"  # GitHub Pages の公開ディレクトリ（--publish で dist から同期）
CFG = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))

# ---- ページ定義（slug, title, description, og_type, robots, jsonld種別） ----
# title は「<ページ名>｜<サイト名>」で統一。description はページ個別。
PAGES = [
    {"slug": "index", "name": "トップ",
     "title": "あさひほうむ 特定技能サポート｜茨城・千葉の登録支援機関",
     "desc": "茨城・千葉の登録支援機関「あさひほうむ」。社労士×行政書士×キャリアコンサルタントのワンストップ体制で、特定技能外国人材の受け入れを安く・手厚くサポートします。",
     "jsonld": "home"},
    {"slug": "about-ssw", "name": "特定技能とは",
     "title": "特定技能とは｜あさひほうむ 特定技能サポート",
     "desc": "特定技能制度のしくみ・技能実習との違い・1号と2号・受け入れの要件を、外国人材の採用が初めての企業にもわかりやすく解説します。",
     "jsonld": "article"},
    {"slug": "support", "name": "支援内容",
     "title": "登録支援機関の支援内容（義務的支援10項目）｜あさひほうむ",
     "desc": "登録支援機関として行う10項目の義務的支援（事前ガイダンス・生活オリエンテーション・公的手続き同行・相談対応など）と任意支援をご紹介します。",
     "jsonld": "service"},
    {"slug": "industries", "name": "対応分野",
     "title": "対応分野（特定技能16分野）｜あさひほうむ 特定技能サポート",
     "desc": "製造・農業・介護・外食・建設・宿泊など、特定技能の対象分野ごとの受け入れポイントとサポート内容をご案内します。",
     "jsonld": "service"},
    {"slug": "pricing", "name": "料金プラン",
     "title": "料金プラン｜あさひほうむ 特定技能サポート",
     "desc": "支援委託費・登録支援機関への委託費用の目安をわかりやすくご案内。安さと手厚さを両立した明朗な料金体系です。",
     "jsonld": "service"},
    {"slug": "flow", "name": "ご利用の流れ",
     "title": "ご利用の流れ｜あさひほうむ 特定技能サポート",
     "desc": "お問い合わせから人材のマッチング・在留資格申請・受け入れ・入国後の定着支援まで、特定技能外国人を受け入れるまでの流れを解説します。",
     "jsonld": "article"},
    {"slug": "reasons", "name": "選ばれる理由",
     "title": "選ばれる理由｜あさひほうむ 特定技能サポート",
     "desc": "社労士・行政書士・キャリアコンサルタントのワンストップ、安さ＋手厚さ、法令順守の徹底。あさひほうむが選ばれる理由をご紹介します。",
     "jsonld": "article"},
    {"slug": "jobs", "name": "求人情報",
     "title": "特定技能 求人情報｜あさひほうむ 特定技能サポート",
     "desc": "特定技能で働きたい外国人材向けの求人情報を掲載。分野・地域・条件から、安心して働ける受け入れ企業の求人をご覧いただけます。",
     "jsonld": "article"},
    {"slug": "blog", "name": "お役立ち情報",
     "title": "お役立ち情報・ブログ｜あさひほうむ 特定技能サポート",
     "desc": "特定技能制度の最新動向や受け入れの実務ノウハウ、よくあるご相談など、企業・外国人材に役立つ情報をお届けします。",
     "jsonld": "blog"},
    {"slug": "faq", "name": "よくある質問",
     "title": "よくある質問｜あさひほうむ 特定技能サポート",
     "desc": "特定技能の受け入れ・費用・期間・登録支援機関への委託について、よくいただくご質問にお答えします。",
     "jsonld": "faq"},
    {"slug": "about-us", "name": "事務所紹介",
     "title": "事務所紹介｜あさひほうむ 特定技能サポート",
     "desc": "茨城県つくば市の登録支援機関「株式会社あさひほうむ」。社会保険労務士・行政書士・キャリアコンサルタントのワンストップ体制と理念をご紹介します。",
     "jsonld": "about"},
    {"slug": "voice", "name": "お客様の声",
     "title": "お客様の声・導入事例｜あさひほうむ 特定技能サポート",
     "desc": "特定技能外国人材を受け入れた企業の声・導入事例をご紹介します。安さと手厚さを両立したサポートの実際をご覧ください。",
     "jsonld": "article"},
    {"slug": "contact", "name": "お問い合わせ",
     "title": "お問い合わせ｜あさひほうむ 特定技能サポート",
     "desc": "特定技能外国人材の受け入れ・登録支援機関への委託に関するご相談・お見積りはこちらから。お気軽にお問い合わせください。",
     "jsonld": "contact"},
    # 動画で知る特定技能（フル設計 B2／EVM-8 の掲載先）。YouTube ID 未設定のうちは準備中表示
    {"slug": "videos", "name": "動画で知る特定技能",
     "title": "動画で知る特定技能｜あさひほうむ 特定技能サポート",
     "desc": "特定技能の制度、支援機関の選び方、受け入れ現場の実際を、社会保険労務士がインタビュー形式で解説します。",
     "jsonld": None, "priority": "0.8"},
    # メール登録だけで即ダウンロード（承認制にしない＝客様ご指定）＝リード獲得ページなので検索対象にする
    {"slug": "members", "name": "資料ダウンロード",
     "title": "特定技能 受け入れガイドブック（無料）｜あさひほうむ",
     "desc": "特定技能外国人の受け入れに役立つガイドブックを無料でご用意しています。メールアドレスのご登録だけで、審査なしでご覧いただけます。",
     "jsonld": None, "priority": "0.8"},
    {"slug": "privacy", "name": "プライバシーポリシー",
     "title": "プライバシーポリシー｜あさひほうむ 特定技能サポート",
     "desc": "あさひほうむ 特定技能サポートにおける個人情報の取り扱い方針（プライバシーポリシー）です。",
     "jsonld": None},
    # ---- 分野別SEO入口ページ（フル設計 B1・親=対応分野） ----
    {"slug": "industry-manufacturing", "name": "製造業の特定技能",
     "title": "製造業（工業製品製造業）の特定技能 受け入れサポート｜あさひほうむ",
     "desc": "製造業（工業製品製造業・飲食料品製造業）で特定技能外国人を受け入れるための要件・流れ・注意点を解説。茨城・千葉の登録支援機関が申請から定着までワンストップで支援します。",
     "jsonld": "service", "parent": {"slug": "industries", "name": "対応分野"},
     "priority": "0.8"},
    {"slug": "industry-agriculture", "name": "農業の特定技能",
     "title": "農業の特定技能 受け入れサポート｜あさひほうむ",
     "desc": "農業分野で特定技能外国人を受け入れるための要件・派遣形態の活用・季節性への対応を解説。茨城・千葉の登録支援機関が地域の農業経営をワンストップで支援します。",
     "jsonld": "service", "parent": {"slug": "industries", "name": "対応分野"},
     "priority": "0.8"},
    {"slug": "industry-care", "name": "介護の特定技能",
     "title": "介護分野の特定技能 受け入れサポート｜あさひほうむ",
     "desc": "介護分野で特定技能外国人を受け入れるための要件・試験・配置基準の考え方・定着支援を解説。茨城・千葉の登録支援機関が介護現場の人材確保をワンストップで支援します。",
     "jsonld": "service", "parent": {"slug": "industries", "name": "対応分野"},
     "priority": "0.7"},
    # ---- 初期記事5本（フル設計 B3・親=お役立ち情報） ----
    {"slug": "blog-difference", "name": "特定技能と技能実習の違い",
     "title": "特定技能と技能実習、結局どう違う？企業がまず押さえるべき3つのポイント｜あさひほうむ",
     "desc": "特定技能と技能実習の違いを「目的・転職・期間」の3つの観点からやさしく整理。外国人材の採用がはじめての企業向けに、どちらの制度を選ぶべきかの考え方を解説します。",
     "jsonld": "post", "date": "2026-09-11", "category": "制度解説",
     "parent": {"slug": "blog", "name": "お役立ち情報"}, "priority": "0.6"},
    {"slug": "blog-preparation", "name": "受け入れ前の準備チェックリスト",
     "title": "外国人材を受け入れる前に企業が準備すべきこと【チェックリスト付き】｜あさひほうむ",
     "desc": "特定技能外国人の受け入れ前に企業がやるべき準備を、雇用条件・社内体制・住まい・生活支援の4領域のチェックリストで整理。抜け漏れなく受け入れを始められます。",
     "jsonld": "post", "date": "2026-09-11", "category": "受け入れ実務",
     "parent": {"slug": "blog", "name": "お役立ち情報"}, "priority": "0.6"},
    {"slug": "blog-cost", "name": "受け入れ費用の内訳",
     "title": "特定技能の受け入れにかかる費用の内訳をわかりやすく解説｜あさひほうむ",
     "desc": "特定技能外国人の受け入れにかかる費用を「初期費用・毎月かかる費用・その他の費用」の3つに分けて整理。何にいくらかかるのかの全体像と、費用を抑える考え方を解説します。",
     "jsonld": "post", "date": "2026-09-11", "category": "費用",
     "parent": {"slug": "blog", "name": "お役立ち情報"}, "priority": "0.6"},
    {"slug": "blog-retention", "name": "定着の工夫",
     "title": "外国人材に長く働いてもらうための「定着」の工夫｜あさひほうむ",
     "desc": "せっかく受け入れた外国人材の早期離職を防ぐには。コミュニケーション・生活支援・キャリアの見通しの3つの観点から、現場ですぐできる定着の工夫を紹介します。",
     "jsonld": "post", "date": "2026-09-11", "category": "定着支援",
     "parent": {"slug": "blog", "name": "お役立ち情報"}, "priority": "0.6"},
    {"slug": "blog-care-attention", "name": "介護分野の受け入れ注意点",
     "title": "介護分野で特定技能を受け入れるときの注意点｜あさひほうむ",
     "desc": "介護分野で特定技能外国人を受け入れる際に押さえるべき注意点を解説。必要な試験・従事できる業務の範囲・利用者や職員への配慮など、介護現場ならではのポイントをまとめました。",
     "jsonld": "post", "date": "2026-09-11", "category": "分野別",
     "parent": {"slug": "blog", "name": "お役立ち情報"}, "priority": "0.6"},
    # ---- 追加記事3本（2026-08-09・客様提供の県庁講話資料をもとに作成） ----
    {"slug": "blog-illegal-work", "name": "不法就労のリスク",
     "title": "「知らなかった」では済まされない ― 不法就労のリスクとNG事例｜あさひほうむ",
     "desc": "不法就労助長罪の罰則（2027年4月の引き上げを含む）、受け入れ停止や信用失墜のリスク、現場で起きやすい4つのNG事例を、社労士×行政書士の登録支援機関が解説します。",
     "jsonld": "post", "date": "2026-09-11", "category": "法令順守",
     "parent": {"slug": "blog", "name": "お役立ち情報"}, "priority": "0.6"},
    {"slug": "blog-safety", "name": "労働災害の防止",
     "title": "外国人材の労働災害を防ぐ ― 現場でできる安全対策｜あさひほうむ",
     "desc": "外国人労働者の労災死傷者数は2024年に初めて6,000人を超えました。言語・経験・文化という3つの要因と、「わかった？」と聞かない伝え方など現場で今日から始められる対策を解説します。",
     "jsonld": "post", "date": "2026-09-11", "category": "安全衛生",
     "parent": {"slug": "blog", "name": "お役立ち情報"}, "priority": "0.6"},
    {"slug": "blog-signs", "name": "離職のサイン",
     "title": "離職のサインを見逃さない ― 黄色信号と赤信号｜あさひほうむ",
     "desc": "外国人材が辞める前に必ず出る兆候を、黄色信号（初期）と赤信号（切迫）に分けて解説。気づいたときの3ステップと、そもそもサインを出させない職場の3つの土台を紹介します。",
     "jsonld": "post", "date": "2026-09-11", "category": "定着支援",
     "parent": {"slug": "blog", "name": "お役立ち情報"}, "priority": "0.6"},
]

# ---- CMS 記事（microCMS → fetch_cms.py → content/cms_posts.json）----
# JSON が無ければ 0 件＝従来どおり静的記事だけでビルドされる（鍵なしフォールバック）。
CMS_JSON = ROOT / "content" / "cms_posts.json"
SLUG_RE = re.compile(r"^[a-z0-9-]{3,60}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


UNSAFE_TAG_RE = re.compile(r"<\s*(script|object|embed|form|meta|link|style)\b", re.I)
EVENT_ATTR_RE = re.compile(r"\son[a-z]+\s*=", re.I)
JS_URL_RE = re.compile(r"(href|src)\s*=\s*[\"']?\s*(javascript|data|vbscript):", re.I)
IFRAME_RE = re.compile(r"<\s*iframe\b[^>]*\bsrc\s*=\s*[\"']([^\"']*)", re.I)
IFRAME_OK = ("https://www.youtube.com/embed/", "https://www.youtube-nocookie.com/embed/")


def unsafe_html(body):
    """客様1名の入力でも、スクリプトを実行できる要素は通さない（信頼境界の最低限）。

    リッチエディタが出す通常のHTML（p/h2/ul/img/a/strong…）と YouTube 埋め込みは通す。
    戻り値は理由の文字列（安全なら空文字）。
    """
    m = UNSAFE_TAG_RE.search(body)
    if m:
        return "<%s>" % m.group(1).lower()
    if EVENT_ATTR_RE.search(body):
        return "on*= 属性"
    if JS_URL_RE.search(body):
        return "javascript:/data: URL"
    for m in IFRAME_RE.finditer(body):
        if not m.group(1).startswith(IFRAME_OK):
            return "YouTube 以外の iframe (%s)" % m.group(1)[:40]
    return ""


def load_cms_posts():
    """content/cms_posts.json を PAGES 形式へ。1件でも不正なら止める（誤ったURLを公開しない）。"""
    if not CMS_JSON.exists():
        return []
    posts = json.loads(CMS_JSON.read_text(encoding="utf-8")).get("posts", [])
    static_slugs = {p["slug"] for p in PAGES}
    seen, pages = set(), []
    for p in posts:
        slug = p.get("slug", "")
        if not SLUG_RE.match(slug):
            sys.exit("中止: CMS記事の slug が不正（半角英数ハイフン3〜60字）: %r" % slug)
        full = "blog-" + slug
        if full in static_slugs or full in seen:
            sys.exit("中止: CMS記事の slug が既存ページまたは他の記事と重複: %r" % slug)
        seen.add(full)
        if not p.get("title", "").strip():
            sys.exit("中止: CMS記事 %r のタイトルが空" % slug)
        if not DATE_RE.match(p.get("date", "")):
            sys.exit("中止: CMS記事 %r の日付が YYYY-MM-DD でない: %r" % (slug, p.get("date")))
        bad = unsafe_html(p.get("body", ""))
        if bad:
            sys.exit("中止: CMS記事 %r の本文に許可しない要素: %s" % (slug, bad))
        title = p["title"].strip()
        pages.append({
            "slug": full, "name": title,
            "title": title + "｜あさひほうむ 特定技能サポート",
            "desc": p.get("description", "").strip() or title,
            "jsonld": "post", "date": p["date"], "category": p.get("category", ""),
            "parent": {"slug": "blog", "name": "お役立ち情報"}, "priority": "0.6",
            "cms": True, "body": p.get("body", ""), "eyecatch": p.get("eyecatch", ""),
        })
    # 新しい記事が先（一覧カードの並び順もこれに従う）
    return sorted(pages, key=lambda x: x["date"], reverse=True)


CMS_PAGES = load_cms_posts()
PAGES += CMS_PAGES


def cms_post_html(page):
    """CMS記事の本文を src/templates/post.html に流し込む（blog-*.html と同じ骨格）。"""
    tpl = (SRC / "templates" / "post.html").read_text(encoding="utf-8")
    eye = ""
    if page["eyecatch"]:
        eye = '<p><img src="%s" alt="" loading="lazy" style="width:100%%;border-radius:12px;"></p>' % (
            html.escape(page["eyecatch"], quote=True))
    return (tpl.replace("{{POST_TITLE}}", html.escape(page["name"]))
            .replace("{{POST_CATEGORY}}", html.escape(page["category"]))
            .replace("{{POST_DATE}}", page["date"].replace("-", "."))
            .replace("{{POST_EYECATCH}}", eye)
            .replace("{{POST_BODY}}", page["body"]))


def cms_post_cards():
    """blog.html 一覧の先頭に差し込むカード（date 降順・静的カードはその後ろに残る）。"""
    cards = []
    for p in CMS_PAGES:
        cards.append(
            '<article class="card post">\n'
            '        <span class="tag tag--field">%s</span>\n'
            '        <p class="post__meta">%s</p>\n'
            '        <h3><a href="%s.html">%s</a></h3>\n'
            '        <p class="muted">%s</p>\n'
            '      </article>' % (
                html.escape(p["category"]), p["date"].replace("-", "."),
                p["slug"], html.escape(p["name"]), html.escape(p["desc"])))
    return "".join("\n      " + c for c in cards)


def nav_html(current_slug):
    desk, mob = [], []
    for item in CFG["nav"]:
        # href は属性値に入るのでエスケープする（本文の {{CONTENT}} は信頼済みHTMLなので対象外）
        href = html.escape(item["href"], quote=True)
        label = html.escape(item["label"])
        desk.append('<li><a href="{0}" data-nav>{1}</a></li>'.format(href, label))
        mob.append('<li><a href="{0}">{1}</a></li>'.format(href, label))
    # お問い合わせ / 会員 はナビ末尾（モバイルのみ）に補助導線
    mob.append('<li><a href="contact.html">お問い合わせ</a></li>')
    return "\n        ".join(desk), "\n        ".join(mob)


def org_jsonld():
    org = CFG["org"]
    site = CFG["site"]
    data = {
        "@context": "https://schema.org",
        "@type": ["ProfessionalService", "Organization"],
        "name": site["name"],
        "legalName": org["legal_name"],
        "description": site["description"],
        "url": site["base_url"],
        "telephone": org["tel"],
        "email": org["email"],
        "areaServed": ["茨城県", "千葉県"],
        "knowsAbout": ["特定技能", "登録支援機関", "外国人雇用", "労務管理", "在留資格"],
        "openingHours": "Mo-Fr 09:00-18:00",
        "address": {"@type": "PostalAddress", "streetAddress": "榎戸681-5",
                    "addressLocality": "つくば市", "addressRegion": "茨城県",
                    "addressCountry": "JP"},
    }
    return data


FAQ_Q_RE = re.compile(r'<button[^>]*class="faq__q"[^>]*>(.*?)</button>', re.S)
FAQ_A_RE = re.compile(r'<div[^>]*class="faq__a"[^>]*>(.*?)</div>', re.S)
TAG_RE = re.compile(r"<[^>]+>")


def strip_tags(fragment):
    """HTML断片を構造化データ用のプレーンテキストへ落とす。"""
    return html.unescape(TAG_RE.sub("", fragment)).strip()


def faq_jsonld():
    # FAQページ用の構造化データは src/pages/faq.html から毎回生成する。
    # 以前はここに質問・回答を手書きで複製していたが、本文だけ直した時に
    # 静かにズレる（2026-08-01: 本文は相場を是正済なのに構造化データは旧相場のまま／
    # 本文8問に対し構造化データ5問と件数まで乖離）。複製を持たなければズレようがない。
    src = (SRC / "pages" / "faq.html").read_text(encoding="utf-8")
    questions = [strip_tags(m) for m in FAQ_Q_RE.findall(src)]
    answers = [strip_tags(m) for m in FAQ_A_RE.findall(src)]
    if not questions or len(questions) != len(answers):
        raise SystemExit(
            f"[BUILD ERROR] faq.html の質問{len(questions)}件と回答{len(answers)}件が対応しません")
    qa = list(zip(questions, answers))
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qa
    ]}


def breadcrumb_jsonld(page):
    if page["slug"] == "index":
        return None
    base = CFG["site"]["base_url"]
    items = [{"@type": "ListItem", "position": 1, "name": "ホーム", "item": base + "/"}]
    # 親ページがある場合は3階層（ホーム › 親 › 当ページ）
    parent = page.get("parent")
    if parent:
        items.append({"@type": "ListItem", "position": 2, "name": parent["name"],
                      "item": base + "/" + parent["slug"] + ".html"})
    items.append({"@type": "ListItem", "position": len(items) + 1, "name": page["name"],
                  "item": base + "/" + page["slug"] + ".html"})
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": items,
    }


def post_jsonld(page):
    # 記事ページ用 BlogPosting（著者=組織・日付は本公開時に実公開日へ更新）
    site = CFG["site"]
    url = site["base_url"] + "/" + page["slug"] + ".html"
    return {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": page["title"].split("｜")[0],
        "description": page["desc"],
        "datePublished": page["date"],
        "dateModified": page["date"],
        "inLanguage": site["lang"],
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "author": {"@type": "Organization", "name": site["name"]},
        "publisher": {"@type": "Organization", "name": site["name"],
                      "url": site["base_url"]},
        "articleSection": page.get("category", ""),
        **({"image": page["eyecatch"]} if page.get("eyecatch") else {}),
    }


def build_jsonld(page):
    blocks = [org_jsonld()]
    bc = breadcrumb_jsonld(page)
    if bc:
        blocks.append(bc)
    if page.get("jsonld") == "faq":
        blocks.append(faq_jsonld())
    if page.get("jsonld") == "post":
        blocks.append(post_jsonld(page))
    out = []
    for b in blocks:
        out.append('<script type="application/ld+json">\n'
                   + json.dumps(b, ensure_ascii=False, indent=2)
                   + "\n</script>")
    return "\n".join(out)


def download_texts():
    """資料ダウンロードページの文言を site.json の download 設定から機械で決める。

    手で「準備中」と書くと、PDF が届いても文言だけが古いまま残る（2026-09-02 実際に発生＝
    8/31 にPDFを配置したのにページは「ガイドブックは現在準備中です」と言い続けていた）。
    ＝配れるかどうかは PDF現物(guidebook_url) と 送信先(form_endpoint) の両方で決まるので、
    その2つだけを唯一の正にして、文言はここから出す。
    """
    dl = CFG.get("download", {})
    ready = bool(dl.get("guidebook_url")) and bool(dl.get("form_endpoint"))
    if ready:
        return {
            "{{DL_LEAD}}": "特定技能の受け入れに役立つ資料を、無料でご用意しています。<br>"
                           "メールアドレスのご登録だけで、その場でダウンロードいただけます。",
            "{{DL_STATUS}}": '<p class="muted">ご登録いただくと、その場でガイドブックを'
                             'ダウンロードいただけます。あわせて、今後の資料や制度改正の'
                             'お知らせをメールでお届けします。</p>',
            "{{DL_TAG}}": '<span class="tag">ダウンロードできます</span>',
        }
    # 未設定のうちは main.js もモック動作に落ちる＝画面の文言と実際の挙動を一致させる
    return {
        "{{DL_LEAD}}": "特定技能の受け入れに役立つ資料を、無料でご用意しています。<br>"
                       "ご登録の受付は準備中です。開始しだい、このページからご案内します。",
        "{{DL_STATUS}}": '<p class="muted">ただいまご登録の受付を準備中です。'
                         '受付を開始しましたら、ご登録のその場でダウンロードいただけます。</p>\n'
                         '        <p class="placeholder-note">※ ご登録の受付は、本番ドメインと'
                         'フォームの設定後に有効化します。現在はデモ表示です。</p>',
        "{{DL_TAG}}": '<span class="tag">受付準備中</span>',
    }


def video_blocks():
    """site.json videos.items から動画セクションのHTMLを組む。

    youtube_id が空の本は埋め込み iframe も目次も出さず「準備中」だけを出す。
    ＝公開後に直せない誤ったURLを載せないための既定値（members の準備中表示と同じ考え方）。
    """
    import html as _html

    vids = CFG.get("videos", {}).get("items", [])
    if not vids:
        return '<p class="placeholder-note">※ 動画は準備中です。</p>'
    out = []
    for i, v in enumerate(vids, 1):
        t = _html.escape(v["title"])
        lead = _html.escape(v["lead"])
        dur = _html.escape(v["duration"])
        yid = (v.get("youtube_id") or "").strip()
        parts = ['<article class="card" style="margin-bottom:32px;">']
        parts.append('<h2 style="margin-top:0;">%d. %s</h2>' % (i, t))
        parts.append('<p class="muted">%s（%s）</p>' % (lead, dur))
        if yid:
            parts.append(
                '<div style="position:relative;padding-top:56.25%%;margin:16px 0;">'
                '<iframe src="https://www.youtube-nocookie.com/embed/%s" title="%s" '
                'loading="lazy" allowfullscreen '
                'style="position:absolute;inset:0;width:100%%;height:100%%;border:0;"></iframe></div>'
                % (_html.escape(yid), t))
            parts.append('<h3>目次</h3><ul class="chapter-list">')
            for c in v.get("chapters", []):
                parts.append('<li><span class="chapter-list__t">%s</span> %s</li>'
                             % (_html.escape(c["t"]), _html.escape(c["label"])))
            parts.append("</ul>")
        else:
            parts.append('<p class="placeholder-note">※ この動画は現在準備中です。'
                         '公開でき次第、このページでご覧いただけます。</p>')
        parts.append("</article>")
        out.append("\n".join(parts))
    return "\n".join(out)


def site_verification_meta(site):
    """Google Search Console 所有権確認の meta（URLプレフィックス＋HTMLタグ方式）。
    site.json の google_site_verification が空なら出さない。英数字・-・_ 以外を含む値や
    長さが不自然な値も出さない（貼り間違いで壊れた <head> を公開しないため）。"""
    v = (site.get("google_site_verification") or "").strip()
    if not (20 <= len(v) <= 80 and all(c.isalnum() or c in "-_" for c in v)):
        return ""
    return f'<meta name="google-site-verification" content="{v}">'


def token_map(page):
    site = CFG["site"]
    org = CFG["org"]
    canonical = site["base_url"] + "/" + ("" if page["slug"] == "index" else page["slug"] + ".html")
    # 仮プレビュー時は全ページを検索除外（noindex,nofollow）
    robots = "noindex,nofollow" if site.get("preview") else page.get("robots", "index,follow")
    return {
        "{{LANG}}": site["lang"],
        "{{TITLE}}": page["title"],
        "{{DESCRIPTION}}": page["desc"],
        "{{ROBOTS}}": robots,
        "{{SITE_VERIFICATION}}": site_verification_meta(site),
        "{{CANONICAL}}": canonical,
        "{{OG_TYPE}}": "website" if page["slug"] == "index" else "article",
        "{{SITE_NAME}}": site["name"],
        "{{LOCALE}}": site["locale"],
        "{{BASE_URL}}": site["base_url"],
        "{{THEME_COLOR}}": site["theme_color"],
        "{{SITE_TAGLINE}}": site["tagline"],
        "{{SITE_DESC}}": site["description"],
        "{{COPYRIGHT}}": site["copyright_holder"],
        # 制定日は本公開日。未確定のうちは「本サイトの公開日」と明示する（嘘の日付を置かない）
        "{{POLICY_DATE}}": site.get("policy_date") or "本サイトの公開日",
        "{{ORG_LEGAL}}": org["legal_name"],
        "{{ORG_REP}}": org["representative"],
        "{{ORG_FOUNDED}}": org["founded"],
        "{{ORG_REG_NO}}": org["registration_no"],
        "{{ORG_TEL}}": org["tel"],
        "{{ORG_EMAIL}}": org["email"],
        "{{ORG_HOURS}}": org["hours"],
        # 支援受付は新規問い合わせと時間帯が別（2026-07-31 客様回答5）。未設定なら空文字で落とさない
        "{{ORG_HOURS_SUPPORT}}": org.get("hours_support", ""),
        "{{ORG_ADDRESS}}": org["address"],
        "{{ORG_AREAS}}": " / ".join(org["areas"]),
        "{{FORM_ENDPOINT}}": CFG["contact"]["form_endpoint"],
        # 資料ダウンロード（メール登録で即DL）。未設定のうちは空文字＝main.js がモック動作に落とす
        "{{DL_ENDPOINT}}": CFG.get("download", {}).get("form_endpoint", ""),
        "{{GUIDEBOOK_URL}}": CFG.get("download", {}).get("guidebook_url", ""),
        # 動画一覧。YouTube ID が空の本は埋め込まず「準備中」を出す（誤ったURLを載せないため）
        "{{VIDEO_BLOCKS}}": video_blocks(),
        # お役立ち情報 一覧の先頭に CMS 記事のカード（0件なら空）
        "{{CMS_POST_CARDS}}": cms_post_cards(),
        # 資料DLページの文言。PDF現物と送信先の2つから機械で決める（手打ちの stale を作らない）
        **download_texts(),
    }


def render(page, base):
    if page.get("cms"):
        content = cms_post_html(page)
    else:
        content = (SRC / "pages" / (page["slug"] + ".html")).read_text(encoding="utf-8")
    nav_d, nav_m = nav_html(page["slug"])
    html = base
    html = html.replace("{{JSONLD}}", build_jsonld(page))
    html = html.replace("{{NAV_DESKTOP}}", nav_d)
    html = html.replace("{{NAV_MOBILE}}", nav_m)
    html = html.replace("{{CONTENT}}", content)
    for k, v in token_map(page).items():
        html = html.replace(k, v)
    return html


def write_sitemap():
    base = CFG["site"]["base_url"]
    urls = []
    for p in PAGES:
        if p.get("robots", "").startswith("noindex"):
            continue
        loc = base + "/" + ("" if p["slug"] == "index" else p["slug"] + ".html")
        pri = "1.0" if p["slug"] == "index" else p.get("priority", "0.7")
        urls.append("  <url><loc>{0}</loc><priority>{1}</priority></url>".format(loc, pri))
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(urls) + "\n</urlset>\n")
    (DIST / "sitemap.xml").write_text(xml, encoding="utf-8")


def write_robots():
    base = CFG["site"]["base_url"]
    if CFG["site"].get("preview"):
        # 仮プレビュー: 全クローラ拒否（検索結果に出さない）
        txt = "User-agent: *\nDisallow: /\n"
    else:
        txt = ("User-agent: *\n"
               "Allow: /\n"
               "Sitemap: {0}/sitemap.xml\n".format(base))
    (DIST / "robots.txt").write_text(txt, encoding="utf-8")


def safe_rmtree(target):
    """rmtree の誤爆ガード。ROOT 直下の想定ディレクトリ以外は絶対に消さない。

    パス定義のバグや将来の書き換えで ROOT 外（$HOME や /）を指した場合に、
    黙って消さずその場で止める。破壊的操作は「消してよい根拠」を毎回確かめる。
    """
    if target.resolve().parent != ROOT.resolve() or target.name not in ("dist", "docs"):
        sys.exit("中止: 想定外のディレクトリを削除しようとしました -> {0}".format(target))
    if target.exists():
        shutil.rmtree(target)


# GitHub Pages の制御ファイル。dist/ には無いが docs/ には必要で、
# 同期のたびに消すと Pages の挙動が変わる（CNAME を消すと独自ドメインが落ちる）。
PAGES_CONTROL_FILES = (".nojekyll", "CNAME")


def publish():
    """dist/ の内容を docs/ へ同期する（GitHub Pages の公開ディレクトリが docs/ のため）。

    ⚠️ docs/ を更新して push するとクライアント送信済みのプレビューURLに即反映される。
    取締役の実物検証が済むまで実行しない（既定は build のみ）。
    """
    if not DIST.exists():
        sys.exit("中止: dist/ が無い状態で publish しようとしました（先に build してください）")
    # Pages 制御ファイルを退避してから入れ替え、あとで書き戻す
    keep = {}
    for name in PAGES_CONTROL_FILES:
        src = DOCS / name
        if src.exists():
            keep[name] = src.read_bytes()
    safe_rmtree(DOCS)
    shutil.copytree(DIST, DOCS)
    for name, data in keep.items():
        (DOCS / name).write_bytes(data)
    # .nojekyll は無いと _ 始まりのパスが無視される。退避が無ければ新規に作る。
    nojekyll = DOCS / ".nojekyll"
    if not nojekyll.exists():
        nojekyll.write_bytes(b"")
        keep.setdefault(".nojekyll", b"")
    print("published: {0} -> {1}（保持: {2}）".format(
        DIST, DOCS, ", ".join(sorted(keep)) or "なし"))


def main():
    safe_rmtree(DIST)
    DIST.mkdir(parents=True)
    # assets コピー
    shutil.copytree(SRC / "assets", DIST / "assets")
    base = (SRC / "templates" / "base.html").read_text(encoding="utf-8")
    for page in PAGES:
        out = render(page, base)
        (DIST / (page["slug"] + ".html")).write_text(out, encoding="utf-8")
        print("  built:", page["slug"] + ".html")
    write_sitemap()
    write_robots()
    print("done. {0} pages -> {1}".format(len(PAGES), DIST))
    if "--publish" in sys.argv:
        publish()


if __name__ == "__main__":
    main()
