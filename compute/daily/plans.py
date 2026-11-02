# 村の進め方の候補：指定の順（盤面にある区分の並べ方）× 本物のCO者は対抗に入れるか × 護衛の順 × GJ後に狩人がCOするか
# × 名指しの護衛指示（狩CO・ギが2人以上：A→B、B→C…、最後は護衛の順の区分。夜の結果で偽物が分かる）
import itertools
ORDER = ['霊', '猫', 'ギ', '狩', '灰']
def candidates(board, n_alive=None):
    # 区分は見た目の1文字目（狩A・狩B は前の日までの公開の出来事で区別できる狩）。白は指定・護衛の区分にしない
    present = sorted({l for l in board if l[0] != '白'}, key=lambda l: (ORDER.index(l[0]), l))
    cnt = lambda l: sum(1 for x in board if x[0] == l)
    out = []
    # 指定の順：1番目と2番目の区分を選び、残りは決まった順
    des_orders = []
    for a in present:
        for b in [x for x in present if x != a] or [None]:
            des_orders.append(tuple([a] + ([b] if b else []) + [x for x in present if x not in (a, b)]))
    # 護衛の順：1番目の区分を選び、残りは決まった順
    guard_orders = [tuple([a] + [x for x in present if x != a]) for a in present] if len(board) >= 4 else [tuple(present)]
    for des in des_orders:
        for counter in (True, False):
            if not counter and not any(cnt(l) >= 2 for l in ('霊', '猫', '狩', 'ギ')): 
                if counter is False: continue
            for guard in guard_orders:
                for co in ((True, False) if len(board) >= 4 else (True,)):
                    for mode in ('designate', 'spread'):
                        for chain in ((False, True) if any(cnt(l) >= 2 for l in ('狩', 'ギ')) else (False,)):
                            out.append(dict(des=des, counter=counter, guard=guard, co=co, mode=mode, chain=chain))
    # 対抗に入れるかが意味を持たない盤面では重複を除く
    seen = set(); res = []
    for p in out:
        k = (p['des'], p['counter'] if any(cnt(l) >= 2 for l in ('霊', '猫', '狩', 'ギ')) else None, p['guard'], p['co'], p['mode'], p['chain'])
        if k in seen: continue
        seen.add(k); res.append(p)
    return res
