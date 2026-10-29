# 盤面（1人ずつの見え方の並び）と条件（ありうる内訳）から、村の最善進行と村勝率を厳密に求める。
#
# ・ケース：条件に書いた内訳（「または」で並べたもの）は等確率、各内訳の中で灰の役の並びは等確率。
# ・村：公開情報（吊り・噛み・GJ・占い結果・霊能結果・狩人CO）が同じなら、どの内訳でも同じ手を打つ。
#       毎日の吊り先は村が話し合いで決める（人外が過半数ならPP）。GJの朝、潜伏狩人がCOするかも村の手。
# ・人外（狼＋狂人）：お互いを知っていて、公開情報と自分たちの噛み先から手を決める（狩人・本物の占い師の位置は知らない）。
#       噛み先、偽の占い結果、偽の霊能結果、狩人COへの対抗COを選ぶ。
# ・本物の占い師は毎晩まだ占っていない灰からランダムに占う。狩人は 占いCO者 > 霊能CO者 > 確定白 > ほかの人 から護衛（同順位はランダム）。
# ・村の勝率を最大化／人外が最小化するゲームを sequence form の線形計画で解く。
from fractions import Fraction as F
from itertools import permutations, product
import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix

ROLE_NAME = {'V': '村人', 'H': '狩人', 'X': '狂人', 'W': '狼', 'S': '占い師', 'M': '霊能者'}

class Node:
    __slots__ = ('kind', 'children', 'payoff', 'info', 'case', 'ev', 'vseq', 'aseq', 'alabel', 'vlabel')
    def __init__(self, kind, case, ev=None, info=None, payoff=None):
        self.kind = kind; self.case = case; self.ev = ev; self.info = info; self.payoff = payoff
        self.children = []   # [(確率 or 手, 子)]
        self.alabel = None; self.vlabel = None

def expand_cases(board):
    """[(重み, 内訳番号, 役の並び)]"""
    labels = board['labels']; out = []
    alts = board['cases']; wa = F(1, len(alts))
    for ai, alt in enumerate(alts):
        fl = alt.get('fixed', {}); fl = fl if isinstance(fl, list) else [fl]   # 固定の並びを複数（どちらが真か不明など）
        for fixed in fl:
            free = [i for i in range(len(labels)) if i not in fixed]
            pool = []
            for r, k in alt['gray'].items(): pool += [r] * k
            assert len(pool) == len(free), (alt, pool, free)
            perms = sorted(set(permutations(pool)))
            for pm in perms:
                roles = [None] * len(labels)
                for i, r in fixed.items(): roles[i] = r
                for i, r in zip(free, pm): roles[i] = r
                out.append((wa / len(fl) / len(perms), ai, tuple(roles)))
    return out

class St:
    __slots__ = ('alive', 'div', 'last', 'hco', 'day', 'vh', 'ah')
    def __init__(self, **kw):
        for k, v in kw.items(): setattr(self, k, v)
    def but(self, **kw):
        d = {k: getattr(self, k) for k in self.__slots__}; d.update(kw); return St(**d)

