# 3人日の計算結果を、wiki（ゲヘナのwiki）の書き方に合わせた文章にする。
#   見出し「1狼1狂生存で猫に狂」、1行目「〇〇なら村勝率1/4、△△なら3/8」、導出「村勝ちは狼が真猫に入れる(1/2)×猫飛び(1/2)=1/4」
import itertools
from fractions import Fraction as F
from collections import defaultdict
import vote3 as V3

def fs(x):
    x = F(x); return str(x.numerator) if x.denominator == 1 else f'{x.numerator}/{x.denominator}'

def pname(board, roles, i):
    """人の呼び名（真猫・狂・狼・村 など）"""
    l, r = board[i], roles[i]
    if len(l) > 1:   # 狩A・狩B など、公開の出来事で区別できる人：見た目＋役
        return f"{l}（{ {'W': '狼', 'X': '狂'}.get(r) or ('本物' if l[0] in '霊猫狩' else {'V': '村', 'H': '狩', 'C': '猫'}[r])}）"
    if r == 'W': return '狼'
    if r == 'X': return '狂'
    if l == '猫': return '真猫'
    if l == '霊': return '真霊'
    if l == '狩': return '真狩'
    if l == 'ギ': return {'H': 'ギの狩', 'C': 'ギの猫'}[r]
    if l == '白': return {'V': '白の村', 'C': '白の猫'}[r]
    return {'V': '村', 'H': '灰の狩', 'C': '灰の猫'}[r]

def names(board, roles):
    ns = [pname(board, roles, i) for i in range(len(board))]
    for x in set(ns):
        idx = [i for i, y in enumerate(ns) if y == x]
        if len(idx) > 1:
            for k, i in enumerate(idx): ns[i] = x + 'ABC'[k]
    return ns

def tname(own, x):
    if x == own and x != '灰': return '対抗'
    if x == own: return 'もう1人の灰'
    return x

def tname_p(board, i, j, ns):
    return ns[j]

def plan_text(board, vt, vs, only=None):
    out = []
    for (l, r), d in zip(vt, vs):
        if only is not None and (l, r) not in only: continue
        who = {('猫', 'C'): '真猫', ('霊', 'M'): '真霊', ('狩', 'H'): '真狩', ('ギ', 'H'): 'ギの狩', ('ギ', 'C'): 'ギの猫',
               ('灰', 'V'): '村', ('灰', 'H'): '灰の狩', ('灰', 'C'): '灰の猫', ('白', 'V'): '白の村', ('白', 'C'): '白の猫'}[(l, r)]
        items = [(x, p) for x, p in d.items() if p > 0]
        if len(items) == 1: out.append(f'{who}が{tname(l, items[0][0])}に投票')
        else:
            (a, pa), (b, pb) = sorted(items, key=lambda t: -t[1])
            if pa == pb: out.append(f'{who}が{tname(l, a)}と{tname(l, b)}に1/2ずつで投票')
            else: out.append(f'{who}が{tname(l, a)}に{fs(pa)}・{tname(l, b)}に{fs(pb)}で投票')
    return '、'.join(out) if out else '村の票は決まっている'

def case_title(board, roles, sit, single):
    if single: return sit
    parts = []
    # 狩A・狩B など区別できる人がいれば、その見た目ごとに書く
    for l in sorted({b for b in board if b[0] in '霊猫ギ狩'}, key=lambda b: ('霊猫ギ狩'.index(b[0]), b)):
        rs = [r for b, r in zip(board, roles) if b == l]
        if 'X' in rs: parts.append(f'{l}に狂')
        if 'W' in rs: parts.append(f'{l}に狼')
    if not parts:
        rs = [r for b, r in zip(board, roles) if b[0] == '灰']
        x = ('狼' if 'W' in rs else '') + ('と狂' if 'W' in rs and 'X' in rs else ('狂' if 'X' in rs else ''))
        if x: parts.append('灰に' + x)
    return sit + 'で' + '・'.join(parts) if parts else sit

