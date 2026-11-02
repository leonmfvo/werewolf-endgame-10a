# 10a狩（占い・霊能・狩人・狼2・狂人・村人4）の1日分のゲーム木：12A猫（werewolf-endgame-12a-3 の compute/game.py）と同じ前提で解く。
#
# 前提：生存状況（狼の数・狂人の生死・本物の狩人の生死）は全員が知っている。誰がどの役かは自分の役しか分からない（狼どうしは仲間を知る。狂人は狼を知らない）。
#       投票は公開・最多票を吊る（同票はランダム）。狩人は毎晩1人を護衛（連続護衛あり）。GJの翌朝、狩人はCOして護衛先を出せる（村の進め方の一部）。
#       本物の占い師は毎晩1人を占い、朝に結果（○白／●黒）を出す。偽の占いCO者（狂人・狼）は、誰に白／黒を出すかを選ぶ。
#       本物の霊能者は前の日に吊られた人の色を出す。偽の霊能CO者は色を選ぶ。噛まれた占い師・霊能者は結果を出せない。
#       PP：5人以上・狂人が生きていて人外が過半数なら狼の勝ち（同数なら半々）。狼が全滅で村、狼が半数以上で狼の勝ち。
#
# 盤面の見た目（ラベル）：占a・占b✕（✕は破綻）・霊a・狩・確白・灰、結果の印 黒a白b（占aの●・占bの○）。確白(白a) のように括弧で印を書く。
# 死んだ占い・霊能CO者は「†占a」のような見えない席として持つ（本物かどうかで、その人が出した結果を信じてよいかが変わる）。
# 公開の出来事で区別できる同じ見た目の人は「白a|A」「白a|B」のように分ける（daily10.canon）。
import itertools, re
from fractions import Fraction as F
from collections import defaultdict

ROLES = {'S': 1, 'M': 1, 'H': 1, 'X': 1, 'W': 2, 'V': 4}
VILL = set('SMHV')

# ---------------------------------------------------------------- ラベル
def parse(l):
    """ラベル → dict(kind, let, broken, conf, marks)。kind：'占' '霊' '狩' '確白' '' '†占' '†霊'。marks：{(文字, '白'/'黒')}"""
    l = l.split('|')[0]
    m = re.match(r'^(†?)(占|霊)([a-c]?)(✕?)(?:\((.*)\))?$', l)
    if m:
        return dict(kind=m.group(1) + m.group(2), let=m.group(3), broken=bool(m.group(4)), conf=False, marks=marks_of(m.group(5) or ''))
    m = re.match(r'^(狩|確白)(?:\((.*)\))?$', l)
    if m: return dict(kind=m.group(1), let='', broken=False, conf=(m.group(1) == '確白'), marks=marks_of(m.group(2) or ''))
    if l == '灰': return dict(kind='', let='', broken=False, conf=False, marks=frozenset())
    return dict(kind='', let='', broken=False, conf=False, marks=marks_of(l))

def marks_of(s):
    out = set(); col = None
    for ch in s:
        if ch in '白黒': col = ch
        elif ch in 'abc_': out.add(('' if ch == '_' else ch, col))
    if s in ('白', '黒'): out.add(('', s))
    return frozenset(out)

def mark_str(marks):
    s = ''
    for col in ('黒', '白'):
        ls = sorted(x for x, c in marks if c == col)
        if ls: s += col + ''.join(ls)
    return s

def compose(p):
    ms = mark_str(p['marks'])
    if p['kind'] in ('占', '霊', '†占', '†霊'):
        return p['kind'] + p['let'] + ('✕' if p['broken'] else '') + (f'({ms})' if ms else '')
    if p['kind'] in ('狩', '確白'): return p['kind'] + (f'({ms})' if ms else '')
    return ms or '灰'

def is_alive_label(l): return not l.startswith('†')

CAN = {'占': 'SXW', '霊': 'MXW', '狩': 'HXW', '確白': 'VHX', '': 'VHXW', '†占': 'SXW', '†霊': 'MXW'}

def weight(roles):
    cnt = defaultdict(int); w = 1
    for r in roles:
        w *= ROLES[r] - cnt[r]; cnt[r] += 1
    return w

