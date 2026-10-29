# data/pos5.json から、wiki ふうの静的ページ（左にメニュー、1盤面1ページ）を pos/ に書き出す
import json, os, sys, html, datetime
from fractions import Fraction as F

ROOT = sys.argv[1] if len(sys.argv) > 1 else '../..'
D = []
for n in (3, 5, 6):
    f = os.path.join(ROOT, f'data/pos{n}.json')
    if os.path.exists(f): D += json.load(open(f))
DAYS = sorted({b['day'] for b in D})
OUT = os.path.join(ROOT, 'pos'); os.makedirs(OUT, exist_ok=True)
TODAY = datetime.date.today().isoformat()
e = html.escape

def fv(s): a, _, b = s.partition('/'); return F(int(a), int(b or 1))
def pct(s): return f'{float(fv(s)) * 100:.1f}%'
def sym(s): return f'P<sub>{s[1:]}</sub>' if s.startswith('P') and len(s) > 1 else ('P' if s == 'P' else s)
def outcome(v): return '村勝ち' if v == '1' else '狼勝ち' if v == '0' else v
def name(b): return ','.join(b['labels'])

def group(b):
    L = b['labels']
    if L.count('占') == 2: return '占い2CO'
    if L.count('霊') == 2: return '霊能2CO'
    return '占い師あり' if '占' in L else '占い師なし'
GROUPS = ['占い師あり', '占い2CO', '占い師なし', '霊能2CO']

def menu(cur):
    out = ['<div class="side"><div class="mb"><div class="mh">メニュー</div><a href="index.html">トップページ</a><a href="index.html#rules">前提</a><a href="../index.html">終盤表（役と見え方の人数から）</a></div>']
    for d in DAYS:
        out.append(f'<div class="mb"><div class="mh">{d}人日</div>')
        for g in GROUPS:
            bs = [b for b in D if b['day'] == d and group(b) == g]
            if not bs: continue
            out.append(f'<div class="mg">{e(g)}</div><ul>')
            for b in bs:
                c = ' class="cur"' if b['id'] == cur else ''
                out.append(f'<li><a href="{b["id"]}.html"{c}>{e(name(b))}</a></li>')
            out.append('</ul>')
        out.append('</div>')
    out.append('</div>')
    return ''.join(out)

def page(title, body, cur=None, desc=''):
    return f'''<!doctype html>
<html lang="ja" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<title>{e(title)} - 10a狩 盤面別勝率</title>
<meta name="description" content="{e(desc)}">
<link rel="stylesheet" href="wiki.css">
</head>
<body>
<header class="site"><a href="index.html">10a狩 盤面別勝率</a></header>
<div class="layout">
<main class="main"><article>{body}<div class="upd">最終更新：{TODAY}</div></article><div class="totop"><a href="#">ページトップ</a></div></main>
{menu(cur)}
</div>
<footer class="foot">10a狩（占い・霊能・狩人・狼2・狂人・村人4）の盤面ごとの村勝率。計算：<a href="https://github.com/leonmfvo/werewolf-endgame-10a/tree/main/compute/pos">compute/pos</a></footer>
</body>
</html>
'''

def section(sec, aid):
    b = sec; multi = len(b['cases']) > 1
    s = [f'<h3 id="{aid}">{e(sec["title"])} → {b["value"]}</h3>']
    s.append(f'<p class="big">村勝率 {b["value"]}（{pct(b["value"])}）</p>')
    if multi:
        s.append('<p class="sm">村はどちらか分からないので、平均が一番高くなる進行をとる</p><ul class="arrow">')
        for c in b['cases']:
            k = '' if c['known'] == c['value'] else f'（分かっていれば {c["known"]}）'
            s.append(f'<li>{e(c["name"])}だった場合 → {c["value"]}{k}</li>')
        s.append('</ul>')
    s.append('<p class="sub">1日目の吊り先</p><ul class="arrow">')
    best = max(fv(v) for r in b['root'] for v in r['values'])
    for r in b['root']:
        v = r['value'] or '〜'.join(r['values'])
        isb = any(fv(x) == best for x in r['values'])
        s.append(f'<li>{e(r["label"])}を吊る → {v}{" <b>← 最善</b>" if isb else ""}</li>')
    s.append('</ul><p class="sub">最善進行</p><ul class="arrow">')
    for p in b['policy']:
        seen = '' if p['seen'] == '初日' else f'（{e(p["seen"])}）'
        pr = '' if p['p'] == '1' else f'（{p["p"]}）'
        s.append(f'<li>{e(p["when"])}{seen}：<b>{e(p["act"])}</b>{pr}</li>')
    s.append('</ul>')
    for d, c in zip(b['deriv'], b['cases']):
        s.append(f'<details><summary>導出{"（" + e(d["name"]) + "）" if multi else ""}</summary>')
        for r in d['f']:
            s.append('<div class="ans">')
            if r['path']: s.append(f'<p class="path">{e(" → ".join(r["path"]))}</p>')
            if len(r['alts']) > 1:
                s.append('<p class="alt">人外の選択：' + '、'.join(
                    (f'<b>{e(a["label"])}→{a["value"]}</b>' if a['chosen'] else f'{e(a["label"])}→{a["value"]}') for a in r['alts']) + '</p>')
            rhs = ' + '.join(f'{t["q"]}×{sym(t["v"])}' for t in r['terms'])
            tail = f' = {r["value"]}' if (len(r['terms']) > 1 or r['terms'][0]['v'] != r['value']) else ''
            s.append(f'<p class="eq">{sym(r["sym"])} = {rhs}{tail}</p><ul>')
            for t in r['terms']:
                rv = f'{sym(t["v"])} = {t["val"]}' if t.get('val') else outcome(t['v'])
                s.append(f'<li>{t["q"]}：{e(t["ev"])} → {rv}</li>')
            s.append('</ul></div>')
        s.append('</details>')
    return ''.join(s)

