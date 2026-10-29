# 10a狩の終盤表：生存者の「本当の役」と「村から見えている情報」の組から、村勝率を厳密に（分数で）求める。
#
# 1人ごとに（役, 見え方）の組を持ち、局面はその人数の組（多重集合）で表す。
#   役：V 村人 / H 狩人 / X 狂人 / W 狼 / S 本物の占い師（確定） / M 本物の霊能者（確定）
#   見え方：g グレー / w 確定白（人間と分かっている。狂人も占いの○で確定白になりうる） / b 確定黒（占いの●）
#          H 狩人CO済み（対抗なし） / c 狩人CO者2人（本物と狼の対抗）の片方 / S 確定占い / M 確定霊能
# 村：吊り先は見え方の区分（確定黒・狩人CO者2人・グレー・確定白・…）から選び、区分の中ではランダム。
#     指定役（確定占い > 確定霊能 > 狩人CO済み > 確定白からランダム）がいれば区分を村勝率が一番高くなるように選ぶ。
#     確定白の指定役が実は狂人なら、狂人が村勝率を一番低くする区分を選ぶ。指定役がいなければ自由投票（狼は身内に投票しない多数決）。
#     本物の占い師は毎晩グレーからランダムに1人を占い、結果は朝に公開。本物の霊能者は前日に吊った人の色を朝に公開。
#     狩人は 確定占い > 確定霊能 > 確定白からランダム > ほかの生存者からランダム の順で護衛する。
#     GJ の翌朝、潜伏している狩人は「COして護衛先（噛まれた人）を申告する」か「潜伏を続ける」かを村勝率が高い方で選ぶ。
# 人外：狼は噛む区分（見え方）を村勝率が一番低くなるように選ぶ（区分の中ではランダム。狼は生きている役の数は知っているが、誰がどれかは知らない）。
#     狩人がCOしたら、灰の狼に対抗の狩人COをさせるかを選ぶ。狂人は人間として数え、PP（人外が過半数）に加わる。
from fractions import Fraction as F
from functools import lru_cache
from plurx import plurality

PAIRS = [('V', 'g'), ('V', 'w'), ('H', 'g'), ('H', 'w'), ('H', 'H'), ('H', 'c'), ('X', 'g'), ('X', 'w'),
         ('W', 'g'), ('W', 'b'), ('W', 'c'), ('S', 'S'), ('M', 'M')]
IDX = {p: i for i, p in enumerate(PAIRS)}
NP = len(PAIRS)
STATUS_NAME = {'b': '確定黒', 'c': '狩人CO者2人', 'g': 'グレー', 'w': '確定白', 'H': '狩人CO者', 'S': '確定占い', 'M': '確定霊能'}

def cnt(c, role=None, st=None):
    return sum(c[i] for i, (r, s) in enumerate(PAIRS) if (role is None or r == role) and (st is None or s == st))

def nwolf(c): return cnt(c, 'W')
def alive(c): return sum(c)

def term(c):
    w, n = nwolf(c), alive(c)
    if w == 0: return F(1)
    if 2 * w >= n: return F(0)
    return None

def add(c, i, d):
    l = list(c); l[i] += d; return tuple(l)

def members(c, st):
    """見え方 st の人：[(重み, 組の番号)]"""
    return [(c[i], i) for i, (r, s) in enumerate(PAIRS) if s == st and c[i]]

# ---------------------------------------------------------------- 昼
def day_value(c):
    t = term(c)
    if t is not None: return t
    w, n, mad = nwolf(c), alive(c), cnt(c, 'X')
    if mad and n >= 5 and 2 * (w + 1) >= n:   # PP：人外（狼＋狂人）が過半数なら負け、同数なら決選で半々
        if 2 * (w + 1) > n: return F(0)
        return F(1, 2) * hang_value(c)
    return hang_value(c)

def hang_cat(c, st):
    """見え方 st の人をランダムに吊ったときの値"""
    ms = members(c, st); tot = sum(m for m, _ in ms)
    return sum(F(m, tot) * V(('N', add(c, i, -1), i)) for m, i in ms)

def hang_options(c):
    return [st for st in ('b', 'c', 'g', 'w', 'H', 'M', 'S') if cnt(c, st=st)]