def consistent(labels, roles):
    """役の割り振りが見た目と矛盾しないか（本物の占い師の結果は正しい、など）"""
    P = [parse(l) for l in labels]
    if any(roles.count(r) > ROLES[r] for r in ROLES): return False
    for p, r in zip(P, roles):
        if r not in CAN[p['kind']]: return False
        if p['broken'] and r in 'SM': return False
    seers = [i for i, p in enumerate(P) if p['kind'] in ('占', '†占')]
    meds = [i for i, p in enumerate(P) if p['kind'] in ('霊', '†霊')]
    # 本物の占い師・霊能者はCOしている（CO者がいれば、その中にちょうど1人。全員破綻なら本物は死亡済み）
    if seers and not all(P[i]['broken'] for i in seers) and sum(1 for i in seers if roles[i] == 'S') != 1: return False
    if meds and not all(P[i]['broken'] for i in meds) and sum(1 for i in meds if roles[i] == 'M') != 1: return False
    if any(r in 'SM' and P[i]['kind'] not in ('占', '霊', '†占', '†霊') for i, r in enumerate(roles)): return False
    # 狩人COが1人なら本物。狩人COがいれば本物の狩人は灰・確白にいない
    hc = [i for i, p in enumerate(P) if p['kind'] == '狩']
    if len(hc) == 1 and roles[hc[0]] != 'H': return False
    if hc and any(r == 'H' and P[i]['kind'] != '狩' for i, r in enumerate(roles)): return False
    # 本物の占い師の結果は正しい
    tl = [P[i]['let'] for i in seers if roles[i] == 'S']
    for p, r in zip(P, roles):
        for x, col in p['marks']:
            if x in tl:
                if col == '白' and r == 'W': return False
                if col == '黒' and r != 'W': return False
    # 生きている狼の数から、死んだ偽CO者に回せる狼・狂人が足りるか
    alive = [i for i, l in enumerate(labels) if is_alive_label(l)]
    w_alive = sum(1 for i in alive if roles[i] == 'W')
    return 2 * w_alive < len(alive) and w_alive > 0

def worlds(labels):
    """[(重み, 役の並び)]：見た目と矛盾しない役の割り振り全部（生存状況はまだ分けない）"""
    opts = [CAN[parse(l)['kind']] for l in labels]
    out = []
    for roles in itertools.product(*opts):
        if consistent(labels, roles): out.append((weight(roles), roles))
    return out

def situation(labels, roles, alive=None):
    """生存状況（全員が知っている）：1w1k生存（狩生存）"""
    alive = [i for i, l in enumerate(labels) if is_alive_label(l)] if alive is None else alive
    w = sum(1 for i in alive if roles[i] == 'W'); x = any(roles[i] == 'X' for i in alive)
    lone = sum(1 for i in alive if parse(labels[i])['kind'] == '狩') == 1
    h = any(roles[i] == 'H' and not (parse(labels[i])['kind'] == '狩' and lone) for i in alive)
    return f'{w}w' + ('1k' if x else '') + '生存' + ('（狩生存）' if h else '')

# ---------------------------------------------------------------- 木
class Node:
    __slots__ = ('kind', 'ch', 'v', 'info', 'agent', 'opts', 'tag', 'fch', 'fv', 'mimic')
    def __init__(self, kind, **kw):
        self.kind = kind; self.ch = None; self.v = None; self.info = None; self.agent = None; self.opts = None; self.tag = None; self.mimic = 0
        self.fch = None; self.fv = None
        for k, x in kw.items(): setattr(self, k, x)

MODE = {'exact': True, 'tags': True}
def leaf(v): return Node('L', v=F(v) if MODE['exact'] else float(v))
def tagged(tag, node):
    if not MODE['tags']: return node
    return Node('C', ch=[(F(1) if MODE['exact'] else 1.0, node)], tag=tag)
def chance(lst):
    lst = [(p, c) for p, c in lst if p > 0]
    if len(lst) == 1: return lst[0][1]
    if not MODE['exact']: lst = [(float(p), c) for p, c in lst]
    return Node('C', ch=lst)

KIND_ORDER = ['占', '霊', '狩', '確白', '']
def label_key(l):
    p = parse(l); return (KIND_ORDER.index(p['kind']) if p['kind'] in KIND_ORDER else 9, l)