class Game:
    def __init__(self, board, force_root=None):
        self.b = board; self.labels = board['labels']; self.n0 = len(self.labels)
        self.cases = expand_cases(board)
        self.vinfo = {}; self.ainfo = {}   # 情報集合 → (親の手順, 手の一覧)
        self.root = Node('C', None)
        for ci, (w, ai, roles) in enumerate(self.cases):
            st = St(alive=frozenset(range(self.n0)), div=frozenset(), last=None,
                    hco=frozenset(i for i, l in enumerate(self.labels) if l == '狩'), day=1, vh=(), ah=())
            self.cur = (ci, roles)
            self.root.children.append((w, self.day(st, (), ())))

    # ---- 共通
    def term(self, alive):
        roles = self.cur[1]
        w = sum(1 for i in alive if roles[i] == 'W')
        if w == 0: return F(1)
        if 2 * w >= len(alive): return F(0)
        return None

    def leaf(self, v, ev, vs, as_):
        nd = Node('L', self.cur[0], ev=ev, payoff=v); nd.vseq = vs; nd.aseq = as_; return nd

    def vnode(self, info, acts, vs, as_, ev=None):
        nd = Node('V', self.cur[0], ev=ev, info=info); nd.vseq = vs; nd.aseq = as_
        old = self.vinfo.setdefault(info, (vs, tuple(acts)))
        assert old == (vs, tuple(acts)), ('village perfect recall', info, old, vs, acts)
        return nd

    def anode(self, info, acts, vs, as_, ev=None):
        nd = Node('A', self.cur[0], ev=ev, info=info); nd.vseq = vs; nd.aseq = as_
        old = self.ainfo.setdefault(info, (as_, tuple(acts)))
        assert old == (as_, tuple(acts)), ('adversary perfect recall', info, old, as_, acts)
        return nd

    def cnode(self, vs, as_, ev=None):
        nd = Node('C', self.cur[0], ev=ev); nd.vseq = vs; nd.aseq = as_; return nd

    def nm(self, st, i, role=True):
        """表示名：見え方（＋占い結果の印・狩人CO）＋（中身）"""
        base = self.labels[i]
        if i in st.hco and base != '狩': base = '狩CO'
        marks = ''.join('○' if e[3] == 'o' else '●' for e in st.vh if e[0] == 'seer' and e[2] == i)
        r = self.cur[1][i]
        return base + marks + (f'({ROLE_NAME[r]})' if role else '')

    def advkey(self, st):
        roles = self.cur[1]
        return (tuple(i for i in range(self.n0) if roles[i] == 'W'), tuple(i for i in range(self.n0) if roles[i] == 'X'), st.vh, st.ah)

    # ---- 昼
    def day(self, st, vs, as_, ev=None):
        roles = self.cur[1]
        t = self.term(st.alive)
        if t is not None: return self.leaf(t, ev, vs, as_)
        n = len(st.alive); w = sum(1 for i in st.alive if roles[i] == 'W')
        mad = any(roles[i] == 'X' for i in st.alive)
        if mad and n >= 5 and 2 * (w + 1) >= n:
            if 2 * (w + 1) > n: return self.leaf(F(0), (ev or ()) + ('PP（人外が過半数）',), vs, as_)
            c = self.cnode(vs, as_, ev)
            c.children.append((F(1, 2), self.leaf(F(0), ('PP：決選で人外の吊りが通る',), vs, as_)))
            c.children.append((F(1, 2), self.day_vote(st, vs, as_, ('PP：決選で村の吊りが通る',))))
            return c
        return self.day_vote(st, vs, as_, ev)

    def day_vote(self, st, vs, as_, ev):
        info = ('D', st.vh)
        acts = sorted(st.alive)
        nd = self.vnode(info, acts, vs, as_, ev)
        nd.vlabel = {a: self.nm(st, a, role=False) for a in acts}
        for a in acts:
            vs2 = vs + ((info, a),)
            st2 = st.but(alive=st.alive - {a}, last=a, vh=st.vh + (('hang', a),))
            t = self.term(st2.alive)
            e = (f'{st.day}日目 {self.nm(st, a)}を吊る',)
            ch = self.leaf(t, e, vs2, as_) if t is not None else self.night(st2, vs2, as_, e)
            nd.children.append((a, ch))
        return nd

    # ---- 夜
    def guard_dist(self, st):
        roles = self.cur[1]
        h = next((i for i in st.alive if roles[i] == 'H'), None)
        if h is None: return None, []
        o = [i for i in sorted(st.alive) if i != h]
        for cond in (lambda i: self.labels[i] == '占', lambda i: self.labels[i] == '霊', lambda i: self.labels[i] == '白', lambda i: True):
            tg = [i for i in o if cond(i)]
            if tg: return h, [(F(1, len(tg)), i) for i in tg]
        return h, []

    def night(self, st, vs, as_, ev):
        roles = self.cur[1]
        al = sorted(st.alive)
        bites = [i for i in al if roles[i] not in 'WX']
        fsr = [i for i in al if self.labels[i] == '占' and roles[i] in 'WX']
        fmd = [i for i in al if self.labels[i] == '霊' and roles[i] in 'WX'] if st.last is not None else []
        acts = []
        for b in bites:
            fo = [[(s, j, c) for j in al if j != s and j != b for c in ('o', 'x')] for s in fsr]
            mo = [[(m, c) for c in ('o', 'x')] for m in fmd]
            for fk in product(*fo):
                for mk in product(*mo):
                    acts.append((b, fk, mk))
        info = ('N', self.advkey(st))
        nd = self.anode(info, acts, vs, as_, ev)
        mk_ = lambda c: '○' if c == 'o' else '●'
        nd.alabel = {a: '・'.join([f'{self.nm(st, a[0])}を噛む'] + [f'{self.nm(st, s_)}→{self.nm(st, j)}{mk_(c)}' for s_, j, c in a[1]]
                                  + [f'{self.nm(st, m)}→{self.nm(st, st.last)}{mk_(c)}' for m, c in a[2]]) for a in acts}
        for a in acts:
            nd.children.append((a, self.night_chance(st, vs, as_ + ((info, a),), a)))
        return nd

    def night_chance(self, st, vs, as_, act):
        roles = self.cur[1]
        b, fk, mk = act
        h, gd = self.guard_dist(st)
        gj = F(0) if h is None else sum((q for q, i in gd if i == b), F(0))
        c = self.cnode(vs, as_)
        for ok, pr in ((True, gj), (False, 1 - gj)):
            if pr == 0: continue
            al2 = st.alive if ok else st.alive - {b}
            e0 = (f'{st.day}夜 GJ（{self.nm(st, b)}への噛み）',) if ok else (f'{st.day}夜 {self.nm(st, b)}が噛まれる',)
            p0 = (('gj',),) if ok else (('dead', b),)
            seer = next((i for i in al2 if roles[i] == 'S'), None)
            outs = [(pr, (), st.div)]
            if seer is not None:
                cand = [j for j in sorted(al2) if j != seer and j not in st.div and self.labels[j] == '灰' and j not in st.hco]
                if cand:
                    outs = [(pr / len(cand), (('seer', seer, j, 'x' if roles[j] == 'W' else 'o'),), st.div | {j}) for j in cand]
            for q, es, dv in outs:
                pub = p0 + es + tuple(('seer', s, j, cc) for s, j, cc in fk if s in al2)
                med = next((i for i in al2 if roles[i] == 'M'), None)
                if med is not None and st.last is not None:
                    pub += (('med', med, 'x' if roles[st.last] == 'W' else 'o'),)
                pub += tuple(('med', m, cc) for m, cc in mk if m in al2)
                mk_ = lambda c: '○' if c == 'o' else '●'
                e = e0 + tuple(f'{self.nm(st, x[1])}→{self.nm(st, x[2])}{mk_(x[3])}' for x in pub if x[0] == 'seer') \
                       + tuple(f'{self.nm(st, x[1])}→{self.nm(st, st.last)}{mk_(x[2])}' for x in pub if x[0] == 'med')
                st2 = st.but(alive=al2, div=dv, last=None, day=st.day + 1, vh=st.vh + pub,
                             ah=st.ah + ((b,),) if ok else st.ah)
                t = self.term(al2)
                ch = self.leaf(t, e, vs, as_) if t is not None else self.morning(st2, vs, as_, e, ok, b)
                c.children.append((q, ch))
        return c

    # ---- 朝：GJなら潜伏狩人がCOするか（村の手）→ COなら人外が対抗COするか
    def morning(self, st, vs, as_, ev, ok, b):
        roles = self.cur[1]
        h = next((i for i in st.alive if roles[i] == 'H'), None)
        if not (ok and h is not None and not st.hco):
            return self.day(st, vs, as_, ev)
        info = ('CO', st.vh)
        nd = self.vnode(info, ['no', 'co'], vs, as_, ev)
        nd.children.append(('no', self.day(st.but(vh=st.vh + (('hide',),)), vs + ((info, 'no'),), as_, ('狩人は潜伏',))))
        vs2 = vs + ((info, 'co'),)
        st2 = st.but(hco=frozenset([h]), vh=st.vh + (('hco', h, b),))
        ws = [i for i in sorted(st.alive) if roles[i] == 'W' and self.labels[i] == '灰']
        if not ws:
            nd.children.append(('co', self.day(st2, vs2, as_, (f'{self.nm(st, h)}が狩人CO',))))
            return nd
        ai = ('CC', self.advkey(st2))
        acts = ['none'] + ws
        an = self.anode(ai, acts, vs2, as_, (f'{self.nm(st, h)}が狩人CO',))
        an.alabel = {a: ('対抗COしない' if a == 'none' else f'{self.nm(st, a)}が対抗CO') for a in acts}
        for a in acts:
            as2 = as_ + ((ai, a),)
            if a == 'none': an.children.append((a, self.day(st2, vs2, as2, ('対抗COなし',))))
            else:
                st3 = st2.but(hco=frozenset([h, a]), vh=st2.vh + (('hco2', a),))
                an.children.append((a, self.day(st3, vs2, as2, (f'{self.nm(st, a)}が対抗の狩人CO',))))
        nd.children.append(('co', an))
        return nd

