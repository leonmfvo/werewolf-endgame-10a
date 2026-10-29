from fractions import Fraction as F   # plurx：plur を分数で計算する版
# 自由投票の多数決（最多票の人を吊る。同票なら最多の中からランダム）で、人間の候補1人・狼の候補1人が吊られる確率。
#   候補：人間 HC 人・狼 WC 人。投票者：候補の人間（自分以外の候補からランダム）、
#   候補でない人間 NH 人（候補全員からランダム）、狼 NW 人（人間の候補からランダム）。
# 人間の候補は「(票数, もう投票したか)」、狼の候補は票数だけの多重集合で持てば、並び替えて同じ局面をまとめられる。
from functools import lru_cache
from collections import defaultdict

def _step(dist, voter):
    nd = defaultdict(F)
    for (hs, ws), p in dist.items():
        hs = list(hs); ws = list(ws)
        if voter == 'hc':                       # まだ投票していない人間の候補の1人（どれでも同じ）
            i = next(j for j, x in enumerate(hs) if not x[1])
            me = (hs[i][0], True)
            rest = hs[:i] + hs[i + 1:]
            ch = [('h', j) for j in range(len(rest))] + [('w', j) for j in range(len(ws))]
            base_h = rest
        else:
            me = None; base_h = hs
            ch = [('h', j) for j in range(len(hs))] + ([('w', j) for j in range(len(ws))] if voter == 'nh' else [])
        q = p / F(len(ch))
        for kind, j in ch:
            h2 = list(base_h); w2 = list(ws)
            if kind == 'h': h2[j] = (h2[j][0] + 1, h2[j][1])
            else: w2[j] += 1
            if me is not None: h2.append(me)
            nd[(tuple(sorted(h2)), tuple(sorted(w2)))] += q
    return nd

@lru_cache(None)
def plurality(HC, WC, NH, NW):
    """(人間の候補1人が吊られる確率, 狼の候補1人が吊られる確率)"""
    C = HC + WC
    if HC == 0 or C < 2: return (F(1, C), F(1, C))
    dist = {(tuple([(0, False)] * HC), tuple([0] * WC)): F(1)}
    voters = ['hc'] * HC + ['nh'] * NH + ['w'] * NW
    if C == 1: voters = []
    for v in voters:
        if v == 'hc' and C < 2: continue
        dist = _step(dist, v)
    pw = F(0)
    for (hs, ws), p in dist.items():
        m = max([x[0] for x in hs] + list(ws))
        th = sum(1 for x in hs if x[0] == m); tw = sum(1 for x in ws if x == m)
        pw += p * F(tw, th + tw)
    pw1 = pw / WC if WC else F(0)
    return ((1 - pw) / HC, pw1)

if __name__ == '__main__':
    import time; t = time.time()
    print(plurality(7, 2, 1, 3), 2 * plurality(7, 2, 1, 3)[1], time.time() - t)
    t = time.time(); print(plurality(9, 2, 0, 3), time.time() - t)
