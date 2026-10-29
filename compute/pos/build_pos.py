import json, sys, time
from fractions import Fraction as F
from pos import Game, solve, behaviour, exact_eval, case_values, symmetrize
from derive import build_trie, formulas, policy, fs

def run(b, known=None):
    g = Game(b)
    val, x = solve(g); beh = behaviour(g, symmetrize(g, x)); ex, adv, v = exact_eval(g, beh)
    assert abs(float(ex) - val) < 1e-7, (b['labels'], b['cases'], val, ex)
    cv = case_values(g, v)
    if known is None and len(b['cases']) == 1: known = [fs(ex)]
    for c in ([] if known is not None else b['cases']):
        known = known or []
        g1 = Game(dict(b, cases=[c])); v1, x1 = solve(g1); e1 = exact_eval(g1, behaviour(g1, x1))[0]
        assert abs(float(e1) - v1) < 1e-7; known.append(fs(e1))
    # 1日目の吊り先ごとの勝率（その手に固定して解き直す）
    rinfo = ('D', ())
    root_alts = {}
    def find(nd):
        if nd.kind == 'V' and nd.info == rinfo: return nd
        for _, ch in nd.children:
            if ch.kind in 'CV':
                r = find(ch)
                if r: return r
    rn = find(g.root)
    done = {}
    for a in g.vinfo[rinfo][1]:
        lab = rn.vlabel[a]
        if lab not in done:   # 同じ見え方の人は条件が対称なので1人だけ解く
            va, xa = solve(g, {(rinfo, a): 1}); ba = behaviour(g, xa); ea, adva, vva = exact_eval(g, ba)
            if abs(float(ea) - va) > 1e-7:   # 混ぜる手が分数に丸まらないとき：値は線形計画から
                ea = F(va).limit_denominator(100000); vva = None
            done[lab] = (ea, [fs(c) for c in case_values(g, vva)] if vva else [])
        root_alts.setdefault(lab, []).append((a, done[lab][0], done[lab][1]))
    ra = []
    for lab, lst in root_alts.items():
        vals = sorted({e for _, e, _ in lst})
        ra.append(dict(label=lab, pos=[a + 1 for a, _, _ in lst], value=fs(vals[-1]) if len(vals) == 1 else None,
                       values=[fs(e) for _, e, _ in lst], cases=lst[0][2]))
    ra.sort(key=lambda r: -max(F(s) for s in r['values']))
    out = dict(id=b['id'], labels=b['labels'], cond=b['cond'], note=b['note'], group=b.get('group'),
               cases=[dict(name=c['name'], value=fs(cv[i]), known=known[i]) for i, c in enumerate(b['cases'])],
               value=fs(ex), root=ra, policy=policy(g, beh, adv),
               deriv=[dict(name=c['name'], f=formulas(build_trie(g, beh, adv, v, i))) for i, c in enumerate(b['cases'])],
               size=[len(g.vinfo), len(g.ainfo)])
    return out

