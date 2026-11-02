# 12A猫 3人日：投票まで含めて、各人の視点から解く。
#
# ・その日の吊りは投票で決まる。生きている全員が自分以外の1人に投票し、最多票の人が吊られる（同票なら同票の人からランダム）。
# ・狼を吊れば村の勝ち。人間を吊れば残り2人で狼の勝ち。本物の猫又が吊られると、残りからランダムに1人を道連れにする（狼なら村の勝ち）。
# ・生存状況（1狼1狂生存・（狩生存）など）は全員が知っている。誰がどの役かは、自分の役しか分からない（狼は狂人を、狂人は狼を知らない）。
# ・村（村人・狩人・猫又・霊能者）は「見た目と自分の役ごとに、誰に入れるか（確率で混ぜてもよい）」を前もって決める。
#   狼と狂人は、その決め方を知ったうえで、自分の見た目から村勝率が一番低くなる投票をする（2人で示し合わせた最善）。
#   村はこの最悪に対して一番勝てる決め方を選ぶ（生存状況ごと。中の内訳は役の札の数からの重みで平均）。
import itertools, json, sys
from fractions import Fraction as F
from collections import defaultdict

ROLES = {'M': 1, 'H': 1, 'C': 1, 'X': 1, 'W': 3, 'V': 4}
RN = {'S': '占い師', 'M': '霊能者', 'H': '狩人', 'C': '猫又', 'X': '狂人', 'W': '狼', 'V': '村人'}
LABELS = ['霊', '猫', 'ギ', '狩', '白', '灰']
CAN = {'霊': 'MXW', '狩': 'HXW', 'ギ': 'HCXW', '白': 'VCX', '灰': 'VHCXW'}   # 白：狩人COで出た護衛先（人間確定）
VILL = set('SMHCV')   # 10a：S 本物の占い師
GRID = sorted({F(k, 12) for k in range(13)})   # 混ぜる確率の刻み（1/12）

def boards(n=3, white=True):
    out = []
    for c in itertools.combinations_with_replacement(LABELS, n):
        c = list(c)
        if 'ギ' in c and ('猫' in c or '狩' in c): continue   # ギドラは猫・狩のCOとは同時に出ない
        if c.count('ギ') == 1: continue                       # ギドラは2人以上で出すCO。1人だけは意味がない
        if c.count('白') > (2 if white else 0): continue      # 白（狩人COで出た護衛先）は翌日の盤面にだけ出る
        out.append(c)
    return out

def weight(roles):
    cnt = defaultdict(int); w = 1
    for r in roles:
        w *= ROLES[r] - cnt[r]; cnt[r] += 1
    return w

def assignments(board):
    opts = [('CXW' if l == '猫' else CAN[l]) for l in board]
    for roles in itertools.product(*opts):
        if roles.count('W') != 1: continue
        if any(roles.count(r) > ROLES[r] for r in ROLES): continue
        cats = [r for l, r in zip(board, roles) if l == '猫']
        if cats and cats.count('C') != 1: continue
        # 霊COが1人・狩COが1人なら本物（偽のCOには本物が対抗する）
        if board.count('霊') == 1 and roles[board.index('霊')] != 'M': continue
        if board.count('狩') == 1 and roles[board.index('狩')] != 'H': continue
        # 狩人COが出ているなら、本物の狩人が灰に潜伏していることはない（偽の狩人COには本物が対抗する）
        if '狩' in board and any(l == '灰' and r == 'H' for l, r in zip(board, roles)): continue
        # ギドラがいるなら、生きている本物の狩人・猫又はギドラに加わっている（灰にはいない）
        if 'ギ' in board and any(l == '灰' and r in 'HC' for l, r in zip(board, roles)): continue
        # 白は本物の狩人がGJの翌朝にCOして出した護衛先：本物の狩人は狩COで生きているか、死んでいる（灰などには潜んでいない）
        if '白' in board and any(r == 'H' and l != '狩' for l, r in zip(board, roles)): continue
        yield weight(roles), roles

