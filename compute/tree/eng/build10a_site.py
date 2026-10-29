# 10a狩人サイト（GitHub Pages 用の静的ファイル）を site10a/ に書き出す。
# 盤面ごとに、内訳ごとの全進行の村勝率と、最善進行の全分岐ツリー（data/trees/*.json）を載せる。
import sys, json, os, shutil, html; sys.setrecursionlimit(1000000)
import re
import e10a, run10a, tree10a, tree10ax

OUT = 'site10a'

def pol_name(key, c):
    sp, mp = key.split('-')
    ns, nm = len(sp), len(mp)
    parts = []
    gtxt = {'plain': '灰はランダムに吊る', 'info': '灰は占いCO者の●を優先して吊る', 'anti': '灰は占いCO者の○を優先して吊る'}
    lack = 'T' not in sp
    if c['sp'] == 'ignore': parts.append(f"占いを見ない（{gtxt[c.get('gp', 'info')]}）")
    elif c['sp'] == 'roller': parts.append(('占いCO者を吊る' if ns == 1 else '占いロラ') + (f"（{gtxt[c.get('gp', 'info')]}）" if lack or c.get('gp') == 'anti' else ''))
    elif ns == 1: parts.append('占いを真置き')
    else:
        parts.append(('占いは●の少ない方を真置き' if c['tp'] == 'white' else '占いを乱数で1人真置き') + ('・他の占いを吊る' if c['sp'] == 'trust' else ''))
        if c.get('gp') == 'anti': parts.append('灰は真置きしていない占いの○を優先して吊る')
    if c.get('hm'): parts.append('霊能CO者を吊る')
    elif nm == 1: parts.append('霊能を真置き')
    elif c['mp'] == 'roller': parts.append('霊ロラ')
    else: parts.append('霊能1人を真置き（乱数）')
    parts.append({'seer': '占い指定', 'medium': '霊指定', 'none': '自由投票'}[c['ds']])
    return '・'.join(parts)

def pol_id(c): return f"{c['sp']}_{c['tp']}_{c.get('gp', 'info')}_{c['mp']}_{int(bool(c.get('hm')))}_{c['ds']}"

def dedupe(key, rows):
    """盤面で意味のない違い（占い1人の tp など）をまとめる"""
    seen = {}; out = []
    # 村勝率が同じなら、単純な進行（乱数で真置き・灰は●優先・霊能CO者を吊らない）を先に出す
    simple = lambda x: (x.get('tp') == 'white', x.get('gp', 'info') != 'info', bool(x.get('hm')))
    for r in sorted(rows, key=lambda x: (-round(x['v'], 9), simple(x))):
        nm = pol_name(key, r)
        if nm in seen: continue
        # 「●の少ない方を真置き」は、同じ進行の「乱数で真置き」と全内訳で村勝率が完全に一致した（初日に●が出ないので、
        # 2日目の真置きの時点では誰も●を出していない）。表には載せない
        if r.get('tp') == 'white': continue
        seen[nm] = 1; out.append(dict(r, name=nm))
    return out

CHUNK = 20000

# ツリーのラベルを試合中に読みやすい短い形にする（'／' で区切った各部分ごと）
SHORT = [
    (r'^霊能の結果：前日に吊った人は(○|●)$', r'霊結果\1'),
    (r'^霊能(\d)の結果：(○|●)$', r'霊\1結果\2'),
    (r'^(占い\d?|占いCO者\d?)（狼）の結果：(.+)に(○|●)$', r'\1(狼) \2に\3'),
    (r'^(占い\d?)の結果：噛まれた人を占っていた$', r'\1 噛まれた人を占っていた'),
    (r'^(占い\d?)の結果：(.+)に(○|●)$', r'\1 \2に\3'),
    (r'^(占い\d)（狼）は(.+)に(○|●)$', r'\1(狼)は\2に\3'),
    (r'^偽霊能は(○|●)を出す$', r'偽霊\1'),
    (r'^狂人の占い結果は(○|●)$', r'狂人\1'),
    (r'^噛み失敗（GJ）$', 'GJ'),
    (r'^初日犠牲者を噛む$', '初日犠牲者'),
    (r'^(.+)が噛まれて死亡$', r'噛み：\1'),
    (r'^(.+)を噛む$', r'噛み先：\1'),
    (r'^(.+)が破綻（霊能結果と矛盾）$', r'\1破綻'),
    (r'^霊能CO者が破綻（信用占い師と矛盾）$', '霊能CO者破綻'),
    (r'^噛まれた(.+)を真とみなす$', r'\1を真に乗り換え'),
    (r'^人外の選択（夜）$', '人外の選択'),
    (r'^夜が明ける$', '朝'),
    (r'^信用する占い師を決める$', '真置き'),
    (r'^信用する占い師：(.+)（ランダムに選ぶ）$', r'真置き：\1（乱数）'),
    (r'^信用する占い師：なし$', '真置きなし'),
    (r'^信用する占い師：(.+)$', r'真置き：\1'),
    (r'^(指定|投票|乱数|指定（狼の指定役）)：(.+)を吊る$', r'\1 \2'),
]
def short(x):
    if not x or x.startswith('生存') or x.startswith('狼から見た'): return x
    out = []
    for part in x.split('／'):
        for a, b in SHORT:
            if re.match(a, part): part = re.sub(a, b, part); break
        out.append(part)
    return '／'.join(out)

