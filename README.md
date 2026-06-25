# あさひほうむ 特定技能サポート — コーポレート/サービスサイト

茨城・千葉の登録支援機関「あさひほうむ（あさひ労務管理センター）」向けの、
特定技能サポート専用サイト（提案スタンダードプラン＝15ページ構成）。

> ⚠️ **受注前の先行ビルド**です。本番デプロイはしていません（feature ブランチ運用）。
> 代表者名・住所・電話番号・登録番号・お問い合わせ送信先・会員認証などは
> プレースホルダ／モックです。受注確定後に正式値へ差し替えて本番化します。

## 構成

```
asahihomu-ssw-site/
├── site.json              # サイト共通設定（社名・連絡先・ナビ・SEO）★差し替えはここ
├── build.py               # 静的サイトビルダー（python3 build.py で再生成）
├── src/
│   ├── templates/base.html   # 共通レイアウト（ヘッダー/フッター/ナビ/SEOメタ）
│   ├── pages/*.html          # 各ページ本文（15枚）
│   └── assets/
│       ├── css/style.css     # デザインシステム（モバイルファースト）
│       ├── js/main.js        # ナビ・FAQ・フォーム挙動（依存ライブラリなし）
│       └── img/favicon.svg
└── dist/                  # ★ビルド成果物（公開対象）。build.py が生成
```

## ビルド方法

```bash
python3 build.py
```

`dist/` に 15ページ + `sitemap.xml` + `robots.txt` が生成されます。
ローカル確認は `dist/` を任意の静的サーバーで開くだけ（例: `python3 -m http.server -d dist`）。

## ページ一覧（15）

| # | ファイル | 内容 |
|---|----------|------|
| 1 | index.html | トップ（ヒーロー・強み・サービス・流れ・CTA） |
| 2 | about-ssw.html | 特定技能とは（制度解説） |
| 3 | support.html | 支援内容（義務的支援10項目） |
| 4 | industries.html | 対応分野（特定技能16分野） |
| 5 | pricing.html | 料金プラン |
| 6 | flow.html | ご利用の流れ |
| 7 | reasons.html | 選ばれる理由 |
| 8 | jobs.html | 特定技能 求人掲載ページ |
| 9 | blog.html | お役立ち情報（投稿機能フロント） |
| 10 | faq.html | よくある質問（FAQ構造化データ付き） |
| 11 | about-us.html | 事務所紹介 |
| 12 | voice.html | お客様の声・導入事例 |
| 13 | contact.html | お問い合わせ（フォーム） |
| 14 | members.html | 会員ページ（限定資料DL・noindex） |
| 15 | privacy.html | プライバシーポリシー |

## SEO 土台（実装済み）

- 各ページ個別の `title` / `meta description` / canonical / OGP / Twitter Card
- 構造化データ（JSON-LD）：Organization/ProfessionalService・BreadcrumbList・FAQPage
- `sitemap.xml` / `robots.txt` 自動生成（会員ページは noindex / Disallow）

## 🔴 受注後に対応する項目（外部依存・要顧客判断）

差し替え・有効化が必要な箇所は、ソース内に `placeholder-note` クラスや
`site.json` のコメントで明示しています。

1. **連絡先・事業者情報** … `site.json` の `org`（代表者名・住所・電話・登録番号）
2. **お問い合わせ送信先** … `site.json` の `contact.form_endpoint`（Formspree/独自サーバー等）
3. **投稿・編集機能（CMS）** … blog/jobs の更新基盤。方式は受注後に確定（WordPress / ヘッドレスCMS 等）
4. **会員ページの認証・限定DL** … 認証基盤の構築が必要
5. **本番ドメイン・サーバー** … 御社ご負担の実費契約
6. **Search Console 登録** … 御社アカウントでの実登録
7. **お客様の声・実績** … 掲載許諾を得た実データへ差し替え

## 技術メモ

- 依存ライブラリ・ビルドツールなし（Python標準ライブラリのみ）。どの静的ホストにもそのまま載る。
- ヘッダー/フッター/ナビ/連絡先は一元管理（base.html + site.json）。15ページの一括更新が1か所で完結。
