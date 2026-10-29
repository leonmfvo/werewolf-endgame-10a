# 分岐サイトの局面の文字列（例：生存7（狼2）／灰 5（狼2）／占いの○ 1（狼0）／占いCO者：死亡・信用／霊能CO者）を、
# 盤面の書き方（占a,占b,白a,白ab,灰…）と条件に直す
import re

LET = 'abc'
TRUTH = {'T': '真', 'M': '狂', 'W': '狼'}

def seer_name(s, single):
    m = re.match(r'占い(\d)?', s)
    return '占' if single or not m.group(1) else '占' + LET[int(m.group(1)) - 1]

def med_name(s, single):
    m = re.match(r'霊能(\d)?', s)
    return '霊' if single or not m.group(1) else '霊' + LET[int(m.group(1)) - 1]

def cat_label(c):
    hunter = c.endswith('（狩人CO者）'); human = c.endswith('（人間確定）')
    c = re.sub(r'（(狩人CO者|人間確定)）$', '', c)
    if c == '灰': base = '灰'
    elif c == '人間確定': base = '確白'
    elif c == '': base = ''
    else:
        wh, bl = [], []
        for part in c.split('・'):
            m = re.match(r'占い(\d)?の([○●])', part)
            if not m: return c
            l = LET[int(m.group(1)) - 1] if m.group(1) else ''
            (wh if m.group(2) == '○' else bl).append(l)
        base = ('黒' + ''.join(sorted(bl)) if bl else '') + ('白' + ''.join(sorted(wh)) if wh else '')
    if hunter: return '狩' + (f'({base})' if base and base != '灰' else '')
    if human: return '確白' + (f'({base})' if base and base not in ('灰', '確白') else '')
    return base

ORDER = lambda l: (0 if l.startswith('占') else 1 if l.startswith('霊') else 2 if l.startswith('狩') else 3 if l.startswith('確白')
                   else 4 if l.startswith('黒') else 5 if l.startswith('白') else 6, l)

def parse(pub, key, hid):
    toks = pub.split('／')
    m = re.match(r'生存(\d+)（狼(\d+)）', toks[0]); n = int(m.group(1))
    sp, mp = key.split('-')
    s_single = len(sp) <= 1 or not any(re.match(r'占い\d', t) for t in toks)
    m_single = len(mp) <= 1 or not any(re.match(r'霊能\d', t) for t in toks)
    labels = []; pubc = []; wolves = []
    for t in toks[1:]:
        mm = re.match(r'^(.*) (\d+)（狼(\d+)）$', t)
        if mm:
            lab = cat_label(mm.group(1)); k = int(mm.group(2)); w = int(mm.group(3))
            labels += [lab] * k
            if w: wolves.append(f'{lab}に{w}狼' if k > 1 else f'{lab}が狼')
            continue
        name, _, st = t.partition('：')
        flags = st.split('・') if st else []
        if '・' in name: name, *f2 = name.split('・'); flags += f2
        if name.startswith('占い'): nm = seer_name(name, s_single)
        elif name.startswith('霊能'): nm = med_name(name, m_single)
        else: nm = name
        if '死亡' in flags: pubc.append(nm + '死亡' + ('（破綻）' if '破綻' in flags else ''))
        else:
            labels.append(nm)
            if '破綻' in flags: pubc.append(nm + '破綻')
        if '信用' in flags: pubc.append(nm + 'を真置き')
    labels.sort(key=ORDER)
    # 真偽（内訳）
    tr = []
    if sp: tr.append('占' + ''.join(TRUTH[c] for c in sp) if len(sp) > 1 else '占' + TRUTH[sp])
    if mp: tr.append('霊' + ''.join(TRUTH[c] for c in mp) if len(mp) > 1 else '霊' + TRUTH[mp])
    truth = '・'.join(tr) if tr else 'CO なし'
    if len(sp) > 1: truth = truth.replace('占', '占' + ''.join(LET[:len(sp)]) + '＝', 1)
    if len(mp) > 1: truth = truth.replace('霊', '霊' + ''.join(LET[:len(mp)]) + '＝', 1)
    hidden = ''
    if hid:
        x = re.search(r'狂人生存 (\d+)%', hid); y = re.search(r'狩人生存 (\d+)%', hid)
        hidden = '・'.join(s for s in [f'狂人生存{x.group(1)}%' if x else '', f'狩人生存{y.group(1)}%' if y else ''] if s)
    return n, ','.join(labels), pubc, truth, wolves, hidden

if __name__ == '__main__':
    import json, sys, collections
    E = json.load(open(sys.argv[1]))
    pages = collections.defaultdict(float); sec = collections.defaultdict(float)
    for e in E:
        n, lab, pubc, truth, wolves, hidden = parse(e['pub'], e['key'], e['hid'])
        pages[(n, lab, tuple(pubc))] += e['w']
    byn = collections.defaultdict(list)
    for k, w in pages.items(): byn[k[0]].append((w, k))
    for n in sorted(byn):
        L = sorted(byn[n], reverse=True)
        print(n, len(L), sum(w for w, _ in L))
        for w, k in L[:6]: print('   ', round(w, 4), k[1], '（' + '、'.join(k[2]) + '）' if k[2] else '')
