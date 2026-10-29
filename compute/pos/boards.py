# 5人日の盤面一覧。labels：見え方の並び、cases：「または」で並べた内訳（等確率）。
# 内訳：fixed（位置→役。複数の並びをリストで書くと等確率）、gray（残りの人に入る役の数。並びは等確率）
import re

def G(spec):
    return {r: int(k) for r, k in re.findall(r'([VHXW])(\d)', spec)}

def C(name, gray, fixed=None):
    return dict(name=name, gray=G(gray), fixed=fixed or {})

def two(i, j, a, b):   # 位置 i, j に役 a, b（どちらがどちらか不明）
    return [{i: a, j: b}, {i: b, j: a}]

HUNT = {'なし': '狩人なし', '潜伏': '灰に狩人潜伏'}

def onewolf(pre, fixed, cond, g1, g2, hunter=True, extra=None):
    """灰に「1狼」または「1狼1狂」。g1, g2 は狩人なしの灰の内訳（村人の数で合わせる）"""
    out = []
    for h in (('なし', '潜伏') if hunter else ('なし',)):
        def addH(gs):
            if h == 'なし': return gs
            d = G(gs); d['V'] -= 1; d['H'] = 1
            return ''.join(f'{r}{k}' for r, k in d.items() if k)
        cs = [C('灰に1狼', addH(g1), fixed), C('灰に1狼1狂', addH(g2), fixed)]
        c = cond + ['灰に1狼または1狼1狂'] + ([HUNT[h]] if hunter else [])
        out.append(dict(labels=pre, cond=c, cases=cs, group=extra))
    return out

