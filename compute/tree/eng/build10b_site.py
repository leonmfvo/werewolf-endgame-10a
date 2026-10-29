# 10a狩人サイト（第2版）：全54内訳・盤面ごとの共通の進行・出現率の式・均衡・日ごとの進行の流れ。
#   python3 build10b_site.py trees <key>...   内訳ごとに最善進行のツリーを書き出す（並列に回せる）
#   python3 build10b_site.py site             ページを組み立てる（ツリーと均衡の結果を読む）
import sys, json, os, shutil, html, re; sys.setrecursionlimit(1000000)
from fractions import Fraction
import numpy as np
import e10a, run10a, run10b, tree10ax, nash10a
import build10a_site as B1    # ラベルの短縮・区分・分数の関数を使う

OUT = 'site10b'
MAXN = 1500000
TREE_CAP_MB = 20   # これより大きいツリーのファイルは載せない（GitHub Pages の容量 1GB のため）   # これより局面が多いツリーは載せない
TD = f'{OUT}/data/trees'
E_ = html.escape

def pct(v): return f'{v * 100:.1f}%'

def parse(pid):
    sp, gp, mp, hm, ds, *rest = pid.split('|')
    g = next((x for x in rest if x.startswith('g')), None)
    return dict(sp=sp, tp='rand', gp=gp, mp=mp, hm=hm == '1', ds=ds, hg='co2' if 'co2' in rest else None, cw=1 if 'cw' in rest else 0,
                hgm=Fraction(int(g[1:]), 100) if g else None)

def pol_name(board, pid):
    """助詞を省いた短い進行名"""
    c = parse(pid)
    ns, nm = map(int, board.split('-'))
    parts = []
    g = {'info': '', 'infoa': '（全占いの●優先）', 'infos': '（●で止まった後だけ●優先）', 'anti': '（○優先）', 'plain': '（灰ランダム）'}[c['gp']]
    if ns:
        if c['sp'] == 'keep': parts.append('占い真置き' + g)
        elif c['sp'] == 'trust': parts.append('占い真置き・他占い吊り' + g)
        elif c['sp'] == 'roller': parts.append(('占いCO吊り' if ns == 1 else '占いロラ') + g)
        elif c['sp'] == 'rstop': parts.append('占い1●止めロラ' + g)
        else: parts.append('占い無視' + ({'info': '（●優先）'}.get(c['gp'], g)))
    if nm:
        if c['hm']: parts.append('霊能CO吊り')
        elif nm == 1: parts.append('霊能真置き')
        elif c['mp'] == 'roller': parts.append('霊ロラ')
        else: parts.append('霊能1人真置き')
    parts.append({'seer': '占い指定', 'medium': '霊指定', 'none': '自由投票'}[c['ds']])
    if c.get('hg') == 'co2': parts.append('狩人は占いCO護衛')
    if c.get('cw'): parts.append('確定白に指定役引継ぎ')
    if c.get('hgm') is not None: parts.append(f'狩人は指定役を{round(c["hgm"] * 100)}%護衛')
    return '・'.join(parts)

TGT = {'灰': '灰', '占いCO': '占いCO', '霊能CO': '霊能CO', '●': '●', '○': '○'}
def act_text(act):
    how, kinds = act
    t = 'か'.join(TGT.get(k, k) for k in kinds.split('・'))
    return f'{how}で{t}吊り' if how != '自由投票' else f'自由投票で{t}吊り'

