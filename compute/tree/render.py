# cache/（eng/eng_build.py の出力）から wiki ふうの盤面ページ（pos/）を作る
import json, os, sys, glob, html, datetime, re
from fractions import Fraction as F
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'eng'))
import build10a_site as B1

CACHE, ROOT = sys.argv[1], sys.argv[2]
TODAY = datetime.date.today().isoformat()
TREEURL = 'https://leonmfvo.github.io/werewolf-tree-10a/tree.html?t='
def ab(t):
    t = re.sub(r'占い(CO者)?([123])', lambda m: '占' + 'abc'[int(m.group(2)) - 1], t)
    return re.sub(r'霊能(CO者)?([123])', lambda m: '霊' + 'abc'[int(m.group(2)) - 1], t)
e = lambda t: html.escape(ab(str(t)))
fv = lambda s: F(s)
pct = lambda x: f'{float(F(x)) * 100:.1f}%'
def frac(s): return f'（{s}）' if '/' in s and len(s) <= 11 else ''

R = [json.load(open(f)) for f in glob.glob(os.path.join(CACHE, 'b*.json'))]
BYKEY = {(r['n'], r['lab'], r['note']): r for r in R}
DAYS = sorted({r['n'] for r in R}, reverse=True)
def title(r): return r['lab'] + (f'（{r["note"]}）' if r['note'] else '')
def gname(g): return g['truth'] + (f'、{g["wolves"]}' if g['wolves'] else '') if g['truth'] else (g['wolves'] or '')

def anchor(r, g=None, o=None):
    if g is None: return ''
    gi = r['groups'].index(g) + 1
    return f'#g{gi}-{g["opts"].index(o) + 1}' if o else f'#g{gi}-1'

def avg_of(r):
    tw = sum(g['w'] for g in r['groups'])
    return sum(g['w'] * sum(float(fv(o['v'])) for o in g['opts']) / len(g['opts']) for g in r['groups']) / tw if tw else 0

def target(t, v):
    if t is None: return '村勝ち' if fv(v) == 1 else '狼勝ち' if fv(v) == 0 else pct(v)
    pm, ph = fv(t['pm']), {k: fv(x) for k, x in t['ph'].items()}
    st = [f'{t["w"]}狼']
    if pm == 1: st[0] += '1狂'
    st.append('生存')
    if ph['hide'] == 1: st.append('・灰に狩')
    elif ph['co'] == 1: st.append('・狩CO済み')
    s = ''.join(st)
    unk = []
    if 0 < pm < 1: unk.append(f'狂人生存{pct(pm)}')
    if 0 < ph['hide'] < 1: unk.append(f'灰に狩{pct(ph["hide"])}')
    if 0 < ph['co'] < 1: unk.append(f'狩CO済み{pct(ph["co"])}')
    if unk: s += '（' + '・'.join(unk) + '）'
    name = f'{t["n"]}人日 {e(t["lab"])}' + (f'（{e(t["note"])}）' if t['note'] else '')
    r2 = BYKEY.get((t['n'], t['lab'], t['note']))
    href = None
    if r2:
        g2 = next((g for g in r2['groups'] if g['truth'] == t['truth'] and g['wolves'] == t['wolves']), None)
        o2 = None
        if g2 and not unk:
            o2 = next((o for o in g2['opts'] if o['name'].split('（')[0] == s), None)
        href = f'{r2["id"]}.html{anchor(r2, g2, o2)}'
    cond = '、'.join(x for x in (s, t['truth'], t['wolves']) if x)
    body = f'{name}［{e(cond)}］'
    return (f'<a href="{href}">{body}</a>' if href else body) + f' → {pct(v)}'

def choices_html(o):
    out = []; seen = set()
    for c in o['choices']:
        k = (c['who'], c['t'], tuple(a[0] for a in c['alts']))
        if k in seen or len(c['alts']) < 2: continue
        seen.add(k)
        alts = sorted(c['alts'], key=lambda a: -fv(a[1]) if c['who'] == 'v' else fv(a[1]))
        bi = c['alts'][c['best']][0]
        items = '、'.join((f'<b>{e(B1.short(a[0]))}→{pct(a[1])}</b>' if a[0] == bi else f'{e(B1.short(a[0]))}→{pct(a[1])}') for a in alts[:6])
        out.append(f'<p class="alt">{"村" if c["who"] == "v" else "人外"}の選択：{items}</p>')
        if len(seen) >= 4: break
    return ''.join(out)

