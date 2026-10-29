# 分岐サイトの昼の局面（extract.py の出力）から、wiki ふうの盤面ページ（pos/）を作る。
# 盤面＝生存人数と見た目（占a,占b,白a,…,灰）と公開情報（死亡・真置き）。ページの中を内訳・狼の位置・狂人と狩人の生存確率で分け、
# 次の昼にどの盤面へ帰着するかを確率つきで載せる（村勝率＝帰着先の村勝率の重みつき和）。
import json, os, sys, html, glob, datetime
from collections import defaultdict
from notation import parse

ENTS, ROOT = sys.argv[1], sys.argv[2]
TOP = int(sys.argv[3]) if len(sys.argv) > 3 else 40
TREEURL = 'https://leonmfvo.github.io/werewolf-tree-10a/tree.html?t='
E = json.load(open(ENTS))
import re as _re
def _ab(t):
    t = _re.sub(r'占い([123])', lambda m: '占' + 'abc'[int(m.group(1)) - 1], t)
    return _re.sub(r'霊能([123])', lambda m: '霊' + 'abc'[int(m.group(1)) - 1], t)
e = lambda t: html.escape(_ab(str(t)))
TODAY = datetime.date.today().isoformat()
pct = lambda x: f'{x * 100:.1f}%'

def frac(vf):
    return vf if vf and '/' in vf and len(vf) <= 13 else None

# ---- まとめる
pages = {}          # 盤面キー → dict
loc = {}            # (tree, node) → (盤面キー, 場合キー)
for x in E:
    n, lab, pubc, truth, wolves, hidden = parse(x['pub'], x['key'], x['hid'])
    pk = (n, lab, tuple(pubc))
    sk = (truth, tuple(wolves), hidden, round(x['v'], 9))
    pg = pages.setdefault(pk, dict(n=n, lab=lab, pubc=pubc, w=0.0, secs={}))
    pg['w'] += x['w']
    s = pg['secs'].setdefault(sk, dict(truth=truth, wolves=wolves, hidden=hidden, v=x['v'], vf=x['vf'], w=0.0, ents=[]))
    s['w'] += x['w']; s['ents'].append(x)
    loc[(x['tree'], x['node'])] = (pk, sk)

byn = defaultdict(list)
for pk, pg in pages.items(): byn[pg['n']].append(pg)
keep = {}
for n, L in byn.items():
    L.sort(key=lambda p: -p['w'])
    for i, pg in enumerate(L[:TOP]):
        pg['id'] = f't{n}-{i + 1:02d}'; keep[(pg['n'], pg['lab'], tuple(pg['pubc']))] = pg
DAYS = sorted({pg['n'] for pg in keep.values()}, reverse=True)

def title(pg):
    return pg['lab'] + (f'（{"、".join(pg["pubc"])}）' if pg['pubc'] else '')

def sec_name(s):
    parts = [s['truth']] + (s['wolves'] or ['狼の位置不明']) + ([s['hidden']] if s['hidden'] else [])
    return '、'.join(parts)

def target_html(t, v):
    if t is None: return ('村勝ち' if v >= 0.5 else '狼勝ち') if v in (0, 1) else pct(v)
    pk, sk = loc[tuple(t)]
    pg = pages[pk]; s = pg['secs'][sk]
    name = f'{pg["n"]}人日 {e(title(pg))}'
    if pk in keep:
        si = sorted(pg['secs'].values(), key=lambda z: -z['w']).index(s) + 1
        return f'<a href="{pg["id"]}.html#c{si}">{name}</a>（{pct(s["v"])}）'
    return f'{name}（{pct(s["v"])}）'

