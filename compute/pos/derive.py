# 最善進行に沿った勝率の導出（答案ふう）：内訳ごとに、役の並びをまとめて「出来事の列」の木を作り、式にする。
from fractions import Fraction as F
from pos import Game, solve, behaviour, exact_eval, case_values, ROLE_NAME

class T:
    __slots__ = ('kids', 'P', 'W', 'alts', 'order')
    def __init__(self):
        self.kids = {}; self.P = F(0); self.W = F(0); self.alts = {}; self.order = []
    def child(self, step, p):
        if step not in self.kids: self.kids[step] = T(); self.order.append(step)
        c = self.kids[step]; c.P += p; return c

def build_trie(g, beh, adv, v, ai):
    root = T()
    def walk(nd, p, tn):
        if p == 0: return
        if nd.ev: tn = tn.child('・'.join(nd.ev), p)
        if nd.kind == 'L': tn.W += p * nd.payoff; return
        if nd.kind == 'C':
            for q, ch in nd.children: walk(ch, p * q, tn)
        elif nd.kind == 'V':
            bh = beh.get(nd.info) or {nd.children[0][0]: F(1)}
            for a, ch in nd.children:
                if bh.get(a, 0): walk(ch, p * bh[a], tn)
        else:
            best = adv[nd.info]
            per = {}
            for a, ch in nd.children:
                lab = nd.alabel[a]; val = v(ch)
                if lab not in per or val < per[lab][0]: per[lab] = (val, a == best)
                elif val == per[lab][0] and a == best: per[lab] = (val, True)
            for lab, (val, ch_) in per.items():
                d = tn.alts.setdefault(lab, [F(0), F(0), F(0)])
                d[0] += p; d[1] += p * val; d[2] += p if ch_ else 0
            walk(next(ch for a, ch in nd.children if a == best), p, tn)
    for (w, ch), (_, a_, _) in zip(g.root.children, g.cases):
        if a_ == ai: root.P += w; walk(ch, w, root)
    return root

def total_W(t):
    return t.W + sum(total_W(c) for c in t.kids.values())

def fs(x):
    x = F(x); return str(x.numerator) if x.denominator == 1 else f'{x.numerator}/{x.denominator}'

def formulas(root):
    """[{sym, path, terms:[(q, 説明, 値 or 記号)], value, alts}]"""
    out = []; cnt = [0]
    def compress(t, lab):
        # 子が1つで、人外の選択も終了もない鎖はつなげる
        labs = [lab]
        while len(t.kids) == 1 and not t.alts and t.W == 0:
            (s, c), = t.kids.items(); labs.append(s); t = c
        return t, labs
    def emit(t, sym, path):
        terms = []
        val = total_W(t) / t.P
        rec = {'sym': sym, 'path': path, 'terms': terms, 'value': fs(val), 'alts': []}
        out.append(rec)
        if t.alts:
            tot = sum(d[0] for d in t.alts.values())
            for lab, (pp, ww, ch) in sorted(t.alts.items(), key=lambda kv: kv[1][1] / kv[1][0]):
                rec['alts'].append({'label': lab, 'value': fs(ww / pp), 'chosen': ch > 0, 'share': fs(pp / t.P)})
        if t.W and t.kids:
            pass
        later = []
        leafmass = t.P - sum(c.P for c in t.kids.values())
        if leafmass:
            terms.append({'q': fs(leafmass / t.P), 'ev': '決着', 'v': fs(t.W / leafmass)})
        for s in t.order:
            c = t.kids[s]
            q = c.P / t.P
            c2, labs = compress(c, s)
            if not c2.kids:
                terms.append({'q': fs(q), 'ev': ' → '.join(labs), 'v': fs(c2.W / c2.P)})
            else:
                cnt[0] += 1; sym2 = f'P{cnt[0]}'
                terms.append({'q': fs(q), 'ev': ' → '.join(labs), 'v': sym2, 'val': fs(total_W(c2) / c2.P)})
                later.append((c2, sym2, path + labs))
        for c2, sym2, p2 in later: emit(c2, sym2, p2)
    emit(root, 'P', [])
    return out