def patterns_html(o):
    """帰着先を、行き着く村勝率ごとの「パターン」にまとめる（wiki の「1/4になるパターン」と同じ）"""
    pat = {}
    for s_ in o['succ']:
        v = fv(s_['v']); pat.setdefault(v, []).append(s_)
    out = []
    for v in sorted(pat, reverse=True):
        L = sorted(pat[v], key=lambda x: -fv(x['p'])); tp = sum(fv(x['p']) for x in L)
        if all(x['tgt'] is None for x in L):
            head = '村勝ちになるパターン' if v == 1 else '狼勝ちになるパターン' if v == 0 else f'{pct(v)}で決着するパターン'
        else: head = f'{pct(v)}の盤面に進むパターン'
        out.append(f'<h4>{head}（{pct(tp)}）</h4><ul class="arrow">')
        for x in L[:8]:
            labs = ' → '.join(B1.short(y) for y in x['labs'][1:] if y) or '（そのまま）'
            tail = '' if x['tgt'] is None else ' → ' + target(x['tgt'], x['v'])
            out.append(f'<li>{pct(x["p"])}：{e(labs)}{tail}</li>')
        if len(L) > 8: out.append(f'<li class="sm">ほか {len(L) - 8} 通り</li>')
        out.append('</ul>')
    terms = ' + '.join(f'{pct(sum(fv(x["p"]) for x in pat[v]))}×{pct(v)}' for v in sorted(pat, reverse=True))
    tot = sum(fv(x['p']) * fv(x['v']) for x in o['succ'])
    out.append(f'<p class="eq">P = {terms} = {pct(tot)}</p>')
    return ''.join(out)

def board_page(r):
    from collections import Counter
    # 見出しが同じで値も同じ（進行だけ違う）内訳はまとめる
    keep, seen = [], set()
    for g in r['groups']:
        sig = (gname(g), tuple((o['name'], o['v']) for o in g['opts']))
        if sig in seen: continue
        seen.add(sig); keep.append(g)
    r['groups'] = keep
    cnt = Counter(gname(g) for g in r['groups'])
    for g in r['groups']:
        g['_t'] = (gname(g) or 'CO者なし') + (f'（進行：{g["policy"]}）' if cnt[gname(g)] > 1 else '')
    # 生存状況（1w1k生存・灰に狩 など）を見出しにする
    sits = []
    for g in r['groups']:
        for o in g['opts']:
            if o['name'] not in sits: sits.append(o['name'])
    order = lambda n: (int(n[0]), '1狂' not in n, '灰に狩' not in n, '狩CO' not in n, n)
    sits.sort(key=order)
    s = [f'<h1 class="pt">{e(r["lab"])}<span class="day">{r["n"]}人日</span></h1>']
    if r['note']: s.append(f'<p class="cond">{e(r["note"])}</p>')
    s.append(LEGEND)
    s.append('<h2>まとめ</h2><ul class="arrow">')
    for si, sn in enumerate(sits, 1):
        vals = [(g, o) for g in r['groups'] for o in g['opts'] if o['name'] == sn]
        vs = sorted({fv(o['v']) for g, o in vals})
        rng = pct(vs[0]) if len(vs) == 1 else f'{pct(vs[0])}〜{pct(vs[-1])}'
        s.append(f'<li><a href="#s{si}">{e(sn)}</a> → {rng}</li>')
    s.append('</ul>')
    for si, sn in enumerate(sits, 1):
        vals = [(g, o) for g in r['groups'] for o in g['opts'] if o['name'] == sn]
        s.append(f'<h2 id="s{si}">{e(sn)}</h2>')
        s.append('<ul class="arrow">' + ''.join(f'<li>{e(g["_t"])} → <b>{pct(o["v"])}</b>{frac(o["v"])}</li>' for g, o in vals) + '</ul>')
        for g, o in vals:
            gi = r['groups'].index(g) + 1; oi = g['opts'].index(o) + 1
            s.append(f'<h3 id="g{gi}-{oi}">{e(g["_t"])} → {pct(o["v"])}</h3>')
            s.append(f'<p class="sm">進行：{e(g["policy"])}　<a href="{TREEURL}{e(g["tree"])}">分岐ツリー</a></p>')
            s.append(choices_html(o))
            s.append(patterns_html(o))
    return page(f'{r["n"]}人日 {title(r)}', ''.join(s), r['id'])