def situation(board, roles):
    st = '1w' + ('1k' if 'X' in roles else '') + '生存'
    hid = []
    if any(l == '灰' and r == 'H' for l, r in zip(board, roles)): hid.append('狩生存')
    if any(l == '灰' and r == 'C' for l, r in zip(board, roles)): hid.append('猫生存')
    return st + ('（' + '・'.join(hid) + '）' if hid else '')

SH = {'M': '真', 'H': '狩', 'C': '猫', 'X': '狂', 'W': '狼', 'V': '村'}
def detail(board, roles):
    det = []
    for l in ('霊', '猫', 'ギ', '狩'):
        rs = [r for b, r in zip(board, roles) if b == l]
        if not rs or (l == '猫' and len(rs) == 1): continue
        if l == 'ギ': det.append('ギ' + ''.join(SH[r] for r in sorted(rs, key='HCXW'.index)))
        else: det.append(l + ''.join({'M': '真', 'H': '真', 'C': '真', 'X': '狂', 'W': '狼'}[r] for r in sorted(rs, key='MHCXW'.index)))
    for l in ('灰',):
        rs = [r for b, r in zip(board, roles) if b == l]
        if 'W' in rs: det.append('灰が狼' if len(rs) == 1 else '灰に狼')
        if 'X' in rs: det.append('灰が狂' if len(rs) == 1 else '灰に狂')
    return '、'.join(det)

def who(board, roles, i):
    l, r = board[i], roles[i]
    if l[0] in ('灰', 'ギ', '白') or len(l) > 1: return f'{l}（{RN[r] if l[0] in ("灰", "ギ", "白") or r in "XW" else "本物"}）'
    return f'{l}（{RN[r] if r in "XW" else "本物"}）'

def targets(board, i):
    """i から見た投票先の区分（自分以外の見た目）"""
    from game10 import label_key
    return sorted({board[j] for j in range(len(board)) if j != i}, key=label_key)

def vote_dist(board, i, dist):
    """区分ごとの確率 → 個人ごとの確率（同じ見た目の人は等分）"""
    out = defaultdict(F)
    for l, p in dist.items():
        js = [j for j in range(len(board)) if j != i and board[j] == l]
        for j in js: out[j] += p / len(js)
    return out

def outcome(board, roles, votes):
    """votes：各人の投票先の分布 → [(吊られる人, 確率)] と村勝率"""
    n = len(board)
    hang = defaultdict(F)
    for combo in itertools.product(*[list(v.items()) for v in votes]):
        p = F(1); cnt = [0] * n
        for t, q in combo: p *= q; cnt[t] += 1
        if p == 0: continue
        m = max(cnt); top = [k for k in range(n) if cnt[k] == m]
        for k in top: hang[k] += p / len(top)
    v = F(0)
    for k, p in hang.items():
        r = roles[k]
        if r == 'W': x = F(1)
        elif r == 'C': x = F(sum(1 for j in range(n) if j != k and roles[j] == 'W'), n - 1)
        else: x = F(0)
        v += p * x
    return hang, v

def solve_sit(board, cases):
    """cases：[(重み, 役)]（同じ生存状況）。村の決め方（混合の格子）× 人外の最善応答"""
    # 村の型＝(見た目, 役)、人外の型＝(見た目, 役)
    vt = sorted({(board[i], r[i]) for _, r in cases for i in range(len(board)) if r[i] in VILL}, key=lambda t: (LABELS.index(t[0]), t[1]))
    at = sorted({(board[i], r[i]) for _, r in cases for i in range(len(board)) if r[i] in 'WX'}, key=lambda t: (LABELS.index(t[0]), t[1]))
    def opts_of(t):
        i = board.index(t[0]) if board.count(t[0]) == 1 else board.index(t[0])
        return targets(board, i)
    vopt = []
    for t in vt:
        tg = opts_of(t)
        if len(tg) == 1: vopt.append([{tg[0]: F(1)}])
        else: vopt.append([{tg[0]: p, tg[1]: 1 - p} for p in GRID])
    aopt = [[{x: F(1)} for x in opts_of(t)] for t in at]
    tot = sum(w for w, _ in cases)
    def value(vs, ads, per=False):
        V = dict(zip(vt, vs)); A = dict(zip(at, ads))
        s = F(0); pc = []
        for w, roles in cases:
            votes = [vote_dist(board, i, V[(board[i], roles[i])] if roles[i] in VILL else A[(board[i], roles[i])]) for i in range(len(board))]
            hang, v = outcome(board, roles, votes)
            s += F(w, tot) * v
            if per: pc.append((hang, v))
        return (s, pc) if per else s
    best = None; allv = []
    for vs in itertools.product(*vopt):
        worst = None
        for ads in itertools.product(*aopt):
            v = value(vs, ads)
            if worst is None or v < worst[0]: worst = (v, ads)
        allv.append((worst[0], vs, worst[1]))
        if best is None or worst[0] > best[0]: best = (worst[0], vs, worst[1])
    return vt, at, best, allv, value

