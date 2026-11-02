# 日ごとに解く（辞書方式）：盤面の状態＝見た目＋内訳の割合＋狼だけが知っていること。
# その日の朝、村は状態に対して進め方の候補から最善を選び、人外は自分の視点で最善を返す。翌日の状態の村勝率は辞書から引く（なければ解いて足す）。
# 状態の村勝率 = Σ（その日の結果で次の状態になる確率 × 次の状態の村勝率）＋（その日のうちに決着する分）。定義上、参照と全部作り直しは一致する。
import itertools, json, os, random, time
from fractions import Fraction as F
from collections import defaultdict
import game10 as GM
from game10 import Game
from plans10 import candidates
import vote3g as G3

BASE = lambda l: l.split('|')[0]   # 区別のための印（|A）を外した見た目
DICT = {}   # 状態のキー → 村勝率（分数）
SAVE_HOOK = None; LAST_SAVE = 0.0
INFO = {}   # 状態のキー → 説明用（最善の進め方など）

def canon(labels, worlds, with_pos=False):
    """状態の正規形：同じ見た目の人の並べ替えで、いちばん小さい形にそろえる。worlds = [(確率, 役, 知っている人)]
    with_pos：（正規形, 新しい並び）を返す（新しい i 番目＝元の pos[i] 番目の人）
    見た目は1文字目（狩A→狩）にもどしてから並べ替え、そのあと、入れ替えても内訳の割合が変わらない人どうしだけを同じ見た目に、
    前の日までの公開の出来事で区別できる人は 狩A・狩B のように別の見た目にする（村も人外も名指しで選べる）"""
    n = len(labels)
    base = [BASE(l) for l in labels]
    order = sorted(range(n), key=lambda i: GM.label_key(base[i]))
    groups = []
    for i in order:
        if groups and base[groups[-1][0]] == base[i]: groups[-1].append(i)
        else: groups.append([i])
    perms = [list(itertools.permutations(g)) for g in groups]
    merged = defaultdict(F)   # 同じ（役, 狼が知っている人）の内訳はまとめる（1/13 と 2/13 のように分かれたままだと、同じ状態が別のキーになる）
    for p, r, know in worlds: merged[(tuple(r), tuple(sorted(know)))] += F(p)
    worlds = [(p, r, kn) for (r, kn), p in merged.items()]
    best = None
    tot = sum(p for p, _, _ in worlds)
    for combo in itertools.product(*perms):
        pos = [i for g in combo for i in g]          # 新しい並び
        inv = {old: new for new, old in enumerate(pos)}
        ws = tuple(sorted((tuple(r[i] for i in pos), tuple(sorted(inv[k] for k in know)), str(F(p) / tot)) for p, r, know in worlds))
        key = (tuple(base[i] for i in pos), ws)
        if best is None or key < best[0]: best = (key, pos)
        if len(perms) and sum(len(x) for x in perms) > 5040: break
    (labs, ws), pos = best
    labs = split_labels(list(labs), ws)
    key = (tuple(labs), ws)
    return (key, pos) if with_pos else key

def split_labels(labs, ws):
    """正規形の内訳 ws を変えない同じ見た目の人の入れ替えだけで行き来できる人を同じ見た目に、そうでない人を A・B… に分ける"""
    n = len(labs)
    idx = defaultdict(list)
    for i, l in enumerate(labs): idx[l].append(i)
    cls = [v for v in idx.values() if len(v) >= 2]
    if not cls: return labs
    S = set(ws)
    parent = list(range(n))
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for combo in itertools.product(*[itertools.permutations(c) for c in cls]):
        sig = list(range(n))
        for c, pc in zip(cls, combo):
            for a, b in zip(c, pc): sig[a] = b
        # 人 i を sig[i] の席に移したときに内訳が同じか
        moved = set()
        for r, kn, p in ws:
            r2 = [None] * n
            for i in range(n): r2[sig[i]] = r[i]
            moved.add((tuple(r2), tuple(sorted(sig[k] for k in kn)), p))
        if moved == S:
            for i in range(n): parent[find(i)] = find(sig[i])
    out = list(labs)
    for c in cls:
        orbits = []
        for i in c:
            if find(i) not in orbits: orbits.append(find(i))
        if len(orbits) > 1:
            for i in c: out[i] = labs[i] + '|' + 'ABCDEFGH'[orbits.index(find(i))]
    return out

