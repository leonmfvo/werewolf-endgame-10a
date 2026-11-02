# 分岐サイトの全分岐ツリーに出てくる昼の盤面（compute/tree/ents.json の公開情報）を、game10 の見た目（ラベルの並び）にする。
# 真置き（◎）は村の決め事なので使わない（◎だけが違う盤面は同じ盤面）。死んだ占い・霊能CO者は「†占a」の見えない席として残す。
import json, os, re, sys
from collections import defaultdict
from game10 import parse, compose, label_key, worlds

LET = 'abc'

def cat_r(name, ns):
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
    return tuple(r), fl

def labels_of(pub, key):
    toks = pub.split('／')
    sp, mp = key.split('-')
    ns, nm = len(sp), len(mp)
    L = (lambda n: (lambda i: LET[i] if n > 1 else ''))
    out = []
    for t in toks[1:]:
        if re.match(r'^(占い|霊能)', t) and not re.match(r'^占い\d?の', t):
            name, _, st = t.partition('：')
            flags = st.split('・') if st else []
            if '・' in name: name, *f2 = name.split('・'); flags += f2
            m = re.match(r'(占い|霊能)(\d)?', name)
            i = int(m.group(2)) - 1 if m.group(2) else 0
            kind = '占' if m.group(1) == '占い' else '霊'
            let = L(ns)(i) if kind == '占' else L(nm)(i)
            out.append(compose(dict(kind=('' if '死亡' not in flags else '†') + kind, let=let, broken=('破綻' in flags), conf=False, marks=frozenset())))
            continue
        mm = re.match(r'^(.*) (\d+)（狼(\d+)）$', t)
        if not mm: continue
        r, fl = cat_r(mm.group(1), ns)
        marks = frozenset((L(ns)(i), '白' if c == 1 else '黒') for i, c in enumerate(r) if c)
        kind = '確白' if fl == 1 else '狩' if fl == 2 else ''
        out += [compose(dict(kind=kind, let='', broken=False, conf=(fl == 1), marks=marks))] * int(mm.group(2))
    return tuple(sorted(out, key=label_key))

def all_boards(ents_path):
    """{人数: [ラベルの並び]}（重複なし、出てくる重みの大きい順）"""
    ents = json.load(open(ents_path))
    w = defaultdict(float)
    for x in ents: w[labels_of(x['pub'], x['key'])] += x['w']
    by = defaultdict(list)
    for b, ww in sorted(w.items(), key=lambda kv: -kv[1]):
        n = sum(1 for l in b if not l.startswith('†'))
        by[n].append(list(b))
    return by

def save(ents_path, out):
    """盤面一覧を保存（内訳が1つもない盤面＝この前提ではありえない盤面は除く）"""
    by = all_boards(ents_path)
    res = {n: [b for b in by[n] if worlds(b)] for n in sorted(by)}
    json.dump(res, open(out, 'w'), ensure_ascii=False)
    for n in res: print(n, len(by[n]), '->', len(res[n]))

def load(path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'boards10.json')):
    return {int(n): v for n, v in json.load(open(path)).items()}

if __name__ == '__main__':
    save(sys.argv[1], sys.argv[2])