def schedule(board, pid, da):
    """日ごとの進行の流れ：2d は真置きなど＋その日の吊り、3d 以降は日ごとに一番多い吊り方（同じなら「以降」でまとめる）"""
    c = parse(pid)
    ns, nm = map(int, board.split('-'))
    start = []
    if ns:
        start.append({'keep': '占い真置き', 'trust': '占い真置き', 'roller': '占いロラ' if ns > 1 else '占いCO吊り', 'rstop': '占い1●止めロラ', 'ignore': '占い無視'}[c['sp']])
    if nm:
        start.append('霊能CO吊り' if c['hm'] else ('霊ロラ' if c['mp'] == 'roller' and nm > 1 else ('霊能真置き' if nm == 1 else '霊能1人真置き')))
    days = sorted(da)
    tops = {}
    for d in days:
        tot = sum(da[d].values())
        if tot < 0.05: continue
        a, p = max(da[d].items(), key=lambda kv: kv[1])
        tops[d] = (act_text(a), float(p / tot))
    if not tops: return '・'.join(start)
    segs = []
    for d in sorted(tops):
        t = tops[d][0]
        if segs and segs[-1][1] == t and segs[-1][0] > 2: segs[-1][2] = d   # 2d は初日の設定と一緒に単独で書く
        else: segs.append([d, t, d])
    out = []
    for i, (a, t, b) in enumerate(segs):
        lab = f'{a}d以降' if (i == len(segs) - 1 and a > 2) else (f'{a}d' if a == b else f'{a}–{b}d')
        out.append(f"{lab} {'・'.join(start) + '・' if a == 2 else ''}{t}")
    return ' → '.join(out)

# ---------------------------------------------------------------- ツリー（内訳ごと・並列）
def best_of(V, key):
    b = e10a.board_of(key)
    pids = [p for p in (run10b.pid(c) for c in run10b.board_candidates(b)) if p in V[key]]
    # 同じ値なら単純な進行（候補の並び順）を優先
    return max(pids, key=lambda p: (round(V[key][p], 9), -pids.index(p)))

