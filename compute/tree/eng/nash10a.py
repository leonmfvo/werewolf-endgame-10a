# 10a狩人：騙り率から内訳の出現確率を出す式と、ゲーム理論的な均衡（村 vs 人外）。
#
# 人外の選択（2日目のCO）
#   狂人：占いCO（s）・霊能CO（m）・潜伏（h）   s + m + h = 1
#   狼  ：（占い騙りの人数 fs, 霊能騙りの人数 fm）∈ {(0,0),(1,0),(2,0),(0,1),(0,2),(1,1)} を確率 w_{fs,fm} で
# 初日犠牲者（狼以外の8人から等確率）：占い 1/8・霊能 1/8・狂人 1/8・狩人と村人 5/8
#
# 内訳（占い側-霊能側）の出現確率：
#   本物が両方生きている（初日犠牲は狩人・村人・狂人）
#     狂人が占いCO  ：P = w · (5/8) · s
#     狂人が霊能CO  ：P = w · (5/8) · m
#     狂人がCOしない：P = w · (5/8 · h + 1/8)      （1/8 は狂人が初日犠牲）
#   占い欠け（初日犠牲が本物の占い師）：P = w · (1/8) · (狂人が s / m / h のどれか)
#   霊能欠け（初日犠牲が本物の霊能者）：P = w · (1/8) · (同上)
# 村は盤面（CO数）しか見えないので、盤面ごとに1つの進行を選ぶ。人外は村の進行を知ったうえで選択を決める。
import json, glob, itertools
from fractions import Fraction as F
import numpy as np
from scipy.optimize import linprog
import e10a, run10b

MADS = ('S', 'M', 'H')
WOLF = e10a.WOLF_OPTS
DUMMY = (('seer', F(1, 8)), ('med', F(1, 8)), ('mad', F(1, 8)), ('other', F(5, 8)))
OPTS = [(m, w) for m in MADS for w in WOLF]

def outcomes(mad, wolf):
    """（狂人の選択, 狼の選択）→ [(内訳キー, 確率)]（初日犠牲者について足し合わせる）"""
    fs, fm = wolf
    out = {}
    for dummy, p in DUMMY:
        if dummy == 'mad': key = e10a.compose('X', fs, fm, 'other')
        else: key = e10a.compose(mad, fs, fm, dummy)
        out[key] = out.get(key, 0) + p
    return list(out.items())

def key_prob(key, s, m, h, w):
    """式による出現確率。w は {(fs, fm): 確率}"""
    sp, mp = key.split('-')
    fs, fm = sp.count('W'), mp.count('W')
    pw = w.get((fs, fm), 0)
    madc = 's' if 'M' in sp else ('m' if 'M' in mp else 'h')
    pm = {'s': s, 'm': m, 'h': h}[madc]
    if 'T' in sp and 'T' in mp:
        return pw * (F(5, 8) * pm + (F(1, 8) if madc == 'h' else 0))
    return pw * F(1, 8) * pm

def load_values():
    """V[key][進行ID] = 村勝率（盤面ごとの共通の進行の候補）"""
    V = {}
    for f in glob.glob('r10b_*.part*of*.json'):
        key = f[len('r10b_'):f.index('.part')]
        for p, (v, mm) in json.load(open(f)).items(): V.setdefault(key, {})[p] = v
    return V

def board_policies(V):
    """盤面ごとに、その盤面の全内訳で計算済みの進行だけを使う"""
    out = {}
    for b, keys in e10a.BOARDS.items():
        cands = [run10b.pid(c) for c in run10b.board_candidates(b)]
        out[b] = [p for p in cands if all(p in V.get(k, {}) for k in keys)]
    return out

def payoff_tensor(V, BP):
    """C[o][b] = 進行ごとのベクトル：人外の選択 o・盤面 b のときの「確率 × 村勝率」の和"""
    C = {}
    for o in OPTS:
        C[o] = {}
        for key, p in outcomes(*o):
            b = e10a.board_of(key)
            vec = np.array([V[key][q] for q in BP[b]]) * float(p)
            C[o][b] = C[o].get(b, 0) + vec
    return C

