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

## お役立ち情報の更新（CMS＝microCMS ＋ GitHub Actions）

記事は microCMS の「お役立ち情報（posts）」で書き、公開ボタンを押すだけでサイトに載ります。

### 月1回の操作（3手）
1. microCMS にログイン →「お役立ち情報（posts）」→「追加」
2. タイトル・カテゴリ・本文を書く。URL用の `slug` は半角英数字とハイフンで短く（例 `visa-renewal`）
3. 「公開」を押す → 数分後にサイトの「お役立ち情報」に載る（他の操作は不要）

### 気をつけること
- **公開後に `slug` を変えない・公開した記事を削除や下書きに戻さない**（元のURLが開けなくなります）。直したい・消したい時は制作側へご連絡ください（内容の修正はそのまま上書きして公開すれば反映されます）
- 本文には YouTube の埋め込み・画像・見出し・箱組みが使えます。それ以外の埋め込み（外部の iframe やスクリプト）は安全のため載りません
- 「公開」を押して10分たっても載らない時は制作側へご連絡ください（自動ビルドの失敗は制作側へ通知が届きます）

### 仕組み（制作側メモ）
```
microCMS で公開 → Webhook(GitHub Actions 連携・event: cms-update)
  → .github/workflows/build.yml
     fetch_cms.py --require-key   … 記事を全件取得 → content/cms_posts.json
     build.py                     … 既存の PAGES に記事を足して dist/ 生成
     checks.py                    … 機械検査（赤なら docs/ に触らず終了）
     build.py --publish           … dist/ → docs/（.nojekyll/CNAME は保持）
     git commit / push            … content/cms_posts.json ＋ docs/
```
- 鍵は GitHub Secrets（`MICROCMS_SERVICE_DOMAIN` / `MICROCMS_API_KEY`＝GET専用）だけ。ローカルで鍵が無い時は既存記事だけでビルドされる
- `content/cms_posts.json` はコミットする＝ローカル再現と記事データの持ち出し（将来の移設）のため
- workflow は push では走らない（repository_dispatch / 手動のみ）。`site.json` の preview・CNAME には触らない
- 検証: `python3 test_cms.py`（T1〜T9）／`python3 test_cms_mutation.py`（守りを外すと赤くなる実証）

## 技術メモ

- 依存ライブラリ・ビルドツールなし（Python標準ライブラリのみ）。どの静的ホストにもそのまま載る。
- ヘッダー/フッター/ナビ/連絡先は一元管理（base.html + site.json）。15ページの一括更新が1か所で完結。
