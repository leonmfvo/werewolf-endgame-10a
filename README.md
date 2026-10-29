# werewolf-endgame-10a

10a狩配役（占い・霊能・狩人・狼2・狂人・村人4）の終盤表です。生存3〜9人の局面について、生きている人の本当の役と、村から見えている情報（グレー・確定白・確定黒・狩人CO済みなど）から、村勝率を厳密に（分数で）求めます。

- 公開ページ：https://leonmfvo.github.io/werewolf-endgame-10a/
- `index.html` / `app.js` / `app.css` / `style.css`：ページ（`data/states.json` を読む）
- `data/states.json`：全局面（6,712）の昼・夜の村勝率と、吊り先・噛み先の区分ごとの値
- `compute/endgame.py`：計算（局面の定義と前提はファイル冒頭とページの「前提」にあります）
- `compute/build_site.py`：`cd compute && python3 build_site.py ..` でページとデータを作り直す

関連：開始時からの全分岐ツリーと均衡は https://leonmfvo.github.io/werewolf-tree-10a/

## 盤面別勝率（5人日）

- `pos/`：wiki ふうの静的ページ。見た目の盤面（占,灰,灰,灰,灰 など）を1ページにし、真偽（占い真など）と生存状況（1w生存・1w1k生存・2w生存・狩生存・1wか1w1kか不明）ごとに村勝率・1日目の吊り先・最善進行・導出を載せる（`pos.html` は `pos/` への転送）
- `compute/pos/pos.py`：村と人外がそれぞれ見えている情報だけで手を決めるゲームを sequence form の線形計画で解き、分数で検算する
- `compute/pos/boards2.py`：見た目の盤面と真偽の一覧（生存状況は自動で並ぶ。ここに足せば増やせる）
- `compute/pos/derive.py`：導出の式と最善進行の表
- 作り直し：`cd compute/pos && python3 build_surf.py ../../data/pos5.json && python3 build_wiki.py ../..`
