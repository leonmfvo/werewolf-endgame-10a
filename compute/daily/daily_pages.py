# 日ごとに解いた辞書（data/dict.json）から、4・5人日のページ用の説明（data/d<n>.json）を作る。
# 内訳ごとの村勝率は「その日のうちの決着」＋「翌日の状態での、その内訳の村勝率」。翌日の状態も同じ辞書の進め方で解き直す。
import sys, json, os
from fractions import Fraction as F
from collections import defaultdict
import game10 as GM
from game10 import Game
from plans10 import candidates
import daily as D, rundaily as RD
import vote3g as G3

from analyze45 import assemble, who
import wikitext as WT
from vote3 import RN

WV = {}   # 状態のキー → {(役, 狼が知っている人): 村勝率}
SID = {}  # ページに載せる翌日の状態のキー → 番号（data/s<n>.json の何番目か）
SQ = []   # 説明をまだ作っていない翌日の状態

def sid_of(key):
    if key not in SID: SID[key] = len(SQ); SQ.append(key)
    return SID[key]

def adv_policy(labels, worlds, plan):
    GM.MODE.update(exact=False, tags=False)
    g = Game(labels, plan, start=worlds); root, _ = g.root()
    return D.adversary_min(root)

def next_states(g, pol):
    """翌日の状態ごとに（正規形, 並び）"""
    GM.MODE.update(exact=True, tags=False)
    root, _ = g.root()
    term, nxt = D.outcomes(root, pol, True)
    out = {}
    for (hist, al, lab), ws in nxt.items():
        idx = {old: new for new, old in enumerate(al)}
        labs = [lab[i] for i in al]
        worlds = [(p, tuple(r[i] for i in al), tuple(idx[k] for k in kn)) for p, r, kn in ws]
        key, pos = D.canon(labs, worlds, with_pos=True)
        out[(hist, al, lab)] = (key, pos)
    return out

def next_value(ns, info):
    hist, al, lab, roles, know = info
    key, pos = ns[(hist, al, lab)]
    idx = {old: new for new, old in enumerate(al)}
    inv = {idx[al[old]]: new for new, old in enumerate(pos)}
    r = tuple(roles[al[i]] for i in pos)
    kn = tuple(sorted(inv[idx[k]] for k in know))
    return key, world_values(key)[(r, kn)], r

def walk(board, roles, node, pol, ns, reg=False):
    """決着か翌日までの道すじ：{説明: [確率, 確率×その先の村勝率]}。
    reg：翌日の状態に番号を付けて、鍵を (説明, 番号, 翌日の状態でのこの内訳の見出し) にする（ページで翌日の状態を開けるように）"""
    out = defaultdict(lambda: [F(0), F(0)])
    def go(nd, p, labs):
        if p == 0: return
        if nd.tag:
            t = nd.tag
            if t[0] == '吊': labs = labs + [f'{who(board, roles, t[1])}を吊る']
            elif t[0] == '道連れ': labs = labs + [f'道連れで{who(board, roles, t[1])}']
            elif t[0] == '噛み': labs = labs + [f'{who(board, roles, t[1])}を噛む']
            elif t[0] == 'GJ': labs = labs + ['GJ']
            elif t[0] == '猫噛み': labs = labs + ['猫噛みで狼が死ぬ']
            elif t[0] == '狩人CO': labs = labs + ['狩人CO']
        if nd.kind == 'N':
            key, v, r = next_value(ns, nd.info)
            k = ' → '.join(labs + ['翌日 ' + ','.join(key[0])])
            if reg: k = (k, sid_of(key), WT.case_title(list(key[0]), r, GM.situation(key[0], r), False))
            out[k][0] += p; out[k][1] += p * v; return
        if nd.kind == 'L':
            k = ' → '.join(labs) + (' → 村勝ち' if nd.v == 1 else ' → 狼勝ち' if nd.v == 0 else '')
            out[k][0] += p; out[k][1] += p * nd.v; return
        if nd.kind == 'C':
            for q, c in nd.ch: go(c, p * q, labs)
        elif nd.kind == 'T': go(nd.ch[0], p, labs)
        else: go(nd.ch[pol.get((nd.agent, nd.info), 0)], p, labs)
    go(node, F(1), [])
    return out

def run_plan(labels, worlds, plan, pol=None, with_paths=False):
    """進め方 plan での内訳ごとの村勝率（と道すじ）"""
    if pol is None: pol = adv_policy(labels, worlds, plan)[1]
    g = Game(labels, plan, start=worlds)
    ns = next_states(g, pol)
    st0 = dict(alive=tuple(range(len(labels))), lab=tuple(labels), hist=())
    per = []
    for p, roles, know in worlds:
        # 翌日の状態を解くと MODE が変わるので、内訳ごとに設定し直す（目印が切れて「〇〇を吊る」が抜けていた）
        GM.MODE.update(exact=True, tags=with_paths)
        nd = g.day(roles, dict(st0, bites=tuple(know)))
        pt = walk(labels, roles, nd, pol, ns, reg=with_paths)
        per.append((sum(x[1] for x in pt.values()), pt))
    return per