class Game:
    """plan: dict(des=(区分…), counter, mode, guard=(区分…), co, div=(区分…))。start：[(確率, 役, 狼が知っている人)]"""
    def __init__(self, labels, plan, start):
        self.board = list(labels); self.plan = plan; self.n = len(labels); self.start = start

    def root(self):
        alive = tuple(i for i, l in enumerate(self.board) if is_alive_label(l))
        st0 = dict(alive=alive, lab=tuple(self.board), hist=())
        cv = (lambda x: x) if MODE['exact'] else float
        return Node('C', ch=[(cv(p), self.day(roles, dict(st0, bites=tuple(know)))) for p, roles, know in self.start]), None

    def wins(self, roles, alive):
        w = sum(1 for i in alive if roles[i] == 'W')
        if w == 0: return F(1)
        if 2 * w >= len(alive): return F(0)
        return None

    # ---- 昼
    def day(self, roles, st):
        alive = st['alive']
        t = self.wins(roles, alive)
        if t is not None: return leaf(t)
        n = len(alive); w = sum(1 for i in alive if roles[i] == 'W')
        if any(roles[i] == 'X' for i in alive) and n >= 5 and 2 * (w + 1) >= n:
            if 2 * (w + 1) > n: return leaf(0)
            return chance([(F(1, 2), leaf(0)), (F(1, 2), self.vote(roles, st))])
        return self.vote(roles, st)

    def classes(self, st):
        out = defaultdict(list)
        for i in st['alive']: out[st['lab'][i]].append(i)
        return out

    def designations(self, st):
        cl = self.classes(st)
        for l in self.plan['des']:
            if cl.get(l): return [(F(1, len(cl[l])), d) for d in cl[l]]
        rest = list(st['alive'])
        return [(F(1, len(rest)), d) for d in rest]

    def village_vote(self, st, i, d):
        lab = st['lab']; cl = self.classes(st); me = parse(lab[i])
        if self.plan.get('counter') and me['kind'] in ('占', '霊', '狩'):
            mine = [j for j in st['alive'] if j != i and parse(lab[j])['kind'] == me['kind']]
            if mine: return {j: F(1, len(mine)) for j in mine}
        if d is not None and i != d: return {d: F(1)}
        for l in self.plan['des']:
            c = [j for j in cl.get(l, []) if j != i]
            if c: return {j: F(1, len(c)) for j in c}
        c = [j for j in st['alive'] if j != i]
        return {j: F(1, len(c)) for j in c}

    def vote(self, roles, st):
        if self.plan.get('mode') == 'spread': return self.vote_d(roles, st, None)
        return chance([(pd, self.vote_d(roles, st, d)) for pd, d in self.designations(st)])

    def groups(self, st, i, d=None, excl=None):
        g = defaultdict(list)
        for j in st['alive']:
            if j == i or (excl and j in excl): continue
            g[(st['lab'][j], j == d)].append(j)
        return [tuple(v) for k, v in sorted(g.items(), key=lambda kv: (label_key(kv[0][0]), not kv[0][1]))]

    def vote_d(self, roles, st, d):
        alive = st['alive']
        vill = {i: self.village_vote(st, i, d) for i in alive if roles[i] in VILL}
        wolves = tuple(i for i in alive if roles[i] == 'W'); mad = [i for i in alive if roles[i] == 'X']
        like = lambda i, gs: max(range(len(gs)), key=lambda a: sum(self.village_vote(st, i, d).get(j, 0) for j in gs[a]))
        wopts = list(itertools.product(*[self.groups(st, i, d) for i in wolves]))
        wnode = Node('A', agent='W', info=('V', st['hist'], st['lab'], wolves, st['bites'], d), opts=wopts, ch=[])
        wnode.mimic = wopts.index(tuple(self.groups(st, i, d)[like(i, self.groups(st, i, d))] for i in wolves))
        for wv in wopts:
            wd = {i: {j: F(1, len(g)) for j in g} for i, g in zip(wolves, wv)}
            if mad:
                m = mad[0]; mo = self.groups(st, m, d)
                mnode = Node('A', agent='X', info=('V', st['hist'], st['lab'], m, d), opts=mo, ch=[])
                mnode.mimic = like(m, mo)
                for g in mo: mnode.ch.append(self.resolve(roles, st, vill, wd | {m: {j: F(1, len(g)) for j in g}}))
                wnode.ch.append(mnode)
            else:
                wnode.ch.append(self.resolve(roles, st, vill, wd))
        return wnode

    def resolve(self, roles, st, vill, advv):
        alive = st['alive']
        dists = [list(vill[i].items()) if i in vill else list(advv[i].items()) for i in alive]
        out = []
        for combo in itertools.product(*dists):
            p = F(1); cnt = defaultdict(int)
            for t, q in combo: p *= q; cnt[t] += 1
            m = max(cnt.values()); top = sorted(k for k, c in cnt.items() if c == m)
            prof = tuple(t for t, _ in combo)
            for k in top: out.append((p / len(top), tagged(('吊', k), self.after_hang(roles, st, k, prof))))
        return chance(out)

    def after_hang(self, roles, st, k, prof):
        alive = tuple(i for i in st['alive'] if i != k)
        lab = st['lab']
        p = parse(lab[k])
        if p['kind'] in ('占', '霊'): lab = lab[:k] + ('†' + lab[k].split('|')[0],) + lab[k + 1:]   # 吊られたCO者は見えない席として残る
        st2 = dict(st, alive=alive, lab=lab, hist=st['hist'] + (('vote', prof, k),), hanged=k)
        t = self.wins(roles, alive)
        if t is not None: return leaf(t)
        return self.night(roles, st2)

    # ---- 夜
    def claimants(self, st, kind):
        return [i for i in st['alive'] if parse(st['lab'][i])['kind'] == kind]

    def result_opts(self, st, i):
        """偽の占いCO者 i が出せる結果：(見た目のまとまり, 色)。まとまりの中の誰に出すかはランダム"""
        let = parse(st['lab'][i])['let']
        gs = [g for g in self.groups(st, i) if not any(x == let for x, _ in parse(st['lab'][g[0]])['marks'])]
        return [(g, c) for g in gs for c in ('白', '黒')] or [(None, None)]

    def div_dist(self, st, s):
        """本物の占い師 s の占い先の分布（進め方の順で、まだ自分が占っていない人の最初の区分からランダム）"""
        let = parse(st['lab'][s])['let']
        cand = [j for j in st['alive'] if j != s and not any(x == let for x, _ in parse(st['lab'][j])['marks'])]
        if not cand: return []
        for l in self.plan.get('div', ()):
            c = [j for j in cand if st['lab'][j] == l]
            if c: return [(F(1, len(c)), j) for j in c]
        return [(F(1, len(cand)), j) for j in cand]

    def guard_dist(self, st, h):
        cl = self.classes(st)
        for l in self.plan['guard']:
            c = [j for j in cl.get(l, []) if j != h]
            if c: return [(F(1, len(c)), j) for j in c]
        c = [j for j in st['alive'] if j != h]
        return [(F(1, len(c)), j) for j in c]

    def night(self, roles, st):
        alive = st['alive']
        wolves = tuple(i for i in alive if roles[i] == 'W'); mad = [i for i in alive if roles[i] == 'X']
        fake_seers = [i for i in self.claimants(st, '占') if roles[i] in 'XW']
        fake_meds = [i for i in self.claimants(st, '霊') if roles[i] in 'XW'] if st.get('hanged') is not None else []
        # 狂人の手（狼の噛みは知らない）：偽占いの結果・偽霊能の色
        xs = [i for i in fake_seers if roles[i] == 'X']; xm = [i for i in fake_meds if roles[i] == 'X']
        xopts = list(itertools.product(*[self.result_opts(st, i) for i in xs], *[('白', '黒') for _ in xm])) if (xs or xm) else [()]
        def wolf_part(xo):
            ws_ = [i for i in fake_seers if roles[i] == 'W']; wm = [i for i in fake_meds if roles[i] == 'W']
            bite_g = self.groups(st, None, None, excl=set(wolves))
            wopts = list(itertools.product(bite_g, *[self.result_opts(st, i) for i in ws_], *[('白', '黒') for _ in wm]))
            node = Node('A', agent='W', info=('N', st['hist'], st['lab'], wolves, st['bites']), opts=wopts, ch=[])
            node.mimic = self.mimic_index(st, roles, wopts, 1, ws_, wm)
            for wo in wopts:
                grp = wo[0]; seer_res = dict(zip(xs + ws_, list(xo[:len(xs)]) + list(wo[1:1 + len(ws_)])))
                med_res = dict(zip(xm + wm, list(xo[len(xs):]) + list(wo[1 + len(ws_):])))
                node.ch.append(chance([(F(1, len(grp)), tagged(('噛み', b), self.bite(roles, st, b, seer_res, med_res))) for b in grp]))
            return node
        if mad and (xs or xm):
            m = mad[0]
            xn = Node('A', agent='X', info=('N', st['hist'], st['lab'], m), opts=xopts, ch=[])
            xn.mimic = self.mimic_index(st, roles, xopts, 0, xs, xm)
            for xo in xopts: xn.ch.append(wolf_part(xo))
            return xn
        return wolf_part(())

    def mimic_index(self, st, roles, opts, off, seers, meds):
        """正体を隠す手：占いは進め方の占い先の区分に白、霊能は本当の色"""
        hk = st.get('hanged'); true_col = '黒' if hk is not None and roles[hk] == 'W' else '白'
        def score(o):
            s = 0
            for k, i in enumerate(seers):
                g, c = o[off + k]
                if c == '白': s += 1
                if g is not None and self.plan.get('div') and st['lab'][g[0]] == self.plan['div'][0]: s += 1
            for k, i in enumerate(meds):
                if o[off + len(seers) + k] == true_col: s += 2
            return s
        return max(range(len(opts)), key=lambda a: score(opts[a]))

    def bite(self, roles, st, b, seer_res, med_res):
        alive = st['alive']
        h = next((i for i in alive if roles[i] == 'H'), None)
        gd = self.guard_dist(st, h) if h is not None and h != b else []
        pgj = sum((p for p, j in gd if j == b), F(0))
        s = next((i for i in alive if roles[i] == 'S'), None)
        dd = self.div_dist(st, s) if s is not None else []
        out = []
        for pj, dead in ((pgj, None), (1 - pgj, b)):
            if pj == 0: continue
            for pd, tgt in (dd or [(F(1), None)]):
                sub = self.morning(roles, st, dead, b, s, tgt, seer_res, med_res, gj=(dead is None))
                out.append((pj * pd, tagged(('GJ',), sub) if dead is None else tagged(('死亡', b), sub)))
        return chance(out)

    def morning(self, roles, st, dead, bitten, s, tgt, seer_res, med_res, gj):
        alive = tuple(i for i in st['alive'] if i != dead)
        lab = list(st['lab']); hist = st['hist']
        if dead is not None and parse(lab[dead])['kind'] in ('占', '霊'): lab[dead] = '†' + lab[dead].split('|')[0]
        # 占い結果（生きている占いCO者だけ）
        res = []
        if s is not None and s in alive and tgt is not None: res.append((s, tgt, '黒' if roles[tgt] == 'W' else '白'))
        for i, (g, c) in seer_res.items():
            if i in alive and g is not None:
                res.append((i, g, c))
        rnd = [(i, x, c) for i, x, c in res if isinstance(x, tuple)]
        fixed = [(i, x, c) for i, x, c in res if not isinstance(x, tuple)]
        outs = []
        for picks in itertools.product(*[[(F(1, len(g)), j) for j in g if j in alive] or [(F(1), None)] for _, g, _ in rnd]):
            p = F(1); rr = list(fixed)
            for (i, g, c), (q, j) in zip(rnd, picks):
                p *= q
                if j is not None: rr.append((i, j, c))
            L = list(lab)
            for i, j, c in rr:
                P = parse(L[j]); P['marks'] = P['marks'] | {(parse(L[i])['let'], c)}; L[j] = compose(P)
            meds = tuple(sorted((i, ('黒' if roles[st['hanged']] == 'W' else '白') if roles[i] == 'M' else med_res[i])
                                for i in alive if parse(lab[i])['kind'] == '霊' and st.get('hanged') is not None and (roles[i] == 'M' or i in med_res)))
            h2 = hist + (('night', tuple(sorted((i, j, c) for i, j, c in rr)), meds, dead),)
            st2 = dict(alive=alive, lab=tuple(L), hist=h2, bites=st['bites'] + (bitten,))
            t = self.wins(roles, alive)
            node = leaf(t) if t is not None else (self.gj_morning(roles, st2, bitten) if gj else self.next_day(roles, st2))
            outs.append((p, node))
        return chance(outs)

    def gj_morning(self, roles, st, b):
        h = next(i for i in st['alive'] if roles[i] == 'H')
        if not self.plan.get('co') or parse(st['lab'][h])['kind'] == '狩':
            return self.next_day(roles, st)
        L = list(st['lab'])
        L[h] = compose(dict(parse(L[h]), kind='狩', conf=False))
        P = parse(L[b])
        if P['kind'] == '': L[b] = compose(dict(P, kind='確白', conf=True))
        st3 = dict(st, lab=tuple(L), hist=st['hist'] + (('hco', h, b),))
        return tagged(('狩人CO',), self.next_day(roles, st3))

    def next_day(self, roles, st):
        al = st['alive']
        keep = tuple(sorted(set(al) | {i for i, l in enumerate(st['lab']) if l.startswith('†')}))   # 翌日に持ち越す席：生存者＋死んだCO者
        know = tuple(sorted(set(st['bites']) & set(al)))
        sk = ('sit', situation(st['lab'], roles, al))
        return Node('N', info=(st['hist'] + (sk,), keep, st['lab'], roles, know))