def section(s, si):
    out = [f'<h3 id="c{si}">{e(sec_name(s))} → {pct(s["v"])}</h3>']
    vf = frac(s['vf'])
    out.append(f'<p class="big">村勝率 {pct(s["v"])}{"（" + vf + "）" if vf else ""}</p>')
    x0 = max(s['ents'], key=lambda x: x['w'])
    pols = sorted({x['policy'] for x in s['ents']})
    out.append(f'<p class="sm">内訳 {e(x0["key"])}（{e(x0["board"])}）の進行：{e("／".join(pols))}　<a href="{TREEURL}{e(x0["tree"])}">分岐ツリー</a></p>')
    # 村と人外の選択（最初の昼から次の昼まで）
    seen = set()
    for c in x0['choices']:
        if c['p'] < 1e-9: continue
        k = (c['who'], c['t'], tuple(a[0] for a in c['alts']))
        if k in seen: continue
        seen.add(k)
        who = '村の選択' if c['who'] == 'v' else '人外の選択'
        alts = sorted(c['alts'], key=lambda a: -a[1] if c['who'] == 'v' else a[1])
        bi = c['alts'][c['best']][0] if c['best'] is not None and c['best'] >= 0 else alts[0][0]
        items = '、'.join((f'<b>{e(a[0])}→{pct(a[1])}</b>' if a[0] == bi else f'{e(a[0])}→{pct(a[1])}') for a in alts[:6])
        pre = f'（{e(" → ".join(c["labs"]))}）' if c['labs'] else ''
        out.append(f'<p class="alt">{who}{pre}：{items}</p>')
        if len(seen) >= 6: break
    # 帰着先（重みつきでまとめる）
    agg = defaultdict(float); tw = sum(x['w'] for x in s['ents'])
    for x in s['ents']:
        for p, labs, t, v in x['next']:
            agg[(' → '.join(labs), tuple(t) if t else None, v if t is None else None)] += p * x['w'] / tw
    rows = sorted(agg.items(), key=lambda kv: -kv[1])
    terms = []
    out.append('<p class="sub">帰着先（次の昼）</p><ul class="arrow">')
    for (labs, t, v), p in rows[:14]:
        out.append(f'<li>{pct(p)}：{e(labs) or "（そのまま）"} → {target_html(t, v)}</li>')
    if len(rows) > 14:
        rest = sum(p for _, p in rows[14:])
        out.append(f'<li class="sm">ほか {len(rows) - 14} 通り（合わせて {pct(rest)}）</li>')
    out.append('</ul>')
    tot = sum(p * (pages[loc[t][0]]['secs'][loc[t][1]]['v'] if t else v) for (labs, t, v), p in rows)
    out.append(f'<p class="eq">P = Σ（確率 × 帰着先の村勝率）= {pct(tot)}</p>')
    return ''.join(out)

def board_page(pg):
    secs = sorted(pg['secs'].values(), key=lambda z: -z['w'])
    s = [f'<h1 class="pt">{e(pg["lab"])}<span class="day">{pg["n"]}人日</span></h1>']
    if pg['pubc']: s.append(f'<p class="cond">公開情報：{e("、".join(pg["pubc"]))}</p>')
    s.append('<h2>まとめ</h2><p class="sm">内訳ごとの村勝率。割合はこの盤面になったときにその内訳である割合（分岐サイトの最善進行での到達確率から）。</p><ul class="arrow">')
    for i, z in enumerate(secs[:30]):
        s.append(f'<li><a href="#c{i + 1}">{e(sec_name(z))}</a> → {pct(z["v"])}<span class="sm">（{pct(z["w"] / pg["w"])}）</span></li>')
    if len(secs) > 30: s.append(f'<li class="sm">ほか {len(secs) - 30} 通り</li>')
    avg = sum(z['w'] * z['v'] for z in secs) / pg['w']
    s.append(f'<li><b>平均 → {pct(avg)}</b></li></ul>')
    s.append('<h2>内訳ごと</h2>')
    for i, z in enumerate(secs[:30]): s.append(section(z, i + 1))
    return page(f'{pg["n"]}人日 {title(pg)}', ''.join(s), pg['id'])

def menu(cur):
    out = ['<div class="side"><div class="mb"><div class="mh">メニュー</div><a href="index.html">トップページ</a><a href="index.html#rules">前提</a><a href="https://leonmfvo.github.io/werewolf-tree-10a/">分岐サイト</a><a href="../index.html">終盤表</a></div>']
    for n in DAYS:
        L = sorted([p for p in keep.values() if p['n'] == n], key=lambda p: -p['w'])
        open_ = any(p['id'] == cur for p in L)
        out.append(f'<details class="mb"{" open" if open_ else ""}><summary class="mh">{n}人日（{len(L)}）</summary><ul>')
        for p in L:
            c = ' class="cur"' if p['id'] == cur else ''
            out.append(f'<li><a href="{p["id"]}.html"{c}>{e(p["lab"])}{"<span>" + e("、".join(p["pubc"])) + "</span>" if p["pubc"] else ""}</a></li>')
        out.append('</ul></details>')
    out.append('</div>')
    return ''.join(out)