LEGEND = ('<div class="legend sm"><b>記号</b>　占a・占b＝占いCO者（a・b で区別）、白a＝占aの○、黒a＝占aの●、白ab＝占aと占bの両方から○。'
          '◎＝村が<b>真置き</b>している占い師と、その占い師の結果。✕＝<b>破綻</b>した（偽と確定した）占い師と、その占い師の結果（白b✕ は偽の占い師の○なので、囲いの可能性がある）。'
          '確白＝人間確定。GJの翌朝に狩人がCOして護衛先を申告すると、その狩人と、護衛されていた灰の人が人間確定になる（このときは狩人はもうCO済みなので「灰に狩」はない）。'
          '狩＝狩人CO者（狼が対抗COして2人いる）。1狼1狂生存＝狼1人と狂人が生きている。</div>')

def menu(cur):
    out = ['<div class="side"><div class="mb"><div class="mh">メニュー</div><a href="index.html">トップページ</a><a href="index.html#rules">前提</a><a href="https://leonmfvo.github.io/werewolf-tree-10a/">分岐サイト</a><a href="../index.html">終盤表</a></div>']
    for n in DAYS:
        L = sorted([x for x in R if x['n'] == n], key=lambda x: x['id'])
        op = ' open' if any(x['id'] == cur for x in L) else ''
        out.append(f'<details class="mb"{op}><summary class="mh">{n}人日（{len(L)}）</summary><ul>')
        for x in L:
            c = ' class="cur"' if x['id'] == cur else ''
            out.append(f'<li><a href="{x["id"]}.html"{c}>{e(x["lab"])}{"<span>" + e(x["note"]) + "</span>" if x["note"] else ""}</a></li>')
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
<footer class="foot">10a狩（占い・霊能・狩人・狼2・狂人・村人4）の盤面ごとの村勝率。規則と計算は<a href="https://leonmfvo.github.io/werewolf-tree-10a/">分岐サイト</a>と同じ。</footer>
</body>
</html>
'''

def index_page():
    s = ['<h1 class="pt">10a狩 盤面別勝率</h1>',
         '<p>盤面（生きている人の見た目）を選ぶと、内訳と<b>人外が何人残っているか（1狼1狂生存 など）・狩人が灰に残っているか</b>ごとに、村勝率と、次の昼にどの盤面へ帰着するかが出ます。それまでに誰が死んだかは載せません。</p>',
         LEGEND]
    for n in DAYS:
        L = sorted([x for x in R if x['n'] == n], key=lambda x: x['id'])
        s.append(f'<h2>{n}人日</h2><ul>')
        for x in L:
            s.append(f'<li><a href="{x["id"]}.html">{e(x["lab"])}</a>{" <span class=sm>" + e(x["note"]) + "</span>" if x["note"] else ""}</li>')
        s.append('</ul>')
    s.append('''<h2 id="rules">前提</h2><ul>
<li>規則と計算は<a href="https://leonmfvo.github.io/werewolf-tree-10a/">分岐サイト</a>と同じエンジンです（吊りは指定役か自由投票、狼は見え方の区分で噛む、狂人は狼と示し合わせる、GJの朝は狩人がCOするかを村が選ぶ、など）。村の進行は、分岐サイトでその内訳に使っている進行です。</li>
<li>条件（内訳・狼の位置・狂人の生死・狩人が灰に潜伏／CO済み／死亡）は、狼も知っているものとして解いています。狩人と狂人が灰の誰かは、狼には分かりません。</li>
<li>帰着先：その進行と人外の最善の手で、次の昼にどの盤面になるか。噛まれたのが狩人かどうかなど、狼にも村にも分からないことは「灰に狩80%」のように確率で書きます。村勝率は帰着先の村勝率の重みつき和です。</li>
<li>載せている盤面：分岐サイトの全分岐ツリーに出てくる昼の盤面のうち、出やすい順に各人数40個まで（内訳の出現率は、狂人の騙り先と狼の騙り方を等確率とした式）。ツリーがない内訳（3-0・3-1の一部・4-0 など）から来る盤面は入っていません。1つの盤面には出やすい内訳・狼の位置を6つまで載せています。</li>
</ul>''')
    return page('トップページ', ''.join(s), None)

OUT = os.path.join(ROOT, 'pos')
for f in glob.glob(os.path.join(OUT, '*.html')): os.remove(f)
open(os.path.join(OUT, 'index.html'), 'w').write(index_page())
for r in R: open(os.path.join(OUT, r['id'] + '.html'), 'w').write(board_page(r))
print(len(R) + 1, 'pages')