def export_one(key, V, MM, pid=None, mdir='tmeta10b'):
    """pid を与えると、その進行のツリーを作る（試合用ガイドの推奨進行）。メタ情報は mdir に書く"""
    b = e10a.board_of(key)
    pid = pid or best_of(V, key)
    os.makedirs(mdir, exist_ok=True)
    mname = f'{key or "_"}__{pid.replace("|", "_")}' if mdir == 'tmeta_guide' else (key or '_')   # ガイド用は進行ごとに別ファイル
    c = parse(pid)
    if '4' in b:   # 4CO はロラで必ず勝つ。ツリーは載せない
        json.dump(dict(board=b, key=key, label=e10a.label(key), policy=pol_name(b, pid), sched='', v=V[key][pid], frac=None, sym=[], tree=None, nodes=None, pid=pid, toolarge=True),
                  open(f'{mdir}/{mname}.json', 'w'), ensure_ascii=False)
        print(key, pid, '4CO: no tree', flush=True)
        return
    T, root, v = tree10ax.build10(key, {**run10a.BASE, **c, 'mm': MM[key][pid]})
    assert abs(float(v) - V[key][pid]) < 1e-9, (key, float(v), V[key][pid])
    tid = f'{key or "_"}__{pid.replace("|", "_")}'
    def summary_meta():
        """ツリーを載せない場合でも、流れ・記号・GJ・人外の手の要約は残す"""
        sy = sorted(([k[0], k[1], k[2], float(p)] for k, p in tree10ax.reach_symbols(T, root).items() if p >= 0.005), key=lambda x: (-x[2], -x[1], x[0]))
        gjr = sorted([d, n, c, float(p)] for (d, n, c), p in tree10ax.reach_gj(T, root).items() if p > 1e-6)
        return dict(board=b, key=key, label=e10a.label(key), policy=pol_name(b, pid), sched=schedule(b, pid, tree10ax.day_actions(T, root)),
                    v=float(v), frac=[v.numerator, v.denominator], sym=sy, gj=gjr, wolf=tree10ax.wolf_plan(T, root), tree=None, nodes=len(T.nodes), pid=pid)
    if tree10ax.PRUNE[0]:   # 要約だけ（選んだ枝だけを作ったので、ツリーとしては載せない）
        json.dump(summary_meta(), open(f'{mdir}/{mname}.json', 'w'), ensure_ascii=False)
        print(key, pid, 'summary only', len(T.nodes), flush=True)
        return
    if T.bad:   # ツリーの局面の値が計算結果と食い違う（ラベルの分け方の問題）。値は正しいのでツリーだけ載せない
        json.dump(dict(summary_meta(), mismatch=T.bad), open(f'{mdir}/{mname}.json', 'w'), ensure_ascii=False)
        print(key, pid, 'tree mismatch', T.bad, flush=True)
        return
    if len(T.nodes) > MAXN:   # 大きすぎるツリーは載せない（容量とブラウザの重さのため）
        json.dump(summary_meta(), open(f'{mdir}/{mname}.json', 'w'), ensure_ascii=False)
        print(key, pid, 'tree too large', len(T.nodes), flush=True)
        return
    d = f'{TD}/{tid}'
    if os.path.isdir(d): shutil.rmtree(d)
    os.makedirs(d)
    n = len(T.nodes)
    for base in range(0, n, B1.CHUNK):
        strs = {}; S = []
        def si(x):
            x = B1.short(x or '')
            if x not in strs: strs[x] = len(S); S.append(x)
            return strs[x]
        rows = []
        for nd in T.nodes[base:base + B1.CHUNK]:
            ch = [[None if p is None else round(float(p), 6), None if p is None else si(B1.fr(p)), si(lab), cid, kind[0],
                   round(float(T.nodes[cid]['v']), 6), si(B1.fr(T.nodes[cid]['v']))] for p, lab, cid, kind in nd.get('c', [])]
            rows.append([nd['k'][0], B1.cat_of(nd), nd.get('d', -1), round(float(nd['v']), 6), si(B1.fr(nd['v'])), si(nd.get('t')), si(nd.get('pub')), si(nd.get('hid')), nd.get('best', -1), ch])
        json.dump(dict(strs=S, nodes=rows), open(f'{d}/c{base // B1.CHUNK}.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    sy = sorted(([k[0], k[1], k[2], float(p)] for k, p in tree10ax.reach_symbols(T, root).items() if p >= 0.005), key=lambda x: (-x[2], -x[1], x[0]))
    sched = schedule(b, pid, tree10ax.day_actions(T, root))
    gjr = sorted([d, n, c, float(p)] for (d, n, c), p in tree10ax.reach_gj(T, root).items() if p > 1e-6)
    wplan = tree10ax.wolf_plan(T, root)
    meta = dict(board=b, key=key, label=e10a.label(key), policy=pol_name(b, pid), sched=sched, v=float(v), frac=[v.numerator, v.denominator], sym=sy, gj=gjr, wolf=wplan)
    json.dump(dict(root=root, v=float(v), n=n, chunk=B1.CHUNK, meta=meta), open(f'{d}/meta.json', 'w'), ensure_ascii=False)
    os.makedirs('tmeta10b', exist_ok=True)
    json.dump(dict(meta, tree=tid, nodes=n, pid=pid), open(f'{mdir}/{mname}.json', 'w'), ensure_ascii=False)
    print(key, pid, round(float(v), 4), n, sched, flush=True)

def load_mm():
    MM = {}
    import glob
    for f in glob.glob('r10b_*.part*of*.json'):
        key = f[len('r10b_'):f.index('.part')]
        for p, (v, mm) in json.load(open(f)).items(): MM.setdefault(key, {})[p] = mm
    return MM

# ---------------------------------------------------------------- ページ
def frac_html(v, fr):
    if not fr: return pct(v)
    num = f'{fr[0]}/{fr[1]}' if fr[1] != 1 else f'{fr[0]}'
    return f'<span class="frac">{pct(v)}</span><span class="fr2">（{num}）</span>'

def sym_html(sy):
    if not sy: return ''
    terms = ' '.join(f'<span class="sy">+ {p:.2f}·{t}<sub>{g}:{n}</sub></span>' for t, g, n, p in sy)
    tot = {}
    for t, g, n, p in sy: tot[t] = tot.get(t, 0) + p
    short = ' '.join(f'<span class="sy">+ {tot[t]:.2f}·{t}</span>' for t in ('D', 'A', 'S', 'G', 'T') if t in tot)
    return f'<details class="symd"><summary>{short}</summary>{terms}</details>'

def mix_text(x, keys):
    return '、'.join(f'{name} {x[k] * 100:.0f}%' for k, name in keys if x[k] > 0.005)

def site():
    V = nash10a.load_values()
    BP = nash10a.board_policies(V)
    empty = [b for b in BP if not BP[b]]
    assert not empty, f'進行が1つも揃っていない盤面がある：{empty}'
    C = nash10a.payoff_tensor(V, BP)
    # まだ計算が終わっていない進行がある盤面（その盤面では、終わった進行だけで比べている）
    pending = {}
    for b in BP:
        full = [run10b.pid(c) for c in run10b.board_candidates(b)]
        if len(BP[b]) < len(full): pending[b] = (len(BP[b]), len(full))
    val_c, x_c, vill_c = nash10a.solve_correlated(C, BP)
    val_i, q_i, w_i = nash10a.solve_independent(C, BP, step=0.05)
    # 細かい格子で詰める（最適の近く）
    best = (val_i, q_i, w_i)
    for ds in np.arange(-0.05, 0.0501, 0.01):
        for dm in np.arange(-0.05, 0.0501, 0.01):
            s = q_i['S'] + ds; m = q_i['M'] + dm; h = 1 - s - m
            if min(s, m, h) < -1e-9: continue
            q = {'S': max(s, 0), 'M': max(m, 0), 'H': max(h, 0)}
            x = {(mad, w): q[mad] * 1 for mad in nash10a.MADS for w in nash10a.WOLF}
            # 狼の分布は同じ線形計画で
            r = nash10a.solve_independent_q(C, BP, q)
            if r[0] < best[0] - 1e-12: best = r
    val_i, q_i, w_i = best
    x_i = {(mad, w): q_i[mad] * w_i[w] for mad in nash10a.MADS for w in nash10a.WOLF}
    tot_i, br_i = nash10a.village_best(C, BP, x_i)
    # 内訳ごとの出現確率（均衡の騙り率で）
    wd = {w: w_i[w] for w in nash10a.WOLF}
    from fractions import Fraction as F
    pk_i = {k: float(nash10a.key_prob(k, F(q_i['S']).limit_denominator(1000), F(q_i['M']).limit_denominator(1000), F(q_i['H']).limit_denominator(1000), {w: F(wd[w]).limit_denominator(1000) for w in wd})) for ks in e10a.BOARDS.values() for k in ks}
    TM = {}
    for k in [k for ks in e10a.BOARDS.values() for k in ks]:
        f = f'tmeta10b/{k or "_"}.json'
        if os.path.exists(f): TM[k] = json.load(open(f))
    # ---- 試合用ガイド
    import guide10b
    G = guide10b.render(V, BP, C, x_i, q_i, w_i, br_i, pk_i, TM, val_i, pol_name)
    # ---- GJ の朝の狩人CO（内訳ごとの最善進行で、その場面に来る確率と、COしたか）
    gj_rows = []
    for k in sorted(TM, key=lambda k: -pk_i.get(k, 0)):
        g = TM[k].get('gj') or []
        if not g: continue
        cells = '　'.join(f'{d}d（{n}人）<b class="{"good" if c == "co" else "muted"}">{"CO" if c == "co" else "潜伏"}</b> {p * 100:.1f}%' for d, n, c, p in g)
        gj_rows.append(f'<tr><td>{e10a.board_of(k)}</td><td>{E_(e10a.label(k))}</td><td class="n">{pk_i.get(k, 0) * 100:.2f}%</td><td>{cells}</td></tr>')
    # ---- 盤面ごとの表
    WN = {(0, 0): '騙りなし', (1, 0): '占い1', (2, 0): '占い2', (0, 1): '霊能1', (0, 2): '霊能2', (1, 1): '占い1・霊能1'}
    summ, secs = [], []
    for b, keys in e10a.BOARDS.items():
        pols = BP[b]
        pb = sum(pk_i[k] for k in keys)
        eqp = br_i.get(b)
        boxes = []
        for k in keys:
            m = TM.get(k)
            vk = V[k]
            bestp = best_of(V, k)
            rows = []
            order = sorted(pols, key=lambda p: -vk[p])
            for p in order:
                tags = ''
                if p == bestp: tags += '<span class="lbl good">この内訳の最善</span>'
                if eqp and p == eqp[0]: tags += '<span class="lbl acc">均衡の進行</span>'
                rows.append(f'<tr{" class=best" if p == bestp else ""}><td>{E_(pol_name(b, p))}{tags}</td><td class="n">{pct(vk[p])}</td></tr>')
            tree = f'<a class="btn" href="tree.html?t={m["tree"]}">ツリー</a>' if m and m.get('tree') else '<span class="muted">ツリーなし</span>'
            head = frac_html(m['v'], m['frac']) if m else pct(vk[bestp])
            boxes.append(f'''<div class="box"><div class="hd"><span>{E_(e10a.label(k))}</span><span class="lbl">出現率 {pk_i[k] * 100:.2f}%</span><span class="lbl">最善 {head}</span><span style="margin-left:auto">{tree}</span></div>
<div class="bd symrow"><div><b>{E_(pol_name(b, bestp))}</b></div>{f'<div class="sched">{E_(m["sched"])}</div>' if m and m.get("sched") else ''}{sym_html(m.get("sym", [])) if m else ''}</div>
<div class="bd"><details><summary class="muted">全進行の村勝率（{len(pols)}通り）</summary><div class="tbl"><table><thead><tr><th>進行</th><th style="text-align:right">村勝率</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></details></div></div>''')
            mm = TM.get(k)
            summ.append(f'<tr><td>{b}</td><td>{E_(e10a.label(k))}</td><td><div>{E_(pol_name(b, bestp))}</div>{f"<div class=sched>{E_(mm['sched'])}</div>" if mm and mm.get('sched') else ""}</td><td class="n">{frac_html(mm["v"], mm["frac"]) if mm else pct(vk[bestp])}</td><td>{f"<a href=tree.html?t={mm['tree']}>ツリー</a>" if mm and mm.get('tree') else ""}</td></tr>')
        eqline = ''
        if eqp and pb > 0:
            eqline = f'<p class="eq">均衡でのこの盤面の進行：<b>{E_(pol_name(b, eqp[0]))}</b>（この盤面になったときの村勝率 {pct(eqp[1] / pb)}、盤面の出現率 {pb * 100:.2f}%）</p>'
        secs.append(f'<h2 id="b{b}">{b}</h2>{eqline}' + ''.join(boxes))
    # ---- 均衡の表
    eq_rows = []
    for b in e10a.BOARDS:
        pb = sum(pk_i[k] for k in e10a.BOARDS[b])
        if b not in br_i or pb < 1e-9: continue
        p, val = br_i[b]
        eq_rows.append(f'<tr><td>{b}</td><td class="n">{pb * 100:.2f}%</td><td>{E_(pol_name(b, p))}</td><td class="n">{pct(val / pb)}</td></tr>')
    vc_rows = []
    for b in e10a.BOARDS:
        if b not in vill_c: continue
        tot = sum(vill_c[b].values())
        vc_rows.append(f'<tr><td>{b}</td><td>' + '<br>'.join(f'{E_(pol_name(b, p))} <span class="muted">{y / tot * 100:.0f}%</span>' for p, y in sorted(vill_c[b].items(), key=lambda kv: -kv[1])) + '</td></tr>')
    xc_text = '、'.join(f"狂人{'占い' if o[0] == 'S' else ('霊能' if o[0] == 'M' else '潜伏')}×狼{WN[o[1]]} {p * 100:.0f}%" for o, p in sorted(x_c.items(), key=lambda kv: -kv[1]) if p > 0.005)
    eq = dict(val_i=val_i, q=q_i, w={WN[w]: w_i[w] for w in nash10a.WOLF}, val_c=val_c, x_c=xc_text)
    # ---- 対話式の計算に渡すデータ
    calc = dict(boards={b: dict(pols=[pol_name(b, p) for p in BP[b]], keys=e10a.BOARDS[b]) for b in e10a.BOARDS},
                V={k: [V[k][p] for p in BP[e10a.board_of(k)]] for ks in e10a.BOARDS.values() for k in ks},
                eq=dict(s=q_i['S'], m=q_i['M'], h=q_i['H'], w=[w_i[w] for w in nash10a.WOLF]))
    os.makedirs(f'{OUT}/data', exist_ok=True)
    json.dump(calc, open(f'{OUT}/data/calc.json', 'w'), ensure_ascii=False)
    json.dump(dict(eq=eq, boards={b: [dict(key=k, best=pol_name(b, best_of(V, k)), v=V[k][best_of(V, k)]) for k in ks] for b, ks in e10a.BOARDS.items()}), open(f'{OUT}/data/summary.json', 'w'), ensure_ascii=False, indent=1)
    tpl = open('site10b_static/index.tpl.html').read()
    WL = [('S', '占いCO'), ('M', '霊能CO'), ('H', '潜伏')]
    rep = {
        '{{GUAR}}': pct(G['guar']), '{{GPICKS}}': G['picks'], '{{GVPAN}}': G['vpan'], '{{GWPAN}}': G['wpan'], '{{CLAIM_M}}': G['claim_m'], '{{CLAIM_W}}': G['claim_w'],
        '{{GJROWS}}': ''.join(gj_rows) or '<tr><td colspan="4" class="muted">（ツリーのある内訳だけ）</td></tr>',
        '{{SUMMARY}}': ''.join(summ), '{{SECTIONS}}': ''.join(secs), '{{EQROWS}}': ''.join(eq_rows), '{{VCROWS}}': ''.join(vc_rows),
        '{{PENDING}}': ('<div class="note"><b>暫定版</b>：次の盤面は、進行の候補の一部（計算に時間のかかる真置き系）がまだ計算中で、終わった候補だけで比べています。終わり次第更新します。' + '、'.join(f'{b}（{n}/{m}）' for b, (n, m) in pending.items()) + '</div>') if pending else '',
        '{{VAL_I}}': pct(val_i), '{{VAL_C}}': pct(val_c), '{{XC}}': E_(xc_text),
        '{{MADMIX}}': '、'.join(f'{n} {q_i[k] * 100:.0f}%' for k, n in WL if q_i[k] > 0.005),
        '{{WOLFMIX}}': '、'.join(f'{WN[w]} {w_i[w] * 100:.0f}%' for w in nash10a.WOLF if w_i[w] > 0.005),
    }
    for a, b_ in rep.items(): tpl = tpl.replace(a, b_)
    # 容量：大きすぎるツリー（TREE_CAP_MB より大きいもの）とどこからも参照されないツリーは載せない。リンクも外す
    import re as _re
    big = os.path.join(os.path.dirname(os.path.abspath(OUT)), 'trees_big'); os.makedirs(big, exist_ok=True)
    refs = set(_re.findall(r'tree\.html\?t=([^"&<>]+)"', tpl))
    def dsize(d): return sum(os.path.getsize(os.path.join(d, f)) for f in os.listdir(d)) / 2**20
    keep = set()
    for t in os.listdir(TD):
        d = os.path.join(TD, t)
        if t in refs and dsize(d) <= TREE_CAP_MB: keep.add(t)
        else: shutil.move(d, os.path.join(big, t)) if not os.path.exists(os.path.join(big, t)) else shutil.rmtree(d)
    for t in refs - keep:
        tpl = tpl.replace(f'<a href="tree.html?t={t}">ツリー</a>', '<span class="muted">ツリーなし（大きすぎる）</span>')
        tpl = tpl.replace(f'href="tree.html?t={t}"', 'href="#notation" title="ツリーが大きすぎるため載せていません"')
    print('trees kept', len(keep), 'removed', len(refs - keep), flush=True)
    open(f'{OUT}/index.html', 'w').write(tpl)
    for f in ('style.css', 'tree.html', 'tree.js', 'calc.js', 'guide.js'): shutil.copy(f'site10b_static/{f}', f'{OUT}/{f}')
    open(f'{OUT}/.nojekyll', 'w').write('')
    print('site ok', 'val_i', val_i, 'q', q_i, 'w', w_i, 'val_c', val_c)

if __name__ == '__main__':
    if sys.argv[1] == 'guidesum':   # 大きな内訳：選んだ枝だけを作って要約を書く
        tree10ax.PRUNE[0] = True
        V = nash10a.load_values(); MM = load_mm()
        export_one('' if sys.argv[2] == '_' else sys.argv[2], V, MM, pid=sys.argv[3], mdir='tmeta_guide')
    elif sys.argv[1] == 'guidetree':   # 試合用ガイド：内訳 k を盤面の推奨進行 pid で
        V = nash10a.load_values(); MM = load_mm()
        export_one('' if sys.argv[2] == '_' else sys.argv[2], V, MM, pid=sys.argv[3], mdir='tmeta_guide')
    elif sys.argv[1] == 'trees':
        V = nash10a.load_values(); MM = load_mm()
        for k in sys.argv[2:]:
            export_one('' if k == '_' else k, V, MM)
    else:
        site()
