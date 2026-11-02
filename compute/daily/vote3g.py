# 3人日：村は生存状況（狂人の生死・灰の狩人や猫又）を知らない。盤面ごとに1つの決め方（見た目と自分の役ごと）を選ぶ。
# 狼・狂人も自分の見た目と役しか分からない。村はすべての内訳（役の札の数からの重み）の平均で一番勝てる決め方を選び、
# 人外はそれを知ったうえで、2人で一番村に不利な投票をする。
import itertools
from fractions import Fraction as F
from collections import defaultdict
import vote3 as V3
from game10 import label_key

COARSE = [0, 1/4, 1/3, 1/2, 2/3, 3/4, 1]

def solve_board(board, cases=None, extras=None):
    """cases：[(重み, 役)]（省略すると役の札の数からの重み）。extras：内訳ごとの、狼だけが知っていること（狼の型を分ける）"""
    cases = list(V3.assignments(board)) if cases is None else list(cases)
    if not cases: return None
    extras = extras or [None] * len(cases)
    xt = lambda k, i, r: (board[i], r, extras[k] if r == 'W' else None)
    vt = sorted({(board[i], r[i]) for _, r in cases for i in range(len(board)) if r[i] in V3.VILL}, key=lambda t: (label_key(t[0]), t[1]))
    at = sorted({xt(k, i, r[i]) for k, (_, r) in enumerate(cases) for i in range(len(board)) if r[i] in 'WX'}, key=lambda t: (label_key(t[0]), t[1], repr(t[2])))
    tg = {t: V3.targets(board, board.index(t[0])) for t in vt + at}
    tot = sum(w for w, _ in cases)
    # 浮動小数で速く：各内訳について、各人の投票先（個人）の確率
    idx_of = {t: i for i, t in enumerate(vt)}
    seats = {(i, l): [j for j in range(len(board)) if j != i and board[j] == l] for i in range(len(board)) for l in set(board)}
    def val(ps, ads, exact=False, per=None, hangs=None):
        num = (lambda x: F(x)) if exact else float
        s = num(0)
        for k, (w, roles) in enumerate(cases):
            votes = []
            for i in range(len(board)):
                t = (board[i], roles[i])
                if roles[i] in V3.VILL:
                    labs = tg[t]; d = {labs[0]: num(ps[idx_of[t]]), labs[1]: 1 - num(ps[idx_of[t]])} if len(labs) == 2 else {labs[0]: num(1)}
                else: d = {ads[at.index(xt(k, i, roles[i]))]: num(1)}
                if exact: votes.append(V3.vote_dist(board, i, d))
                else:   # 小数のまま（分数にすると遅い）：区分ごとの確率を、その区分の人に等分
                    vd = {}
                    for l, q in d.items():
                        js = seats[(i, l)]
                        for j in js: vd[j] = vd.get(j, 0.0) + float(q) / len(js)
                    votes.append(vd)
            hang, v = outcome(board, roles, votes, exact)
            if per is not None: per.append(v)
            if hangs is not None: hangs.append(dict(hang))
            s += num(w) / num(tot) * v
        return s
    aopts = list(itertools.product(*[tg[t] for t in at]))
    wmemo = {}
    def worst(ps):
        k = tuple(ps)
        if k not in wmemo: wmemo[k] = min((val(ps, a), a) for a in aopts)
        return wmemo[k]
    nv = [len(tg[t]) == 2 for t in vt]
    grids = [COARSE if two else [1] for two in nv]
    best = None
    if 7 ** sum(nv) <= 20000:
        seeds = itertools.product(*grids)
    else:
        # 決め方の種類が多い（狩A・狩B などで見分けられる人が多い）ときは、0・1/2・1 の組み合わせを出発点にして 1/12 刻みで良くしていく
        seeds = itertools.product(*[[0, 1/2, 1] if two else [1] for two in nv])
    for ps in seeds:
        w = worst(ps)
        if best is None or w[0] > best[0] + 1e-12: best = (w[0], ps, w[1])
    if 7 ** sum(nv) > 20000:
        tops = sorted(((worst(ps)[0], ps) for ps in itertools.product(*[[0, 1/2, 1] if two else [1] for two in nv])), key=lambda x: -x[0])
        for _, ps in tops[:6]:   # 上位の出発点から 1/12 刻みで1つずつ動かして詰める
            ps = list(ps); cur = worst(ps)
            improved = True
            while improved:
                improved = False
                for k in range(len(vt)):
                    if not nv[k]: continue
                    for q in [x / 12 for x in range(13)]:
                        trial = ps[:]; trial[k] = q
                        w = worst(trial)
                        if w[0] > cur[0] + 1e-12: cur = w; ps = trial; improved = True
            if cur[0] > best[0] + 1e-12: best = (cur[0], tuple(ps), cur[1])
    # 1/12 刻みで、1つずつ動かして詰める
    improved = True
    ps = list(best[1])
    while improved:
        improved = False
        for k in range(len(vt)):
            if not nv[k]: continue
            for q in [x / 12 for x in range(13)]:
                trial = ps[:]; trial[k] = q
                w = worst(trial)
                if w[0] > best[0] + 1e-12: best = (w[0], tuple(trial), w[1]); ps = trial; improved = True
    ps = [F(p).limit_denominator(12) for p in best[1]]
    ads = min(aopts, key=lambda a: val(ps, a, True))
    # 比べる相手：「全部入れる／1/2ずつ」の決め方で、最善と違うもののうち一番よいもの（同じく人外の最善応答に対して）
    alt = None
    for q in itertools.product(*[[0, 1/2, 1] if two else [1] for two in nv]):
        qf = [F(x).limit_denominator(12) for x in q]
        if qf == ps: continue
        w = worst(q)
        if alt is None or w[0] > alt[0] + 1e-12: alt = (w[0], qf)
    altd = None
    if alt:
        a_ads = min(aopts, key=lambda a: val(alt[1], a, True))
        altd = dict(ps=alt[1], ads=a_ads, v=val(alt[1], a_ads, True))
    per = []; hangs = []; v = val(ps, ads, True, per, hangs)   # per：内訳ごとの村勝率、hangs：内訳ごとの吊られる人の確率
    def evalp(ps2, ads2):   # 別の決め方での（村勝率, 内訳ごと, 吊られる人）
        p2 = []; h2 = []; v2 = val(ps2, ads2, True, p2, h2); return v2, p2, h2
    return dict(cases=cases, vt=vt, at=at, tg=tg, ps=ps, ads=ads, v=v, per=per, hangs=hangs, alt=altd, evalp=evalp)

