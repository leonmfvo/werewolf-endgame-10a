# 10a狩人（占い・霊能・狩人・狼2・狂人・村人4、初日犠牲者あり）の初期局面。engine10 の上に作る。
# 2日目の朝は9人。本物の占い・霊能が初日犠牲になった内訳（占い欠け・霊能欠け）も含む。
# 初日犠牲者は、生きている人のうち狼・CO者以外から均等（狩人・村人4人、狂人が灰に潜伏していれば狂人も）。
# 本物の占い師（霊能者）がCOしていない内訳では、初日犠牲者はその役職に決まる。
import itertools
import engine10 as E

N_DAY2 = 9
S_, W_ = (0, 1, 0), (1, 1, 0)

# 人外の選択（狂人：占いCO S / 霊能CO M / 潜伏 H、狼：占い騙り fs 人・霊能騙り fm 人）と初日犠牲者から到達しうる内訳をすべて並べる
WOLF_OPTS = ((0, 0), (1, 0), (2, 0), (0, 1), (0, 2), (1, 1))
def compose(mad, fs, fm, dummy):
    """mad: S/M/H/X（X は狂人が初日犠牲）、dummy: seer / med / other → 内訳キー"""
    sp = ('' if dummy == 'seer' else 'T') + ('M' if mad == 'S' else '') + 'W' * fs
    mp = ('' if dummy == 'med' else 'T') + ('M' if mad == 'M' else '') + 'W' * fm
    return f'{sp}-{mp}'

def _all_keys():
    ks = {}
    for mad in 'SMHX':
        for fs, fm in WOLF_OPTS:
            for dummy in ('seer', 'med', 'other'):
                if mad == 'X' and dummy != 'other': continue
                ks[compose(mad, fs, fm, dummy)] = 1
    return ks

def board_of(key):
    sp, mp = key.split('-')
    return f'{len(sp)}-{len(mp)}'

# 盤面 → 内訳キー（占い側-霊能側）。T 本物 / M 狂人 / W 狼。CO者がいない側は空
BOARDS = {}
for k in sorted(_all_keys(), key=lambda k: (len(k.split('-')[0]) + len(k.split('-')[1]), len(k.split('-')[0]), ('T' not in k.split('-')[0]) + ('T' not in k.split('-')[1]), k)):
    BOARDS.setdefault(board_of(k), []).append(k)

def lacking(key):
    sp, mp = key.split('-')
    return '占い欠け' if 'T' not in sp else ('霊能欠け' if 'T' not in mp else '')

NAME = {'T': '真', 'M': '狂', 'W': '狼'}

def label(key):
    a, b = key.split('-')
    return (''.join(NAME[x] for x in a) or '欠') + '-' + (''.join(NAME[x] for x in b) or '欠')

def initial10(key):
    sp, mp = key.split('-')
    slots = tuple(W_ if x == 'W' else S_ for x in sp)
    meds = tuple(W_ if x == 'W' else S_ for x in mp)
    ns = len(slots)
    r0 = (0,) * ns
    gw = 2 - sp.count('W') - mp.count('W')
    gh = N_DAY2 - ns - len(meds) - gw
    mad_co = 'M' in sp or 'M' in mp
    E.MADMED[0] = -1
    # 狼から見て見分けがつかない人間のCO者（本物と狂人）の並べ替えをすべて同じ重みで持つ
    hs = [i for i, x in enumerate(sp) if x != 'W']
    hm = [j for j, x in enumerate(mp) if x != 'W']
    pairs = []   # (本物占いの枠 / -1 不在, 狂人の位置 / None 潜伏)
    if 'M' in sp:
        if 'T' in sp: pairs = [(t, m) for t in hs for m in hs if m != t]
        else: pairs = [(-1, hs[0])]
    elif 'M' in mp:
        t = hs[0] if 'T' in sp else -1
        pairs = [(t, -10 - j) for j in hm]
    else:
        pairs = [(hs[0] if 'T' in sp else -1, None)]   # 占いCO者がいなければ本物の占い師は不在（-1）
    bel = {}
    if 'T' in sp and 'T' in mp:
        dummies = [('H', 1), ('V', 4)] + ([] if mad_co else [('m', 1)])
    else:
        dummies = [('X', 1)]       # 初日犠牲者は本物の占い師（霊能者）
    tot = sum(w for _, w in dummies)
    for t, m in pairs:
        mm = m if m is not None else r0
        for kind, w in dummies:
            if kind == 'H': k = (t, mm, None, None)
            elif kind == 'm': k = (t, -1, r0, None)
            else: k = (t, mm, r0, None)
            bel[k] = bel.get(k, 0) + w / tot / len(pairs)
    s = ('N', slots, meds, -1, -1, ((r0, gw, gh),), None, 0, E.norm_bel(bel))
    # 狩人CO（hco / hcoopt）では、灰の人間確定などの目印を分類に足す
    return E.add_flag(s) if (E.POL.get('hco') or E.POL.get('hcoopt')) else s
