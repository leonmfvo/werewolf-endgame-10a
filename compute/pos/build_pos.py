import json, sys, time
from fractions import Fraction as F
from pos import Game, solve, behaviour, exact_eval, case_values
from derive import build_trie, formulas, policy, fs
from boards import boards

def run(b):
    g = Game(b)
    val, x = solve(g); beh = behaviour(g, x); ex, adv, v = exact_eval(g, beh)
    assert abs(float(ex) - val) < 1e-7, (b['note'], val, ex)
    cv = case_values(g, v)
    known = []
    for c in b['cases']:
        g1 = Game(dict(b, cases=[c])); v1, x1 = solve(g1); e1 = exact_eval(g1, behaviour(g1, x1))[0]
        assert abs(float(e1) - v1) < 1e-7; known.append(fs(e1))
    # 1日目の吊り先ごとの勝率（その手に固定して解き直す）
    rinfo = ('D', ())
    root_alts = {}
    rn = next(nd for _, nd in g.root.children if nd.kind == 'V')
    for a in g.vinfo[rinfo][1]:
        va, xa = solve(g, {(rinfo, a): 1}); ba = behaviour(g, xa); ea, adva, vva = exact_eval(g, ba)
        assert abs(float(ea) - va) < 1e-7
        lab = rn.vlabel[a]
        root_alts.setdefault(lab, []).append((a, ea, [fs(c) for c in case_values(g, vva)]))
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

if __name__ == '__main__':
    res = []
    for b in boards():
        t = time.time(); r = run(b); res.append(r)
        print(r['id'], r['note'], r['value'], [c['value'] for c in r['cases']], [c['known'] for c in r['cases']], f'{time.time() - t:.1f}s', flush=True)
    json.dump(res, open(sys.argv[1] if len(sys.argv) > 1 else 'pos5.json', 'w'), ensure_ascii=False, separators=(',', ':'))