def derivation(board, roles, votes):
    """村勝ちになる票の入り方：(固定票, 項の並び, 合計)。項 = dict(f=[[説明, 確率]], o=None | ['猫飛び', 確率] | ['ランダム', [[狼, 確率] or [猫, 確率, 道連れ]]], v=値)"""
    n = len(board); ns = names(board, roles)
    fixed = []; terms = []
    for i, v in enumerate(votes):
        if len(v) == 1 and roles[i] in 'WX':
            j = next(iter(v)); fixed.append(f'{ns[i]}→{ns[j]}')
    total = F(0)
    for combo in itertools.product(*[sorted(v.items()) for v in votes]):
        p = F(1); cnt = [0] * n; fac = []
        for i, (t, q) in enumerate(combo):
            p *= q; cnt[t] += 1
            if q != 1: fac.append([f'{ns[i]}が{ns[t]}に入れる', fs(q)])
        if p == 0: continue
        m = max(cnt); top = [k for k in range(n) if cnt[k] == m]
        parts = []; wv = F(0)
        for k in sorted(top, key=lambda k: roles[k] != 'W'):
            if roles[k] == 'W': parts.append(['狼', fs(F(1, len(top)))]); wv += F(1, len(top))
            elif roles[k] == 'C':
                dr = F(sum(1 for j in range(n) if j != k and roles[j] == 'W'), n - 1)
                if dr: parts.append(['猫', fs(F(1, len(top))), fs(dr)]); wv += dr / len(top)
        if wv == 0: continue
        total += p * wv
        if len(top) > 1: o = ['ランダム', parts]
        elif roles[top[0]] == 'C': o = ['猫飛び', parts[0][2]]
        else: o = None
        terms.append(dict(f=fac, o=o, v=fs(p * wv)))
    return fixed, terms, fs(total)

def board_text(board):
    """村も人外も生存状況を知らない。盤面で1つの決め方（最善）と、比べる相手（次にいい「全部入れる／1/2ずつ」の決め方）"""
    import vote3g as G
    R = G.solve_board(board)
    if not R: return None
    plans = [('g', G.plan_dists(R), {t[:2]: {a: F(1)} for t, a in zip(R['at'], R['ads'])})]
    if R['alt']: plans.append(('a', G.plan_dists(R, R['alt']['ps']), {t[:2]: {a: F(1)} for t, a in zip(R['at'], R['alt']['ads'])}))
    sits = defaultdict(list)
    for w, roles in R['cases']: sits[V3.situation(board, roles)].append((w, roles))
    allw = sum(w for w, _ in R['cases'])
    secs = []; summ = []
    for st in sorted(sits, key=lambda s: ('1k' not in s, s)):
        cases = sits[st]; tot = sum(w for w, _ in cases)
        groups = {}
        for w, roles in cases: groups.setdefault(case_title(board, roles, st, False), []).append((w, roles))
        single = len(groups) == 1
        for t, lst in groups.items():
            w, roles = lst[0]
            title = st if single else t
            items = []
            present = {(board[i], roles[i]) for i in range(len(board))}
            for tag, P, A in plans:
                votes = [V3.vote_dist(board, i, P[(board[i], roles[i])] if roles[i] in V3.VILL else A[(board[i], roles[i])]) for i in range(len(board))]
                fixed, terms, tv = derivation(board, roles, votes)
                pt = plan_text(board, list(P), [P[x] for x in P], present)
                if tag == 'a' and any(pt == x['plan'] and tv == x['v'] for x in items): continue
                items.append(dict(plan=pt, tag=tag, best=(tag == 'g'), fixed=fixed, terms=terms, v=tv))
            sec = dict(title=title, share=fs(F(sum(x for x, _ in lst), allw)), items=items)
            if not any(x['title'] == title and x['items'] == items for x in secs): secs.append(sec)
        vals = []
        for tag, P, A in plans:
            v = F(0)
            for w, roles in cases:
                votes = [V3.vote_dist(board, i, P[(board[i], roles[i])] if roles[i] in V3.VILL else A[(board[i], roles[i])]) for i in range(len(board))]
                v += F(w, tot) * G.outcome(board, roles, votes, True)[1]
            vals.append(fs(v))
        summ.append(dict(sit=st, share=fs(F(tot, allw)), v=vals[0], va=vals[1] if len(vals) > 1 else None))
    G_plan = plans[0][1]
    return dict(board=board, v=fs(R['v']), plan=plan_text(board, list(G_plan), [G_plan[x] for x in G_plan]),
                va=fs(R['alt']['v']) if R['alt'] else None, plana=plan_text(board, list(plans[1][1]), [plans[1][1][x] for x in plans[1][1]]) if R['alt'] else None,
                secs=secs, summ=summ)

if __name__ == '__main__':
    import sys, json
    print(json.dumps(board_text(sys.argv[1].split(',')), ensure_ascii=False, indent=1)[:2500])
