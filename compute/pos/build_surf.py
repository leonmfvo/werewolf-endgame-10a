# 見た目の盤面ごとに、真偽 × 生存状況の各場合を解いて data/pos{n}.json に書く（python3 build_surf.py n 出力 [並列数]）
import json, sys, time
from multiprocessing import Pool
from build_pos import run
from boards2 import surfaces

def job(arg):
    key, b, known = arg
    t = time.time()
    r = run(dict(b, id='', cond=[], note='', group=''), known)
    return key, {k: r[k] for k in ('value', 'cases', 'root', 'policy', 'deriv')}, time.time() - t

if __name__ == '__main__':
    n = int(sys.argv[1]); outp = sys.argv[2]; npar = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    S = surfaces(n)
    secs = {(si, ti, ki): sec for si, s in enumerate(S) for ti, t in enumerate(s['truths']) for ki, sec in enumerate(t['sections'])}
    single = [k for k, sec in secs.items() if len(sec['board']['cases']) == 1]
    mixed = [k for k, sec in secs.items() if len(sec['board']['cases']) > 1]
    res = {}
    def report(k, r, dt):
        res[k] = r; s = S[k[0]]
        print(f"{len(res)}/{len(secs)} {','.join(s['labels'])} {s['truths'][k[1]]['name']} {secs[k]['title']} {r['value']} {dt:.0f}s", flush=True)
    with Pool(npar) as pool:
        # 重いものから
        order = sorted(single, key=lambda k: -sum(secs[k]['board']['cases'][0]['gray'].values()))
        for k, r, dt in pool.imap_unordered(job, [(k, secs[k]['board'], None) for k in order]): report(k, r, dt)
        args = []
        for k in mixed:
            si, ti, _ = k
            known = []
            for c in secs[k]['board']['cases']:
                kk = next(x for x in single if x[:2] == (si, ti) and secs[x]['title'] == c['name'])
                known.append(res[kk]['value'])
            args.append((k, secs[k]['board'], known))
        for k, r, dt in pool.imap_unordered(job, args): report(k, r, dt)
    for k, sec in secs.items():
        sec.pop('board'); sec.pop('key'); sec.update(res[k])
    json.dump(S, open(outp, 'w'), ensure_ascii=False, separators=(',', ':'))
