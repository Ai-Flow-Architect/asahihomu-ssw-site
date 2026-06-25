#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
あさひほうむ 特定技能サポート — 静的サイト ビルダー

役割:
  src/templates/base.html（共通レイアウト）に
  src/pages/<slug>.html（各ページ本文）を流し込み、
  共通トークン（社名・連絡先・ナビ・SEOメタ・構造化データ）を置換して
  dist/ に 15ページの完成HTML + sitemap.xml + robots.txt を出力する。

特徴:
  - ヘッダー/フッター/ナビは base.html に一元化（DRY・更新は1か所）
  - 連絡先・社名等は site.json に一元化（受注後の差し替えが1ファイルで完結）
  - 依存ライブラリなし。python3 build.py だけで再生成可能。

使い方:
  python3 build.py
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
DIST = ROOT / "dist"
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
     "desc": "茨城・千葉の2拠点で労務・行政手続きを支える「あさひ労務管理センター」。特定技能サポートの体制と理念をご紹介します。",
     "jsonld": "about"},
    {"slug": "voice", "name": "お客様の声",
     "title": "お客様の声・導入事例｜あさひほうむ 特定技能サポート",
     "desc": "特定技能外国人材を受け入れた企業の声・導入事例をご紹介します。安さと手厚さを両立したサポートの実際をご覧ください。",
     "jsonld": "article"},
    {"slug": "contact", "name": "お問い合わせ",
     "title": "お問い合わせ｜あさひほうむ 特定技能サポート",
     "desc": "特定技能外国人材の受け入れ・登録支援機関への委託に関するご相談・お見積りはこちらから。お気軽にお問い合わせください。",
     "jsonld": "contact"},
    {"slug": "members", "name": "会員ページ",
     "title": "会員ページ（限定資料ダウンロード）｜あさひほうむ",
     "desc": "既存のお客様向けの会員ページ。各種申請書類のテンプレートや限定資料をダウンロードいただけます。",
     "jsonld": None, "robots": "noindex,follow"},
    {"slug": "privacy", "name": "プライバシーポリシー",
     "title": "プライバシーポリシー｜あさひほうむ 特定技能サポート",
     "desc": "あさひほうむ 特定技能サポートにおける個人情報の取り扱い方針（プライバシーポリシー）です。",
     "jsonld": None},
]


def nav_html(current_slug):
    desk, mob = [], []
    for item in CFG["nav"]:
        href = item["href"]
        desk.append('<li><a href="{0}" data-nav>{1}</a></li>'.format(href, item["label"]))
        mob.append('<li><a href="{0}">{1}</a></li>'.format(href, item["label"]))
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
        "address": {"@type": "PostalAddress", "addressRegion": "茨城県・千葉県", "addressCountry": "JP"},
    }
    return data


def faq_jsonld():
    # FAQページ用の構造化データ（src/pages/faq.html の質問と同期）
    qa = [
        ("特定技能と技能実習は何が違いますか？",
         "技能実習は国際貢献・技能移転を目的とした制度ですが、特定技能は人手不足分野での就労を正面から認める在留資格です。特定技能は同一分野内での転職が可能で、即戦力としての就労を前提としています。"),
        ("登録支援機関に委託すると何をしてもらえますか？",
         "事前ガイダンスや生活オリエンテーション、公的手続きの同行、相談・苦情対応など、法律で義務づけられた10項目の支援を企業に代わって実施します。受け入れ企業の事務負担を大きく軽減できます。"),
        ("費用はどのくらいかかりますか？",
         "支援委託費は受け入れ人数や支援内容によって異なります。あさひほうむでは安さと手厚さを両立した明朗な料金でご案内しています。詳しくはお問い合わせください。"),
        ("受け入れまでどのくらいの期間が必要ですか？",
         "海外からの新規入国か、国内在留者の切り替えかによって異なりますが、一般的に数か月程度を見込みます。スケジュールも含めて個別にご案内します。"),
        ("茨城・千葉以外でも対応してもらえますか？",
         "まずはお問い合わせください。対応可否を含めてご相談を承ります。"),
    ]
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
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ホーム", "item": CFG["site"]["base_url"] + "/"},
            {"@type": "ListItem", "position": 2, "name": page["name"],
             "item": CFG["site"]["base_url"] + "/" + page["slug"] + ".html"},
        ],
    }


def build_jsonld(page):
    blocks = [org_jsonld()]
    bc = breadcrumb_jsonld(page)
    if bc:
        blocks.append(bc)
    if page.get("jsonld") == "faq":
        blocks.append(faq_jsonld())
    out = []
    for b in blocks:
        out.append('<script type="application/ld+json">\n'
                   + json.dumps(b, ensure_ascii=False, indent=2)
                   + "\n</script>")
    return "\n".join(out)


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
        "{{CANONICAL}}": canonical,
        "{{OG_TYPE}}": "website" if page["slug"] == "index" else "article",
        "{{SITE_NAME}}": site["name"],
        "{{LOCALE}}": site["locale"],
        "{{BASE_URL}}": site["base_url"],
        "{{THEME_COLOR}}": site["theme_color"],
        "{{SITE_TAGLINE}}": site["tagline"],
        "{{SITE_DESC}}": site["description"],
        "{{COPYRIGHT}}": site["copyright_holder"],
        "{{ORG_LEGAL}}": org["legal_name"],
        "{{ORG_REP}}": org["representative"],
        "{{ORG_REG_NO}}": org["registration_no"],
        "{{ORG_TEL}}": org["tel"],
        "{{ORG_EMAIL}}": org["email"],
        "{{ORG_HOURS}}": org["hours"],
        "{{ORG_ADDRESS}}": org["address"],
        "{{ORG_AREAS}}": " / ".join(org["areas"]),
        "{{FORM_ENDPOINT}}": CFG["contact"]["form_endpoint"],
    }


def render(page, base):
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
        pri = "1.0" if p["slug"] == "index" else "0.7"
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
               "Disallow: /members.html\n"
               "Sitemap: {0}/sitemap.xml\n".format(base))
    (DIST / "robots.txt").write_text(txt, encoding="utf-8")


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
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


if __name__ == "__main__":
    main()
