# 10a狩人：盤面ごとに村の進行の候補を1つの共通リストにし、その盤面のすべての内訳で村勝率を求める。
# 村は内訳を知らないので、ナッシュ均衡では「盤面ごとに1つの進行」を全内訳に当てはめた値が要る。
# 結果は r10b_<key>.json（{進行ID: [村勝率, 狂人の霊能結果]}）。r10a_<key>.json に同じ進行があれば計算を省く。
import sys, json, time, os, itertools; sys.setrecursionlimit(1000000)
import engine10 as E, e10a, run10a
from fractions import Fraction
if os.environ.get('HKEY'): E.HKEY[0] = True   # メモリ節約：局面の hash だけを覚える

BASE = run10a.BASE

def pid(c):
    base = f"{c['sp']}|{c['gp']}|{c['mp']}|{int(c['hm'])}|{c['ds']}"
    return base + ('|co2' if c.get('hg') == 'co2' else '') + ('|cw' if c.get('cw') else '') + (f"|g{round(c['hgm'] * 100)}" if c.get('hgm') is not None else '')

def board_candidates(board):
    """盤面（占いCO数-霊能CO数）ごとの進行の候補。内訳によらず同じ規則として当てはめる"""
    ns, nm = map(int, board.split('-'))
    if ns == 0: seer = [('ignore', 'plain')]
    elif ns == 1: seer = [('keep', 'info'), ('roller', 'plain'), ('roller', 'anti'), ('ignore', 'plain'), ('ignore', 'anti')]
    # 占いCO者が2人以上：これまでどの内訳でも最善にならなかった組み合わせ（真置き＋○優先・灰ランダムなど）は外す
    # 占い無視（灰ランダム）も2人以上ではどの内訳でも最善にならず、計算が非常に重いので外す
    else: seer = [('keep', 'info'), ('trust', 'info'), ('trust', 'anti'), ('roller', 'info'), ('roller', 'anti'), ('roller', 'plain')]
    # 占い1●止めロラ：占いロラを始め、霊能結果で●が出たらロラを止める（霊能CO者がいるときだけ意味がある）
    if ns >= 2 and nm >= 1: seer += [('rstop', 'info'), ('rstop', 'anti'), ('rstop', 'plain')]
    # 全占いの●優先（真置きしていない占いの●も見る）。並び順を変えないよう最後に足す
    if ns >= 2: seer += [('keep', 'infoa'), ('trust', 'infoa')]
    if nm == 0: med = [('trust', False)]
    elif nm == 1: med = [('trust', False), ('trust', True)]
    else: med = [('trust', False), ('roller', False)]
    # 指定役：占い指定 / 霊指定 / 自由投票（占いCO者がいなければ占い指定は霊指定と同じ、霊能CO者がいなければ逆も同じ）
    dss = ['seer', 'medium', 'none']
    if ns == 0: dss = ['medium', 'none']
    if nm == 0: dss = ['seer', 'none']
    out = []
    for (s_, g), (m, h), d in itertools.product(seer, med, dss):
        if s_ == 'ignore' and d == 'seer' and nm > 0: continue   # 占いを無視するなら占い指定はない
        out.append(dict(sp=s_, tp='rand', gp=g, mp=m, hm=h, ds=d, hg=None))
        # 占いロラでは、狩人が占いCO者を護衛して灰でGJを出さない進行も試す（終盤の偶奇がずれないように）
        # 4-0（真狂狼狼-欠）は占いロラ＋狩人は占いCO護衛で村勝率100%になる。護衛なしの占いロラは非常に重く（1件3時間以上・メモリ不足）、
        # 100%を超えることはないので計算しない
        if s_ == 'roller' and (ns, nm) == (4, 0): out[-1]['hg'] = 'co2'
        elif s_ == 'roller': out.append(dict(sp=s_, tp='rand', gp=g, mp=m, hm=h, ds=d, hg='co2'))
    # 4CO（占いまたは霊能のCO者が4人）：人外3人が全員CO者なので灰は全員人間。ロラで必ず勝てるので、ロラの進行だけを候補にする
    if ns == 4: out = [c for c in out if c['sp'] == 'roller']
    if nm == 4: out = [c for c in out if c['mp'] == 'roller']
    for c in out: c['cw'] = 0
    # 確定白に指定役引継ぎ（cw）：指定役（真置きの占い・霊能）がいなくなったら確定白が指定役になる。並び順を変えないよう最後に足す
    # 4CO は既に村勝率100%なので足さない。自由投票の進行（ds none）では意味がない
    if ns < 4 and nm < 4: out += [dict(c, cw=1) for c in out if c['ds'] != 'none']
    for c in out: c['hgm'] = None
    # 狩人の混合護衛（hgm）：狩人は確率 g で指定役を、残りは生存者からランダムに護衛する。ロラ系・他占い吊りの進行に、g = 0.4 / 0.5 / 0.75 を足す
    # （自由投票の進行は指定役がいないので意味がない。狩人は占いCO護衛・確定白に指定役引継ぎとは組み合わせない）。並び順を変えないよう最後に足す
    # 3-1・3-2 は1件10〜20分かかり、3-1 の主な内訳（真狂狼-真）でも上がらなかったので足さない
    if ns < 4 and nm < 4 and (ns, nm) not in ((3, 1), (3, 2)):
        base = [c for c in out if c['sp'] in ('roller', 'rstop', 'trust') and c['ds'] != 'none' and not c.get('hg') and not c['cw']]
        out += [dict(c, hgm=Fraction(g, 100)) for g in (40, 50, 75) for c in base]
    # 占い1●止めロラの追加分：全占いの●優先、および狩人は占いCO護衛との組み合わせ。並び順を変えないよう最後に足す
    if 2 <= ns < 4 and 1 <= nm < 4:
        for (m, h), d in itertools.product(med, dss):
            out.append(dict(sp='rstop', tp='rand', gp='infoa', mp=m, hm=h, ds=d, hg=None, cw=0, hgm=None))
            for g in ('info', 'anti', 'plain', 'infoa'):
                out.append(dict(sp='rstop', tp='rand', gp=g, mp=m, hm=h, ds=d, hg='co2', cw=0, hgm=None))
        # ●で止まった後だけ●優先（infos）。確定白に指定役引継ぎとの組み合わせも
        for (m, h), d in itertools.product(med, dss):
            out.append(dict(sp='rstop', tp='rand', gp='infos', mp=m, hm=h, ds=d, hg=None, cw=0, hgm=None))
            if d != 'none': out.append(dict(sp='rstop', tp='rand', gp='infos', mp=m, hm=h, ds=d, hg=None, cw=1, hgm=None))
    return out

