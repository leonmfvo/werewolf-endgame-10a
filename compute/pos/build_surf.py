# 見た目の盤面ごとに、真偽 × 生存状況の各場合を解いて data/pos5.json に書く
import json, sys, time
from build_pos import run
from boards2 import surfaces

out = []
for s in surfaces():
    t0 = time.time()
    for t in s['truths']:
        for sec in t['sections']:
            b = dict(sec['board'], id='', cond=[t['name'], sec['title']], note='', group='')
            r = run(b)
            sec.pop('board'); sec.pop('key')
            sec.update({k: r[k] for k in ('value', 'cases', 'root', 'policy', 'deriv')})
    out.append(s)
    print(s['id'], ','.join(s['labels']), [(t['name'], [(x['title'], x['value']) for x in t['sections']]) for t in s['truths']], f'{time.time() - t0:.0f}s', flush=True)
json.dump(out, open(sys.argv[1], 'w'), ensure_ascii=False, separators=(',', ':'))