def board_page(b):
    s = [f'<h1 class="pt">{e(name(b))}<span class="day">{b["day"]}人日</span></h1>']
    body = []
    summ = []
    for ti, t in enumerate(b['truths']):
        if t['name']: body.append(f'<h2>{e(t["name"])}の場合</h2>')
        summ.append(f'<p class="sub">{e(t["name"]) or "生存状況"}</p><ul class="arrow">' if t['name'] else '<ul class="arrow">')
        for si, sec in enumerate(t['sections']):
            aid = f't{ti + 1}-{si + 1}'
            body.append(section(sec, aid))
            summ.append(f'<li><a href="#{aid}">{e(sec["title"])}</a> → {sec["value"]}（{pct(sec["value"])}）</li>')
        summ.append('</ul>')
    s.append('<h2>まとめ</h2>' + ''.join(summ))
    s += body
    return page(f'{b["day"]}人日 {name(b)}', ''.join(s), b['id'], f'{b["day"]}人日 {name(b)} の生存状況ごとの村勝率と最善進行')

def index_page():
    s = ['<h1 class="pt">10a狩 盤面別勝率</h1>',
         '<p>盤面は生きている人の見え方を横一列に並べ、（ ）に条件を書きます。盤面を選ぶと、真偽（占い真など）と生存状況（1w生存・1w1k生存・2w生存、狩生存かどうか）ごとに村勝率・最善進行・導出が並びます。</p>',
         '<p class="sm">占＝占いCO者、霊＝霊能CO者、狩＝狩人CO者、白＝確定白、黒＝確定黒、灰＝グレー。w＝狼、k＝狂人。真偽と生存状況は村が知っているものとして解きます。「1wか1w1kか不明」は両方を等確率とし、村は平均が一番高くなる進行をとります。</p>']
    for d in DAYS:
        s.append(f'<h2>{d}人日</h2>')
        for g in GROUPS:
            bs = [b for b in D if b['day'] == d and group(b) == g]
            if not bs: continue
            s.append(f'<p class="sub">{e(g)}</p><ul>')
            for b in bs:
                ts = '、'.join(t['name'] for t in b['truths'] if t['name'])
                s.append(f'<li><a href="{b["id"]}.html">{e(name(b))}</a> <span class="sm">{e(ts)}</span></li>')
            s.append('</ul>')
    s.append('''<h2 id="rules">前提</h2><ul>
<li>配役：10a狩（占い・霊能・狩人・狼2・狂人・村人4）。生存3・5・6人の昼から始める。役の数から起こりえない組み合わせと、始まった時点で決着している組み合わせ（5人日の2w1k生存はPPで狼勝ち）は載せない。3人日は夜が来ないので、灰の狩人の有無では分けない。</li>
<li>内訳：条件に書いた内訳は等確率。灰の中で役がどう並ぶかも等確率。</li>
<li>村：公開情報（吊り・噛み・GJ・占い結果・霊能結果・狩人CO）が同じなら、どの内訳でも同じ手を打つ。吊り先は村が話し合いで決める（人外の票では覆らない扱い）。GJの翌朝に潜伏狩人がCOするかも村の手。</li>
<li>人外：狼と狂人はお互いを知っているものとし、公開情報と自分たちの噛み先から村勝率が一番低くなる手を選ぶ（噛み先・偽の占い結果・偽の霊能結果・灰の狼の対抗狩人CO）。狩人や本物の占い師が誰かは知らない。</li>
<li>本物の占い師は毎晩まだ占っていない灰からランダムに占う（噛まれたら結果なし）。霊能者は前日に吊った人の色を出す。狩人は 占いCO者 ＞ 霊能CO者 ＞ 確定白 ＞ ほかの人 の順で護衛（同順位はランダム、連続護衛の制限なし）。</li>
<li>決着：狼全滅で村勝ち、狼が生存者の半数以上で狼勝ち。狂人が生きていて生存5人以上なら、人外が過半数で狼勝ち、同数なら決選で半々（PP）。</li>
<li>解き方：村と人外がそれぞれ見えている情報だけで手を決めるゲームを線形計画で解き、分数で検算している。乱数やシミュレーションは使っていない。</li>
</ul>''')
    return page('トップページ', ''.join(s), None, '10a狩の5人日の盤面ごとの村勝率・最善進行・導出')

open(os.path.join(OUT, 'index.html'), 'w').write(index_page())
import glob
for f in glob.glob(os.path.join(OUT, 'p5-*.html')) + glob.glob(os.path.join(OUT, 's*-*.html')): os.remove(f)
for b in D: open(os.path.join(OUT, b['id'] + '.html'), 'w').write(board_page(b))
print(len(D) + 1, 'pages')
