# werewolf-endgame-10a

10a狩配役（占い・霊能・狩人・狼2・狂人・村人4）の終盤表です。生存3〜9人の局面について、生きている人の本当の役と、村から見えている情報（グレー・確定白・確定黒・狩人CO済みなど）から、村勝率を厳密に（分数で）求めます。

- 公開ページ：https://leonmfvo.github.io/werewolf-endgame-10a/
- `index.html` / `app.js` / `app.css` / `style.css`：ページ（`data/states.json` を読む）
- `data/states.json`：全局面（6,712）の昼・夜の村勝率と、吊り先・噛み先の区分ごとの値
- `compute/endgame.py`：計算（局面の定義と前提はファイル冒頭とページの「前提」にあります）
- `compute/build_site.py`：`cd compute && python3 build_site.py ..` でページとデータを作り直す

関連：開始時からの全分岐ツリーと均衡は https://leonmfvo.github.io/werewolf-tree-10a/

## 盤面別勝率

- `pos/`：wiki ふうの盤面ページ（3〜9人日）。盤面は生きている人の見た目（占a,占b,白a,白ab,黒a,確白,灰 など。◎ 真置き、✕ 破綻）。ページの中を内訳・狼の位置と、人外の残り（1w1k生存 など）・狩人の位置（灰に狩／狩CO済み／なし）で分け、村勝率と次の昼の帰着先を載せる
- 規則と計算は分岐サイト（werewolf-tree-10a）と同じエンジン。村の進行は分岐サイトがその内訳に使っている進行
- `compute/tree/extract.py`：分岐サイトのツリーから昼の盤面と到達確率を集める（盤面の選び方に使う）
- `compute/tree/eng/`：分岐サイトのエンジン一式（engine10x・tree10ax など）と、盤面＋条件から局面を作って解く `board.py`・`state.py`・`eng_build.py`
- `compute/tree/render.py`：ページを作る
- 作り直し：`cd compute/tree && python3 extract.py <werewolf-tree-10a> ents.json && python3 eng/eng_build.py ents.json cache 40 4 && python3 render.py cache ../..`
- `compute/pos/`：旧版の厳密ソルバ（村が話し合いで吊る規則。今のページでは使っていない）
