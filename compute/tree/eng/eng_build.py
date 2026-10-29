# 分岐サイトに出てくる盤面（上位）について、条件ごとに村勝率と帰着先を求めて cache/ に書く
#   python3 eng_build.py <ents.json> <出力 dir> [各人数の盤面数] [並列数]
import sys, json, os, time, hashlib
from fractions import Fraction as F
from collections import defaultdict
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from board import *

def fs(x):
    x = F(x); return str(x.numerator) if x.denominator == 1 else f'{x.numerator}/{x.denominator}'

def pages_from(ents, top):
    pages = {}
    for x in ents:
        P = parse_pub(x['pub'], x['key'])
        lab, note = notation(P)
        pk = (P['n'], lab, note)
        pg = pages.setdefault(pk, dict(n=P['n'], lab=lab, note=note, w=0.0, groups={}))
        pg['w'] += x['w']
        pol = B.pol_name(e10a.board_of(x['key']), policy_of(x['tree'])[1])
        gk = (truth_label(P, x['key']), wolf_label(P), pol)
        g = pg['groups'].setdefault(gk, dict(key=x['key'], truth=gk[0], wolves=gk[1], w=0.0, rep=None))
        g['w'] += x['w']
        if g['rep'] is None or x['w'] > g['rep'][0]: g['rep'] = (x['w'], x['pub'], x['tree'], x['day']); g['key'] = x['key']
    byn = defaultdict(list)
    for pk, pg in pages.items(): byn[pg['n']].append((pk, pg))
    out = []
    for n, L in byn.items():
        L.sort(key=lambda t: -t[1]['w'])
        for i, (pk, pg) in enumerate(L[:top]):
            pg['id'] = f'b{n}-{i + 1:02d}'; out.append(pg)
    return out, pages

def walk(T, root, inv):
    """根（昼）から次の昼まで：帰着 [(確率, ラベル列, 局面 or None, 値)] と、選択 [(誰, 題, [(ラベル, 値)], 最善, 経路)]"""
    nxt = []; ch = []
    def go(i, p, labs, first):
        nd = T.nodes[i]; s = inv.get(i)
        if not first and s is not None and s[0] == 'D':
            nxt.append((p, labs, s, nd['v'])); return
        if nd['k'] == 'end' or not nd.get('c'):
            nxt.append((p, labs, None, nd['v'])); return
        if nd['k'] in ('wolf', 'vil') and len(nd['c']) > 1:
            ch.append(('v' if nd['k'] == 'vil' else 'w', nd.get('t'), [(c[1], T.nodes[c[2]]['v']) for c in nd['c']], nd.get('best', 0), list(labs)))
        kids = nd['c']
        if nd['k'] in ('wolf', 'vil'): kids = [nd['c'][nd.get('best', 0)]]
        for c in kids:
            q = c[0] if (nd['k'] == 'chance' and c[0] is not None) else F(1)
            go(c[2], p * q, labs + ([c[1]] if c[1] else []), False)
    go(root, F(1), [], True)
    return nxt, ch

def job(pg):
    t0 = time.time()
    res = dict(id=pg['id'], n=pg['n'], lab=pg['lab'], note=pg['note'], w=pg['w'], groups=[])
    groups = sorted(pg['groups'].values(), key=lambda g: -g['w'])[:GMAX]
    for g in groups:
        _, pub, tree, nt = g['rep']
        P = parse_pub(pub, g['key'])
        gr = dict(key=g['key'], truth=g['truth'], wolves=g['wolves'], w=g['w'], tree=tree, policy=B.pol_name(e10a.board_of(g['key']), policy_of(tree)[1]), opts=[])
        for o in options(P, g['key']):
            tree10ax.PRUNE[0] = pg['n'] >= 7
            T, root, inv = solve(P, g['key'], tree, nt, o)
            nxt, ch = walk(T, root, inv)
            succ = []
            for p, labs, s, v in nxt:
                tgt = None
                if s is not None:
                    P2 = dict(n=E.counts(s[1], s[2], s[5])[1], slots=s[1], meds=s[2], T=s[3], TM=s[4], cats=s[5])
                    lab2, note2 = notation(P2)
                    pm, phu = status_of(s, g['key'])
                    tgt = dict(n=P2['n'], lab=lab2, note=note2, truth=truth_label(P2, g['key']), wolves=wolf_label(P2),
                               w=wolves_alive(P2), pm=fs(pm), ph={k: fs(x) for k, x in phu.items()})
                succ.append(dict(p=fs(p), labs=labs, tgt=tgt, v=fs(v)))
            gr['opts'].append(dict(name=o['name'], mad=o['mad'], hunter=o['hunter'], v=fs(T.nodes[root]['v']), nodes=len(T.nodes),
                                   succ=succ, choices=[dict(who=a, t=b, alts=[(l, fs(x)) for l, x in c], best=d, labs=e) for a, b, c, d, e in ch]))
            E.V.cache_clear(); E.VT.cache_clear()
        res['groups'].append(gr)
    res['sec'] = round(time.time() - t0, 1)
    json.dump(res, open(os.path.join(OUT, pg['id'] + '.json'), 'w'), ensure_ascii=False)
    return pg['id'], res['sec'], sum(len(g['opts']) for g in res['groups'])

GMAX = 6
if __name__ == '__main__':
    ents = json.load(open(sys.argv[1])); OUT = sys.argv[2]; top = int(sys.argv[3]); npar = int(sys.argv[4])
    os.makedirs(OUT, exist_ok=True)
    sel, allp = pages_from(ents, top)
    json.dump([dict(n=p['n'], lab=p['lab'], note=p['note'], w=p['w'], id=p.get('id')) for p in allp.values()], open(os.path.join(OUT, '_all.json'), 'w'), ensure_ascii=False)
    todo = [p for p in sorted(sel, key=lambda p: p['n']) if not os.path.exists(os.path.join(OUT, p['id'] + '.json'))]
    print(len(sel), 'pages,', len(todo), 'to do', flush=True)
    with Pool(npar) as pool:
        for pid, sec, k in pool.imap_unordered(job, todo):
            print(pid, sec, 's', k, 'cases', flush=True)
