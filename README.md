# Python 引き出しトレーニング

Python の演算子・文・入力処理を「やりたいこと → 形」で引けるようにするための学習アプリ。すべて静的HTMLで、ビルド工程はない。

| ファイル | 中身 | 通信 |
|---|---|---|
| `index.html` | 入口 | 不要 |
| `pydrill.html` | 組み立てドリル46問 + 辞書30見出し + その場実行 | 実行ボタンを押した時のみ |
| `pydrill-pro.html` | 上記 + 記述モード18問 | 実行機能・記述モードのみ初回10MB |
| `pyplay.html` | コード実行の試行錯誤場 | 初回10MB |
| `python-patterns.md` | 定型パターン辞書26件 | 不要 |

記述モードと試行錯誤場、および辞書の「動かす」／出題の「いじってみる」は Pyodide（WebAssembly 版 CPython 3）を `cdn.jsdelivr.net` から読み込む。**押した瞬間にだけ**取りに行くので、押さなければ通信は起きない。取得に失敗しても46問と辞書はそのまま使える。

---

## デプロイ手順

### A. Netlify Drop — アカウント不要、いちばん速い

1. https://app.netlify.com/drop を開く
2. このフォルダ（または `site.zip`）をブラウザにドラッグ
3. その場で URL が発行される

### B. GitHub Pages

1. GitHub で新しいリポジトリを作る（Public）
2. リポジトリのトップで **Add file → Upload files**
3. このフォルダの中身を**すべて**ドラッグして Commit
   - `.nojekyll` を含めること（Jekyll の処理を止めるため。入れ忘れると `_` 始まりのファイルが無視される）
4. **Settings → Pages** で Source を `Deploy from a branch`、Branch を `main` / `/ (root)` にして Save
5. 1〜2分後に `https://<ユーザー名>.github.io/<リポジトリ名>/` で公開される

### C. Render

静的サイトとして置く場合、先に B の 1〜3 でリポジトリを作っておく。

1. Render で **New → Static Site**
2. そのリポジトリを選ぶ
3. 設定は次のとおり
   - **Build Command**: 空欄
   - **Publish Directory**: `.`
4. Create Static Site

Render は Web Service（サーバープロセス）向けの機能が主なので、この用途では B より手間が増える。特別な理由がなければ Netlify Drop か GitHub Pages で十分。

---

## ローカルで確認する

`file://` で直接開くと Pyodide の取得が環境によって止まる。ローカルで確認するときは簡易サーバーを立てる。

```
cd site
python3 -m http.server
```

→ `http://localhost:8000/`

## 既知の制約

- **無限ループ**を書いても大丈夫。実行中は「実行」が「中断」に変わり、押せば即座に止まる（Pyodide は Web Worker で動いている）
- 記述モードの採点は**標準出力の照合**。行末の余分な空白と前後の空行は無視する
- 初回起動はスマホだと十数秒かかる
- ドリルの記録（XP・連続日数・正答率）は localStorage 保存。ブラウザやデバイスをまたいでは共有されない
