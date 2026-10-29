# 分岐サイト（werewolf-tree-10a）の全分岐ツリーから、昼の局面（盤面）を集める。
# 各内訳は「その内訳で一番よい進行」のツリーを使い、到達確率（偶然の分岐の確率、村と人外は最善の手）を求める。
import json, glob, os, sys, re
from collections import defaultdict

TREE = sys.argv[1] if len(sys.argv) > 1 else '/home/user/werewolf-tree-10a'

def load(d):
    meta = json.load(open(f'{d}/meta.json'))
    nodes = []; strs_of = []
    k = 0
    while os.path.exists(f'{d}/c{k}.json'):
        c = json.load(open(f'{d}/c{k}.json'))
        S = c['strs']
        for nd in c['nodes']:
            s = lambda j: None if j is None else S[j]
            nodes.append(dict(k=nd[0], cat=nd[1], d=nd[2], v=nd[3], vf=s(nd[4]), t=s(nd[5]), pub=s(nd[6]), hid=s(nd[7]), best=nd[8],
                              ch=[dict(p=p, pf=s(pf), lab=s(lab), cid=cid, kind=kind, v=v, vf=s(vf)) for p, pf, lab, cid, kind, v, vf in nd[9]]))
        k += 1
    return meta, nodes

def follow(nodes, i):
    """局面 i から先で使われる子：偶然の分岐は全部（確率つき）、選択は最善の子だけ"""
    nd = nodes[i]
    if nd['k'] in ('w', 'v'):
        b = nd['best']
        c = nd['ch'][b] if b is not None and b >= 0 else min(nd['ch'], key=lambda c: c['v']) if nd['k'] == 'w' else max(nd['ch'], key=lambda c: c['v'])
        return [(1.0, c)]
    return [((c['p'] if c['p'] is not None else 1.0), c) for c in nd['ch']]

def reach(nodes, root):
    order = []; seen = set(); st = [(root, 0)]
    while st:   # 帰りがけ順
        i, s = st.pop()
        if s == 0:
            if i in seen: continue
            seen.add(i); st.append((i, 1))
            for _, c in follow(nodes, i):
                if c['cid'] is not None and c['cid'] >= 0 and c['cid'] not in seen: st.append((c['cid'], 0))
        else: order.append(i)
    order.reverse()
    r = defaultdict(float); r[root] = 1.0
    for i in order:
        for p, c in follow(nodes, i):
            if c['cid'] is not None and c['cid'] >= 0: r[c['cid']] += r[i] * p
    return r


def next_days(nodes, i):
    """昼の局面 i から、次の昼の局面（または決着）まで：[(確率, ラベルの列, 行き先の局面 or None, 決着の値)]、と村・人外の選択"""
    out = []; choices = []
    def walk(j, p, labs, first):
        nd = nodes[j]
        if not first and nd['t'] == '昼':
            out.append((p, labs, j, None)); return
        if nd['k'] == 'e' or not nd['ch']:
            out.append((p, labs, None, nd['v'])); return
        if nd['k'] in ('v', 'w') and len(nd['ch']) > 1:
            choices.append(dict(who=nd['k'], t=nd['t'], p=p, labs=list(labs),
                                alts=[(c['lab'], c['v'], c['vf']) for c in nd['ch']], best=nd['best']))
        for q, c in follow(nodes, j):
            l = labs + ([c['lab']] if c['lab'] else [])
            if c['cid'] is None or c['cid'] < 0: out.append((p * q, l, None, c['v'])); continue
            walk(c['cid'], p * q, l, False)
    walk(i, 1.0, [], True)
    return out, choices

if __name__ == '__main__':
    sys.path.insert(0, f'{TREE}/handoff')
    from nash10a import key_prob
    from fractions import Fraction as F
    summ = json.load(open(f'{TREE}/data/summary.json'))
    best = {e['key']: e['best'] for b in summ['boards'].values() for e in b}
    board_of = {e['key']: b for b, es in summ['boards'].items() for e in es}
    cand = defaultdict(list)
    for f in glob.glob(f'{TREE}/data/trees/*/meta.json'):
        m = json.load(open(f))['meta']; cand[m['key']].append((m['policy'] == best.get(m['key']), m['v'], os.path.dirname(f), m['policy']))
    W6 = {k: F(1, 6) for k in [(0, 0), (1, 0), (2, 0), (0, 1), (0, 2), (1, 1)]}
    third = F(1, 3)
    ents = []
    for key in sorted(cand):
        isbest, v0, d, pol = max(cand[key])
        pk = float(key_prob(key, third, third, third, W6))
        M, nodes = load(d)
        r = reach(nodes, M['root'])
        tid = os.path.basename(d)
        for i, nd in enumerate(nodes):
            if nd['t'] != '昼' or r.get(i, 0) <= 0: continue
            nx, ch = next_days(nodes, i)
            ents.append(dict(key=key, board=board_of[key], tree=tid, policy=pol, polbest=isbest, node=i, w=pk * r[i], pub=nd['pub'], hid=nd['hid'],
                             v=nd['v'], vf=nd['vf'], day=nd['d'], next=[(p, l, (tid, j) if j is not None else None, v) for p, l, j, v in nx], choices=ch))
        print(key, pol, isbest, len(nodes), file=sys.stderr, flush=True)
    json.dump(ents, open(sys.argv[2], 'w'), ensure_ascii=False)