def world_values(key):
    if key in WV: return WV[key]
    labels, worlds = D.from_key(key)
    if len(labels) <= 3:
        R = G3.solve_board(labels, cases=[(p, r) for p, r, kn in worlds], extras=[kn for p, r, kn in worlds])
        vals = R['per'] if R else [F(0)] * len(worlds)
    else:
        D.value(key)   # 辞書になければ解いて、進め方を INFO に入れる
        vals = [v for v, _ in run_plan(labels, worlds, D.INFO[key]['plan'])]
    WV[key] = {(r, tuple(kn)): v for (p, r, kn), v in zip(worlds, vals)}
    tot = sum(p * v for (p, r, kn), v in zip(worlds, vals))
    assert tot == D.value(key), (key[0], tot, D.DICT[key])   # 辞書の値と一致すること（比べる相手の進め方の先は辞書にないこともあるので、なければ解いて足す）
    return WV[key]

def alt_plan(labels, worlds, best):
    """比べる相手：最善と「指定の順番の先頭・投票の仕方」が違う候補のうち一番よいもの"""
    scr = []
    for plan in candidates(labels):
        if (plan['des'][0], plan['mode']) == (best['des'][0], best['mode']): continue
        vf, pol = adv_policy_1(labels, worlds, plan)
        scr.append((vf, plan))
    if not scr: return None
    scr.sort(key=lambda x: -x[0])
    return max(((adv_policy(labels, worlds, p)[0], p) for _, p in scr[:3]), key=lambda x: x[0])[1]

def adv_policy_1(labels, worlds, plan):
    GM.MODE.update(exact=False, tags=False)
    g = Game(labels, plan, start=worlds); root, _ = g.root()
    return D.adversary_min(root, starts=1)

def vote_text(R):
    """3人の状態の村の投票（見た目と自分の役ごとの、区分ごとの確率）"""
    out = []
    for t, p in zip(R['vt'], R['ps']):
        labs = R['tg'][t]
        me = f'{t[0]}（{RN[t[1]]}）' if t[0][0] in ('灰', 'ギ', '白') else f'{t[0]}（本物）'
        d = [(labs[0], p), (labs[1], 1 - p)] if len(labs) == 2 else [(labs[0], F(1))]
        out.append(me + 'は' + '・'.join(f'{l}に{WT.fs(q) if q != 1 else "全部"}' for l, q in d if q))
    return '昼：' + '、'.join(out)

def hang_paths(labels, worlds, per_v, hangs):
    """3人の状態：内訳ごとの（村勝率, 道すじ）。道すじは吊られる人ごと"""
    per = []
    for (p, r, kn), x, hang in zip(worlds, per_v, hangs):
        pt = {}
        for k, q in hang.items():
            if q == 0: continue
            lab = f'{who(labels, r, k)}を吊る'
            if r[k] == 'W': lab += ' → 村勝ち'; w = F(1)
            elif r[k] == 'C': w = F(sum(1 for j in range(len(r)) if j != k and r[j] == 'W'), len(r) - 1); lab += ' → 道連れ'
            else: lab += ' → 狼勝ち'; w = F(0)
            pt[lab] = [F(q), F(q) * w]
        per.append((x, pt))
    return per

def solve3_full(labels, worlds):
    return G3.solve_board(labels, cases=[(p, r) for p, r, kn in worlds], extras=[kn for p, r, kn in worlds])

def state_entry(key):
    """翌日の状態の説明：盤面のページと同じ形（内訳ごとの割合と村勝率、道すじ）"""
    labels, worlds = D.from_key(key)
    ws0 = [(p, r) for p, r, kn in worlds]
    v = D.value(key)
    if len(labels) >= 4:
        plan = D.INFO[key]['plan']
        per = run_plan(labels, worlds, plan, with_paths=True)
    else:
        R = solve3_full(labels, worlds)
        plan = vote_text(R); per = hang_paths(labels, worlds, R['per'], R['hangs'])
    e = assemble(labels, ws0, [('g', plan, per, v)])
    fresh = False   # 生存状況ごとの盤面とは、内訳の割合や見分けられる人が違うことが多い（同じなら番号で分かる）
    assert sum(p * x for (p, _), (x, _) in zip(ws0, per)) == v
    return dict(n=len(labels), board=e['board'], v=e['v'], plan=e['plan'], secs=e['secs'], summ=e['summ'], fresh=fresh)