def solve_correlated(C, BP):
    """人外が（狂人と狼をまとめて）選択の組み合わせを確率で選ぶときの均衡（線形計画）。
    変数：x_o（18）, t_b（盤面ごと）。最小化 Σ t_b、t_b ≥ Σ_o x_o C[o][b][π]（全進行 π）"""
    boards = list(BP)
    no, nb = len(OPTS), len(boards)
    c = np.r_[np.zeros(no), np.ones(nb)]
    A, bub, rows = [], [], []
    for j, b in enumerate(boards):
        for k, q in enumerate(BP[b]):
            row = np.zeros(no + nb)
            for i, o in enumerate(OPTS):
                if b in C[o]: row[i] = C[o][b][k]
            row[no + j] = -1
            A.append(row); bub.append(0); rows.append((b, q))
    Aeq = [np.r_[np.ones(no), np.zeros(nb)]]
    res = linprog(c, A_ub=np.array(A), b_ub=bub, A_eq=np.array(Aeq), b_eq=[1], bounds=[(0, None)] * (no + nb), method='highs')
    x = dict(zip(OPTS, res.x[:no]))
    # 村の均衡戦略：制約の双対変数（盤面ごとに足すとその盤面の出現確率になる）
    duals = -res.ineqlin.marginals
    vill = {}
    for (b, q), y in zip(rows, duals):
        if y > 1e-9: vill.setdefault(b, {})[q] = y
    return res.fun, x, vill

def village_best(C, BP, x):
    """人外の選択の分布 x に対する、盤面ごとの村の最善の進行と値"""
    out = {}; tot = 0
    for b in BP:
        vec = sum((x[o] * C[o][b] for o in OPTS if b in C[o] and x[o] > 0), np.zeros(len(BP[b])))
        if not np.any(vec): continue
        k = int(np.argmax(vec)); tot += vec[k]
        out[b] = (BP[b][k], vec[k])
    return tot, out

def solve_independent_q(C, BP, q):
    """狂人の分布 q を固定したときの、狼の最善の分布（線形計画）：(値, q, 狼の分布)"""
    boards = list(BP); nw, nb = len(WOLF), len(boards)
    A, bub = [], []
    for jb, b in enumerate(boards):
        M = np.zeros((len(BP[b]), nw))
        for iw, w in enumerate(WOLF):
            for mad in MADS:
                if q[mad] > 0 and b in C[(mad, w)]: M[:, iw] += q[mad] * C[(mad, w)][b]
        if not M.any(): continue
        for k in range(len(BP[b])):
            row = np.zeros(nw + nb); row[:nw] = M[k]; row[nw + jb] = -1
            A.append(row); bub.append(0)
    res = linprog(np.r_[np.zeros(nw), np.ones(nb)], A_ub=np.array(A), b_ub=bub,
                  A_eq=[np.r_[np.ones(nw), np.zeros(nb)]], b_eq=[1], bounds=[(0, None)] * (nw + nb), method='highs')
    return res.fun, q, dict(zip(WOLF, res.x[:nw]))

def solve_independent(C, BP, step=0.05):
    """狂人と狼が別々に（示し合わせずに）選択の確率を決めるときの、人外にとっての最善（チーム・マックスミン）。
    狂人の分布 (s, m, h) を格子で動かし、それぞれで狼の分布を線形計画で最適化する"""
    best = None
    n = round(1 / step)
    for i in range(n + 1):
        for j in range(n + 1 - i):
            q = {'S': i * step, 'M': j * step, 'H': max(0.0, 1 - (i + j) * step)}
            r = solve_independent_q(C, BP, q)
            if best is None or r[0] < best[0] - 1e-12: best = r
    return best

if __name__ == '__main__':
    # 式の確認：どんな騙り率でも出現確率の合計は 1、選択ごとの数え上げと一致する
    import random
    for _ in range(5):
        a = [random.randint(0, 9) for _ in range(3)]; s, m, h = [F(x, sum(a) or 1) for x in a] if sum(a) else (F(1), F(0), F(0))
        ww = [random.randint(0, 9) for _ in WOLF]; w = {o: F(x, sum(ww)) for o, x in zip(WOLF, ww)}
        keys = [k for ks in e10a.BOARDS.values() for k in ks]
        P = {k: key_prob(k, s, m, h, w) for k in keys}
        enum = {}
        for (mad, wo) in OPTS:
            pm = {'S': s, 'M': m, 'H': h}[mad]
            for k, p in outcomes(mad, wo): enum[k] = enum.get(k, 0) + pm * w[wo] * p
        assert sum(P.values()) == 1, sum(P.values())
        assert all(P[k] == enum.get(k, 0) for k in keys)
    print('formula ok')
