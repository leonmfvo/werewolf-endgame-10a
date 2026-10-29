# 盤面（生存者の見た目）＋条件（内訳・狼の位置・狂人の生死・狩人の位置）から、分岐サイトのエンジンで村勝率と帰着先を求める
import sys, json, os, re, itertools
from fractions import Fraction as F
from collections import defaultdict
sys.setrecursionlimit(1000000)
import engine10x as E, e10a, run10a, tree10ax
import build10b_site as B
from state import parse_pub
e10a.E = E
MM = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mm.json')))
LET = 'abc'
ROLE = {'T': '真', 'M': '狂', 'W': '狼'}

# ---------------------------------------------------------------- 書き方
def letters(n): return (lambda i: LET[i]) if n > 1 else (lambda i: '')

def mark(P, i):
    s = P['slots'][i]
    return ('◎' if P['T'] == i and len(P['slots']) > 1 else '') + ('✕' if s[2] else '')

def cat_label(P, r):
    ns = len(P['slots']); L = letters(ns)
    fl = r[-1]
    wh = [L(i) + mark(P, i) for i in range(ns) if r[i] == 1]
    bl = [L(i) + mark(P, i) for i in range(ns) if r[i] == 2]
    base = ('黒' + ''.join(bl) if bl else '') + ('白' + ''.join(wh) if wh else '')
    if fl == 1: return '確白' + (f'({base})' if base else '')
    if fl == 2: return '狩' + (f'({base})' if base else '')
    return base or '灰'

ORDER = lambda l: (0 if l.startswith('占') else 1 if l.startswith('霊') else 2 if l.startswith('狩') else 3 if l.startswith('確白')
                   else 4 if l.startswith('黒') else 5 if l.startswith('白') else 6, l)

def notation(P):
    ns, nm = len(P['slots']), len(P['meds'])
    Ls, Lm = letters(ns), letters(nm)
    labs = []
    for i, x in enumerate(P['slots']):
        if x[1]: labs.append('占' + Ls(i) + mark(P, i))
    for j, x in enumerate(P['meds']):
        if x[1]: labs.append('霊' + Lm(j) + ('◎' if P['TM'] == j and nm > 1 else '') + ('✕' if x[2] else ''))
    for r, w, h in P['cats']: labs += [cat_label(P, r)] * (w + h)
    labs.sort(key=ORDER)
    note = []
    if P['T'] >= 0 and not P['slots'][P['T']][1] and any(x[1] for x in P['slots']): note.append(f'真置きの占{Ls(P["T"])}は死亡')
    if P['TM'] >= 0 and not P['meds'][P['TM']][1] and any(x[1] for x in P['meds']): note.append(f'真置きの霊{Lm(P["TM"])}は死亡')
    return ','.join(labs), '、'.join(note)

def relevant_slots(P):
    ns = len(P['slots'])
    alive = any(x[1] for x in P['slots'])
    return [i for i, x in enumerate(P['slots']) if x[1] or (i == P['T'] and alive) or any(r[i] for r, w, h in P['cats'])]

def truth_label(P, key):
    sp, mp = key.split('-')
    ns, nm = len(sp), len(mp); Ls, Lm = letters(ns), letters(nm)
    out = [f'占{Ls(i)}{ROLE[sp[i]]}' for i in relevant_slots(P)]
    malive = any(x[1] for x in P['meds'])
    out += [f'霊{Lm(j)}{ROLE[mp[j]]}' for j, x in enumerate(P['meds']) if x[1] or (j == P['TM'] and malive)]
    return '・'.join(out)

def wolf_label(P):
    out = []
    for r, w, h in P['cats']:
        if w: out.append(f'{cat_label(P, r)}に{w}狼' if w + h > 1 else f'{cat_label(P, r)}が狼')
    return '、'.join(out)

# ---------------------------------------------------------------- 条件 → belief
def wolves_alive(P):
    return sum(w for r, w, h in P['cats']) + sum(1 for x in P['slots'] if x[0] and x[1]) + sum(1 for x in P['meds'] if x[0] and x[1])

def options(P, key):
    """[(名前, 狂人, 狩人, bel)]。狂人：'co' 騙っている（生死は盤面どおり）/ 'alive' 灰などに潜伏 / 'dead'。狩人：'hide' / 'co' / 'dead'"""
    sp, mp = key.split('-')
    S = sp.index('T') if 'T' in sp else -1
    mco = None
    if 'M' in sp: mco = sp.index('M')
    elif 'M' in mp: mco = -10 - mp.index('M')
    hum = [(r, h) for r, w, h in P['cats'] if h]
    out = []
    madopts = [('co', None)] if mco is not None else [('alive', None), ('dead', None)]
    for mo, _ in madopts:
        flagged = any(r[-1] != 0 for r, w, h in P['cats'])   # 人間確定・狩人CO者2人がいる＝狩人はもうCOした（灰に潜伏はありえない）
        for ho in (('co', 'dead') if flagged else ('hide', 'dead')):
            bel = defaultdict(F)
            mpos = [(mco, 1)] if mo == 'co' else ([(-1, 1)] if mo == 'dead' else [(r, h) for r, h in hum if r[-1] != 2])
            if ho == 'dead': hpos = [(None, 1)]
            elif ho == 'hide': hpos = [(r, h) for r, h in hum if r[-1] == 0]
            else: hpos = [(r, h) for r, h in hum if r[-1] != 0]
            for (m, wm), (H, wh) in itertools.product(mpos, hpos):
                if isinstance(m, tuple) and isinstance(H, tuple):
                    wt = wm * (wh - 1) if m == H else wm * wh
                else: wt = wm * wh
                if wt > 0: bel[(S, m, H, None)] += wt
            if not bel: continue
            tot = sum(bel.values())
            bel = {k: v / tot for k, v in bel.items()}
            w = wolves_alive(P)
            mad_alive = mo == 'alive' or (mo == 'co' and E.mad_alive(mco, P['slots'], P['meds']))
            name = f'{w}w' + ('1k' if mad_alive else '') + '生存' + {'hide': '・灰に狩', 'co': '・狩CO済み', 'dead': ''}[ho]
            if mo == 'co' and mad_alive: name += '（狂人はCO者）'
            out.append(dict(name=name, mad=mo, hunter=ho, bel=bel))
    return out

def status_of(s, key):
    """局面 s の belief から：(狂人生存の確率, 狩人 hide/co/dead の確率)"""
    ph, slots, meds, T, TM, cats, last, nt, bel = s
    pm = sum(p for k, p in bel if E.mad_alive(k[1], slots, meds))
    ph_ = {'hide': F(0), 'co': F(0), 'dead': F(0)}
    for k, p in bel:
        H = k[2]
        ph_['dead' if H is None else ('hide' if H[-1] == 0 else 'co')] += p
    return pm, ph_

def policy_of(tree_id):
    key, pid = tree_id.split('__', 1)
    toks = pid.split('_')
    pid = '|'.join(toks)
    return key, pid

def solve(P, key, tree_id, nt, opt):
    _, pid = policy_of(tree_id)
    c = B.parse(pid)
    E.MADMED[0] = -1
    E.setpol(**{**run10a.BASE, **c, 'mm': MM[key][pid]})
    s0 = ('D', P['slots'], P['meds'], P['T'], P['TM'], P['cats'], None, nt, E.norm_bel(opt['bel']))
    T = tree10ax.Tree(); tree10ax.PRUNE[0] = True
    root = T.state(s0)
    inv = {v: k for k, v in T.ids.items()}
    return T, root, inv
