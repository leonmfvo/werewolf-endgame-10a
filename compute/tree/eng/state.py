# 分岐サイトの局面の文字列（公開部分）から、エンジン（engine10x）の局面を組み立てる
import re
from fractions import Fraction as F
import engine10x as E

def cat_r(name, ns):
    """分類名 → r（占い師ごとの結果 0/1/2 と、最後に目印 0 / 1 人間確定 / 2 狩人CO者2人）"""
    fl = 0
    if name.endswith('（人間確定）'): fl, name = 1, name[:-6]
    elif name.endswith('（狩人CO者）'): fl, name = 2, name[:-7]
    if name == '人間確定': fl, name = 1, ''
    r = [0] * ns
    if name not in ('', '灰'):
        for part in name.split('・'):
            m = re.match(r'占い(\d)?の([○●])$', part)
            assert m, (name, part)
            i = int(m.group(1)) - 1 if m.group(1) else 0
            r[i] = 1 if m.group(2) == '○' else 2
    return tuple(r) + (fl,)

def parse_pub(pub, key):
    """→ dict(n, slots, meds, T, TM, cats)。slots/meds は (狼?, 生存?, 破綻?)"""
    toks = pub.split('／')
    sp, mp = key.split('-')
    seer_t = [t for t in toks[1:] if t.startswith('占い') and not re.match(r'^占い\d?の', t)]
    med_t = [t for t in toks[1:] if t.startswith('霊能')]
    ns = len(sp); nm = len(mp)
    slots = [None] * ns; meds = [None] * nm; T = TM = -1
    for t in seer_t + med_t:
        name, _, st = t.partition('：')
        flags = st.split('・') if st else []
        if '・' in name: name, *f2 = name.split('・'); flags += f2
        m = re.match(r'(占い|霊能)(\d)?', name)
        i = int(m.group(2)) - 1 if m.group(2) else 0
        isw = (sp if m.group(1) == '占い' else mp)[i] == 'W'
        x = (int(isw), 0 if '死亡' in flags else 1, 1 if '破綻' in flags else 0)
        if m.group(1) == '占い':
            slots[i] = x
            if '信用' in flags: T = i
        else:
            meds[i] = x
            if '信用' in flags: TM = i
    assert all(slots) and all(meds), (pub, key)
    cats = []
    for t in toks[1:]:
        mm = re.match(r'^(.*) (\d+)（狼(\d+)）$', t)
        if not mm: continue
        k, w = int(mm.group(2)), int(mm.group(3))
        cats.append((cat_r(mm.group(1), ns), w, k - w))
    n = int(re.match(r'生存(\d+)', toks[0]).group(1))
    return dict(n=n, slots=tuple(slots), meds=tuple(meds), T=T, TM=TM, cats=tuple(sorted(cats)))

def make_state(P, nt, bel):
    return ('D', P['slots'], P['meds'], P['T'], P['TM'], P['cats'], None, nt, E.norm_bel(bel))