@lru_cache(None)
def hang_value(c):
    opts = hang_options(c)
    vals = {st: hang_cat(c, st) for st in opts}
    best = max(vals.values()); worst = min(vals.values())
    if cnt(c, st='S') or cnt(c, st='M') or cnt(c, st='H'): return best   # 確定した役の指定役
    nw_ = cnt(c, st='w')
    if nw_:   # 確定白から指定役をランダムに：狂人なら村に一番悪い区分を選ぶ
        pm = F(cnt(c, 'X', 'w'), nw_)
        return (1 - pm) * best + pm * worst
    return vote_value(c)

def vote_value(c):
    """指定役なし：確定黒 > 狩人CO者2人 は全員一致で吊る。それ以外はグレー（いなければ確定白）から多数決"""
    for st in ('b', 'c'):
        if cnt(c, st=st): return hang_cat(c, st)
    st = 'g' if cnt(c, st='g') else 'w'
    ms = members(c, st)
    WC = sum(m for m, i in ms if PAIRS[i][0] == 'W'); HC = sum(m for m, i in ms if PAIRS[i][0] != 'W')
    nw, n = nwolf(c), alive(c)
    if HC == 0 or WC + HC < 2: return hang_cat(c, st)
    vh, vw = plurality(HC, WC, n - nw - HC, nw)
    return sum(m * (vw if PAIRS[i][0] == 'W' else vh) * V(('N', add(c, i, -1), i)) for m, i in ms)

# ---------------------------------------------------------------- 夜
def guard_dist(c):
    """狩人（見え方を問わず1人）の護衛先：[(確率, 組の番号)]。狩人自身は除く"""
    hi = next((i for i, (r, s) in enumerate(PAIRS) if r == 'H' and c[i]), None)
    if hi is None: return None, []
    for st in ('S', 'M'):
        if cnt(c, st=st): return hi, [(F(1), IDX[(st, st)])]
    def others(st):
        ms = [(c[i] - (1 if i == hi else 0), i) for i, (r, s) in enumerate(PAIRS) if (st is None or s == st) and c[i]]
        ms = [(m, i) for m, i in ms if m > 0]; tot = sum(m for m, _ in ms)
        return [(F(m, tot), i) for m, i in ms] if tot else []
    return hi, (others('w') or others(None))

def morning(c, pend, gj_target):
    """朝：占い・霊能の結果。[(確率, 局面)]"""
    outs = [(F(1), c)]
    if cnt(c, 'S'):   # 本物の占い師がグレーをランダムに占う
        no = []
        for p, c1 in outs:
            ms = members(c1, 'g'); tot = sum(m for m, _ in ms)
            if not tot: no.append((p, c1)); continue
            for m, i in ms:
                r = PAIRS[i][0]
                no.append((p * F(m, tot), add(add(c1, i, -1), IDX[(r, 'b' if r == 'W' else 'w')], 1)))
        outs = no
    if cnt(c, 'M') and pend is not None and pend >= 0 and PAIRS[pend][1] == 'c':   # 霊能：狩人CO者2人の片方の色
        no = []
        for p, c1 in outs:
            if PAIRS[pend][0] == 'W' and c1[IDX[('H', 'c')]]: c1 = add(add(c1, IDX[('H', 'c')], -1), IDX[('H', 'H')], 1)
            elif PAIRS[pend][0] == 'H' and c1[IDX[('W', 'c')]]: c1 = add(add(c1, IDX[('W', 'c')], -1), IDX[('W', 'b')], 1)
            no.append((p, c1))
        outs = no
    return outs

def night_options(c):
    return [st for st in ('g', 'w', 'H', 'c', 'S', 'M') if sum(m for m, i in members(c, st) if PAIRS[i][0] != 'W')]

def bite_value(c, pend, st):
    """見え方 st の人間を噛む"""
    hi, gd = guard_dist(c)
    ms = [(m, i) for m, i in members(c, st) if PAIRS[i][0] != 'W']; tot = sum(m for m, _ in ms)
    v = F(0)
    for m, i in ms:
        p = F(m, tot)
        gj = gj_prob(c, hi, gd, i)
        if gj < 1:   # 噛まれて死亡
            c2 = add(c, i, -1)
            v += p * (1 - gj) * sum(q * V(('D', c3, -1)) for q, c3 in morning(c2, pend, None))
        if gj > 0:   # GJ
            v += p * gj * gj_morning(c, pend, i)
    return v