def show(fm):
    for r in fm:
        print(f"{r['sym']}  [{' → '.join(r['path']) or '初期'}]")
        for a in r['alts']: print(f"    人外：{a['label']} = {a['value']}{' ←' if a['chosen'] else ''}")
        for t in r['terms']: print(f"    {t['q']} × {t['v']}   ({t['ev']})")
        print(f"    = {r['value']}")

if __name__ == '__main__':
    board = dict(labels=['占','灰','灰','灰','灰'],
                 cases=[dict(name='灰に1狼', fixed={0:'S'}, gray={'W':1,'V':3}),
                        dict(name='灰に1狼1狂', fixed={0:'S'}, gray={'W':1,'X':1,'V':2})])
    g = Game(board); val, x = solve(g); beh = behaviour(g, x); ex, adv, v = exact_eval(g, beh)
    for ai, c in enumerate(board['cases']):
        print('=====', c['name']); show(formulas(build_trie(g, beh, adv, v, ai)))

# ---------------------------------------------------------------- 村の進行（公開情報ごとの手）
def policy(g, beh, adv):
    """到達する村の情報集合ごとに：(公開情報の説明, 手の説明, 到達確率)。同じ見え方の人の入れ替えはまとめる"""
    reach = {}
    stack = [(g.root, F(1))]
    nodes = {}
    while stack:
        nd, p = stack.pop()
        if p == 0: continue
        if nd.kind == 'V':
            reach[nd.info] = reach.get(nd.info, F(0)) + p; nodes.setdefault(nd.info, nd)
        for e, ch in nd.children:
            if nd.kind == 'C': q = p * e
            elif nd.kind == 'V': q = p * (beh.get(nd.info) or {nd.children[0][0]: F(1)}).get(e, F(0))
            else: q = p if e == adv[nd.info] else F(0)
            stack.append((ch, q))
    labels = g.labels
    groups = {}
    for info, p in reach.items():
        kind, vh = info
        names = {}; cnt = {}
        multi = {l for l in labels if labels.count(l) > 1}
        def nm(i):
            if i not in names:
                l = labels[i]
                if l in multi:
                    cnt[l] = cnt.get(l, 0) + 1; names[i] = l + 'ABCDE'[cnt[l] - 1]
                else: names[i] = l
            return names[i]
        day = 1; parts = []; cur = []
        mk = lambda c: '○' if c == 'o' else '●'
        last = None
        for e in vh:
            t = e[0]
            if t == 'hang': cur.append(f'{nm(e[1])}吊り'); last = e[1]
            elif t == 'dead': cur.append(f'{nm(e[1])}噛まれ')
            elif t == 'gj': cur.append('GJ')
            elif t == 'seer': cur.append(f'{nm(e[1])}→{nm(e[2])}{mk(e[3])}')
            elif t == 'med': cur.append(f'{nm(e[1])}→{nm(last)}{mk(e[2])}')
            elif t == 'hide': cur.append('狩人潜伏')
            elif t == 'hco': cur.append(f'{nm(e[1])}狩人CO（{nm(e[2])}護衛）')
            elif t == 'hco2': cur.append(f'{nm(e[1])}対抗CO')
        desc = '・'.join(cur) if cur else '初日'
        bh = beh.get(info) or {}
        nd = nodes[info]
        if kind == 'D':
            acts = '／'.join(f'{nm(a)}を吊る' + ('' if q == 1 else f'（{fs(q)}）') for a, q in sorted(bh.items(), key=lambda kv: -kv[1]))
            d = 1 + sum(1 for e in vh if e[0] == 'hang')
            when = f'{d}日目'
        else:
            acts = '／'.join(('狩人CO' if a == 'co' else '潜伏') + ('' if q == 1 else f'（{fs(q)}）') for a, q in bh.items())
            d = 1 + sum(1 for e in vh if e[0] == 'hang')
            when = f'{d}日目朝（GJ）'
        k = (when, desc, acts)
        groups[k] = groups.get(k, F(0)) + p
    out = [dict(when=w, seen=d, act=a, p=fs(p)) for (w, d, a), p in groups.items()]
    out.sort(key=lambda r: (r['when'], -F(r['p'])))
    return out
