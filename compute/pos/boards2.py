# 5人日：見た目の盤面ごとに、真偽（占い真など）→ 生存状況（1w生存・1w1k生存・2w生存 × 狩の有無）を自動で並べる
from itertools import product

TOTAL = {'S': 1, 'M': 1, 'H': 1, 'X': 1, 'W': 2, 'V': 4}

def two(i, j, a, b): return [{i: a, j: b}, {i: b, j: a}]

# (見た目, [(真偽の名前, 固定の並び（リスト）)])
SURF = [
    ('占,灰,灰,灰,灰', [('占い真', [{0: 'S'}]), ('占いが狂人', [{0: 'X'}]), ('占いが狼', [{0: 'W'}])]),
    ('占,白,灰,灰,灰', [('占い真・白は村人', [{0: 'S', 1: 'V'}])]),
    ('占,白,白,灰,灰', [('占い真・白は村人', [{0: 'S', 1: 'V', 2: 'V'}])]),
    ('占,黒,灰,灰,灰', [('占い真・黒は狼', [{0: 'S', 1: 'W'}])]),
    ('占,霊,灰,灰,灰', [('占い・霊能真', [{0: 'S', 1: 'M'}])]),
    ('占,狩,灰,灰,灰', [('占い・狩人真', [{0: 'S', 1: 'H'}])]),
    ('占,霊,狩,灰,灰', [('占い・霊能・狩人真', [{0: 'S', 1: 'M', 2: 'H'}])]),
    ('占,霊,白,灰,灰', [('占い・霊能真・白は村人', [{0: 'S', 1: 'M', 2: 'V'}])]),
    ('占,占,灰,灰,灰', [('占いは真狂', two(0, 1, 'S', 'X')), ('占いは真狼', two(0, 1, 'S', 'W'))]),
    ('占,占,霊,灰,灰', [('占いは真狂・霊能真', [{**d, 2: 'M'} for d in two(0, 1, 'S', 'X')]),
                         ('占いは真狼・霊能真', [{**d, 2: 'M'} for d in two(0, 1, 'S', 'W')])]),
    ('占,占,狩,灰,灰', [('占いは真狂・狩人真', [{**d, 2: 'H'} for d in two(0, 1, 'S', 'X')]),
                         ('占いは真狼・狩人真', [{**d, 2: 'H'} for d in two(0, 1, 'S', 'W')])]),
    ('霊,灰,灰,灰,灰', [('霊能真', [{0: 'M'}]), ('霊能が狂人', [{0: 'X'}])]),
    ('狩,灰,灰,灰,灰', [('狩人真', [{0: 'H'}])]),
    ('霊,狩,灰,灰,灰', [('霊能・狩人真', [{0: 'M', 1: 'H'}])]),
    ('占,霊,霊,灰,灰', [('占い真・霊能は真狂', [{**d, 0: 'S'} for d in two(1, 2, 'M', 'X')]),
                         ('占い真・霊能は真狼', [{**d, 0: 'S'} for d in two(1, 2, 'M', 'W')])]),
    ('霊,霊,灰,灰,灰', [('霊能は真狂', two(0, 1, 'M', 'X')), ('霊能は真狼', two(0, 1, 'M', 'W'))]),
    ('白,灰,灰,灰,灰', [('白は村人', [{0: 'V'}])]),
    ('灰,灰,灰,灰,灰', [('', [{}])]),
]

def sit_name(w, x, h):
    return f'{w}w' + (f'{x}k' if x else '') + '生存' + ('・狩生存' if h else '')

def situations(labels, fixed):
    """固定の役を含めて、生存する狼 w・狂人 x・狩人 h の組と、灰に入る役の数"""
    f0 = fixed[0]; nfree = len(labels) - len(f0)
    fc = {r: sum(1 for v in f0.values() if v == r) for r in TOTAL}
    out = []
    for w, x, h in product((1, 2), (0, 1), (0, 1)):
        gw, gx, gh = w - fc['W'], x - fc['X'], h - fc['H']
        if min(gw, gx, gh) < 0: continue
        gv = nfree - gw - gx - gh
        if gv < 0 or gv + fc['V'] > TOTAL['V']: continue
        n = len(labels)
        if x and 2 * (w + 1) > n: continue          # PP 確定（村勝率0）は載せない
        gray = {r: k for r, k in (('W', gw), ('X', gx), ('H', gh), ('V', gv)) if k}
        out.append(dict(key=(w, x, h), title=sit_name(w, x, h), gray=gray))
    return out

def surfaces():
    res = []
    for si, (lab, truths) in enumerate(SURF):
        labels = lab.split(',')
        T = []
        for tn, fixed in truths:
            secs = []
            sits = situations(labels, fixed)
            for s in sits:
                secs.append(dict(title=s['title'], key=s['key'],
                                 board=dict(labels=labels, cases=[dict(name=s['title'], gray=s['gray'], fixed=fixed)])))
            # 1w と 1w1k のどちらか分からない（狩の有無ごと）
            for h in (0, 1):
                a = next((s for s in sits if s['key'] == (1, 0, h)), None); b = next((s for s in sits if s['key'] == (1, 1, h)), None)
                if a and b:
                    secs.append(dict(title='1wか1w1kか不明' + ('・狩生存' if h else ''), key=(1, 9, h),
                                     board=dict(labels=labels, cases=[dict(name=a['title'], gray=a['gray'], fixed=fixed),
                                                                      dict(name=b['title'], gray=b['gray'], fixed=fixed)])))
            secs.sort(key=lambda s: s['key'])
            T.append(dict(name=tn, sections=secs))
        res.append(dict(id=f's5-{si + 1:02d}', labels=labels, truths=T))
    return res

if __name__ == '__main__':
    n = 0
    for s in surfaces():
        print(s['id'], ','.join(s['labels']))
        for t in s['truths']:
            print('   ', t['name'], [x['title'] for x in t['sections']]); n += len(t['sections'])
    print(n)