def page(t, body, cur):
    return f'''<!doctype html>
<html lang="ja" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<title>{e(t)} - 10a狩 盤面別勝率</title>
<link rel="stylesheet" href="wiki.css">
</head>
<body>
<header class="site"><a href="index.html">10a狩 盤面別勝率</a></header>
<div class="layout">
<main class="main"><article>{body}<div class="upd">最終更新：{TODAY}</div></article><div class="totop"><a href="#">ページトップ</a></div></main>
{menu(cur)}
</div>
<footer class="foot">10a狩（占い・霊能・狩人・狼2・狂人・村人4）の盤面ごとの村勝率。値は<a href="https://leonmfvo.github.io/werewolf-tree-10a/">分岐サイト</a>の計算から。</footer>
</body>
</html>
'''

def index_page():
    s = ['<h1 class="pt">10a狩 盤面別勝率</h1>',
         '<p>分岐サイト（全分岐ツリー）に出てくる昼の盤面のうち、出やすいものを人数ごとに上から並べています。盤面を開くと、内訳ごとの村勝率と、次の昼にどの盤面へ帰着するか（確率つき）が出ます。村勝率は帰着先の村勝率の重みつき和です。</p>',
         '<p class="sm">表記：占a・占b・占c＝占いCO者（分岐サイトの占い1・2・3）、霊・霊a・霊b＝霊能CO者、狩＝狩人CO者、白a＝占aの○、白ab＝占aと占bの○、黒a＝占aの●、確白＝人間確定、灰＝グレー。占いCO者が1人なら 占・白・黒。（ ）は公開情報（死亡・真置き）。内訳は 真＝本物、狂＝狂人、狼＝狼 で、占ab＝真狂 なら占aが本物・占bが狂人。</p>']
    for n in DAYS:
        L = sorted([p for p in keep.values() if p['n'] == n], key=lambda p: -p['w'])
        tot = sum(p['w'] for p in byn[n])
        s.append(f'<h2>{n}人日</h2><table class="bl"><tbody>')
        for p in L:
            avg = sum(z['w'] * z['v'] for z in p['secs'].values()) / p['w']
            s.append(f'<tr><td><a href="{p["id"]}.html">{e(p["lab"])}</a><div class="sm">{e("、".join(p["pubc"]))}</div></td><td class="n">{pct(avg)}</td><td class="n sm">{pct(p["w"] / tot)}</td></tr>')
        s.append('</tbody></table>')
        s.append(f'<p class="sm">右の列はこの人数の盤面の中での出やすさ。分岐サイトに出てくる{n}人日の盤面は全部で {len(byn[n])} 通りで、ここには上位 {len(L)} 個を載せています。</p>')
    s.append('''<h2 id="rules">前提</h2><ul>
<li>値はすべて<a href="https://leonmfvo.github.io/werewolf-tree-10a/">分岐サイト</a>の全分岐ツリーから取っています（同じ規則・同じ計算）。内訳ごとに、その内訳で一番村勝率の高い進行のツリーを使います（ツリーがない内訳は、ある中で一番よい進行）。</li>
<li>規則：吊りは指定役（真置きした占い・霊能など）が決め、指定役がいなければ自由投票。狼は見え方の区分で噛み、狂人は狼と示し合わせて最悪の結果を出す。狩人の護衛・本物の占い先はランダム。詳しくは分岐サイトの「前提」。</li>
<li>出やすさ：内訳の出現率（狂人の騙り先 占い・霊能・潜伏 と狼の騙り方6通りを等確率とした式）× その内訳の最善進行でその盤面に着く確率。</li>
<li>盤面の割合（まとめの（ ））：その盤面になったとき、各内訳・狼の位置である割合。村から見た平均の村勝率はこの割合での平均。</li>
<li>分岐サイトで局面が大きすぎてツリーがない内訳（3-0・3-1の一部・4-0 など）から来る盤面は載っていません。</li>
</ul>''')
    return page('トップページ', ''.join(s), None)

OUT = os.path.join(ROOT, 'pos'); os.makedirs(OUT, exist_ok=True)
for f in glob.glob(os.path.join(OUT, '*.html')): os.remove(f)
open(os.path.join(OUT, 'index.html'), 'w').write(index_page())
for pg in keep.values(): open(os.path.join(OUT, pg['id'] + '.html'), 'w').write(board_page(pg))
print(len(keep) + 1, 'pages', {n: len([p for p in keep.values() if p['n'] == n]) for n in DAYS})
