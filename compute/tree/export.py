# cache/（eng/eng_build.py の出力）から、表示ページ（pos/index.html）が読むデータ pos/data/b<人数>.json を作る。
# 12A猫のサイトと同じ形：盤面ごとに 生存状況 → 内訳 の順に並べ、帰着先を「○%の盤面に進むパターン」にまとめる。
import json, os, sys, glob, re
from fractions import Fraction as F
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'eng'))
import build10a_site as B1

CACHE, OUT = sys.argv[1], sys.argv[2]
def ab(t):
    t = re.sub(r'占い(CO者)?([123])', lambda m: '占' + 'abc'[int(m.group(2)) - 1], t)
    return re.sub(r'霊能(CO者)?([123])', lambda m: '霊' + 'abc'[int(m.group(2)) - 1], t)

def wk(name):
    """1狼1狂生存・灰に狩 → 1w1k生存（狩生存）"""
    m = re.match(r'(\d)狼(1狂)?生存(・灰に狩|・狩CO済み)?(（狂人はCO者）)?$', name)
    if not m: return name
    s = f'{m.group(1)}w' + ('1k' if m.group(2) else '') + '生存'
    tail = []
    if m.group(3) == '・灰に狩': tail.append('狩生存')
    if m.group(3) == '・狩CO済み': tail.append('狩CO済み')
    if m.group(4): tail.append('狂人はCO者')
    return s + ('（' + '・'.join(tail) + '）' if tail else '')

R = [json.load(open(f)) for f in glob.glob(os.path.join(CACHE, 'b*.json'))]
BYKEY = {(r['n'], r['lab'], r['note']): r for r in R}
def gname(g): return '、'.join(x for x in (g['truth'], g['wolves']) if x) or 'CO者なし'

def target(t, v):
    if t is None: return None
    pm, ph = F(t['pm']), {k: F(x) for k, x in t['ph'].items()}
    st = f'{t["w"]}w' + ('1k' if pm == 1 else '') + '生存'
    tail = []
    if ph['hide'] == 1: tail.append('狩生存')
    elif ph['co'] == 1: tail.append('狩CO済み')
    unk = []
    if 0 < pm < 1: unk.append(f'狂人生存{float(pm) * 100:.0f}%')
    if 0 < ph['hide'] < 1: unk.append(f'灰に狩{float(ph["hide"]) * 100:.0f}%')
    if 0 < ph['co'] < 1: unk.append(f'狩CO済み{float(ph["co"]) * 100:.0f}%')
    sit = st + ('（' + '・'.join(tail + unk) + '）' if tail or unk else '')
    cond = '、'.join(x for x in (sit, t['truth'], t['wolves']) if x)
    r2 = BYKEY.get((t['n'], t['lab'], t['note']))
    href = None
    if r2:
        gi = next((i for i, g in enumerate(r2['groups']) if g['truth'] == t['truth'] and g['wolves'] == t['wolves']), None)
        href = r2['id']
    return dict(n=t['n'], lab=t['lab'], note=t['note'], cond=cond, href=href)

def short(x): return ab(B1.short(x)) if x else ''

days = {}
for r in R:
    # 見出しが同じで値も同じ（進行だけ違う）内訳はまとめる
    keep, seen = [], set()
    for g in r['groups']:
        sig = (gname(g), tuple((o['name'], o['v']) for o in g['opts']))
        if sig in seen: continue
        seen.add(sig); keep.append(g)
    from collections import Counter
    dup = Counter(gname(g) for g in keep)
    groups = []
    for gi, g in enumerate(keep):
        opts = []
        for o in g['opts']:
            # 帰着先を行き着く村勝率ごとのパターンに
            pats = {}
            for s in o['succ']:
                pats.setdefault(s['v'], []).append(s)
            pl = []
            for v in sorted(pats, key=lambda x: -F(x)):
                L = sorted(pats[v], key=lambda s: -F(s['p']))
                tp = sum(F(s['p']) for s in L)
                ends = all(s['tgt'] is None for s in L)
                pl.append(dict(v=v, tp=str(tp), end=ends,
                               lines=[dict(p=s['p'], labs=' → '.join(short(x) for x in s['labs'][1:] if x) or '（そのまま）', tgt=target(s['tgt'], s['v'])) for s in L[:8]],
                               more=len(L) - 8 if len(L) > 8 else 0))
            ch = []
            seenc = set()
            for c in o['choices']:
                k = (c['who'], c['t'], tuple(a[0] for a in c['alts']))
                if k in seenc or len(c['alts']) < 2: continue
                seenc.add(k)
                alts = sorted(c['alts'], key=lambda a: -F(a[1]) if c['who'] == 'v' else F(a[1]))
                bi = c['alts'][c['best']][0]
                ch.append(dict(who='村' if c['who'] == 'v' else '人外', alts=[[short(a[0]), a[1], a[0] == bi] for a in alts[:6]]))
                if len(ch) >= 4: break
            opts.append(dict(sit=wk(o['name']), v=o['v'], pats=pl, choices=ch))
        groups.append(dict(name=gname(g) + (f'（進行：{ab(g["policy"])}）' if dup[gname(g)] > 1 else ''), policy=ab(g['policy']), tree=g['tree'], key=g['key'], opts=opts))
    days.setdefault(r['n'], []).append(dict(id=r['id'], lab=r['lab'], note=r['note'], w=r['w'], groups=groups))
os.makedirs(OUT, exist_ok=True)
for n, L in days.items():
    json.dump(L, open(os.path.join(OUT, f'b{n}.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
print({n: len(L) for n, L in sorted(days.items())})