def from_key(key):
    labels, ws = key
    return list(labels), [(F(p), r, kn) for r, kn, p in ws]

def value(key):
    if key in DICT: return DICT[key]
    labels, worlds = from_key(key)
    n = sum(1 for l in labels if GM.is_alive_label(l))   # 生存者の数（死んだCO者の見えない席は数えない）
    if n <= 3: v = solve3(labels, worlds)
    else: v = solve_day(key, labels, worlds)
    DICT[key] = v
    global LAST_SAVE
    if SAVE_HOOK and time.time() - LAST_SAVE > 600:   # 盤面の途中でも10分ごとに辞書を保存（止まっても続きから）
        LAST_SAVE = time.time(); SAVE_HOOK()
    return v

def alive3(labels, worlds):
    """3人の状態：生存者だけの見た目と内訳（死んだCO者の見えない席は、この先の投票に関係しないので外してまとめる）"""
    al = [i for i, l in enumerate(labels) if GM.is_alive_label(l)]
    idx = {o: n for n, o in enumerate(al)}
    m = defaultdict(F)
    for p, r, kn in worlds: m[(tuple(r[i] for i in al), tuple(idx[k] for k in kn if k in idx))] += F(p)
    return [labels[i] for i in al], [(p, r, kn) for (r, kn), p in m.items()]

def solve3(labels, worlds):
    labels, worlds = alive3(labels, worlds)
    R = G3.solve_board(labels, cases=[(p, r) for p, r, kn in worlds], extras=[kn for p, r, kn in worlds])
    return R['v'] if R else F(0)

def outcomes(root, pol, exact):
    """方針 pol のもとで：その日のうちの決着分と、翌日の状態ごとの（確率, 世界）"""
    num = (lambda x: x) if exact else float
    term = num(0); nxt = defaultdict(list)
    stack = [(root, num(1))]
    while stack:
        nd, p = stack.pop()
        if p == 0: continue
        if nd.kind == 'L': term += p * (nd.v if exact else float(nd.v))
        elif nd.kind == 'N':
            hist, al, lab, roles, know = nd.info
            nxt[(hist, al, lab)].append((p, roles, know))
        elif nd.kind == 'C':
            for q, c in nd.ch: stack.append((c, p * (q if exact else float(q))))
        else: stack.append((nd.ch[pol.get((nd.agent, nd.info), 0)], p))
    return term, nxt

KICKS = 20   # 行き詰まったあとに手をばらばらに変えて試し直す回数
FCACHE = {}   # 探索中（小数）の翌日の状態 → 村勝率（小数）。同じ状態を何度も正規形にしないため

def total(root, pol, exact=False):
    term, nxt = outcomes(root, pol, exact)
    v = term
    for (hist, al, lab), ws in nxt.items():
        mass = sum(p for p, _, _ in ws)
        idx = {old: new for new, old in enumerate(al)}
        labs = tuple(lab[i] for i in al)
        if not exact:
            fk = (labs, frozenset((tuple(r[i] for i in al), tuple(idx[k] for k in kn), round(p / mass, 12)) for p, r, kn in ws))
            x = FCACHE.get(fk)
            if x is None:
                worlds = [(F(p / mass).limit_denominator(10**9), tuple(r[i] for i in al), tuple(idx[k] for k in kn)) for p, r, kn in ws]
                x = float(value(canon(list(labs), worlds))); FCACHE[fk] = x
            v += mass * x
            continue
        worlds = [(F(p), tuple(r[i] for i in al), tuple(idx[k] for k in kn)) for p, r, kn in ws]
        v += mass * value(canon(list(labs), worlds))
    return v