def board_page(board):
    """盤面のページ：生存状況（全員が知っている）ごとに、村の最善の進め方と比べる相手、内訳ごとの道すじ"""
    allw = sum(F(w) for w, _ in GM.worlds(board))
    secs = []; summ = []; v = F(0); va = F(0); has_alt = True
    for sit, key in D.board_keys(board).items():
        labels, worlds = D.from_key(key)
        share = sum(F(w) for w, r in GM.worlds(board) if GM.situation(board, r) == sit) / allw
        ws0 = [(p, r) for p, r, kn in worlds]
        if len(labels) >= 4:
            best = D.INFO[key]['plan']
            plans = [('g', best)]
            a = alt_plan(labels, worlds, best)
            if a: plans.append(('a', a))
            runs = []
            for tag, plan in plans:
                per = run_plan(labels, worlds, plan, with_paths=True)
                runs.append((tag, plan, per, sum(p * x for (p, _, _), (x, _) in zip(worlds, per))))
        else:
            R = solve3_full(labels, worlds)
            runs = [('g', vote_text(R), hang_paths(labels, worlds, R['per'], R['hangs']), R['v'])]
            if R['alt']:
                ps2, ads2 = R['alt']['ps'], R['alt']['ads']
                v2, p2, h2 = R['evalp'](ps2, ads2)
                runs.append(('a', vote_text(dict(R, ps=ps2)), hang_paths(labels, worlds, p2, h2), v2))
        assert runs[0][3] == D.value(key), (board, sit)
        e = assemble(labels, ws0, runs)
        for s in e['secs']:
            s['share'] = WT.fs(F(s['share']) * share)
            if len(e['secs']) == 1: s['title'] = sit
        secs += e['secs']
        x = e['summ'][0]; summ.append(dict(sit=sit, share=WT.fs(share), v=x['v'], va=x['va'], plan=e['plan'], plana=e['plana']))
        v += share * runs[0][3]
        if len(runs) > 1: va += share * runs[1][3]
        else: has_alt = False
    return dict(board=list(board), v=WT.fs(v), plan=None, va=WT.fs(va) if has_alt else None, plana=None, secs=secs, summ=summ)

def key_json(k):
    return json.dumps([list(k[0]), [[list(a), list(b), c] for a, b, c in k[1]]], ensure_ascii=False)

def key_from(j):
    x = json.loads(j)
    return (tuple(x[0]), tuple((tuple(a), tuple(b), c) for a, b, c in x[1]))

if __name__ == '__main__':
    n = int(sys.argv[1]); dst = sys.argv[2]
    sdst = os.environ.get('SFILE') or os.path.join(os.path.dirname(dst), f's{n}.json')   # 翌日の状態の説明（ページで開く）
    kdst = dst + '.keys.json'   # 翌日の状態の番号（途中から再開・盤面を足すとき用）
    RD.load()
    out = json.load(open(dst)) if os.path.exists(dst) else []
    done = {','.join(x['board']) for x in out}
    st = json.load(open(sdst)) if os.path.exists(sdst) and os.path.exists(kdst) else []
    if os.path.exists(kdst):
        for j in json.load(open(kdst)): sid_of(key_from(j))
    skip = set(os.environ.get('SKIP', '').split(';')) - {''}
    bl = RD.board_list(n)
    if os.environ.get('REVERSE'): bl = bl[::-1]   # 並行して作るとき：後ろから
    for b in bl:
        if not GM.worlds(b) or ','.join(b) in done or ','.join(b) in skip: continue
        out.append(board_page(b))
        print(','.join(b), out[-1]['v'], out[-1]['va'], len(SQ), flush=True)
        json.dump(out, open(dst, 'w'), ensure_ascii=False, separators=(',', ':'))
        json.dump([key_json(k) for k in SQ], open(kdst, 'w'), ensure_ascii=False)
    while len(st) < len(SQ):   # 翌日の状態の説明（その中の翌日の状態も足していく）
        st.append(state_entry(SQ[len(st)]))
        if len(st) % 200 == 0:
            print('states', len(st), '/', len(SQ), flush=True)
            json.dump(st, open(sdst, 'w'), ensure_ascii=False, separators=(',', ':')); json.dump([key_json(k) for k in SQ], open(kdst, 'w'), ensure_ascii=False)
    json.dump(st, open(sdst, 'w'), ensure_ascii=False, separators=(',', ':'))
    json.dump([key_json(k) for k in SQ], open(kdst, 'w'), ensure_ascii=False)
    print('states done', len(st), flush=True)