def gj_prob(c, hi, gd, i):
    """噛まれる人（組 i のうちの1人）を狩人が守っている確率"""
    if hi is None or PAIRS[i][0] == 'H': return F(0)
    for q, j in gd:
        if j == i:
            m = c[i] - (1 if i == hi else 0)
            return q / m
    return F(0)

def gj_morning(c, pend, i):
    """GJ の朝：結果を出したあと、潜伏している狩人がCOするかを村が選ぶ（COしたら狼は対抗するかを選ぶ）"""
    v_no = sum(q * V(('D', c3, -1)) for q, c3 in morning(c, pend, i))
    hid = [j for j in (IDX[('H', 'g')], IDX[('H', 'w')]) if c[j]]
    if not hid: return v_no
    def co(c1, counter):
        h = next((j for j in (IDX[('H', 'g')], IDX[('H', 'w')]) if c1[j]), None)
        if h is None: return c1
        r = PAIRS[i]
        if r[1] == 'g' and c1[i] and (i != h or c1[i] > 1): c1 = add(add(c1, i, -1), IDX[(r[0], 'w')], 1)   # 護衛先（噛まれた人）は人間確定
        c1 = add(c1, h, -1)
        if counter:   # 灰の狼が対抗の狩人CO：2人とも「狩人CO者2人」
            return add(add(add(c1, IDX[('H', 'c')], 1), IDX[('W', 'g')], -1), IDX[('W', 'c')], 1)
        return add(c1, IDX[('H', 'H')], 1)
    vs = []
    for counter in ((False, True) if c[IDX[('W', 'g')]] else (False,)):
        vs.append(sum(q * V(('D', co(c3, counter), -1)) for q, c3 in morning(c, pend, i)))
    return max(v_no, min(vs))

@lru_cache(None)
def night_value(c, pend):
    t = term(c)
    if t is not None: return t
    opts = night_options(c)
    if not opts: return sum(q * V(('D', c3, -1)) for q, c3 in morning(c, pend, None))
    return min(bite_value(c, pend, st) for st in opts)

def V(s):
    ph, c, pend = s
    return day_value(c) if ph == 'D' else night_value(c, pend)


# ---------------------------------------------------------------- すべての局面
def all_states(nmin=3, nmax=9):
    """生存 nmin〜nmax 人の、ありうる局面（狼が1人以上で、まだ決着していないもの）"""
    import itertools
    out = []
    Hst = [None, 'g', 'w', 'H', 'c']; Xst = [None, 'g', 'w']
    for nv in range(5):
        for vw in range(nv + 1):
            for hs in Hst:
                for xs in Xst:
                    for wg, wb, wc in itertools.product(range(3), range(3), range(2)):
                        if not 1 <= wg + wb + wc <= 2: continue
                        if (hs == 'c') != (wc == 1) and not (hs == 'c' or wc == 1): pass
                        for s_, m_ in itertools.product(range(2), range(2)):
                            c = [0] * NP
                            c[IDX[('V', 'g')]] = nv - vw; c[IDX[('V', 'w')]] = vw
                            if hs: c[IDX[('H', hs)]] = 1
                            if xs: c[IDX[('X', xs)]] = 1
                            c[IDX[('W', 'g')]] = wg; c[IDX[('W', 'b')]] = wb; c[IDX[('W', 'c')]] = wc
                            c[IDX[('S', 'S')]] = s_; c[IDX[('M', 'M')]] = m_
                            c = tuple(c)
                            if not nmin <= alive(c) <= nmax or term(c) is not None: continue
                            out.append(c)
    return out

def options_day(c):
    if term(c) is not None: return {}
    return {st: hang_cat(c, st) for st in hang_options(c)}

def options_night(c):
    if term(c) is not None: return {}
    return {st: bite_value(c, -1, st) for st in night_options(c)}