def boards():
    B = []
    L = lambda s: s.split(',')
    # ---- 占い師（真）が生きている
    B += onewolf(L('占,灰,灰,灰,灰'), {0: 'S'}, ['占い真'], 'V3W1', 'V2X1W1', extra='占い師あり')
    for h in ('なし', '潜伏'):
        B.append(dict(labels=L('占,灰,灰,灰,灰'), cond=['占い真', '灰に2狼', HUNT[h]], group='占い師あり',
                      cases=[C('灰に2狼', 'V2W2' if h == 'なし' else 'V1H1W2', {0: 'S'})]))
    B += onewolf(L('占,白,灰,灰,灰'), {0: 'S', 1: 'V'}, ['占い真', '白は村人'], 'V2W1', 'V1X1W1', extra='占い師あり')
    B += onewolf(L('占,白,白,灰,灰'), {0: 'S', 1: 'V', 2: 'V'}, ['占い真', '白は村人'], 'V1W1', 'X1W1', hunter=False, extra='占い師あり')
    B.append(dict(labels=L('占,黒,灰,灰,灰'), cond=['占い真', '黒は狼', '灰にもう1狼または狂人'], group='占い師あり',
                  cases=[C('灰にもう1狼', 'V2W1', {0: 'S', 1: 'W'}), C('灰に狂人', 'V2X1', {0: 'S', 1: 'W'})]))
    B += onewolf(L('占,霊,灰,灰,灰'), {0: 'S', 1: 'M'}, ['占い・霊能真'], 'V2W1', 'V1X1W1', extra='占い師あり')
    B += onewolf(L('占,狩,灰,灰,灰'), {0: 'S', 1: 'H'}, ['占い・狩人真'], 'V2W1', 'V1X1W1', hunter=False, extra='占い師あり')
    B += onewolf(L('占,霊,狩,灰,灰'), {0: 'S', 1: 'M', 2: 'H'}, ['占い・霊能・狩人真'], 'V1W1', 'X1W1', hunter=False, extra='占い師あり')
    B += onewolf(L('占,霊,白,灰,灰'), {0: 'S', 1: 'M', 2: 'V'}, ['占い・霊能真', '白は村人'], 'V1W1', 'X1W1', hunter=False, extra='占い師あり')
    # ---- 占い師が死亡
    B += onewolf(L('霊,灰,灰,灰,灰'), {0: 'M'}, ['霊能真'], 'V3W1', 'V2X1W1', extra='占い師なし')
    B += onewolf(L('狩,灰,灰,灰,灰'), {0: 'H'}, ['狩人真'], 'V3W1', 'V2X1W1', hunter=False, extra='占い師なし')
    B += onewolf(L('霊,狩,灰,灰,灰'), {0: 'M', 1: 'H'}, ['霊能・狩人真'], 'V2W1', 'V1X1W1', hunter=False, extra='占い師なし')
    B += onewolf(L('白,灰,灰,灰,灰'), {0: 'V'}, ['白は村人'], 'V3W1', 'V2X1W1', extra='占い師なし')
    B += onewolf(L('灰,灰,灰,灰,灰'), {}, [], 'V4W1', 'V3X1W1', extra='占い師なし')
    for h in ('なし', '潜伏'):
        B.append(dict(labels=L('霊,灰,灰,灰,灰'), cond=['霊能真', '灰に2狼', HUNT[h]], group='占い師なし',
                      cases=[C('灰に2狼', 'V2W2' if h == 'なし' else 'V1H1W2', {0: 'M'})]))
        B.append(dict(labels=L('灰,灰,灰,灰,灰'), cond=['灰に2狼', HUNT[h]], group='占い師なし',
                      cases=[C('灰に2狼', 'V3W2' if h == 'なし' else 'V2H1W2')]))
    # ---- 占い2CO（どちらが真か不明）
    for h in ('なし', '潜伏'):
        gH = (lambda s: s) if h == 'なし' else (lambda s: s.replace('V2', 'V1H1').replace('V3', 'V2H1'))
        B.append(dict(labels=L('占,占,灰,灰,灰'), cond=['占いは真狂', '灰に1狼', HUNT[h]], group='占い2CO',
                      cases=[C('真狂', gH('V2W1'), two(0, 1, 'S', 'X'))]))
        B.append(dict(labels=L('占,占,灰,灰,灰'), cond=['占いは真狼', HUNT[h]], group='占い2CO',
                      cases=[C('真狼', gH('V3'), two(0, 1, 'S', 'W'))]))
        B.append(dict(labels=L('占,占,灰,灰,灰'), cond=['占いは真狂または真狼', '狼は合わせて1', HUNT[h]], group='占い2CO',
                      cases=[C('真狂', gH('V2W1'), two(0, 1, 'S', 'X')), C('真狼', gH('V3'), two(0, 1, 'S', 'W'))]))
    B.append(dict(labels=L('占,占,霊,灰,灰'), cond=['霊能真', '占いは真狂または真狼', '狼は合わせて1'], group='占い2CO',
                  cases=[C('真狂', 'V1W1', [{**d, 2: 'M'} for d in two(0, 1, 'S', 'X')]),
                         C('真狼', 'V2', [{**d, 2: 'M'} for d in two(0, 1, 'S', 'W')])]))
    B.append(dict(labels=L('占,占,狩,灰,灰'), cond=['狩人真', '占いは真狂または真狼', '狼は合わせて1'], group='占い2CO',
                  cases=[C('真狂', 'V1W1', [{**d, 2: 'H'} for d in two(0, 1, 'S', 'X')]),
                         C('真狼', 'V2', [{**d, 2: 'H'} for d in two(0, 1, 'S', 'W')])]))
    # ---- 霊能2CO
    B.append(dict(labels=L('占,霊,霊,灰,灰'), cond=['占い真', '霊能は真狂または真狼', '狼は合わせて1'], group='霊能2CO',
                  cases=[C('真狂', 'V1W1', [{**d, 0: 'S'} for d in two(1, 2, 'M', 'X')]),
                         C('真狼', 'V2', [{**d, 0: 'S'} for d in two(1, 2, 'M', 'W')])]))
    B.append(dict(labels=L('霊,霊,灰,灰,灰'), cond=['霊能は真狂または真狼', '狼は合わせて1', '狩人なし'], group='霊能2CO',
                  cases=[C('真狂', 'V2W1', two(0, 1, 'M', 'X')), C('真狼', 'V3', two(0, 1, 'M', 'W'))]))
    # ---- 占い1CO（真偽不明）
    B.append(dict(labels=L('占,灰,灰,灰,灰'), cond=['占いは真または狂人', '灰に1狼', '狩人なし'], group='占い師あり',
                  cases=[C('占い真', 'V3W1', {0: 'S'}), C('占いは狂人', 'V3W1', {0: 'X'})]))
    for i, b in enumerate(B):
        b['id'] = f'p5-{i + 1:02d}'
        b['note'] = ','.join(b['labels']) + '（' + '、'.join(b['cond']) + '）'
    return B

if __name__ == '__main__':
    bs = boards(); print(len(bs))
    for b in bs: print(b['id'], b['note'])