# ---------------------------------------------------------------- 線形計画
def collect_leaves(root):
    out = []
    stack = [(root, F(1))]
    while stack:
        nd, p = stack.pop()
        if nd.kind == 'L':
            if nd.payoff: out.append((p * nd.payoff, nd.vseq, nd.aseq))
            continue
        for e, ch in nd.children:
            stack.append((ch, p * e if nd.kind == 'C' else p))
    return out

def solve(g, fix=None, refine=True):
    """fix = {(村の情報集合, 手): 1} で村の手を固定。戻り値：(値, 村の手順ごとの重み)"""
    vseqs = [()]
    for info, (par, acts) in g.vinfo.items(): vseqs += [par + ((info, a),) for a in acts]
    aseqs = [()]
    for info, (par, acts) in g.ainfo.items(): aseqs += [par + ((info, a),) for a in acts]
    vi = {s: k for k, s in enumerate(vseqs)}; ai = {s: k for k, s in enumerate(aseqs)}
    ainf = ['root'] + list(g.ainfo); aqi = {k: j for j, k in enumerate(ainf)}
    NV, NQ, NA = len(vseqs), len(ainf), len(aseqs)
    # 変数：[x (NV), q (NQ)]
    rows, cols, vals = [], [], []
    for p, vs, as_ in collect_leaves(g.root):
        rows.append(ai[as_]); cols.append(vi[vs]); vals.append(-float(p))
    for s in aseqs:   # q_{J(s)} − Σ_{J: 親=s} q_J − (Aᵀx)_s ≤ 0
        J = 'root' if not s else s[-1][0]
        rows.append(ai[s]); cols.append(NV + aqi[J]); vals.append(1.0)
    for info, (par, acts) in g.ainfo.items():
        rows.append(ai[par]); cols.append(NV + aqi[info]); vals.append(-1.0)
    Aub = coo_matrix((vals, (rows, cols)), shape=(NA, NV + NQ)).tocsr()
    er, ec, ev = [0], [0], [1.0]; beq = [1.0]; r = 1
    for info, (par, acts) in g.vinfo.items():
        er.append(r); ec.append(vi[par]); ev.append(-1.0)
        for a in acts: er.append(r); ec.append(vi[par + ((info, a),)]); ev.append(1.0)
        beq.append(0.0); r += 1
    for (info, a), val in (fix or {}).items():
        par = g.vinfo[info][0]
        er.append(r); ec.append(vi[par + ((info, a),)]); ev.append(1.0); beq.append(float(val)); r += 1
    Aeq = coo_matrix((ev, (er, ec)), shape=(r, NV + NQ)).tocsr()
    c = np.zeros(NV + NQ); c[NV + aqi['root']] = -1
    bounds = [(0, 1)] * NV + [(None, None)] * NQ
    res = linprog(c, A_ub=Aub, b_ub=np.zeros(NA), A_eq=Aeq, b_eq=beq, bounds=bounds, method='highs')
    assert res.status == 0, res.message
    val = -res.fun
    if not refine: return val, {s: res.x[vi[s]] for s in vseqs}
    # 2段目：勝率 val を保ったまま、人外がでたらめに打ったときの村勝率も最大にする（最善から外れた局面でも村がまともに打つように）
    acts_n = {info: len(acts) for info, (par, acts) in g.ainfo.items()}
    c2 = np.zeros(NV + NQ)
    for p, vs, as_ in collect_leaves(g.root):
        u = 1.0
        for info, a in as_: u /= acts_n[info]
        c2[vi[vs]] -= float(p) * u
    row = coo_matrix(([-1.0], ([0], [NV + aqi['root']])), shape=(1, NV + NQ))
    from scipy.sparse import vstack
    res2 = linprog(c2, A_ub=vstack([Aub, row]).tocsr(), b_ub=np.concatenate([np.zeros(NA), [-(val - 1e-9)]]),
                   A_eq=Aeq, b_eq=beq, bounds=bounds, method='highs')
    if res2.status == 0: res = res2
    x = {s: res.x[vi[s]] for s in vseqs}
    return val, x