class Flat:
    """1日分の木を「行き着く先」の並びに平らにして、人外の手を1か所変えたときに、影響する行き先だけを足し引きする（探索を速くする）"""
    def __init__(self, root):
        self.keys = {}; self.opts = []; self.mimic = []   # 情報集合 → 番号、選択肢の数、村人と同じ投票をする手
        self.leaves = []                       # (確率, 条件 [(情報集合番号, 手)], 決着の値 or None, 翌日の状態, 世界)
        stack = [(root, 1.0, ())]
        while stack:
            nd, p, req = stack.pop()
            if p == 0: continue
            if nd.kind == 'L': self.leaves.append((p, req, float(nd.v), None, None))
            elif nd.kind == 'N':
                hist, al, lab, roles, know = nd.info
                idx = {old: new for new, old in enumerate(al)}
                self.leaves.append((p, req, None, (hist, al, lab), (tuple(roles[i] for i in al), tuple(idx[k] for k in know))))
            elif nd.kind == 'C':
                for q, c in nd.ch: stack.append((c, p * float(q), req))
            else:
                k = (nd.agent, nd.info)
                if k not in self.keys: self.keys[k] = len(self.opts); self.opts.append(len(nd.opts)); self.mimic.append(nd.mimic)
                i = self.keys[k]
                for a, c in enumerate(nd.ch): stack.append((c, p, req + ((i, a),)))
        self.by = defaultdict(list)
        for li, (p, req, tv, ok, wd) in enumerate(self.leaves):
            for ia in req: self.by[ia].append(li)
        self.order = list(range(len(self.opts)))

    def setup(self, pol):
        self.pol = list(pol)
        self.term = 0.0; self.mass = defaultdict(lambda: defaultdict(float)); self.labs = {}
        self.active = [False] * len(self.leaves)
        self.contrib = {}; self.sumc = 0.0; self.dirty = set()
        for li, (p, req, tv, ok, wd) in enumerate(self.leaves):
            if all(self.pol[i] == a for i, a in req): self.add(li, 1)
        return self.value()

    def add(self, li, sgn):
        p, req, tv, ok, wd = self.leaves[li]
        self.active[li] = sgn > 0
        if tv is not None: self.term += sgn * p * tv
        else:
            self.mass[ok][wd] += sgn * p
            self.dirty.add(ok)

    def outcome_value(self, ok):
        ws = {w: m for w, m in self.mass[ok].items() if m > 1e-15}
        mass = sum(ws.values())
        if mass <= 1e-15: return 0.0
        hist, al, lab = ok
        labs = tuple(lab[i] for i in al)
        fk = (labs, frozenset((r, kn, round(m / mass, 12)) for (r, kn), m in ws.items()))
        x = FCACHE.get(fk)
        if x is None:
            worlds = [(F(m / mass).limit_denominator(10**9), r, kn) for (r, kn), m in ws.items()]
            x = float(value(canon(list(labs), worlds))); FCACHE[fk] = x
        return mass * x

    def value(self):
        """変わった行き先（dirty）だけ村勝率を求め直す"""
        for ok in self.dirty:
            new = self.outcome_value(ok)
            self.sumc += new - self.contrib.get(ok, 0.0); self.contrib[ok] = new
        self.dirty.clear()
        return self.term + self.sumc

    def change(self, i, a):
        """情報集合 i の手を a に変え、影響した分だけ足し引きする"""
        old = self.pol[i]
        for li in self.by[(i, old)]:
            if self.active[li]: self.add(li, -1)
        self.pol[i] = a
        for li in self.by[(i, a)]:
            p, req, tv, ok, wd = self.leaves[li]
            if all(self.pol[j] == b for j, b in req): self.add(li, 1)

