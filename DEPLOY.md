# DEPLOY.md — Render に無料公開（静的サイト）

Python 引き出しトレーニングを **Render の Static Site** で公開する手順。
すべて静的HTMLなのでサーバもビルドも不要。無料プランでも**スリープしない**（Web Service と違う）。

## 全体像
- **GitHub**（`owtlawaaron/python-`）… コード置き場。`main` に push すると Render が自動デプロイ。
- **Render Static Site** … リポジトリ直下（`index.html` ほか）をそのままグローバルCDNで配信するだけ。
- **通信**… ページ配信は Render。記述モードと試行錯誤場だけ Pyodide を CDN から取得（初回のみ約10MB）。

### tango（成功例）との違い
tango は import の「みんなに公開」で共有DBを読み書きする `/api` を持つため
**Web Service（`server.js`／runtime: node）**で配信し、公開パスワード `IMPORT_PASS` を使う。
pydrill には合鍵もサーバも無い＝**純静的サイト**なので **Static Site（runtime: static）**を使う。
Static Site は無料でスリープせず、環境変数もサーバも不要。これが pydrill にとっての正解。

## 手順

### 1) GitHub（済み）
リポジトリ: `https://github.com/owtlawaaron/python-`（Public）。push で Render が自動デプロイ。

### 2) Render に接続
**方法A（Blueprint・推奨）**: Render ダッシュボード → **New → Blueprint** → このリポジトリを選択。
同梱の `render.yaml` を読んで `pydrill`（Static Site）が自動で作られる → **Apply**。

**方法B（手動）**: **New → Static Site** → リポジトリを選択 →
- **Build Command**: 空欄（またはそのまま）
- **Publish Directory**: `.`
- **Create Static Site**

デプロイ後 `https://pydrill-xxxx.onrender.com/` で開ける。

### 3) 確認
- `/`（入口）／`/pydrill.html`（組み立てドリル・辞書）が表示される
- `/pydrill-pro.html` の「記述モード」で **Pyodide が起動**して採点できる
- `/pyplay.html`（試行錯誤場）でコードが実行できる

## 注意・既知の性質
- **Static Site はスリープしない**（無料 Web Service のような起動待ちが無い）。
- **記述モード／試行錯誤場は初回だけ通信**（Pyodide 本体を CDN から取得。約10MB、2回目以降はキャッシュ）。
- **`file://` で直接開かない**（Pyodide の取得が環境により止まる）。ローカル確認は `python3 -m http.server`。
- GitHub Pages（`https://owtlawaaron.github.io/python-/`）はそのまま並行して使える。Render はもう1つの公開先。