def outcome(board, roles, votes, exact):
    n = len(board)
    hang = defaultdict(float if not exact else F)
    for combo in itertools.product(*[list(v.items()) for v in votes]):
        p = 1; cnt = [0] * n
        for t, q in combo: p *= q; cnt[t] += 1
        if p == 0: continue
        m = max(cnt); top = [k for k in range(n) if cnt[k] == m]
        for k in top: hang[k] += p / len(top)
    v = 0
    for k, p in hang.items():
        r = roles[k]
        x = 1 if r == 'W' else ((sum(1 for j in range(n) if j != k and roles[j] == 'W') / (n - 1)) if not exact else F(sum(1 for j in range(n) if j != k and roles[j] == 'W'), n - 1)) if r == 'C' else 0
        v += p * x
    return hang, v

def plan_dists(R, ps=None):
    out = {}
    for t, p in zip(R['vt'], ps if ps is not None else R['ps']):
        labs = R['tg'][t]
        out[t] = {labs[0]: p, labs[1]: 1 - p} if len(labs) == 2 else {labs[0]: F(1)}
    return out

if __name__ == '__main__':
    import time
    for b in V3.boards():
        t = time.time(); R = solve_board(b)
        if R: print(','.join(b), R['v'], {t: str(p) for t, p in zip(R['vt'], R['ps'])}, R['ads'], round(time.time() - t, 1), flush=True)