def desc_plan(board, t, dist, me_adv=False):
    l, r = t
    me = (f'{l}（{RN[r]}）' if l in ('灰', 'ギ') else (f'{l}（本物）' if r in VILL else f'{l}（{RN[r]}）'))
    parts = []
    for x, p in sorted(dist.items(), key=lambda kv: -kv[1]):
        if p == 0: continue
        name = ('対抗の' + x if x == l and x != '灰' else ('もう1人の灰' if x == l else x))
        parts.append(name + ('' if p == 1 else f'に{p}') )
    return me + '：' + ('、'.join(parts) + ('に投票' if len(parts) == 1 and list(dist.values()).count(F(1)) else 'ずつ投票' if len(parts) > 1 else ''))

def solve(board):
    sits = defaultdict(list)
    for w, roles in assignments(board): sits[situation(board, roles)].append((w, roles))
    if not sits: return None
    out = []
    for st, cases in sits.items():
        vt, at, best, allv, value = solve_sit(board, cases)
        bv, vs, ads = best
        _, pc = value(vs, ads, per=True)
        tot = sum(w for w, _ in cases)
        # 内訳（見出しが同じものはまとめる）
        grp = defaultdict(lambda: [0, F(0), defaultdict(F)])
        for (w, roles), (hang, v) in zip(cases, pc):
            g = grp[detail(board, roles)]; g[0] += w; g[1] += w * v
            for k, p in hang.items(): g[2][who(board, roles, k)] += w * p
        subs = [dict(det=d or '内訳', share=str(F(g[0], tot)), v=str(g[1] / g[0]),
                     hang=sorted([[k, str(p / g[0])] for k, p in g[2].items()], key=lambda x: -F(x[1]))) for d, g in grp.items()]
        # ほかの決め方（上位）
        alts = sorted(allv, key=lambda x: -x[0])
        seen = []; alt_out = []
        for v, vs2, ads2 in alts:
            d = [desc_plan(board, t, x) for t, x in zip(vt, vs2)]
            if d in seen or d == [desc_plan(board, t, x) for t, x in zip(vt, vs)]: continue
            seen.append(d); alt_out.append(dict(v=str(v), plan=d))
            if len(alt_out) >= 4: break
        out.append(dict(sit=st, share=str(F(tot, sum(w for w, _ in assignments(board)))), v=str(bv),
                        plan=[desc_plan(board, t, x) for t, x in zip(vt, vs)],
                        adv=[desc_plan(board, t, x) for t, x in zip(at, ads)],
                        subs=subs, alts=alt_out))
    order = lambda s: (('1k' not in s['sit']), s['sit'])
    out.sort(key=order)
    return dict(board=board, sits=out)

if __name__ == '__main__':
    import wikitext
    res = []
    for b in boards():
        wt = wikitext.board_text(b)
        if wt: res.append(wt); print(','.join(b), wt['v'], flush=True)
    json.dump(res, open(sys.argv[1], 'w'), ensure_ascii=False, separators=(',', ':'))
    print(len(res), 'boards')
