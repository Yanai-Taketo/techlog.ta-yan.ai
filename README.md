# テックろぐ (techlog.ta-yan.ai)

WordPress(さくらのレンタルサーバ + SANGOテーマ)から移行した、静的サイト版「テックろぐ」です。

| 項目 | 採用技術 |
|---|---|
| フレームワーク | [Astro](https://astro.build/) 7(静的サイト生成) |
| デザイン | [デジタル庁デザインシステム](https://design.digital.go.jp/)(`@digital-go-jp/tailwind-theme-plugin` + デザイントークン準拠のカスタムCSS) |
| CSS | Tailwind CSS 4 |
| ホスティング | Cloudflare Workers(静的アセット)/ Cloudflare Pages |
| サイト内検索 | [Pagefind](https://pagefind.app/)(日本語対応・ビルド時にインデックス生成) |
| 広告 | Google AdSense(旧サイトの広告ユニットを継続使用) |
| アクセス解析 | Google Analytics 4(`G-DVK9T8VYBR`) |

## ディレクトリ構成

```
├── src/
│   ├── content/
│   │   ├── blog/            # 記事(Markdown)。ファイル名がURLになる
│   │   └── pages/           # 固定ページ(info, logo-guidelines)
│   ├── components/          # UIパーツ(広告・記事カード・ページ送り等)
│   ├── layouts/             # Base(全体) / Article(記事)
│   ├── pages/               # ルーティング
│   ├── plugins/             # remarkプラグイン(コールアウト・リンクカード)
│   └── styles/global.css    # デジタル庁DSベースの全体スタイル
├── public/
│   ├── wp-content/uploads/  # 旧サイトから引き継いだ画像(URLパス維持)
│   ├── ads.txt              # AdSense用
│   ├── _redirects           # 旧URL→新URLの301リダイレクト定義
│   └── robots.txt
├── scripts/convert_wp.py    # WordPress DB→Markdown変換スクリプト(移行時に使用した記録)
└── wrangler.jsonc           # Cloudflare Workers設定
```

## 記事の書き方

記事の編集方法は2通りあります。

1. **ブラウザで編集(CMS)**: `https://techlog.ta-yan.ai/admin/` にアクセスし、GitHubアカウントでログインします([Sveltia CMS](https://github.com/sveltia/sveltia-cms)・日本語UI対応)。記事の作成・編集・画像アップロードがWordPressの管理画面に近い感覚で行え、保存するとGitHubへコミット→自動デプロイされます。初回セットアップは「[CMSのセットアップ](#cmsのセットアップ)」を参照
2. **Markdownを直接編集**: `src/content/blog/` に Markdown ファイルを置くだけで記事になります。**ファイル名(拡張子を除く)がそのままURL**になります(例: `my-new-post.md` → `https://techlog.ta-yan.ai/my-new-post/`)。

> 旧WordPress記事は互換性のため `20260610` + 記事ID という旧URL形式のファイル名になっています。新しい記事は自由な英数字スラッグで構いません。

### frontmatter(記事の先頭に書くメタ情報)

```markdown
---
title: "記事タイトル"
description: "検索結果やOGPに使われる説明文(1〜2文)"
pubDate: 2026-08-13T12:00:00+09:00
categories: ["備忘録"]        # 備忘録 / テクニック / ニュース / テクノロジー / 雑談
image: "/wp-content/uploads/2026/08/example.png"   # アイキャッチ(任意)
draft: false                  # true にすると非公開
affiliate: false              # アフィリエイトリンク(Amazonアソシエイト等)を含む記事は true にする
---

本文をここに書く。
```

### 独自記法(コールアウト・リンクカード)

旧SANGOテーマの装飾ブロックの置き換えとして、以下のディレクティブ記法が使えます。

```markdown
:::memo{title="MEMO"}
補足メモ(青いボックス)
:::

:::alert{title="注意"}
注意書き(黄色いボックス)
:::

:::box{title="タイトル"}
汎用ボックス(タイトルは省略可)
:::

::linkcard[リンクのタイトル]{url="https://example.com" site="サイト名" image="/path/to/thumb.png"}
```

コードブロックにラベルを付けたい場合は、直前に `<div class="code-label">PowerShell</div>` を置きます。

### 画像

`public/` 配下に置いたファイルがそのまま配信されます。新規画像は `public/images/2026/…` のように置き、`![説明](/images/2026/example.png)` で参照してください(旧記事の画像は `public/wp-content/uploads/` にパス互換で配置済み)。

### 広告・アフィリエイトの表記ルール(重要)

- **アフィリエイトリンクを含む記事は frontmatter で `affiliate: true` にする** — 記事冒頭に「本記事にはアフィリエイト広告(Amazonアソシエイト)が含まれています」が自動表示されます。ステマ規制(景品表示法)対応のため、Amazonアソシエイト等のリンクを貼る記事では必須です
- AdSense広告ユニットには「スポンサーリンク」ラベルを自動表示しています。**ラベル文言はAdSense規約上「広告」「スポンサーリンク」の2種のみ許可**(「スポンサードリンク」「PR」「AD」等は不可)なので変更しないでください
- Amazonアソシエイトの必須文言(「Amazonのアソシエイトとして、テックろぐは適格販売により収入を得ています。」)は全ページのフッターに表示しています
- 検索ページ・404ページには広告を置かないでください(コンテンツのないページへの掲載はAdSenseポリシー違反)

## ローカル開発

```sh
npm install
npm run dev      # http://localhost:4321 (検索は動きません)
npm run build    # dist/ に本番ビルド+検索インデックス生成
npm run preview  # ビルド結果の確認
```

## CMSのセットアップ

CMS本体(`/admin/`)はサイトに同梱済みです。GitHubログインの認証中継用に、小さなWorkerを一度だけデプロイする必要があります。

1. **認証Workerのデプロイ**: [sveltia/sveltia-cms-auth](https://github.com/sveltia/sveltia-cms-auth) の「Deploy to Cloudflare Workers」ボタンから自分のCloudflareアカウントへデプロイし、Worker URL(例: `https://sveltia-cms-auth.xxxx.workers.dev`)を控える
2. **GitHub OAuth Appの作成**: GitHub → Settings → Developer settings → [OAuth Apps](https://github.com/settings/applications/new) → New OAuth App
   - Application name: `Sveltia CMS Authenticator`(任意)
   - Homepage URL: `https://techlog.ta-yan.ai`
   - Authorization callback URL: `<Worker URL>/callback`
   - 作成後に Client ID を控え、「Generate a new client secret」で Client Secret を発行
3. **Workerに環境変数を設定**: Cloudflareダッシュボード → 該当Worker → Settings → Variables
   - `GITHUB_CLIENT_ID`: 上記Client ID
   - `GITHUB_CLIENT_SECRET`: 上記Client Secret(「暗号化」を選択)
   - `ALLOWED_DOMAINS`: `techlog.ta-yan.ai`(プレビューでも使う場合はカンマ区切りで追加)
4. **config.ymlの更新**: `public/admin/config.yml` の `base_url:` を手順1のWorker URLに書き換えてコミット

## デプロイ(Cloudflare)

GitHub連携で main ブランチへのプッシュのたびに自動デプロイされる構成を想定しています。

1. [Cloudflareダッシュボード](https://dash.cloudflare.com/) → **Workers & Pages** → **Create** → **Import a repository** でこのリポジトリを選択
2. ビルド設定:
   - Build command: `npm run build`
   - Deploy command(Workersの場合): `npx wrangler deploy`(`wrangler.jsonc` が使われます)
   - ※ Pagesを選ぶ場合は Build output directory: `dist`
3. デプロイ後、`*.workers.dev`(または `*.pages.dev`)のプレビューURLで表示確認
4. **カスタムドメイン設定**: Workers/Pages の設定画面で `techlog.ta-yan.ai` を追加
   - `ta-yan.ai` のDNSがCloudflare管理なら自動でレコードが張られます
   - 外部DNSの場合は案内されるCNAMEレコードを追加します

### 本番切替チェックリスト

- [ ] プレビューURLで全ページ・画像・検索・リダイレクトの動作確認
- [ ] `techlog.ta-yan.ai` のDNSをCloudflareへ向ける(サブドメインのみ。ルートドメインやメールには影響しない)
- [ ] https://techlog.ta-yan.ai/ads.txt が配信されていることを確認
- [ ] AdSense管理画面 → サイト でステータス確認(ドメイン不変のため再審査は不要)
- [ ] AdSense管理画面 → プライバシーとメッセージ → **広告ブロック回復メッセージを有効化**(タグは設置済み)
- [ ] Google Search Console でsitemap(`https://techlog.ta-yan.ai/sitemap-index.xml`)を送信
- [ ] GA4のリアルタイムレポートで計測確認
- [ ] 旧URL(例: `/en/20231230609/`、`/feed/`)が301リダイレクトされることを確認
- [ ] 2〜4週間ほど問題ないことを確認後、さくらのレンタルサーバ上のWordPressを停止・解約

## 移行に関する設計メモ

- **URL互換**: 旧WordPressのパーマリンク(`/{YYYYMMDD}{記事ID}/`)をそのまま維持しているため、日本語記事はリダイレクト不要。`?title=…` のクエリ文字列は無視されます(静的ホスティングはパスのみでルーティング)
- **英語版記事**: 移行対象外とし、`public/_redirects` で日本語版へ301リダイレクト
- **画像**: 旧 `wp-content/uploads` のパスを維持(被リンク・Google画像検索のインデックスを保全)。本文から参照されているファイルのみ引き継ぎ
- **広告**: 旧サイトの広告ユニット(記事タイトル下 `1243417992`、記事下 `8126189415`、一覧下 `4159024247`)を継続使用。ユニットの追加・変更は `src/components/Ad.astro` の利用箇所を編集
- **コメント・問い合わせフォーム**: 廃止(旧サイトでもほぼ未使用のため)
- **変換元データ**: WordPressのDBダンプおよびバックアップZIPは個人情報を含むため**リポジトリには含めていません**(Boxに保管)

## 要確認・TODO

- [ ] プライバシーポリシー(`src/pages/privacy-policy.astro`)の文面を確認・必要に応じて修正(旧サイトでは下書きのままだったため新規作成)
- [ ] AdSense「広告ブロック回復メッセージ」をAdSense管理画面で作成・有効化(旧サイトの有料プラグインの代替。不要ならBase.astroの該当スクリプトを削除)
- [ ] CMSの認証Workerセットアップ(上記「CMSのセットアップ」の手順1〜4)