def behaviour(g, x):
    """村の行動戦略：情報集合 → {手: 確率（分数に丸め）}"""
    out = {}
    for info, (par, acts) in g.vinfo.items():
        tot = x[par]
        if tot < 1e-9: continue
        ps = {a: F(x[par + ((info, a),)] / tot).limit_denominator(64) for a in acts}
        ps = {a: p for a, p in ps.items() if p > 0}
        s = sum(ps.values()); out[info] = {a: p / s for a, p in ps.items()}
    return out

def exact_eval(g, beh):
    """村の戦略を固定し、人外の最善応答（情報集合ごと）を厳密に求める。戻り値：(値, 人外の手, ノード値)"""
    # 各ノードの到達確率（偶然×村）と、人外の情報集合ごとのノード一覧
    reach = {}; byinfo = {}; order = []
    stack = [(g.root, F(1))]
    while stack:
        nd, p = stack.pop()
        reach[id(nd)] = p; order.append(nd)
        if nd.kind == 'A': byinfo.setdefault(nd.info, []).append(nd)
        for e, ch in nd.children:
            if nd.kind == 'C': q = p * e
            else: q = p
            stack.append((ch, q))
    adv = {}
    val = {}
    def v(nd):
        k = id(nd)
        if k in val: return val[k]
        if nd.kind == 'L': r = nd.payoff
        elif nd.kind == 'C': r = sum((e * v(ch) for e, ch in nd.children), F(0))
        elif nd.kind == 'V':
            bh = beh.get(nd.info)
            if bh is None: bh = {nd.children[0][0]: F(1)}   # 到達しない情報集合
            r = sum((bh.get(e, F(0)) * v(ch) for e, ch in nd.children), F(0))
        else:
            a = adv[nd.info]; r = next(v(ch) for e, ch in nd.children if e == a)
        val[k] = r; return r
    infos = sorted(byinfo, key=lambda I: -len(g.ainfo[I][0]))
    for I in infos:
        best = None
        for a in g.ainfo[I][1]:
            tot = F(0)
            for nd in byinfo[I]:
                if reach[id(nd)] == 0: continue
                ch = next(c for e, c in nd.children if e == a)
                tot += reach[id(nd)] * v(ch)
            if best is None or tot < best[0]: best = (tot, a)
        adv[I] = best[1]
    return v(g.root), adv, v