def cat_of(nd):
    """背景色の区分：n 夜（人外の選択）/ m 朝（結果）/ d 昼（真置き）/ v 投票・吊り / e 終局"""
    t = nd.get('t') or ''
    if nd['k'] == 'end': return 'e'
    if t in ('人外の選択（夜）', '夜の行動'): return 'n'
    if t == '夜が明ける': return 'm'
    if t.startswith(('吊り', '乱数吊り', 'PP', '狼の指定役', '自由投票', '組織票', '狼が組織票', '吊りの選び直し')): return 'v'
    return 'n' if nd.get('ph') == 'night' else 'd'

def fr(x):
    """分数の文字列（整数なら分母なし）"""
    return f'{x.numerator}' if x.denominator == 1 else f'{x.numerator}/{x.denominator}'

def export_tree(key, c, mm, tid, meta):
    """ツリーを CHUNK 局面ずつのファイルに分けて書き出す（開いた枝の分だけ読み込めるように）"""
    T, root, v = tree10ax.build10(key, {**run10a.BASE, **c, 'mm': mm})   # 分数（厳密な値）で作る
    assert T.bad == 0, (key, c, T.bad)
    d = f'{OUT}/data/trees/{tid}'
    os.makedirs(d)
    n = len(T.nodes)
    for base in range(0, n, CHUNK):
        strs = {}; S = []
        def si(x):
            x = short(x or '')
            if x not in strs: strs[x] = len(S); S.append(x)
            return strs[x]
        rows = []
        for nd in T.nodes[base:base + CHUNK]:
            # 子：[出現率, 出現率の分数, ラベル, 子の番号, 種類, 子の村勝率, 村勝率の分数]
            ch = [[None if p is None else round(float(p), 6), None if p is None else si(fr(p)), si(lab), cid, kind[0],
                   round(float(T.nodes[cid]['v']), 6), si(fr(T.nodes[cid]['v']))] for p, lab, cid, kind in nd.get('c', [])]
            # 局面：[種類, 区分, 夜番号, 村勝率, 村勝率の分数, 見出し, 公開情報, 狼視点, 最善の子, 子]
            rows.append([nd['k'][0], cat_of(nd), nd.get('d', -1), round(float(nd['v']), 6), si(fr(nd['v'])), si(nd.get('t')), si(nd.get('pub')), si(nd.get('hid')), nd.get('best', -1), ch])
        json.dump(dict(strs=S, nodes=rows), open(f'{d}/c{base // CHUNK}.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    sy = sorted(([k[0], k[1], k[2], float(p)] for k, p in tree10ax.reach_symbols(T, root).items() if p >= 0.005), key=lambda x: (-x[2], -x[1], x[0]))
    meta = dict(meta, sym=sy)
    meta = dict(meta, frac=[v.numerator, v.denominator])
    json.dump(dict(root=root, v=float(v), n=n, chunk=CHUNK, meta=meta), open(f'{d}/meta.json', 'w'), ensure_ascii=False)
    return n, sy, [v.numerator, v.denominator]

def main():
    if os.path.isdir(OUT): shutil.rmtree(OUT)
    shutil.copytree('site10a_static', OUT)
    os.makedirs(f'{OUT}/data/trees')
    boards = []
    for b, keys in e10a.BOARDS.items():
        bk = []
        for key in keys:
            if not os.path.exists(f'r10a_{key}.json'): print('skip', key); continue
            rows = dedupe(key, json.load(open(f'r10a_{key}.json')))
            best = rows[0]
            tid = f'{key}__{pol_id(best)}'
            n, sy, frac = export_tree(key, {k: best[k] for k in ('sp', 'tp', 'gp', 'mp', 'hm', 'ds') if k in best}, best['mm'], tid,
                            dict(board=b, key=key, label=e10a.label(key), policy=best['name'], v=best['v']))
            print(b, key, best['name'], round(best['v'], 4), 'nodes', n, flush=True)
            bk.append(dict(key=key, label=e10a.label(key), tree=tid, nodes=n, sym=sy, frac=frac,
                           rows=[dict(name=r['name'], v=r['v']) for r in rows]))
        if bk: boards.append(dict(board=b, keys=bk))
    json.dump(boards, open(f'{OUT}/data/summary.json', 'w'), ensure_ascii=False, indent=1)
    open(f'{OUT}/index.html', 'w').write(index_html(boards))
    open(f'{OUT}/.nojekyll', 'w').write('')
    os.remove(f'{OUT}/index.tpl.html')

E_ = html.escape

def frac_html(v, fr):
    """村勝率を小数（%）で、厳密な分数をかっこ書きで"""
    if not fr: return pct(v)
    num = f'{fr[0]}/{fr[1]}' if fr[1] != 1 else f'{fr[0]}'
    return f'<span class="frac">{pct(v)}</span><span class="muted">（{num}）</span>'

def sym_html(v, sy, fr=None):
    """完全ランダムでの村勝率 + 係数・記号（係数はその場面に来る確率）"""
    terms = ' '.join(f'<span class="sy">+ {p:.2f}·{t}<sub>{g}:{n}</sub></span>' for t, g, n, p in sy)
    # 畳んだ表示：種類ごとに係数を足したもの（その種類の場面が起こる回数の期待値）
    tot = {}
    for t, g, n, p in sy: tot[t] = tot.get(t, 0) + p
    short = ' '.join(f'<span class="sy">+ {tot[t]:.2f}·{t}</span>' for t in ('D', 'A') if t in tot)
    if not sy: return f'<span class="base">{frac_html(v, fr)}</span>'
    return f'<span class="base">{frac_html(v, fr)}</span> <details class="symd"><summary>{short}</summary>{terms}</details>'

def pct(v): return f'{v * 100:.1f}%'

def index_html(boards):
    summ = []
    for b in boards:
        for k in b['keys']:
            r = k['rows'][0]
            lk = e10a.lacking(k['key'])
            summ.append(f"<tr><td>{b['board']}</td><td>{E_(k['label'])}{f'<span class=\"lbl\">{lk}</span>' if lk else ''}</td><td>{E_(r['name'])}</td><td class=\"n\">{frac_html(r['v'], k.get('frac'))}</td><td class=\"syms\">{sym_html(r['v'], k['sym'])}</td><td><a href=\"tree.html?t={k['tree']}\">ツリー</a> <span class=\"muted\">{k['nodes']:,}局面</span></td></tr>")
    secs = []
    for b in boards:
        boxes = []
        for k in b['keys']:
            rows = []
            for i, r in enumerate(k['rows']):
                tag = '<span class="lbl good">最善</span>' if i == 0 else ''
                rows.append(f"<tr{' class=\"best\"' if i == 0 else ''}><td>{E_(r['name'])}{tag}</td><td class=\"n\">{pct(r['v'])}</td></tr>")
            lk = e10a.lacking(k['key'])
            boxes.append(f"""<div class="box"><div class="hd">{E_(k['label'])}{f'<span class="lbl">{lk}</span>' if lk else ''}<span class="lbl">最善 {frac_html(k['rows'][0]['v'], k.get('frac'))}</span><a class="btn" style="margin-left:auto" href="tree.html?t={k['tree']}">最善進行のツリー</a></div>
<div class="bd symrow"><span class="muted">最善進行の表記：</span>{sym_html(k['rows'][0]['v'], k['sym'], k.get('frac'))}</div>
<div class="bd"><div class="tbl"><table><thead><tr><th>進行</th><th style="text-align:right">村勝率</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></div></div>""")
        secs.append(f'<h2 id="b{b["board"]}">{b["board"]}</h2>' + NOTES.get(b['board'], '') + ''.join(boxes))
    return TEMPLATE.replace('{{SUMMARY}}', ''.join(summ)).replace('{{SECTIONS}}', ''.join(secs))

NOTES = {
    '2-1': '<p class="muted">真狼-真で「占いを真置きして、もう1人の占いは残す」進行は0%です。真置きしなかった占いが狼でも最後まで吊らないので、狼が1人残り続けて必ず負けます。</p>',
    '3-1': '<p class="muted">狼が2人とも出ている内訳（真狼狼-真など）では、灰に狼がいません。</p>',
}

# 第1版のページの雛形（第2版の build10b_site は使わない。無ければ読まない）
TEMPLATE = open('site10a_static/index.tpl.html').read() if os.path.exists('site10a_static/index.tpl.html') else ''

if __name__ == '__main__':
    main()

def add_fractions():
    """x10a_<key>.json（分数で求めた最善進行の村勝率）を summary とツリーの meta に入れ、index.html を書き直す"""
    boards = json.load(open(f'{OUT}/data/summary.json'))
    for b in boards:
        for k in b['keys']:
            x = json.load(open(f'x10a_{k["key"]}.json'))
            assert abs(x['v'] - k['rows'][0]['v']) < 1e-9, k['key']
            k['frac'] = [x['num'], x['den']]
            mp = f'{OUT}/data/trees/{k["tree"]}/meta.json'
            m = json.load(open(mp)); m['meta']['frac'] = k['frac']
            json.dump(m, open(mp, 'w'), ensure_ascii=False)
    json.dump(boards, open(f'{OUT}/data/summary.json', 'w'), ensure_ascii=False, indent=1)
    open(f'{OUT}/index.html', 'w').write(index_html(boards))
