# 10a狩人：内訳ごとに、村の進行の候補すべての村勝率を求める（狼は最小化、狂人は毎晩●○を選ぶ）
import sys, time, json, itertools; sys.setrecursionlimit(1000000)
import engine10 as E, e10a

BASE = dict(w0=True, fix2=True, cw=0, hcoopt=1, cr='tm', gp='info', bt='switch', tp='rand', mad='A', nwv=True, plur=True, lot=False, hm=False, hu=0, mstart=2, mr=0, bloc=0, tdelay=0)

def candidates(key):
    """村が内訳を仮定したうえで選びうる進行の候補"""
    sp, mp = key.split('-')
    if 'T' in sp:
        # 占いCO者が2人以上なら、灰の吊り方に「真置きしていない占いCO者の○を優先（囲いを疑う）」も加える
        seer = [('keep', 'rand', 'info')] if len(sp) == 1 else [(x, t, g) for x, t in (('keep', 'rand'), ('keep', 'white'), ('trust', 'rand'), ('trust', 'white'), ('roller', 'rand')) for g in ('info', 'anti')]
    else:   # 占い欠け：占いCO者は全員偽
        seer = [(x, 'rand', g) for x in ('ignore', 'roller') for g in ('plain', 'info', 'anti')]
    if 'T' in mp:
        med = [('trust', False)] if len(mp) == 1 else [('trust', False), ('roller', False)]
    else:   # 霊能欠け：霊能CO者は全員偽
        med = [('trust', False), ('trust', True)] if len(mp) == 1 else [('trust', False), ('roller', False)]
    out = []
    # 占い欠けでは真置きする占い師がいないので、占い指定は霊指定と同じになる（霊指定と自由投票だけを試す）
    dss = ['seer', 'medium', 'none'] if 'T' in sp else ['medium', 'none']
    for (s_, t, g), (m, h), d in itertools.product(seer, med, dss):
        out.append(dict(sp=s_, tp=t, gp=g, mp=m, hm=h, ds=d))
    return out

def run(key):
    mms = ('W', 'B', 'contra') if 'M' in key.split('-')[1] else ('B',)
    res = []
    for c in candidates(key):
        t = time.time(); best = None
        for mm in mms:
            E.setpol(**{**BASE, **c, 'mm': mm})
            v = E.V(e10a.initial10(key))
            if best is None or v < best[0]: best = (v, mm)
        res.append(dict(**c, v=best[0], mm=best[1]))
        print(key, c, round(best[0], 4), best[1], round(time.time() - t), 's', flush=True)
    return res

if __name__ == '__main__':
    keys = sys.argv[1:] or [k for b in e10a.BOARDS.values() for k in b]
    for key in keys:
        r = run(key)
        json.dump(r, open(f'r10a_{key}.json', 'w'), ensure_ascii=False)
        b = max(r, key=lambda x: x['v'])
        print('BEST', key, b, flush=True)