def old_cache(key):
    """r10a の結果（同じ規則・同じエンジン）を流用する"""
    f = f'r10a_{key}.json'
    if BASE.get('fix2') or not os.path.exists(f): return {}   # r10a は fix2 前の規則なので使わない
    out = {}
    for r in json.load(open(f)):
        if r.get('tp', 'rand') != 'rand': continue
        c = dict(sp=r['sp'], tp='rand', gp=r.get('gp', 'info'), mp=r['mp'], hm=bool(r.get('hm')), ds=r['ds'])
        out[pid(c)] = [r['v'], r['mm']]
    return out

def run_part(key, i, K):
    board = e10a.board_of(key)
    mms = ('W', 'B', 'contra') if 'M' in key.split('-')[1] else ('B',)
    cache = old_cache(key)
    import glob   # 番号の付け方が変わっても、計算済みの進行は使い回す
    for f in glob.glob(f'r10b_{key}.part*of*.json'):
        for p, v in json.load(open(f)).items(): cache.setdefault(p, v)
    res = {}
    for n, c in enumerate(board_candidates(board)):
        if n % K != i: continue
        p = pid(c)
        if p in cache: res[p] = cache[p]; continue
        t = time.time(); best = None
        for mm in mms:
            E.setpol(**{**BASE, **c, 'mm': mm})
            v = E.V(e10a.initial10(key))
            if best is None or v < best[0]: best = (v, mm)
        res[p] = [best[0], best[1]]
        print(key, p, round(best[0], 4), best[1], round(time.time() - t), 's', flush=True)
    json.dump(res, open(f'r10b_{key}.part{i}of{K}.json', 'w'))
    print('DONE', key, i, K, flush=True)

if __name__ == '__main__':
    run_part(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