def case_values(g, val):
    nalt = len(g.b['cases']); out = [F(0)] * nalt; wsum = [F(0)] * nalt
    for (w, ch), (_, ai, _) in zip(g.root.children, g.cases):
        out[ai] += w * val(ch); wsum[ai] += w
    return [o / s for o, s in zip(out, wsum)]

# ---------------------------------------------------------------- 対称化
# 同じ見え方の人を入れ替えてもゲームは変わらないので、村の手順の重みを入れ替えの平均にしても最善のまま。
# 線形計画が返す「最善の中の偏った1点」を、入れ替えに対して公平な点（灰からランダム、など）にそろえる。
def _pm_ev(e, p):
    t = e[0]
    if t in ('hang', 'dead', 'hco2'): return (t, p[e[1]]) + e[2:]
    if t == 'seer': return (t, p[e[1]], p[e[2]], e[3])
    if t == 'med': return (t, p[e[1]], e[2])
    if t == 'hco': return (t, p[e[1]], p[e[2]])
    return e

def _pm_seq(seq, p):
    out = []
    for (kind, vh), a in seq:
        out.append(((kind, tuple(_pm_ev(e, p) for e in vh)), p[a] if isinstance(a, int) else a))
    return tuple(out)

def symmetrize(g, x, cap=800):
    from itertools import permutations, product
    cls = {}
    for i, l in enumerate(g.labels): cls.setdefault(l, []).append(i)
    groups = [list(permutations(v)) for v in cls.values()]
    total = 1
    for gg in groups: total *= len(gg)
    if total == 1 or total > cap: return x
    perms = []
    for combo in product(*groups):
        p = list(range(g.n0))
        for src, dst in zip(cls.values(), combo):
            for a, b in zip(src, dst): p[a] = b
        perms.append(p)
    out = {s: 0.0 for s in x}
    for s, w in x.items():
        if w < 1e-12: continue
        for p in perms:
            t = _pm_seq(s, p)
            if t in out: out[t] += w / total
    return out