def adversary_min(root, starts=9, kicks=KICKS):
    """人外の最善（村勝率が一番低くなる手）を、1人ずつ手を良くする探索で求める。
    やり直し starts 回。それぞれ、行き詰まったら手をいくつかばらばらに変えてまた良くする（kicks 回）。良くならなければ元に戻す"""
    fl = Flat(root)
    n = len(fl.opts)
    best = None
    def descend(order, cur):
        improved = True
        while improved:
            improved = False
            for i in order:
                for a in range(fl.opts[i]):
                    old = fl.pol[i]
                    if a == old: continue
                    fl.change(i, a)
                    v = fl.value()
                    if v < cur - 1e-12: cur = v; improved = True
                    else: fl.change(i, old)
        return cur
    for s in range(starts):
        rnd = random.Random(s)
        # 1回目は「人外が村人と同じ投票をする（正体を隠す）」手から、2回目以降はばらばらの手から
        pol = list(fl.mimic) if s == 0 else [rnd.randrange(fl.opts[i]) for i in range(n)]
        cur = fl.setup(pol)
        # 見る順番：前から・後ろから・ばらばら（順番しだいで行き着く手が変わるので、いくつか試して一番低いものを取る）
        order = list(range(n)) if s % 3 == 0 else (list(range(n))[::-1] if s % 3 == 1 else rnd.sample(range(n), n))
        cur = descend(order, cur)
        many = [i for i in range(n) if fl.opts[i] > 1]
        for _ in range(kicks if many else 0):
            keep = list(fl.pol)
            for i in rnd.sample(many, min(len(many), rnd.randint(1, 3))):
                fl.change(i, rnd.randrange(fl.opts[i]))
            v = descend(rnd.sample(range(n), n), fl.value())
            if v < cur - 1e-12: cur = v
            else:
                for i in range(n):
                    if fl.pol[i] != keep[i]: fl.change(i, keep[i])
        if best is None or cur < best[0] - 1e-12:
            best = (cur, {k: fl.pol[i] for k, i in fl.keys.items()})
    return best

def solve_day(key, labels, worlds):
    start = [(p, r, kn) for p, r, kn in worlds]
    # 1段目：全候補を、人外の探索1回でふるう（人外の最善を見逃すと値は高めに出るので、上位を取りこぼしにくい）
    scr = []
    for plan in candidates(labels):
        GM.MODE.update(exact=False, tags=False)   # 探索は小数の木で
        g = Game(labels, plan, start=start); root, _ = g.root()
        vf, pol = adversary_min(root, starts=1, kicks=0)   # 1段目は崩しての探し直しなし（2段目の1回目はこれと同じ探索から始まるので、2段目の値はこれ以下）
        scr.append((vf, plan))
    scr.sort(key=lambda x: -x[0])
    # 2段目：1段目の値の高い順に、やり直し9回で詰め直す。9回のうち1回目は1段目と同じ探索なので、詰め直した値は1段目の値以下。
    # よって1段目の値がここまでの最善以下になったら、残りの候補が最善を超えることはない（全候補を9回ずつ探索した最大と一致する）
    best = None; bestf = None
    for vf0, plan in scr:
        if bestf is not None and vf0 <= bestf + 1e-12: break
        GM.MODE.update(exact=False, tags=False)
        g = Game(labels, plan, start=start); root, _ = g.root()
        vf, pol = adversary_min(root)
        if best is not None and vf < float(best[0]) - 1e-9: continue
        GM.MODE.update(exact=True, tags=False)    # 値は分数の木で厳密に
        root, _ = g.root()
        v = total(root, pol, exact=True)
        if best is None or v > best[0]: best = (v, plan, pol)
        bestf = vf if bestf is None else max(bestf, vf)
    INFO[key] = dict(plan=best[1])
    return best[0]

def sit_name(w, k):
    return f'{w}w' + ('1k' if k else '') + '生存'

def board_keys(board):
    """盤面の、生存状況（狼の数・狂人の生死）ごとの状態キー {生存状況: キー}。生存状況は全員が知っている（wiki と同じ）。
    割合は役の札の数から。狩人・猫又が灰にいるかは分からない"""
    ws = GM.worlds(board)
    by = {}
    for w, roles in ws:
        by.setdefault(GM.situation(board, roles), []).append((F(w), roles, ()))
    return {s: canon(board, lst) for s, lst in sorted(by.items(), key=lambda kv: (kv[0][0], '1k' not in kv[0], kv[0]))}

def board_key(board):
    """（参考）生存状況を分けない盤面の状態キー"""
    ws = GM.worlds(board)
    return canon(board, [(F(w), roles, ()) for w, roles in ws])
