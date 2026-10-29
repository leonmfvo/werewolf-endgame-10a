# werewolf-endgame-10a

10a狩配役（占い・霊能・狩人・狼2・狂人・村人4）の終盤表です。生存3〜9人の局面について、生きている人の本当の役と、村から見えている情報（グレー・確定白・確定黒・狩人CO済みなど）から、村勝率を厳密に（分数で）求めます。

- 公開ページ：https://leonmfvo.github.io/werewolf-endgame-10a/
- `index.html` / `app.js` / `app.css` / `style.css`：ページ（`data/states.json` を読む）
- `data/states.json`：全局面（6,712）の昼・夜の村勝率と、吊り先・噛み先の区分ごとの値
- `compute/endgame.py`：計算（局面の定義と前提はファイル冒頭とページの「前提」にあります）
- `compute/build_site.py`：`cd compute && python3 build_site.py ..` でページとデータを作り直す

関連：開始時からの全分岐ツリーと均衡は https://leonmfvo.github.io/werewolf-tree-10a/

## 盤面別勝率

- `pos/`：wiki ふうの盤面ページ。分岐サイト（werewolf-tree-10a）の全分岐ツリーに出てくる昼の盤面を、人数（3〜9人日）ごとに出やすい順に上位40個載せる。ページの中は内訳・狼の位置・狂人と狩人の生存確率で分け、次の昼にどの盤面へ帰着するかを確率つきで載せる
- 表記：占a・占b・占c＝占いCO者、白a＝占aの○、白ab＝占aと占bの○、黒a＝占aの●、確白＝人間確定、灰＝グレー
- `compute/tree/extract.py`：分岐サイトのツリー（`data/trees/`）から昼の局面と到達確率・帰着先を集める
- `compute/tree/notation.py`：局面の文字列を盤面の書き方に直す
- `compute/tree/build.py`：ページを作る
- 作り直し：`cd compute/tree && python3 extract.py <werewolf-tree-10a の場所> ents.json && python3 build.py ents.json ../.. 40`
- `compute/pos/`：旧版の厳密ソルバ（村が話し合いで吊る規則。今のページでは使っていない）
